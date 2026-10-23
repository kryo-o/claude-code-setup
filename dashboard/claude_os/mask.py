"""Hides who you are in an inventory: username, home path, project names, and the names of
your own skills, agents, commands and MCP servers. Public plugin names and every number stay,
so the page looks the same for a screenshot or a demo.
"""
import re

HOME = "/Users/you"
PROJECT = "~/projects/demo"
KEEP_FILES = {"CLAUDE.md", "CLAUDE.local.md", "MEMORY.md"}


def mask(inv):
    real_home = inv["home"]
    real_proj = inv.get("project")
    projects, names = {}, {}

    def project(dirname):
        return projects.setdefault(dirname, f"project-{len(projects) + 1}")

    def text(s):
        if not isinstance(s, str):
            return s
        if real_proj:
            s = s.replace(real_home + real_proj[1:], HOME + PROJECT[1:]).replace(real_proj, PROJECT)
        s = s.replace(real_home, HOME)
        s = re.sub(r"(\.claude/projects/)([^/]+)(/)",lambda m: m.group(1) + project(m.group(2)) + m.group(3), s)
        for real, fake in sorted(names.items(), key=lambda kv: -len(kv[0])):
            s = re.sub(rf"(?<![\w-]){re.escape(real)}(?![\w-])", fake, s)
        return s

    for s in inv["sessions"]:
        s["project"] = project(s["project"])

    for key, word in (("skills", "skill"), ("agents", "agent"), ("commands", "command")):
        n = 0
        for i in inv[key]:
            if i["source"].startswith("plugin:"):
                continue
            n += 1
            names[i["name"]] = f"{word}-{n}"
            i["name"], i["description"], i["proposals"] = names[i["name"]], "", []
            i["path"] = f"~/…/{i['name']}"

    n = 0
    for m in inv["mcp"]:
        if not m["source"].startswith("plugin:"):
            n += 1
            m["name"] = f"mcp-{n}"

    notes = 0
    for m in inv["memory"]:
        path = text(m["path"])
        head, _, name = path.rpartition("/")
        if name not in KEEP_FILES:
            notes += 1
            name = f"note-{notes}.md"
        m["path"] = f"{head}/{name}"

    st = inv["settings"]
    for layer in st["layers"]:
        layer["path"] = text(layer["path"])
    for r in st["rules"]:
        r["rule"] = text(r["rule"])
        for p in r.get("proposals", []):
            p["how"], p["text"] = text(p["how"]), text(p["text"])
    for h in st["hooks"]:
        h["command"] = text(h["command"])
    for p in inv["plugins"]:
        p["path"] = text(p["path"])
    inv["routines"]["items"] = [{k: ("…" if k in ("name", "prompt") else v) for k, v in t.items()}
                                for t in inv["routines"]["items"]]
    inv["warnings"] = [text(w) for w in inv["warnings"]]
    inv["home"], inv["project"] = HOME, PROJECT if real_proj else None
    return inv
