# Changelog

All notable changes to this template are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
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

[1.0.1]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.0.1
[1.0.0]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.0.0
