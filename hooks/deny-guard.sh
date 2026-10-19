#!/bin/bash
# PreToolUse hook (Bash matcher): greps the FULL command string for dangerous
# patterns, unlike permissions.deny globs which only match the literal prefix
# and are bypassed by wrapping the command in a loop/variable/subshell.
#
# Speed bump, not a boundary: text matching can always be out-spelled.
# The real boundary is sandbox.enabled in settings.json.
# Test: bash ~/.claude/hooks/deny-guard-test.sh
set -euo pipefail

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty')

[ -z "$COMMAND" ] && exit 0

deny() {
  jq -n --arg reason "$1" \
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":$reason}}'
  exit 0
}

# Scan scripts the command runs (bash x.sh, python x.py, ...), so writing a
# script and then executing it doesn't hide its contents.
# ponytail: one level deep only; a script that calls another script slips past.
SCAN="$COMMAND"
set -f  # split the command into words without expanding globs like * against the disk
for tok in $COMMAND; do
  tok="${tok//[\'\"]/}"
  case "$tok" in
    *.sh|*.bash|*.zsh|*.py|*.js|*.mjs|*.cjs|*.ts|*.pl|*.rb)
      f="${tok/#\~/$HOME}"
      [[ "$f" != /* && -n "$CWD" ]] && f="$CWD/$f"
      [ -f "$f" ] && SCAN+=$'\n'"$(head -c 200000 "$f" 2>/dev/null || true)"
      ;;
  esac
done
set +f

# Strip quotes and backslashes so "rm", r''m and \rm all read as rm.
TEXT=$(printf '%s' "$SCAN" | tr -d "'\"\\\\")
# Here-string, not a pipe: with pipefail, grep -q exiting early on a match makes
# the writer of a large input fail with SIGPIPE, which would turn a match into a miss.
has() { grep -qE "$1" <<< "$TEXT"; }

# A word not glued to letters, digits, _ . - (so /bin/rm and $(echo rm) match, rm.txt doesn't)
W='(^|[^[:alnum:]_.-])'
E='([^[:alnum:]_.-]|$)'

# --- obfuscated execution ---
grep -qE "\\\$'[^']*\\\\(x|[0-7]{3})" <<< "$SCAN" && deny "ANSI-C escaped command text is denied"
has "${W}eval${E}" && deny "eval is denied"
has 'base64[[:space:]]+(-d|-D|--decode)' && deny "base64 decode is denied"

# --- destructive commands ---
has "${W}rm${E}" && deny "rm is denied"
has "${W}rmdir${E}" && deny "rmdir is denied"
has "${W}unlink${E}" && deny "unlink is denied"
has "${W}(shred|srm|truncate)${E}" && deny "shred/srm/truncate is denied"
has "${W}find${E}.*-delete" && deny "find -delete is denied"
has "${W}dd${E}.*of=" && deny "dd of= is denied"
has "${W}mv${E}.*(/dev/null|\.Trash)" && deny "mv to /dev/null or Trash is denied"
has "${W}sudo${E}" && deny "sudo is denied"
has 'git\s+push\s+.*(--force|-f)\b' && deny "git push --force/-f is denied"
has 'git\s+reset\s+.*--hard' && deny "git reset --hard is denied"
has 'git\s+clean\s+.*-[a-zA-Z]*f[a-zA-Z]*d|git\s+clean\s+.*-[a-zA-Z]*d[a-zA-Z]*f' && deny "git clean -fd is denied"
has 'git\s+branch\s+.*-D\b' && deny "git branch -D is denied"
has 'osascript.*delete' && deny "osascript delete is denied"

# --- git and gh run outside the sandbox (excludedCommands), so block what turns them into code execution ---
# git accepts any unique prefix of a long option (--upl=, --rece=, --ex=), so match the shortest forms.
has 'git\s+(push|fetch|pull|ls-remote)\b.*--(upl|rece|ex[^i]|e(=|\s|$))' && deny "git --upload-pack/--receive-pack/--exec is denied"
has 'git\s+(-c|--config-env)(\s|=)' && deny "git -c config override is denied"
has 'GIT_(SSH|SSH_COMMAND|EXEC_PATH|ASKPASS|PROXY_COMMAND|CONFIG_COUNT|CONFIG_KEY_|CONFIG_VALUE_|CONFIG_PARAMETERS|CONFIG_GLOBAL|CONFIG_SYSTEM)' && deny "git environment overrides are denied"
# git config keys are case-insensitive (core.SSHCommand works), so match with -i.
grep -qiE 'git\s+config\b.*(core\.(sshCommand|hooksPath|fsmonitor|gitProxy)|protocol\..*allow|insteadOf)' <<< "$TEXT" && deny "git config keys that run commands are denied"
has 'git\s+credential\b' && deny "git credential is denied"
has 'gh\s+(extension|alias)\b' && deny "gh extensions and aliases are denied"
has 'gh\s+auth\s+(token|login|logout|refresh|setup-git|switch|git-credential)|--show-token|gh\s+auth\s+status\b.*\s-[a-zA-Z]*t' && deny "gh auth commands that touch the token are denied"
has 'gh\s+repo\s+delete' && deny "gh repo delete is denied"
grep -qiE 'gh\s+api\b.*(-X|--method)[[:space:]=]*delete' <<< "$TEXT" && deny "gh api DELETE is denied"
grep -qiE 'gh\s+api\b.*\bgraphql\b.*mutation' <<< "$TEXT" && deny "gh api graphql mutations are denied"
# A query read from a file (--input, -F query=@file) can't be checked for mutations, so deny it.
has 'gh\s+api\b.*\bgraphql\b.*(--input|=@)' && deny "gh api graphql with a query from a file is denied"

# --- delete APIs inside interpreters (python, node, ruby) ---
has 'os\.(remove|removedirs)|shutil\.rmtree|\.unlink\(|(rmSync|rmdirSync|unlinkSync)|fs\.(promises\.)?(rm|rmdir|unlink)\(|FileUtils\.rm|File\.delete' \
  && deny "file-deletion API call is denied"

# --- pipe into a shell ---
has '\|\s*(sh|bash|zsh)\b' && deny "piping into a shell interpreter is denied"

# --- sensitive credential / key paths ---
has '\.ssh/id_|\.pem\b' && deny "SSH private key path is denied"
has '\.aws/credentials' && deny "AWS credentials path is denied"
has '\.config/gcloud/' && deny "gcloud config path is denied"
has '\.azure/' && deny "Azure config path is denied"
has '\.gnupg/' && deny "GnuPG directory is denied"
has '\.zsh_history|\.bash_history' && deny "shell history file is denied"
has 'CloudDocs|Mobile Documents|com~apple~CloudDocs' && deny "iCloud CloudDocs path is denied"

# --- browser cookie / login-data files ---
has '(Google/Chrome|google-chrome|chromium|BraveSoftware).*(Cookies|Login Data)|Cookies\b.*Chrome|Login Data\b' && deny "browser cookie/login-data file is denied"
has 'cookies\.sqlite|logins\.json' && deny "Firefox cookie/login-data file is denied"

# --- password stores: macOS Keychains, GNOME keyrings, pass ---
has 'Library/Keychains' && deny "macOS Keychain path is denied"
has 'share/keyrings|\.password-store' && deny "password store path is denied"

# --- .env files ---
has '(^|[^a-zA-Z0-9_.])\.env(\.[a-zA-Z0-9_.-]+)?\b' && deny ".env file access is denied"

exit 0
