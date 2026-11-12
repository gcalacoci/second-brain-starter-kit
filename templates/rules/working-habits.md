---
name: Working habits
---

# Working habits — all projects, all sessions

Edit freely: these are defaults that worked in a daily-use brain. Add the date when you
set or change a habit, so later sessions know how current it is.

## Talking to the user
- **Full absolute paths** for every file mentioned, never relative or bare names. No
  punctuation right after a path: end the sentence before it or put the path last on its
  line, so the path stays clickable and copy-safe.
- **Explain commands:** for every command given to the user, one line per command or key
  flag: what it does, what to expect, any risk.
- **Warn before slow runs:** say in one line that it takes minutes, or run it in the
  background.
- **Saving before compact/clear** ends with a ready-to-paste resume prompt in a code block:
  topic, session-note path, open items in priority order with key paths, what to check
  first (`git status`). Short; the session note has the details.
- **Every save has a "Learned" step** before the resume prompt: list what the session
  learned beyond its decisions (tool quirks, working endpoints, sources that mislabel, user
  corrections), each with a reason and a destination page; no page fits → create one,
  link it, index it; write them all; end with "nothing else learned". Disk is cheap: never
  skip a write to save tokens.

## How to work
- **Two tracks:** finish the task, then propose in one line at most one change that makes
  the next similar task cheaper or safer (a recipe, script, rule, template field); never
  build it unasked.
- **Prior art first** for work over ~1 h, or that needs maintenance or runs unattended: a
  time-boxed search (~15 min) for existing tools; rate up to 3 candidates (maintained,
  license, dependencies, security: read the code); choose adopt / build on top / build
  from scratch / drop; record the decision with its date in the brain (also "nothing
  found"). Skip for small scripts.
- **Brain lookups:** search first (`qmd search "<keywords>" -n 5 --files` when qmd is
  installed, else `python3 scripts/kb-search.py "<keywords>"`), then read only the hits.
  grep only for exact strings in code.
- **Track every number** a job produces (cost, turns, counts, outcomes of crons and
  unattended runs) in a log or CSV, so later decisions rest on data.

## Git
- **Check which repo before any commit.** The brain repo: the agent commits its own
  changes, atomic per operation, Conventional Commits. Other repos: follow that repo's
  rules; if unsure, stage and hand the user a paste-ready commit command.
- **Shared working tree:** other sessions and crons may write the same tree. Run
  `git status` before each commit, stage only the files you changed (by path), never
  `git add -A` / `.`, never stash, reset or revert someone else's changes.
- **Never push** unless the user says so for that push. Rebase over merge; never rewrite
  pushed history.
- Commit message: Conventional Commits subject (imperative, ≤72 chars) plus a body that
  says what changed and why.

## Models and helpers
- **Subagents** when they save work (research, long digests, brain sweeps, review,
  parallel independent items); skip when spawning costs more than doing it. Subagents
  propose, the main session writes the brain; one task each, with a "Done when:" line
  and full paths.
- **Cheapest model that does the job:** smaller models for mechanical steps, the larger
  one for judgement. Always set the model explicitly for subagents and headless runs.

## Token economy
1. One topic per session; on a topic change: session note + resume prompt, fresh session.
2. Compact at a fixed context size you pick (the status line shows it), not on a guess.
3. Web and repository searches go to a helper that returns only the answer.
4. Small outputs: scripts print counts and heads; never print the same thing twice.
5. Batch calls: one call or script for several items.
6. Just in time: only what is needed today or the next working day.
7. Read once per session (SCHEMA, session notes); read slices, not whole files.
