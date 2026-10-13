---
name: Second Brain Rules
path: '{{WORKSPACE_DIR}}/**'
---

# Second Brain Rules — Path-Scoped

These rules apply only when working inside {{WORKSPACE_DIR}}/.

## Hard rules
- Never edit files in raw/sources/. If a correction is needed, create a new version with a new name.
- Every content page in raw/pages/ must have YAML frontmatter with id, type, title, tags, created, updated, agent.
- wiki/ may contain only index.md, log.md, processed.md.
- New captures go to inbox/ first; ingestion moves them into raw/sources/ + raw/pages/.
- All writes to the brain must update wiki/log.md and, where relevant, wiki/index.md and wiki/processed.md.
- Git is local-only. Never run git push. Never add a remote without explicit user instruction (and it must be private).
- Always read SCHEMA.md before any operation in this tree.

## Frontmatter requirements
All pages require id (kebab-case, unique), type, title, tags, created, updated, agent.

## Ingest protocol
Check wiki/processed.md before ingesting. If already listed, skip and inform the user.

## Commit messages
Use atomic commits with prefixes: ingest:, query:, dream:, session:, skill:.

## Safety
Before editing sensitive files (.env, credentials), warn the user.
