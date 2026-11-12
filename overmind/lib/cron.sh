#!/usr/bin/env bash
# Shared cron helpers: lock, PATH, log rotation, status file and failure notice.
# Use: source lib/cron.sh; cron_init NAME "$@". Optional: define cron_cleanup() for temp
# files (the lib owns the EXIT trap); set CRON_NOTIFY_ON_FAIL=0 if the job notifies itself.
# Set CRON_EXTRA_JSON=<file with a JSON object> to add job fields to the status file.
# Environment: CRON_PATH (prepended to PATH; setup puts your login PATH in the crontab line),
# CRON_NOTIFY (an executable that gets one message argument; default .overmind/notify.sh,
# skipped when missing), CRON_LOG_DIR, CRON_STATE_DIR, CRON_KEEP_DAYS (log retention).

_cron_finish() {
    local rc=$? fin secs
    # Restore the caller's stdout/stderr, let tee drain, then write the log tail.
    # A job's own cleanup (temp files) runs first; it cannot change the job's rc.
    declare -F cron_cleanup >/dev/null && { cron_cleanup || true; }
    exec 1>&3 2>&4 3>&- 4>&-
    [ -n "${_CRON_TEE_PID:-}" ] && wait "$_CRON_TEE_PID" 2>/dev/null
    fin=$(date -Iseconds)
    secs=$SECONDS
    printf '=== %s end rc=%s %s ===\n' "$CRON_NAME" "$rc" "$fin" >>"$CRON_LOG"
    python3 -I - "$CRON_STATE_DIR" "$CRON_NAME" "$rc" "$_CRON_STARTED" "$fin" "$secs" \
        "$(basename "$CRON_LOG")" "${CRON_EXTRA_JSON:-}" <<'PY'
import json, os, sys
d, n, rc, started, finished, secs, log, extra = sys.argv[1:9]
s = {"name": n, "rc": int(rc), "started": started,
     "finished": finished, "seconds": int(secs), "log": log}
try:  # CRON_EXTRA_JSON: job-specific fields (e.g. restic last_snapshot); never override the above
    with open(extra) as fh:
        s = {**json.load(fh), **s}
except (OSError, ValueError, TypeError):
    pass
with open(os.path.join(d, n + ".json"), "w") as fh:
    json.dump(s, fh)
PY
    [ "$_CRON_LOCKED" = 1 ] && rmdir "$CRON_LOG_DIR/.$CRON_NAME.lockdir" 2>/dev/null
    # CRON_NOTIFY_ON_FAIL=0: the job sends its own failure notice (no duplicate).
    if [ "$rc" -ne 0 ] && [ "$CRON_DRY_RUN" != 1 ] && [ "${CRON_NOTIFY_ON_FAIL:-1}" != 0 ] \
        && [ -x "$CRON_NOTIFY" ]; then
        "$CRON_NOTIFY" "$CRON_NAME FAILED rc=$rc, log $(basename "$CRON_LOG")" || true
    fi
    exit "$rc"
}

# Optional long-lived token for headless `claude -p` (`claude setup-token`, ~1 year): the
# interactive login expires every few weeks and every cron that calls claude then fails.
# Keep the file mode 600; its content is never printed. No file: the login is used.
# NOT called by cron_init: a setup-token login loads no claude.ai connectors (Gmail,
# Calendar...), so call it only in a job that needs none.
cron_claude_token() {
    local f=${CRON_CLAUDE_TOKEN_FILE:-$HOME/.config/claude-cron/oauth-token} tok
    [ -r "$f" ] || return 0
    tok=$(tr -d '[:space:]' <"$f")
    [ -n "$tok" ] && export CLAUDE_CODE_OAUTH_TOKEN=$tok
    return 0
}

cron_init() {
    local name=$1 arg src node
    shift
    CRON_NAME=$name
    KB_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
    CRON_LOG_DIR=${CRON_LOG_DIR:-$KB_DIR/.overmind/logs}
    CRON_STATE_DIR=${CRON_STATE_DIR:-$HOME/.local/state/cron-status}
    CRON_NOTIFY=${CRON_NOTIFY:-$KB_DIR/.overmind/notify.sh}
    CRON_KEEP_DAYS=${CRON_KEEP_DAYS:-30}
    mkdir -p "$CRON_LOG_DIR" "$CRON_STATE_DIR"
    CRON_DRY_RUN=0
    for arg in "$@"; do
        [ "$arg" = "--dry-run" ] && CRON_DRY_RUN=1
    done
    export CRON_NAME CRON_DRY_RUN
    CRON_LOG=$CRON_LOG_DIR/$CRON_NAME-$(date +%F).log
    export CRON_LOG
    node=$(ls -d "$HOME"/.nvm/versions/node/*/bin 2>/dev/null | sort -V | tail -1)
    PATH="${CRON_PATH:+$CRON_PATH:}${node:+$node:}$HOME/.local/bin:$HOME/.opencode/bin:/usr/local/bin:/usr/bin:/bin"
    export PATH
    find "$CRON_LOG_DIR" -maxdepth 1 -name "$CRON_NAME-*.log" \
        -mtime +"$CRON_KEEP_DAYS" -delete 2>/dev/null
    _CRON_LOCKED=0
    if mkdir "$CRON_LOG_DIR/.$CRON_NAME.lockdir" 2>/dev/null; then
        _CRON_LOCKED=1
    else
        printf '%s skipped: previous %s still running\n' "$(date -Iseconds)" \
            "$CRON_NAME" >>"$CRON_LOG"
        exit 0
    fi
    _CRON_STARTED=$(date -Iseconds)
    _CRON_TEE_PID=
    exec 3>&1 4>&2
    if [ "$CRON_DRY_RUN" = 1 ]; then
        exec > >(tee -a "$CRON_LOG") 2>&1
        _CRON_TEE_PID=$!
    else
        exec >>"$CRON_LOG" 2>&1
    fi
    printf '=== %s start %s ===\n' "$CRON_NAME" "$_CRON_STARTED" >>"$CRON_LOG"
    SECONDS=0
    trap _cron_finish EXIT
}

cron_status() {
    local dir=${CRON_STATE_DIR:-$HOME/.local/state/cron-status}
    [ -d "$dir" ] || return 0
    python3 -I - "$dir" <<'PY'
import glob, json, os, sys
rows = []
for path in glob.glob(os.path.join(sys.argv[1], "*.json")):
    try:
        with open(path) as fh:
            s = json.load(fh)
    except (OSError, ValueError):
        continue
    rc = int(s.get("rc", 0))
    rows.append((s.get("name", os.path.basename(path)[:-5]),
                 "ok" if rc == 0 else "FAILED rc=%d" % rc,
                 s.get("finished", "?"), s.get("seconds", 0)))
for name, state, finished, secs in sorted(rows):
    print("%s  %s  %s  %ss" % (name, state, finished, secs))
PY
}
