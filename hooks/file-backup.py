#!/usr/bin/env python3
"""file-backup.py — PreToolUse hook: back up brain files before edits.

Reads the standard hook JSON from stdin, and if the target file is inside the
Second Brain, copies it to ~/.claude/backups/second-brain/ before the edit.
Keeps the last 10 backups per filename.
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Brain root — substituted by setup.sh ({{KB_DIR}})
KB_ROOT = "{{KB_DIR}}"
BACKUP_DIR = Path.home() / ".claude" / "backups" / "second-brain"
KEEP = 10

def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    p = Path(os.path.expanduser(file_path)).resolve()
    kb = Path(KB_ROOT).expanduser().resolve()

    # Only back up files inside the brain
    if not (p == kb or kb in p.parents):
        sys.exit(0)
    if not p.is_file():
        sys.exit(0)

    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        dest = BACKUP_DIR / f"{p.name}-{ts}.bak"
        shutil.copy2(p, dest)
        print(f"📦 Backed up: {p.name} -> {dest}")

        # Keep only the last KEEP backups per filename
        siblings = sorted(
            BACKUP_DIR.glob(f"{p.name}-*.bak"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        for old in siblings[KEEP:]:
            old.unlink(missing_ok=True)
    except OSError as e:
        # Never block an edit because backup failed
        print(f"⚠️ backup failed: {e}", file=sys.stderr)

    sys.exit(0)

if __name__ == "__main__":
    main()
