#!/usr/bin/env bash
# Khởi động Mosquitto MQTT broker (Docker).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
docker compose up -d mqtt-broker
echo "[broker] Mosquitto listening on localhost:1883"
docker compose ps mqtt-broker
