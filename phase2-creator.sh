#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/infra/swarm/.env"
PHASE2_STACK="$ROOT_DIR/infra/swarm/docker-compose.phase2.yml"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT_DIR/infra/swarm/.env.example" "$ENV_FILE"
  echo "Creado $ENV_FILE desde .env.example"
fi

echo "[phase2] Starting data services (postgres + redis)..."
docker compose up -d postgres redis

echo "[phase2] Starting n8n..."
docker compose -f "$PHASE2_STACK" --env-file "$ENV_FILE" up -d n8n

echo "[phase2] Ensuring backend on :8000..."
if ! curl -fsS http://localhost:8000/health >/dev/null; then
  if lsof -i :8000 -n -P >/dev/null 2>&1; then
    echo "Puerto 8000 ocupado, pero backend no responde /health."
    echo "Revisa proceso activo en :8000 antes de continuar."
    exit 1
  fi
  nohup bash -lc "source backend/venv/bin/activate && uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000" >/tmp/th3lab-backend.log 2>&1 &
fi

until curl -fsS http://localhost:8000/health >/dev/null; do
  sleep 2
done

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

echo "[phase2] Waiting n8n..."
until curl -fsS http://localhost:5678/healthz >/dev/null 2>&1; do
  sleep 2
done

echo "[phase2] OK"
echo " - Backend: http://localhost:8000/health"
echo " - MCP:     http://localhost:8090/health"
echo " - n8n:     http://localhost:5678"
echo " - Worlds:  ./think.sh worlds"
echo " - Ingesta: ./think.sh ingest amniotic <archivo_o_carpeta>"
