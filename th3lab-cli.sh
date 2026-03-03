#!/bin/bash
# th3lab-cli.sh — API client for th3lab backend
# Usage: th3lab-cli.sh <command> [args]
#
# Commands:
#   status              — health check
#   login               — get fresh JWT token
#   projects            — list all projects
#   project <id>        — get project detail
#   jobs                — list analysis jobs
#   job <id>            — get job detail + result
#   users               — list users
#   library             — list library items
#   worlds              — list worlds
#   analyze-video <path> <project_id>  — submit video for analysis
#   analyze-images <project_id> [urls...] — analyze image set
#   report <project_id> — generate semantic report
#   query <text>        — query the RAG library

BASE="http://localhost:8000"
EMAIL="admin@amlkr.com"
PASSWORD="3n4n0m4hn@@"

# ─── Auth ────────────────────────────────────────────────────────────────────
get_token() {
  curl -s -X POST "$BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('token',''))" 2>/dev/null
}

TOKEN=$(get_token)
AUTH="-H \"Authorization: Bearer $TOKEN\""

api() {
  local method="$1"; local path="$2"; shift 2
  curl -s -X "$method" "$BASE$path" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "$@" | python3 -m json.tool 2>/dev/null
}

# ─── Commands ─────────────────────────────────────────────────────────────────
CMD="$1"
shift

case "$CMD" in
  status)
    curl -s "$BASE/health" | python3 -m json.tool
    ;;
  login)
    echo "Token: $TOKEN"
    ;;
  projects)
    api GET /api/projects/
    ;;
  project)
    api GET "/api/projects/$1"
    ;;
  jobs)
    api GET /api/jobs/
    ;;
  job)
    api GET "/api/jobs/$1"
    ;;
  users)
    api GET /api/users/
    ;;
  library)
    api GET /api/library/
    ;;
  worlds)
    api GET /api/library/worlds
    ;;
  analyze-video)
    FILE="$1"; PROJECT_ID="$2"
    api POST /api/analysis/video -d "{\"file_path\":\"$FILE\",\"project_id\":\"$PROJECT_ID\"}"
    ;;
  analyze-images)
    PROJECT_ID="$1"; shift
    URLS=$(python3 -c "import sys,json; print(json.dumps(sys.argv[1:]))" "$@")
    api POST /api/analysis/images -d "{\"project_id\":\"$PROJECT_ID\",\"image_urls\":$URLS}"
    ;;
  report)
    PROJECT_ID="$1"
    api POST /api/semantic/report -d "{\"project_id\":\"$PROJECT_ID\"}"
    ;;
  query)
    api POST /api/library/query -d "{\"query\":\"$*\",\"n_results\":5}"
    ;;
  *)
    echo "th3lab-cli — comandos disponibles:"
    echo "  status | login | projects | project <id> | jobs | job <id>"
    echo "  users | library | worlds"
    echo "  analyze-video <path> <project_id>"
    echo "  analyze-images <project_id> <url1> <url2>..."
    echo "  report <project_id>"
    echo "  query <texto>"
    ;;
esac
