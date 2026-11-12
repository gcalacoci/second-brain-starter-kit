#!/usr/bin/env python3
"""UserPromptSubmit hook: warn the user (and the model) as the session's context grows.

Every message re-reads the whole context, so a long session burns the plan's limit fastest.
Tiers (thousands of tokens) come from CONTEXT_WARN_TIERS="notice,warning,critical", default
"100,140,170" for a 200k window; with a 1M window try "200,250,400". The status line reads
the same variable. notice and warning fire once each, critical on every prompt.
Context = input + cache_read + cache_write of the last main-thread API response; right
after a /compact there is none yet, so the hook stays quiet until the next reply.

Save requests ("save session", "save everything", "save point", ...) also get the "Learned"
step and the transcript candidates from <brain>/.overmind/learned.py.
Live sessions only (not claude -p); never blocks the prompt.
"""
import json
import os
import sys

KB_ROOT = "{{KB_DIR}}"
STATE = os.path.expanduser("~/.claude/state/context-warn")


def tiers():
    raw = os.environ.get("CONTEXT_WARN_TIERS") or "100,140,170"
    try:
        n, w, c = (int(float(x) * 1000) for x in raw.split(","))
    except ValueError:
        n, w, c = 100_000, 140_000, 170_000
    return [(c, "critical"), (w, "warning"), (n, "notice")]


def context_size(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 4_000_000))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        if '"compact_boundary"' in line:
            return None  # compacted since the last reply: the old usage no longer applies
        if '"usage"' not in line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("type") != "assistant" or r.get("isSidechain"):
            continue
        u = (r.get("message") or {}).get("usage") or {}
        return sum(u.get(k) or 0 for k in
                   ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return None


def main():
    if os.environ.get("CLAUDE_CODE_ENTRYPOINT") not in ("cli", "claude-desktop"):
        return
    data = json.load(sys.stdin)
    learned = save_step(data)
    size = context_size(data.get("transcript_path") or "")
    if not size:
        emit(None, learned)
        return
    tier = next((name for limit, name in tiers() if size >= limit), None)
    os.makedirs(STATE, exist_ok=True)
    state = os.path.join(STATE, data.get("session_id") or "unknown")
    try:
        last = open(state).read().strip()
    except OSError:
        last = ""
    with open(state, "w") as f:
        f.write(tier or "")
    if tier is None or (tier == last and tier != "critical"):
        emit(None, learned)
        return
    k = round(size / 1000)
    user = {
        "notice": f"Context at {k}k tokens: every message re-reads all of it. Good moment for a save point.",
        "warning": f"⚠ CONTEXT {k}k TOKENS. Each message now costs ~{k}k. Save state to disk, then /compact or start a new session.",
        "critical": f"⛔ CONTEXT {k}k TOKENS. Every message burns ~{k}k of your limit. Save state and /compact or start a new session NOW.",
    }[tier]
    model = {
        "notice": f"Context is {k}k tokens. Mention it in one line at the end of your reply and suggest a save point if a task just finished.",
        "warning": f"Context is {k}k tokens. Start your reply with a one-line warning. Offer to write the current state to disk (session note, memory) so the user can /compact or start a new session safely.",
        "critical": f"Context is {k}k tokens. Start your reply with a warning. Before more work, propose saving state to disk and compacting or starting a new session; continue only if the user insists.",
    }[tier]
    emit((user, model), learned)


def save_step(data):
    """The "Learned" step + transcript candidates when the prompt asks for a save."""
    try:
        sys.path.insert(0, os.environ.get("LEARNED_DIR") or os.path.join(KB_ROOT, ".overmind"))
        import learned
        if not learned.is_save_request(data.get("prompt", "")):
            return None
        path = data.get("transcript_path") or ""
        cands = learned.render(learned.candidates(learned.records(path))) if path else "(no transcript)"
        return learned.STEP + cands
    except Exception:
        return None


def emit(warn, learned):
    if not warn and not learned:
        return
    out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                  "additionalContext": "\n\n".join(
                                      x for x in ((warn or (None, None))[1], learned) if x)}}
    if warn:
        out["systemMessage"] = warn[0]
    print(json.dumps(out))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
