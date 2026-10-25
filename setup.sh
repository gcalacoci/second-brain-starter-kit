#!/bin/bash
set -euo pipefail

# Second Brain Starter Kit — Setup Script
# Phase 1: Create the workspace (knowledge base skeleton)
# Phase 2: Install schema, skills, and agent discovery wiring
# Phase 2b: MCP server registration (Claude Desktop + Claude Code)

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

# --- uv (Python package manager — required for the MCP server) ---
# The MCP server is launched via: uv run --no-project --with "mcp>=1.2" python ...
# which resolves the mcp package on demand, so no manual pip install is needed.
UV_BIN=""
if command -v uv >/dev/null 2>&1; then
    UV_BIN="$(command -v uv)"
    echo "  ok uv ($("$UV_BIN" --version | head -c 20))"
else
    echo "  - uv — not found (needed for the MCP server)"
    if command -v curl >/dev/null 2>&1; then
        echo "    Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        read -p "    Install uv now? [Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            curl -LsSf https://astral.sh/uv/install.sh | sh
            if [[ -f "$HOME/.local/bin/uv" ]]; then
                export PATH="$HOME/.local/bin:$PATH"
                UV_BIN="$(command -v uv || echo "$HOME/.local/bin/uv")"
                echo "  ok uv ($("$UV_BIN" --version | head -c 20))"
            fi
        fi
    else
        echo "    curl not found — install curl first, then: curl -LsSf https://astral.sh/uv/install.sh | sh"
    fi
fi
if [[ -z "$UV_BIN" ]]; then
    echo "  ! uv unavailable — the MCP server will NOT be installed or registered."
    echo "    Everything else (skills, hooks, cron) works without it."
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
# Expand $HOME explicitly (no eval — a path like ~/$(rm -rf /) must never execute)
WORKSPACE_DIR="${WORKSPACE_DIR//\$HOME/$HOME}"
# Also expand the braced form ${HOME}.
WORKSPACE_DIR="${WORKSPACE_DIR//\$\{HOME\}/$HOME}"

# Refuse anything that is still not an absolute path BEFORE creating files
# ($WS, an unexpanded variable name, must not become a directory in the cwd).
if [[ "$WORKSPACE_DIR" != /* ]]; then
    echo "Error: workspace path must be absolute (got: $WORKSPACE_DIR)"
    exit 1
fi

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

# --- Install-file helper -----------------------------------------------
# install_kit_file SRC DEST
#   MERGE=0: copy, overwriting (fresh install).
#   MERGE=1: create only if missing; if the existing file differs, write the
#            new version next to it as <dest>.kit-new and record it in
#            KIT_NEW_FILES for the end-of-run summary. Identical files are
#            skipped silently. Never overwrites user content.
KIT_NEW_FILES=()
install_kit_file() {
    local src="$1" dest="$2"
    if [[ -f "$dest" ]]; then
        if cmp -s "$src" "$dest"; then
            return 0  # identical — nothing to do
        fi
        if [[ $MERGE -eq 1 ]]; then
            cp "$src" "$dest.kit-new"
            chmod 0644 "$dest.kit-new"
            KIT_NEW_FILES+=("$dest.kit-new")
            return 0
        fi
    fi
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
    # Sources are rendered into mktemp files (0600); installed content files are
    # user-readable. Executables are chmod 0755 by their callers afterwards.
    chmod 0644 "$dest"
}

# --- Folder READMEs (self-documenting) ---
install_kit_file "$SCRIPT_DIR/templates/root-README.md" "$WORKSPACE_DIR/README.md"
install_kit_file "$SCRIPT_DIR/templates/inbox-README.md" "$WORKSPACE_DIR/inbox/README.md"
install_kit_file "$SCRIPT_DIR/templates/raw-README.md" "$WORKSPACE_DIR/raw/README.md"
install_kit_file "$SCRIPT_DIR/templates/raw-pages-README.md" "$WORKSPACE_DIR/raw/pages/README.md"
# NOTE: no wiki/README.md — the schema's hard rule says wiki/ contains only
# index.md, log.md and processed.md (D7). The wiki is explained in root-README.
install_kit_file "$SCRIPT_DIR/templates/outputs-README.md" "$WORKSPACE_DIR/outputs/README.md"
install_kit_file "$SCRIPT_DIR/templates/skills-README.md" "$WORKSPACE_DIR/skills/README.md"

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
CONFIG_TMP="$(mktemp)"
cat > "$CONFIG_TMP" <<EOF
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
# If config.yaml already exists (merge), the dream-cron step may have recorded
# schedule/runner keys into it — those edits must survive, so skip the install
# entirely instead of letting install_kit_file file a .kit-new for it.
if [[ -f "$WORKSPACE_DIR/.overmind/config.yaml" ]] && grep -q "schedule:" "$WORKSPACE_DIR/.overmind/config.yaml" 2>/dev/null; then
    rm -f "$CONFIG_TMP"
else
    install_kit_file "$CONFIG_TMP" "$WORKSPACE_DIR/.overmind/config.yaml"
    rm -f "$CONFIG_TMP"
fi

# --- Schema (with workspace path substituted) ---
SCHEMA_TMP="$(mktemp)"
sed -e "s|{{WORKSPACE_DIR}}|$WORKSPACE_DIR|g" \
    -e "s/{{USER_NAME}}/$USER_NAME/g" \
    -e "s|{{USER_BIO}}|$USER_BIO|g" \
    "$SCRIPT_DIR/templates/SCHEMA.md" > "$SCHEMA_TMP"
install_kit_file "$SCHEMA_TMP" "$WORKSPACE_DIR/SCHEMA.md"
rm -f "$SCHEMA_TMP"

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
    for skill_file in "$skill_dir"/*; do
        install_kit_file "$skill_file" "$WORKSPACE_DIR/skills/$skill_id/$(basename "$skill_file")"
    done
done

# --- Install utility scripts (MCP server, search, stats, media pipeline) ---
# D1: these were previously never installed, yet SCHEMA.md refers to them.
mkdir -p "$WORKSPACE_DIR/scripts"
for script_file in "$SCRIPT_DIR"/scripts/*; do
    [[ -f "$script_file" ]] || continue  # skip subdirectories (e.g. __pycache__)
    install_kit_file "$script_file" "$WORKSPACE_DIR/scripts/$(basename "$script_file")"
done
find "$WORKSPACE_DIR/scripts" -maxdepth 1 -type f -exec chmod 0755 {} + 2>/dev/null || true
echo "  Scripts installed: $(find "$WORKSPACE_DIR/scripts" -maxdepth 1 -type f | wc -l | tr -d ' ') (mcp_server.py, kb-search.py, ...)"

# --- Install agent definitions (brain agents + general dev agents) ---
mkdir -p "$WORKSPACE_DIR/agents"
for agent_file in "$SCRIPT_DIR"/agents/*.md; do
    agent_name=$(basename "$agent_file")
    # Substitute workspace path in brain agents (temp file, then merge-install)
    AGENT_TMP="$(mktemp)"
    sed -e "s|{{WORKSPACE_DIR}}|$WORKSPACE_DIR|g" "$agent_file" > "$AGENT_TMP"
    install_kit_file "$AGENT_TMP" "$WORKSPACE_DIR/agents/$agent_name"
    rm -f "$AGENT_TMP"
done

# Wire Claude Code global discovery (personal agents, all projects).
# Individual symlinks — never clobber the user's own agents.
mkdir -p "$HOME/.claude/agents"
for agent_file in "$WORKSPACE_DIR"/agents/*.md; do
    agent_name=$(basename "$agent_file")
    target="$HOME/.claude/agents/$agent_name"
    # Clean up legacy extension-less links pointing into this workspace only.
    legacy="$HOME/.claude/agents/${agent_name%.md}"
    if [[ -L "$legacy" ]] && readlink "$legacy" | grep -q "^$WORKSPACE_DIR"; then
        rm "$legacy"
    fi
    if [[ -e "$target" && ! -L "$target" ]]; then
        echo "  - ~/.claude/agents/$agent_name exists (your own) — left untouched"
    else
        ln -sfn "$agent_file" "$target"
    fi
done
AGENT_COUNT=$(find "$WORKSPACE_DIR/agents" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
echo "  Agents installed: $AGENT_COUNT definitions (Claude Code discovery linked)"

# Substitute workspace path inside skill bodies (portable: temp file + move)
find "$WORKSPACE_DIR/skills" -name "SKILL.md" | while read -r f; do
    SKILL_TMP="$(mktemp)"
    sed "s|{{WORKSPACE_DIR}}|$WORKSPACE_DIR|g" "$f" > "$SKILL_TMP" && chmod 0644 "$SKILL_TMP" && mv "$SKILL_TMP" "$f"
done

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

# Path-scoped rules for Claude Code (merge-aware, portable sed)
mkdir -p "$HOME/.claude/rules"
RULES_TMP="$(mktemp)"
sed -e "s|{{WORKSPACE_DIR}}|$WORKSPACE_DIR|g" \
    "$SCRIPT_DIR/templates/second-brain-rules.md" > "$RULES_TMP"
install_kit_file "$RULES_TMP" "$HOME/.claude/rules/second-brain-rules.md"
rm -f "$RULES_TMP"
echo "  Claude Code rules installed at ~/.claude/rules/second-brain-rules.md"

# Claude Code skill discovery: one symlink per skill.
# Claude Code only discovers ~/.claude/skills/<skill-id>/SKILL.md — a single
# link to the parent folder leaves every SKILL.md one level too deep (D3).
mkdir -p "$HOME/.claude/skills"
# Legacy layout from older installs: remove the parent-folder symlink if present.
if [[ -L "$HOME/.claude/skills/second-brain" ]]; then
    rm "$HOME/.claude/skills/second-brain"
    echo "  Removed legacy symlink ~/.claude/skills/second-brain (replaced by per-skill links)"
elif [[ -d "$HOME/.claude/skills/second-brain" ]]; then
    echo "  ! ~/.claude/skills/second-brain is a real directory — left untouched"
fi
for skill_dir in "$WORKSPACE_DIR"/skills/*/; do
    skill_id=$(basename "$skill_dir")
    target="$HOME/.claude/skills/$skill_id"
    if [[ -e "$target" && ! -L "$target" ]]; then
        echo "  ! ~/.claude/skills/$skill_id exists (your own) — left untouched"
    else
        ln -sfn "$WORKSPACE_DIR/skills/$skill_id" "$target"
    fi
done
echo "  Claude Code skills linked: one symlink per skill in ~/.claude/skills/"

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

# Safety hooks: security guard + pre-edit backup (registered in settings.json)
# Merge-aware: rendered into temp files first, then install_kit_file decides
# (fresh = overwrite; merge = .kit-new on conflict).
mkdir -p "$HOME/.claude/hooks" "$HOME/.claude/state"
for hook in security-guard.py file-backup.py; do
    HOOK_TMP="$(mktemp)"
    sed -e "s|{{KB_DIR}}|$WORKSPACE_DIR|g" "$SCRIPT_DIR/hooks/$hook" > "$HOOK_TMP"
    install_kit_file "$HOOK_TMP" "$HOME/.claude/hooks/$hook"
    rm -f "$HOOK_TMP"
done
chmod 0755 "$HOME/.claude/hooks/security-guard.py" "$HOME/.claude/hooks/file-backup.py"
# Superseded script from older installs
rm -f "$HOME/.claude/hooks/bash-safety.sh"

# Register hooks + permissions in ~/.claude/settings.json (merge, never clobber)
python3 - "$HOME/.claude/settings.json" "$SCRIPT_DIR/templates/settings-permissions.json" <<'PYEOF'
import json, os, sys

settings_path, perms_path = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(settings_path), exist_ok=True)

cfg = {}
if os.path.exists(settings_path):
    try:
        with open(settings_path) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}

# --- Merge deny list ---
extra = json.load(open(perms_path))
deny = set(cfg.get("permissions", {}).get("deny", [])) | set(extra.get("deny", []))
cfg.setdefault("permissions", {})["deny"] = sorted(deny)

# --- Register hooks (idempotent) ---
hooks = cfg.setdefault("hooks", {})
pre = hooks.setdefault("PreToolUse", [])

def has(hook_list, needle):
    return any(needle in json.dumps(h) for h in hook_list)

if not has(pre, "security-guard.py"):
    pre.append({
        "matcher": "Read|Write|Edit|Bash|Grep|Glob|NotebookEdit",
        "hooks": [{"type": "command",
                   "command": "python3 $HOME/.claude/hooks/security-guard.py",
                   "timeout": 5}],
    })
if not has(pre, "file-backup.py"):
    pre.append({
        "matcher": "Edit|Write",
        "hooks": [{"type": "command",
                   "command": "python3 $HOME/.claude/hooks/file-backup.py",
                   "timeout": 5}],
    })

with open(settings_path, "w") as f:
    json.dump(cfg, f, indent=2)

print("  settings.json updated: security-guard + file-backup registered, deny list merged")
PYEOF
echo "  Safety layer installed: security-guard.py (boundaries, secrets, push guard) + file-backup.py"

# ===============================================
# PHASE 2b: MCP server registration (needs uv)
# ===============================================
# The server is launched with uv, which resolves the mcp package on demand —
# no manual pip install required (D2). Registration is skipped cleanly if uv
# is unavailable (D5).

MCP_LAUNCH_CMD="\"$UV_BIN\" run --no-project --with \"mcp>=1.2\" python \"$WORKSPACE_DIR/scripts/mcp_server.py\""
MCP_SERVER_REGISTERED=0
DESKTOP_CONFIG_FAILED=0

if [[ -n "$UV_BIN" ]]; then
    echo ""
    echo "Phase 2b: MCP server registration (search + read + inbox capture) ..."

    # 1) Claude Desktop
    read -p "  Register the brain MCP server in Claude Desktop? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        if [[ "$(uname)" == "Darwin" ]]; then
            DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
        else
            DESKTOP_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"
        fi
        DESKTOP_PY_EXIT=0
        if python3 - "$DESKTOP_CONFIG" "$UV_BIN" "$WORKSPACE_DIR" <<PYEOF
import json, os, shutil, sys
from datetime import datetime

config_path, uv_bin, workspace = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(os.path.dirname(config_path), exist_ok=True)

# Exit codes: 0 = registered/updated, 3 = aborted without touching the file.
def abort(msg):
    print(f"  ! {msg}", file=sys.stderr)
    sys.exit(3)

cfg = {}
existed = os.path.exists(config_path)
if existed:
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except Exception as e:
        abort(f"Could not parse existing config ({e}) — file left untouched")
    if not isinstance(cfg, dict):
        abort("Existing config is valid JSON but not an object — left untouched")

mcp_servers = cfg.setdefault("mcpServers", {})
if not isinstance(mcp_servers, dict):
    abort("Existing config's 'mcpServers' is not an object — left untouched")

already = "second-brain" in mcp_servers
new_entry = {
    "command": uv_bin,
    "args": ["run", "--no-project", "--with", "mcp>=1.2",
             "python", f"{workspace}/scripts/mcp_server.py"],
    "env": {"SECOND_BRAIN_DIR": workspace},
}
if already and mcp_servers["second-brain"] == new_entry:
    print("  Claude Desktop: 'second-brain' entry already up to date — no change")
    sys.exit(0)

# Back up the user's config only when the entry actually changes
if existed:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{config_path}.bak-{stamp}"
    shutil.copy2(config_path, backup)
    print(f"  Backed up existing config -> {os.path.basename(backup)}")

mcp_servers["second-brain"] = new_entry
# Preserve all other top-level keys in cfg (like userCustomSetting)

# Atomic write: temp file in the same directory, then os.replace
tmp_path = f"{config_path}.tmp-{os.getpid()}"
with open(tmp_path, "w") as f:
    json.dump(cfg, f, indent=2)
os.replace(tmp_path, config_path)

if already:
    print("  Claude Desktop: replaced existing 'second-brain' MCP entry")
else:
    print("  Claude Desktop: registered 'second-brain' MCP server")
print("  Restart Claude Desktop completely to load the server.")
PYEOF
        then
            MCP_SERVER_REGISTERED=1
        else
            DESKTOP_PY_EXIT=$?
            if [[ $DESKTOP_PY_EXIT -eq 3 ]]; then
                echo "  Skipped Claude Desktop registration (config problem — file untouched)."
                DESKTOP_CONFIG_FAILED=1
            else
                echo "  ! Claude Desktop registration failed unexpectedly."
            fi
            MCP_SERVER_REGISTERED=0
        fi
    else
        echo "  Skipped Claude Desktop registration."
    fi

    # 2) Claude Code (optional, default no)
    read -p "  Register it in Claude Code too? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v claude >/dev/null 2>&1; then
            # Remove an existing entry first (idempotent), then add.
            claude mcp remove --scope user second-brain >/dev/null 2>&1 || true
            if claude mcp add --scope user second-brain \
                -e "SECOND_BRAIN_DIR=$WORKSPACE_DIR" \
                -- "$UV_BIN" run --no-project --with "mcp>=1.2" \
                python "$WORKSPACE_DIR/scripts/mcp_server.py"; then
                echo "  Claude Code: registered 'second-brain' MCP server (user scope)"
                MCP_SERVER_REGISTERED=1
            else
                echo "  ! claude mcp add failed — add it manually:"
                echo "    claude mcp add --scope user second-brain \\"
                echo "      -e \"SECOND_BRAIN_DIR=$WORKSPACE_DIR\" -- \\"
                echo "      $MCP_LAUNCH_CMD"
            fi
        else
            echo "  ! claude CLI not found — add it manually:"
            echo "    claude mcp add --scope user second-brain \\"
            echo "      -e \"SECOND_BRAIN_DIR=$WORKSPACE_DIR\" -- \\"
            echo "      $MCP_LAUNCH_CMD"
        fi
    else
        echo "  Skipped Claude Code registration."
    fi

    if [[ $MCP_SERVER_REGISTERED -eq 1 ]]; then
        echo "  MCP server ready. Tools: get_schema, get_index, search, read_file,"
        echo "  list_files, list_by_tag, list_by_type, write_inbox (inbox-only write)."
    fi
else
    echo ""
    echo "Phase 2b: MCP server registration — SKIPPED (uv not available)."
    echo "  The brain works fully without it (plain file reads). To add MCP later:"
    echo "    1. Install uv:  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "    2. Re-run ./setup.sh and answer yes to registration."
fi

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
    git commit -q -m "chore: init second brain knowledge base (local-only git)"
    echo "  Git repo initialized (no remote — your knowledge stays on this machine)."
else
    # Merge mode: the user's repo is theirs. Setup never stages or commits on
    # its behalf (D6) — the end-of-run summary tells them what to review.
    echo "  Existing repo detected — no commits made by setup (review with 'git status')."
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

    # Record schedule in config.yaml (portable: python, not sed -i; skipped
    # if the schedule is already recorded so re-runs don't create .kit-new)
    python3 - "$WORKSPACE_DIR/.overmind/config.yaml" "$SCHEDULE" "$AGENT_NAME" <<'CFGEOF'
import sys
path, schedule, runner = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    text = open(path).read()
except OSError:
    sys.exit(0)
if "schedule:" in text and "runner:" in text:
    sys.exit(0)  # already recorded — don't touch the file
if "last-run: null" not in text:
    sys.exit(0)
text = text.replace(
    "last-run: null",
    f'last-run: null\n    schedule: "{schedule}"\n    runner: {runner}',
    1,
)
open(path, "w").write(text)
CFGEOF
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
echo "  skills/     — $(ls "$WORKSPACE_DIR/skills" | grep -v README | wc -l | tr -d ' ') shared skills (ingest, query, dream, onboard, ...)"
echo "  scripts/    — mcp_server.py, kb-search.py, kb-stats.py, media-to-text.sh"
echo "  inbox/      — drop stuff here, process weekly"
echo "  knowledge/  — your profile, problems, goals (filled by /onboard)"
echo ""
echo "Agent wiring:"
echo "  Claude Code: shim + rules + one skills symlink per skill"
echo "  OpenCode:    shim + skills config entry"
if [[ $MCP_SERVER_REGISTERED -eq 1 ]]; then
    echo "  MCP server:  registered (Claude Desktop and/or Claude Code)"
elif [[ -z "$UV_BIN" ]]; then
    echo "  MCP server:  NOT registered (uv unavailable — install uv and re-run setup)"
elif [[ $DESKTOP_CONFIG_FAILED -eq 1 ]]; then
    echo "  MCP server:  NOT registered (Claude Desktop config could not be used - see message above)"
else
    echo "  MCP server:  NOT registered (declined — re-run setup to register)"
fi
echo ""
echo "Documentation:"
echo "  MANUAL.md        — complete command reference (read this first)"
echo "  AGENT-PROMPT.md  — paste into any agent session to load the brain"
echo ""
if [[ -d "$WORKSPACE_DIR/.git" && $MERGE -eq 1 ]]; then
    # Merge mode: setup never commits on the user's behalf, so always point
    # at git status — whether or not there are .kit-new files.
    if [[ ${#KIT_NEW_FILES[@]} -gt 0 ]]; then
        echo "=== Files needing manual review ==="
        echo ""
        echo "The kit updated these files, but you had local edits, so the new kit"
        echo "versions were written alongside as .kit-new. Review and merge manually:"
        echo ""
        for f in "${KIT_NEW_FILES[@]}"; do
            echo "  $f"
        done
        echo ""
    fi
    echo "Review changes with: git -C $WORKSPACE_DIR status"
    echo "Then commit what you want to keep."
    echo ""
fi
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
