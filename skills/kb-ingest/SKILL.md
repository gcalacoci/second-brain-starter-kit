---
name: KB Ingest
description: Ingest a link, file, or text into the Second Brain knowledge base at {{WORKSPACE_DIR}}. Use when the user says "add this", drops a source to be processed, or asks to save an article/document/note into the brain.
---

# KB Ingest

Ingest a new source into the Second Brain knowledge base at `{{WORKSPACE_DIR}}/`.

## Prerequisites

1. Read `{{WORKSPACE_DIR}}/SCHEMA.md` — it is the source of truth for paths, frontmatter, and rules.
2. Check `{{WORKSPACE_DIR}}/wiki/processed.md` first. If the source is already listed, STOP and tell the user. Never re-ingest.

## Steps

1. **Save the raw source untouched** into `{{WORKSPACE_DIR}}/raw/sources/<slug>.md` (keep original extension for non-text files). Never modify it after saving.
2. Read the source. Extract key points, entities, topics, and claims.
3. Create a **source summary** at `{{WORKSPACE_DIR}}/raw/pages/sources/<slug>.md` with frontmatter: `type: source-summary`, `title`, `raw-file`, `tags`, `topics`, `entities`, `ingested`, `agent: <your agent name>`.
4. **Create or update** topic pages in `raw/pages/topics/` and entity pages in `raw/pages/entities/` as needed. Update the `updated` date on every page you touch.
5. Update `wiki/index.md` — add new pages under the right category with a one-line summary.
6. Append to `wiki/log.md`: `## [YYYY-MM-DD] ingest - <short title>`
7. Add a row to `wiki/processed.md`.
8. Commit: `git -C {{WORKSPACE_DIR}} add -A && git -C {{WORKSPACE_DIR}} commit -m "ingest: <short title>"` — the repo is **local-only, no remote. Never push.**

## Rules

- wiki/ gets only index.md, log.md, processed.md — never put content there.
- Every page you create or modify must have complete YAML frontmatter.
- Link related pages with `[[wikilinks]]` in `related:`/`topics:`/`entities:` frontmatter fields.
- A single source may touch 5-15 pages — that is expected, not a bug.
