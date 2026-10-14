---
name: KB Dream
description: Run the Dream Sequence (lint and health check) on the Second Brain knowledge base at {{WORKSPACE_DIR}}. Ingests new raw files, finds contradictions, orphans, stale claims, and missing pages. Use when the user says "dream sequence" or on the scheduled cadence.
---

# KB Dream Sequence

Lint and health-check the Second Brain knowledge base at `{{WORKSPACE_DIR}}/`.

## Steps

1. Read `{{WORKSPACE_DIR}}/SCHEMA.md` (source of truth).
2. **Ingest new raw files**: list `raw/sources/`, compare against `wiki/processed.md`. Ingest anything new (follow the kb-ingest flow for each).
3. **Find contradictions**: compare claims across pages on the same topic/entity. Flag or reconcile each conflict; if you reconcile, update both pages.
4. **Detect stale content**: claims superseded by newer sources. Update the page and note the change in its body.
5. **Find orphans**: pages in `raw/pages/` with no inbound `[[wikilink]]` or index entry. Link them from related pages or flag them.
6. **Find missing pages**: concepts or entities mentioned repeatedly but without their own page. Create them or flag them as gaps.
7. **Verify index.md matches reality**: every page in `raw/pages/` is listed, no dead entries remain.
8. **Check frontmatter integrity**: every page has required fields (`type`, `title`, `tags`, `created`, `updated`, `agent`).
9. Append to `wiki/log.md`: `## [YYYY-MM-DD] dream - <summary of findings and fixes>`
10. Update `last-run` in `.overmind/config.yaml` (dream section) to today.
11. Commit: `git -C {{WORKSPACE_DIR}} add -A && git -C {{WORKSPACE_DIR}} commit -m "chore: dream health check <YYYY-MM-DD>"` — **local-only repo, never push.**


## Delegation (recommended at scale)

Past ~50 pages, delegate the sweep to the `kb-linter` subagent (read-only,
returns structured findings) and apply its `proposed_fix` items yourself.
Keep the main context for judgment calls — the subagent does the bulk reading.

## Rules

- Fix what you can confidently fix; FLAG the rest in the log entry rather than guessing.
- Contradictions that need a human decision get a `## ⚠️ Conflict` note on the affected page(s) plus a log entry.
- Report a short summary to the user at the end: what was ingested, fixed, and flagged.
