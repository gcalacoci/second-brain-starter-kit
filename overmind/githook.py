#!/usr/bin/env python3
"""Git hooks for the brain: pre-commit and commit-msg gates.

pre-commit: no private/ or secret files, raw/sources/ is append-only, no secret content,
brain_lint --staged passes. commit-msg: refuses AI-assistant trailers (Co-Authored-By:
Claude, Claude-Session:, "Generated with Claude Code") only when you opt in with
`git config brain.blockAiTrailers true`.
"""
import re
import subprocess
import sys
from pathlib import Path

SECRET_NAME = re.compile(
    r"^(?:\.env(?:\..*)?|.*\.pem|.*\.key|id_rsa.*|id_ed25519.*|id_ecdsa.*|"
    r"credentials\.json|\.credentials\.json|.*\.secret)$")
SECRET_CONTENT = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
    r"|sk-ant-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|AKIA[A-Z0-9]{16}|xox[abprs]-[A-Za-z0-9-]{10,}")
TRAILER = re.compile(
    r"^co-authored-by:.*(?:claude|anthropic)|^claude-session:"
    r"|generated with .*claude code", re.IGNORECASE)


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def repo_root():
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip())


def sources(path):
    return path == "raw/sources" or path.startswith("raw/sources/")


def staged_entries(root):
    """[(status, old, new)] for the staged diff, renames detected."""
    entries = []
    for line in git(root, "diff", "--cached", "--name-status", "-M").stdout.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status = fields[0][:1]
        move = len(fields) >= 3 and status in ("R", "C")
        entries.append((status, fields[1], fields[2] if move else fields[1]))
    return entries


def added_lines(root):
    """[(path, line)] for added content lines in the staged diff."""
    current, lines = None, []
    for line in git(root, "diff", "--cached", "-U0").stdout.splitlines():
        if line.startswith("+++ "):
            current = line[4:].strip()
            if current.startswith("b/"):
                current = current[2:]
            elif current == "/dev/null":
                current = None
        elif line.startswith("+") and current:
            lines.append((current, line[1:]))
    return lines


def check_staged(root):
    entries, problems, seen = staged_entries(root), [], set()
    for status, old, new in entries:
        for path in dict.fromkeys((old, new)):
            if path == "private" or path.startswith("private/"):
                problems.append(f"{path}: staged path under private/")
            if SECRET_NAME.match(path.rsplit("/", 1)[-1]):
                problems.append(f"{path}: secret file name")
        if status == "A":
            continue
        if status in ("M", "D", "T") and sources(new):
            problems.append(f"{new}: raw/sources/ is append-only ({status})")
        elif status == "R" and (sources(old) or sources(new)):
            problems.append(f"{old}: raw/sources/ is append-only (renamed)")
        elif status == "C" and sources(old):
            problems.append(f"{old}: raw/sources/ is append-only (copied)")
    for path, line in added_lines(root):
        if path not in seen and SECRET_CONTENT.search(line):
            seen.add(path)
            problems.append(f"{path}: secret content")
    return problems


def trailers_blocked(root):
    value = git(root, "config", "--bool", "brain.blockAiTrailers").stdout.strip()
    return value == "true"


def lint_staged(root):
    lint = Path(__file__).resolve().parent / "brain_lint.py"
    result = subprocess.run([sys.executable, "-I", str(lint), "--root", str(root), "--staged"],
                            capture_output=True, text=True)
    return result.stdout + result.stderr if result.returncode else ""


def main(argv):
    root = repo_root()
    if not argv or root is None:
        print("brain gate: missing hook name or not a git repository", file=sys.stderr)
        return 1
    if argv[0] == "pre-commit":
        problems, lint_output = check_staged(root), lint_staged(root)
        for problem in problems:
            print(f"brain gate: {problem}", file=sys.stderr)
        if lint_output:
            sys.stderr.write(lint_output)
        return 1 if problems or lint_output else 0
    if argv[0] == "commit-msg" and len(argv) >= 2:
        if not trailers_blocked(root):
            return 0
        try:
            text = Path(argv[1]).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"brain gate: cannot read commit message: {exc}", file=sys.stderr)
            return 1
        found = [line.strip() for line in text.splitlines() if TRAILER.search(line)]
        for line in found:
            print(f"brain gate: Claude trailer in commit message: {line}", file=sys.stderr)
        return 1 if found else 0
    print("brain gate: usage: githook.py pre-commit | commit-msg <message-file>",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
