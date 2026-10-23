import tempfile
import unittest
from pathlib import Path

from claude_os import cost
from tests.helpers import transcript


class CostTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "s1.jsonl"
        self.path.write_text(transcript())

    def tearDown(self):
        self.tmp.cleanup()

    def test_session_summary(self):
        s = cost.session(self.path)
        self.assertEqual(s["session"], "s1")
        self.assertEqual(s["messages"], 4, "the streamed duplicate of m1 counts once")
        self.assertEqual(s["first"], "2026-10-20T10:00:05Z")
        self.assertEqual(s["last"], "2026-10-20T11:21:00Z")
        self.assertEqual(s["models"], ["claude-opus-5-5"])
        self.assertEqual(s["tokens"], {"input": 4, "output": 40, "cache_write": 71000, "cache_read": 52000})

    def test_engine_cost_wins_over_estimate(self):
        s = cost.session(self.path)
        self.assertEqual(s["cost_usd"], 1.2345)
        self.assertFalse(s["estimated"])

    def test_estimate_when_no_cost_state(self):
        self.path.write_text("".join(l for l in transcript().splitlines(True) if "cost-state" not in l))
        s = cost.session(self.path)
        self.assertTrue(s["estimated"])
        # opus 5.5 per 1M: $4 in, $20 out, $5 for a 5-minute cache write, $0.20 cache read
        self.assertAlmostEqual(s["cost_usd"], (4 * 4 + 40 * 20 + 71000 * 5 + 52000 * 0.2) / 1e6)

    def test_cold_reload_detected(self):
        c = cost.session(self.path)["cold_reloads"]
        self.assertEqual(c["count"], 1, "the first message is a warm-up and m4 a big tool result")
        self.assertEqual(c["tokens"], 50000)
        self.assertAlmostEqual(c["usd"], 50000 * 5 / 1e6)
        self.assertEqual(c["max_idle_min"], 75)

    def test_one_hour_cache_writes_cost_double(self):
        u = {"input": 0, "output": 0, "cache_write": 1000, "cache_read": 0}
        self.assertAlmostEqual(cost.price("claude-opus-5-5", u, write_1h=1000), 1000 * 8 / 1e6)

    def test_unknown_model_has_no_estimate(self):
        self.assertIsNone(cost.price("some-other-model", {"input": 1, "output": 1, "cache_write": 0, "cache_read": 0}))

    def test_message_text_is_never_kept(self):
        self.assertNotIn("PROMPTSECRET", repr(cost.session(self.path)))


if __name__ == "__main__":
    unittest.main()
