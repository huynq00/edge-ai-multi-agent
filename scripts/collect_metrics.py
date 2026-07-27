#!/usr/bin/env python3
"""Thu thập metrics E2E + docker stats trong một cửa sổ đo (cho báo cáo).

Usage:
  python scripts/collect_metrics.py --duration 45 --out reports/metrics_run.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import paho.mqtt.client as mqtt

from shared.schemas import TOPICS, AnalysisResult, DecisionAlert, SensorReading


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    idx = min(len(sorted_vals) - 1, int(len(sorted_vals) * p))
    return round(sorted_vals[idx], 3)


def docker_stats_sample() -> dict[str, dict]:
    cmd = [
        "docker",
        "stats",
        "--no-stream",
        "--format",
        "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}",
        "sensor_agent",
        "analysis_agent",
        "decision_agent",
        "mqtt-broker",
    ]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}
    result: dict[str, dict] = {}
    for line in out.strip().splitlines():
        parts = line.split("|")
        if len(parts) < 4:
            continue
        name, cpu, mem, mem_pct = parts[0], parts[1], parts[2], parts[3]
        # MemUsage like "51.76MiB / 4GiB"
        peak_part = mem.split("/")[0].strip()
        result[name] = {
            "cpu_perc": cpu.strip(),
            "mem_usage": mem.strip(),
            "mem_limit_side": peak_part,
            "mem_perc": mem_pct.strip(),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--duration", type=float, default=45.0)
    parser.add_argument("--out", default="reports/metrics_run.json")
    args = parser.parse_args()

    e2e: list[float] = []
    infer: list[float] = []
    alerts = 0
    degraded = 0
    readings = 0
    results = 0
    lock = threading.Lock()
    docker_samples: list[dict] = []

    def on_message(_c, _u, msg):
        nonlocal alerts, degraded, readings, results
        topic = msg.topic
        try:
            if topic == TOPICS["decision_alerts"]:
                alert = DecisionAlert.from_json(msg.payload)
                with lock:
                    alerts += 1
                    if alert.degraded:
                        degraded += 1
                    if alert.e2e_latency_ms is not None:
                        e2e.append(float(alert.e2e_latency_ms))
            elif topic == TOPICS["analysis_results"]:
                result = AnalysisResult.from_json(msg.payload)
                with lock:
                    results += 1
                    infer.append(float(result.inference_ms))
            elif topic == TOPICS["sensor_readings"]:
                SensorReading.from_json(msg.payload)
                with lock:
                    readings += 1
        except Exception as exc:  # noqa: BLE001
            print(f"parse skip: {exc}", file=sys.stderr)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        client_id="collect_metrics",
        protocol=mqtt.MQTTv311,
    )
    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=60)
    for t in (
        TOPICS["decision_alerts"],
        TOPICS["analysis_results"],
        TOPICS["sensor_readings"],
    ):
        client.subscribe(t, qos=1)
    client.loop_start()

    print(f"Collecting for {args.duration}s on {args.host}:{args.port} ...")
    t_end = time.time() + args.duration
    while time.time() < t_end:
        docker_samples.append({"ts": time.time(), "stats": docker_stats_sample()})
        time.sleep(5)

    client.loop_stop()
    client.disconnect()

    e2e_sorted = sorted(e2e)
    infer_sorted = sorted(infer)
    wall = args.duration

    summary = {
        "duration_sec": args.duration,
        "counts": {
            "sensor_readings": readings,
            "analysis_results": results,
            "decision_alerts": alerts,
            "degraded_alerts": degraded,
        },
        "throughput": {
            "sensor_msg_per_sec": round(readings / wall, 3),
            "analysis_msg_per_sec": round(results / wall, 3),
            "decision_msg_per_sec": round(alerts / wall, 3),
        },
        "e2e_latency_ms": {
            "n": len(e2e_sorted),
            "p50": _percentile(e2e_sorted, 0.50) if e2e_sorted else None,
            "p95": _percentile(e2e_sorted, 0.95) if e2e_sorted else None,
            "mean": round(statistics.mean(e2e_sorted), 3) if e2e_sorted else None,
            "max": round(max(e2e_sorted), 3) if e2e_sorted else None,
        },
        "analysis_inference_ms": {
            "n": len(infer_sorted),
            "p50": _percentile(infer_sorted, 0.50) if infer_sorted else None,
            "p95": _percentile(infer_sorted, 0.95) if infer_sorted else None,
            "mean": round(statistics.mean(infer_sorted), 3) if infer_sorted else None,
        },
        "docker_stats_last": docker_samples[-1]["stats"] if docker_samples else {},
        "docker_stats_samples": len(docker_samples),
        "resource_limits": {"vcpu": 2, "ram_gb": 4, "gpu": False},
        "model": {
            "name": "IsolationForest + StandardScaler",
            "format": "ONNX",
            "path": "models/anomaly.onnx",
            "runtime": "onnxruntime CPU",
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {out}")
    return 0 if alerts > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
