import json
import unittest

from claude_os.redact import R, scrub
from tests.helpers import API_KEY, BEARER, CRED, GH_TOKEN


class RedactTest(unittest.TestCase):
    def test_secret_keys_lose_their_values(self):
        out = scrub({"env": {"TOKEN": "plain-value"}, "headers": {"X": "v"}, "apiKey": "abc", "name": "keep"})
        self.assertEqual(out, {"env": {"TOKEN": R}, "headers": {"X": R}, "apiKey": R, "name": "keep"})

    def test_secret_shaped_strings_anywhere(self):
        for s in (API_KEY, GH_TOKEN, BEARER, CRED, "AKIA" + "A" * 16, "xoxb-" + "1" * 12):
            out = json.dumps(scrub({"deep": [{"command": f"run --key {s} now"}]}))
            self.assertNotIn(s, out)
            self.assertIn("run --key", out)

    def test_plain_text_untouched(self):
        self.assertEqual(scrub(["Bash(rm *)", 3, None, True]), ["Bash(rm *)", 3, None, True])


if __name__ == "__main__":
    unittest.main()
