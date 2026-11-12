"""Unsaved interactive sessions: sessions that did real work and were never saved.

Run by brain-maint.sh (part A); the Dream Sequence lists them in its report so the user
can save (kb-session-capture from the transcript) or dismiss each one. It writes no notes.

Usage:
    python3 -I unsaved_sessions.py [--projects DIR] [--state FILE] [--now ISO]
    python3 -I unsaved_sessions.py [options] list
    python3 -I unsaved_sessions.py [options] dismiss <session_id>

Scans ~/.claude/projects for interactive transcripts, lists those that are idle,
did real work (a commit or enough turns), and have no later save point, and can
dismiss one until it does new work.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from learned import SAVE  # noqa: E402
from userwords import is_user_typed, user_text  # noqa: E402

INTERACTIVE = {"cli", "claude-desktop"}
IDLE_HOURS = 12
MIN_TURNS = 20
MAX_AGE_DAYS = 14
SAVE_PATHS = ("raw/session-notes/", "outputs/briefings/")
COMMIT = re.compile(r"\bgit\b(?:\s+-C\s+\S+)?\s+commit\b")

DEFAULT_PROJECTS = Path.home() / ".claude" / "projects"
DEFAULT_STATE = Path(__file__).resolve().parent / "state" / "unsaved-sessions.json"


def _dt(value):
    """Parse an ISO timestamp, tolerating a trailing Z and missing timezones."""
    if not isinstance(value, str):
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _newer(a, b):
    """Return the later of two ISO strings (None-safe)."""
    if a is None:
        return b
    if b is None:
        return a
    da, db = _dt(a), _dt(b)
    if da is None:
        return b
    if db is None:
        return a
    return a if da >= db else b


def analyze(path):
    """Analyze one transcript file. Returns a JSON-serialisable verdict dict."""
    path = Path(path)
    entrypoint = None
    session_id = None
    last_activity = None
    last_turn = None
    last_commit = None
    last_save = None
    turns = 0
    commits = 0
    custom_title = None
    agent_name = None
    ai_title = None

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or record.get("isSidechain"):
                continue

            if entrypoint is None and "entrypoint" in record:
                entrypoint = record.get("entrypoint")
            if session_id is None and record.get("sessionId"):
                session_id = record.get("sessionId")

            ts = record.get("timestamp")
            if ts is not None:
                last_activity = _newer(last_activity, ts)

            rtype = record.get("type")
            if rtype == "custom-title" and record.get("customTitle"):
                custom_title = record["customTitle"]
            elif rtype == "agent-name" and record.get("agentName"):
                agent_name = record["agentName"]
            elif rtype == "ai-title" and record.get("aiTitle"):
                ai_title = record["aiTitle"]

            if rtype == "user":
                if is_user_typed(record):
                    turns += 1
                    if ts is not None:
                        last_turn = ts
                    if SAVE.search(user_text(record)) and ts is not None:
                        last_save = _newer(last_save, ts)
                continue

            if rtype != "assistant":
                continue
            content = (record.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "tool_use":
                    name = block.get("name")
                    data = block.get("input") or {}
                    if not isinstance(data, dict):
                        data = {}
                    if name == "Bash":
                        command = data.get("command") or ""
                        if COMMIT.search(command):
                            commits += 1
                            if ts is not None:
                                last_commit = ts
                            if any(p in command for p in SAVE_PATHS) and ts is not None:
                                last_save = _newer(last_save, ts)
                    elif name == "Skill":
                        if data.get("skill") == "kb-session-capture" and ts is not None:
                            last_save = _newer(last_save, ts)
                    elif name in ("Write", "Edit"):
                        file_path = data.get("file_path", "") or ""
                        if any(p in file_path for p in SAVE_PATHS) and ts is not None:
                            last_save = _newer(last_save, ts)

    if session_id is None:
        session_id = path.stem
    name = custom_title or agent_name or ai_title or session_id
    last_work = _newer(last_turn, last_commit)
    if last_save is None:
        saved = False
    else:
        reference = last_turn if last_turn else last_work
        saved = reference is None or _dt(last_save) >= _dt(reference)
    return {
        "session_id": session_id,
        "name": name,
        "interactive": entrypoint in INTERACTIVE,
        "last_activity": last_activity,
        "last_work": last_work,
        "turns": turns,
        "commits": commits,
        "saved": saved,
        "path": str(path),
    }


def _load_state(state_path):
    try:
        with open(state_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    files = data.get("files")
    dismissed = data.get("dismissed")
    return {
        "files": files if isinstance(files, dict) else {},
        "dismissed": dismissed if isinstance(dismissed, dict) else {},
    }


def _save_state(state_path, state):
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=1), encoding="utf-8")


def scan(projects=None, state_path=None, now=None):
    """Return unsaved interactive sessions, newest work first."""
    projects = Path(projects) if projects is not None else DEFAULT_PROJECTS
    state_path = Path(state_path) if state_path is not None else DEFAULT_STATE
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    state = _load_state(state_path)
    cached = state["files"]
    dismissed = state["dismissed"]
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    idle = timedelta(hours=IDLE_HOURS)
    sessions = []

    for path in sorted(projects.glob("*/*.jsonl")):
        key = str(path)
        try:
            info = path.stat()
        except OSError:
            continue
        mtime = info.st_mtime
        size = info.st_size
        if (datetime.fromtimestamp(mtime, timezone.utc) < cutoff
                and key not in cached):
            continue

        entry = cached.get(key)
        if (isinstance(entry, dict) and entry.get("mtime") == mtime
                and entry.get("size") == size
                and isinstance(entry.get("verdict"), dict)):
            verdict = entry["verdict"]
        else:
            verdict = analyze(path)
            cached[key] = {"mtime": mtime, "size": size, "verdict": verdict}

        if not verdict.get("interactive"):
            continue
        activity = _dt(verdict.get("last_activity"))
        if activity is None or now - activity < idle:
            continue
        if verdict.get("commits", 0) < 1 and verdict.get("turns", 0) < MIN_TURNS:
            continue
        if verdict.get("saved"):
            continue
        if dismissed.get(verdict.get("session_id")) == verdict.get("last_work"):
            continue

        name = verdict.get("name") or verdict.get("session_id") or ""
        # Track = the first word of a "<track>-<topic>" session name; none for unnamed ones.
        track = name.split("-", 1)[0] if ("-" in name and " " not in name
                                          and name != verdict.get("session_id")) else ""
        sessions.append({
            "session_id": verdict.get("session_id"),
            "name": name,
            "track": track,
            "last_work": verdict.get("last_work"),
            "turns": verdict.get("turns", 0),
            "commits": verdict.get("commits", 0),
            "path": verdict.get("path", key),
        })

    _save_state(state_path, state)
    sessions.sort(key=lambda s: _dt(s["last_work"]) or datetime.min.replace(tzinfo=timezone.utc),
                  reverse=True)
    return sessions


def dismiss(state_path, session_id):
    """Dismiss a session until it has new work. False when it is not cached."""
    state_path = Path(state_path)
    if not state_path.exists():
        return False
    state = _load_state(state_path)
    for entry in state["files"].values():
        verdict = entry.get("verdict") if isinstance(entry, dict) else None
        if isinstance(verdict, dict) and verdict.get("session_id") == session_id:
            state["dismissed"][session_id] = verdict.get("last_work")
            _save_state(state_path, state)
            return True
    return False


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects")
    parser.add_argument("--state")
    parser.add_argument("--now")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list")
    dismiss_parser = sub.add_parser("dismiss")
    dismiss_parser.add_argument("session_id")
    args = parser.parse_args(argv)

    state_path = Path(args.state) if args.state else DEFAULT_STATE
    if args.command == "dismiss":
        if dismiss(state_path, args.session_id):
            print(f"dismissed {args.session_id}")
            return 0
        print(f"unknown session {args.session_id}")
        return 1

    now = _dt(args.now) if args.now else None
    sessions = scan(args.projects, state_path, now=now)
    print(f"unsaved sessions: {len(sessions)}")
    for session in sessions:
        when = (session.get("last_work") or "")[:16].replace("T", " ")
        print(f"  {session['name']} | {session['track'] or '-'} | last work {when} | "
              f"turns {session['turns']} | commits {session['commits']} | "
              f"{session['session_id']} | {session['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
