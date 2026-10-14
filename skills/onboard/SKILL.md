---
name: Onboard Second Brain
description: Guided setup for the Second Brain knowledge base. Walks through establishing the KB's focus, mental models, goals, and initial seeds. Use when the user starts fresh or wants to redefine the brain's purpose. Run this in the first session after setup or when changing focus.
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
argument-hint: "[focus|resume]"
---

# Onboarding the Second Brain

You are guiding a user through setting up their Second Brain knowledge base.
This is their human-readable brain. Be conversational, patient, and build from
what they care about. Don't rush — each step embeds principles for future use.

**Arguments:** `$ARGUMENTS`

---

## Quick Reference

- **Focus Questions:** every KB should start with a focus (e.g., "everything", "learning", "projects")
- **Mental Models:** 12 key ideas that should guide every piece of knowledge in the brain
- **Goals:** end goal (months out) + subgoals (milestones) that the brain will serve
- **Seed Content:** initial sources/pages that make the brain useful on day 1

---

## Before Starting

1. Read `../SCHEMA.md` from the shared KB root (`{{WORKSPACE_DIR}}/`)
2. Check for `state/onboard-progress.yaml` — if it exists, resume
3. Check if `knowledge/` folder exists with content — if so, summary first

### Resuming

On any `/onboard` invocation:

1. Check `state/onboard-progress.yaml`
2. If yes: read `step_completed`, report current state, continue
3. If no: start from Step 1
4. Commit after each step (local git only, never push)
5. Delete progress file at the end

---

## Step 1: Define the KB's Focus (2 min)

**Goal:** Create `knowledge/user/profile.md` with the brain's purpose.

Ask:

> What's the main focus for your knowledge base? Is it "everything in your life",
> or something narrower like "my software projects", "my learning journey",
> "my career development", or "my health and habits"?

Wait for answer. Then refine:

> Give me an example: what would you expect to find here in a month? What
> kinds of questions would you ask this brain?

Summarize what you learned:

```markdown
# User Profile

**Main Focus:** [THEIR ANSWER]

**Example Questions:**
- [Question 1]
- [Question 2]

**What I Observed About Their Brain:**
- They care about [topic A] and [topic B]
- They enjoy [learning style], prefer [output style]
```

Write to `knowledge/user/profile.md` with:

```yaml
---
tags: [user, profile, focus]
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
focus: "whatever they chose"
---
```

**Structure requirement — the file MUST have these two sections:**

1. **Current State** (top) — who the user is right now: role, focus, context.
2. **Change Log** (bottom) — an append-only history, seeded with the onboarding
   entry:
   ```markdown
   ## Change Log
   - YYYY-MM-DD: Profile created — <one-line current state>
   ```

Future transitions (new job, team change, role change) are appended here by the
`kb-update` skill — never overwriting the current state. See `skills/kb-update/SKILL.md`.

Save, commit: `git -C {{WORKSPACE_DIR}} add -A && git -C {{WORKSPACE_DIR}} commit -m "chore: onboard: step 1 - focus defined"`

---

## Step 2: Define Mental Models (5 min)

**Goal:** Populate `knowledge/problems/00-overview.md`

Introduce the concept:

> Richard Feynman kept 12 problems constantly in mind. When he encountered a new idea,
> he tested it against each problem to see if it helped. We're going to define yours.
> These aren't tasks — they're the deep questions the brain should help answer.

Ask:

> What are the 3-4 biggest questions you think about? The deep tensions?

Listen. Reflect. Iterate.

Tip: if they say "I want to build a SaaS", ask "What's the deeper question?"

Once you have 3-4, ask:

> What else keeps you up at night? What do you wish you understood better?

Continue until you have 6-12 genuine problems.

Write `knowledge/problems/00-overview.md`:

```markdown
---
tags: [problems, overview]
created: YYYY-MM-DD
---

# Mental Models for Your Second Brain

Richard Feynman's 12 Problems principle: keep core questions in mind so every
new piece of knowledge can be tested against them.

## Layers

| Layer | Focus |
|---|---|
| The Craft | How you build things |
| The Work | What you're building |
| The Understanding | What you need to learn |
| The Person | Who you're becoming |

## Problems

| # | Problem | One-liner | Layer | Status |
|---|---------|-----------|-------|--------|
| 1 | [Problem 1] | [One-liner] | [Craft/Work/Understanding/Person] | active |
2. [Problem 2] — ...
```

Write individual `knowledge/problems/01-*.md` files for each.

Save, commit: `git -C {{WORKSPACE_DIR}} add -A && git -C {{WORKSPACE_DIR}} commit -m "chore: onboard: step 2 - mental models defined"`

---

## Step 3: Define Goals (3 min)

**Goal:** Create `knowledge/user/goals.md`

Ask:

> Looking at your mental models, what's the one big thing you're building toward?
> Where do you want to be in 3-6 months?

Help them articulate. Then:

> What are 3-5 concrete milestones to get there? Each should be clear enough
> that you'd know when it's done.

For each milestone, capture:

- What it is
- "Done when" criteria
- Which mental models it serves

Write `knowledge/user/goals.md`:

```markdown
---
tags: [goals, milestones]
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
---

# Goals for Your Second Brain

## End Goal

[The big outcome they want]

**Why:** [Their reasoning]

## Subgoals

| # | Milestone | Done When | Mental Models | Status |
|---|-----------|----------|---------------|--------|
| 1 | [Milestone] | [Criteria] | [1,2,3] | active |

## Change Log

- YYYY-MM-DD: Goals created — end goal: <one-liner>
```

**Structure requirement:** each subgoal carries a `Status` column (`active`,
later `completed`/`abandoned` with a `closed:` date via the `kb-update` skill).
The `## Change Log` is append-only.

Save, commit: `git -C {{WORKSPACE_DIR}} add -A && git -C {{WORKSPACE_DIR}} commit -m "chore: onboard: step 3 - goals defined"`

---

## Step 4: Seed Content (optional) (5 min)

**Goal:** Make the brain useful on day 1. Ask about initial sources.

Ask:

> What are 3-5 pieces of knowledge you want in the brain right away?
> 
> Ideas: a foundational article, a project you're working on, notes from a recent
> conversation, a topic you're learning.

For each item:

1. Ingest: "add this" (or paste the URL/text)
2. The brain will create the page/summary

If they have nothing, simulate a first ingest by creating a "Getting Started" topic:

```markdown
---
id: getting-started
type: topic
title: Getting Started with Your Second Brain
tags: [introduction, setup]
created: YYYY-MM-DD
updated: YYYY-MM-DD
agent: opencode
---

# Getting Started

Welcome to your Second Brain. This is the table of contents for Day 1.

## What This Brain Is For

[Brief description of purpose]

## Key Mental Models

[Links to mental models]

## First Steps

1. Use "add this" to drop content
2. Use "what do I know about ___" to query
3. Use "save this session" at the end of conversations
4. Use "dream sequence" for weekly maintenance
```

Save, commit.

Save, commit: `git -C {{WORKSPACE_DIR}} add -A && git -C {{WORKSPACE_DIR}} commit -m "chore: onboard: step 4 - seeded content"`

---

## Step 5: Review & Archive (2 min)

Show a summary:

> Here's what we built:
>
> - **Focus:** [profile.md focus]
> - **Mental Models:** [N] problems in `knowledge/problems/`
> - **Goals:** [end goal] with [N] subgoals in `knowledge/user/goals.md`
> - **Seeded:** [what was added]
>
> Ready to use! Your brain is now self-improving.

Write `state/onboard-progress.yaml`:

```yaml
step_completed: 5
timestamp: YYYY-MM-DDTHH:MM
files_written:
  - knowledge/user/profile.md
  - knowledge/problems/00-overview.md
  - knowledge/problems/01-*.md (N files)
  - knowledge/user/goals.md
  - knowledge/topics/getting-started.md
```

Final commit: `git -C {{WORKSPACE_DIR}} add -A && git -C {{WORKSPACE_DIR}} commit -m "chore: onboard: complete"`

Delete progress file and commit cleanup.

---

## Ready

Your Second Brain is ready. Key commands:

- `add this` — ingest a source
- `what do I know about ___` — query with citations
- `save this session` — capture conversation
- `save that` — persist current answer
- `dream sequence` — weekly lint + health check
- `weekly review` — spot gaps, orphans, stale content
- `/onboard` — restart onboarding if needed