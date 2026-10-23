#!/bin/bash
# Tests the installer: the settings merge (merge-settings.jq) and one full install.sh run
# against a fake home. Run from the repo root: bash install-test.sh
set -uo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/install-test.XXXXXX")"
pass=0
fail=0
ok() { pass=$((pass + 1)); }
no() { echo "FAIL: $1"; fail=$((fail + 1)); }
check() { if [ "$2" = "$3" ]; then ok; else no "$1 (expected $2, got $3)"; fi; }

TPL="$T/template.json"
jq --arg h "/home/u" 'walk(if type == "string" then gsub("__HOME__"; $h) else . end)' "$REPO/settings.json" > "$TPL"

# A user's settings: personal preferences, plus keys that switch the guardrails off.
cat > "$T/user.json" <<'EOF'
{
  "model": "opus[1m]",
  "outputStyle": "Concise",
  "includeCoAuthoredBy": true,
  "disableAllHooks": true,
  "skipDangerousModePermissionPrompt": true,
  "env": { "FOO": "bar" },
  "permissions": {
    "defaultMode": "bypassPermissions",
    "allow": ["Bash(npm test)"],
    "deny": ["Read(~/secret/**)", "Read(~/.npmrc)"],
    "ask": ["Bash(docker *)"]
  },
  "sandbox": { "enabled": false, "allowUnsandboxedCommands": true },
  "statusLine": { "type": "command", "command": "my-status" },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "~/.claude/hooks/deny-guard.sh" }] },
      { "matcher": "Edit", "hooks": [{ "type": "command", "command": "my-edit-hook" }] }
    ],
    "Stop": [{ "hooks": [{ "type": "command", "command": "say done" }] }]
  },
  "enabledPlugins": { "typesafe@typesafe-ai": true, "humanizer@humanizer": false },
  "extraKnownMarketplaces": {
    "typesafe-ai": { "source": { "source": "github", "repo": "typesafe-ai/skills" } },
    "caveman": { "autoUpdate": false }
  }
}
EOF

merge() { jq -n --slurpfile user "$1" --slurpfile tpl "$TPL" -f "$REPO/merge-settings.jq"; }
M="$(merge "$T/user.json")"
S="$(jq '.settings' <<< "$M")"
q() { jq -c "$1" <<< "$S"; }

# Preferences stay the user's.
check "model kept" '"opus[1m]"' "$(q .model)"
check "outputStyle kept" '"Concise"' "$(q .outputStyle)"
check "includeCoAuthoredBy kept" 'true' "$(q .includeCoAuthoredBy)"
check "env kept" '{"FOO":"bar"}' "$(q '.["env"]')"
check "user allow kept" 'true' "$(q '.permissions.allow | index("Bash(npm test)") != null')"
check "user plugin kept" 'true' "$(q '.enabledPlugins["typesafe@typesafe-ai"]')"
check "user turned a template plugin off, it stays off" 'false' "$(q '.enabledPlugins["humanizer@humanizer"]')"
check "user marketplace kept" '"typesafe-ai/skills"' "$(q '.extraKnownMarketplaces["typesafe-ai"].source.repo')"
check "marketplace autoUpdate kept" 'false' "$(q '.extraKnownMarketplaces.caveman.autoUpdate')"
check "template marketplace source set" '"JuliusBrussee/caveman"' "$(q '.extraKnownMarketplaces.caveman.source.repo')"
check "user hook kept" 'true' "$(q '[.hooks.PreToolUse[].hooks[].command] | index("my-edit-hook") != null')"
check "user Stop hook kept" '"say done"' "$(q '.hooks.Stop[0].hooks[0].command')"

# Security follows the template.
check "disableAllHooks removed" 'null' "$(q .disableAllHooks)"
check "skipDangerousModePermissionPrompt removed" 'null' "$(q .skipDangerousModePermissionPrompt)"
check "bypassPermissions removed" 'null' "$(q .permissions.defaultMode)"
check "sandbox is the template's" "$(jq -c .sandbox "$TPL")" "$(q .sandbox)"
check "statusLine is the template's" "$(jq -c .statusLine "$TPL")" "$(q .statusLine)"
check "deny-guard hook once" '1' "$(q '[.hooks.PreToolUse[].hooks[] | select(.command == "~/.claude/hooks/deny-guard.sh")] | length')"
check "every template deny rule" '[]' "$(jq -c --argjson s "$S" '.permissions.deny - $s.permissions.deny' "$TPL")"
check "every template ask rule" '[]' "$(jq -c --argjson s "$S" '.permissions.ask - $s.permissions.ask' "$TPL")"
check "user deny rule kept" 'true' "$(q '.permissions.deny | index("Read(~/secret/**)") != null')"
check "user ask rule kept" 'true' "$(q '.permissions.ask | index("Bash(docker *)") != null')"
check "no duplicate deny rules" "$(q '.permissions.deny | length')" "$(q '.permissions.deny | unique | length')"
check "template plugins on" 'true' "$(q '.enabledPlugins["caveman@caveman"]')"

# The installer says what it changed.
dropped="$(jq -r '.dropped[]' <<< "$M")"
for k in disableAllHooks skipDangerousModePermissionPrompt bypassPermissions sandbox statusLine; do
  grep -q "$k" <<< "$dropped" && ok || no "dropped list names $k"
done

# A fresh install (no settings yet) is the template, and merging twice changes nothing.
echo '{}' > "$T/empty.json"
check "fresh install is the template" "$(jq -cS . "$TPL")" "$(merge "$T/empty.json" | jq -cS .settings)"
check "fresh install drops nothing" '[]' "$(merge "$T/empty.json" | jq -c .dropped)"
jq '.settings' <<< "$M" > "$T/once.json"
check "merging twice is stable" "$(jq -cS . "$T/once.json")" "$(merge "$T/once.json" | jq -cS .settings)"
check "second merge drops nothing" '[]' "$(merge "$T/once.json" | jq -c .dropped)"

# --- one full install.sh run against a fake home ---
H="$T/home"
mkdir -p "$H/.claude/mods/claude-code-playground" "$T/bin"
if ! touch "$H/.claude/CLAUDE.md" 2>/dev/null; then
  echo "SKIP: full install run (this sandbox cannot create CLAUDE.md); run it in your own terminal"
else
  cp "$T/user.json" "$H/.claude/settings.json"
  # The vendored mods are already installed, so a run without a terminal must keep them.
  mkdir -p "$H/.claude/mods/vendored-mods/reflect-mod" "$H/.claude/mods/vendored-mods/cache-tax"
  jq '.enabledPlugins += {"reflect-mod@vendored-mods": true, "cache-tax@vendored-mods": true}' "$T/user.json" > "$H/.claude/settings.json"
  printf '%s\n' '#!/bin/bash' 'echo "$*" >> "$HOME/claude-calls.log"' > "$T/bin/claude"
  chmod +x "$T/bin/claude"
  out="$(HOME="$H" PATH="$T/bin:$PATH" bash "$REPO/install.sh" < /dev/null 2>&1)"
  code=$?
  check "install.sh exits 0" 0 "$code"
  [ "$code" -eq 0 ] || echo "$out" | tail -20
  F="$H/.claude/settings.json"
  check "real run keeps model" '"opus[1m]"' "$(jq -c .model "$F")"
  check "real run keeps vendored mods without a terminal" 'true' "$(jq -c '.enabledPlugins["reflect-mod@vendored-mods"]' "$F")"
  check "real run removes bypassPermissions" 'null' "$(jq -c .permissions.defaultMode "$F")"
  # claude plugin install turns a plugin back on, so the loop must skip the ones you turned off.
  check "real run keeps humanizer off" 'false' "$(jq -c '.enabledPlugins["humanizer@humanizer"]' "$F")"
  grep -q "plugin install humanizer@humanizer" "$H/claude-calls.log" && no "installer reinstalled a plugin you turned off" || ok
  grep -q "plugin install caveman@caveman" "$H/claude-calls.log" && ok || no "installer installs plugins that are on"
  ls "$H/.claude/settings.json.bak-"* >/dev/null 2>&1 && ok || no "backup written"
  [ -x "$H/.local/bin/claude-os" ] && ok || no "claude-os launcher installed"
  [ -f "$H/.claude/claude-os/serve.py" ] && ok || no "dashboard copied"
  [ ! -d "$H/.claude/claude-os/tests" ] && ok || no "dashboard tests not copied"
  grep -q "bypassPermissions" <<< "$out" && ok || no "installer reports what it removed"
  before="$(jq -cS . "$F")"
  HOME="$H" PATH="$T/bin:$PATH" bash "$REPO/install.sh" < /dev/null > /dev/null 2>&1
  check "second install changes nothing" "$before" "$(jq -cS . "$F")"
fi

echo "install: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
