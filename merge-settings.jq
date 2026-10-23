# Merges this template into a user's existing settings.json.
# Security follows the template: sandbox, status line, the template's permission rules and hooks,
# and no keys that switch the guardrails off. Everything else stays the user's.
# Input: --slurpfile user <current settings> --slurpfile tpl <template, __HOME__ replaced>
# Output: {settings, dropped}; dropped names what was removed or replaced, for the installer to print.
# Used by install.sh and the manual install steps; tested by install-test.sh.

# Template entries first, then the user's extras. Merging twice gives the same list.
def union($a; $b): ($a // []) + (($b // []) - ($a // []));

# Per event: the user's hook entries that run none of the template's commands, then the template's.
def merge_hooks($uh; $th):
  reduce ($th | to_entries[]) as $e ($uh // {};
    [$e.value[].hooks[]?.command] as $cmds
    | .[$e.key] = ([(.[$e.key] // [])[] | select(([.hooks[]?.command] - $cmds) == [.hooks[]?.command])] + $e.value));

($user[0] // {}) as $u
| $tpl[0] as $t
| {
    settings: (
      ($t | del(.permissions, .sandbox, .hooks, .enabledPlugins, .extraKnownMarketplaces, .statusLine))
      * ($u | del(.permissions, .sandbox, .hooks, .enabledPlugins, .extraKnownMarketplaces, .statusLine,
                  .disableAllHooks, .skipDangerousModePermissionPrompt))
      | .statusLine = $t.statusLine
      | .sandbox = $t.sandbox
      | .permissions = (
          (($u.permissions // {}) | del(.allow, .deny, .ask)
            | if .defaultMode == "bypassPermissions" then del(.defaultMode) else . end)
          + {deny: union($t.permissions.deny; $u.permissions.deny), ask: union($t.permissions.ask; $u.permissions.ask)}
          + (if ($t.permissions.allow // $u.permissions.allow) != null
             then {allow: union($t.permissions.allow; $u.permissions.allow)} else {} end))
      | .hooks = merge_hooks($u.hooks; $t.hooks)
      # A plugin the user already turned off stays off; new template plugins come in on.
      | .enabledPlugins = ($t.enabledPlugins + ($u.enabledPlugins // {}))
      | .extraKnownMarketplaces = (($u.extraKnownMarketplaces // {}) * $t.extraKnownMarketplaces)
    ),
    dropped: [
      if $u.disableAllHooks != null then "disableAllHooks (it turns off the deny-guard hook)" else empty end,
      if $u.skipDangerousModePermissionPrompt != null then "skipDangerousModePermissionPrompt" else empty end,
      if $u.permissions.defaultMode == "bypassPermissions"
        then "permissions.defaultMode: bypassPermissions (it skips every permission prompt)" else empty end,
      if $u.sandbox != null and $u.sandbox != $t.sandbox then "sandbox: replaced with the template's" else empty end,
      if $u.statusLine != null and $u.statusLine != $t.statusLine then "statusLine: replaced with the template's" else empty end
    ]
  }
