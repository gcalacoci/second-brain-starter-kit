# Second Brain Starter Kit — User Manual

A complete reference for using your Second Brain knowledge base. This manual is for **you** (the human user), not for agents. For agent-facing documentation, see `README.md` and `SCHEMA.md`.

---

## Quick Reference Card

Print this or keep it handy. These are the commands you'll use daily.

| You say | What happens | Skill |
|---|---|---|
| `add this` + link/file/text | Ingests a source: saves raw, creates pages, updates index | `kb-ingest` |
| `what do I know about ___` | Answers from the brain with citations | `kb-query` |
| `save that` | Persists the current answer as a new topic page | (part of `kb-query`) |
| `save this session` | Captures chat takeaways into session notes | `kb-session-capture` |
| `dream sequence` | Lint + ingest new inbox files + find contradictions/orphans | `kb-dream` |
| `weekly review` | Maintenance report: stale content, vague tags, backlog | `kb-weekly-review` |
| `update my profile` / `I changed jobs` | Updates identity files with change log, cascades to goals/pages | `kb-update` |
| `/onboard` | Guided setup: focus, favorite problems, goals, seeds | `onboard` |
| `/kb-plan <what to build>` | Gated 6-phase workflow for building brain features | `kb-plan` |

---

## The Daily Four

These four commands are 90% of how you'll interact with the brain.

### 1. `add this` — Feed the brain

Drop anything into the brain:

```
add this: https://example.com/article-about-ml
```

or paste text:

```
add this:
[paste meeting notes, article excerpt, idea, etc.]
```

**What happens:**
- Raw source saved to `raw/sources/` (immutable, never edited)
- A source summary page created in `raw/pages/sources/`
- Relevant topic/entity pages created or updated in `raw/pages/`
- `wiki/index.md`, `wiki/log.md`, `wiki/processed.md` all updated
- Git commit: `ingest: <title>`

**Pro tip:** Use the inbox for quick capture. Drop files into `inbox/` and run `dream sequence` weekly to process them in batch.

---

### 2. `what do I know about ___` — Query with citations

Ask anything you've accumulated knowledge about:

```
what do I know about machine learning?
what do I know about my career goals?
what do I know about project X?
```

**What happens:**
- Agent reads `wiki/index.md` first (table of contents)
- Reads relevant pages in `raw/pages/`
- Synthesizes an answer **with citations** to specific pages and raw sources
- If you say `save that`, the answer becomes a new topic page

**Pro tip:** The brain compounds only if you file valuable answers back. When an answer feels like "this should be permanent", say `save that`.

---

### 3. `save this session` — Capture chat takeaways

At the end of a substantive conversation:

```
save this session
```

**What happens:**
- Key takeaways summarized into `raw/session-notes/<date>-<slug>.md`
- Any content pages the session touched are updated
- `wiki/log.md` appended
- Git commit: `session: <title>`

**Pro tip:** Session notes are ephemeral capture — the durable knowledge lives in the content pages they link to (`pages-updated` in frontmatter).

---

### 4. `dream sequence` — The brain tidies itself

Run weekly or on-demand:

```
dream sequence
```

**What happens:**
- Processes any new files in `inbox/`
- Ingests them (same flow as `add this`)
- Finds contradictions between pages
- Detects stale/outdated claims
- Identifies orphan pages (no inbound links)
- Flags missing pages (concepts mentioned but without their own page)
- Fixes what it can, flags the rest in `wiki/log.md`
- Git commit: `dream: <date>`

**Pro tip:** Schedule this for Friday afternoon. Wake up Monday to a cleaner brain.

---

## Maintenance Commands

### `weekly review`

A lighter, report-focused check:

```
weekly review
```

**What you get:**
- Identity staleness check (profile/goals not reviewed in 90+ days)
- Pages with vague/missing tags
- Orphan pages
- Duplicate content candidates
- Inbox backlog (files older than 7 days)

Output goes to `outputs/reports/YYYY-MM-DD-weekly-review.md`.

**When to use:** Alternate with `dream sequence` — one week dream, one week review.

---

### `update my profile` / `I changed jobs`

Your context changed; the brain should too:

```
update my profile
I changed jobs
I got the job
I moved to the AI team
my goals changed
```

**What happens:**
- Agent interviews you (1-4 questions, one at a time)
- Proposes the exact diff before writing
- Updates `knowledge/user/profile.md`, `knowledge/user/goals.md`, or `knowledge/problems/`
- Appends to each file's `## Change Log` (append-only history)
- Closes achieved/abandoned goals (never deletes)
- Parks irrelevant problems (never deletes)
- Scans `raw/pages/` for stale claims about your old context
- Commits: `update: <change>`

**Pro tip:** If the agent notices you contradicting your profile mid-session ("I'm on the AI team now" when profile says "job searching"), it will **ask** before updating — identity is never silently rewritten.

---

### `/onboard` — Guided setup

Run this when:
- You're starting fresh
- You want to redefine the brain's focus
- Your life phase changed dramatically (new career, new domain, etc.)

```
/onboard
```

**The 5 steps:**
1. **Focus** — what's the brain for?
2. **Mental models** — your 6-12 Feynman-style favorite problems
3. **Goals** — end goal + 3-5 subgoals
4. **Seed content** — 3-5 pieces of knowledge to start with
5. **Summary** — what was built, how to use it

**Checkpoint commits:** progress is saved after every step. Disconnect anytime, run `/onboard` again to resume.

---

### `/kb-plan <what to build>`

For building new brain features (not daily use — for architectural changes):

```
/kb-plan add a github ingest skill
/kb-plan redesign the inbox workflow
/kb-plan add vector search support
```

**The 6 phases:**
1. Explore — understand the need
2. Discover — find existing patterns/tools
3. Design — sketch the minimal change
4. Approve — explicit "go" from you
5. Implement — atomic commits per file
6. Verify — test and update docs

**When to use:** Anything touching 3+ files or changing how the brain operates.

---

## The Knowledge Layer (`knowledge/`)

This is meta-knowledge **about you**, not the brain's content:

| File | Purpose | Updated by |
|---|---|---|
| `knowledge/user/profile.md` | Who you are, focus, communication style | `/onboard`, `kb-update` |
| `knowledge/user/goals.md` | End goal + subgoals the brain serves | `/onboard`, `kb-update` |
| `knowledge/problems/` | Your favorite problems (Feynman-style) | `/onboard`, `kb-update` |
| `knowledge/projects/` | Per-project working notes | You / agents |

**Read these at session start** when working on the brain — they tell the agent *who the brain is for*, not just what's in it.

### Change Log Convention

Every identity file has two parts:

```markdown
# Current State (top)
You are X, working on Y, goal is Z.

## Change Log (bottom, append-only)
- 2026-10-13: Profile created — job searching, learning ML
- 2027-01-15: Hired at Acme AI as Senior Python Dev
- 2027-03-02: Moved to AI team; architect of Project X
```

**Rules:**
- Transitions are **never deleted** — the history of change is knowledge
- Goals are closed (`completed`/`abandoned` + date), never removed
- Problems may be `parked` — they stay on disk
- `last_reviewed` in frontmatter tracks freshness

---

## Folder Reference

| Folder | Purpose |
|---|---|
| `inbox/` | Quick capture — drop stuff here, process weekly |
| `raw/sources/` | Immutable raw dumps (never edited) |
| `raw/pages/topics/` | Concept/topic pages |
| `raw/pages/entities/` | People, orgs, products |
| `raw/pages/sources/` | One summary per ingested source |
| `raw/session-notes/` | Captured conversation takeaways |
| `wiki/` | Navigation only: `index.md`, `log.md`, `processed.md` |
| `knowledge/` | Meta-knowledge about you |
| `outputs/` | Finished briefings, reports, summaries |
| `skills/` | Shared skill library (all agents use these) |

---

## Git Policy

**Local-only by default.** The repo has no remote and must never be pushed to a public host.

- Each operation commits atomically: `ingest:`, `query:`, `dream:`, `session:`, `update:`, `skill:`
- A safety hook blocks `git push` for this repo
- For off-machine backup: create a **private** repo deliberately (never public)

```bash
# Optional: private backup
cd ~/prj/second-brain
git remote add origin git@github.com:YOUR_USERNAME/private-brain.git
git push -u origin master
```

---

## Multi-Agent Access

The same brain is operated by any agent:

| Agent | How it finds the brain | How it finds skills |
|---|---|---|
| **Claude Code** | `~/prj/CLAUDE.md` shim → `SCHEMA.md` | `~/.claude/skills/second-brain` symlink |
| **OpenCode** | `~/.opencode/instructions.md` shim | `skills` entry in `~/.config/opencode/opencode.json` |
| **Any other** | "Read `~/prj/second-brain/SCHEMA.md` and follow it" | Read `SKILL.md` files directly |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Agent doesn't know the brain exists | Paste the agent prompt (see `AGENT-PROMPT.md`) |
| Skills not loading | Check symlinks / config entries (see Multi-Agent table) |
| "processed.md says X is ingested but I don't see it" | Check `raw/sources/` — the raw file is the source of truth |
| Profile feels stale | Say "update my profile" or run `weekly review` |
| Too many orphan pages | Run `dream sequence` — it links or flags them |
| Inbox backlog | Run `dream sequence` or `weekly review` |

---

## Credits

Built on Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern, with onboarding and workflow ideas adapted from [mp-web3/claude-starter-kit](https://github.com/mp-web3/claude-starter-kit).

## License

MIT
