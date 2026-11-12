#!/usr/bin/env python3
"""doctor.py: one OK / WARN / FAIL view of the brain's health.

    python3 -I .overmind/doctor.py [--root DIR] [--state DIR] [--now EPOCH]

Reads only what already exists: the cron status files lib/cron.sh writes
(~/.local/state/cron-status/<job>.json), the git hook path, brain_lint.py's error count and
the inbox backlog. One line per check; exit 1 on any FAIL.

Max age per job before WARN: MAX_AGE below, or BRAIN_DOCTOR_MAX_AGE="job=hours,job=hours".
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_AGE = {"brain-maint": 8 * 24}  # hours; jobs not listed: 48
INBOX_WARN = 20  # files waiting in inbox/


def max_age():
    ages = dict(MAX_AGE)
    for item in os.environ.get("BRAIN_DOCTOR_MAX_AGE", "").split(","):
        name, _, hours = item.partition("=")
        if name.strip() and hours.strip().isdigit():
            ages[name.strip()] = int(hours)
    return ages


def _epoch(text):
    text = str(text).strip()
    return float(text) if text.replace(".", "", 1).isdigit() else datetime.fromisoformat(text).timestamp()


def _age(now, ts, limit):
    hours = (now - ts) / 3600
    return ("OK" if hours <= limit else "WARN"), "%.1fh ago (max %dh)" % (hours, limit)


def crons(state, now):
    out, ages = [], max_age()
    for path in sorted((state / "cron-status").glob("*.json")):
        name = path.stem
        if name.startswith("."):  # temp files
            continue
        try:
            data = json.loads(path.read_text())
        except ValueError:
            out.append(("FAIL", "cron %s" % name, "unreadable status file"))
            continue
        if data.get("rc") not in (0, None):
            out.append(("FAIL", "cron %s" % name, "rc %s (log %s)" % (data["rc"], data.get("log"))))
            continue
        if not data.get("finished"):
            out.append(("OK", "cron %s" % name, "running since %s" % data.get("started")))
            continue
        level, text = _age(now, _epoch(data["finished"]), ages.get(name, 48))
        out.append((level, "cron %s" % name, text))
    if not out:
        out.append(("OK", "crons", "no cron status files yet"))
    return out


def gates(root):
    hooks = subprocess.run(["git", "-C", str(root), "config", "core.hooksPath"],
                           capture_output=True, text=True).stdout.strip()
    ok = hooks == ".overmind/git-hooks" and (root / hooks / "pre-commit").exists()
    return [("OK" if ok else "FAIL", "git gates", "hooksPath %s" % (hooks or "unset"))]


def lint(root):
    result = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve().parent / "brain_lint.py"),
                             "--root", str(root)], capture_output=True, text=True)
    last = (result.stdout.strip().splitlines() or ["no output"])[-1]
    return [("OK" if result.returncode == 0 else "FAIL", "brain lint", last)]


def inbox(root):
    folder = root / "inbox"
    files = [p for p in folder.rglob("*") if p.is_file() and p.name not in ("README.md", ".gitkeep")] \
        if folder.is_dir() else []
    level = "WARN" if len(files) > INBOX_WARN else "OK"
    return [(level, "inbox", "%d files waiting" % len(files))]


def main(argv):
    parser = argparse.ArgumentParser(prog="doctor")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--state", default=str(Path.home() / ".local/state"))
    parser.add_argument("--now", type=float, default=None)
    args = parser.parse_args(argv)
    root, state, now = Path(args.root), Path(args.state), args.now or time.time()
    rows = crons(state, now) + gates(root) + lint(root) + inbox(root)
    for level, what, text in rows:
        print("%-4s %-22s %s" % (level, what, text))
    counts = {k: sum(r[0] == k for r in rows) for k in ("OK", "WARN", "FAIL")}
    print("%(OK)d ok, %(WARN)d warn, %(FAIL)d fail" % counts)
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
