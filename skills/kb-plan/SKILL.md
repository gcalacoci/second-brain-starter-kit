---
name: KB Plan
description: Phase-wise build for the Second Brain. Use when building new features, large rollouts, or architectural changes. Follow the gates: Explore, Discover, Design, Approve, Implement, Verify.
allowed-tools: [Read, Write, Edit, Bash, Web, AskUserQuestion]
---

# /kb-plan — Second Brain Build Workflow

A gated, phased workflow for building changes to your Second Brain at {{WORKSPACE_DIR}}/. Starts small, expands safely.

---

## The 6 Phases

| Phase | Goal | Gate |
|---|---|---|
| **Explore** | Understand the need, scan existing KB | Pause for your input |
| **Discover** | Find existing knowledge, tools, patterns | Share findings |
| **Design** | Sketch the minimal change | Propose, get approval |
| **Approve** | You decide: GO, modify, or cancel | Explicit confirmation |
| **Implement** | Make the change (atomic commits) | Correctness + tests |
| **Verify** | Confirm the change works and docs are updated | Close the loop |

---

## Before Starting

Read these first:

- `SCHEMA.md` — Know the rules
- `skills/` — Use the correct skills (kb-ingest, kb-query, etc.)

---

## Usage

```

/kb-plan <what to build> [argument]
```

Examples:

- `/kb-plan create a github ingest skill`
- `/kb-plan add vector search support`
- `/kb-plan redesign the inbox workflow`

---

## Flow

### Phase 1: Explore

Ask the user one question at a time via `AskUserQuestion`:

> What's the problem you're trying to solve?

> What's the desired outcome?

> What would success look like?

Summarize. Write findings to `knowledge/projects/<slug>-explore.md`.

Checkpoint: commit with `plan: explore - <title>`.

### Phase 2: Discover

Search the brain and tools for relevant stuff:

- Scan `wiki/index.md`, `wiki/log.md`
- Look for existing patterns, similar pages
- Note any contradictions or gaps

Write to `knowledge/projects/<slug>-discover.md`.

Checkpoint commit.

### Phase 3: Design

Sketch the minimal design:

- What files need creating/editing?
- What frontmatter, tags, IDs?
- What skill(s) need updating?
- What's the fallback if this fails?

Propose. Show a design document.

### Phase 4: Approve

Wait for explicit "go". No timer-based moves.

If denied: iterate on the design.

If modified: re-design.

### Phase 5: Implement

Execute. Atomic commits per file, per operation.

- For new pages: process frontmatter properly
- For skill changes: update schema
- For structural changes: document in LEARNINGS.md

### Phase 6: Verify

- Test the workflow
- Update README/indexes as needed
- Run skills that might be affected

Final commit: `plan: complete - <title>`.

---

## Rules

- Always commit after each phase (checkpoint)
- Local-only git, no remote
- Reference SCHEMA.md for conventions
- If you need to create supporting files (scripts, docs), mention in Design phase

## Completion

When done, you'll have a new capability in the Second Brain, with commits marking progress and documentation of what worked.

---

Tip: For simple changes, the workflow can skip Explore/Discover and go straight to Design:Approve:Implement.