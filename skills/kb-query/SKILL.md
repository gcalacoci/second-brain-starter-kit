---
name: kb-query
description: Answer questions from the Second Brain knowledge base at ~/prj/second-brain with citations. Use when the user asks "what do I know about ___", requests a briefing, or wants an answer synthesized from the brain.
---

# KB Query

Answer a question using the Second Brain knowledge base at `~/prj/second-brain/`.

## Steps

1. Read `~/prj/second-brain/SCHEMA.md` if not already in context (source of truth for paths and rules).
2. Read `wiki/index.md` first — it is the table of contents. Identify the relevant pages.
3. Read the relevant content pages in `raw/pages/` (topics, entities, source summaries).
4. Synthesize the answer **with citations** — cite the content pages and the raw source files they reference (`raw/sources/...`).
5. Present the answer to the user.
6. If the user says "save that" (or similar): write the answer as a new topic page in `raw/pages/topics/` with full frontmatter (`agent: <your agent name>`), update `wiki/index.md`, and add a `related:` link from the pages it drew on.
7. Append to `wiki/log.md`: `## [YYYY-MM-DD] query - <short title>` (or `query (saved)` if filed back).
8. Commit: `git -C ~/prj/second-brain add -A && git -C ~/prj/second-brain commit -m "docs: query <short title>"` — **local-only repo, never push.**

## Rules

- Never answer from memory alone when the KB has relevant pages — the whole point is that the brain holds the synthesized, current state.
- If the KB has nothing relevant, say so, and optionally offer to research the topic (which becomes an ingest).
- Filing a valuable answer back is what makes the brain compound — don't skip it when the user asks.
