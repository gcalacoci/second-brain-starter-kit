---
name: kb-query
description: Answer questions from the Second Brain knowledge base at {{WORKSPACE_DIR}} with citations. Use when the user asks "what do I know about ___", requests a briefing, or wants an answer synthesized from the brain.
---

# KB Query

Answer a question using the Second Brain knowledge base at `{{WORKSPACE_DIR}}/`.

## Steps

1. Read `{{WORKSPACE_DIR}}/SCHEMA.md` if not already in context (source of truth for paths and rules).
2. Search first: `qmd search "<keywords>" -n 10 --files` when qmd is installed (`qmd get <path>:<from>:<count>`
   reads a slice), else `python3 {{WORKSPACE_DIR}}/scripts/kb-search.py "<keywords>"`. Read `wiki/index.md`
   only when search finds nothing useful or the question is a broad briefing.
3. Read the relevant content pages in `raw/pages/` (topics, entities, source summaries).
4. Synthesize the answer **with citations** — cite the content pages and the raw source files they reference (`raw/sources/...`).
5. Present the answer to the user.
6. If the user says "save that" (or similar): write the answer as a new topic page in `raw/pages/topics/` with full frontmatter (`summary:`, `agent: <your agent name>`), run `python3 -I .overmind/indexgen.py`, and add a `related:` link from the pages it drew on.
7. If an answer was filed back, commit it (`docs: query <short title>`): the commit message is the log line.
8. Commit: `git -C {{WORKSPACE_DIR}} add -A && git -C {{WORKSPACE_DIR}} commit -m "docs: query <short title>"` — **local-only repo, never push.**

## Rules

- Never answer from memory alone when the KB has relevant pages — the whole point is that the brain holds the synthesized, current state.
- If the KB has nothing relevant, say so, and optionally offer to research the topic (which becomes an ingest).
- Filing a valuable answer back is what makes the brain compound — don't skip it when the user asks.
