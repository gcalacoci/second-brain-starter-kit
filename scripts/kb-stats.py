#!/usr/bin/env python3
"""kb-stats.py — Telemetry for the Second Brain.

Counts pages by type, sources, inbox backlog, problem statuses, inbound-link
popularity, and commit activity. Prints a dashboard; with --save also writes
a report to outputs/reports/YYYY-MM-DD-stats.md.

Usage: kb-stats.py [--root PATH] [--save]
"""

import os
import re
import sys
import glob
import subprocess
from datetime import date, datetime
from collections import Counter

def parse_args(argv):
    root = os.path.expanduser("~/prj/second-brain")
    save = False
    i = 0
    while i < len(argv):
        if argv[i] == "--root":
            root = os.path.expanduser(argv[i + 1]); i += 2
        elif argv[i] == "--save":
            save = True; i += 1
        else:
            i += 1
    return root, save

def fm(content, field):
    m = re.search(rf"^{field}:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else ""

def count_dir(path):
    return len([f for f in glob.glob(os.path.join(path, "**", "*.md"), recursive=True)
                if os.path.basename(f) != "README.md"])

def commit_activity(root):
    """Commits per week for the last 8 weeks (git log, local-only repo)."""
    try:
        out = subprocess.run(
            ["git", "-C", root, "log", "--pretty=%ad", "--date=format:%G-W%V"],
            capture_output=True, text=True, check=True).stdout.strip().splitlines()
    except Exception:
        return None
    return Counter(out)

def inbound_links(root):
    """How many times each [[Page]] is referenced across all pages."""
    counts = Counter()
    pages = glob.glob(os.path.join(root, "raw", "pages", "**", "*.md"), recursive=True)
    bodies = []
    for p in pages:
        try:
            bodies.append(open(p, encoding="utf-8", errors="ignore").read())
        except OSError:
            pass
    for body in bodies:
        for link in re.findall(r"\[\[([^\]|#]+)", body):
            counts[link.strip().lower()] += 1
    return counts, len(bodies)

def main():
    root, save = parse_args(sys.argv[1:])
    lines = []
    add = lines.append

    add(f"# Second Brain Stats — {date.today().isoformat()}")
    add("")
    add("## Volume")
    add("")
    add("| Metric | Count |")
    add("|---|---|")
    add(f"| Topic pages | {count_dir(os.path.join(root, 'raw/pages/topics'))} |")
    add(f"| Entity pages | {count_dir(os.path.join(root, 'raw/pages/entities'))} |")
    add(f"| Source summaries | {count_dir(os.path.join(root, 'raw/pages/sources'))} |")
    add(f"| Session notes | {count_dir(os.path.join(root, 'raw/session-notes'))} |")
    add(f"| Raw sources (immutable) | {len(glob.glob(os.path.join(root, 'raw/sources', '*')))} |")
    add(f"| Inbox backlog | {len(glob.glob(os.path.join(root, 'inbox', '*')))} |")
    add(f"| Outputs | {count_dir(os.path.join(root, 'outputs'))} |")
    add("")

    # Problems status
    problems = glob.glob(os.path.join(root, "knowledge", "problems", "*.md"))
    statuses = Counter()
    for p in problems:
        if os.path.basename(p).startswith("00-"):
            continue
        try:
            c = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        statuses[fm(c, "status") or "unmarked"] += 1
    if problems:
        add("## Favorite Problems")
        add("")
        add("| Status | Count |")
        add("|---|---|")
        for k, v in statuses.most_common():
            add(f"| {k} | {v} |")
        add("")

    # Hub pages (most inbound links)
    links, page_count = inbound_links(root)
    if page_count:
        add(f"## Hub Pages (inbound [[links]] across {page_count} pages)")
        add("")
        add("| Page | Inbound links |")
        add("|---|---|")
        for name, n in links.most_common(8):
            add(f"| [[{name}]] | {n} |")
        orphans = page_count - len([n for n in links if links[n] > 0 and not n.startswith('#')])
        add("")
        add(f"Pages with zero inbound links: **{max(0, page_count - len(links))}** candidate orphans")
        add("")

    # Commit activity
    weeks = commit_activity(root)
    if weeks:
        add("## Commit Activity (last 8 weeks)")
        add("")
        add("| Week | Commits |")
        add("|---|---|")
        for wk, n in sorted(weeks.items(), reverse=True)[:8]:
            add(f"| {wk} | {n} |")
        add("")

    report = "\n".join(lines)
    print(report)

    if save:
        out_dir = os.path.join(root, "outputs", "reports")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, f"{date.today().isoformat()}-stats.md")
        with open(out, "w") as f:
            f.write(report + "\n")
        print(f"\nSaved: {out.replace(os.path.expanduser('~'), '~')}")

if __name__ == "__main__":
    sys.exit(main())
