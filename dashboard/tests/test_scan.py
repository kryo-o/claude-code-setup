import builtins
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from claude_os import scan
from tests import helpers
from tests.helpers import SECRETS, build_home


class ScanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.home, cls.proj = build_home(cls.tmp.name)
        cls.inv = scan.scan(cls.home, project=cls.proj, managed=None)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def by(self, key, field="name"):
        return {i[field]: i for i in self.inv[key]}

    # 1. inventory
    def test_permission_rules_keep_their_layer(self):
        rules = {(r["kind"], r["rule"]): r["source"] for r in self.inv["settings"]["rules"]}
        self.assertEqual(rules, {
            ("deny", "Bash(rm *)"): "user",
            ("ask", "Bash(gh *)"): "user",
            ("allow", "mcp__gh__search_code"): "user",
            ("allow", "Bash(npm test)"): "project",
            ("deny", "WebFetch"): "local",
        })

    def test_settings_hooks_listed(self):
        self.assertIn({"event": "PreToolUse", "matcher": "Bash", "command": "~/.claude/hooks/deny-guard.sh",
                       "source": "user"}, self.inv["settings"]["hooks"])

    def test_sandbox_state(self):
        self.assertTrue(self.inv["settings"]["sandbox"]["enabled"])

    def test_plugins(self):
        p = self.by("plugins", "id")
        self.assertEqual(set(p), {"tool-a@official", "frozen-b@local", "helper@builtin", "anth-tool@anth"})
        a, b = p["tool-a@official"], p["frozen-b@local"]
        self.assertEqual((a["version"], a["commit"], a["enabled"], a["frozen"]), ("1.0.0", "abc123", True, False))
        self.assertTrue(b["frozen"])
        self.assertTrue(b["enabled"], "project layer enables it over the user layer")
        self.assertEqual(a["hooks"], "command")
        self.assertEqual(b["hooks"], "mod")
        self.assertFalse(p["helper@builtin"]["installed"])

    def test_skills_from_every_source(self):
        s = self.by("skills")
        self.assertEqual({n: i["source"] for n, i in s.items()}, {
            "my-skill": "user", "web-skill": "claude.ai", "proj-skill": "project",
            "lint": "plugin:tool-a@official", "big": "plugin:frozen-b@local",
        })
        self.assertEqual(s["lint"]["model"], "haiku")
        self.assertIsNone(s["my-skill"]["model"])
        self.assertEqual(s["lint"]["description"], "lint skill for tests")
        self.assertGreater(s["my-skill"]["tokens"], 9000)
        self.assertTrue(s["my-skill"]["path"].startswith("~/.claude/skills/"))

    def test_skills_ranked_by_tokens(self):
        tokens = [i["tokens"] for i in self.inv["skills"]]
        self.assertEqual(tokens, sorted(tokens, reverse=True))

    def test_agents_and_commands(self):
        self.assertEqual(self.by("agents")["reviewer"]["model"], "sonnet")
        self.assertEqual(self.by("commands")["hello"]["description"], "say hello")

    def test_mcp_names_and_types_only(self):
        m = {(i["name"], i["source"]): i["type"] for i in self.inv["mcp"]}
        expected = {("gh", "user"): "stdio", ("local-http", "local"): "http"}
        if ".mcp.json" not in helpers.skipped:
            expected |= {("proj-mcp", "project"): "sse", ("tool-a-mcp", "plugin:tool-a@official"): "stdio"}
        self.assertEqual(m, expected)
        for i in self.inv["mcp"]:
            self.assertEqual(set(i), {"name", "type", "source"})

    def test_memory_files(self):
        paths = {i["path"] for i in self.inv["memory"]}
        expected = {"~/.claude/projects/-proj/memory/MEMORY.md", "~/.claude/projects/-proj/memory/note.md"}
        if "CLAUDE.md" not in helpers.skipped:
            expected |= {"~/.claude/CLAUDE.md", "~/proj/CLAUDE.md"}
        self.assertEqual(paths, expected)

    def test_claude_md_found(self):
        if not "CLAUDE.md" not in helpers.skipped:
            self.skipTest("this sandbox cannot create CLAUDE.md; run the tests in your own terminal")
        kinds = {i["path"]: i["kind"] for i in self.inv["memory"]}
        self.assertEqual(kinds["~/proj/CLAUDE.md"], "CLAUDE.md")

    def test_sessions_included(self):
        self.assertEqual([s["session"] for s in self.inv["sessions"]], ["s1"])

    def test_routines_missing_file(self):
        self.assertEqual(self.inv["routines"], {"exists": False, "items": []})

    def test_warns_on_auto_updating_third_party_plugin(self):
        self.assertTrue(any("tool-a@official" in w for w in self.inv["warnings"]))

    def test_large_skill_warning_only_for_skills_you_own(self):
        large = [w for w in self.inv["warnings"] if w.startswith("Skill ")]
        self.assertEqual(len(large), 1)
        self.assertIn("my-skill", large[0])

    def test_anthropic_marketplaces_count_as_first_party(self):
        self.assertFalse(any("anth-tool@anth" in w for w in self.inv["warnings"]))
        self.assertTrue(self.by("plugins", "id")["anth-tool@anth"]["installed"])

    def test_project_at_home_is_no_project(self):
        # claude-os run from ~ would otherwise list ~/.claude/settings.json as a project layer too.
        inv = scan.scan(self.home, project=self.home)
        self.assertIsNone(inv["project"])
        self.assertEqual([l["source"] for l in inv["settings"]["layers"]], ["user", "user-local"])

    def test_missing_home_does_not_crash(self):
        inv = scan.scan(Path(self.tmp.name) / "nobody", project=None, managed=None)
        self.assertEqual(inv["skills"], [])

    # 2. no secrets out
    def test_no_secret_reaches_the_output(self):
        out = json.dumps(self.inv)
        for s in SECRETS:
            self.assertNotIn(s, out)
        self.assertNotIn("someone@example.com", out)

    # 3. denied paths never opened
    def test_denied_paths_never_opened(self):
        opened = []
        real_open = builtins.open

        def spy(file, *a, **k):
            opened.append(str(file))
            return real_open(file, *a, **k)

        with mock.patch("builtins.open", spy), mock.patch("io.open", spy):
            scan.scan(self.home, project=self.proj, managed=None)
        self.assertTrue(opened, "spy saw no reads, so the test proves nothing")
        bad = [p for p in opened if scan.is_denied(p)]
        self.assertEqual(bad, [])
        names = {Path(p).name for p in opened}
        for n in (".env", ".env.local", ".credentials.json", "history.jsonl", "id_ed25519", "1.abc.key"):
            self.assertNotIn(n, names)

    def test_read_guard_refuses_denied_path(self):
        with self.assertRaises(PermissionError):
            scan.read_text(self.proj / ".env")


if __name__ == "__main__":
    unittest.main()
