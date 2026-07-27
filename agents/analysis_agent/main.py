"""Analysis Agent — suy luận AI cục bộ (ONNX) trên edge qua MQTT.

Deploy: VM/container 2 vCPU / 4GB RAM, CPU-only.
Giao tiếp: chỉ MQTT (không gọi hàm agent khác).
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.config import load_config, project_root  # noqa: E402
from shared.metrics import MetricsCollector  # noqa: E402
from shared.onnx_model import OnnxAnomalyModel  # noqa: E402
from shared.schemas import TOPICS, AnalysisResult, Heartbeat, SensorReading  # noqa: E402

AGENT_ID = "analysis_agent"
ROLE = "local_ai_inference"
LOG = logging.getLogger(AGENT_ID)


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
        topic_in = userdata["topic_readings"]
        client.subscribe(topic_in, qos=1)
        LOG.info("subscribed %s", topic_in)

    def on_disconnect(client, _userdata, rc):
        LOG.warning("MQTT disconnected rc=%s — will reconnect", rc)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    return client


def run(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    mqtt_cfg = cfg["mqtt"]
    analysis_cfg = cfg["analysis_agent"]
    metrics_cfg = cfg.get("metrics", {})

    host = os.environ.get("MQTT_HOST", mqtt_cfg.get("host", "localhost"))
    port = int(os.environ.get("MQTT_PORT", mqtt_cfg.get("port", 1883)))

    topics = mqtt_cfg.get("topics", {})
    topic_readings = topics.get("sensor_readings", TOPICS["sensor_readings"])
    topic_results = topics.get("analysis_results", TOPICS["analysis_results"])
    topic_heartbeat = topics.get("heartbeat", TOPICS["heartbeat"])

    model_rel = analysis_cfg.get("model_path", "models/anomaly.onnx")
    model_path = Path(model_rel)
    if not model_path.is_absolute():
        model_path = project_root() / model_path

    out_dir = Path(metrics_cfg.get("output_dir", "metrics"))
    sample_interval = float(metrics_cfg.get("sample_interval_sec", 1))
    heartbeat_every = max(1, int(analysis_cfg.get("heartbeat_every_n", 10)))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    backend = analysis_cfg.get("model_backend", "onnx")
    if backend != "onnx":
        raise SystemExit(f"Unsupported model_backend={backend!r} (step 2 uses onnx)")

    model = OnnxAnomalyModel(model_path)
    LOG.info("loaded ONNX model %s outputs=%s", model_path, model.output_names)

    metrics = MetricsCollector(AGENT_ID, sample_interval_sec=sample_interval)
    metrics.start()

    stop = False
    n_ok = 0
    n_bad = 0
    n_malformed = 0

    def _handle_signal(_signum, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    userdata = {"topic_readings": topic_readings}
    client = build_client(host, port)
    client.user_data_set(userdata)

    def on_message(_client, _userdata, msg):
        nonlocal n_ok, n_bad, n_malformed
        if stop:
            return
        try:
            reading = SensorReading.from_json(msg.payload)
        except Exception as exc:  # noqa: BLE001 — malformed không được crash process
            n_malformed += 1
            LOG.warning("malformed SensorReading rejected: %s", exc)
            return

        try:
            t0 = time.perf_counter()
            out = model.predict(reading)
            result = AnalysisResult(
                agent_id=AGENT_ID,
                trace_id=reading.trace_id,
                anomaly_score=out.anomaly_score,
                is_anomaly=out.is_anomaly,
                label=out.label,
                inference_ms=out.inference_ms,
            )
            client.publish(topic_results, result.to_json(), qos=1)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            metrics.record_latency(elapsed_ms)
            n_ok += 1
            if out.is_anomaly:
                n_bad += 1
            LOG.info(
                "result n=%s trace_id=%s label=%s score=%.4f infer=%.2fms total=%.1fms",
                n_ok,
                result.trace_id,
                result.label,
                result.anomaly_score,
                result.inference_ms,
                elapsed_ms,
            )
            if n_ok % heartbeat_every == 0:
                client.publish(
                    topic_heartbeat,
                    Heartbeat(agent_id=AGENT_ID, status="alive").to_json(),
                    qos=0,
                )
        except Exception:
            LOG.exception("inference/publish failed for trace_id=%s", getattr(reading, "trace_id", "?"))

    client.on_message = on_message
    client.connect_async(host, port, keepalive=60)
    client.loop_start()

    LOG.info(
        "Analysis agent started role=%s host=%s:%s in=%s out=%s",
        ROLE,
        host,
        port,
        topic_readings,
        topic_results,
    )

    try:
        while not stop:
            time.sleep(0.2)
    finally:
        metrics.stop()
        snap = metrics.dump(out_dir / f"{AGENT_ID}.json")
        LOG.info(
            "metrics dumped: %s | ok=%s anomalies=%s malformed=%s",
            snap,
            n_ok,
            n_bad,
            n_malformed,
        )
        client.loop_stop()
        client.disconnect()
        LOG.info("Analysis agent stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge Analysis Agent (ONNX)")
    parser.add_argument(
        "--config",
        default=os.environ.get("CONFIG_PATH"),
        help="Path to YAML config (default: configs/default.yaml)",
    )
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
