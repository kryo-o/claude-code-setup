import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from claude_os import propose, scan
from tests.helpers import build_home


class ProposeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home, self.proj = build_home(self.tmp.name)
        self.inv = propose.attach(scan.scan(self.home, project=self.proj))

    def tearDown(self):
        self.tmp.cleanup()

    def find(self, key, field, value):
        return next(i for i in self.inv[key] if i[field] == value)

    def test_every_proposal_is_text(self):
        for key in ("plugins", "skills", "agents", "commands"):
            for item in self.inv[key]:
                for p in item.get("proposals", []):
                    self.assertEqual(set(p), {"title", "how", "text"})
                    self.assertTrue(all(isinstance(v, str) for v in p.values()))

    def test_plugin_toggle(self):
        on = self.find("plugins", "id", "tool-a@official")["proposals"]
        off = self.find("plugins", "id", "helper@builtin")
        self.assertIn("claude plugin disable tool-a@official", [p["text"] for p in on])
        self.assertTrue(off["proposals"])

    def test_untrusted_plugin_id_is_quoted(self):
        p = propose.plugin({"id": "x@y; touch /tmp/pwned", "enabled": True})[0]
        self.assertEqual(p["text"], "claude plugin disable 'x@y; touch /tmp/pwned'")

    @unittest.skipUnless(shutil.which("patch"), "needs patch")
    def test_pin_model_diff_applies(self):
        skill = self.find("skills", "name", "proj-skill")
        diff = next(p["text"] for p in skill["proposals"] if "haiku" in p["title"])
        target = self.proj / ".claude/skills/proj-skill/SKILL.md"
        r = subprocess.run(["patch", "--dry-run", "-i", "-", str(target)], input=diff, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("+model: haiku", diff)

    def test_no_pin_for_pinned_or_plugin_skills(self):
        # lint already has a model; a plugin update would overwrite an edit to big.
        for name in ("lint", "big"):
            titles = [p["title"] for p in self.find("skills", "name", name).get("proposals", [])]
            self.assertFalse(any("Pin" in t for t in titles), name)

    def test_ask_rule_can_be_loosened_per_project(self):
        rules = {(r["kind"], r["rule"]): r for r in self.inv["settings"]["rules"]}
        p = rules[("ask", "Bash(gh *)")]["proposals"][0]
        self.assertEqual(json.loads(p["text"]), {"permissions": {"allow": ["Bash(gh *)"]}})
        self.assertIn("settings.local.json", p["how"])

    def test_deny_rule_gets_no_loosening(self):
        # Deny wins over allow in every layer, so a per-project allow would not work.
        rules = {(r["kind"], r["rule"]): r for r in self.inv["settings"]["rules"]}
        self.assertEqual(rules[("deny", "Bash(rm *)")].get("proposals", []), [])

    def test_propose_cannot_write_or_run(self):
        src = Path(propose.__file__).read_text()
        for bad in (r"\.write", r"write_text", r"subprocess", r"os\.system", r"popen", r"unlink", r"rename",
                    r"open\([^)]*['\"][wa]"):
            self.assertIsNone(re.search(bad, src), bad)


if __name__ == "__main__":
    unittest.main()
