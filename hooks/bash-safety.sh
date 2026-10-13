#!/bin/bash
# bash-safety.sh — PreToolUse hook to block dangerous git commands

CMD="$1"

if [[ "$CMD" == *git*push* ]] || [[ "$CMD" == *git*push*--force* ]] || [[ "$CMD" == *git*reset*--hard* ]] || [[ "$CMD" == *git*branch*-D* ]]; then
  echo "🚫 Blocked: $CMD — git push / force operations are blocked for Second Brain (local-only repo)"
  exit 1
fi
