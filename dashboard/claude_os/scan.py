"""Read-only inventory of a Claude Code install: settings, plugins, skills, agents,
commands, hooks, MCP servers, memory, sessions and routines.

Nothing here writes. Every file goes through read_text, which refuses the paths
the template's Read deny rules cover, and the result passes through redact.scrub.
"""
import json
import re
from pathlib import Path

from . import cost
from .redact import scrub

DENY_NAMES = {".env", ".credentials.json", "history.jsonl", ".zsh_history", ".bash_history", ".netrc",
              ".npmrc", ".pypirc", ".git-credentials", "credentials", "credentials.toml", "hosts.yml"}
DENY_DIRS = {".ssh", ".gnupg", ".aws", ".azure", ".kube", "gcloud", "Keychains", ".password-store", "keyrings"}
DENY_SUFFIXES = (".key", ".pem")
MAX_TEXT = 2 * 1024 * 1024
LARGE_SKILL = 5000


def is_denied(path):
    p = Path(path)
    return (p.name in DENY_NAMES or p.name.startswith(".env.") or p.name.endswith(DENY_SUFFIXES)
            or any(part in DENY_DIRS for part in p.parts))


def read_text(path):
    if is_denied(path):
        raise PermissionError(f"refusing to read {path}")
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read(MAX_TEXT)


def read_json(path):
    try:
        return json.loads(read_text(path))
    except (OSError, ValueError):
        return None


def frontmatter(text):
    """The simple key: value lines of a --- block, with > and | values folded to one line."""
    m = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    out, key = {}, None
    for line in (m.group(1).splitlines() if m else []):
        kv = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            out[key] = "" if val in (">", "|", ">-", "|-") else val.strip("'\"")
        elif key and line.startswith((" ", "\t")):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


class Scanner:
    def __init__(self, home, project, managed):
        self.home = Path(home)
        self.cl = self.home / ".claude"
        self.project = Path(project) if project else None
        self.managed = Path(managed) if managed else None
        self.warnings = []

    def short(self, path):
        s, h = str(path), str(self.home)
        return "~" + s[len(h):] if s.startswith(h + "/") else s

    def item(self, path, name, source):
        try:
            text = read_text(path)
        except OSError:
            return None
        fm = frontmatter(text)
        desc = " ".join(fm.get("description", "").split())
        return {"name": fm.get("name") or name, "description": desc[:300], "model": fm.get("model") or None,
                "tokens": len(text) // 4, "source": source, "path": self.short(path)}

    def items(self, base, kind, source):
        if not base or not base.is_dir():
            return []
        if kind == "skills":
            found = [(d / "SKILL.md", d.name) for d in sorted(base.iterdir()) if (d / "SKILL.md").is_file()]
        else:
            found = [(f, f.stem) for f in sorted(base.glob("*.md"))]
        return [i for i in (self.item(p, n, source) for p, n in found) if i]

    # --- settings ---
    def layers(self):
        L = [("user", self.cl / "settings.json"), ("user-local", self.cl / "settings.local.json")]
        if self.project:
            L += [("project", self.project / ".claude/settings.json"),
                  ("local", self.project / ".claude/settings.local.json")]
        if self.managed:
            L.append(("managed", self.managed))
        return [(src, path, read_json(path) or {}) for src, path in L]

    def settings(self, layers):
        rules, hooks, sandbox, enabled = [], [], {}, {}
        for src, _, s in layers:
            for kind in ("allow", "ask", "deny"):
                rules += [{"kind": kind, "rule": r, "source": src} for r in (s.get("permissions") or {}).get(kind, [])]
            for event, groups in (s.get("hooks") or {}).items():
                for g in groups:
                    for h in g.get("hooks", []):
                        hooks.append({"event": event, "matcher": g.get("matcher"), "command": h.get("command"),
                                      "source": src})
            sandbox.update({k: v for k, v in (s.get("sandbox") or {}).items() if not isinstance(v, (dict, list))})
            enabled.update(s.get("enabledPlugins") or {})
        if not sandbox.get("enabled"):
            self.warnings.append("The sandbox is off: Bash commands run with your full user access.")
        return {
            "layers": [{"source": src, "path": self.short(p), "exists": p.is_file(), "keys": sorted(s)}
                       for src, p, s in layers],
            "rules": rules, "hooks": hooks, "sandbox": sandbox,
        }, enabled

    # --- plugins ---
    def plugins(self, enabled):
        installed = (read_json(self.cl / "plugins/installed_plugins.json") or {}).get("plugins", {})
        markets = read_json(self.cl / "plugins/known_marketplaces.json") or {}
        out = []
        for pid in sorted(set(installed) | set(enabled)):
            market = pid.rsplit("@", 1)[-1]
            inst = (installed.get(pid) or [{}])[0]
            root = Path(inst["installPath"]) if inst.get("installPath") else None
            src = (markets.get(market) or {}).get("source", {})
            frozen = src.get("source") == "directory"
            first_party = market in ("claude-plugins-official", "builtin") or str(src.get("repo", "")).startswith("anthropics/")
            hj = read_json(root / "hooks/hooks.json") if root else None
            p = {"id": pid, "marketplace": market, "installed": bool(inst), "enabled": bool(enabled.get(pid)),
                 "version": inst.get("version"), "commit": inst.get("gitCommitSha"), "frozen": frozen,
                 "hooks": "mod" if hj and "modules" in hj else "command" if hj else None,
                 "path": self.short(root) if root else None, "_root": root}
            out.append(p)
            if inst and not frozen and not first_party:
                self.warnings.append(f"{pid} auto-updates from its author's repo, so new code reaches you unreviewed.")
        return out

    # --- MCP ---
    def mcp(self, plugins):
        def entries(servers, source):
            return [{"name": n, "type": v.get("type") or ("stdio" if "command" in v else "unknown"), "source": source}
                    for n, v in (servers or {}).items() if isinstance(v, dict)]
        cj = read_json(self.home / ".claude.json") or {}
        out = entries(cj.get("mcpServers"), "user")
        if self.project:
            out += entries(((cj.get("projects") or {}).get(str(self.project)) or {}).get("mcpServers"), "local")
            out += entries((read_json(self.project / ".mcp.json") or {}).get("mcpServers"), "project")
        for p in plugins:
            if p["_root"]:
                out += entries((read_json(p["_root"] / ".mcp.json") or {}).get("mcpServers"), "plugin:" + p["id"])
        return out

    # --- memory ---
    def memory(self):
        cands = [self.cl / "CLAUDE.md"]
        if self.project:
            cands += [self.project / n for n in ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md")]
        cands += sorted(self.cl.glob("projects/*/memory/*.md"))
        out = []
        for p in cands:
            if p.is_file():
                text = read_text(p)
                out.append({"path": self.short(p), "tokens": len(text) // 4, "lines": text.count("\n"),
                            "kind": p.name if p.name in ("CLAUDE.md", "CLAUDE.local.md", "MEMORY.md") else "memory"})
        return out

    # --- sessions ---
    def sessions(self):
        # shortcut: top-level transcripts only, subagent transcripts in <session>/ folders are skipped.
        out = []
        for p in self.cl.glob("projects/*/*.jsonl"):
            if not is_denied(p):
                s = cost.session(p)
                s["project"] = p.parent.name
                out.append(s)
        return sorted(out, key=lambda s: s["last"] or "", reverse=True)

    # --- routines ---
    def routines(self):
        path = self.cl / "scheduled_tasks.json"
        data = read_json(path)
        # shortcut: the file's shape is undocumented, so only a few well-known keys are shown.
        raw = data if isinstance(data, list) else (data or {}).get("tasks", []) if isinstance(data, dict) else []
        keep = ("id", "name", "cron", "schedule", "enabled", "prompt")
        items = [{k: (str(t[k])[:160] if k == "prompt" else t[k]) for k in keep if k in t}
                 for t in raw if isinstance(t, dict)]
        return {"exists": path.is_file(), "items": items}

    def run(self):
        layers = self.layers()
        settings, enabled = self.settings(layers)
        plugins = self.plugins(enabled)
        skills = (self.items(self.cl / "skills", "skills", "user")
                  + [i for b in sorted((self.cl / "skills/synced").glob("*/")) if b.is_dir()
                     for i in self.items(b, "skills", "claude.ai")])
        skills = [s for s in skills if s["name"] != "synced"]
        agents = self.items(self.cl / "agents", "agents", "user")
        commands = self.items(self.cl / "commands", "commands", "user")
        if self.project:
            pc = self.project / ".claude"
            skills += self.items(pc / "skills", "skills", "project")
            agents += self.items(pc / "agents", "agents", "project")
            commands += self.items(pc / "commands", "commands", "project")
        for p in plugins:
            if p["_root"]:
                src = "plugin:" + p["id"]
                skills += self.items(p["_root"] / "skills", "skills", src)
                agents += self.items(p["_root"] / "agents", "agents", src)
                commands += self.items(p["_root"] / "commands", "commands", src)
        skills.sort(key=lambda s: -s["tokens"])
        for s in skills:
            # Only skills you can edit; plugin skills are the author's to slim.
            if s["tokens"] > LARGE_SKILL and s["source"] in ("user", "project"):
                self.warnings.append(f"Skill {s['name']} is about {s['tokens']} tokens; slim it or split its references out.")
        mcp = self.mcp(plugins)
        for p in plugins:
            del p["_root"]
        return scrub({
            "home": str(self.home), "project": self.short(self.project) if self.project else None,
            "settings": settings, "plugins": plugins, "skills": skills, "agents": agents, "commands": commands,
            "mcp": mcp, "memory": self.memory(), "sessions": self.sessions(), "routines": self.routines(),
            "warnings": self.warnings,
            "unavailable": [
                "claude.ai projects, connectors and cloud routines: no local file holds them.",
                "Per-chat token cost of each MCP tool list: only the running engine knows it. Run /context.",
            ],
        })


def scan(home, project=None, managed=None):
    return Scanner(home, project, managed).run()
