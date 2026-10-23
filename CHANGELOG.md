# Changelog

All notable changes to this template are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [1.2.1] - 2026-10-23

### Fixed
- Re-running `install.sh` turned back on any plugin you had turned off. The merge kept it off, but the plugin loop then reinstalled every plugin in `enabledPlugins`, and `claude plugin install` enables what it installs. The loop, and the manual Step 4 loop in the README, now install only plugins set to `true`. Covered in `install-test.sh`.

## [1.2.0] - 2026-10-23

### Added
- `dashboard/`: Claude OS, a read-only local web page over your Claude Code install. It lists settings layers and the file each permission rule comes from, plugins (frozen or auto-updating), skills ranked by size with their pinned model, agents, commands, hooks, MCP servers, `CLAUDE.md` and memory files, session costs, and what cold-cache reloads cost. Changes come as commands or diffs you apply yourself. Python 3 standard library only, with 67 tests covering secret redaction, denied paths, server hardening, cost maths, masking and proposals.
- `claude-os` command: the installer copies the dashboard to `~/.claude/claude-os` and adds a launcher to `~/.local/bin` that opens it for the current folder. `Edit` deny rules keep Claude out of both, since they run outside the sandbox.
- `claude-os --mask` hides your username, paths, project names and the names of your own skills, agents and MCP servers, for screenshots and demos.
- `install.sh` installs Claude Code with Anthropic's installer when `claude` is missing, after asking. Before, it stopped with "Missing: claude". The step has its own tests in `install-claude-test.sh`.
- `demo/dashboard-gif.sh` turns a screen recording of the dashboard into the README GIF.

### Fixed
- Re-running `install.sh` replaced your whole `settings.json` with the template, so your model, output style, extra plugins and own permission rules were lost (a backup was kept). It now merges with `merge-settings.jq`: your settings stay, the sandbox, status line, deny-guard hook and template rules follow the template, and settings that switch the guardrails off are removed and listed. Tested in `install-test.sh`.
- Run without a terminal, for example with `!` inside Claude, the installer took the mods question as "no" and removed `reflect-mod` and `cache-tax`. It now keeps mods that are already installed.
- `claude-os --mask` showed the names of your own MCP servers inside permission rules such as `mcp__<name>__tool`, and the names of plugins from your own local marketplaces. Both are masked now.

## [1.1.7] - 2026-10-23

### Changed
- The reviewed code of `reflect-mod` 3.3.0 and `cache-tax` 2.2.1 now ships in `mods/vendored-mods/`, and the installer copies it from there. Before, it downloaded the latest upstream release and only warned if the version number differed, so new or swapped code could get frozen after a single "y". Both copies match the reviewed commits byte for byte, and both are MIT licensed.
- Re-running the installer now replaces `~/.claude/mods/vendored-mods/reflect-mod` and `cache-tax` with the repo's copies, so a reviewed upgrade reaches you. Before, existing copies were kept.

### Fixed
- `install.sh` failed on Linux at the deny-guard self-test with `jq: Argument list too long`. The 300 KB test input went to jq as one argument, and Linux caps a single argument at 128 KB. It now goes through stdin.
- README: cache-tax's source repo is `karanb192/cache-tax`, not `karanb192/claude-code-mods`.

## [1.1.6] - 2026-10-22

### Added
- README: a "What it protects against" table of the attacks the template stops and how, and a note at the top that the setup puts security before convenience. Loosen one project in its `.claude/settings.local.json`, and leave the global settings as they are.

## [1.1.5] - 2026-10-22

### Changed
- README: the security layers section is split into the sandbox, permission rules and deny-guard, with a table of what each permission rule covers and why. No settings changed.

## [1.1.4] - 2026-10-22

### Fixed
- The `CLAUDE.md` and `CLAUDE.local.md` `ask` rules only matched that exact case. On macOS, a write to `claude.md` changes the same file, so the rules now match any case.
- `sandbox.filesystem.denyWrite` for `CLAUDE.md` and `CLAUDE.local.md` only covered your home folder. It now uses `//**/` and covers projects anywhere, such as `/Volumes` or `/opt`.

## [1.1.3] - 2026-10-22

### Added
- `ask` rules for project `CLAUDE.md` and `CLAUDE.local.md`. Every session loads them as instructions, and they can be committed, so a prompt injection saved there would last and spread to everyone who clones the repo.
- `sandbox.filesystem.denyWrite` for `CLAUDE.md` and `CLAUDE.local.md` under your home folder, so shell commands and the scripts they run can't write them and edits go through the `ask` prompt. deny-guard also blocks shell writes to them (`>`, `tee`, `sed -i`, `cp`, `mv`, any letter case) as a second layer. 9 new guard test cases.

### Fixed
- `.git` deny rules missed submodule and worktree git folders (`.git/modules/<name>/hooks`, `config`, and `config.worktree`), which `git push` and `pull --recurse-submodules` use outside the sandbox.

## [1.1.2] - 2026-10-22

### Added
- README section on loosening the rules for one project with `.claude/settings.local.json`, and what project settings can't override.
- `ask` rule for writes to Claude Code's memory (`~/.claude/projects/*/memory/**`), which every later session loads and which Claude otherwise saves without asking.

### Fixed
- Security: Claude could write a project's `.claude/settings.local.json` or `.claude/settings.json`, which override user settings and can turn off the sandbox, add allow rules or add hooks. Claude Code only asks before these writes, and in auto mode a classifier decides. `Edit` is now denied on both files in every folder, and on project `.claude/hooks`, `skills`, `agents`, `commands`, `rules` and `.mcp.json`.
- `.git/hooks` and `.git/config` deny rules only matched under the current folder. They now use `//**/` and match anywhere.
- `Edit` denied on `~/.config/git` and `~/.config/gh`, which git and `gh` read when they run outside the sandbox, plus `~/.claude/rules`, `~/.zlogin`, `~/.bash_login` and fish config.
- `Read` denied on `~/.claude/.credentials.json` (Claude Code's login on Linux), `~/.git-credentials`, `~/.config/git/credentials`, `~/.pypirc` and `~/.cargo/credentials.toml`.

## [1.1.1] - 2026-10-19

### Fixed
- deny-guard: `gh api graphql` with a query read from a file (`--input`, `-F query=@file`) bypassed the mutation check. Such queries are now denied, and the mutation check also matches when `graphql` comes after other options.
- deny-guard: git config keys are matched case-insensitively (`core.SSHCommand`), and `git credential` and `gh auth git-credential` are blocked. `git push --e=` (the shortest abbreviation of `--exec`) is caught. 8 new guard test cases.

## [1.1.0] - 2026-10-19

### Added
- `git push`, `pull` and `fetch` and the `gh` subcommands `repo`, `release`, `pr`, `issue` and `api` run outside the sandbox (`excludedCommands`), so Claude can use GitHub after you approve each command (`ask` rules).
- deny-guard and permission rules block the forms of those commands that could run arbitrary code or leak the token: `git --upload-pack`, `--receive-pack`, `--exec` and `-c`, `gh extension`, `gh alias`, `gh auth token`, `gh repo delete` and `gh api` DELETE calls. `Edit` is denied on `.git/hooks` and `.git/config`. deny-guard also blocks git environment overrides (`GIT_SSH_COMMAND`, `GIT_EXEC_PATH`, `GIT_CONFIG_*`) and `git config` keys that run commands (`core.sshCommand`, `core.hooksPath`, `core.fsmonitor`, `protocol.*.allow`, `insteadOf`). The git checks also catch abbreviated options (`--upl=`, `--rece=`, `--ex=`), the `gh auth` checks cover every subcommand that touches the token (including `gh auth status -t`), and `gh api` DELETE matching ignores case and also covers GraphQL mutations. 35 new guard test cases.
- `Edit` deny rules for Claude Code's own config (settings, hooks, plugins, mods, skills, agents, commands, global `CLAUDE.md`, `~/.claude.json`), shell startup files, `~/.gitconfig`, `~/.ssh`, and login items (macOS LaunchAgents, Linux systemd user units and autostart).

## [1.0.1] - 2026-10-19

### Added
- Demo GIF in the README and a `demo/` folder with the script that records it (`vhs demo/demo.tape`).
- Linux support, including WSL2. The installer checks for `bubblewrap` and `socat`, which the Linux sandbox needs.
- Permission rules and deny-guard patterns for Linux credential paths: Chrome, Chromium and Brave profiles in `~/.config`, Firefox in `~/.mozilla`, GNOME keyrings and `pass`. Five new guard test cases (49 total).

- Disclaimer in the README, and a note at the end of the installer, about unfrozen third-party plugins updating from their authors.

### Changed
- Manual install steps no longer use the macOS-only `sed -i ''`.
- `statusline.sh` moved to `hooks/statusline.sh`. The status line runs outside the sandbox, so it now lives in a folder the sandbox always protects from writes.
- The installer shows which version of each third-party mod it downloaded and warns if it isn't the reviewed one.

### Fixed
- Security: `deny-guard.sh` could miss a dangerous command in a large input (over about 64 KB, for example a long script run with `bash x.sh`). With `pipefail` on, `grep -q` stopping at the first match made the pipe fail, which counted as no match. Added a regression test.
- `deny-guard.sh` no longer expands `*` in commands against files on disk while looking for scripts.
- The status line showed `0%` and `$0.00` in locales that use a decimal comma, such as German or Polish.
- The installer's plugin loops could lose items when `claude` read from standard input, and broke on a home folder with a space in its path.
- The installer no longer uses `sed` to fill in the home path, which broke on paths containing `&` or `#`.

## [1.0.0] - 2026-10-19

### Added
- `install.sh`, a one-command installer that backs up existing settings, freezes reviewed third-party mods, installs every plugin and runs the guard tests.
- `settings.json` with sandbox, permission deny and ask lists, the deny-guard hook, the status line and 15 plugins.
- Context7 plugin plus a `CLAUDE.md` rule that makes Claude check current library docs before writing code.
- `deny-guard.sh` hook that scans whole Bash commands for deletes, `eval`, encoded commands, pipes into a shell and credential paths, with 44 test cases.
- `statusline.sh` showing model, context bar, session cost, 5h and 7d usage limits, git branch and plugin badges.
- Local `vendored-mods` marketplace for reviewed copies of `reflect-mod` 3.3.0 and `cache-tax` 2.2.1.
- Install guide with a loop that reinstalls every marketplace and plugin.
- `SECURITY.md` with private reporting, plus issue templates for bugs and deny-guard false positives.

[1.1.7]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.7
[1.1.6]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.6
[1.1.5]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.5
[1.1.4]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.4
[1.1.3]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.3
[1.1.2]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.2
[1.1.1]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.1
[1.1.0]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.0
[1.0.1]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.0.1
[1.0.0]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.0.0
