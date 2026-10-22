# Changelog

All notable changes to this template are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

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

[1.1.3]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.3
[1.1.2]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.2
[1.1.1]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.1
[1.1.0]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.1.0
[1.0.1]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.0.1
[1.0.0]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.0.0
