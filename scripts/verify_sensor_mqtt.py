#!/usr/bin/env python3
"""Subscribe MQTT và xác nhận SensorReading hợp lệ (bước 1)."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import paho.mqtt.client as mqtt

from shared.schemas import TOPICS, SensorReading


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--count", type=int, default=3, help="Số message cần nhận")
    args = parser.parse_args()

    topic = TOPICS["sensor_readings"]
    got: list[SensorReading] = []
    errors: list[str] = []

    def on_message(_client, _userdata, msg):
        try:
            reading = SensorReading.from_json(msg.payload)
            got.append(reading)
            print(
                f"OK trace_id={reading.trace_id} temp={reading.temperature_c} "
                f"pm25={reading.pm25_ugm3} co2={reading.co2_ppm}"
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            print(f"FAIL parse: {exc}", file=sys.stderr)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        client_id="verify_sensor",
        protocol=mqtt.MQTTv311,
    )
    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=30)
    client.subscribe(topic, qos=1)
    client.loop_start()
    print(f"Listening on {args.host}:{args.port} topic={topic} (need {args.count})")

    deadline = time.time() + args.timeout
    while time.time() < deadline and len(got) < args.count:
        time.sleep(0.2)

    client.loop_stop()
    client.disconnect()

    if errors:
        print(f"Parse errors: {len(errors)}", file=sys.stderr)
        return 2
    if len(got) < args.count:
        print(f"Timeout: got {len(got)}/{args.count}", file=sys.stderr)
        return 1
    print(f"PASS: received {len(got)} valid SensorReading(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
