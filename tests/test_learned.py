"""learned.py: save-point candidates from a session transcript.

Run: python3 -m unittest discover -s tests -p 'test_learned.py'
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "overmind"))
import learned  # noqa: E402


def asst(*uses):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": i, "name": n, "input": inp} for i, n, inp in uses]}}


def result(id_, text, err=False):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": id_, "is_error": err, "content": text}]}}


def said(text):
    return {"type": "user", "message": {"content": text}}


BOUNDARY = {"type": "system", "subtype": "compact_boundary"}


class Candidates(unittest.TestCase):
    def write(self, recs):
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        self.addCleanup(Path(f.name).unlink)
        f.write("\n".join(json.dumps(r) for r in recs) + "\n")
        f.close()
        return f.name

    def test_only_since_the_last_compaction(self):
        path = self.write([
            asst(("a", "Bash", {"command": "curl -s https://docs.example.org/api/old"})),
            result("a", '{"jobs": []}'), BOUNDARY,
            asst(("b", "Bash", {"command": "curl -s https://docs.example.org/api/v2"})),
            result("b", '{"jobs": [1]}')])
        c = learned.candidates(learned.records(path))
        self.assertEqual(c["fetched"], ["https://docs.example.org/api/v2"])

    def test_failed_fetches_are_not_candidates(self):
        path = self.write([
            asst(("a", "WebFetch", {"url": "https://docs.example.org/missing"})), result("a", "404 Not Found", True),
            asst(("b", "Bash", {"command": "curl -s https://x.example/api"})), result("b", "HTTP 429 Too Many Requests"),
            asst(("c", "WebFetch", {"url": "https://docs.example.org/ok"})), result("c", "API reference")])
        self.assertEqual(learned.candidates(learned.records(path))["fetched"], ["https://docs.example.org/ok"])

    def test_error_then_success_is_a_fix(self):
        path = self.write([
            asst(("a", "Bash", {"command": "python3 -I report.py"})), result("a", "No module named yaml", True),
            asst(("b", "Bash", {"command": ".venv/bin/python -I report.py"})), result("b", "{}")])
        fixes = learned.candidates(learned.records(path))["fixes"]
        self.assertEqual(len(fixes), 1)
        self.assertIn("yaml", fixes[0])
        self.assertIn(".venv/bin/python", fixes[0])

    def test_user_corrections(self):
        path = self.write([said("go"), said("90 days is a LOT, 10 days is fair"),
                           said("no, use trash not rm"), said("<command-name>/compact</command-name>"),
                           said("This session is being continued from a previous conversation"),
                           said("Another Claude session sent a message: <cross-session-message from=x> hi there")])
        self.assertEqual(learned.candidates(learned.records(path))["corrections"],
                         ["90 days is a LOT, 10 days is fair", "no, use trash not rm"])

    def test_render_caps_and_says_none(self):
        c = {"fetched": [f"https://a.example/{i}" for i in range(30)], "fixes": [], "corrections": []}
        out = learned.render(c, cap=5)
        self.assertIn("+25 more", out)
        self.assertIn("fixes: none", out)


class Trigger(unittest.TestCase):
    def test_save_phrases(self):
        for p in ("save session", "Save everything please", "save for compact", "save point now",
                  "ok save state", "salva la sessione", "salva tutto", "save this session",
                  "fine thanks work for now. save for compact"):
            self.assertTrue(learned.is_save_request(p), p)

    def test_not_save_phrases(self):
        for p in ("save this file", "save the report as PDF", "the save point hook", "how do we save sessions?"):
            self.assertFalse(learned.is_save_request(p), p)


if __name__ == "__main__":
    unittest.main()
