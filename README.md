# Claude Code secure setup template

A ready-to-use Claude Code configuration for macOS. It locks down what Claude can touch on your machine, shows the cost of each session in the status line, and installs a short, reviewed list of plugins. Copy it as is, or keep the security parts and swap the plugins for your own.

## What's inside

| File | Purpose |
|---|---|
| `settings.json` | Permissions, sandbox, hook, status line, plugins and marketplaces |
| `hooks/deny-guard.sh` | Blocks dangerous Bash commands, including disguised ones |
| `hooks/deny-guard-test.sh` and `hooks/deny-guard-cases.txt` | 44 test cases for the guard |
| `statusline.sh` | One-line status: model, context bar, cost, 5h/7d limits, git branch, plugin badges |
| `mods/vendored-mods/.claude-plugin/marketplace.json` | A local marketplace for frozen copies of third-party mods |

## How it works

### Three security layers

Each layer misses things the others catch.

The sandbox is the actual boundary. With `sandbox.enabled: true` and `allowUnsandboxedCommands: false`, every Bash command runs inside macOS Seatbelt. Commands can only write to the project folder and temp folders, and network access goes through a filter. `autoAllowBashIfSandboxed` skips most permission prompts, which is safe because the sandbox limits what a command can damage.

Permission rules come next. The `deny` list blocks reads of credentials: SSH keys, cloud credentials, browser cookies, the keychain, shell history, `.env` files and iCloud. It also blocks `rm`, `sudo`, force-pushes and `curl | bash`. The `ask` list makes Claude ask before installing packages, so dependencies don't get added without you noticing.

The `deny-guard.sh` hook covers a gap in those rules. Permission rules only match the start of a command, so `for f in x; do rm $f; done` or `r''m` gets past them. The hook searches the whole command, plus any script the command runs, for deletes, `eval`, base64-decoded commands, pipes into a shell and credential paths. Text matching can always be worked around, so treat the hook as a speed bump and rely on the sandbox. Run `bash ~/.claude/hooks/deny-guard-test.sh` to test it.

One quirk: the hook decides which scripts to read by file extension. If a harmless command mentions a `.sh` or `.ts` file that happens to contain `eval` or `.env`, the hook blocks it.

### Third-party mods are frozen after review

Plugins and mods run code on your machine, and an update can replace that code with anything. The official Anthropic plugins update normally. The two third-party mods get more access than unreviewed code should have: `reflect-mod` writes to `CLAUDE.md`, and `cache-tax` sends model requests in the background. So the template installs them from a local `directory` marketplace, pinned to reviewed commits. They only change when you copy in a new version yourself.

| Mod | Source | Reviewed commit |
|---|---|---|
| reflect-mod 3.3.0 | `bayramannakov/claude-reflect` | `b6c42326903af3dd2bf3772b979730a44d8548ca` |
| cache-tax 2.2.1 | `karanb192/claude-code-mods` | `06cac47ec125a41a4aeeb78a6b006bec8cc6d6ed` |

This repo doesn't include their code. The install steps below have you download and review it yourself.

### Plugins

From Anthropic's official marketplace:
- `security-guidance` warns about risky code as files are edited and reviews the changes at the end of each turn.
- `claude-security` runs a deep scan on demand and checks each finding before reporting it.
- `mattpocock-skills` adds skills for TDD, debugging, code review, PR writing and more.
- `blast-radius` and `replay-theater` come from `anthropics/claude-code-playground`. The first previews what a risky shell command would change; the second replays Claude's edits as diffs.

From the community:
- `caveman` makes replies terse, which saves output tokens.
- `ponytail` pushes Claude toward the simplest code that works (YAGNI, standard library first).
- `humanizer` removes AI-sounding patterns from prose.
- `reflect-mod` turns your corrections into `CLAUDE.md` rules, and you approve each one.
- `cache-tax` warns before an expensive resend after the prompt cache expires, and `/keepwarm` keeps the cache alive while you're away.

Optional, for specific kinds of work. Delete the ones you don't need from `settings.json` before step 4:
- `commercial-legal` and `privacy-legal` (Anthropic) review contracts, data processing agreements and privacy impact assessments.
- `claude-seo` runs SEO audits.
- `nateherk-design` builds landing pages that animate as you scroll.

### Status line

```
Opus | ████░░░░░░ 42% | $1.50 | 5h:12% 7d:30% | ⎇ main | [CAVEMAN] | [PONYTAIL]
```

It shows how full the context window is, what the session has cost and how much of your plan's usage limits you've used, so a runaway session is easy to spot. It finds the plugin badges by searching the plugin cache, so they survive plugin updates. It needs `jq`, which comes with macOS 15 and later.

## Install (macOS)

### Step 0: prepare

Clone this repo. Back up your current `~/.claude/settings.json` if you have one, because step 3 overwrites it. Make sure `jq` is installed, since the install loop and the status line both use it:
```bash
which jq || brew install jq
```

### Step 1: get the Anthropic playground mods

```bash
mkdir -p ~/.claude/mods
git clone https://github.com/anthropics/claude-code-playground ~/.claude/mods/claude-code-playground
```

### Step 2: freeze the third-party mods

Install each mod from upstream, review it, copy it into your local marketplace, then remove the upstream version:
```bash
claude plugin marketplace add bayramannakov/claude-reflect
claude plugin install reflect-mod@claude-reflect-marketplace
claude plugin marketplace add karanb192/claude-code-mods
claude plugin install cache-tax@claude-code-mods
```
Read the code in `~/.claude/plugins/cache/claude-reflect-marketplace/reflect-mod/<version>/hooks/` and `~/.claude/plugins/cache/claude-code-mods/cache-tax/<version>/hooks/`. If the versions are newer than the ones in the table above, the code hasn't been reviewed yet, so read it closely.

Then copy them and remove the upstream installs:
```bash
V=~/.claude/mods/vendored-mods; C=~/.claude/plugins/cache
mkdir -p $V
rsync -a --exclude .in_use $C/claude-reflect-marketplace/reflect-mod/*/ $V/reflect-mod/
rsync -a --exclude .in_use --exclude site --exclude docs --exclude .github $C/claude-code-mods/cache-tax/*/ $V/cache-tax/
claude plugin uninstall reflect-mod@claude-reflect-marketplace
claude plugin uninstall cache-tax@claude-code-mods
claude plugin marketplace remove claude-reflect-marketplace
claude plugin marketplace remove claude-code-mods
```

### Step 3: copy this config in

Run these from inside this repo's folder:
```bash
cp -R mods/vendored-mods/.claude-plugin ~/.claude/mods/vendored-mods/
cp settings.json statusline.sh ~/.claude/
mkdir -p ~/.claude/hooks && cp hooks/* ~/.claude/hooks/ && chmod +x ~/.claude/hooks/deny-guard.sh
sed -i '' "s#__HOME__#$HOME#g" ~/.claude/settings.json
```

### Step 4: install every marketplace and plugin

Don't count on the prompts Claude Code shows at first start. Copying `settings.json` on its own can leave plugins half-installed, and some (caveman and ponytail, for example) then fail on startup. This loop reads both lists from your new `settings.json`, removes any existing copy of each plugin and installs it again. If plugins break later, run it again:
```bash
S=~/.claude/settings.json
claude plugin marketplace add anthropics/claude-plugins-official   # usually already there
for m in $(jq -r '.extraKnownMarketplaces[].source | .repo // .path' $S); do
  claude plugin marketplace add "$m"
done
for p in $(jq -r '.enabledPlugins | keys[] | select(endswith("@builtin") | not)' $S); do
  claude plugin uninstall "$p" 2>/dev/null
  claude plugin install "$p"
done
```
You can ignore "already added" and "not installed" messages. Each install line should end with `✔ Successfully installed`.

### Step 5: check and start

```bash
bash ~/.claude/hooks/deny-guard-test.sh   # should print: all cases pass
claude
```
In Claude Code, run `/plugin` and check that every plugin listed in `settings.json` is installed (14 if you kept them all). The status line should appear at the bottom of the screen.

## Moving to another machine

Copy `settings.json`, `statusline.sh`, `hooks/` and `mods/` from `~/.claude`. Leave out `plugins/cache` and `plugins/marketplaces`. On the new machine:

1. Unzip into your home folder.
2. If your username is different, fix the paths: `sed -i '' "s#/Users/OLDNAME#$HOME#g" ~/.claude/settings.json`.
3. Run the step 4 loop to install every plugin.

## Notes

- Tested on macOS only. The permission paths (Keychains, `Library/Application Support`) and `sed -i ''` won't work as written on Linux.
- `cache-tax` pings and `security-guidance` reviews are model calls, so they count toward your plan's limits.
- Keep the sandbox on. The hook and the permission rules can be worked around; the sandbox is what actually limits damage.
