#!/bin/bash
# Usage: dispatch.sh "agent-id" "task text"
# Routes task to any named agent and delivers response via WhatsApp
AGENT="$1"
TASK="$2"
if [ -z "$AGENT" ] || [ -z "$TASK" ]; then
    echo "Usage: dispatch.sh 'agent-id' 'task text'"
    exit 1
fi
echo "⚡ Dispatching to $AGENT: $TASK"
openclaw agent --agent "$AGENT" --message "$TASK" --deliver --reply-channel whatsapp --reply-to "+61432483747" --json
