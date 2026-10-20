import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)
KB_SEARCH = os.path.join(SCRIPTS_DIR, "kb-search.py")
KB_STATS = os.path.join(SCRIPTS_DIR, "kb-stats.py")


class TestKBScripts(unittest.TestCase):
    def setUp(self):
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.root = self.temp_dir_obj.name

        # Create workspace directories
        self.topics_dir = os.path.join(self.root, "raw", "pages", "topics")
        self.entities_dir = os.path.join(self.root, "raw", "pages", "entities")
        self.sources_pages_dir = os.path.join(self.root, "raw", "pages", "sources")
        self.session_notes_dir = os.path.join(self.root, "raw", "session-notes")
        self.raw_sources_dir = os.path.join(self.root, "raw", "sources")
        self.inbox_dir = os.path.join(self.root, "inbox")
        self.outputs_dir = os.path.join(self.root, "outputs")
        self.problems_dir = os.path.join(self.root, "knowledge", "problems")

        for d in [
            self.topics_dir,
            self.entities_dir,
            self.sources_pages_dir,
            self.session_notes_dir,
            self.raw_sources_dir,
            self.inbox_dir,
            self.outputs_dir,
            self.problems_dir,
        ]:
            os.makedirs(d, exist_ok=True)

        # Populate sample pages
        self._create_file(
            os.path.join(self.topics_dir, "python.md"),
            "---\n"
            "id: python-topic\n"
            "type: topic\n"
            'title: "Python Guide"\n'
            "tags: python, programming\n"
            "---\n"
            "Python is a versatile programming language. See [[FastAPI]] and [[Django]].\n",
        )

        self._create_file(
            os.path.join(self.topics_dir, "fastapi.md"),
            "---\n"
            "id: fastapi-topic\n"
            "type: topic\n"
            'title: "FastAPI Overview"\n'
            "tags: python, web\n"
            "---\n"
            "FastAPI is a modern python web framework. See [[Python]].\n",
        )

        self._create_file(
            os.path.join(self.entities_dir, "guido.md"),
            "---\n"
            "id: guido-entity\n"
            "type: entity\n"
            'title: "Guido van Rossum"\n'
            "tags: person, python\n"
            "---\n"
            "Creator of Python. Mentioned in [[Python]].\n",
        )

        self._create_file(
            os.path.join(self.session_notes_dir, "meeting.md"),
            "---\n"
            "id: note-1\n"
            "type: session-note\n"
            'title: "Architecture Meeting"\n'
            "tags: meeting\n"
            "---\n"
            "Discussed database migration and refactoring.\n",
        )

        self._create_file(
            os.path.join(self.problems_dir, "prob-1.md"),
            "---\n"
            "id: prob-1\n"
            "type: problem\n"
            'title: "Scaling DB"\n'
            "status: active\n"
            "---\n"
            "How to scale database?\n",
        )

        self._create_file(
            os.path.join(self.raw_sources_dir, "article.pdf"), "binary data"
        )
        self._create_file(
            os.path.join(self.inbox_dir, "item1.txt"), "todo item"
        )

        # Initialize git repository in self.root
        subprocess.run(
            ["git", "init"], cwd=self.root, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=self.root,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.root,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "add", "."], cwd=self.root, capture_output=True, check=True
        )
        subprocess.run(
            # no signing: the user's global git config may require it
            ["git", "-c", "commit.gpgsign=false", "commit", "-m", "Initial commit"],
            cwd=self.root,
            capture_output=True,
            check=True,
        )

    def tearDown(self):
        self.temp_dir_obj.cleanup()

    def _create_file(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def run_script(self, script, args):
        cmd = [sys.executable, script] + args
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_kb_search_finds_by_title(self):
        res = self.run_script(KB_SEARCH, ["Architecture", "--root", self.root])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Search: architecture", res.stdout)
        self.assertIn("Architecture Meeting", res.stdout)

    def test_kb_search_finds_by_body(self):
        res = self.run_script(KB_SEARCH, ["migration", "--root", self.root])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Search: migration", res.stdout)
        self.assertIn("Architecture Meeting", res.stdout)

    def test_kb_search_ranks_better_match_first(self):
        # Searching for 'FastAPI' should rank 'FastAPI Overview' (title match) higher than 'Python Guide' (body match)
        res = self.run_script(KB_SEARCH, ["fastapi", "--root", self.root])
        self.assertEqual(res.returncode, 0)
        fastapi_pos = res.stdout.find("FastAPI Overview")
        python_pos = res.stdout.find("Python Guide")
        self.assertNotEqual(fastapi_pos, -1)
        self.assertNotEqual(python_pos, -1)
        self.assertLess(fastapi_pos, python_pos)

    def test_kb_search_no_matches(self):
        res = self.run_script(KB_SEARCH, ["nonexistentterm", "--root", self.root])
        self.assertEqual(res.returncode, 0)
        self.assertIn("No matches for: nonexistentterm", res.stdout)

    def test_kb_search_no_terms(self):
        res = self.run_script(KB_SEARCH, [])
        self.assertEqual(res.returncode, 1)
        self.assertIn("usage: kb-search.py", res.stdout)

    def test_kb_stats_reports_counts(self):
        res = self.run_script(KB_STATS, ["--root", self.root])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Topic pages | 2", res.stdout)
        self.assertIn("Entity pages | 1", res.stdout)
        self.assertIn("Session notes | 1", res.stdout)
        self.assertIn("Raw sources (immutable) | 1", res.stdout)
        self.assertIn("Inbox backlog | 1", res.stdout)

    def test_kb_stats_reports_inbound_links(self):
        res = self.run_script(KB_STATS, ["--root", self.root])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Hub Pages", res.stdout)
        self.assertIn("[[python]]", res.stdout)
        self.assertIn("[[fastapi]]", res.stdout)

    def test_kb_stats_reports_commit_activity(self):
        res = self.run_script(KB_STATS, ["--root", self.root])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Commit Activity", res.stdout)

    def test_kb_stats_save_option(self):
        res = self.run_script(KB_STATS, ["--root", self.root, "--save"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Saved:", res.stdout)
        reports_dir = os.path.join(self.root, "outputs", "reports")
        self.assertTrue(os.path.exists(reports_dir))
        files = os.listdir(reports_dir)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith("-stats.md"))
