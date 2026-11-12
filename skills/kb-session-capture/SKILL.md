---
name: kb-session-capture
description: Save takeaways from the current conversation into the Second Brain knowledge base at {{WORKSPACE_DIR}}. Use when the user says "save this session" at the end of a substantive chat.
---

# KB Session Capture

Capture the key takeaways of the current conversation into the Second Brain at `{{WORKSPACE_DIR}}/`.

## Steps

1. Read `{{WORKSPACE_DIR}}/SCHEMA.md` if not already in context.
2. Summarize the substantive takeaways of this conversation (decisions, facts learned, open questions, action items).
3. Save a session note at `{{WORKSPACE_DIR}}/raw/session-notes/<YYYY-MM-DD>-<slug>.md` with frontmatter:
   - `type: session-note`
   - `title`, `tags`, `date`, `agent: <your agent name>`
   - `participants: [user, <agent name>]`
   - `topics:` — wikilinks to topic pages the session touched
   - `pages-updated:` — list of content pages this session created or modified
3b. **Learned:** list what the session learned beyond its decisions (tool quirks, working endpoints, sources that mislabel, user corrections), each with a reason and a destination page. No page fits → create one, link it, index it. Write every item: disk is cheap. End the list with "nothing else learned".
4. If the session produced knowledge that belongs in the brain (a decision, a new fact, a lesson), **update or create the affected content pages** in `raw/pages/` — don't leave the insight trapped in the session note.
5. New pages get a one-line `summary:`; run `python3 -I .overmind/indexgen.py` (wiki/index.md is generated; each line is the page's `summary:` field).
6. (Log: the commit message is the log line (wiki/log.md is generated from git log after each commit; never edit it).)
7. Commit: `git -C {{WORKSPACE_DIR}} status`, then `git -C {{WORKSPACE_DIR}} add <paths you wrote> && git -C {{WORKSPACE_DIR}} commit -m "docs: session <short title>"` (shared tree: never `add -A`) — **local-only repo, never push.**

## Rules

- Session notes are ephemeral capture; content pages are the durable home. The `pages-updated` link is the bridge between the two.
- Capture decisions and reasoning, not chatter. If the conversation had nothing durable, say so and skip the write.
