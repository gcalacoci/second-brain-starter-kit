#!/usr/bin/env python3
"""kb-search.py — Fallback search for the Second Brain (no qmd needed).

Scores pages by term matches (title/tags weighted 3x, body 1x) with a small
recency boost. Prints a ranked list of paths.

Usage: kb-search.py <terms...> [--limit N] [--root PATH]
"""

import os
import re
import sys
import glob
from datetime import date

def parse_args(argv):
    terms, limit, root = [], 15, os.path.expanduser("~/prj/second-brain")
    i = 0
    while i < len(argv):
        if argv[i] == "--limit":
            limit = int(argv[i + 1]); i += 2
        elif argv[i] == "--root":
            root = os.path.expanduser(argv[i + 1]); i += 2
        else:
            terms.append(argv[i].lower()); i += 1
    return terms, limit, root

def score_text(text, terms):
    tl = text.lower()
    return sum(tl.count(t) * (3 if i == 0 else 1) for i, t in enumerate(terms))

def frontmatter_field(content, field):
    m = re.search(rf"^{field}:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip().strip('"') if m else ""

def main():
    terms, limit, root = parse_args(sys.argv[1:])
    if not terms:
        print("usage: kb-search.py <terms...> [--limit N] [--root PATH]"); return 1

    search_dirs = [
        os.path.join(root, "raw", "pages"),
        os.path.join(root, "knowledge"),
        os.path.join(root, "raw", "session-notes"),
        os.path.join(root, "outputs"),
    ]
    results = []
    for d in search_dirs:
        for path in glob.glob(os.path.join(d, "**", "*.md"), recursive=True):
            if os.path.basename(path) == "README.md":
                continue
            try:
                content = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            title = frontmatter_field(content, "title") or os.path.basename(path)[:-3]
            tags = frontmatter_field(content, "tags")
            score = score_text(title, terms) * 3 + score_text(tags, terms) * 3 + score_text(content, terms)
            if score == 0:
                continue
            # small recency boost: pages updated recently rank higher
            m = re.search(r"^updated:\s*(\d{4}-\d{2}-\d{2})", content, re.MULTILINE)
            if m:
                try:
                    days = (date.today() - date.fromisoformat(m.group(1))).days
                    score += max(0, 10 - days // 30)  # up to +10 for this month
                except ValueError:
                    pass
            results.append((score, path.replace(os.path.expanduser("~"), "~"), title))

    results.sort(reverse=True)
    if not results:
        print(f"No matches for: {' '.join(terms)}")
        return 0

    print(f"Search: {' '.join(terms)}  ({len(results)} matches, top {min(limit, len(results))})\n")
    for score, path, title in results[:limit]:
        print(f"  [{score:>4}] {title}\n         {path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
