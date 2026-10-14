#!/usr/bin/env python3
"""Second Brain MCP Server — stdio transport.

Exposes the knowledge base as MCP resources so any MCP-capable agent can
query the brain without touching the filesystem directly.

Resources exposed:
- second-brain://schema          → SCHEMA.md
- second-brain://wiki/index      → wiki/index.md
- second-brain://wiki/log        → wiki/log.md
- second-brain://wiki/processed  → wiki/processed.md
- second-brain://page/{path}     → raw/pages/{path}.md
- second-brain://pages/tag/{tag} → ranked list of pages with tag
- second-brain://pages/type/{t}  → all pages of type (topic|entity|source-summary)
- second-brain://config          → .overmind/config.yaml
- second-brain://search?q={q}    → search results (delegates to kb-search.py)

Run: python3 mcp_server.py (stdio transport — for MCP clients)
"""

import json
import os
import re
import sys
import subprocess
from pathlib import Path
from mcp.server import FastMCP

KB = Path(os.path.expanduser("~/prj/second-brain"))
PY = sys.executable

mcp = FastMCP("second-brain")


# ── Static resources ────────────────────────────────────────────────

@mcp.resource("second-brain://schema")
def schema() -> str:
    return (KB / "SCHEMA.md").read_text(encoding="utf-8")

@mcp.resource("second-brain://wiki/index")
def wiki_index() -> str:
    return (KB / "wiki" / "index.md").read_text(encoding="utf-8")

@mcp.resource("second-brain://wiki/log")
def wiki_log() -> str:
    return (KB / "wiki" / "log.md").read_text(encoding="utf-8")

@mcp.resource("second-brain://wiki/processed")
def wiki_processed() -> str:
    return (KB / "wiki" / "processed.md").read_text(encoding="utf-8")

@mcp.resource("second-brain://config")
def config() -> str:
    return (KB / ".overmind" / "config.yaml").read_text(encoding="utf-8")


# ── Templated resources ─────────────────────────────────────────────

@mcp.resource("second-brain://page/{path}")
def page(path: str) -> str:
    """Read a content page: second-brain://page/topics/machine-learning"""
    p = KB / "raw" / "pages" / f"{path}.md"
    if not p.is_file():
        return f"Page not found: {path}"
    return p.read_text(encoding="utf-8")


@mcp.resource("second-brain://pages/tag/{tag}")
def pages_by_tag(tag: str) -> str:
    """Find all pages with a given tag (uses kb-search.py logic)."""
    from datetime import date

    results = []
    for d in ["topics", "entities", "sources"]:
        dirp = KB / "raw" / "pages" / d
        if not dirp.is_dir():
            continue
        for fp in dirp.glob("*.md"):
            try:
                txt = fp.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            m = re.search(r"^tags:\s*\[(.+?)\]", txt, re.MULTILINE | re.IGNORECASE)
            if m and tag.lower() in [t.strip().lower() for t in m.group(1).split(",")]:
                title = re.search(r"^title:\s*(.+)$", txt, re.MULTILINE)
                results.append(f"- [[{fp.stem}]] ({d}) — {title.group(1).strip() if title else 'no title'}")
    return "\n".join(results) if results else f"No pages tagged '{tag}'"


@mcp.resource("second-brain://pages/type/{typ}")
def pages_by_type(typ: str) -> str:
    """List all pages of a type: topic, entity, source-summary."""
    mapping = {"topic": "topics", "entity": "entities", "source-summary": "sources"}
    d = mapping.get(typ.lower())
    if not d:
        return f"Unknown type: {typ}"
    dirp = KB / "raw" / "pages" / d
    if not dirp.is_dir():
        return f"No {typ} pages yet"
    pages = sorted(f"- [[{p.stem}]]" for p in dirp.glob("*.md"))
    return "\n".join(pages) if pages else f"No {typ} pages yet"


@mcp.resource("second-brain://search")
def search(q: str = "") -> str:
    """Full search via kb-search.py (BM25 + recency)."""
    if not q:
        return "Provide ?q=your+query"
    try:
        out = subprocess.run(
            [PY, str(Path(__file__).with_name("kb-search.py")), *q.split()],
            capture_output=True, text=True, check=True, cwd=Path(__file__).parent
        )
        return out.stdout.strip() or "No matches"
    except subprocess.CalledProcessError as e:
        return f"Search error: {e.stderr}"


if __name__ == "__main__":
    import re
    mcp.run()