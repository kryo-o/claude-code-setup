#!/bin/bash
# Installs this template into ~/.claude. Run from the repo folder: bash install.sh
# Safe to re-run: it backs up settings.json, skips steps already done and reinstalls plugins.
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
CL="$HOME/.claude"
V="$CL/mods/vendored-mods"

say() { printf '\n\033[1m%s\033[0m\n' "$1"; }
ask() { read -r -p "$1 [y/N] " a; [[ "$a" =~ ^[Yy]$ ]]; }

# --- checks ---
need="git jq rsync"
case "$(uname)" in
  Darwin) hint="brew install jq" ;;
  # The Linux sandbox runs commands through bubblewrap and proxies network via socat.
  Linux) need+=" bwrap socat"; hint="your package manager, e.g. apt install jq rsync bubblewrap socat" ;;
  *) echo "Supported on macOS and Linux (including WSL2) only."; exit 1 ;;
esac
for cmd in $need; do
  command -v "$cmd" >/dev/null || { echo "Missing: $cmd. Install with: $hint"; exit 1; }
done
# shellcheck source=install-claude.sh
source "$REPO/install-claude.sh"
ensure_claude || exit 1

# --- backup ---
mkdir -p "$CL/hooks" "$V"
if [ -f "$CL/settings.json" ]; then
  b="$CL/settings.json.bak-$(date +%Y%m%d-%H%M%S)"
  cp "$CL/settings.json" "$b"
  say "Backed up your settings to $b"
fi

# --- Anthropic playground mods ---
if [ ! -d "$CL/mods/claude-code-playground" ]; then
  say "Cloning anthropics/claude-code-playground"
  git clone --depth 1 https://github.com/anthropics/claude-code-playground "$CL/mods/claude-code-playground"
fi

# --- third-party mods: reviewed copies shipped in this repo ---
use_vendored=yes
say "Third-party mods (reflect-mod, cache-tax)"
echo "Reviewed copies ship in this repo, so nothing is downloaded from their authors."
if [ ! -t 0 ]; then
  # No terminal to answer (for example run through Claude's !): keep what is already there.
  if [ -d "$V/reflect-mod" ] && [ -d "$V/cache-tax" ]; then
    echo "No terminal to ask, so the mods you already have stay installed."
    answer=yes
  else
    echo "No terminal to ask, so they are skipped. Re-run in a terminal to add them."
    answer=no
  fi
elif ask "Install them?"; then answer=yes; else answer=no; fi
if [ "$answer" = yes ]; then
  # --delete makes the installed copy match the repo exactly; .in_use is Claude Code's and stays.
  for m in reflect-mod cache-tax; do
    rsync -a --delete --exclude .in_use "$REPO/mods/vendored-mods/$m/" "$V/$m/"
  done
else
  use_vendored=no
fi

# --- config files ---
say "Copying config into $CL"
mkdir -p "$V"
cp -R "$REPO/mods/vendored-mods/.claude-plugin" "$V/"
cp "$REPO"/hooks/* "$CL/hooks/"
chmod +x "$CL/hooks/deny-guard.sh"
# jq, not sed: a home path containing & or # would break a sed replacement.
TMP="$(mktemp -d "${TMPDIR:-/tmp}/claude-setup.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
jq --arg h "$HOME" 'walk(if type == "string" then gsub("__HOME__"; $h) else . end)' \
  "$REPO/settings.json" > "$TMP/template.json"
if [ -f "$CL/settings.json" ]; then cp "$CL/settings.json" "$TMP/user.json"; else echo '{}' > "$TMP/user.json"; fi
# Merge, not overwrite: your preferences stay, the security settings follow the template.
jq -n --slurpfile user "$TMP/user.json" --slurpfile tpl "$TMP/template.json" \
  -f "$REPO/merge-settings.jq" > "$TMP/merged.json"
jq '.settings' "$TMP/merged.json" > "$CL/settings.json"
jq -r '.dropped[] | "Removed or replaced in your settings: " + .' "$TMP/merged.json"
if [ "$use_vendored" = no ]; then
  jq 'del(.enabledPlugins["reflect-mod@vendored-mods", "cache-tax@vendored-mods"]) | del(.extraKnownMarketplaces["vendored-mods"])' \
    "$CL/settings.json" > "$CL/settings.json.tmp" && mv "$CL/settings.json.tmp" "$CL/settings.json"
  echo "Skipped reflect-mod and cache-tax."
fi

# --- CLAUDE.md docs rule (appended once) ---
if ! grep -q 'claude-code-setup: docs rule' "$CL/CLAUDE.md" 2>/dev/null; then
  { [ -s "$CL/CLAUDE.md" ] && echo; cat "$REPO/claude-md/docs-rule.md"; } >> "$CL/CLAUDE.md"
  echo "Added the Context7 docs rule to $CL/CLAUDE.md"
fi

# --- marketplaces and plugins ---
say "Installing marketplaces and plugins"
S="$CL/settings.json"
claude plugin marketplace add anthropics/claude-plugins-official || true
# while-read, not for-in: a home folder with a space in its name must stay one path.
while IFS= read -r m; do
  claude plugin marketplace add "$m" </dev/null || true
done < <(jq -r '.extraKnownMarketplaces[].source | .repo // .path' "$S")
failed=""
while IFS= read -r p; do
  claude plugin uninstall "$p" </dev/null >/dev/null 2>&1 || true
  claude plugin install "$p" </dev/null || failed+=" $p"
done < <(jq -r '.enabledPlugins | keys[] | select(endswith("@builtin") | not)' "$S")

# --- Claude OS dashboard and its claude-os command ---
# Both run outside the sandbox when you start them, so settings.json denies Claude edits to them.
say "Installing the Claude OS dashboard"
rsync -a --delete --exclude tests --exclude __pycache__ --exclude .claude --exclude .gitignore \
  "$REPO/dashboard/" "$CL/claude-os/"
mkdir -p "$HOME/.local/bin"
printf '%s\n' '#!/bin/bash' \
  '# Opens the Claude OS dashboard for the current folder. Installed by claude-code-setup.' \
  'exec python3 -I "$HOME/.claude/claude-os/serve.py" --project "$PWD" --open "$@"' > "$HOME/.local/bin/claude-os"
chmod +x "$HOME/.local/bin/claude-os"
case ":$PATH:" in
  *":$HOME/.local/bin:"*) echo "Run claude-os in any project folder to open the dashboard." ;;
  *) echo "Add ~/.local/bin to your PATH, then run claude-os in any project folder." ;;
esac

# --- self-test ---
say "Testing deny-guard"
bash "$CL/hooks/deny-guard-test.sh"

if [ -n "$failed" ]; then
  say "Done, but these plugins failed to install:$failed"
  echo "Re-run bash install.sh, or install them by hand with: claude plugin install <name>"
  exit 1
fi
say "Done. Start claude and run /plugin to check everything is there."
echo "Note: plugins other than the frozen mods update from their authors' repos."
echo "Turn off auto-update in /plugin > Marketplaces if you want to review each version first."
