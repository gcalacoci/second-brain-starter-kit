#!/usr/bin/env python3
"""Save-point candidates from a session transcript: what the session may have learned.

Why: sessions find working endpoints, fix failing commands and get corrected by the user,
then save only their decisions; "save everything" often gets "actually there is more". The
session still reflects on its own; this adds what reflection misses: URLs that answered,
commands that failed and then worked, and the user's own words (corrections). Since the last
/compact only.

    python3 -I learned.py <transcript.jsonl>      print the candidates (capped)

Run by ~/.claude/hooks/context-warn.py when the user asks for a save (is_save_request).
"""
import json
import re
import sys

URL = re.compile(r"https?://[^\s'\"<>)]+")
FAILED = re.compile(r"\b(404|403|429|Not Found|Too Many Requests|Forbidden)\b")
SAVE = re.compile(
    r"(?:^|[.!?;,]\s+)\s*(?:(?:ok|okay|please|now|let'?s|go|and)[,.!]?\s+)*"
    r"(?:save\s+(?:this\s+|the\s+)?(?:session|everything|state|all)\b"
    r"|save\s+(?:for|before)\s+(?:the\s+)?compact"
    r"|save\s*point\b"
    r"|salva(?:re)?\s+(?:la\s+|lo\s+)?(?:sessione|tutto|stato))",
    re.I)


NOT_USER = ("<", "This session is being continued", "Another Claude session sent a message")


def is_save_request(prompt):
    return bool(SAVE.search(prompt or ""))


def records(path, tail=40_000_000):
    """Transcript records after the last compact boundary (main thread only)."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - tail))
        lines = f.read().decode("utf-8", "replace").splitlines()
    out = []
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("isSidechain"):
            continue
        if r.get("type") == "system" and r.get("subtype") == "compact_boundary":
            out = []
            continue
        if r.get("type") in ("assistant", "user"):
            out.append(r)
    return out


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
    return ""


def candidates(recs):
    uses, results, said = {}, {}, []
    order = []
    for r in recs:
        content = (r.get("message") or {}).get("content")
        if r["type"] == "assistant" and isinstance(content, list):
            for c in content:
                if c.get("type") == "tool_use":
                    uses[c["id"]] = (c.get("name"), c.get("input") or {})
                    order.append(c["id"])
        elif r["type"] == "user":
            if isinstance(content, list) and any(c.get("type") == "tool_result" for c in content if isinstance(c, dict)):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        results[c.get("tool_use_id")] = (bool(c.get("is_error")), _text(c.get("content")))
            else:
                t = _text(content).strip()
                if t and not t.startswith(NOT_USER) and "<cross-session-message" not in t and len(t.split()) >= 4:
                    said.append(" ".join(t.split())[:160])
    fetched, fixes, last_err = [], [], None
    for i in order:
        name, inp = uses[i]
        err, text = results.get(i, (False, ""))
        failed = err or bool(FAILED.search(text[:300]))
        if name == "WebFetch" and inp.get("url"):
            urls = [inp["url"]]
        elif name == "Bash":
            urls = URL.findall(inp.get("command", ""))
        else:
            urls = []
        if not failed:
            fetched += [u for u in urls if u not in fetched and "{" not in u and "$" not in u]
        if name == "Bash":
            cmd = " ".join(inp.get("command", "").split())[:140]
            if err:
                last_err = (cmd, " ".join(text.split())[:100])
            elif last_err:
                fixes.append(f"failed: {last_err[0]} ({last_err[1]}) -> worked: {cmd}")
                last_err = None
    return {"fetched": fetched, "fixes": fixes, "corrections": said}


def render(c, cap=20):
    labels = {"fetched": "URLs that answered (endpoints, boards, docs)",
              "fixes": "fixes (an error, then the command that worked)",
              "corrections": "the user's own words (look for corrections and preferences)"}
    out = []
    for key, label in labels.items():
        items = c.get(key) or []
        if not items:
            out.append(f"{key}: none")
            continue
        out.append(f"{key}: {label}")
        out += [f"  - {x}" for x in items[-cap:]]
        if len(items) > cap:
            out.append(f"  (+{len(items) - cap} more, oldest left out)")
    return "\n".join(out)


STEP = """SAVE POINT, "Learned" step (rules/working-habits.md). Before the resume prompt:
1. List what this session learned beyond its decisions: tool quirks, working endpoints and
   slugs, sources that mislabel, user corrections and preferences. Use the candidates below
   AND your own reflection (the script cannot see judgement).
2. Each item: one line with a reason and a destination (a project or topic page, a source
   page, memory or rules). No home fits: create one, link it, index it.
3. Write them. Token rules protect what is re-read into context, not disk: a 3-line note is
   cheap, rediscovering it costs rounds. Never skip a write "to save tokens".
4. End the list with "nothing else learned" stated explicitly.
Candidates from the transcript since the last compaction:
"""


def main(argv):
    if not argv:
        sys.exit(__doc__)
    print(render(candidates(records(argv[0]))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
