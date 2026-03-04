#!/bin/bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

usage() {
  cat <<'EOF'
think.sh — flujo no-code para conciencia estilistica (th3lab)

Uso:
  ./think.sh map
  ./think.sh worlds
  ./think.sh ingest <world_id> <file_o_directorio>
  ./think.sh docs <world_id>
  ./think.sh ask <world_id> "<pregunta>" [project_id]
  ./think.sh agent "<mensaje>"

World IDs:
  amniotic | cine_lentitud | cuerpo_politico
EOF
}

require_backend() {
  if ! curl -fsS "$BASE_URL/health" >/dev/null; then
    echo "Backend no disponible en $BASE_URL"
    echo "Levanta backend primero (localhost:8000)."
    exit 1
  fi
}

json_post() {
  local endpoint="$1"
  local json="$2"
  curl -fsS -X POST "$BASE_URL$endpoint" \
    -H "Content-Type: application/json" \
    -d "$json"
}

map_agents() {
  openclaw config get agents.list | python3 -c '
import json,sys
agents=json.load(sys.stdin)
print("Mapa de agentes:")
for a in agents:
    print("- {id:<12} model={model} workspace={ws}".format(
        id=a.get("id","?"),
        model=a.get("model","?"),
        ws=(a.get("workspace") or a.get("agentDir"))
    ))
'
}

list_worlds() {
  require_backend
  curl -fsS "$BASE_URL/api/library/worlds" | python3 -m json.tool
}

ingest_one() {
  local world_id="$1"
  local file_path="$2"
  echo "Ingestando: $file_path"
  curl -fsS -X POST "$BASE_URL/api/library/worlds/$world_id/ingest" \
    -F "file=@$file_path" \
    -F "project_id=_admin" | python3 -m json.tool
}

ingest_world() {
  local world_id="$1"
  local source_path="$2"
  require_backend

  if [[ ! -e "$source_path" ]]; then
    echo "No existe: $source_path"
    exit 1
  fi

  if [[ -f "$source_path" ]]; then
    ingest_one "$world_id" "$source_path"
    return
  fi

  local found=0
  while IFS= read -r -d '' f; do
    found=1
    ingest_one "$world_id" "$f"
  done < <(find "$source_path" -type f \( -iname "*.pdf" -o -iname "*.epub" -o -iname "*.txt" -o -iname "*.md" -o -iname "*.docx" \) -print0)

  if [[ "$found" -eq 0 ]]; then
    echo "No encontré archivos compatibles en: $source_path"
    exit 1
  fi
}

world_docs() {
  local world_id="$1"
  require_backend
  curl -fsS "$BASE_URL/api/library/worlds/$world_id/documents" | python3 -m json.tool
}

ask_world() {
  local world_id="$1"
  local question="$2"
  local project_id="${3:-}"
  require_backend

  local payload
  if [[ -n "$project_id" ]]; then
    payload=$(python3 - "$question" "$world_id" "$project_id" <<'PY'
import json
import sys
print(json.dumps({
  "message": sys.argv[1],
  "history": [],
  "world_id": sys.argv[2],
  "project_id": sys.argv[3]
}))
PY
)
  else
    payload=$(python3 - "$question" "$world_id" <<'PY'
import json
import sys
print(json.dumps({
  "message": sys.argv[1],
  "history": [],
  "world_id": sys.argv[2]
}))
PY
)
  fi

  json_post "/api/chat/" "$payload" | python3 -m json.tool
}

agent_teoria() {
  local msg="$1"
  openclaw agent --agent teoria --session-id "teoria-$(date +%s)" --timeout 180 --message "$msg" --json
}

cmd="${1:-}"
case "$cmd" in
  map)
    map_agents
    ;;
  worlds)
    list_worlds
    ;;
  ingest)
    [[ $# -lt 3 ]] && usage && exit 1
    ingest_world "$2" "$3"
    ;;
  docs)
    [[ $# -lt 2 ]] && usage && exit 1
    world_docs "$2"
    ;;
  ask)
    [[ $# -lt 3 ]] && usage && exit 1
    ask_world "$2" "$3" "${4:-}"
    ;;
  agent)
    [[ $# -lt 2 ]] && usage && exit 1
    agent_teoria "$2"
    ;;
  *)
    usage
    exit 1
    ;;
esac
