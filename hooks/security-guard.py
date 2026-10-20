#!/usr/bin/env python3
"""security-guard.py — Security guard for the Second Brain Starter Kit.

Defense-in-depth: secrets protection, path boundaries, destructive command
checks, and the brain's local-only guarantee.

Adapted from mp-web3/claude-starter-kit's global-guard.py (MIT), with one
addition: ALL git push is blocked when working inside the Second Brain
(the KB is local-only; push must be a deliberate user action in a terminal).

Receives JSON on stdin: { "tool_name": "...", "tool_input": {...}, "cwd": "..." }
Exit 0 = allow, Exit 2 = block (stderr shown to the agent)
"""

import json
import os
import re
import shlex
import sys
from datetime import datetime, timezone
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

READ_CMDS = {"cat", "head", "tail", "less", "more", "bat", "sed", "awk", "grep"}
DESTRUCTIVE_CMDS = {"rm", "rmdir", "mv", "cp", "touch", "mkdir", "chmod", "chown", "ln"}

SHELL_OP_RE = re.compile(r"\s*(?:&&|\|\||[;|])\s*")

GUARD_LOG = Path.home() / ".claude" / "state" / "guard-log.jsonl"


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
    return bool(SECRETS_RE.search(os.path.basename(p)))


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


def git_push_args(tokens: list):
    """The arguments after `push` if these tokens run `git push`, else None.
    Skips git's global options (`git -C dir push`), so `git stash push` or a
    commit message containing "push" is not a push."""
    if "git" not in tokens:
        return None
    i = tokens.index("git") + 1
    while i < len(tokens) and tokens[i].startswith("-"):
        i += 2 if tokens[i] in GIT_OPTS_WITH_VALUE else 1
    if i < len(tokens) and tokens[i] == "push":
        return tokens[i + 1:]
    return None


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
    # --- Brain local-only guarantee: no push from inside the brain, ever ---
    # Covers: cwd inside the brain, `cd <brain> && git push`, `git -C <brain> push`
    pushes = [a for a in (git_push_args(tokenize(s.strip())) for s in SHELL_OP_RE.split(cmd))
              if a is not None]
    if pushes:
        if (cwd and in_brain(cwd)) or mentions_brain(cmd):
            block(tool, "LOCAL-ONLY: The Second Brain repo must never be pushed. "
                        "Push is a deliberate manual action in your own terminal.", cmd)
        if any(is_force_push(a) for a in pushes):
            block(tool, "SECURITY: Force-push is blocked", cmd)

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
        sys.exit(0)

    if tool == "Bash":
        cmd = inp.get("command", "")
        if cmd:
            check_bash(tool, cmd, cwd)
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
