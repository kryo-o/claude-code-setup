"""Turns inventory items into proposed changes: text the user applies, never applied here."""
import difflib
import json
import shlex

from .scan import read_text

PIN_MODELS = ("haiku", "sonnet")
RUN = "Run it in your terminal, or in Claude Code with ! in front."


def _p(title, how, text):
    return {"title": title, "how": how, "text": text}


def plugin(p):
    verb = "disable" if p.get("enabled") else "enable"
    return [_p(f"{verb.capitalize()} {p['id']}", RUN, f"claude plugin {verb} {shlex.quote(p['id'])}")]


def pin_model(path, display, model):
    """A unified diff that adds `model:` to a file's frontmatter, or None when it has none."""
    try:
        old = read_text(path)
    except OSError:
        return None
    lines = old.splitlines(True)
    if not lines or lines[0].strip() != "---":
        return None
    end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), None)
    if end is None:
        return None
    new = lines[:end] + [f"model: {model}\n"] + lines[end:]
    diff = "".join(difflib.unified_diff(lines, new, fromfile=display, tofile=display))
    return _p(f"Pin to {model}",
              f"Save as pin.diff, check it still works on the smaller model, then run: patch {shlex.quote(display)} < pin.diff",
              diff)


def item(i, home):
    # Plugin files are replaced on every update, so an edit there would not last.
    if i.get("model") or i["source"].startswith("plugin:"):
        return []
    path = home + i["path"][1:] if i["path"].startswith("~") else i["path"]
    return [p for p in (pin_model(path, i["path"], m) for m in PIN_MODELS) if p]


def rule(r, project):
    # Deny wins over allow in every settings layer, so only ask rules can be loosened per project.
    if r["kind"] != "ask" or r["source"] != "user" or not project:
        return []
    return [_p("Allow in this project only",
               f"Merge into {project}/.claude/settings.local.json yourself; Claude may not edit that file.",
               json.dumps({"permissions": {"allow": [r["rule"]]}}, indent=2))]


def attach(inv):
    for p in inv["plugins"]:
        p["proposals"] = plugin(p)
    for key in ("skills", "agents"):
        for i in inv[key]:
            i["proposals"] = item(i, inv["home"])
    for r in inv["settings"]["rules"]:
        r["proposals"] = rule(r, inv["project"])
    return inv
