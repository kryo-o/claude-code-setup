import json
import tempfile
import unittest

from claude_os import propose, scan
from claude_os.mask import mask
from tests import helpers
from tests.helpers import build_home


class MaskTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.home, cls.proj = build_home(cls.tmp.name)
        cls.real = propose.attach(scan.scan(cls.home, project=cls.proj))
        cls.inv = mask(json.loads(json.dumps(cls.real)))
        cls.out = json.dumps(cls.inv)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_no_home_path_or_project_names(self):
        for s in (str(self.home), str(self.proj), "-proj", '"~/proj"', "~/proj/"):
            self.assertNotIn(s, self.out, s)
        self.assertIn("~/projects/demo/.claude/settings.json", self.out)

    def test_personal_skills_and_mcp_renamed(self):
        for s in ("my-skill", "web-skill", "proj-skill", "local-http", '"gh"'):
            self.assertNotIn(s, self.out, s)

    def test_public_plugin_names_kept(self):
        kept = ["tool-a@official", "lint", "reviewer"]
        if ".mcp.json" not in helpers.skipped:
            kept.append("tool-a-mcp")
        for s in kept:
            self.assertIn(s, self.out, s)

    def test_numbers_and_shape_kept(self):
        self.assertEqual(set(self.inv), set(self.real))
        self.assertEqual(len(self.inv["skills"]), len(self.real["skills"]))
        self.assertEqual([s["cost_usd"] for s in self.inv["sessions"]], [s["cost_usd"] for s in self.real["sessions"]])
        self.assertEqual(self.inv["sessions"][0]["project"], "project-1")

    def test_same_name_masks_the_same_way(self):
        # Sessions and memory files of one project must still line up after masking.
        mem = [m["path"] for m in self.inv["memory"] if "/projects/" in m["path"]]
        self.assertTrue(mem and all("/projects/project-1/" in p for p in mem), mem)

    def test_personal_proposals_dropped(self):
        # A pin-model diff quotes the skill file itself.
        own = [s for s in self.inv["skills"] if not s["source"].startswith("plugin:")]
        self.assertTrue(own)
        self.assertTrue(all(s["proposals"] == [] for s in own))


if __name__ == "__main__":
    unittest.main()
