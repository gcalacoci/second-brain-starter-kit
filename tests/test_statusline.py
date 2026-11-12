"""hooks/statusline.py: context tiers and the failed-cron segment.

Run: python3 -m unittest discover -s tests -p 'test_statusline.py'
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "hooks" / "statusline.py"


class StatuslineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.state = self.dir / "cron-status"
        self.state.mkdir()

    def line(self, used, size=200_000, **env):
        data = {"model": {"display_name": "Sonnet"}, "cwd": str(self.dir),
                "context_window": {"context_window_size": size, "total_input_tokens": used}}
        r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True,
                           input=json.dumps(data),
                           env={"HOME": str(self.dir), "PATH": os.environ.get("PATH", ""),
                                "CRON_STATE_DIR": str(self.state), **env})
        return r.stdout

    def test_default_tiers_fit_a_200k_window(self):
        self.assertNotIn("⚠", self.line(90_000))
        self.assertIn("⚠", self.line(110_000))
        self.assertIn("⚠ compact", self.line(150_000))
        self.assertIn("COMPACT NOW", self.line(175_000))

    def test_tiers_from_env(self):
        self.assertNotIn("⚠", self.line(150_000, size=1_000_000, CONTEXT_WARN_TIERS="200,250,400"))
        self.assertIn("⚠ compact", self.line(260_000, size=1_000_000, CONTEXT_WARN_TIERS="200,250,400"))

    def test_failed_cron_shown_passing_hidden(self):
        (self.state / "brain-maint.json").write_text(json.dumps({"name": "brain-maint", "rc": 1}))
        (self.state / "backup.json").write_text(json.dumps({"name": "backup", "rc": 0}))
        out = self.line(10_000)
        self.assertIn("cron ✗ brain-maint", out)
        self.assertNotIn("backup", out)
        (self.state / "brain-maint.json").write_text(json.dumps({"name": "brain-maint", "rc": 0}))
        self.assertNotIn("cron", self.line(10_000))


if __name__ == "__main__":
    unittest.main()
