"""Builds a fake home with a ~/.claude tree for the tests.

Secrets are assembled at runtime so no key-shaped string sits in the repo,
where GitHub secret scanning would flag it.
"""
import json
from pathlib import Path

SECRETS = [
    "sk-ant-" + "api03-" + "F1XTURE" * 6,
    "ghp_" + "F1xtureToken" * 3,
    "Bearer " + "f1xture-bearer-" + "x" * 20,
    "sk-ant-" + "oat01-" + "CRED" * 10,
    "transcript-" + "PROMPTSECRET",
    "dotenv-" + "SECRET-VALUE",
]
API_KEY, GH_TOKEN, BEARER, CRED, PROMPT_SECRET, DOTENV = SECRETS


# File names the Claude Code sandbox refuses to create in any folder. When a test run
# under Claude hits one, the file is left out and the tests that need it skip.
SANDBOX_BLOCKED = {"CLAUDE.md", ".mcp.json"}
skipped = set()


def _w(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(data if isinstance(data, str) else json.dumps(data))
    except PermissionError:
        if path.name not in SANDBOX_BLOCKED:
            raise
        skipped.add(path.name)


def _dot_claude(parent, real):
    # The sandbox refuses writes to **/.claude/settings.json and friends, even in temp;
    # a symlinked folder keeps the real path free of ".claude" so tests run under Claude too.
    real.mkdir(parents=True)
    parent.mkdir(parents=True, exist_ok=True)
    (parent / ".claude").symlink_to(real)


def _skill(name, model=None, body="Do the thing.\n"):
    fm = f"---\nname: {name}\ndescription: >\n  {name} skill\n  for tests\n"
    if model:
        fm += f"model: {model}\n"
    return fm + "---\n\n" + body


def _line(**o):
    return json.dumps(o) + "\n"


def transcript():
    def usage(inp=1, out=10, create=0, read=0):
        return {"input_tokens": inp, "output_tokens": out,
                "cache_creation_input_tokens": create, "cache_read_input_tokens": read,
                "cache_creation": {"ephemeral_5m_input_tokens": create, "ephemeral_1h_input_tokens": 0}}

    def asst(mid, ts, **u):
        return _line(type="assistant", sessionId="s1", timestamp=ts,
                     message={"id": mid, "model": "claude-opus-5-5", "role": "assistant",
                              "content": [{"type": "text", "text": "hi"}], "usage": usage(**u)})

    return "".join([
        _line(type="user", sessionId="s1", timestamp="2026-10-20T10:00:00Z",
              message={"role": "user", "content": "my key is " + PROMPT_SECRET}),
        asst("m1", "2026-10-20T10:00:05Z", create=1000),
        asst("m1", "2026-10-20T10:00:05Z", create=1000),  # streaming writes a message twice
        asst("m2", "2026-10-20T10:05:00Z", read=1000),
        # Idle 75 min: the system prompt is still cached, the conversation is written again.
        asst("m3", "2026-10-20T11:20:00Z", read=500, create=50000),
        asst("m4", "2026-10-20T11:21:00Z", read=50500, create=20000),  # a big tool result, not a reload
        "not json\n",
        _line(type="cost-state", sessionId="s1", totalCostUSD=1.2345),
    ])


def build_home(root):
    root = Path(root)
    home = root / "home"
    cl = home / ".claude"
    proj = home / "proj"
    tool_a = cl / "plugins/cache/official/tool-a/1.0.0"
    frozen_b = cl / "mods/local/frozen-b"
    _dot_claude(home, root / "home-dot-claude")
    _dot_claude(proj, root / "proj-dot-claude")

    _w(cl / "settings.json", {
        "permissions": {"deny": ["Bash(rm *)"], "ask": ["Bash(gh *)"], "allow": ["mcp__gh__search_code"]},
        "env": {"ANTHROPIC_API_KEY": API_KEY},
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": "~/.claude/hooks/deny-guard.sh"}]}]},
        "sandbox": {"enabled": True},
        "enabledPlugins": {"tool-a@official": True, "frozen-b@local": False, "helper@builtin": True},
    })
    _w(cl / ".credentials.json", {"token": CRED})
    _w(cl / "history.jsonl", _line(display="prompt with " + PROMPT_SECRET))
    _w(cl / "CLAUDE.md", "# rules\nbe nice\n")
    _w(cl / "skills/my-skill/SKILL.md", _skill("my-skill", body="x" * 40000))
    _w(cl / "skills/synced/bucket1/web-skill/SKILL.md", _skill("web-skill"))
    _w(cl / "skills/synced/bucket1/manifest.json", {"skills": ["web-skill"]})
    _w(cl / "skills/synced/1.abc.key", CRED)
    _w(cl / "projects/-proj/memory/MEMORY.md", "- [Note](note.md) — a note\n")
    _w(cl / "projects/-proj/memory/note.md", "---\nname: note\n---\nfact\n")
    _w(cl / "projects/-proj/s1.jsonl", transcript())

    _w(cl / "plugins/installed_plugins.json", {"version": 2, "plugins": {
        "tool-a@official": [{"scope": "user", "installPath": str(tool_a), "version": "1.0.0", "gitCommitSha": "abc123"}],
        "frozen-b@local": [{"scope": "user", "installPath": str(frozen_b), "version": "0.2.0"}],
        "anth-tool@anth": [{"scope": "user", "installPath": str(cl / "plugins/cache/anth/anth-tool/1.0.0"),
                            "version": "1.0.0"}],
    }})
    _w(cl / "plugins/known_marketplaces.json", {
        "official": {"source": {"source": "github", "repo": "x/official"}},
        "local": {"source": {"source": "directory", "path": str(cl / "mods/local")}},
        "anth": {"source": {"source": "github", "repo": "anthropics/some-plugins"}},
    })
    _w(tool_a / "skills/lint/SKILL.md", _skill("lint", model="haiku"))
    _w(tool_a / "agents/reviewer.md", _skill("reviewer", model="sonnet"))
    _w(tool_a / "commands/hello.md", "---\ndescription: say hello\n---\nhello\n")
    _w(tool_a / "hooks/hooks.json", {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo done"}]}]}})
    _w(tool_a / ".mcp.json", {"mcpServers": {"tool-a-mcp": {"command": "node", "env": {"K": GH_TOKEN}}}})
    _w(frozen_b / "skills/big/SKILL.md", _skill("big", body="y" * 40000))
    _w(frozen_b / "hooks/hooks.json", {"modules": ["./register.tsx"]})

    _w(home / ".claude.json", {
        "oauthAccount": {"emailAddress": "someone@example.com"},
        "mcpServers": {"gh": {"type": "stdio", "command": "gh-mcp", "env": {"GITHUB_TOKEN": GH_TOKEN}}},
        "projects": {str(proj): {"mcpServers": {"local-http": {"type": "http", "url": "http://x",
                                                                "headers": {"Authorization": BEARER}}}}},
    })

    _w(proj / ".claude/settings.json", {"permissions": {"allow": ["Bash(npm test)"]},
                                        "enabledPlugins": {"frozen-b@local": True}})
    _w(proj / ".claude/settings.local.json", {"permissions": {"deny": ["WebFetch"]}})
    _w(proj / ".claude/skills/proj-skill/SKILL.md", _skill("proj-skill"))
    _w(proj / ".mcp.json", {"mcpServers": {"proj-mcp": {"type": "sse", "url": "http://y"}}})
    _w(proj / ".env", "TOKEN=" + DOTENV)
    _w(proj / ".env.local", "TOKEN=" + DOTENV)
    _w(proj / "CLAUDE.md", "# project map\n")
    _w(home / ".ssh/id_ed25519", CRED)
    return home, proj
