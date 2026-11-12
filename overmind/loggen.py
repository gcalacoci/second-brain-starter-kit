#!/usr/bin/env python3
"""loggen.py: build wiki/log.md from git log.

    python3 -I .overmind/loggen.py [--root DIR] [--out FILE]

The commit message is the log line: one "## [date] type - subject" heading per commit,
oldest first, in the format brain_lint LOG001 checks. Run by the post-commit hook;
wiki/log.md is untracked (.gitignore) and nobody appends to it by hand.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TYPES = {"ingest", "query", "dream", "session", "lint", "review", "update", "fix", "plan",
         "feat", "docs", "chore", "refactor", "create", "output"}  # brain_lint LOG_TYPES
SUBJECT = re.compile(r"^([a-z]+)(?:\([^)]*\))?!?:\s*(.+)$")
HEADER = """# Knowledge Base Log

Generated from `git log` by .overmind/loggen.py (post-commit hook): do not edit. The
commit message is the log entry; details: `git show <hash>`.

---
"""


def entries(root):
    out = subprocess.run(["git", "-C", str(root), "log", "--reverse", "--date=short",
                          "--format=%ad%x1f%h%x1f%s%x1f%b%x1e"],
                         capture_output=True, text=True, check=True).stdout
    for record in out.split("\x1e"):
        parts = record.strip("\n").split("\x1f")
        if len(parts) == 4:
            yield parts


def render(rows):
    lines = [HEADER]
    for day, short, subject, body in rows:
        match = SUBJECT.match(subject)
        kind, text = (match.group(1), match.group(2)) if match else ("chore", subject)
        if subject.startswith("Revert"):
            kind, text = "fix", subject
        elif kind not in TYPES:
            kind = "chore"
        lines.append("## [%s] %s - %s" % (day, kind, text.strip()))
        paragraph = body.strip().split("\n\n")[0].splitlines()
        first = " ".join(b.strip() for b in paragraph if not re.match(r"^[\w-]+: ", b))
        lines.append("- %s%s" % (short, (" " + first) if first else ""))
        lines.append("")
    return "\n".join(lines)


def write(path, text):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".log.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def main(argv):
    parser = argparse.ArgumentParser(prog="loggen")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    root = Path(args.root)
    text = render(entries(root))
    write(args.out or root / "wiki/log.md", text)
    print("%d entries" % text.count("\n## ["))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
