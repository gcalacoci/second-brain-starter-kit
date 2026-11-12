#!/usr/bin/env python3
"""PreToolUse hook (matcher "Read"): an image is read once per session.

An image costs ~1-3k tokens per view, and every later message re-reads it with the rest of
the context. A second Read of the same, unchanged image is denied with a reminder to use
what was already seen; an image that changed since the earlier Read (a re-rendered PDF
page, a new screenshot) is allowed. The current call's own tool_use id is skipped: it is
often already in the transcript when the hook runs. Never blocks on errors.
"""
import json
import os
import sys
from datetime import datetime

IMAGES = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    sys.exit(0)


def seen_before(transcript, path, mtime, current_id):
    needle = json.dumps(path)[1:-1]
    with open(transcript) as f:
        for line in f:
            if needle not in line:
                continue
            rec = json.loads(line)
            content = (rec.get("message") or {}).get("content")
            for b in content if isinstance(content, list) else []:
                if (isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Read"
                        and b.get("id") != current_id
                        and (b.get("input") or {}).get("file_path") == path):
                    ts = rec.get("timestamp", "1970-01-01T00:00:00+00:00").replace("Z", "+00:00")
                    if datetime.fromisoformat(ts).timestamp() > mtime:
                        return True
    return False


def main():
    d = json.load(sys.stdin)
    p = str((d.get("tool_input") or {}).get("file_path", ""))
    if d.get("tool_name") != "Read" or not p.lower().endswith(IMAGES) or not d.get("transcript_path"):
        return
    mtime = os.path.getmtime(p) if os.path.exists(p) else 0
    if seen_before(d["transcript_path"], p, mtime, d.get("tool_use_id")):
        deny(f"Token rule: {p} was already viewed in this session and has not changed; "
             "use what you saw.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass
