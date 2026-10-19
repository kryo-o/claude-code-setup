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
[ "$(uname)" = "Darwin" ] || { echo "This template is macOS only for now."; exit 1; }
for cmd in claude git jq rsync; do
  command -v "$cmd" >/dev/null || { echo "Missing: $cmd (jq: brew install jq)"; exit 1; }
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
    echo
    echo "Review the code before freezing it:"
    ls -d "$C"/claude-reflect-marketplace/reflect-mod/*/hooks "$C"/claude-code-mods/cache-tax/*/hooks || true
    echo "Reviewed versions: reflect-mod 3.3.0, cache-tax 2.2.1. Anything newer is unreviewed."
    if ask "Freeze these copies?"; then
      mkdir -p "$V"
      rsync -a --exclude .in_use "$C"/claude-reflect-marketplace/reflect-mod/*/ "$V/reflect-mod/"
      rsync -a --exclude .in_use --exclude site --exclude docs --exclude .github "$C"/claude-code-mods/cache-tax/*/ "$V/cache-tax/"
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
cp "$REPO/statusline.sh" "$CL/"
cp "$REPO"/hooks/* "$CL/hooks/"
chmod +x "$CL/hooks/deny-guard.sh"
sed "s#__HOME__#$HOME#g" "$REPO/settings.json" > "$CL/settings.json"
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
for m in $(jq -r '.extraKnownMarketplaces[].source | .repo // .path' "$S"); do
  claude plugin marketplace add "$m" || true
done
failed=""
for p in $(jq -r '.enabledPlugins | keys[] | select(endswith("@builtin") | not)' "$S"); do
  claude plugin uninstall "$p" >/dev/null 2>&1 || true
  claude plugin install "$p" || failed+=" $p"
done

# --- self-test ---
say "Testing deny-guard"
bash "$CL/hooks/deny-guard-test.sh"

if [ -n "$failed" ]; then
  say "Done, but these plugins failed to install:$failed"
  echo "Re-run bash install.sh, or install them by hand with: claude plugin install <name>"
  exit 1
fi
say "Done. Start claude and run /plugin to check everything is there."
