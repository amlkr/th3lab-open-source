#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

LOG_DIR="/tmp/th3lab"
PID_FILE="$LOG_DIR/pids.env"
mkdir -p "$LOG_DIR"

DASHBOARD_PORT="${TH3LAB_DASHBOARD_PORT:-5173}"
CHAT_PORT="${TH3LAB_CHAT_PORT:-3001}"
BACKEND_PORT="${TH3LAB_BACKEND_PORT:-8000}"
MCP_PORT="${TH3LAB_MCP_PORT:-8090}"
WITH_NGROK="${1:-}"

command -v lsof >/dev/null || { echo "lsof is required"; exit 1; }
command -v curl >/dev/null || { echo "curl is required"; exit 1; }

is_listening() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

wait_http() {
  local url="$1"
  local tries="${2:-60}"
  for ((i=1; i<=tries; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_bg() {
  local name="$1"
  local cmd="$2"
  local log="$LOG_DIR/${name}.log"
  nohup bash -lc "$cmd" >"$log" 2>&1 &
  local pid=$!
  echo "${name}_PID=$pid" >> "$PID_FILE"
  echo "[$name] pid=$pid log=$log"
}

# reset pid file each run
: > "$PID_FILE"

echo "[th3lab] Starting data services (postgres + redis)..."
docker compose up -d postgres redis >/dev/null

echo "[th3lab] Ensuring backend on :$BACKEND_PORT..."
if ! wait_http "http://127.0.0.1:${BACKEND_PORT}/health" 2; then
  if is_listening "$BACKEND_PORT"; then
    echo "Port $BACKEND_PORT is busy but /health fails. Abort."
    exit 1
  fi
  start_bg "backend" "cd '$ROOT_DIR' && source backend/venv/bin/activate && uvicorn main:app --app-dir backend --host 0.0.0.0 --port $BACKEND_PORT"
fi

wait_http "http://127.0.0.1:${BACKEND_PORT}/health" 90 || {
  echo "Backend did not start. See $LOG_DIR/backend.log"
  exit 1
}

echo "[th3lab] Ensuring MCP on :$MCP_PORT..."
if ! wait_http "http://127.0.0.1:${MCP_PORT}/health" 2; then
  if is_listening "$MCP_PORT"; then
    echo "Port $MCP_PORT is busy but MCP /health fails. Abort."
    exit 1
  fi
  start_bg "mcp" "cd '$ROOT_DIR' && source backend/venv/bin/activate && uvicorn th3lab_mcp:app --app-dir infra/mcp --host 0.0.0.0 --port $MCP_PORT"
fi

wait_http "http://127.0.0.1:${MCP_PORT}/health" 90 || {
  echo "MCP did not start. See $LOG_DIR/mcp.log"
  exit 1
}

# write local env for chat bridge
mkdir -p "$ROOT_DIR/th3lab-superinterface"
cat > "$ROOT_DIR/th3lab-superinterface/.env.local" <<EOL
TH3LAB_ASK_URL=http://127.0.0.1:${MCP_PORT}/mcp/world/ask
TH3LAB_WORLD_ID=amniotic
TH3LAB_PROJECT_ID=_admin
BASIC_AUTH_USER=amlkr
BASIC_AUTH_PASS=7777777@@
EOL

echo "[th3lab] Ensuring dashboard on :$DASHBOARD_PORT..."
if ! wait_http "http://127.0.0.1:${DASHBOARD_PORT}" 2; then
  if ! [ -d "$ROOT_DIR/frontend/node_modules" ]; then
    echo "[th3lab] Installing dashboard deps..."
    npm --prefix "$ROOT_DIR/frontend" install >/dev/null
  fi
  start_bg "dashboard" "cd '$ROOT_DIR/frontend' && npm run dev -- --host 0.0.0.0 --port $DASHBOARD_PORT"
fi

wait_http "http://127.0.0.1:${DASHBOARD_PORT}" 120 || {
  echo "Dashboard did not start. See $LOG_DIR/dashboard.log"
  exit 1
}

echo "[th3lab] Ensuring chat on :$CHAT_PORT..."
if ! wait_http "http://127.0.0.1:${CHAT_PORT}/login" 2; then
  if ! [ -d "$ROOT_DIR/th3lab-superinterface/node_modules" ]; then
    echo "[th3lab] Installing chat deps..."
    npm --prefix "$ROOT_DIR/th3lab-superinterface" install >/dev/null
  fi
  start_bg "chat" "cd '$ROOT_DIR/th3lab-superinterface' && npm run dev -- -H 0.0.0.0 -p $CHAT_PORT"
fi

wait_http "http://127.0.0.1:${CHAT_PORT}/login" 120 || {
  echo "Chat did not start. See $LOG_DIR/chat.log"
  exit 1
}

if [[ "$WITH_NGROK" == "--with-ngrok" ]]; then
  echo "[th3lab] Starting ngrok for MCP..."
  pkill -f "ngrok http" >/dev/null 2>&1 || true
  start_bg "ngrok" "ngrok http http://127.0.0.1:${MCP_PORT}"
  sleep 3
  NGROK_URL=$(curl -sS http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[]?.public_url' 2>/dev/null | grep '^https://' | head -n 1 || true)
  if [[ -n "$NGROK_URL" ]]; then
    echo "[th3lab] ngrok URL: $NGROK_URL"
    echo "[th3lab] Set Vercel TH3LAB_ASK_URL=${NGROK_URL}/mcp/world/ask"
  else
    echo "[th3lab] ngrok running but public URL not found yet (check http://127.0.0.1:4040)."
  fi
fi

echo "[th3lab] End-to-end probe (chat -> MCP)..."
RESP=$(curl -sS -X POST "http://127.0.0.1:${CHAT_PORT}/api/th3lab" -H 'Content-Type: application/json' -d '{"message":"ping"}' || true)
if echo "$RESP" | rg -q 'reply'; then
  echo "[th3lab] OK: chat bridge reached MCP"
else
  echo "[th3lab] Warning: bridge response: $RESP"
fi

echo ""
echo "TH3LAB is up:"
echo "- Backend:   http://127.0.0.1:${BACKEND_PORT}/health"
echo "- MCP:       http://127.0.0.1:${MCP_PORT}/health"
echo "- Dashboard: http://127.0.0.1:${DASHBOARD_PORT}"
echo "- Chat:      http://127.0.0.1:${CHAT_PORT}"
echo "- Stop all:  ./th3lab-stop.sh"
