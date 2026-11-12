#!/usr/bin/env python3
"""security-guard.py — Security guard for the Second Brain Starter Kit.

Defense-in-depth: secrets protection, path boundaries, destructive command
checks, and the brain's local-only guarantee.

Adapted from mp-web3/claude-starter-kit's global-guard.py (MIT), with these
additions: no git push from inside the Second Brain (the KB is local-only; push
is a deliberate user action in a terminal), no force-push anywhere, no
`commit --amend` and no skipped git hooks (the brain's pre-commit gate), Claude's
own credential file is off limits, unattended runs (claude -p) cannot change the
Claude config, and calendar invitations are never sent by an agent. Optional:
GUARD_CHEAP_SUBAGENTS=1 makes subagents name model sonnet or haiku.

Receives JSON on stdin: { "tool_name": "...", "tool_input": {...}, "cwd": "..." }
Exit 0 = allow, Exit 2 = block (stderr shown to the agent)
"""

import json
import os
import re
import shlex
import sys
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

HOME_DIR = str(Path.home())

# Brain root — substituted by setup.sh ({{KB_DIR}})
KB_ROOT = "{{KB_DIR}}"

SECRETS_RE = re.compile(r"\.(env|key|pem|secret|keystore)$|\.env\.", re.IGNORECASE)

WRITABLE_ROOTS = [HOME_DIR, str(Path("/tmp").resolve()), str(Path("/var/tmp").resolve())]
READABLE_ROOTS = WRITABLE_ROOTS + [str(Path("/usr/local").resolve()), str(Path("/opt/homebrew").resolve())]

PASSTHROUGH_TOOLS = {
    "WebSearch", "WebFetch", "AskUserQuestion",
    "TaskCreate", "TaskUpdate", "TaskList", "TaskGet",
}

# Claude Code's own login token: never read, copied or sent, whatever the command.
SECRET_FILES = ["~/.claude/.credentials.json"]

# The guard's own config. Unattended runs (claude -p from cron) must never change it;
# interactive sessions (entrypoint cli / claude-desktop) can.
CONFIG_PATHS = ["~/.claude/hooks", "~/.claude/rules", "~/.claude/settings.json",
                "~/.claude/settings.local.json", "~/.claude/statusline.py"]
HEADLESS = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "") not in ("cli", "claude-desktop")

# Opt-in (GUARD_CHEAP_SUBAGENTS=1): subagents must name a cheap model. No model means
# the parent's (often Opus), which burns the plan's limit fastest.
CHEAP_SUBAGENTS = os.environ.get("GUARD_CHEAP_SUBAGENTS") == "1"
CHEAP_MODELS = {"sonnet", "haiku"}
CHEAP_AGENT_TYPES = {"kb-linter"}  # their definition pins sonnet
MODEL_MARK = "[model-approved-by-user]"

# Calendar calls that would email an invitation to other people: always blocked.
CALENDAR_ATTENDEE_KEYS = {
    "mcp__claude_ai_Google_Calendar__create_event": ("attendees", "attendeeEmails"),
    "mcp__claude_ai_Google_Calendar__update_event": ("addedAttendees", "addedAttendeeEmails"),
}

READ_CMDS = {"cat", "head", "tail", "less", "more", "bat", "sed", "awk", "grep"}
DESTRUCTIVE_CMDS = {"rm", "rmdir", "mv", "cp", "touch", "mkdir", "chmod", "chown", "ln"}

SHELL_OP_RE = re.compile(r"\s*(?:&&|\|\||[;|])\s*")

GUARD_LOG = Path(os.environ.get("GUARD_LOG") or Path.home() / ".claude" / "state" / "guard-log.jsonl")


def log_block(tool: str, reason: str, context: str = "") -> None:
    """Append blocked tool call to the audit log."""
    try:
        entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tool": tool,
            "reason": reason,
        }
        if context:
            entry["context"] = context[:200]
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(GUARD_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # Never fail the guard because logging failed


def block(tool: str, reason: str, context: str = "") -> None:
    log_block(tool, reason, context)
    print(reason, file=sys.stderr)
    sys.exit(2)


# The agent's working directory (payload "cwd"), set in main(). Relative paths are
# the agent's, so they resolve against it, not against this hook's own process cwd.
AGENT_CWD = ""


def resolve(p: str) -> str:
    path = Path(os.path.expanduser(p))
    if not path.is_absolute() and AGENT_CWD:
        path = Path(AGENT_CWD) / path
    return str(path.resolve())


def inside(path: str, roots: list) -> bool:
    r = resolve(path)
    return any(r == root or r.startswith(root + "/") for root in roots)


def is_secrets(p: str) -> bool:
    if resolve(p) in {resolve(f) for f in SECRET_FILES}:
        return True
    return bool(SECRETS_RE.search(os.path.basename(p)))


def is_config(p: str) -> bool:
    return inside(p, [resolve(c) for c in CONFIG_PATHS])


def in_brain(p: str) -> bool:
    if not KB_ROOT or KB_ROOT.startswith("{{"):
        return False
    return inside(p, [resolve(KB_ROOT)])


def tokenize(cmd: str) -> list:
    try:
        return shlex.split(cmd)
    except ValueError:
        return cmd.split()


def looks_like_path(token: str) -> bool:
    return token.startswith("/") or token.startswith("~") or token.startswith(".")


GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def git_subcommand(tokens: list):
    """(subcommand, args) if these tokens run git, else None. git must be the
    command itself (after VAR=x assignments), so `echo git push` is not git.
    Skips git's global options (`git -C dir push`), so `git stash push` or a
    commit message containing "push" is not a push."""
    i = 0
    while i < len(tokens) and "=" in tokens[i] and not tokens[i].startswith("-") and tokens[i].index("=") > 0:
        i += 1
    if i >= len(tokens) or os.path.basename(tokens[i]) != "git":
        return None
    i += 1
    while i < len(tokens) and tokens[i].startswith("-"):
        i += 2 if tokens[i] in GIT_OPTS_WITH_VALUE else 1
    return (tokens[i], tokens[i + 1:]) if i < len(tokens) else None


GIT_VALUE_FLAGS = {"-m", "-F", "-c", "-C", "--message", "--file"}


def skips_hooks(args: list) -> bool:
    """--no-verify, or commit's short -n (alone or in a flag cluster)."""
    for i, a in enumerate(args):
        if i and args[i - 1] in GIT_VALUE_FLAGS:
            continue
        if a == "--no-verify" or re.fullmatch(r"-[a-zA-Z]*n[a-zA-Z]*", a):
            return True
    return False


# Heredoc fed to cat or tee: the body is file content, not commands.
HEREDOC_RE = re.compile(
    r"((?:^|[\n;&|])[ \t]*(?:cat|tee)\b[^\n]*?<<-?[ \t]*(['\"]?)(\w+)\2[^\n]*\n)"
    r"(.*?)(\n[ \t]*\3[ \t]*(?:\n|$))",
    re.S,
)


def strip_data_heredocs(cmd: str) -> str:
    """Drop the bodies of heredocs fed to cat/tee; keep every other heredoc."""
    return HEREDOC_RE.sub(lambda m: m.group(1) + m.group(5).lstrip("\n"), cmd)


# Shell token that names a file: strip quoting/substitution debris and curl's @file.
TOKEN_DEBRIS = "\"'`()$<>"


def path_in_token(t: str) -> str:
    t = t.split("=", 1)[1] if t.startswith("--") and "=" in t else t
    return t.strip(TOKEN_DEBRIS).lstrip("@")


def mentions_brain(cmd: str) -> bool:
    """The brain path as a whole path in the command, not as a prefix of a
    sibling folder (e.g. second-brain-starter-kit next to second-brain)."""
    if not KB_ROOT or KB_ROOT.startswith("{{"):
        return False
    return bool(re.search(re.escape(resolve(KB_ROOT)) + r"(?=$|[/\s'\";&|)])", cmd))


def is_force_push(args: list) -> bool:
    for a in args:
        if a.startswith("--force") or a.startswith("+"):
            return True
        if a.startswith("-") and not a.startswith("--") and "f" in a[1:]:
            return True
    return False


def check_bash(tool: str, cmd: str, cwd: str) -> None:
    cmd = strip_data_heredocs(cmd)
    # --- Git: no push from the brain (local-only), no force-push, no amend, no hook skips ---
    # Push covers: cwd inside the brain, `cd <brain> && git push`, `git -C <brain> push`
    for s in SHELL_OP_RE.split(cmd):
        git = git_subcommand(tokenize(s.strip()))
        if not git:
            continue
        sub, args = git
        if sub == "push":
            if (cwd and in_brain(cwd)) or mentions_brain(cmd):
                block(tool, "LOCAL-ONLY: The Second Brain repo must never be pushed. "
                            "Push is a deliberate manual action in your own terminal.", cmd)
            if is_force_push(args):
                block(tool, "SECURITY: Force-push is blocked", cmd)
        if sub == "commit" and "--amend" in args:
            block(tool, "SECURITY: git commit --amend is blocked; make a new commit", cmd)
        if skips_hooks(args) if sub == "commit" else "--no-verify" in args:
            block(tool, "SECURITY: skipping git hooks (--no-verify / -n) is blocked", cmd)

    # --- Claude's own credentials named in any command (cat, cp, curl -d @f, base64...) ---
    for t in tokenize(cmd):
        p = path_in_token(t)
        if looks_like_path(p) and resolve(p) in {resolve(f) for f in SECRET_FILES}:
            block(tool, "SECURITY: Cannot use secrets files in shell commands", cmd)
        if HEADLESS and looks_like_path(p) and is_config(p):
            block(tool, "SECURITY: unattended runs cannot touch the Claude config (hooks/rules/settings)", cmd)

    if re.search(r"git\s+add\s", cmd):
        if re.search(r"\.(env|key|pem|secret|keystore)\b|\.env\.", cmd, re.IGNORECASE):
            block(tool, "SECURITY: Cannot stage secrets files", cmd)

    for m in re.finditer(r">{1,2}\s*(/[^\s;|&>]+)", cmd):
        target = m.group(1)
        if target != "/dev/null" and not inside(target, WRITABLE_ROOTS):
            block(tool, "BOUNDARY: Redirect targets outside allowed directories", cmd)

    for subcmd in SHELL_OP_RE.split(cmd):
        subcmd = subcmd.strip()
        if not subcmd:
            continue

        tokens = tokenize(subcmd)
        if not tokens:
            continue

        cmd_idx = 0
        for i, t in enumerate(tokens):
            if "=" in t and not t.startswith("-") and t.index("=") > 0:
                continue
            cmd_idx = i
            break

        command = tokens[cmd_idx] if cmd_idx < len(tokens) else ""
        args = tokens[cmd_idx + 1:]

        if command in READ_CMDS:
            for arg in args:
                if arg.startswith("-"):
                    continue
                if looks_like_path(arg):
                    if not inside(arg, READABLE_ROOTS):
                        block(tool, "BOUNDARY: Shell read targets outside allowed directories", cmd)
                    if is_secrets(arg):
                        block(tool, "SECURITY: Cannot read secrets files via shell commands", cmd)

        if command in DESTRUCTIVE_CMDS:
            for arg in args:
                if arg.startswith("-"):
                    continue
                if looks_like_path(arg):
                    if not inside(arg, WRITABLE_ROOTS):
                        block(tool, "BOUNDARY: Destructive command targets outside allowed directories", cmd)

        if command == "tee":
            for arg in args:
                if arg.startswith("-"):
                    continue
                if looks_like_path(arg):
                    if not inside(arg, WRITABLE_ROOTS):
                        block(tool, "BOUNDARY: tee targets outside allowed directories", cmd)


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        sys.exit(0)  # Fail open — never brick a session on bad input

    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})
    cwd = data.get("cwd", "")
    global AGENT_CWD
    if isinstance(cwd, str) and os.path.isabs(cwd):
        AGENT_CWD = cwd

    if tool in ("Agent", "Task"):
        if CHEAP_SUBAGENTS:
            model = str(inp.get("model") or "").lower()
            kind = inp.get("subagent_type") or ""
            ok = (model in CHEAP_MODELS and kind != "fork") or (not model and kind in CHEAP_AGENT_TYPES)
            if not ok and MODEL_MARK not in str(inp.get("prompt", "")):
                block(tool, f"MODEL TIER: subagents run on sonnet or haiku (pass model). Other or "
                            f"unset models need the user's yes for this run; then put "
                            f"{MODEL_MARK} in the prompt.", f"{kind}/{model or 'unset'}")
        sys.exit(0)

    if tool in CALENDAR_ATTENDEE_KEYS:
        if any(inp.get(k) for k in CALENDAR_ATTENDEE_KEYS[tool]):
            block(tool, "SECURITY: calendar invitations are never sent by an agent. "
                        "Create the event without attendees and tell the user who to invite.", tool)
        sys.exit(0)

    if tool in PASSTHROUGH_TOOLS or tool.startswith("mcp__"):
        sys.exit(0)

    if tool in ("Grep", "Glob"):
        p = inp.get("path", "")
        if p and not inside(p, READABLE_ROOTS):
            block(tool, "BOUNDARY: Search outside allowed directories", p)
        sys.exit(0)

    if tool == "Read":
        p = inp.get("file_path", "")
        if p:
            if not inside(p, READABLE_ROOTS):
                block(tool, "BOUNDARY: Read outside allowed directories", p)
            if is_secrets(p):
                block(tool, f"SECURITY: Cannot read secrets file: {os.path.basename(p)}", p)
        sys.exit(0)

    if tool in ("Write", "Edit", "NotebookEdit"):
        p = inp.get("file_path", "") or inp.get("notebook_path", "")
        if p:
            if not inside(p, WRITABLE_ROOTS):
                block(tool, "BOUNDARY: Write outside allowed directories", p)
            if is_secrets(p):
                block(tool, f"SECURITY: Cannot write secrets file: {os.path.basename(p)}", p)
            if HEADLESS and is_config(p):
                block(tool, "SECURITY: unattended runs cannot edit the Claude config (hooks/rules/settings)", p)
        sys.exit(0)

    if tool == "Bash":
        cmd = inp.get("command", "")
        if cmd:
            check_bash(tool, cmd, cwd)
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
