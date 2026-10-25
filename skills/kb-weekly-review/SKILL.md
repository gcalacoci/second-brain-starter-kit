---
name: kb-weekly-review
description: Run a weekly review of the Second Brain knowledge base. Identify entries with vague tags, duplicate content, missing cross-links, and outdated info. Use when the user says "weekly review" or at the scheduled Friday time.
---

# KB Weekly Review

Weekly maintenance and improvement of the Second Brain at `~/prj/second-brain/`.

## Steps

1. Read `SCHEMA.md`.
2. **Check identity staleness** — read `knowledge/user/profile.md` and
   `knowledge/user/goals.md` frontmatter. If `last_reviewed` is older than
   90 days (or missing), flag in the report: "Your profile/goals haven't been
   reviewed since DATE. Say 'update my profile' if anything changed." Also scan
   `knowledge/problems/` for problems with `status: active` that haven't been
   mentioned in any session note or page update in 90+ days — flag them as
   possibly parked.
3. Scan `wiki/index.md` for pages with:
   - Tags fewer than 2 tags
   - No inbound wikilinks
   - `updated` older than 90 days
3. Find duplicate content: pages with similar titles or summaries.
4. Identify orphan pages in `raw/pages/` not listed in `wiki/index.md`.
5. Check `inbox/` for unprocessed files older than 7 days.
5b. **Memory audit** (Claude Code; skip if the agent has no auto-memory): find the
   memory folder (`autoMemoryDirectory` in `~/.claude/settings.json`, else
   `~/.claude/projects/*/memory/`). Check: `MEMORY.md` ≤ 120 lines (only the first 200
   load), index lines match the files, no dangling `[[links]]`, no memory that repeats
   a rule in `~/.claude/rules/`, state/todo memories not older than the latest session
   note, the same fact not saved in several per-folder memories. Propose merges, trims
   and promotions to rules; the user decides, then apply them.
6. Produce a report in `outputs/reports/YYYY-MM-DD-weekly-review.md` with:
   - **Identity staleness** (profile/goals `last_reviewed`, parked-problem candidates)
   - Pages needing tags
   - Orphans
   - Duplicates
   - Stale pages
   - Inbox backlog
   - Memory audit
7. Append to `wiki/log.md`: `## [YYYY-MM-DD] session - weekly review`
8. Commit: `git -C ~/prj/second-brain add -A && git -C ~/prj/second-brain commit -m "docs: weekly review <date>"` — local-only, never push.
