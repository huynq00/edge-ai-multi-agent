"""Sensor Agent — thu thập / giả lập cảm biến môi trường, publish qua MQTT.

Deploy: VM/container 2 vCPU / 4GB RAM, CPU-only.
Giao tiếp: chỉ MQTT (không gọi hàm agent khác).
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import signal
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt

# Cho phép chạy trực tiếp: python agents/sensor_agent/main.py
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.config import load_config  # noqa: E402
from shared.metrics import MetricsCollector  # noqa: E402
from shared.schemas import TOPICS, Heartbeat, SensorReading  # noqa: E402

AGENT_ID = "sensor_agent"
ROLE = "collect_and_preprocess"
LOG = logging.getLogger(AGENT_ID)


def simulate_reading(agent_id: str, anomaly_chance: float = 0.05) -> SensorReading:
    """Giả lập nhiệt độ, độ ẩm, PM2.5, CO₂ — thỉnh thoảng spike để test analysis sau."""
    if random.random() < anomaly_chance:
        return SensorReading(
            agent_id=agent_id,
            temperature_c=round(random.uniform(42.0, 55.0), 2),
            humidity_pct=round(random.uniform(85.0, 99.0), 2),
            pm25_ugm3=round(random.uniform(90.0, 180.0), 2),
            co2_ppm=round(random.uniform(1600.0, 2500.0), 2),
        )
    return SensorReading(
        agent_id=agent_id,
        temperature_c=round(random.uniform(22.0, 32.0), 2),
        humidity_pct=round(random.uniform(40.0, 70.0), 2),
        pm25_ugm3=round(random.uniform(8.0, 35.0), 2),
        co2_ppm=round(random.uniform(400.0, 900.0), 2),
    )


def build_client(host: str, port: int) -> mqtt.Client:
    # paho-mqtt 2.x: dùng VERSION1 để giữ callback kiểu (client, userdata, flags, rc)
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        client_id=AGENT_ID,
        protocol=mqtt.MQTTv311,
    )
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    def on_connect(client, _userdata, _flags, rc):
        if rc == 0:
            LOG.info("MQTT connected to %s:%s", host, port)
        else:
            LOG.error("MQTT connect failed rc=%s", rc)

    def on_disconnect(client, _userdata, rc):
        LOG.warning("MQTT disconnected rc=%s — will reconnect", rc)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect_async(host, port, keepalive=60)
    return client


def run(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    mqtt_cfg = cfg["mqtt"]
    sensor_cfg = cfg["sensor_agent"]
    metrics_cfg = cfg.get("metrics", {})

    host = os.environ.get("MQTT_HOST", mqtt_cfg.get("host", "localhost"))
    port = int(os.environ.get("MQTT_PORT", mqtt_cfg.get("port", 1883)))
    interval = float(sensor_cfg.get("interval_sec", 2))
    heartbeat_every = max(1, int(sensor_cfg.get("heartbeat_every_n", 5)))
    anomaly_chance = float(sensor_cfg.get("anomaly_chance", 0.05))

    topics = mqtt_cfg.get("topics", {})
    topic_readings = topics.get("sensor_readings", TOPICS["sensor_readings"])
    topic_heartbeat = topics.get("heartbeat", TOPICS["heartbeat"])

    out_dir = Path(metrics_cfg.get("output_dir", "metrics"))
    sample_interval = float(metrics_cfg.get("sample_interval_sec", 1))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    metrics = MetricsCollector(AGENT_ID, sample_interval_sec=sample_interval)
    metrics.start()

    client = build_client(host, port)
    client.loop_start()

    stop = False

    def _handle_signal(_signum, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    LOG.info(
        "Sensor agent started role=%s host=%s:%s interval=%ss topic=%s",
        ROLE,
        host,
        port,
        interval,
        topic_readings,
    )

    # Chờ kết nối MQTT (tối đa ~15s)
    deadline = time.time() + 15
    while time.time() < deadline and not stop:
        if getattr(client, "is_connected", lambda: False)():
            break
        time.sleep(0.2)
    else:
        if not stop and not client.is_connected():
            LOG.warning("MQTT not connected yet — publishing will retry via paho")

    n = 0
    try:
        while not stop:
            t0 = time.perf_counter()
            reading = simulate_reading(AGENT_ID, anomaly_chance=anomaly_chance)
            payload = reading.to_json()
            info = client.publish(topic_readings, payload, qos=1)
            info.wait_for_publish(timeout=5)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            metrics.record_latency(elapsed_ms)
            n += 1
            LOG.info(
                "published reading n=%s trace_id=%s temp=%.1f pm25=%.1f co2=%.0f (%.1f ms)",
                n,
                reading.trace_id,
                reading.temperature_c,
                reading.pm25_ugm3,
                reading.co2_ppm,
                elapsed_ms,
            )

            if n % heartbeat_every == 0:
                hb = Heartbeat(agent_id=AGENT_ID, status="alive")
                client.publish(topic_heartbeat, hb.to_json(), qos=0)

            time.sleep(interval)
    finally:
        metrics.stop()
        snap = metrics.dump(out_dir / f"{AGENT_ID}.json")
        LOG.info("metrics dumped: %s", snap)
        client.loop_stop()
        client.disconnect()
        LOG.info("Sensor agent stopped after %s readings", n)


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge Sensor Agent")
    parser.add_argument(
        "--config",
        default=os.environ.get("CONFIG_PATH"),
        help="Path to YAML config (default: configs/default.yaml)",
    )
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
