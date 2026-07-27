"""Decision Agent — orchestrator nhẹ: cảnh báo + fallback khi analysis timeout.

Deploy: VM/container 2 vCPU / 4GB RAM, CPU-only.
Giao tiếp: chỉ MQTT (không gọi hàm agent khác).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.config import load_config  # noqa: E402
from shared.metrics import MetricsCollector  # noqa: E402
from shared.schemas import (  # noqa: E402
    TOPICS,
    AnalysisResult,
    DecisionAlert,
    Heartbeat,
    SensorReading,
)

AGENT_ID = "decision_agent"
ROLE = "decide_and_alert"
LOG = logging.getLogger(AGENT_ID)


@dataclass
class PendingTrace:
    reading: SensorReading
    received_at: float


def threshold_fallback(
    reading: SensorReading,
    thresholds: dict[str, Any],
) -> tuple[bool, str, str]:
    """Rule-based fallback khi analysis không phản hồi.

    Returns: (is_alert, severity, reason)
    """
    hits: list[str] = []
    t_temp = float(thresholds.get("temperature_c", 40))
    t_pm = float(thresholds.get("pm25_ugm3", 75))
    t_co2 = float(thresholds.get("co2_ppm", 1500))

    if reading.temperature_c >= t_temp:
        hits.append(f"temperature_c={reading.temperature_c}>={t_temp}")
    if reading.pm25_ugm3 >= t_pm:
        hits.append(f"pm25_ugm3={reading.pm25_ugm3}>={t_pm}")
    if reading.co2_ppm >= t_co2:
        hits.append(f"co2_ppm={reading.co2_ppm}>={t_co2}")

    if hits:
        return True, "degraded", "fallback thresholds exceeded: " + "; ".join(hits)
    return False, "degraded", "analysis timeout; fallback thresholds OK"


def decide_from_analysis(result: AnalysisResult) -> tuple[str, str, str]:
    """Map AnalysisResult → (severity, action, reason)."""
    if not result.is_anomaly:
        return (
            "info",
            "continue_monitoring",
            f"normal (score={result.anomaly_score:.4f})",
        )
    severity = "critical" if result.anomaly_score >= 0.05 else "warning"
    return (
        severity,
        "raise_alert",
        f"anomaly detected label={result.label} score={result.anomaly_score:.4f}",
    )


def build_client(host: str, port: int) -> mqtt.Client:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        client_id=AGENT_ID,
        protocol=mqtt.MQTTv311,
    )
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    def on_connect(client, userdata, _flags, rc):
        if rc != 0:
            LOG.error("MQTT connect failed rc=%s", rc)
            return
        LOG.info("MQTT connected to %s:%s", host, port)
        for key in ("topic_readings", "topic_results", "topic_heartbeat"):
            topic = userdata[key]
            client.subscribe(topic, qos=1)
            LOG.info("subscribed %s", topic)

    def on_disconnect(client, _userdata, rc):
        LOG.warning("MQTT disconnected rc=%s — will reconnect", rc)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    return client


def run(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    mqtt_cfg = cfg["mqtt"]
    decision_cfg = cfg["decision_agent"]
    metrics_cfg = cfg.get("metrics", {})

    host = os.environ.get("MQTT_HOST", mqtt_cfg.get("host", "localhost"))
    port = int(os.environ.get("MQTT_PORT", mqtt_cfg.get("port", 1883)))

    topics = mqtt_cfg.get("topics", {})
    topic_readings = topics.get("sensor_readings", TOPICS["sensor_readings"])
    topic_results = topics.get("analysis_results", TOPICS["analysis_results"])
    topic_alerts = topics.get("decision_alerts", TOPICS["decision_alerts"])
    topic_heartbeat = topics.get("heartbeat", TOPICS["heartbeat"])
    topic_control = topics.get("control", TOPICS["control"])

    timeout_sec = float(decision_cfg.get("analysis_timeout_sec", 5))
    thresholds = decision_cfg.get("alert_thresholds", {})
    out_dir = Path(metrics_cfg.get("output_dir", "metrics"))
    sample_interval = float(metrics_cfg.get("sample_interval_sec", 1))
    heartbeat_every = max(1, int(decision_cfg.get("heartbeat_every_n", 10)))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    metrics = MetricsCollector(AGENT_ID, sample_interval_sec=sample_interval)
    metrics.start()

    pending: dict[str, PendingTrace] = {}
    lock = threading.Lock()
    stop = False
    n_alerts = 0
    n_degraded = 0
    n_malformed = 0
    last_analysis_hb = 0.0

    def _handle_signal(_signum, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    userdata = {
        "topic_readings": topic_readings,
        "topic_results": topic_results,
        "topic_heartbeat": topic_heartbeat,
    }
    client = build_client(host, port)
    client.user_data_set(userdata)

    def publish_alert(alert: DecisionAlert) -> None:
        nonlocal n_alerts, n_degraded
        t0 = time.perf_counter()
        # Không block MQTT callback: tránh chờ wait_for_publish trong on_message
        client.publish(topic_alerts, alert.to_json(), qos=1)
        metrics.record_latency((time.perf_counter() - t0) * 1000)
        n_alerts += 1
        if alert.degraded:
            n_degraded += 1
        LOG.info(
            "alert n=%s trace_id=%s severity=%s degraded=%s e2e=%.1fms action=%s | %s",
            n_alerts,
            alert.trace_id,
            alert.severity,
            alert.degraded,
            alert.e2e_latency_ms or -1,
            alert.action,
            alert.reason,
        )
        if n_alerts % heartbeat_every == 0:
            client.publish(
                topic_heartbeat,
                Heartbeat(agent_id=AGENT_ID, status="alive").to_json(),
                qos=0,
            )

    def on_message(_client, _userdata, msg):
        nonlocal n_malformed, last_analysis_hb
        topic = msg.topic
        try:
            if topic == topic_readings:
                reading = SensorReading.from_json(msg.payload)
                with lock:
                    pending[reading.trace_id] = PendingTrace(
                        reading=reading,
                        received_at=time.time(),
                    )
                LOG.debug("pending trace_id=%s (queue=%s)", reading.trace_id, len(pending))

            elif topic == topic_results:
                result = AnalysisResult.from_json(msg.payload)
                with lock:
                    item = pending.pop(result.trace_id, None)
                if item is None:
                    # Đã fallback timeout trước đó — bỏ qua kết quả muộn
                    LOG.info(
                        "late analysis ignored trace_id=%s (already timed out/unknown)",
                        result.trace_id,
                    )
                    return
                e2e_ms = (time.time() - item.reading.ts) * 1000
                severity, action, reason = decide_from_analysis(result)
                alert = DecisionAlert(
                    agent_id=AGENT_ID,
                    trace_id=result.trace_id,
                    severity=severity,
                    action=action,
                    reason=reason,
                    e2e_latency_ms=round(e2e_ms, 2),
                    degraded=False,
                )
                publish_alert(alert)

            elif topic == topic_heartbeat:
                hb = json.loads(msg.payload)
                if hb.get("agent_id") == "analysis_agent":
                    last_analysis_hb = time.time()

        except Exception as exc:  # noqa: BLE001
            n_malformed += 1
            LOG.warning("malformed on %s rejected: %s", topic, exc)

    client.on_message = on_message
    client.connect_async(host, port, keepalive=60)
    client.loop_start()

    LOG.info(
        "Decision agent started role=%s host=%s:%s timeout=%ss alerts→%s",
        ROLE,
        host,
        port,
        timeout_sec,
        topic_alerts,
    )

    # Announce ready on control topic (optional observability)
    client.publish(
        topic_control,
        Heartbeat(agent_id=AGENT_ID, status="ready").to_json(),
        qos=0,
    )

    try:
        while not stop:
            now = time.time()
            timed_out: list[PendingTrace] = []
            with lock:
                expired = [
                    tid
                    for tid, item in pending.items()
                    if (now - item.received_at) >= timeout_sec
                ]
                for tid in expired:
                    timed_out.append(pending.pop(tid))

            for item in timed_out:
                reading = item.reading
                is_alert, severity, reason = threshold_fallback(reading, thresholds)
                e2e_ms = (time.time() - reading.ts) * 1000
                alert = DecisionAlert(
                    agent_id=AGENT_ID,
                    trace_id=reading.trace_id,
                    severity=severity,
                    action="raise_alert" if is_alert else "continue_monitoring_degraded",
                    reason=reason,
                    e2e_latency_ms=round(e2e_ms, 2),
                    degraded=True,
                )
                publish_alert(alert)
                if last_analysis_hb and (now - last_analysis_hb) > timeout_sec * 2:
                    LOG.warning(
                        "analysis heartbeat stale (%.1fs ago)",
                        now - last_analysis_hb,
                    )

            time.sleep(0.2)
    finally:
        metrics.stop()
        snap = metrics.dump(out_dir / f"{AGENT_ID}.json")
        LOG.info(
            "metrics dumped: %s | alerts=%s degraded=%s malformed=%s",
            snap,
            n_alerts,
            n_degraded,
            n_malformed,
        )
        client.loop_stop()
        client.disconnect()
        LOG.info("Decision agent stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge Decision Agent")
    parser.add_argument(
        "--config",
        default=os.environ.get("CONFIG_PATH"),
        help="Path to YAML config (default: configs/default.yaml)",
    )
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
