#!/usr/bin/env python3
"""Subscribe MQTT và xác nhận DecisionAlert (bước 3).

Mặc định chấp nhận cả alert thường và degraded.
Dùng --require-degraded để bắt buộc thấy ít nhất 1 alert degraded (fault demo).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import paho.mqtt.client as mqtt

from shared.schemas import TOPICS, DecisionAlert


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument(
        "--require-degraded",
        action="store_true",
        help="Đợi ít nhất 1 alert với degraded=true",
    )
    args = parser.parse_args()

    topic = TOPICS["decision_alerts"]
    got: list[DecisionAlert] = []
    errors: list[str] = []

    def on_message(_client, _userdata, msg):
        try:
            alert = DecisionAlert.from_json(msg.payload)
            got.append(alert)
            print(
                f"OK trace_id={alert.trace_id} severity={alert.severity} "
                f"degraded={alert.degraded} e2e_ms={alert.e2e_latency_ms} "
                f"action={alert.action}"
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            print(f"FAIL parse: {exc}", file=sys.stderr)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        client_id="verify_decision",
        protocol=mqtt.MQTTv311,
    )
    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=30)
    client.subscribe(topic, qos=1)
    client.loop_start()
    print(f"Listening on {args.host}:{args.port} topic={topic} (need {args.count})")

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        if len(got) >= args.count:
            if not args.require_degraded or any(a.degraded for a in got):
                break
        time.sleep(0.2)

    client.loop_stop()
    client.disconnect()

    if errors:
        print(f"Parse errors: {len(errors)}", file=sys.stderr)
        return 2
    if len(got) < args.count:
        print(f"Timeout: got {len(got)}/{args.count}", file=sys.stderr)
        return 1
    if args.require_degraded and not any(a.degraded for a in got):
        print("Timeout: no degraded alert observed", file=sys.stderr)
        return 1
    degraded_n = sum(1 for a in got if a.degraded)
    print(f"PASS: received {len(got)} DecisionAlert(s) (degraded={degraded_n})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
