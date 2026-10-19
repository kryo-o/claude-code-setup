# Security policy

## Reporting a problem

If you find a way past the sandbox config, the permission rules or `deny-guard.sh` that this template should catch, report it privately through GitHub's [private vulnerability reporting](../../security/advisories/new) instead of opening a public issue.

Include the command or input, what you expected to be blocked, and your Claude Code and macOS versions.

## What's in scope

- Commands that `deny-guard.sh` should block but doesn't.
- Settings in `settings.json` that weaken the sandbox or permission rules.
- Anything in `install.sh` that could damage a user's existing setup.

## Out of scope

- Bugs in Claude Code itself or its sandbox. Report those to Anthropic.
- Bugs in the plugins this template installs. Report those to each plugin's repo (see Credits in the README).
- Bypasses of `deny-guard.sh` alone while the sandbox is on. The hook is a speed bump by design, and the sandbox is the boundary. These are still welcome as regular issues.
