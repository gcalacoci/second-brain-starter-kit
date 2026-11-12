"""brain_lint.py on a small fake brain.

Run: python3 -m unittest discover -s tests -p 'test_brain_lint.py'
"""
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

LINT = Path(__file__).resolve().parent.parent / "overmind" / "brain_lint.py"
sys.path.insert(0, str(LINT.parent))
import indexgen  # noqa: E402

GOOD_FM = """---
id: {id}
type: {type}
title: "{id}"
tags: [x]
created: 2026-10-01
updated: 2026-10-02
agent: claude-code
{extra}---

Body linking [[topic-a]].
"""


def page(root, rel, id, type="topic", extra=""):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(GOOD_FM.format(id=id, type=type, extra=extra))
    return p


def clean_brain(root):
    """A brain with no findings at all."""
    page(root, "raw/pages/topics/topic-a.md", "topic-a")
    page(root, "raw/pages/sources/src-a.md", "src-a", "source-summary",
         "raw-file: raw/sources/2026-10-01-a.md\n")
    (root / "raw/sources").mkdir(parents=True, exist_ok=True)
    (root / "raw/sources/2026-10-01-a.md").write_text("raw\n")
    page(root, "raw/session-notes/2026-10-01-s.md", "s-1", "session-note")
    (root / "wiki").mkdir(exist_ok=True)
    (root / "wiki/index.md").write_text(indexgen.render(root))
    (root / "wiki/processed.md").write_text(
        "| Date | Title | Raw File | Source Summary |\n|---|---|---|---|\n"
        "| 2026-10-01 | A | raw/sources/2026-10-01-a.md | raw/pages/sources/src-a.md |\n")
    (root / "wiki/log.md").write_text(
        "# Log\n\n## [2026-10-01] ingest - A\n- 2026-10-02: a bullet entry\n")


def lint(root, *args):
    r = subprocess.run([sys.executable, "-I", str(LINT), "--root", str(root), *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout


class BrainLintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        clean_brain(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_brain_passes(self):
        rc, out = lint(self.root)
        self.assertEqual(rc, 0, out)
        self.assertNotRegex(out, r"(FM|WIKI|SRC|IDX|LNK|LOG)\d{3}")

    def test_missing_frontmatter_field_is_an_error(self):
        p = self.root / "raw/pages/topics/topic-a.md"
        p.write_text(p.read_text().replace("agent: claude-code\n", ""))
        rc, out = lint(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("FM001 raw/pages/topics/topic-a.md", out)
        self.assertIn("agent", out)

    def test_no_frontmatter_is_an_error(self):
        (self.root / "raw/pages/topics/bare.md").write_text("# no frontmatter\n")
        rc, out = lint(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("FM001 raw/pages/topics/bare.md", out)

    def test_bad_type_and_date_are_errors(self):
        page(self.root, "raw/pages/topics/t2.md", "t2", "blogpost")
        p = self.root / "raw/pages/topics/t3.md"
        page(self.root, "raw/pages/topics/t3.md", "t3")
        p.write_text(p.read_text().replace("created: 2026-10-01", "created: 01/10/2026"))
        rc, out = lint(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("FM002 raw/pages/topics/t2.md", out)
        self.assertIn("FM003 raw/pages/topics/t3.md", out)

    def test_duplicate_id_is_an_error(self):
        page(self.root, "raw/pages/topics/copy.md", "topic-a")
        rc, out = lint(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("FM004", out)

    def test_extra_file_in_wiki_is_an_error(self):
        (self.root / "wiki/README.md").write_text("x\n")
        rc, out = lint(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("WIKI001 wiki/README.md", out)

    def test_source_summary_not_in_processed_is_an_error(self):
        page(self.root, "raw/pages/sources/src-b.md", "src-b", "source-summary",
             "raw-file: raw/sources/2026-10-03-b.md\n")
        rc, out = lint(self.root)
        self.assertEqual(rc, 1)
        self.assertIn("SRC001 raw/pages/sources/src-b.md", out)

    def test_page_missing_from_index_is_a_warning(self):
        page(self.root, "raw/pages/topics/orphan.md", "orphan")
        rc, out = lint(self.root)
        self.assertEqual(rc, 0, out)
        self.assertIn("IDX001 raw/pages/topics/orphan.md", out)
        self.assertEqual(lint(self.root, "--strict")[0], 1)

    def test_stale_index_and_knowledge_ids(self):
        page(self.root, "knowledge/projects/p.md", "project-p", "project")
        rc, out = lint(self.root)
        self.assertEqual(rc, 0, out)
        self.assertIn("IDX003 wiki/index.md", out)
        (self.root / "wiki/index.md").write_text(indexgen.render(self.root))
        rc, out = lint(self.root)
        self.assertNotIn("IDX", out)
        self.assertIn("[[project-p]]", (self.root / "wiki/index.md").read_text())

    def test_index_link_to_missing_page_is_a_warning(self):
        with open(self.root / "wiki/index.md", "a") as f:
            f.write("- [[ghost]] — gone\n")
        rc, out = lint(self.root)
        self.assertEqual(rc, 0, out)
        self.assertIn("IDX002 wiki/index.md", out)
        self.assertIn("ghost", out)

    def test_dangling_link_is_a_warning_and_filename_stem_resolves(self):
        page(self.root, "raw/pages/topics/linker.md", "linker")
        p = self.root / "raw/pages/topics/linker.md"
        p.write_text(p.read_text() + "See [[nowhere]] and [[topic-a]] and [[2026-10-01-s]].\n")
        with open(self.root / "wiki/index.md", "a") as f:
            f.write("- [[linker]] — l\n")
        rc, out = lint(self.root)
        self.assertEqual(rc, 0, out)
        self.assertIn("LNK001 raw/pages/topics/linker.md", out)
        self.assertIn("nowhere", out)
        self.assertNotIn("[[topic-a]]", out.split("LNK001")[-1] if "LNK001" in out else "")
        self.assertEqual(out.count("LNK001"), 1)

    def test_bad_log_heading_is_a_warning(self):
        with open(self.root / "wiki/log.md", "a") as f:
            f.write("## [2026-13-40] ingest - bad date\n## [2026-10-05] party - bad type\n")
        rc, out = lint(self.root)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out.count("LOG001"), 2)

    def test_staged_limits_file_checks_to_staged_files(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "raw/pages/topics/bare.md").write_text("# unstaged, no frontmatter\n")
        page(self.root, "raw/pages/topics/staged.md", "staged")
        p = self.root / "raw/pages/topics/staged.md"
        p.write_text(p.read_text().replace("agent: claude-code\n", ""))
        subprocess.run(["git", "-C", str(self.root), "add", "raw/pages/topics/staged.md"], check=True)
        rc, out = lint(self.root, "--staged")
        self.assertEqual(rc, 1)
        self.assertIn("FM001 raw/pages/topics/staged.md", out)
        self.assertNotIn("bare.md", out)
        self.assertNotIn("IDX001", out)

    def test_readme_and_commit_type_headings_pass(self):
        (self.root / "raw/pages/README.md").write_text("# folder readme, no frontmatter\n")
        with open(self.root / "wiki/log.md", "a") as f:
            f.write("## [2026-10-06] docs - a commit-type heading\n")
        rc, out = lint(self.root)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("LOG001", out)

    def test_summary_line(self):
        page(self.root, "raw/pages/topics/orphan.md", "orphan")
        rc, out = lint(self.root)
        self.assertRegex(out.strip().splitlines()[-1], r"^brain_lint: 0 errors, 2 warnings$")  # IDX001 + IDX003


if __name__ == "__main__":
    unittest.main()
