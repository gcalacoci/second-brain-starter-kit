#!/usr/bin/env bash
# Second Brain — Dream Sequencer
# Installed by setup.sh. Runs the Dream Sequence unattended on a cron schedule.
# Logs: {{KB_DIR}}/.overmind/logs/dream-YYYY-MM-DD.log
#
# Manual test (no mutation):  {{KB_DIR}}/.overmind/dream-cron.sh --dry-run
set -uo pipefail

KB_DIR="{{KB_DIR}}"
LOG_DIR="$KB_DIR/.overmind/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/dream-$(date +%F).log"

# PATH captured at install time — cron provides a minimal environment
export PATH="{{AGENT_PATH}}"

# --- Overlap guard (portable; flock is missing on macOS) ---
LOCKDIR="$LOG_DIR/.dream.lockdir"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "$(date -Is) skipped: previous dream still running" >> "$LOG"
  exit 0
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT

# --- Dry run support (test wiring without mutating the brain) ---
if [[ "${1:-}" == "--dry-run" ]]; then
  echo "DRY RUN OK"
  echo "  KB:      $KB_DIR"
  echo "  Agent:   {{AGENT_NAME}} ({{AGENT_BIN}})"
  echo "  Log:     $LOG"
  exit 0
fi

PROMPT='Run the Second Brain Dream Sequence now. Load the kb-dream skill at '"$KB_DIR"'/skills/kb-dream/SKILL.md and read '"$KB_DIR"'/SCHEMA.md first. Then execute the full flow: process new files in inbox/ (ingest flow), lint for contradictions, orphan pages, stale claims, and missing pages, update wiki/index.md, append to wiki/log.md, and update last-run in .overmind/config.yaml. Commit locally with message "dream: scheduled run". NEVER run git push. If the brain is empty or nothing is new, still log the run.'

{
  echo "=== dream start $(date -Is) via {{AGENT_NAME}} ==="
  if [[ "{{AGENT_NAME}}" == "opencode" ]]; then
    "{{AGENT_BIN}}" run "$PROMPT"
  else
    # Headless Claude. NOTE: --dangerously-skip-permissions grants broad autonomy
    # for this unattended run. Scope it down via settings.json permissions allowlist
    # if you prefer (see MANUAL.md troubleshooting).
    "{{AGENT_BIN}}" -p "$PROMPT" --dangerously-skip-permissions
  fi
  rc=$?
  echo "=== dream end rc=$rc $(date -Is) ==="
  echo "--- last log entries ---"
  grep "^## \[" "$KB_DIR/wiki/log.md" 2>/dev/null | tail -5
} >> "$LOG" 2>&1

exit 0
