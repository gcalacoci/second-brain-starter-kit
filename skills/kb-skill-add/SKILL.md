---
name: KB Skill Add
description: Add a new shared skill to the Second Brain skill library at {{WORKSPACE_DIR}}/skills so all agents (Claude Code, OpenCode, others) can use it. Use when the user wants to teach the brain a new reusable workflow or says "add a skill".
---

# KB Skill Add

Add a new shared skill to the Second Brain skill library.

## Library location

`{{WORKSPACE_DIR}}/skills/` — the single source of truth for shared skills.

Agent discovery (already wired, do not re-do):
- **OpenCode**: `skills: ["{{WORKSPACE_DIR}}/skills"]` in `~/.config/opencode/opencode.json`
- **Claude Code**: `~/.claude/skills/second-brain` symlink → the library
- **Other agents**: tell them to read a `SKILL.md` from the library directly

## Steps

1. Confirm the skill's purpose and when it should trigger (this becomes the `description`).
2. Create `{{WORKSPACE_DIR}}/skills/<kebab-case-id>/SKILL.md` with frontmatter:
   ```yaml
   ---
   name: <Human Readable Name>
   description: <One sentence: what it does + when to use it>
   ---
   ```
3. Write the skill body: prerequisites, numbered steps, and rules. Use **absolute paths** to KB locations (`{{WORKSPACE_DIR}}/...`). Reference `SCHEMA.md` as the source of truth for conventions.
4. Put supporting files (templates, scripts, references) in subdirectories of the skill folder — paths inside the skill are relative to its directory.
5. ID rules: unique, lowercase kebab-case, 1-64 chars, matches the directory name. Prefix brain-specific skills with `kb-` to avoid collisions.
6. Update `SCHEMA.md` — add the skill to the skills registry table (name, ID, one-line purpose).
7. Commit: `git -C {{WORKSPACE_DIR}} add -A && git -C {{WORKSPACE_DIR}} commit -m "feat: add skill <skill id>"` — **local-only repo, never push.**

## Rules

- A skill is a *procedure*, not documentation — write imperative steps an agent can follow cold.
- The `description` must contain trigger phrases the user actually says ("use when the user says X").
- Keep skills agent-agnostic: no agent-specific tool names in the body unless unavoidable.
