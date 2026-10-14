---
name: KB Update
description: Update the user's profile, goals, or problems in the Second Brain when their context changes — new job, role change, department move, new focus, achieved or abandoned goal. Use when the user says "update my profile", "I changed jobs", "I got the job", "I moved to a new team", "my goals changed", "I'm no longer working on X", or otherwise contradicts what the brain knows about them.
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
argument-hint: "[profile|goals|problems|full] — or just describe what changed"
---

# KB Update — Context Change Handler

The user's life changed and the brain's knowledge layer is stale. Your job is to
update `knowledge/` **without losing history**: transitions are appended to a
change log, never silently overwritten. Identity files are never rewritten under
the user's nose — always confirm.

**Arguments:** `$ARGUMENTS` (optional target: profile | goals | problems | full,
or a free-text description of what changed)

---

## Core Principles (read first)

1. **Append, don't overwrite.** The current state lives at the top of each file;
   every transition gets a dated line in that file's `## Change Log`. The fact
   that something *changed* is itself knowledge.
2. **Close, never delete.** A goal that's achieved or abandoned is marked
   `completed` or `abandoned` with a date — it stays in the file.
3. **Cascade, don't just patch.** A profile change affects goals, which affect
   problems, which affect content pages. Handle the ripples, don't leave them
   for the next query to trip over.
4. **Confirm before writing identity.** Show the user the diff you intend to
   make. Never guess who they are.
5. **Commit atomically.** Conventional Commits: `docs: <what changed>` — local-only repo, never push.

---

## Workflow

### Step 1: Determine scope

Based on `$ARGUMENTS` and what the user said, pick a scope:

| Scope | Trigger examples | Files touched |
|---|---|---|
| `profile` | "I changed jobs", "I'm in the AI team now", "update my profile" | `knowledge/user/profile.md` |
| `goals` | "I found a job" (goal achieved), "I'm not doing X anymore" | `knowledge/user/goals.md` (+ profile if identity-related) |
| `problems` | "that problem doesn't matter anymore", "new thing I'm thinking about" | `knowledge/problems/` |
| `full` | "re-onboard me", "everything changed", "new life phase" | all of the above (run the `onboard` skill instead, offering resume of old answers) |

If ambiguous, ask ONE question: "Is this just a profile update, or should I also
look at your goals and problems?"

### Step 2: Read current state

1. Read `SCHEMA.md` (source of truth for conventions).
2. Read the target file(s) in `knowledge/`.
3. Note the `last_reviewed` date in frontmatter.

### Step 3: Interview (conversational, 1-4 questions)

Ask only what you need to know. One question at a time. Examples:

- "What changed?" (if not already said)
- "When did this happen / take effect?" (approximate is fine)
- "Does this close any of your current goals?" (when updating goals)
- "Are the favorite problems still the same ones?" (when identity changed a lot)

Do NOT interrogate. If the user gave enough in their first message, go straight
to the proposal.

### Step 4: Propose the diff

Show the user exactly what will change, using this format:

> Here's what I'll update:
>
> **profile.md**
> - Current role: ~~Unemployed, searching~~ → **Senior Python Dev at Acme AI**
> - Change log entry: `2027-01-15: Hired at Acme AI as Senior Python Dev`
>
> **goals.md**
> - Goal G1 "find a job" → marked **completed** (2027-01-15)
> - No new goal yet — want to set one, or leave it open?
>
> **problems/**
> - Flagging "How do I stand out in interviews?" as `parked` (no longer active context)
>
> OK to apply?

Wait for explicit confirmation. Adjust if they correct you.

### Step 5: Apply changes

**For `profile.md`:**
- Update the current-state section (top of file) with the new reality.
- Append one line to `## Change Log`:
  `- YYYY-MM-DD: <transition description>`
- Update frontmatter: `last_reviewed: YYYY-MM-DD`, `updated: YYYY-MM-DD`.
- Create the `## Change Log` section if it doesn't exist (below the current state).

**For `goals.md`:**
- Mark affected goals/subgoals: change `status: active` → `status: completed`
  or `status: abandoned`, add `closed: YYYY-MM-DD` and a one-line `outcome:`.
- If a major transition happened (e.g., got the job), ASK: "What's the next goal?"
  If they have one, add it (new id, linked to problems); if not, leave the top
  of the file with a `## Open Question` note: "No current end goal as of DATE."
- Append transitions to the `## Change Log`.

**For `problems/`:**
- Park irrelevant problems: add `status: parked` + `parked: YYYY-MM-DD` to the
  problem file's frontmatter and a one-line note in the file. Parked problems
  stay on disk (they may return).
- Add new problems if the user names them (new numbered file, `00-overview.md`
  updated).
- Update `00-overview.md` status column accordingly.

**Ripple check (always do this, for any scope):**
1. Grep `raw/pages/` for content that asserts the OLD state (e.g., pages saying
   "currently job hunting", old employer, old team). Flag pages that now carry
   stale claims — fix clearly factual ones (update + `updated` date), list the
   rest for the user in the summary.
2. Grep `raw/session-notes/` is NOT needed (session notes are historical records,
   never edited).
3. If `inbox/` items reference the old context, leave them — they'll be handled
   at ingest.

### Step 6: Log and commit

1. Append to `wiki/log.md`:
   `## [YYYY-MM-DD] update - <short description of the change>`
2. Commit:
   `git -C {{WORKSPACE_DIR}} add -A && git -C {{WORKSPACE_DIR}} commit -m "docs: update <short description>"`
   (local-only repo, never push)

### Step 7: Summarize

Tell the user:

> Done. Updated:
> - profile.md — <change>
> - goals.md — <change>
> - N content pages flagged/fixed for stale claims
>
> Your brain now reflects: <one-line current state>
>
> <If a goal was closed and none was set:> Whenever you're ready, tell me your
> next goal and I'll wire it in.

---

## Soft Auto-Detection (passive mode)

When this skill is NOT invoked but the user says something that contradicts
`knowledge/user/profile.md` or `goals.md` (e.g., mentions their new team, new
role, new employer in passing):

1. Do NOT silently edit identity files.
2. Finish the user's current request first.
3. Then say: "I noticed you mentioned <new fact>, but your profile says <old
   fact> (last reviewed DATE). Want me to update it?" — and run this skill's
   workflow if they say yes.

This keeps identity updates deliberate while making staleness visible.

---

## Rules

- Never delete `knowledge/` content. Park, close, or supersede — with dates.
- Never rewrite identity files without showing the diff and getting a "yes".
- The `## Change Log` is append-only.
- If the user's change is a total life-phase shift, suggest running `/onboard`
  (it will read existing files and update rather than start from zero).
- All commits are local-only. Never push.
