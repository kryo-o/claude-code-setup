# Changelog

All notable changes to this template are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Demo GIF in the README and a `demo/` folder with the script that records it (`vhs demo/demo.tape`).

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

[1.0.0]: https://github.com/kryo-o/claude-code-setup/releases/tag/v1.0.0
