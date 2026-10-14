# Second Brain Knowledge Base — Shared Schema

**KB Location:** `{{WORKSPACE_DIR}}/`
**Schema Path:** `{{WORKSPACE_DIR}}/SCHEMA.md`

This is the single source of truth for all agents accessing this knowledge base.
All agents must read this schema before any operation. This file is agent-agnostic:
the same schema is followed by Claude Code, OpenCode, and any other agent.

## Identity

This is a Karpathy-style LLM Wiki knowledge base. It is multi-agent aware,
multi-project accessible, and self-improving. It lives at `{{WORKSPACE_DIR}}/`
and is reachable from any project under `~/prj/`.

Philosophy: the LLM incrementally builds and maintains a persistent, interlinked
wiki of markdown pages sitting between the user and the raw sources. Knowledge is
compiled once and kept current, not re-derived on every query. The wiki is a
compounding artifact — it gets richer with every source ingested and every valuable
answer filed back.

## Architecture

```
{{WORKSPACE_DIR}}/
│
├── SCHEMA.md                  ← this file (the schema)
├── inbox/                     ← quick capture; processed by dream sequence / weekly review
├── skills/                    ← shared skill library (see Skills section)
│
├── .overmind/
│   ├── config.yaml
│   └── mcp-resource-map.yaml
│
├── raw/
│   ├── sources/               ← immutable raw dumps (links, articles, notes, PDFs)
│   ├── session-notes/         ← capture notes from agent conversations
│   └── pages/                 ← THE BRAIN'S CONTENT (agent-written & maintained)
│       ├── topics/            ← concept / topic pages
│       ├── entities/          ← people, places, orgs, products, concepts
│       └── sources/           ← one source-summary page per ingested raw file
│
├── knowledge/                 ← META-KNOWLEDGE about the user (see Knowledge Layer)
│   ├── user/profile.md
│   ├── user/goals.md
│   ├── problems/
│   └── projects/
│
├── wiki/                      ← NAVIGATION + BOOKKEEPING ONLY
│   ├── index.md               ← table of contents (catalogs all pages in raw/pages/)
│   ├── log.md                 ← chronological activity log (append-only)
│   └── processed.md           ← registry of ingested raw files
│
└── outputs/                   ← finished deliverables for the user
    ├── briefings/
    ├── reports/
    └── summaries/
```

### Hard rules

- `wiki/` contains ONLY `index.md`, `log.md`, `processed.md`. Never put content there.
- `raw/sources/` is IMMUTABLE. Once a file lands there it is never edited or deleted.
- All content pages live in `raw/pages/`, never in `wiki/`.
- Every content page has YAML frontmatter (see Frontmatter Conventions).
- New captures go to `inbox/` first; ingestion moves them into `raw/sources/` + pages.

## Knowledge Layer (meta)

`knowledge/` holds meta-knowledge about the user and the brain's purpose:

- `user/profile.md` — identity, focus, communication style (created by `/onboard`)
- `user/goals.md` — end goal and subgoals the brain serves
- `problems/` — the user's favorite problems; new knowledge should be tested
  against these when deciding what matters
- `projects/` — per-project working notes

Read the relevant knowledge files at session start when working on this brain.

### Change Log convention (identity files)

`profile.md`, `goals.md`, and each problem file carry TWO parts:

1. **Current state** (top) — who the user is right now. What agents use day-to-day.
2. **## Change Log** (bottom) — an **append-only** dated history of transitions:

```markdown
## Change Log
- 2026-10-13: Profile created — job searching, learning ML
- 2027-01-15: Hired at Acme AI as Senior Python Dev
- 2027-03-02: Moved to AI team; architect of Project X (new language: Rust)
```

Rules:
- Transitions are **never overwritten or deleted** — the history of change is
  itself knowledge.
- Goals are closed (`completed`/`abandoned` + `closed:` date), never deleted.
- Problems may be `parked` (with a date) — they stay on disk.
- Updates go through the `kb-update` skill; identity files are never silently
  rewritten by an agent. If a user statement contradicts the profile mid-session,
  the agent proposes an update instead of applying it.
- `last_reviewed` in frontmatter tracks freshness; `kb-weekly-review` flags
  identity files not reviewed in 90+ days.

## Frontmatter Conventions

Every content page in `raw/pages/` (and every session note in `raw/session-notes/`)
MUST start with a YAML frontmatter block. This enables cross-agent search, filtering,
and tooling.

### Required fields (all pages)

| Field | Meaning |
|---|---|
| `id` | Unique kebab-case identifier for the page |
| `type` | `topic`, `entity`, `source-summary`, or `session-note` |
| `title` | Human-readable title |
| `tags` | Array of lowercase keywords |
| `created` | ISO date (YYYY-MM-DD) the page was first created |
| `updated` | ISO date of the last modification |
| `agent` | Which agent created or last edited the page |

### Type-specific fields

| Type | Extra fields |
|---|---|
| `topic` | `sources` (raw file paths), `related` (wikilinks to other pages) |
| `entity` | `kind` (`person`\|`organization`\|`product`\|`place`\|`concept`), `sources`, `related` |
| `source-summary` | `raw-file` (path to the raw source), `topics`, `entities`, `ingested` (date) |
| `session-note` | `date`, `participants`, `duration`, `topics`, `pages-updated` |

### Examples

```yaml
# topic page (raw/pages/topics/<slug>.md)
---
type: topic
title: "Machine Learning Fundamentals"
tags: [ml, fundamentals, ai]
sources: [raw/sources/ml-intro-2026.md]
related: [[Neural Networks], [[Gradient Descent]]]
created: 2026-10-13
updated: 2026-10-13
agent: opencode
---
```

```yaml
# source summary (raw/pages/sources/<slug>.md)
---
type: source-summary
title: "Summary: LLM Wiki Pattern"
raw-file: raw/sources/karpathy-llm-wiki.md
tags: [knowledge-management, llm, wiki]
topics: [[Second Brain], [[LLM Wiki]]]
entities: [[Andrej Karpathy]]
ingested: 2026-10-13
agent: opencode
---
```

### Rules

- Filenames are kebab-case slugs: `machine-learning-fundamentals.md`.
- Cross-link pages using `[[wikilinks]]` in the frontmatter `related`/`topics`/`entities`
  fields and in the page body.
- Always bump the `updated` date when a page changes.

## The 5 Operations

1. **INGEST** — save a raw source untouched into `raw/sources/`, create a source
   summary, create/update topic & entity pages, update `wiki/index.md`, append to
   `wiki/log.md`, add a row to `wiki/processed.md`.
2. **QUERY** — read `wiki/index.md` first, read the relevant pages, answer with
   citations. On request ("save that"), file the answer back as a new topic page.
3. **DREAM** — ingest new raw files, then lint: find contradictions, stale claims,
   orphan pages, missing pages; fix or flag them. Run on command or on schedule.
4. **INDEX + LOG** — always keep `wiki/index.md` current and append to `wiki/log.md`.
5. **SESSION CAPTURE** — on "save this session", write a session note into
   `raw/session-notes/` and update any affected content pages.

Each operation must update the relevant pages AND append to `wiki/log.md`.
Log entry format: `## [YYYY-MM-DD] ingest|query|dream|session - short title`.

**The self-improving rule:** every ingest and every valuable query must touch a
content page and append to the log. That write-back is what makes the brain compound.

These operations are also published as skills (`kb-ingest`, `kb-query`, `kb-dream`,
`kb-session-capture`) in `skills/` — load the matching skill when triggered.

## Skills

`skills/` is the single source of truth for skills shared across agents — the same
way this schema is the source of truth for KB conventions.

### Registry

| Skill ID | Purpose |
|---|---|
| `kb-ingest` | Ingest a source into the brain |
| `kb-query` | Answer a question from the brain with citations |
| `kb-dream` | Run the Dream Sequence (lint / health check) |
| `kb-session-capture` | Save chat takeaways into the brain |
| `kb-weekly-review` | Weekly maintenance report (tags, orphans, duplicates, backlog) |
| `kb-update` | Update profile/goals/problems when the user's context changes (change log + cascade) |
| `kb-plan` | Gated 6-phase workflow for building brain features |
| `kb-skill-add` | Meta-skill: how to add a new shared skill |
| `onboard` | Guided setup: focus, favorite problems, goals, first seeds |

Agent definitions (subagents) live in `agents/` — see the **Delegation &
Subagents** section for authority boundaries. `kb-digest` and `kb-linter`
are read-only brain agents; `researcher`, `code-reviewer`, `bug-fixer`,
`implementer` are general dev agents.

### How agents discover them

- **OpenCode**: `skills: ["{{WORKSPACE_DIR}}/skills"]` in `~/.config/opencode/opencode.json`
- **Claude Code**: `~/.claude/skills/second-brain` symlink → `{{WORKSPACE_DIR}}/skills`
- **Other agents**: read the relevant `SKILL.md` directly (paths are absolute)

### Skill conventions

- Skill ID = directory name: lowercase kebab-case, unique, brain skills prefixed `kb-`.
- Every `SKILL.md` has `name` + `description` frontmatter; the description contains the
  trigger phrases users actually say.
- Skill bodies use absolute paths and reference this schema as the source of truth.
- Adding a skill: use the `kb-skill-add` skill, then add a row to this registry.

## Delegation & Subagents

The main session is persistent; subagents are ephemeral — they run one task and
terminate. All continuity and bookkeeping is the main session's responsibility.

### Agent definitions

Installed in `agents/` (wired into Claude Code via `~/.claude/agents/` symlinks):

| Agent | Type | Purpose |
|---|---|---|
| `kb-digest` | brain, read-only | Digest a long raw source → structured ingest proposal |
| `kb-linter` | brain, read-only | Sweep the whole KB → structured lint findings |
| `researcher` | dev, read-only | Explore codebases/docs/web → structured findings |
| `code-reviewer` | dev, read-only | Review diffs for bugs/security/style/test gaps |
| `bug-fixer` | dev, writes code | Reproduce → root-cause → fix + tests |
| `implementer` | dev, writes code | Implement features from a plan/spec |

### Authority boundaries

| Action | Brain agents (kb-*) | Dev agents |
|---|---|---|
| Read brain files | Yes | Yes |
| Read user's project files | Yes | Yes |
| Write/edit brain content (`raw/pages/`, `wiki/`, `knowledge/`) | **No — propose only** | No (they work on user's projects) |
| Write code in user's projects | n/a | Yes |
| Git commit | **Never** | Never — report files changed, main session commits |
| Git push | **Never** (guard blocks it inside the brain) | Never for the brain; per project rules otherwise |
| Architectural / schema decisions | No — report options | No — report options |

**The core rule: subagents propose, the main session applies.** One writer
(the main session) keeps frontmatter discipline, index updates, and the log
consistent — this is what makes the conflict-resolution protocol rarely needed.

### Task framing

1. One task, one outcome — a subagent finishes in one run or reports `blocked`.
2. Acceptance criteria in the prompt ("Done when: …").
3. Context is cheap, ambiguity is expensive — include paths, conventions,
   relevant knowledge-file context. Subagents have no memory of prior tasks.
4. Never re-delegate the same failed task unchanged.

### When to delegate

- Bulk reading that would flood main context (long-source ingest → `kb-digest`)
- Full-KB sweeps (dream/weekly lint → `kb-linter`)
- Independent parallel work (several inbox files at once)
- Code review / implementation in the user's projects (dev agents)

### Knowledge flow

Subagents never write to `knowledge/` or `raw/pages/`. Their structured output
flows back to the main session, which applies changes through the standard
operations (ingest, dream, update) — so every write lands with proper
frontmatter, index entry, and log line.

## Conflict Resolution

If a page's `updated` date has changed since the agent last read it, the page was
modified by another agent or the user. Protocol:

1. Re-read the page from disk.
2. Merge your changes into the latest version.
3. If the merge is ambiguous, add a `## ⚠️ Merge Note` section at the bottom explaining
   the conflict and your resolution.
4. Update the `updated` date in frontmatter.

## Git Policy

The knowledge base is a **local-only** git repository. No remote is configured and
must never be added. Commits stay on this machine.

### Conventional Commits (required)

All commits use [Conventional Commits](https://www.conventionalcommits.org)
format: `type: description` (imperative mood, no trailing period, ≤72 chars).

| Type | Used for | Example |
|---|---|---|
| `feat` | New knowledge or capability: ingests, new pages, new skills | `feat: ingest karpathy llm wiki` |
| `docs` | Recorded knowledge: query answers filed back, session notes, profile/goal/problem updates | `docs: session standup decisions` |
| `chore` | Maintenance: dream runs, onboarding, config, setup | `chore: dream 2026-10-14` |
| `fix` | Corrections to existing content (wrong claims, broken links, stale facts) | `fix: stale job title in profile` |
| `refactor` | Restructuring pages without changing meaning (splits, merges, moves) | `refactor: split ml topic into two pages` |

One type per commit; atomic commits per operation. **Never run `git push`** for
this repo unless the user explicitly asks. Backups are local (e.g. `git bundle`)
if needed — never to a public host.


## Automation (Dream Sequence)

The Dream Sequence runs on a schedule via cron (installed at setup):

- Runner script: `.overmind/dream-cron.sh` (headless agent invocation)
- Logs: `.overmind/logs/dream-YYYY-MM-DD.log`
- Schedule recorded in `.overmind/config.yaml` → `dream.schedule`, `dream.runner`
- Current schedule: see the `# second-brain-dream` block in `crontab -l`

When running unattended, the agent must still follow this schema, load the
`kb-dream` skill, and commit locally. The runner never pushes. After each run,
`dream.last-run` in config.yaml is updated. Test the wiring anytime with
`.overmind/dream-cron.sh --dry-run`. If the schedule misses (machine off), trigger
manually with "dream sequence" — same flow.

## MCP Resource Map

See `.overmind/mcp-resource-map.yaml` for MCP resource URI templates. MCP access is
an optional acceleration, not a requirement — any agent can read the files directly.
