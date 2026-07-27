#!/usr/bin/env bash
# Build + chạy toàn bộ stack (broker + 3 agent, mỗi agent 2c/4GB).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
docker compose build
docker compose up -d
docker compose ps
echo
echo "Verify from host:"
echo "  source .venv/bin/activate && python scripts/verify_decision_mqtt.py --count 3"
echo "Fault injection:"
echo "  ./scripts/inject_fault_analysis.sh docker"
