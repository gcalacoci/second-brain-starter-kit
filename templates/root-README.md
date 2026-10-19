# Second Brain Knowledge Base

**Owner:** {{USER_NAME}} — {{USER_BIO}}

A self-improving, multi-agent personal knowledge base. See `SCHEMA.md` for the
operating manual every agent follows.

## What this is

- **Raw sources** (`raw/sources/`) — immutable source of truth
- **Wiki pages** (`raw/pages/`) — agent-written synthesis, kept current
- **Index** (`wiki/index.md`) — what agents read first to navigate
- **Inbox** (`inbox/`) — quick capture, processed weekly
- **Skills** (`skills/`) — shared workflows any agent can load

## Daily commands

- `add this` — ingest a source
- `what do I know about ___` — query with citations
- `save that` — persist an answer as a page
- `save this session` — capture chat takeaways
- `dream sequence` — lint + ingest new inbox files
- `weekly review` — maintenance report

## Wiki

`wiki/` is navigation + bookkeeping only — it contains exactly three files,
nothing else:

- `index.md` — table of contents for all brain pages (agent-maintained)
- `log.md` — chronological activity log (append-only)
- `processed.md` — registry of ingested raw files (the dedup source of truth)

All content lives in `raw/pages/`, never in `wiki/`. The agent keeps the index
and log current on every operation; you never edit these by hand.

## Agents

- Claude Code: sees `../CLAUDE.md` shim + one `~/.claude/skills/<skill-id>` symlink per skill
- OpenCode: sees `~/.opencode/instructions.md` shim + skills config entry
- Anything else: "Read SCHEMA.md and follow it"

## Git

Local-only repo. No remote. Never push. (Add a *private* remote only if you
deliberately want an off-machine backup.)
