import json
import os
import time
import unittest
from pathlib import Path

from claude_os import propose, scan
from claude_os.redact import PATTERNS


@unittest.skipUnless(os.environ.get("CLAUDE_OS_SMOKE"), "set CLAUDE_OS_SMOKE=1 to scan your real ~/.claude")
class SmokeTest(unittest.TestCase):
    def test_real_home(self):
        t = time.monotonic()
        inv = propose.attach(scan.scan(Path.home(), project=Path.cwd()))
        took = time.monotonic() - t
        out = json.dumps(inv)
        self.assertLess(took, 5, f"scan took {took:.1f}s")
        self.assertIsNone(PATTERNS.search(out), "a secret-shaped string reached the output")
        print(f"\n  {took:.2f}s, {len(inv['plugins'])} plugins, {len(inv['skills'])} skills, "
              f"{len(inv['sessions'])} sessions, {len(inv['warnings'])} warnings")


if __name__ == "__main__":
    unittest.main()
