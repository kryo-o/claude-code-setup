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
[ "$fail" = 0 ] && echo "all cases pass"
exit "$fail"
