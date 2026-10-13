---
name: KB Weekly Review
description: Run a weekly review of the Second Brain knowledge base. Identify entries with vague tags, duplicate content, missing cross-links, and outdated info. Use when the user says "weekly review" or at the scheduled Friday time.
---

# KB Weekly Review

Weekly maintenance and improvement of the Second Brain at `{{WORKSPACE_DIR}}/`.

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
6. Produce a report in `outputs/reports/YYYY-MM-DD-weekly-review.md` with:
   - **Identity staleness** (profile/goals `last_reviewed`, parked-problem candidates)
   - Pages needing tags
   - Orphans
   - Duplicates
   - Stale pages
   - Inbox backlog
7. Append to `wiki/log.md`: `## [YYYY-MM-DD] session - weekly review`
8. Commit: `git -C {{WORKSPACE_DIR}} add -A && git -C {{WORKSPACE_DIR}} commit -m "session: weekly review <date>"` — local-only, never push.
