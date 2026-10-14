---
name: kb-auto-session
description: Auto-capture session takeaways when the agent stops or when the Dream Sequence finds pending-session markers. Use when the user says "save this session" or when the brain's auto-capture is enabled and a session just ended.
allowed-tools: Read, Write, Edit, Bash
argument-hint: "[<session-id> | <marker-path>] — or just run it"
---

# KB Auto Session Capture

Auto-save takeaways from a conversation into the Second Brain.

**Trigger:** the user says "save this session" (manual), or the agent's Stop hook
wrote a pending-session marker and the Dream Sequence / kb-weekly-review picks it up
(auto). Both paths converge here.

---

## Manual mode ("save this session")

1. Read `SCHEMA.md` and `knowledge/user/profile.md`.
2. Summarize the substantive takeaways (decisions, facts, open questions, action items).
3. Write `raw/session-notes/<YYYY-MM-DD>-<slug>.md` with frontmatter:
   ```yaml
   type: session-note
   title: <short title>
   tags: [tag1, tag2]
   date: YYYY-MM-DD
   participants: [user, <agent>]
   duration: <approx>
   topics: [[Topic 1]]
   pages-updated: []
   agent: <agent name>
   ```
4. Update any content pages the session touched (add `updated` date).
5. Append to `wiki/log.md`: `## [YYYY-MM-DD] session - <short title>`
6. Commit: `git -C ~/prj/second-brain add -A && git -C ~/prj/second-brain commit -m "docs: session <short title>"` — local-only, never push.

## Auto mode (pending-session markers)

1. List `~/prj/second-brain/.overmind/state/pending-sessions/` for markers with
   `"captured": false`.
2. For each, read the marker (cwd, session_id, stopped_at) and, if a transcript
   path is present, skim it for substantive content.
3. Ask the user (or the Dream Sequence's judgment): "I found N pending sessions.
   Capture them now? [y/N]" — auto-capture is opt-in by default for privacy.
4. If yes, run the manual flow for each, then mark `"captured": true` in the
   marker file and commit.
5. If no, leave markers pending — they accumulate until the user opts in.

## Rules

- Session notes are **never** deleted or overwritten — they're historical records.
- Auto-capture is **off by default** unless `kb.session.auto_capture: on` is set
  in `.overmind/config.yaml`. Never auto-capture without the user opting in.
- Never push.