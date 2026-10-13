#!/bin/bash
set -euo pipefail

# Second Brain Starter Kit — Setup Script
# Phase 1: Create the workspace (knowledge base skeleton)
# Phase 2: Install schema, skills, and agent discovery wiring

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_WORKSPACE="$HOME/prj/second-brain"

echo "=== Second Brain Starter Kit ==="
echo ""

# -----------------------------------------------
# Step 1: Check dependencies
# -----------------------------------------------

echo "Checking dependencies..."
MISSING=0

if command -v git >/dev/null 2>&1; then
    echo "  ok git ($(git --version | head -c 20))"
else
    echo "  x git — required (version control for the knowledge base)"
    MISSING=1
fi

if command -v claude >/dev/null 2>&1; then
    echo "  ok claude (Claude Code)"
else
    echo "  - claude not found (optional — install with: npm i -g @anthropic-ai/claude-code)"
fi

if command -v opencode >/dev/null 2>&1; then
    echo "  ok opencode"
else
    echo "  - opencode not found (optional — install from https://opencode.ai)"
fi

if [[ $MISSING -eq 1 ]]; then
    echo ""
    echo "Missing required tools. Install them and re-run ./setup.sh"
    exit 1
fi

echo ""

# -----------------------------------------------
# Step 2: Personalize
# -----------------------------------------------

read -p "Your first name: " USER_NAME
read -p "One-line bio (e.g., 'engineer, learning ML, building side projects'): " USER_BIO

if [[ -z "$USER_NAME" || ${#USER_NAME} -lt 2 ]]; then
    echo "Error: name is required (at least 2 characters)"
    exit 1
fi

read -p "Workspace directory [$DEFAULT_WORKSPACE]: " WORKSPACE_INPUT
WORKSPACE_DIR="${WORKSPACE_INPUT:-$DEFAULT_WORKSPACE}"
# Expand leading ~ (only if present)
if [[ "$WORKSPACE_DIR" == "~"* ]]; then
    WORKSPACE_DIR="${WORKSPACE_DIR/#\~/$HOME}"
fi
# Expand embedded variables like $HOME
WORKSPACE_DIR=$(eval echo "$WORKSPACE_DIR" 2>/dev/null || echo "$WORKSPACE_DIR")

echo ""
echo "Summary:"
echo "  Name:       $USER_NAME"
echo "  Bio:        $USER_BIO"
echo "  Workspace:  $WORKSPACE_DIR"
echo ""

if [[ -d "$WORKSPACE_DIR" ]]; then
    echo "Warning: $WORKSPACE_DIR already exists."
    read -p "Merge into it (existing files are kept)? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    MERGE=1
else
    MERGE=0
fi

# ===============================================
# PHASE 1: Create the workspace
# ===============================================

echo "Phase 1: Creating workspace at $WORKSPACE_DIR ..."

mkdir -p "$WORKSPACE_DIR"/{inbox,raw/sources,raw/session-notes,raw/pages/topics,raw/pages/entities,raw/pages/sources,wiki,outputs/briefings,outputs/reports,outputs/summaries,knowledge/user,knowledge/problems,knowledge/projects,skills,.overmind}

# Preserve empty directories in git
for d in inbox raw/sources raw/session-notes raw/pages/topics raw/pages/entities raw/pages/sources outputs/briefings outputs/reports outputs/summaries knowledge/user knowledge/problems knowledge/projects; do
    touch "$WORKSPACE_DIR/$d/.gitkeep"
done

# Seed example content (only if not already present — safe on merge)
if [[ ! -f "$WORKSPACE_DIR/raw/pages/topics/example-topic.md" && -f "$SCRIPT_DIR/content/example-topic.md" ]]; then
    cp "$SCRIPT_DIR/content/example-topic.md" "$WORKSPACE_DIR/raw/pages/topics/"
fi

# --- Folder READMEs (self-documenting) ---
cp "$SCRIPT_DIR/templates/root-README.md" "$WORKSPACE_DIR/README.md"
cp "$SCRIPT_DIR/templates/inbox-README.md" "$WORKSPACE_DIR/inbox/README.md"
cp "$SCRIPT_DIR/templates/raw-README.md" "$WORKSPACE_DIR/raw/README.md"
cp "$SCRIPT_DIR/templates/raw-pages-README.md" "$WORKSPACE_DIR/raw/pages/README.md"
cp "$SCRIPT_DIR/templates/wiki-README.md" "$WORKSPACE_DIR/wiki/README.md"
cp "$SCRIPT_DIR/templates/outputs-README.md" "$WORKSPACE_DIR/outputs/README.md"
cp "$SCRIPT_DIR/templates/skills-README.md" "$WORKSPACE_DIR/skills/README.md"

# --- Wiki seed files ---
if [[ ! -f "$WORKSPACE_DIR/wiki/index.md" ]]; then
    cat > "$WORKSPACE_DIR/wiki/index.md" <<'EOF'
# Second Brain Wiki Index

## Topics
*No topic pages yet.*

## Entities
*No entity pages yet.*

## Source Summaries
*No source summaries yet.*
EOF
fi

if [[ ! -f "$WORKSPACE_DIR/wiki/log.md" ]]; then
    echo "# Knowledge Base Log" > "$WORKSPACE_DIR/wiki/log.md"
    echo "" >> "$WORKSPACE_DIR/wiki/log.md"
    echo "---" >> "$WORKSPACE_DIR/wiki/log.md"
fi

if [[ ! -f "$WORKSPACE_DIR/wiki/processed.md" ]]; then
    cat > "$WORKSPACE_DIR/wiki/processed.md" <<'EOF'
# Ingested Sources Registry

| Date | Title | Raw File | Source Summary |
|------|-------|----------|----------------|
EOF
fi

# --- Config ---
cat > "$WORKSPACE_DIR/.overmind/config.yaml" <<EOF
kb:
  name: "Second Brain"
  path: "$WORKSPACE_DIR"
  focus: "everything"   # refined during /onboard
  dream:
    cadence: weekly
    last-run: null

git:
  local-only: true
  remote: null
EOF

cp "$SCRIPT_DIR/templates/mcp-resource-map.yaml" "$WORKSPACE_DIR/.overmind/mcp-resource-map.yaml"

# --- Schema (with workspace path substituted) ---
sed -e "s|{{WORKSPACE_DIR}}|$WORKSPACE_DIR|g" \
    -e "s/{{USER_NAME}}/$USER_NAME/g" \
    -e "s|{{USER_BIO}}|$USER_BIO|g" \
    "$SCRIPT_DIR/templates/SCHEMA.md" > "$WORKSPACE_DIR/SCHEMA.md"

echo "  Workspace skeleton created."
echo ""

# ===============================================
# PHASE 2: Skills + agent wiring
# ===============================================

echo "Phase 2: Installing skills and wiring agents ..."

# --- Copy the shared skill library ---
for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    skill_id=$(basename "$skill_dir")
    mkdir -p "$WORKSPACE_DIR/skills/$skill_id"
    cp -R "$skill_dir"/* "$WORKSPACE_DIR/skills/$skill_id/"
done

# Substitute workspace path inside skill bodies
find "$WORKSPACE_DIR/skills" -name "SKILL.md" -exec \
    sed -i "s|{{WORKSPACE_DIR}}|$WORKSPACE_DIR|g" {} \;

# --- Agent shims ---

# Claude Code shim at the workspace parent (so it applies to sibling projects)
SHIM_DIR="$(dirname "$WORKSPACE_DIR")"
if [[ ! -f "$SHIM_DIR/CLAUDE.md" ]]; then
    sed -e "s|{{WORKSPACE_DIR}}|$WORKSPACE_DIR|g" \
        "$SCRIPT_DIR/templates/claude-shim.md" > "$SHIM_DIR/CLAUDE.md"
    echo "  Claude Code shim created at $SHIM_DIR/CLAUDE.md"
else
    echo "  - $SHIM_DIR/CLAUDE.md already exists — left untouched (add the shim manually if needed)"
fi

# Path-scoped rules for Claude Code
mkdir -p "$HOME/.claude/rules"
sed -e "s|{{WORKSPACE_DIR}}|$WORKSPACE_DIR|g" \
    "$SCRIPT_DIR/templates/second-brain-rules.md" > "$HOME/.claude/rules/second-brain-rules.md"
echo "  Claude Code path-scoped rules installed at ~/.claude/rules/second-brain-rules.md"

# Claude Code skills symlink
mkdir -p "$HOME/.claude/skills"
ln -sfn "$WORKSPACE_DIR/skills" "$HOME/.claude/skills/second-brain"
echo "  Claude Code skills linked: ~/.claude/skills/second-brain -> $WORKSPACE_DIR/skills"

# OpenCode shim
mkdir -p "$HOME/.opencode"
sed -e "s|{{WORKSPACE_DIR}}|$WORKSPACE_DIR|g" \
    "$SCRIPT_DIR/templates/opencode-instructions.md" > "$HOME/.opencode/instructions.md"
echo "  OpenCode shim installed at ~/.opencode/instructions.md"

# OpenCode skills config entry (merge into opencode.json if present)
OPENCODE_CONFIG="$HOME/.config/opencode/opencode.json"
if command -v python3 >/dev/null 2>&1; then
    python3 - "$OPENCODE_CONFIG" "$WORKSPACE_DIR" <<'PYEOF'
import json, os, sys
config_path, workspace = sys.argv[1], sys.argv[2]
skills_path = f"~/prj/second-brain/skills" if os.path.expanduser("~") + "/prj/second-brain" == workspace else workspace + "/skills"
entry = workspace + "/skills"
os.makedirs(os.path.dirname(config_path), exist_ok=True)
cfg = {}
if os.path.exists(config_path):
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
skills = cfg.get("skills", [])
if entry not in skills:
    skills.append(entry)
    cfg["skills"] = skills
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"  OpenCode skills config updated: {entry}")
else:
    print("  OpenCode skills config already contains the brain skills path")
PYEOF
else
    echo "  ! python3 not found — add \"$WORKSPACE_DIR/skills\" to the 'skills' array in $OPENCODE_CONFIG manually"
fi

# Safety hooks (block git push for the brain, back up files before edits)
mkdir -p "$HOME/.claude/hooks"
cp "$SCRIPT_DIR/hooks/bash-safety.sh" "$HOME/.claude/hooks/"
cp "$SCRIPT_DIR/hooks/file-backup.sh" "$HOME/.claude/hooks/"
chmod +x "$HOME/.claude/hooks/"*.sh
echo "  Safety hooks installed at ~/.claude/hooks/ (block push, pre-edit backup)"

echo ""

# ===============================================
# PHASE 3: Initialize git (local-only)
# ===============================================

echo "Phase 3: Initializing local-only git repo ..."

cd "$WORKSPACE_DIR"
if [[ ! -d .git ]]; then
    git init -q
    # Ensure a git identity exists for this repo (don't touch global config)
    if ! git config user.email >/dev/null 2>&1; then
        git config user.email "$USER_NAME@second-brain.local"
        git config user.name "$USER_NAME"
    fi
    cat > .gitignore <<'EOF'
# local-only brain: never publish
*.secret
*.key
*.pem
.env*
EOF
    git add -A
    git commit -q -m "init: second brain knowledge base (local-only git)"
    echo "  Git repo initialized (no remote — your knowledge stays on this machine)."
else
    git add -A
    git diff --cached --quiet || git commit -q -m "setup: merge starter kit files"
    echo "  Existing repo detected — starter kit files merged and committed."
fi

# ===============================================
# PHASE 4: Dream Sequence scheduling (optional)
# ===============================================

echo "Phase 4: Dream Sequence scheduling (optional) ..."
read -p "Schedule the Dream Sequence to run automatically (cron)? [Y/n] " -n 1 -r
echo
SCHEDULED=0
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
  read -p "Cadence — [d]aily 9:00, [w]eekly Friday 17:00 [default w]: " CADENCE_INPUT
  case "${CADENCE_INPUT:-w}" in
    d*) SCHEDULE="0 9 * * *";  CADENCE="daily" ;;
    *)  SCHEDULE="0 17 * * 5"; CADENCE="weekly" ;;
  esac

  # Pick an agent binary (absolute path — cron gets a minimal environment)
  AGENT_BIN=""
  AGENT_NAME=""
  if command -v opencode >/dev/null 2>&1; then
    AGENT_BIN="$(command -v opencode)"; AGENT_NAME="opencode"
  elif command -v claude >/dev/null 2>&1; then
    AGENT_BIN="$(command -v claude)"; AGENT_NAME="claude"
  fi

  if [[ -z "$AGENT_BIN" ]]; then
    echo "  ! No agent CLI found (opencode or claude). Skipping schedule — run 'dream sequence' manually."
  else
    mkdir -p "$WORKSPACE_DIR/.overmind/logs"
    sed -e "s|{{KB_DIR}}|$WORKSPACE_DIR|g" \
        -e "s|{{AGENT_BIN}}|$AGENT_BIN|g" \
        -e "s|{{AGENT_NAME}}|$AGENT_NAME|g" \
        -e "s|{{AGENT_PATH}}|$PATH|g" \
        "$SCRIPT_DIR/templates/dream-cron.sh" > "$WORKSPACE_DIR/.overmind/dream-cron.sh"
    chmod +x "$WORKSPACE_DIR/.overmind/dream-cron.sh"

    # Install/update the cron entry (idempotent — replaces previous brain entries)
    CRON_BLOCK="# second-brain-dream
$SCHEDULE $WORKSPACE_DIR/.overmind/dream-cron.sh"
    ( crontab -l 2>/dev/null | grep -v "second-brain-dream" | grep -v "dream-cron.sh" ; echo "$CRON_BLOCK" ) | crontab - 2>/dev/null \
      && echo "  Cron installed: $CADENCE ($SCHEDULE) via $AGENT_NAME" \
      || echo "  ! crontab not available — schedule manually (see MANUAL.md)"
    SCHEDULED=1

    # Record schedule in config.yaml
    sed -i "s|last-run: null|last-run: null\n    schedule: \"$SCHEDULE\"\n    runner: $AGENT_NAME|" "$WORKSPACE_DIR/.overmind/config.yaml" 2>/dev/null || true
  fi
else
  echo "  Skipped. Run 'dream sequence' manually, or re-run setup to schedule."
fi

echo ""

# ===============================================
# Done
# ===============================================

echo ""
echo "=== Setup complete ==="
echo ""
echo "Workspace: $WORKSPACE_DIR"
echo "  SCHEMA.md   — the operating manual every agent reads"
echo "  skills/     — 8 shared skills (ingest, query, dream, onboard, ...)"
echo "  inbox/      — drop stuff here, process weekly"
echo "  knowledge/  — your profile, problems, goals (filled by /onboard)"
echo ""
echo "Agent wiring:"
echo "  Claude Code: shim + rules + skills symlink"
echo "  OpenCode:    shim + skills config entry"
echo ""
echo "Documentation:"
echo "  MANUAL.md        — complete command reference (read this first)"
echo "  AGENT-PROMPT.md  — paste into any agent session to load the brain"
echo ""
echo "=== Next: start your first session ==="
echo ""
echo "  cd $WORKSPACE_DIR"
echo "  claude    # or: opencode"
echo ""
echo "Then type:"
echo "  /onboard"
echo ""
echo "Guided setup (~15-20 min): focus, favorite problems, goals, first seeds."
echo "Pause anytime — run /onboard again to resume."
if [[ $SCHEDULED -eq 1 ]]; then
  echo ""
  echo "Dream Sequence scheduled ($CADENCE). Logs: $WORKSPACE_DIR/.overmind/logs/"
  echo "Test the wiring anytime: $WORKSPACE_DIR/.overmind/dream-cron.sh --dry-run"
fi
