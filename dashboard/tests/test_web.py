import json
import shutil
import subprocess
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parent.parent / "web/lib.js"
NOW = "2026-10-23T12:00:00Z"
SESSIONS = [
    {"project": "-Users-kryo-projects-claude-code-setup", "last": "2026-10-23T09:00:00Z", "cost_usd": 3.0},
    {"project": "-Users-kryo-projects-claude-code-setup", "last": "2026-10-21T09:00:00Z", "cost_usd": 1.0},
    {"project": "-Users-kryo-projects-kryo-website", "last": "2026-10-23T08:00:00Z", "cost_usd": 2.0},
    {"project": "-Users-kryo", "last": "2026-10-22T08:00:00Z", "cost_usd": None},
    {"project": "-private-var-folders-x-T-tmp-abc", "last": "2026-08-01T08:00:00Z", "cost_usd": 9.0},
]


@unittest.skipUnless(shutil.which("node"), "needs node")
class LibTest(unittest.TestCase):
    def js(self, expr):
        prog = (f"const vm=require('vm');const c={{}};vm.createContext(c);"
                f"vm.runInContext(require('fs').readFileSync({json.dumps(str(LIB))},'utf8'),c);"
                f"c.S={json.dumps(SESSIONS)};c.NOW=new Date({json.dumps(NOW)});"
                f"console.log(JSON.stringify(vm.runInContext({json.dumps(expr)},c)))")
        r = subprocess.run(["node", "-e", prog], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_pretty_project(self):
        self.assertEqual(self.js("['-Users-kryo-projects-claude-code-setup','-Users-kryo','-Users-kryo-cc-denytest']"
                                 ".map(prettyProject)"), ["claude-code-setup", "~", "cc-denytest"])

    def test_daily_cost_last_n_days(self):
        days = self.js("dailyCost(S, 3, NOW)")
        self.assertEqual([d["day"] for d in days], ["2026-10-21", "2026-10-22", "2026-10-23"])
        self.assertEqual([d["usd"] for d in days], [1.0, 0, 5.0])

    def test_project_mix_top_and_other(self):
        mix = self.js("projectMix(S, 1, 30, NOW)")
        self.assertEqual(mix, [{"name": "claude-code-setup", "usd": 4.0}, {"name": "other", "usd": 2.0}])

    def test_clip_keeps_short_text_and_cuts_long(self):
        self.assertEqual(self.js("[clip('1.0.2', 8), clip('465f09344424', 8), clip('', 8)]"),
                         ["1.0.2", "465f093…", ""])

    def test_sphere_points_on_unit_sphere(self):
        r = self.js("sphere(200).map(([x,y,z]) => Math.hypot(x,y,z))")
        self.assertEqual(len(r), 200)
        self.assertTrue(all(abs(v - 1) < 1e-9 for v in r))


class StaticTest(unittest.TestCase):
    def test_page_loads_nothing_external(self):
        for f in [p for p in LIB.parent.iterdir() if p.suffix in (".html", ".js", ".css")]:
            # The SVG namespace is an identifier, not something the browser fetches.
            text = f.read_text().replace("http://www.w3.org/2000/svg", "")
            self.assertNotRegex(text, r"https?://", f.name)


if __name__ == "__main__":
    unittest.main()
