#!/usr/bin/env python3
"""Lint the structure of a markdown second brain.

Usage: python3 -I brain_lint.py [--root DIR] [--staged] [--strict]
"""
import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REQUIRED = ("id", "type", "title", "tags", "created", "updated", "agent")
TYPES = {"topic", "entity", "source-summary", "session-note"}
# SCHEMA operation types plus the Conventional Commit types loggen.py writes.
LOG_TYPES = {"ingest", "query", "dream", "session", "lint", "review", "update", "fix", "plan",
             "feat", "docs", "chore", "refactor", "create", "output"}
WIKI_ALLOWED = {"wiki/index.md", "wiki/log.md", "wiki/processed.md"}
CONTENT_DIRS = ("raw/pages", "raw/session-notes")

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
FM_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
LOG_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] ([\w-]+) - (.+)$")


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def is_empty(value):
    return value is None or value.strip() == "" or re.fullmatch(r"\[\s*\]", value.strip()) is not None


def valid_date(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            fields = {}
            for line in lines[1:end]:
                if not line or line[0].isspace():
                    continue  # nested keys and list items are ignored
                match = FM_LINE_RE.match(line)
                if match:
                    fields[match.group(1)] = unquote(match.group(2))
            return fields
    return None


def link_targets(text):
    targets = []
    for raw in LINK_RE.findall(text):
        target = raw.split("|", 1)[0].split("#", 1)[0].strip()
        if target and target not in targets:
            targets.append(target)
    return targets


def rel_posix(path, root):
    return path.relative_to(root).as_posix()


def content_files(root):
    found = []
    for name in CONTENT_DIRS:
        base = root / name
        if base.is_dir():
            found.extend(p for p in base.rglob("*.md") if p.is_file() and p.name != "README.md")
    return sorted(found, key=lambda p: rel_posix(p, root))


def read(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def staged_files(root):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return set()
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def collect(root):
    pages = []
    for path in content_files(root):
        rel = rel_posix(path, root)
        text = read(path)
        pages.append({"rel": rel, "text": text, "fm": parse_frontmatter(text)})
    return pages


def lint(root, staged=False, strict=False):
    errors, warnings = [], []

    def err(code, rel, message):
        errors.append((code, rel, message))

    def warn(code, rel, message):
        warnings.append((code, rel, message))

    all_pages = collect(root)
    if staged:
        changed = staged_files(root)
        checked = [p for p in all_pages if p["rel"] in changed]
    else:
        checked = all_pages

    # Resolvable link targets: page ids plus filename stems of every markdown file.
    resolvers = {p.stem for p in root.rglob("*.md") if p.is_file()}
    for page in all_pages:
        fm = page["fm"]
        if fm and not is_empty(fm.get("id")):
            resolvers.add(fm["id"])
    for path in (root / "knowledge").rglob("*.md"):  # ids of knowledge pages resolve too
        fm = parse_frontmatter(read(path)) or {}
        if not is_empty(fm.get("id")):
            resolvers.add(fm["id"])

    processed = read(root / "wiki/processed.md")

    # FM001-FM004, SRC001, LNK001.
    for page in checked:
        rel, fm = page["rel"], page["fm"]
        if fm is None:
            err("FM001", rel, "missing frontmatter")
        else:
            missing = [f for f in REQUIRED if is_empty(fm.get(f))]
            if missing:
                err("FM001", rel, "missing required field(s): " + ", ".join(missing))
            page_type = fm.get("type", "")
            if not is_empty(page_type) and page_type not in TYPES:
                err("FM002", rel, f"invalid type: {page_type}")
            for field in ("created", "updated"):
                value = fm.get(field, "")
                if not is_empty(value) and not valid_date(value):
                    err("FM003", rel, f"{field} is not a valid ISO date: {value}")
            if page_type == "source-summary":
                raw_file = fm.get("raw-file", "")
                if is_empty(raw_file) or raw_file not in processed:
                    err("SRC001", rel, f"raw-file not listed in wiki/processed.md: {raw_file}")
        for target in link_targets(page["text"]):
            if target not in resolvers:
                warn("LNK001", rel, f"dangling link: {target}")

    # FM004: first occurrence wins; report checked pages that repeat an id.
    first_seen = {}
    for page in all_pages:
        fm = page["fm"]
        if fm and not is_empty(fm.get("id")):
            first_seen.setdefault(fm["id"], page["rel"])
    for page in checked:
        fm = page["fm"]
        if fm and not is_empty(fm.get("id")):
            first = first_seen[fm["id"]]
            if first != page["rel"]:
                err("FM004", page["rel"], f"duplicate id {fm['id']!r} (first used by {first})")

    if not staged:
        index_text = read(root / "wiki/index.md")
        index_links = link_targets(index_text)
        for target in index_links:
            if target not in resolvers:
                warn("IDX002", "wiki/index.md", f"link resolves to no page: {target}")
        for page in all_pages:
            fm = page["fm"]
            if fm and not is_empty(fm.get("id")) and fm["id"] not in index_links:
                warn("IDX001", page["rel"], f"id not linked from wiki/index.md: {fm['id']}")
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import indexgen  # late: indexgen imports this module
        if (root / "wiki").is_dir() and indexgen.render(root) != index_text:
            warn("IDX003", "wiki/index.md", "out of date: run .overmind/indexgen.py")

        log_text = read(root / "wiki/log.md")
        for number, line in enumerate(log_text.splitlines(), 1):
            if not line.startswith("## ["):
                continue
            match = LOG_RE.match(line)
            if not match or not valid_date(match.group(1)) or match.group(2) not in LOG_TYPES:
                warn("LOG001", "wiki/log.md", f"bad log heading on line {number}: {line}")

    # WIKI001 always runs, including --staged.
    wiki = root / "wiki"
    if wiki.is_dir():
        for path in sorted(wiki.rglob("*"), key=lambda p: rel_posix(p, root)):
            if path.is_file():
                rel = rel_posix(path, root)
                if rel not in WIKI_ALLOWED:
                    err("WIKI001", rel, "unexpected file in wiki/")

    for code, rel, message in errors + warnings:
        print(f"{code} {rel}: {message}")
    print(f"brain_lint: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors or (strict and warnings) else 0


def main():
    default_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Lint the structure of a markdown second brain.")
    parser.add_argument("--root", default=str(default_root), help="brain root (default: parent of this script)")
    parser.add_argument("--staged", action="store_true", help="only check content pages staged in git")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    return lint(root, staged=args.staged, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
