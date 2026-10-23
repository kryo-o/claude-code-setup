#!/bin/bash
# Installs Claude Code with Anthropic's native installer when `claude` is missing.
# Sourced by install.sh, which defines ask(). Tested by install-claude-test.sh.

CLAUDE_INSTALLER_URL="https://claude.ai/install.sh"

ensure_claude() {
  command -v claude >/dev/null && return 0
  echo "Claude Code is not installed."
  echo "Anthropic's installer comes from $CLAUDE_INSTALLER_URL and puts claude in ~/.local/bin."
  if ! ask "Download and run it now?"; then
    echo "Install Claude Code first (https://code.claude.com/docs/en/setup), then re-run bash install.sh."
    return 1
  fi
  command -v curl >/dev/null || { echo "Missing: curl"; return 1; }
  local tmp status
  tmp="$(mktemp "${TMPDIR:-/tmp}/claude-install.XXXXXX")"
  # Download in full first, then run: a cut-off download fails here instead of running half a script.
  if ! curl -fsSL --proto '=https' --tlsv1.2 "$CLAUDE_INSTALLER_URL" -o "$tmp"; then
    rm -f "$tmp"
    echo "Download failed. Check your connection, or install Claude Code by hand."
    return 1
  fi
  bash "$tmp"
  status=$?
  rm -f "$tmp"
  [ "$status" -eq 0 ] || { echo "The Claude Code installer failed (exit $status)."; return 1; }
  # The installer adds ~/.local/bin to your shell profile; this run needs it now.
  export PATH="$HOME/.local/bin:$PATH"
  command -v claude >/dev/null || { echo "claude is still not on PATH. Add ~/.local/bin to PATH and re-run."; return 1; }
  echo "Installed $(claude --version 2>/dev/null || echo 'Claude Code')."
}
