#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "[phase2] Starting data services (postgres + redis)..."
docker compose up -d postgres redis

echo "[phase2] Checking backend..."
if ! curl -fsS http://localhost:8000/health >/dev/null; then
  echo "Backend no responde en :8000. Levántalo primero (uvicorn) y reintenta."
  exit 1
fi

echo "[phase2] Checking OpenClaw gateway..."
openclaw gateway status >/dev/null || true

echo "[phase2] Starting MCP bridge on :8090..."
if lsof -i :8090 -n -P >/dev/null 2>&1; then
  echo "Puerto 8090 en uso, manteniendo proceso existente."
else
  nohup bash -lc "source backend/venv/bin/activate && uvicorn th3lab_mcp:app --app-dir infra/mcp --host 0.0.0.0 --port 8090" >/tmp/th3lab-mcp.log 2>&1 &
  sleep 2
fi

if ! curl -fsS http://localhost:8090/health >/dev/null; then
  echo "MCP no levantó correctamente. Revisa /tmp/th3lab-mcp.log"
  exit 1
fi

echo "[phase2] OK"
echo " - Backend: http://localhost:8000/health"
echo " - MCP:     http://localhost:8090/health"
echo " - Worlds:  ./think.sh worlds"
echo " - Ingesta: ./think.sh ingest amniotic <archivo_o_carpeta>"
