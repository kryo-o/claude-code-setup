#!/bin/bash
# Tests install-claude.sh with stand-ins for curl, the installer and the user's answer.
# Run: bash install-claude-test.sh
set -uo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
fail=0
pass=0

# Each case gets a fresh fake home and a PATH without any real claude on it.
setup() {
  T="$(mktemp -d "${TMPDIR:-/tmp}/install-claude-test.XXXXXX")"
  export HOME="$T/home"
  mkdir -p "$HOME" "$T/bin"
  export PATH="$T/bin:/usr/bin:/bin"
  export CURL_LOG="$T/curl.log"
  ANSWER=no
  # shellcheck source=install-claude.sh
  source "$REPO/install-claude.sh"
}
ask() { [ "$ANSWER" = yes ]; }

stub_curl() { # $1: installer body, or "fail"
  printf '%s\n' '#!/bin/bash' "echo \"\$*\" >> \"\$CURL_LOG\"" > "$T/bin/curl"
  if [ "$1" = fail ]; then
    echo 'exit 22' >> "$T/bin/curl"
  else
    # Write the installer to the file named after -o.
    printf '%s\n' 'while [ $# -gt 0 ]; do [ "$1" = -o ] && out="$2"; shift; done' "cat > \"\$out\" <<'EOS'" "$1" "EOS" >> "$T/bin/curl"
  fi
  chmod +x "$T/bin/curl"
}
GOOD_INSTALLER='mkdir -p "$HOME/.local/bin"; printf "#!/bin/bash\necho 2.1.0\n" > "$HOME/.local/bin/claude"; chmod +x "$HOME/.local/bin/claude"'

check() { # $1 name, $2 expected exit code, $3 actual
  if [ "$2" = "$3" ]; then pass=$((pass + 1)); else echo "FAIL: $1 (expected exit $2, got $3)"; fail=$((fail + 1)); fi
}
called_curl() { [ -s "$CURL_LOG" ]; }

# 1. claude already installed: nothing is downloaded
( setup; printf '#!/bin/bash\n' > "$T/bin/claude"; chmod +x "$T/bin/claude"; stub_curl "$GOOD_INSTALLER"
  ensure_claude >/dev/null; r=$?; called_curl && r=99; exit $r ); check "already installed" 0 $?

# 2. user says no: nothing is downloaded, and the step fails
( setup; stub_curl "$GOOD_INSTALLER"; ANSWER=no
  ensure_claude >/dev/null; r=$?; called_curl && r=99; exit $r ); check "user declines" 1 $?

# 3. user says yes: the official URL over HTTPS only, then claude is on PATH
( setup; stub_curl "$GOOD_INSTALLER"; ANSWER=yes
  ensure_claude >/dev/null || exit 1
  grep -q -- "--proto =https" "$CURL_LOG" || exit 2
  grep -q "https://claude.ai/install.sh" "$CURL_LOG" || exit 3
  command -v claude >/dev/null || exit 4 ); check "installs" 0 $?

# 4. download fails: the step fails and nothing runs
( setup; stub_curl fail; ANSWER=yes
  ensure_claude >/dev/null 2>&1; exit $? ); check "download fails" 1 $?

# 5. installer fails: the step fails
( setup; stub_curl 'exit 3'; ANSWER=yes
  ensure_claude >/dev/null 2>&1; exit $? ); check "installer fails" 1 $?

# 6. installer runs but claude is still missing: the step fails
( setup; stub_curl 'true'; ANSWER=yes
  ensure_claude >/dev/null 2>&1; exit $? ); check "claude still missing" 1 $?

echo "install-claude: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
