---
name: Safety
---

# Safety habits — all projects, all sessions

- **Delete into the trash, not into the void:** `trash <path>` (trash-cli: `trash-list`,
  `trash-restore`) instead of `rm -f` / `rm -rf`, also in commands given to the user.
  Session scratch files are fine to remove. Never delete a file the user provided without
  their OK.
- **A question is not a go.** "Can we X?" / "Is it possible…?" gets an answer and a plan;
  no edits, staging or system changes until the user says "go" / "do it".
- **No polling long jobs.** For backups, upgrades and remote jobs, start one background
  waiter and wait for its notification; check by hand only if the user asks or the job runs
  past its stated estimate.
- **Python dependencies through uv** (`uv run --with …`, `uv tool install`); never pip into
  the system Python, never sudo installs.
- **Sensitive files** (`.env`, keys, credentials): warn the user before editing; never
  commit them; never print their values.
