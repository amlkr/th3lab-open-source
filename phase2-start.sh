#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
STACK_FILE="$ROOT_DIR/infra/swarm/docker-compose.phase2.yml"
ENV_FILE="$ROOT_DIR/infra/swarm/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT_DIR/infra/swarm/.env.example" "$ENV_FILE"
  echo "Creado $ENV_FILE desde .env.example"
fi

docker compose -f "$STACK_FILE" --env-file "$ENV_FILE" up -d --build

echo "Esperando backend..."
until curl -fsS http://localhost:8000/health >/dev/null; do
  sleep 2
done

echo "Esperando MCP..."
until curl -fsS http://localhost:8090/health >/dev/null; do
  sleep 2
done

echo "Phase 2 arriba."
echo "- Backend: http://localhost:8000/health"
echo "- MCP:     http://localhost:8090/health"
echo "- Worlds:  ./think.sh worlds"
