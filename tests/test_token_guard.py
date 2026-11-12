"""hooks/token-guard.py: an unchanged image is read once per session.

Run: python3 -m unittest discover -s tests -p 'test_token_guard.py'
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GUARD = Path(__file__).resolve().parent.parent / "hooks" / "token-guard.py"


def read_line(tid, path, ts):
    return json.dumps({"type": "assistant", "timestamp": ts, "message": {"content": [
        {"type": "tool_use", "id": tid, "name": "Read", "input": {"file_path": path}}]}})


class TokenGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def image(self, name="a.png", mtime=1_700_000_000):  # 2023
        p = self.dir / name
        p.write_bytes(b"x")
        os.utime(p, (mtime, mtime))
        return str(p)

    def denied(self, lines, path, tid="toolu_now"):
        t = self.dir / "t.jsonl"
        t.write_text("\n".join(lines) + "\n")
        r = subprocess.run([sys.executable, str(GUARD)], capture_output=True, text=True,
                           input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": path},
                                             "tool_use_id": tid, "transcript_path": str(t)}))
        return "deny" in r.stdout

    def test_current_call_is_not_a_previous_view(self):
        p = self.image()
        self.assertFalse(self.denied([read_line("toolu_now", p, "2026-11-03T10:00:00Z")], p))

    def test_second_view_of_unchanged_image_denied(self):
        p = self.image()
        lines = [read_line("toolu_old", p, "2026-11-03T09:00:00Z"),
                 read_line("toolu_now", p, "2026-11-03T10:00:00Z")]
        self.assertTrue(self.denied(lines, p))

    def test_regenerated_image_allowed(self):
        p = self.image(mtime=1_893_456_000)  # 2030: changed after the earlier read
        self.assertFalse(self.denied([read_line("toolu_old", p, "2026-11-03T09:00:00Z")], p))

    def test_other_path_containing_the_name_does_not_count(self):
        p = self.image("preview.png")
        line = read_line("toolu_old", str(self.dir / "old-preview.png"), "2026-11-03T09:00:00Z")
        line = line.replace("}}]}}", '}}, {"type": "text", "text": "%s"}]}}' % p)  # path only in text
        self.assertFalse(self.denied([line], p))

    def test_non_image_untouched(self):
        p = str(self.dir / "a.md")
        self.assertFalse(self.denied([read_line("toolu_old", p, "2026-11-03T09:00:00Z")], p))


if __name__ == "__main__":
    unittest.main()
