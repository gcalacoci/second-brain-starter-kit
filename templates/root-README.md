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

## Agents

- Claude Code: sees `../CLAUDE.md` shim + `~/.claude/skills/second-brain` symlink
- OpenCode: sees `~/.opencode/instructions.md` shim + skills config entry
- Anything else: "Read SCHEMA.md and follow it"

## Git

Local-only repo. No remote. Never push. (Add a *private* remote only if you
deliberately want an off-machine backup.)
