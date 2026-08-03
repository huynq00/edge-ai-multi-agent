"""Dashboard — MQTT subscriber + Flask-SocketIO server for live monitoring.

Chạy standalone:
    python dashboard/app.py
Hoặc trong Docker Compose: service dashboard (port 5000).
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import sys
import threading
import time
from collections import deque
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt

from shared.schemas import TOPICS, AnalysisResult, DecisionAlert, SensorReading

LOG = logging.getLogger("dashboard")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

MAX_HISTORY = 60
_lock = threading.Lock()
_e2e: deque[dict] = deque(maxlen=MAX_HISTORY)
_infer: deque[dict] = deque(maxlen=MAX_HISTORY)
_alerts: deque[dict] = deque(maxlen=30)
_agents: dict[str, dict] = {
    "sensor_agent":   {"status": "unknown", "last_hb": 0.0},
    "analysis_agent": {"status": "unknown", "last_hb": 0.0},
    "decision_agent": {"status": "unknown", "last_hb": 0.0},
}

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))


def _on_message(_client: mqtt.Client, _userdata: None, msg: mqtt.MQTTMessage) -> None:
    topic = msg.topic
    try:
        if topic == TOPICS["sensor_readings"]:
            r = SensorReading.from_json(msg.payload)
            socketio.emit("sensor", {
                "trace_id": r.trace_id,
                "temperature_c": r.temperature_c,
                "humidity_pct": r.humidity_pct,
                "pm25_ugm3": r.pm25_ugm3,
                "co2_ppm": r.co2_ppm,
                "ts": r.ts,
            })

        elif topic == TOPICS["analysis_results"]:
            res = AnalysisResult.from_json(msg.payload)
            point = {"ts": res.ts, "ms": res.inference_ms, "label": res.label}
            with _lock:
                _infer.append(point)
            socketio.emit("analysis", point)

        elif topic == TOPICS["decision_alerts"]:
            alert = DecisionAlert.from_json(msg.payload)
            point = {
                "ts": alert.ts,
                "trace_id": alert.trace_id,
                "severity": alert.severity,
                "action": alert.action,
                "reason": alert.reason,
                "degraded": alert.degraded,
                "e2e_ms": alert.e2e_latency_ms,
            }
            with _lock:
                _alerts.appendleft(point)
                if alert.e2e_latency_ms is not None:
                    _e2e.append({"ts": alert.ts, "ms": alert.e2e_latency_ms})
            socketio.emit("alert", point)

        elif topic == TOPICS["heartbeat"]:
            hb = json.loads(msg.payload)
            agent_id = hb.get("agent_id", "")
            status = hb.get("status", "alive")
            with _lock:
                if agent_id in _agents:
                    _agents[agent_id] = {"status": status, "last_hb": time.time()}
            socketio.emit("heartbeat", {"agent_id": agent_id, "status": status})

    except Exception:  # noqa: BLE001 — malformed không crash server
        pass


def _mqtt_thread() -> None:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="dashboard",
        protocol=mqtt.MQTTv311,
    )

    def on_connect(c: mqtt.Client, _u: None, _f, rc, _props=None) -> None:
        if rc.is_failure:
            LOG.error("MQTT connect failed: %s", rc)
            return
        LOG.info("MQTT connected %s:%s", MQTT_HOST, MQTT_PORT)
        for t in TOPICS.values():
            c.subscribe(t, qos=1)

    def on_disconnect(_c: mqtt.Client, _u: None, _f=None, rc=None, _props=None) -> None:
        LOG.warning("MQTT disconnected: %s — will reconnect", rc)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = _on_message

    # retry loop: dashboard stays alive even when broker is not yet up
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_forever(retry_first_connection=True)
        except Exception as exc:
            LOG.warning("MQTT unavailable (%s) — retry in 5s", exc)
            time.sleep(5)


@app.route("/")
def index() -> str:
    with _lock:
        init_data = json.dumps({
            "agents": _agents,
            "e2e": list(_e2e),
            "infer": list(_infer),
            "alerts": list(_alerts),
        })
    return render_template("index.html", init_data=init_data)


@app.route("/api/status")
def api_status():
    with _lock:
        return jsonify({
            "agents": _agents,
            "e2e": list(_e2e),
            "infer": list(_infer),
            "alerts": list(_alerts),
        })


if __name__ == "__main__":
    threading.Thread(target=_mqtt_thread, daemon=True).start()
    port = int(os.environ.get("DASHBOARD_PORT", 5000))
    LOG.info("Dashboard starting on http://0.0.0.0:%s", port)
    socketio.run(app, host="0.0.0.0", port=port)
