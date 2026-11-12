---
name: kb-dream
description: Run the Dream Sequence (maintenance, lint and health check) on the Second Brain knowledge base at {{WORKSPACE_DIR}}. Scripted checks first, then ingest of new files, contradictions, stale claims, orphans, duplicates, missing pages, identity staleness, memory audit and a report. Use when the user says "dream sequence", "weekly review", or on the scheduled run (brain-maint).
---

# KB Dream Sequence (maintenance)

One maintenance flow for `{{WORKSPACE_DIR}}/`. The scheduled job
`.overmind/brain-maint.sh` runs part A as scripts and hands the results to part B. By hand,
run part A yourself first: `{{WORKSPACE_DIR}}/.overmind/brain-maint.sh --dry-run` (no agent
call; writes only its log).

## A. Scripted checks (brain-maint.sh; read the output, don't redo them by hand)

- `brain_lint.py`: frontmatter, `wiki/` files, sources ↔ processed, index ↔ pages,
  dangling links, log headings (errors, and warning counts per code).
- `indexgen.py --check`: is `wiki/index.md` current?
- Inbox backlog: files in `inbox/`, and those older than 7 days.
- Memory index (Claude Code auto-memory, skipped when there is none): `MEMORY.md` size,
  index lines without a file, files without an index line.
- Cron status and `doctor.py`: last result of every scheduled job, git gates on.
- Unsaved sessions (`unsaved_sessions.py list`): interactive Claude Code sessions idle 12 h+
  that did real work (a commit or 20+ turns) and have no later save point.

## B. Judgement

1. Read `SCHEMA.md`.
2. **Fix scripted errors** you can fix with confidence (lint errors; stale index: run
   `python3 -I .overmind/indexgen.py`; missing `summary:` lines); list the rest in the report.
3. **Ingest new files**: anything in `inbox/`, or in `raw/sources/` but missing from
   `wiki/processed.md` (kb-ingest flow for each).
4. **Contradictions and stale claims**: compare claims across pages on the same
   topic/entity; reconcile (update both pages) or add a `## ⚠️ Conflict` note when it needs
   the user. A claim superseded by a newer source: update the page and say so in its body.
5. **Orphans, duplicates, missing pages, weak tags**: pages nothing links to, pages with
   similar titles or summaries, concepts mentioned often without a page, pages with fewer
   than 2 tags. Link, merge, create or flag.
6. **Identity staleness**: `knowledge/user/profile.md` and `goals.md` with `last_reviewed`
   older than 90 days (or missing) → flag "say 'update my profile' if anything changed";
   `knowledge/problems/` with `status: active` and no mention in 90 days → possibly parked.
7. **Memory audit** (Claude Code; skip if there is no auto-memory): from part A plus a read
   of the memory folder (`autoMemoryDirectory` in `~/.claude/settings.json`, else
   `~/.claude/projects/*/memory/`): `MEMORY.md` ≤ 120 lines, no memory that repeats a rule
   in `~/.claude/rules/`, state/todo memories not older than the latest session note, the
   same fact not saved in several places. Propose merges, trims and promotions to rules;
   the user decides.
8. **Unsaved sessions**: list each one in the report (name, last work, transcript path).
   Never write a note for them unattended: the user either says "save the session <name>"
   (kb-session-capture from that transcript) or dismisses it with
   `python3 -I .overmind/unsaved_sessions.py dismiss <session_id>` (it comes back only after
   new work).
9. **Report**: `outputs/reports/YYYY-MM-DD-brain-maint.md` with sections: Scripted checks,
   Fixed, Flagged (needs the user), Identity, Memory, Unsaved sessions.
10. Update `last-run` in `.overmind/config.yaml` (dream section) to today.
11. Commit only the files you changed: `git -C {{WORKSPACE_DIR}} add <paths> && git -C
    {{WORKSPACE_DIR}} commit -m "chore: dream <YYYY-MM-DD>"`, with the summary of findings
    and fixes in the body (the commit message is the log entry). The pre-commit gate runs;
    fix what it refuses. **Local-only repo, never push.**

## Delegation (recommended at scale)

Past ~50 pages, the `kb-linter` subagent (read-only, returns structured findings) can do
the bulk reading for steps 4–5; apply its `proposed_fix` items yourself. Keep the main
context for judgement calls.

## Rules

- Never touch `private/`, never edit existing `raw/sources/` files.
- Fix what you can confidently fix; flag the rest in the report rather than guessing.
- End with a short summary to the user: ingested, fixed, flagged.
