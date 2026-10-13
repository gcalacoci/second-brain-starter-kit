#!/bin/bash
# file-backup.sh — PreToolUse hook for file edits in Second Brain

FILE="$1"
BACKUP_DIR="$HOME/.claude/backups/second-brain"
mkdir -p "$BACKUP_DIR"

if [[ "$FILE" == *"/prj/second-brain/"* ]]; then
  TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
  BASENAME=$(basename "$FILE")
  BACKUP_PATH="$BACKUP_DIR/${BASENAME}-${TIMESTAMP}.bak"
  cp "$FILE" "$BACKUP_PATH" 2>/dev/null && echo "📦 Backed up: $FILE -> $BACKUP_PATH"
fi
