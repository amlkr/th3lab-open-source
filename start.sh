#!/bin/bash

# amlkr-dashboard startup script
# Launches all services in separate Terminal tabs

DASHBOARD_DIR="$HOME/Documents/amlkr-dashboard"

# ─── 1. Start Docker Desktop if not running ───────────────────────────────────
if ! pgrep -x "Docker" > /dev/null; then
  echo "Starting Docker Desktop..."
  open /Applications/Docker.app
  echo "Waiting for Docker daemon..."
  until docker info > /dev/null 2>&1; do
    sleep 2
  done
  echo "Docker is ready."
else
  echo "Docker Desktop already running."
fi

# ─── 2. Start Ollama if not running ───────────────────────────────────────────
if ! pgrep -x "ollama" > /dev/null; then
  echo "Starting Ollama..."
  brew services start ollama
  sleep 3
else
  echo "Ollama already running."
fi

# ─── 3. Start Postgres + Redis ────────────────────────────────────────────────
echo "Starting postgres and redis..."
cd "$DASHBOARD_DIR" && docker compose up -d postgres redis
echo "Postgres and Redis started."

# ─── Helper: open a new Terminal tab and run a command ────────────────────────
open_tab() {
  local tab_title="$1"
  local tab_cmd="$2"
  osascript <<EOF
tell application "Terminal"
  activate
  tell application "System Events" to keystroke "t" using {command down}
  delay 0.5
  do script "printf '\\\\e]0;${tab_title}\\\\a'; ${tab_cmd}" in front window
end tell
EOF
}

# ─── 4. FastAPI backend ───────────────────────────────────────────────────────
open_tab "FastAPI" \
  "cd $DASHBOARD_DIR/backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

sleep 1

# ─── 5. Celery worker ─────────────────────────────────────────────────────────
open_tab "Celery" \
  "cd $DASHBOARD_DIR/backend && source venv/bin/activate && celery -A core.celery_app worker --loglevel=info"

sleep 1

# ─── 6. Frontend (Vite) ───────────────────────────────────────────────────────
open_tab "Frontend" \
  "cd $DASHBOARD_DIR/frontend && npm run dev"

sleep 1

# ─── 7. OpenClaw gateway ──────────────────────────────────────────────────────
open_tab "OpenClaw" \
  "cd $DASHBOARD_DIR && env -u CLAUDECODE OLLAMA_API_KEY='ollama-local' openclaw gateway"

sleep 1

# ─── 8. ngrok tunnel ──────────────────────────────────────────────────────────
open_tab "ngrok" \
  "ngrok http 5173"

# ─── 9. Open browser ──────────────────────────────────────────────────────────
echo "Waiting for frontend to be ready..."
until curl -s http://localhost:5173 > /dev/null 2>&1; do
  sleep 2
done
open http://localhost:5173

echo "All services started."
echo "ngrok dashboard: http://localhost:4040"
