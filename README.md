# Second Brain Starter Kit

A multi-agent, local-first personal knowledge base based on Andrej Karpathy's
[LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
Works with Claude Code, OpenCode, and any LLM agent that can read markdown files.

Clone, run `./setup.sh`, open your agent in the created workspace, and run
`/onboard`. Your brain grows smarter every time you use it.

## Why This Exists

Most note systems rot. You write something in March, something else in June,
and by October you can't reconstruct what you know. This kit flips the model:

- **The LLM maintains the wiki, you curate it.** Summarizing, cross-referencing,
  filing, bookkeeping — that's the agent's job.
- **Knowledge compounds.** Every source you ingest and every valuable answer gets
  filed back as pages, so queries get better over time.
- **Plain markdown, no lock-in.** Folders and files, readable in any editor,
  version-controlled with git, browsable in Obsidian.
- **Multi-agent by design.** One shared schema + shared skill library; Claude Code,
  OpenCode, or any other agent can operate the same brain.

## Documentation

| File | Audience | Purpose |
|---|---|---|
| `README.md` | Everyone | Overview, quick start, architecture |
| `MANUAL.md` | **You** (the user) | Complete command reference, workflows, troubleshooting |
| `AGENT-PROMPT.md` | **Agents** | Paste-at-session-start prompt that loads the brain |
| `SCHEMA.md` | Agents (generated) | The operating manual installed into the workspace |

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/second-brain-starter-kit.git
cd second-brain-starter-kit
./setup.sh
```

The script asks for your name and where to put the workspace
(default: `~/prj/second-brain`), then:

1. Creates the workspace: `raw/`, `wiki/`, `skills/`, `inbox/`, `outputs/`, `knowledge/`, `scripts/`
2. Installs the shared schema (`SCHEMA.md`), the skill library, and the utility scripts
3. Wires agent discovery: OpenCode `skills` config entry + one Claude Code symlink per skill
4. Optionally registers the MCP server in Claude Desktop and/or Claude Code (needs uv)
5. Initializes a **local-only** git repo (your knowledge never leaves the machine
   unless you explicitly add a private remote)

Then start your first session:

```bash
cd ~/prj/second-brain
claude   # or: opencode
```

Type `/onboard` — a guided 15-20 minute setup that captures your focus, your
Feynman-style favorite problems, your goals, and seeds the brain with starter
content. Progress is checkpointed to disk after every step, so you can pause
and resume anytime.

## Daily Use — 4 Commands

These are in `MANUAL.md` with full details. Quick version:

| You say | What happens |
|---|---|
| `add this` + a link/file/text | Agent ingests it: raw copy saved, pages created/updated, index + log updated |
| `what do I know about ___` | Agent reads the index, synthesizes an answer with citations |
| `save that` | The current answer becomes a new topic page — the brain compounds |
| `dream sequence` | Scheduled or on-demand lint: ingests new inbox files, finds contradictions, orphans, stale claims |

Plus: `save this session` (capture chat takeaways), `weekly review`
(freeform health check), `update my profile` (context changed), `/onboard`
(redo guided setup).

**Hands-off mode:** say yes during `./setup.sh` and the Dream Sequence schedules
itself via cron (weekly by default) — the brain tidies itself even when you forget
it exists. See `MANUAL.md` → Automation.

## Architecture

```
~/prj/second-brain/
├── SCHEMA.md            ← the operating manual every agent reads first
├── inbox/               ← quick capture; processed weekly by the dream sequence
├── raw/
│   ├── sources/         ← immutable raw dumps (never edited after saving)
│   ├── session-notes/   ← captured conversation takeaways
│   └── pages/           ← THE BRAIN'S CONTENT
│       ├── topics/      ← concept pages
│       ├── entities/    ← people, orgs, products
│       └── sources/     ← one summary page per ingested source
├── wiki/                ← navigation + bookkeeping only (index, log, processed)
├── outputs/             ← finished briefings, reports, summaries
├── knowledge/           ← meta-knowledge: profile, problems, goals (from /onboard)
├── skills/              ← shared skill library (ingest, query, dream, onboard, ...)
└── .overmind/           ← config + MCP resource map
```

Three layers: **raw sources** (immutable truth) → **wiki pages** (LLM-maintained
synthesis) → **index** (what the agent reads first to navigate).

## Multi-Agent Setup

The same brain is operated by any agent:

| Agent | How it finds the brain | How it finds the skills |
|---|---|---|
| **Claude Code** | `~/prj/CLAUDE.md` shim → `SCHEMA.md`; `~/.claude/rules/second-brain-rules.md` | one `~/.claude/skills/<skill-id>` symlink per skill |
| **OpenCode** | `~/.opencode/instructions.md` shim → `SCHEMA.md` | `skills: ["~/prj/second-brain/skills"]` in `~/.config/opencode/opencode.json` |
| **Any other agent** | "Read `~/prj/second-brain/SCHEMA.md` and follow it" | Read a `SKILL.md` directly |

`setup.sh` wires all of this automatically and tells you what it changed.

The rules file loads in every Claude Code session, wherever you start it. Its text
limits it to the workspace; a `paths:` glob can't, because for user-level rules Claude
Code matches it against the folder the session started in.

## Skills Included

| Skill | Purpose |
|---|---|
| `kb-ingest` | Ingest a source: raw copy, summary page, topic/entity updates, index, log |
| `kb-query` | Answer from the brain with citations; optionally file the answer back |
| `kb-dream` | The Dream Sequence: ingest new files + full lint (contradictions, orphans, stale) |
| `kb-session-capture` | Save chat takeaways as structured session notes |
| `kb-auto-session` | Capture pending sessions flagged by the Stop hook (or run by the Dream Sequence) |
| `kb-weekly-review` | Weekly maintenance report: vague tags, duplicates, orphans, inbox backlog, memory audit |
| `kb-update` | Update profile/goals when your context changes (change log + cascade) |
| `kb-plan` | Gated 6-phase workflow for building brain features (explore → verify) |
| `kb-skill-add` | Meta-skill: add a new shared skill correctly |
| `onboard` | Guided first-session setup: focus, 12 favorite problems, goals, seeds |

## Subagents Included

Installed in `agents/` and wired into Claude Code globally (`~/.claude/agents/`).
Brain agents are read-only — they propose, the main session applies (see SCHEMA.md → Delegation & Subagents).

| Agent | Type | Purpose |
|---|---|---|
| `kb-digest` | brain | Digest a long raw source (PDF, article) → structured ingest proposal, without flooding main context |
| `kb-linter` | brain | Sweep the whole KB → structured findings: contradictions, orphans, stale, missing pages |
| `researcher` | dev | Explore codebases/docs/web → structured findings (adapted from mp-web3/claude-starter-kit) |
| `code-reviewer` | dev | Review diffs for bugs, security, style, test gaps |
| `bug-fixer` | dev | Reproduce → root-cause → fix + tests |
| `implementer` | dev | Implement features from a plan/spec |

## When to Upgrade Search

The built-in `kb-search.py` (pure Python, zero deps, BM25 + recency + title/tag weighting) works perfectly up to ~200 pages. When you feel the limits, upgrade path:

| Scale | Recommended | How |
|---|---|---|
| 0–200 pages | Built-in `kb-search.py` (already works) | Zero deps, instant |
| 200–1000 | `qmd` (Karpathy's pick, MCP built-in) | `cargo install qmd && qmd index raw/pages` |
| 1000+ | Meilisearch | `docker run meilisearch` + MCP |
| Team / multi-user | Meilisearch Cloud / Typesense Cloud | Managed, auth, multi-tenant |

No search engine required until you feel the need — `kb-search.py` works out of the box.

## Git Policy

The knowledge base git repo is **local-only by default**. A safety hook blocks
`git push` for the brain. If you want an off-machine backup, create a **private**
repo and add it deliberately — never a public one.

## Requirements

- Git
- Python 3.10+ (for hooks and scripts)
- **uv** (recommended — `curl -LsSf https://astral.sh/uv/install.sh | sh`).
  Required for the MCP server, which is launched via
  `uv run --no-project --with "mcp>=1.2"` — uv resolves the `mcp` package on
  demand, no manual pip install needed.
- One or more agents: [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
  and/or [OpenCode](https://opencode.ai)
- Optional: [Obsidian](https://obsidian.md) for browsing the wiki (graph view is
  excellent for seeing the shape of your brain)

## Customization

- **Workspace location**: chosen during `./setup.sh` (default `~/prj/second-brain`)
- **Focus/scope**: re-run `/onboard` anytime to redefine what the brain is for
- **New skills**: say `add a skill` — the `kb-skill-add` skill walks the agent
  through creating it, registering it in `SCHEMA.md`, and wiring discovery
- **MCP access**: the Python MCP server (`scripts/mcp_server.py`, launched via
  uv) exposes 8 tools — `get_schema`, `get_index`, `search`, `read_file`,
  `list_files`, `list_by_tag`, `list_by_type`, `write_inbox` — see
  SCHEMA.md → MCP Server
- **One Claude Code memory for all folders** (optional): Claude Code keeps a
  separate auto-memory per start folder, so a fact saved in one project is missing
  in the next. Add `"autoMemoryDirectory": "~/.claude/memory"` to
  `~/.claude/settings.json` for one shared pool. Only the first 200 lines (25 KB) of
  `MEMORY.md` load at startup: keep it short, tag lines by track, move standing
  rules to `~/.claude/rules/`. The weekly review audits it.

## Merge Mode (re-running setup)

Re-running `./setup.sh` on an existing workspace is **non-destructive**: your
pages, sources and knowledge files are always kept. Where a kit file would
overwrite one you've edited, the new version is written next to yours as
`<file>.kit-new` and listed at the end of the run for you to merge manually.
Setup never stages or commits anything on your behalf — review with
`git -C <workspace> status` and commit what you want to keep.

## Roadmap

| Status | Item | Notes |
|---|---|---|
| ✅ | Core KB + 10 skills | Ingest, query, dream, session, update, plan, skill-add, auto-session, onboard, weekly-review |
| ✅ | 6 subagents (2 brain + 4 dev) | kb-digest, kb-linter, researcher, code-reviewer, bug-fixer, implementer |
| ✅ | Multi-agent wiring | OpenCode + Claude Code + generic AGENT-PROMPT |
| ✅ | Safety hooks | JSON guard, path boundaries, secrets, push block, audit log, pre-edit backup |
| ✅ | Automation | Cron dream sequence, dry-run, config tracking |
| ✅ | Auto-save session | Stop hook → pending markers → kb-auto-session |
| ✅ | Search (built-in) | kb-search.py — BM25 + recency, zero deps |
| ✅ | Media ingestion | PDF (pdftotext), DOCX (pandoc), audio/video (whisper) |
| ✅ | Batch ingest | inbox/ + media-to-text.sh |
| ✅ | Export / publish | kb-stats.py, kb-query briefings, outputs/ |
| ✅ | Telemetry | kb-stats.py dashboard (volume, hubs, problems, commits) |
| ✅ | Conventional Commits | Policy in SCHEMA, history rewritten, skills emit feat:/docs:/chore: |
| 🟡 | MCP server (Python, uv-launched) | `scripts/mcp_server.py` — register via setup Phase 2b |
| 🟡 | qmd / Meilisearch integration | Optional upgrade when search needs scale |
| 🟢 | Proactive profile refresh | Agent suggests /onboard refresh after 90 days |
| 🟢 | Rich media in Obsidian | raw/assets/ attachment folder + image download |
| 🟢 | Conflict resolution automation | Semantic diff + agent-assisted merge |
| 🟢 | Search skill UX | Dedicated skill with Open/Summarize actions |
| 🟢 | Growth metrics dashboard | Prettier kb-stats output |

---

## Credits

Built on Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
pattern, with onboarding and workflow ideas adapted from
[mp-web3/claude-starter-kit](https://github.com/mp-web3/claude-starter-kit).

## License

MIT
