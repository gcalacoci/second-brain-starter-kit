#!/usr/bin/env python3
"""session-marker.py — Stop hook: drop a pending-session marker for the brain.

On every Claude Code session stop, writes a tiny marker file into the brain:
  ~/prj/second-brain/.overmind/state/pending-sessions/<date>/<time>-<cwd-slug>.json

The marker contains cwd, session_id, and timestamp. It does NOT summarize —
summarizing needs an LLM, which happens later via `kb-session-capture` or the
Dream Sequence, which pick up pending markers and offer to capture them.

Disable in the brain config: kb.session.auto_capture: off
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

KB_ROOT = Path(os.path.expanduser("{{KB_DIR}}"))

def auto_capture_enabled(kb: Path) -> bool:
    cfg = kb / ".overmind" / "config.yaml"
    try:
        text = cfg.read_text()
    except OSError:
        return True  # default on
    if re.search(r"auto_capture:\s*off", text):
        return False
    return True

def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    kb = KB_ROOT
    if "{{" in str(kb):  # unsubstituted template — do nothing
        sys.exit(0)
    if not kb.is_dir():
        sys.exit(0)
    if not auto_capture_enabled(kb):
        sys.exit(0)

    cwd = data.get("cwd", "")
    session_id = data.get("session_id", "unknown")
    now = datetime.now(timezone.utc)
    slug = re.sub(r"[^a-z0-9]+", "-", cwd.replace(os.path.expanduser("~"), "~").lower()).strip("-")[:60] or "session"

    marker_dir = kb / ".overmind" / "state" / "pending-sessions" / now.strftime("%Y-%m-%d")
    try:
        marker_dir.mkdir(parents=True, exist_ok=True)
        marker = marker_dir / f"{now.strftime('%H%M%S')}-{slug}.json"
        marker.write_text(json.dumps({
            "captured": False,
            "session_id": session_id,
            "cwd": cwd,
            "stopped_at": now.isoformat(),
            "transcript_path": data.get("transcript_path", ""),
        }, indent=2) + "\n")
    except OSError:
        pass  # never break session shutdown over a marker

    sys.exit(0)

if __name__ == "__main__":
    main()
