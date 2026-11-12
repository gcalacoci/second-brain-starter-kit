"""loggen.py on a throwaway git repo."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "overmind"))
import loggen  # noqa: E402
import brain_lint  # noqa: E402


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                   env={"GIT_AUTHOR_DATE": "2026-11-03T10:00:00+01:00",
                        "GIT_COMMITTER_DATE": "2026-11-03T10:00:00+01:00", "HOME": str(root),
                        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x", "PATH": "/usr/bin:/bin"})


class TestLoggen(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        git(self.root, "init", "-q")
        git(self.root, "config", "core.hooksPath", "/dev/null")
        for i, msg in enumerate(["feat: add x\n\nWhy x.\nCo-authored-by: a <b>", "docs(job): note y",
                                 "test: pin z", 'Revert "feat: add x"']):
            (self.root / ("f%d" % i)).write_text(str(i))
            git(self.root, "add", "f%d" % i)
            git(self.root, "commit", "-q", "-m", msg)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_render(self):
        text = loggen.render(loggen.entries(self.root))
        heads = [l for l in text.splitlines() if l.startswith("## [")]
        self.assertEqual(heads, ["## [2026-11-03] feat - add x", "## [2026-11-03] docs - note y",
                                 "## [2026-11-03] chore - pin z",
                                 '## [2026-11-03] fix - Revert "feat: add x"'])
        self.assertRegex(text, r"\n- [0-9a-f]{7,} Why x\.\n")
        self.assertNotIn("Co-authored-by", text)
        for head in heads:
            match = brain_lint.LOG_RE.match(head)
            self.assertIn(match.group(2), brain_lint.LOG_TYPES)

    def test_main_writes_file(self):
        (self.root / "wiki").mkdir()
        self.assertEqual(loggen.main(["--root", str(self.root)]), 0)
        self.assertTrue((self.root / "wiki/log.md").read_text().startswith("# Knowledge Base Log"))


if __name__ == "__main__":
    unittest.main()
