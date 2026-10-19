#!/bin/bash
# Installs this template into ~/.claude. Run from the repo folder: bash install.sh
# Safe to re-run: it backs up settings.json, skips steps already done and reinstalls plugins.
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
CL="$HOME/.claude"
V="$CL/mods/vendored-mods"
C="$CL/plugins/cache"

say() { printf '\n\033[1m%s\033[0m\n' "$1"; }
ask() { read -r -p "$1 [y/N] " a; [[ "$a" =~ ^[Yy]$ ]]; }

# --- checks ---
need="claude git jq rsync"
case "$(uname)" in
  Darwin) hint="brew install jq" ;;
  # The Linux sandbox runs commands through bubblewrap and proxies network via socat.
  Linux) need+=" bwrap socat"; hint="your package manager, e.g. apt install jq rsync bubblewrap socat" ;;
  *) echo "Supported on macOS and Linux (including WSL2) only."; exit 1 ;;
esac
for cmd in $need; do
  command -v "$cmd" >/dev/null || { echo "Missing: $cmd. Install with: $hint"; exit 1; }
done

# --- backup ---
mkdir -p "$CL/hooks" "$CL/mods"
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

# --- third-party mods: install, review, freeze ---
use_vendored=yes
if [ -d "$V/reflect-mod" ] && [ -d "$V/cache-tax" ]; then
  say "Frozen copies of reflect-mod and cache-tax already exist, keeping them"
else
  say "Third-party mods (reflect-mod, cache-tax)"
  echo "These are installed from their authors' repos, then frozen so updates can't change them."
  if ask "Install them?"; then
    claude plugin marketplace add bayramannakov/claude-reflect
    claude plugin install reflect-mod@claude-reflect-marketplace
    claude plugin marketplace add karanb192/claude-code-mods
    claude plugin install cache-tax@claude-code-mods
    # Newest cached version of each; older cached versions are ignored.
    rdir=$(ls -d "$C"/claude-reflect-marketplace/reflect-mod/*/ 2>/dev/null | sort -V | tail -1)
    cdir=$(ls -d "$C"/claude-code-mods/cache-tax/*/ 2>/dev/null | sort -V | tail -1)
    [ -n "$rdir" ] && [ -n "$cdir" ] || { echo "Could not find the downloaded mods in $C."; exit 1; }
    rver=$(basename "$rdir"); cver=$(basename "$cdir")
    echo
    echo "Downloaded reflect-mod $rver and cache-tax $cver. Review the code before freezing it:"
    echo "  ${rdir}hooks/"
    echo "  ${cdir}hooks/"
    [ "$rver" = "3.3.0" ] || echo "  WARNING: reflect-mod $rver is not the reviewed version (3.3.0). Read it closely."
    [ "$cver" = "2.2.1" ] || echo "  WARNING: cache-tax $cver is not the reviewed version (2.2.1). Read it closely."
    if ask "Freeze these copies?"; then
      mkdir -p "$V"
      rsync -a --exclude .in_use "$rdir" "$V/reflect-mod/"
      rsync -a --exclude .in_use --exclude site --exclude docs --exclude .github "$cdir" "$V/cache-tax/"
    else
      use_vendored=no
    fi
    claude plugin uninstall reflect-mod@claude-reflect-marketplace || true
    claude plugin uninstall cache-tax@claude-code-mods || true
    claude plugin marketplace remove claude-reflect-marketplace || true
    claude plugin marketplace remove claude-code-mods || true
  else
    use_vendored=no
  fi
fi

# --- config files ---
say "Copying config into $CL"
mkdir -p "$V"
cp -R "$REPO/mods/vendored-mods/.claude-plugin" "$V/"
cp "$REPO"/hooks/* "$CL/hooks/"
chmod +x "$CL/hooks/deny-guard.sh"
# jq, not sed: a home path containing & or # would break a sed replacement.
jq --arg h "$HOME" 'walk(if type == "string" then gsub("__HOME__"; $h) else . end)' \
  "$REPO/settings.json" > "$CL/settings.json"
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
