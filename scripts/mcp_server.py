#!/usr/bin/env python3
"""Second Brain MCP Server — stdio transport.

Lets an MCP client (e.g. Claude Desktop) search and read the brain
autonomously, and capture new material into inbox/. Read-only everywhere
except the single write_inbox tool.

Workspace root resolution:
- env var SECOND_BRAIN_DIR, falling back to ~/prj/second-brain
- startup fails loudly if the root has no SCHEMA.md

Resources (legacy, kept for clients that support them):
- second-brain://schema, second-brain://wiki/index, second-brain://wiki/log,
  second-brain://wiki/processed, second-brain://config,
  second-brain://page/{path}, second-brain://pages/tag/{tag},
  second-brain://pages/type/{t}

Tools (the way clients should actually use the brain):
- get_schema, get_index, search, read_file, list_files, list_by_tag,
  list_by_type, write_inbox

Launch: uv run --no-project --with "mcp>=1.2" python mcp_server.py
"""

import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# SDK compatibility: mcp 2.x renamed FastMCP to MCPServer and removed the old
# import path (importing it raises ModuleNotFoundError with a pointer to the
# migration guide). Support both generations so the server runs with whatever
# `uv run --with "mcp>=1.2"` resolves to.
try:  # SDK v1 (mcp 1.x)
    from mcp.server.fastmcp import FastMCP  # type: ignore[attr-defined,no-redef]
except ImportError:  # SDK v2 (mcp 2.x)
    from mcp.server import MCPServer as FastMCP  # type: ignore[attr-defined,no-redef]


# ── Workspace root ──────────────────────────────────────────────────

KB = Path(os.environ.get("SECOND_BRAIN_DIR") or Path.home() / "prj" / "second-brain").expanduser().resolve()

if not (KB / "SCHEMA.md").is_file():
    print(
        f"Error: no SCHEMA.md at {KB} — is SECOND_BRAIN_DIR set to a second-brain workspace?",
        file=sys.stderr,
    )
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent

# ── Path safety ─────────────────────────────────────────────────────

MAX_READ_BYTES = 1_000_000  # 1 MB cap on any single read
MAX_WRITE_BYTES = 200 * 1024  # 200 KB cap on inbox writes
INBOX_HEADER_SIZE = 200      # approximate header size in bytes

INBOX_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}\.md$")

# Max content size (excluding header) for inbox writes
MAX_CONTENT_BYTES = MAX_WRITE_BYTES - INBOX_HEADER_SIZE

# Protected locations, applied to the path *relative* to KB so a workspace
# living under a directory called ".envs" doesn't trip the secret patterns.
# - .git/ and .overmind/logs/ as directory components (any depth)
# - file *names* .env, .envrc and .env.<anything> (not .environment-setup.md or
#   .envs), *.secret, *.key, *.pem
DENY_DIR_RE = re.compile(r"(^|/)(\.git|\.overmind/logs)(/|$)")
DENY_FILE_RE = re.compile(r"(^|/)(\.env(rc|\.[^/]*)?|[^/]*\.secret|[^/]*\.key|[^/]*\.pem)$", re.IGNORECASE)


def safe_path(rel: str) -> Path:
    """Resolve a KB-relative path, refusing anything that escapes the root
    (.., absolute paths, symlinks pointing outside) or hits a deny pattern.
    The resolved path is checked too, so a symlink pointing at .git/config
    is still refused even if the link itself looks innocent."""
    if os.path.isabs(rel) or ".." in Path(rel).parts:
        raise ValueError("path escapes the workspace root")
    p = (KB / rel).resolve()
    if not (p == KB or KB in p.parents):
        raise ValueError("path escapes the workspace root (symlink?)")
    try:
        rel_resolved = p.relative_to(KB).as_posix()
    except ValueError:
        raise ValueError("path escapes the workspace root")
    if DENY_DIR_RE.search("/" + rel_resolved) or DENY_FILE_RE.search("/" + rel_resolved):
        raise ValueError("path is in a protected location")
    return p


def read_capped(p: Path) -> str:
    """Read a file, refusing anything over the 1 MB read cap."""
    if p.stat().st_size > MAX_READ_BYTES:
        raise ValueError(f"file larger than {MAX_READ_BYTES // 1000} KB read cap")
    return p.read_text(encoding="utf-8", errors="ignore")


mcp = FastMCP("second-brain")


# ── Tools ───────────────────────────────────────────────────────────

@mcp.tool()
def get_schema() -> str:
    """Return the full SCHEMA.md operating manual."""
    try:
        return (KB / "SCHEMA.md").read_text(encoding="utf-8")
    except OSError as e:
        return f"Error: {e}"


@mcp.tool()
def get_index() -> str:
    """Return wiki/index.md, the table of contents."""
    try:
        return (KB / "wiki" / "index.md").read_text(encoding="utf-8")
    except OSError as e:
        return f"Error: {e}"


@mcp.tool()
def search(query: str, limit: int = 15) -> str:
    """Ranked search over pages, knowledge, session notes and outputs (via kb-search.py)."""
    terms = query.split()
    if not terms:
        return "Error: empty query"
    # Refuse option-looking tokens; kb-search.py has no "--" handling, so a
    # query like "--help" would be read as a flag by the CLI.
    clean = [t for t in terms if not t.startswith("-")]
    if not clean:
        return "Error: query contains only option-like tokens"
    limit = max(1, min(int(limit), 50))
    try:
        out = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "kb-search.py"), *clean, "--limit", str(limit), "--root", str(KB)],
            capture_output=True, text=True, check=True, timeout=30,
        )
        return out.stdout.strip() or f"No matches for: {query}"
    except subprocess.CalledProcessError as e:
        return f"Error: search failed: {e.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Error: search timed out"


@mcp.tool()
def read_file(path: str) -> str:
    """Read one file inside the workspace (relative path, 1 MB cap)."""
    try:
        p = safe_path(path)
        if not p.is_file():
            return f"Error: not a file: {path}"
        return read_capped(p)
    except (ValueError, OSError) as e:
        return f"Error: {e}"


@mcp.tool()
def list_files(dir: str = "") -> str:
    """List .md files under a workspace directory (relative, recursive)."""
    try:
        d = safe_path(dir) if dir else KB
        if not d.is_dir():
            return f"Error: not a directory: {dir or '.'}"
        files = []
        # rglob follows symlinked dirs; guard so nothing escapes the root and
        # protected locations (.git/, .overmind/logs/, deny patterns) are skipped.
        for f in d.rglob("*.md"):
            resolved = f.resolve()
            if not (resolved == KB or KB in resolved.parents):
                continue
            try:
                rel = resolved.relative_to(KB).as_posix()
            except ValueError:
                continue
            if DENY_DIR_RE.search("/" + rel) or DENY_FILE_RE.search("/" + rel):
                continue
            files.append(rel)
        files.sort()
        return "\n".join(files) if files else "(no .md files)"
    except (ValueError, OSError) as e:
        return f"Error: {e}"


@mcp.tool()
def list_by_tag(tag: str) -> str:
    """List pages whose frontmatter tags include the given tag."""
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
                t = re.search(r"^title:\s*(.+)$", txt, re.MULTILINE)
                results.append(f"- [[{fp.stem}]] ({d}) — {t.group(1).strip() if t else 'no title'}")
    return "\n".join(results) if results else f"No pages tagged '{tag}'"


@mcp.tool()
def list_by_type(type: str) -> str:
    """List pages of a type: topic, entity or source-summary."""
    typ = type  # keep the builtin usable inside the function body
    mapping = {"topic": "topics", "entity": "entities", "source-summary": "sources"}
    d = mapping.get(typ.lower())
    if not d:
        return f"Error: unknown type '{typ}' (use topic, entity or source-summary)"
    dirp = KB / "raw" / "pages" / d
    if not dirp.is_dir():
        return f"No {typ} pages yet"
    pages = sorted(f"- [[{p.stem}]]" for p in dirp.glob("*.md"))
    return "\n".join(pages) if pages else f"No {typ} pages yet"


@mcp.tool()
def write_inbox(filename: str, content: str) -> str:
    """Capture a note into inbox/. Filename must be kebab-case .md; the file is
    dated (local time), never overwritten, and capped at 200 KB. This is the
    ONLY write in this server."""
    if not INBOX_NAME_RE.fullmatch(filename):
        # fullmatch, not match: "$" alone would let a trailing newline through
        # ("x.md\n" would otherwise pass).
        return "Error: filename must match ^[a-z0-9][a-z0-9-]{0,80}\\.md$"
    # Check content size (not including header) against the cap
    content_size = len(content.encode("utf-8"))
    if content_size > MAX_CONTENT_BYTES:
        return f"Error: content exceeds {MAX_WRITE_BYTES // 1024} KB write cap"
    inbox = KB / "inbox"
    # Refuse if inbox/ is a symlink or resolves outside the root.
    try:
        resolved_inbox = inbox.resolve()
        if not (resolved_inbox == KB or KB in resolved_inbox.parents):
            return "Error: inbox/ resolves outside the workspace root"
    except OSError as e:
        return f"Error: cannot resolve inbox/: {e}"
    # Local time for the date prefix — matches what the user sees in their
    # file manager; the ISO timestamp inside the header carries the offset.
    now = datetime.now().astimezone()
    dest = inbox / f"{now.strftime('%Y-%m-%d')}-{filename}"
    header = f"<!-- captured: {now.isoformat()}, via: second-brain-mcp -->\n"
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # "x" mode is atomic: fails with FileExistsError if the file already
        # exists, closing the check-then-write race.
        with open(dest, "x", encoding="utf-8") as f:
            f.write(header + content)
    except FileExistsError:
        return f"Error: file already exists: {dest.name}"
    except OSError as e:
        return f"Error: write failed: {e}"
    return f"Written: {dest.relative_to(KB)}"


# ── Resources (legacy, kept for manual attach) ─────────────────────

@mcp.resource("second-brain://schema")
def res_schema() -> str:
    return (KB / "SCHEMA.md").read_text(encoding="utf-8")

@mcp.resource("second-brain://wiki/index")
def res_index() -> str:
    return (KB / "wiki" / "index.md").read_text(encoding="utf-8")

@mcp.resource("second-brain://wiki/log")
def res_log() -> str:
    return (KB / "wiki" / "log.md").read_text(encoding="utf-8")

@mcp.resource("second-brain://wiki/processed")
def res_processed() -> str:
    return (KB / "wiki" / "processed.md").read_text(encoding="utf-8")

@mcp.resource("second-brain://config")
def res_config() -> str:
    return (KB / ".overmind" / "config.yaml").read_text(encoding="utf-8")

@mcp.resource("second-brain://page/{path}")
def res_page(path: str) -> str:
    try:
        p = safe_path(f"raw/pages/{path}.md")
        return p.read_text(encoding="utf-8") if p.is_file() else f"Page not found: {path}"
    except (ValueError, OSError) as e:
        return f"Error: {e}"

@mcp.resource("second-brain://pages/tag/{tag}")
def res_tag(tag: str) -> str:
    return list_by_tag(tag)

@mcp.resource("second-brain://pages/type/{type}")
def res_type(type: str) -> str:
    return list_by_type(type)


if __name__ == "__main__":
    mcp.run()
