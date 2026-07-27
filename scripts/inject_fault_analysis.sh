#!/usr/bin/env bash
# Inject fault: dừng analysis agent process để demo timeout / degraded.
# Usage:
#   ./scripts/inject_fault_analysis.sh           # pkill analysis process
#   ./scripts/inject_fault_analysis.sh docker    # docker compose stop analysis_agent
set -euo pipefail
MODE="${1:-process}"
if [[ "$MODE" == "docker" ]]; then
  SERVICE="${2:-analysis_agent}"
  echo "[fault] Stopping docker service ${SERVICE} ..."
  docker compose stop "${SERVICE}" 2>/dev/null || docker stop "${SERVICE}"
else
  echo "[fault] Stopping local analysis_agent process ..."
  if pgrep -f "agents.analysis_agent.main" >/dev/null 2>&1; then
    pkill -TERM -f "agents.analysis_agent.main" || true
    sleep 1
    pkill -KILL -f "agents.analysis_agent.main" 2>/dev/null || true
    echo "[fault] analysis_agent process killed."
  else
    echo "[fault] no analysis_agent process found."
  fi
fi
echo "[fault] Observe decision_agent degraded alerts (timeout ${ANALYSIS_TIMEOUT:-5}s)."
