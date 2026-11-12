"""indexgen.py on a throwaway brain."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "overmind"))
import indexgen  # noqa: E402
import brain_lint  # noqa: E402


def page(root, rel, pid, extra=""):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nid: %s\ntitle: \"Title %s\"\n%s---\nbody\n" % (pid, pid, extra))


class TestIndexgen(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        page(self.root, "raw/pages/topics/b-topic.md", "b-topic", 'summary: "bee"\n')
        page(self.root, "raw/pages/topics/a-topic.md", "a-topic")
        page(self.root, "raw/pages/sources/old.md", "old", "ingested: 2026-10-01\nsummary: old one\n")
        page(self.root, "raw/pages/sources/new.md", "new", "ingested: 2026-11-01\nsummary: new one\n")
        page(self.root, "knowledge/projects/toolbox.md", "toolbox", "summary: tools\n")
        page(self.root, "knowledge/projects/archive/acme.md", "acme")
        page(self.root, "raw/pages/README.md", "readme")
        (self.root / "wiki").mkdir()

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_render(self):
        text = indexgen.render(self.root)
        lines = [l for l in text.splitlines() if l.startswith(("## ", "- [["))]
        self.assertEqual(lines, ["## Topics", "- [[a-topic]] — Title a-topic", "- [[b-topic]] — bee",
                                 "## Source Summaries", "- [[new]] — new one", "- [[old]] — old one",
                                 "## Projects", "- [[toolbox]] — tools"])
        self.assertNotIn("acme", text)
        self.assertNotIn("readme", text)

    def test_check(self):
        self.assertEqual(indexgen.main(["--root", str(self.root), "--check"]), 1)
        self.assertEqual(indexgen.main(["--root", str(self.root)]), 0)
        self.assertEqual(indexgen.main(["--root", str(self.root), "--check"]), 0)
        self.assertEqual(brain_lint.link_targets((self.root / "wiki/index.md").read_text()),
                         ["a-topic", "b-topic", "new", "old", "toolbox"])


if __name__ == "__main__":
    unittest.main()
