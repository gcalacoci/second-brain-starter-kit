"""hooks/context-warn.py on fake transcripts.

Run: python3 -m unittest discover -s tests -p 'test_context_warn.py'
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
HOOK = KIT / "hooks" / "context-warn.py"


def usage(k):
    return {"type": "assistant", "message": {"usage": {
        "input_tokens": 10, "cache_read_input_tokens": k * 1000 - 10, "cache_creation_input_tokens": 0}}}


class ContextWarnTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.env = {"HOME": str(self.dir), "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "CLAUDE_CODE_ENTRYPOINT": "cli", "LEARNED_DIR": str(KIT / "overmind")}

    def hook(self, records, prompt="next", session="s1", **env):
        t = self.dir / "t.jsonl"
        t.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        r = subprocess.run([sys.executable, str(HOOK)], capture_output=True, text=True,
                           env={**self.env, **env}, input=json.dumps(
                               {"transcript_path": str(t), "session_id": session, "prompt": prompt}))
        return json.loads(r.stdout) if r.stdout.strip() else None

    def test_below_notice_is_silent(self):
        self.assertIsNone(self.hook([usage(50)]))

    def test_tiers_fire_once_then_critical_every_time(self):
        out = self.hook([usage(120)])
        self.assertIn("120k", out["systemMessage"])
        self.assertIsNone(self.hook([usage(125)]))  # same tier: once
        self.assertIn("⚠ CONTEXT 150k", self.hook([usage(150)])["systemMessage"])
        self.assertIn("⛔", self.hook([usage(180)])["systemMessage"])
        self.assertIn("⛔", self.hook([usage(181)])["systemMessage"])

    def test_tiers_from_env(self):
        self.assertIsNone(self.hook([usage(180)], CONTEXT_WARN_TIERS="200,250,400"))
        out = self.hook([usage(260)], session="s2", CONTEXT_WARN_TIERS="200,250,400")
        self.assertIn("⚠ CONTEXT 260k", out["systemMessage"])

    def test_quiet_right_after_compact(self):
        recs = [usage(180), {"type": "system", "subtype": "compact_boundary"},
                {"type": "user", "message": {"content": "summary"}}]
        self.assertIsNone(self.hook(recs))

    def test_save_request_gets_learned_step(self):
        recs = [{"type": "user", "message": {"content": "no, use trash not rm please"}}, usage(20)]
        out = self.hook(recs, prompt="save point")
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn('"Learned" step', ctx)
        self.assertIn("no, use trash not rm please", ctx)
        self.assertNotIn("systemMessage", out)

    def test_headless_runs_are_silent(self):
        self.assertIsNone(self.hook([usage(180)], CLAUDE_CODE_ENTRYPOINT="sdk-cli"))


if __name__ == "__main__":
    unittest.main()
