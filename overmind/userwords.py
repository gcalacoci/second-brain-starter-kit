"""userwords: decide whether a transcript record was typed by the user.

A record counts only when it is a user message that is not meta, not a compact summary,
not a tool result, and either has origin kind "human" or (no origin) does not start with
a command or system-reminder tag. Peer relays and compact summaries quote the user
verbatim, so a plain grep over the transcript is never enough.

    python3 -I -m unittest discover -s tests -p 'test_userwords.py'
"""

COMMAND_PREFIXES = (
    "<command-",
    "<local-command-",
    "<bash-stdout",
    "<bash-stderr",
    "<system-reminder",
)


def user_text(record):
    """The user's text in a transcript record (text blocks joined by newlines)."""
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def is_user_typed(record):
    """True only when the record is a human-typed user message (not tool/meta noise)."""
    if record.get("type") != "user":
        return False
    if record.get("isMeta") or record.get("isCompactSummary"):
        return False
    content = (record.get("message") or {}).get("content")
    if isinstance(content, list) and any(
        isinstance(block, dict) and block.get("type") == "tool_result"
        for block in content
    ):
        return False
    text = user_text(record)
    if not text.strip():
        return False
    origin = record.get("origin")
    if origin is not None:
        return isinstance(origin, dict) and origin.get("kind") == "human"
    return not text.lstrip().startswith(COMMAND_PREFIXES)
