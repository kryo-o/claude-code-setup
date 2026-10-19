#!/bin/bash
# Claude Code status line: model, context bar, cost, 5h/7d limits, git branch, plugin badges.
# C locale: in locales with a decimal comma (de_DE, pl_PL...), printf rejects "42.5".
export LC_ALL=C
in=$(cat)
j() { echo "$in" | jq -r "$1 // empty"; }

model=$(j .model.display_name)
pct=$(j .context_window.used_percentage)
cost=$(j .cost.total_cost_usd)
five=$(j .rate_limits.five_hour.used_percentage)
week=$(j .rate_limits.seven_day.used_percentage)
dir=$(j .workspace.current_dir)

out="\033[36m${model}\033[0m"

if [ -n "$pct" ]; then
  p=$(printf '%.0f' "$pct")
  f=$((p / 10)); [ "$f" -gt 10 ] && f=10
  bar=""; for i in 1 2 3 4 5 6 7 8 9 10; do [ "$i" -le "$f" ] && bar+="█" || bar+="░"; done
  out+=" | ${bar} ${p}%"
fi

[ -n "$cost" ] && out+=" | $(printf '$%.2f' "$cost")"

lim=""
[ -n "$five" ] && lim+="5h:$(printf '%.0f' "$five")%"
[ -n "$week" ] && lim+="${lim:+ }7d:$(printf '%.0f' "$week")%"
[ -n "$lim" ] && out+=" | $lim"

br=$(git -C "${dir:-.}" --no-optional-locks branch --show-current 2>/dev/null)
[ -n "$br" ] && out+=" | ⎇ $br"

# Badges: newest installed version of each plugin (glob survives updates).
latest() { ls -d $1 2>/dev/null | sort -V | tail -1; }
for s in \
  "$(latest "$HOME/.claude/plugins/cache/caveman/caveman/*/src/hooks/caveman-statusline.sh")" \
  "$(latest "$HOME/.claude/plugins/cache/ponytail/ponytail/*/hooks/ponytail-statusline.sh")"; do
  [ -n "$s" ] && b=$(bash "$s" </dev/null 2>/dev/null) && [ -n "$b" ] && out+=" | $b"
done

printf '%b\n' "$out"
