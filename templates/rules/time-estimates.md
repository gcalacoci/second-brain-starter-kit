---
name: Time estimates
---

# Time estimates — all projects, all sessions

Applies to every estimate for work the agent, subagents or other models do: code, tests,
plans, research, writing, brain ingests.

- Count **tool-call rounds** (think → edit/write → run → read → fix), about **3 min each**.
  Minutes = rounds × 3. Never start from what a human would take.
- Parallel subagents: the slowest job sets the time, plus 1–2 rounds to review.
- Add rounds only for a named risk (unknown API, flaky environment, a page that may need a
  login), never "to be safe".
- Human-side time (the user reviewing, testing by hand) and waiting time (queues, long
  scans) are estimated separately and labelled as such.
- Say it in one line: "~4 rounds, ~12 min". No estimation tables.

Why: estimates that start from human effort come out 5–10× too high for agent work.
Method adapted from ZhangHanDong/agent-estimation (MIT), reduced to its unit and
conversion.
