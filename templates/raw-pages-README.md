# Raw Pages — The Brain's Content

This is where the brain actually lives. Agent-written markdown pages, each with
YAML frontmatter. This is the persistent, compounding artifact.

## Structure

- `topics/` — Concept and topic pages
- `entities/` — People, organizations, products, places
- `sources/` — Source summaries, one per ingested raw file
- `session-notes/` — Captured session takeaways

## Every page must have

YAML frontmatter with type, title, id, tags, created, updated, agent. See SCHEMA.md.

## Wikilinks

Link pages with `[[Page Title]]`. Wikilinks resolve by filename regardless of
subdirectory. The index is kept current by the agent.

## Examples

- `raw/pages/topics/llm-wiki.md`
- `raw/pages/entities/andrej-karpathy.md`
- `raw/pages/sources/karpathy-llm-wiki-2026-04-04.md`
