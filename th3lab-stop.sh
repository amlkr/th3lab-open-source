#!/bin/bash
set -euo pipefail

LOG_DIR="/tmp/th3lab"
PID_FILE="$LOG_DIR/pids.env"

if [[ -f "$PID_FILE" ]]; then
  echo "[th3lab] Stopping managed processes..."
  tac "$PID_FILE" | while IFS='=' read -r key pid; do
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
      echo "- stopped $key ($pid)"
    fi
  done
  rm -f "$PID_FILE"
fi

pkill -f "ngrok http" >/dev/null 2>&1 || true

echo "[th3lab] Done."
