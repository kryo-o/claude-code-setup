#!/bin/bash
# Feeds each case in deny-guard-cases.txt to deny-guard.sh as a fake Bash
# tool call and checks BLOCK/ALLOW. Nothing in the cases is executed.
dir="$(cd "$(dirname "$0")" && pwd)"
fail=0
while IFS='|' read -r want c; do
  [ -z "$want" ] && continue
  out=$(jq -n --arg c "$c" '{tool_input:{command:$c}}' | bash "$dir/deny-guard.sh")
  if [ -n "$out" ]; then got=BLOCK; else got=ALLOW; fi
  if [ "$got" != "$want" ]; then echo "FAIL want=$want got=$got: $c"; fail=1; fi
done < "$dir/deny-guard-cases.txt"

# A dangerous command followed by 300 KB of padding must still be blocked
# (regression test: a piped grep -q used to miss matches in large inputs).
big="$(printf 'r%s -rf x\n' m)$(head -c 300000 /dev/zero | tr '\0' a)"
out=$(jq -n --arg c "$big" '{tool_input:{command:$c}}' | bash "$dir/deny-guard.sh")
[ -n "$out" ] || { echo "FAIL want=BLOCK got=ALLOW: large input"; fail=1; }

[ "$fail" = 0 ] && echo "all cases pass"
exit "$fail"
