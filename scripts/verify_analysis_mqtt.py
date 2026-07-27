#!/usr/bin/env python3
"""Subscribe MQTT và xác nhận AnalysisResult hợp lệ (bước 2)."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import paho.mqtt.client as mqtt

from shared.schemas import TOPICS, AnalysisResult


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()

    topic = TOPICS["analysis_results"]
    got: list[AnalysisResult] = []
    errors: list[str] = []

    def on_message(_client, _userdata, msg):
        try:
            result = AnalysisResult.from_json(msg.payload)
            got.append(result)
            print(
                f"OK trace_id={result.trace_id} label={result.label} "
                f"score={result.anomaly_score} infer_ms={result.inference_ms}"
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            print(f"FAIL parse: {exc}", file=sys.stderr)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        client_id="verify_analysis",
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
    print(f"PASS: received {len(got)} valid AnalysisResult(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
