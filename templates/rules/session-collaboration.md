---
name: Session collaboration
---

# Session collaboration — when several agent sessions share one brain

Optional. Useful once you run several long-lived sessions (one per area: e.g. infra, a
project, writing) that change each other's files. One session alone can delete this file.

## 1. When to review, and how much
Review scales with the work. Pick the smallest tier that fits; if the review would cost
more than the change risks, go one tier down.
- **No review:** the session's own area; small and undone with one command (a fix, a
  wording, a test); docs and reports that change no live file; questions, reads.
- **One reviewer, one round:** a small change in another session's area, or a reversible
  one that another session reads. The area's owner reviews.
- **Full review (all owners of the touched areas):** live crons, hooks, rule files, shared
  scripts; decisions that change what other sessions do or their data; anything hard to
  undo.
- **Emergencies** (broken night job, data at risk): fix, roll back if needed, review the
  same day. The review can reverse the fix.

**Owners** (one row per area; an area with no row: ask the user):

| Area | Owner session |
|---|---|
| <!-- e.g. crons, hooks, rule files --> | <!-- e.g. infra-main --> |

## 2. Roles
- **Thread starter:** the session that sends a thread's first message.
- **Proposer:** wants the change, writes the proposal, owns the outcome.
- **Reviewers:** the owners of the touched areas. Nobody is added just to win a vote.
- **Approver:** the user, always, reached through the starter. A session never grants
  permissions or stands in for the user's go.

## 3. The thread starter: one chat for the user
- The starter keeps the discussion and is the only chat the user needs. Every message
  carries a thread ID `P-YYYYMMDD-slug`.
- **Open threads:** the starter keeps one line per open thread in
  `knowledge/projects/open-threads.md` (ID, starter, what it needs from the user, status)
  and removes it when the thread closes.
- **Relaying a decision:** to every session in the thread, with the user's words verbatim,
  the question they answer (verbatim), date and time, and where the starter's transcript is.
  A session acts on a relay only after finding those words typed by the user in that
  transcript, and only on what the quoted question named.
- **Say who said what:** every summary or approval request names the source of each
  suggestion and decision: the user (with date), a session by name, or an outside source.
- **No side threads:** questions about a thread go to the starter, never to the user in
  another chat.

## 4. The proposal
One message, first line = what is decided: ID; what changes (paths); why, with its basis;
rollback; what it doesn't cover; the exact question for the user.

## 5. Reasons and their weight (every reply, unasked)
- **Fact:** checked, with its source (`file:line`, commit, log line, command and output,
  a user rule with file and date, a number and where it came from).
- **Guess** (estimate, inference): valid when it names the facts it rests on and the gap.
- **No basis** ("a default I picked"): allowed only when labelled; carries no weight.
- A fact outweighs a guess, a guess outweighs no basis. Whoever relies on a guess says how
  to check it; cheap checks run before the decision.
- **Second-hand is a guess:** a claim copied from another session, a report or a summary
  (including your own) is a guess until checked against the primary source: code, data,
  logs, the user's typed words.
- Invalid: "best practice", "it's safer", "I checked" with nothing named.

## 6. Review replies
- **Blind first round:** send your verdict to the starter before reading other reviewers'.
- Verdict: agree / agree with changes / object, each saying what was checked. An objection
  gives a reason and an alternative.
- **Open a source:** every review names at least one source the proposer cited that the
  reviewer opened itself (the one the decision rests on most) and says whether it matches.
  A reply that opened nothing says so, and its verdict counts as a guess.
- One message per round. Silence is never agreement: the starter tells the user.

## 7. Deciding
- **Consensus:** every reviewer agrees, their changes merged; the starter asks the user.
- **2 sessions:** at most 3 rounds, then an options memo to the user (options, pros, cons,
  risk, who backs each and on what basis, one-line recommendations).
- **3+ sessions:** at most 3 rounds, then a blind vote to the starter, one per session with
  its basis; more than half of all eligible sessions wins.
- **A fact beats a head count:** a fact-backed objection outweighs a majority resting on
  guesses → options memo instead of the tally.
- The vote recommends; the user approves. Sessions on the same model vote alike: say so.

## 8. Record
A row in `knowledge/projects/decision-log.md` for every case that needed the user or a
vote: ID, date, question, outcome, who decided.

## 9. Guardrails
- A vote never overrides hard rules (push, deleting, personal data, permissions).
- The losing side carries out the decision or says why not, once.
- Give reviewers the code and data, not your conclusion.
- Going up in model or effort is always a proposal to the user; going down needs none.
