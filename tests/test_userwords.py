"""userwords.is_user_typed: was this transcript record typed by the user?

    python3 -I -m unittest discover -s tests -p 'test_userwords.py'
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "overmind"))
import userwords  # noqa: E402


def rec(content, origin=None, **extra):
    r = {"type": "user", "message": {"role": "user", "content": content}}
    if origin is not None:
        r["origin"] = {"kind": origin}
    r.update(extra)
    return r


class IsUserTyped(unittest.TestCase):
    def test_human_origin(self):
        self.assertTrue(userwords.is_user_typed(rec("go", "human")))

    def test_human_origin_text_blocks(self):
        self.assertTrue(userwords.is_user_typed(rec([{"type": "text", "text": "go"}], "human")))

    def test_other_origins(self):
        for kind in ("peer", "task-notification", "anything"):
            self.assertFalse(userwords.is_user_typed(rec("go", kind)), kind)

    def test_origin_not_a_dict_never_counts(self):
        r = rec("plain words")
        r["origin"] = "human"
        self.assertFalse(userwords.is_user_typed(r))

    def test_no_origin_command_prefixes(self):
        for t in ("<command-name>/compact</command-name>", "<local-command-stdout>x",
                  "<bash-stdout>x", "<bash-stderr>x", "<system-reminder>x"):
            self.assertFalse(userwords.is_user_typed(rec(t)), t)

    def test_no_origin_plain_text(self):
        self.assertTrue(userwords.is_user_typed(rec("plain words")))

    def test_flags_and_tool_results(self):
        self.assertFalse(userwords.is_user_typed(rec("go", "human", isMeta=True)))
        self.assertFalse(userwords.is_user_typed(rec("go", "human", isCompactSummary=True)))
        self.assertFalse(userwords.is_user_typed(
            rec([{"type": "tool_result", "tool_use_id": "t", "content": "out"}])))
        self.assertFalse(userwords.is_user_typed({"type": "assistant", "origin": {"kind": "human"},
                                                  "message": {"content": "go"}}))
        self.assertFalse(userwords.is_user_typed(rec("", "human")))

    def test_text_helper(self):
        self.assertEqual(userwords.user_text(rec([{"type": "text", "text": "a"},
                                                  {"type": "text", "text": "b"}], "human")), "a\nb")


if __name__ == "__main__":
    unittest.main()
