#!/usr/bin/env bash
# Chạy Analysis Agent local (cần models/anomaly.onnx).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export MQTT_HOST="${MQTT_HOST:-localhost}"
export MQTT_PORT="${MQTT_PORT:-1883}"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
PY="${ROOT}/.venv/bin/python3"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi
if [[ ! -f models/anomaly.onnx ]]; then
  echo "[analysis] models/anomaly.onnx missing — training..."
  "$PY" scripts/train_anomaly_model.py
fi
exec "$PY" -m agents.analysis_agent.main "$@"
