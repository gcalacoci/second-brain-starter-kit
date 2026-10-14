---
name: kb-session-capture
description: Save takeaways from the current conversation into the Second Brain knowledge base at ~/prj/second-brain. Use when the user says "save this session" at the end of a substantive chat.
---

# KB Session Capture

Capture the key takeaways of the current conversation into the Second Brain at `~/prj/second-brain/`.

## Steps

1. Read `~/prj/second-brain/SCHEMA.md` if not already in context.
2. Summarize the substantive takeaways of this conversation (decisions, facts learned, open questions, action items).
3. Save a session note at `~/prj/second-brain/raw/session-notes/<YYYY-MM-DD>-<slug>.md` with frontmatter:
   - `type: session-note`
   - `title`, `tags`, `date`, `agent: <your agent name>`
   - `participants: [user, <agent name>]`
   - `topics:` — wikilinks to topic pages the session touched
   - `pages-updated:` — list of content pages this session created or modified
4. If the session produced knowledge that belongs in the brain (a decision, a new fact, a lesson), **update or create the affected content pages** in `raw/pages/` — don't leave the insight trapped in the session note.
5. Update `wiki/index.md` for any new pages.
6. Append to `wiki/log.md`: `## [YYYY-MM-DD] session - <short title>`
7. Commit: `git -C ~/prj/second-brain add -A && git -C ~/prj/second-brain commit -m "docs: session <short title>"` — **local-only repo, never push.**

## Rules

- Session notes are ephemeral capture; content pages are the durable home. The `pages-updated` link is the bridge between the two.
- Capture decisions and reasoning, not chatter. If the conversation had nothing durable, say so and skip the write.
