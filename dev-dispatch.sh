#!/bin/bash
# Usage: dev-dispatch.sh "task text here"
# Sends task to dev agent and delivers response via WhatsApp
TASK="$1"
if [ -z "$TASK" ]; then
    echo "Usage: dev-dispatch.sh 'task text'"
    exit 1
fi
echo "⚡ Dispatching to dev: $TASK"
openclaw agent --agent dev --message "$TASK" --deliver --reply-channel whatsapp --reply-to "+61432483747" --json
