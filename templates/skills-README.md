# Skills Library — Shared Reusable Workflows

This directory is the single source of truth for skills shared across agents.

## Discovery

- OpenCode: `skills: ["~/prj/second-brain/skills"]` in `~/.config/opencode/opencode.json`
- Claude Code: one `~/.claude/skills/<skill-id>` symlink per skill directory
- Other agents: read the SKILL.md files directly

## Conventions

- Skill ID = directory name, lowercase kebab-case, prefixed `kb-` for brain skills
- Each skill has a `SKILL.md` with `name` and `description` frontmatter
- Description must contain trigger phrases users actually say

## How to add a skill

Use the `kb-skill-add` skill: it walks you through creation, schema update, and commit.
