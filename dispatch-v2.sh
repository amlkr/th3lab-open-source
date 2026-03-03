#!/bin/bash
# dispatch-v2.sh — Dispatch con output a shared memory
# Usage: dispatch-v2.sh <agent-id> <task-name> <task>
#
# Runs the agent, saves output to:
#   agent-output/<agent>/latest.md
#   agent-output/<agent>/<timestamp>-<task-name>.md

AGENT="$1"
TASK_NAME="$2"
TASK="$3"

if [ -z "$AGENT" ] || [ -z "$TASK_NAME" ] || [ -z "$TASK" ]; then
    echo "Usage: dispatch-v2.sh <agent-id> <task-name> <task>"
    echo "Example: dispatch-v2.sh director brief 'visual identity for Bangkok brand'"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTPUT_DIR="$HOME/Documents/amlkr-dashboard/agent-output/$AGENT"
LATEST_FILE="$OUTPUT_DIR/latest.md"
ARCHIVE_FILE="$OUTPUT_DIR/${TIMESTAMP}-${TASK_NAME}.md"

mkdir -p "$OUTPUT_DIR"

echo "⚡ Dispatching to $AGENT [$TASK_NAME]..."
echo "   Task: $TASK"
echo ""

# Run agent, capture output (JSON mode, no direct delivery)
RAW=$(openclaw agent --agent "$AGENT" --message "$TASK" --json 2>&1)

# Extract text content from JSON if possible, fall back to raw
CONTENT=$(echo "$RAW" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # Try common OpenClaw JSON output fields
    for key in ['text', 'content', 'message', 'response', 'result']:
        if key in data and data[key]:
            print(data[key])
            sys.exit(0)
    # If it's a list, get last item's text
    if isinstance(data, list) and data:
        last = data[-1]
        for key in ['text', 'content', 'message']:
            if key in last and last[key]:
                print(last[key])
                sys.exit(0)
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception:
    print(sys.stdin.read() if not sys.stdin.closed else '')
" 2>/dev/null || echo "$RAW")

# Build the output file
OUTPUT_HEADER="# $AGENT — $TASK_NAME
**Fecha:** $(date '+%Y-%m-%d %H:%M')
**Tarea:** $TASK

---

"

# Write to latest and archive
printf '%s%s' "$OUTPUT_HEADER" "$CONTENT" > "$LATEST_FILE"
cp "$LATEST_FILE" "$ARCHIVE_FILE"

echo "✅ Output guardado:"
echo "   latest → $LATEST_FILE"
echo "   archive → $ARCHIVE_FILE"
echo ""
echo "$CONTENT"
