#!/usr/bin/env python3
"""indexgen.py: build wiki/index.md from page frontmatter.

    python3 -I .overmind/indexgen.py [--root DIR] [--check]

One line per page, "- [[id]] — summary", grouped by folder. The line text is the page's
`summary:` frontmatter field (title when missing). Never edit wiki/index.md by hand: change
the page's summary and run this script. --check exits 1 when the file is out of date.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain_lint import parse_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# (heading, folder, newest first?) in page order
SECTIONS = [("Topics", "raw/pages/topics", False), ("Entities", "raw/pages/entities", False),
            ("Source Summaries", "raw/pages/sources", True),
            ("Projects", "knowledge/projects", False), ("Problems", "knowledge/problems", False),
            ("User", "knowledge/user", False), ("Session Notes", "raw/session-notes", True)]
SKIP = {"README.md", "index.md", "_template.md"}
HEADER = """# Second Brain Wiki Index

Generated from page frontmatter by .overmind/indexgen.py: do not edit. To change a line,
edit the page's `summary:` field and run the script.
"""


def pages(folder):
    out = []
    for path in sorted(folder.glob("*.md")):
        if path.name in SKIP:
            continue
        fm = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace")) or {}
        if not fm.get("id"):
            continue
        when = fm.get("ingested") or fm.get("date") or fm.get("created") or ""
        out.append((when, fm["id"], (fm.get("summary") or fm.get("title") or fm["id"]).strip()))
    return out


def render(root):
    lines = [HEADER]
    for heading, folder, newest_first in SECTIONS:
        rows = pages(root / folder)
        if not rows:
            continue
        rows.sort(key=lambda r: (r[0], r[1]) if newest_first else r[1], reverse=newest_first)
        lines.append("## %s" % heading)
        lines.extend("- [[%s]] — %s" % (pid, text) for _, pid, text in rows)
        lines.append("")
    return "\n".join(lines)


def main(argv):
    parser = argparse.ArgumentParser(prog="indexgen")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root)
    target = root / "wiki/index.md"
    text = render(root)
    if args.check:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current != text:
            print("wiki/index.md is out of date: run .overmind/indexgen.py")
            return 1
        return 0
    target.write_text(text, encoding="utf-8")
    print("%d pages" % text.count("\n- [["))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
