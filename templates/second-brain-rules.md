---
name: Second Brain Rules
---

# Second Brain Rules

These rules apply only when working inside {{WORKSPACE_DIR}}/.
<!-- Loaded in every session: no `paths:` key on purpose. For user-level rules Claude Code
     matches `paths:` against the session's start folder, so an absolute workspace glob
     never matches. The sentence above limits the scope. -->

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
Use Conventional Commits: feat: (ingest, new pages, new skills), docs: (filed answers, session notes, profile/goal updates), chore: (dream runs, onboarding), fix: (content corrections), refactor: (restructures).

## Safety
Before editing sensitive files (.env, credentials), warn the user.
