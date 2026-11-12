"""Brain git hooks: pre-commit and commit-msg gates.

Run: python3 -m unittest discover -s tests -p 'test_githook.py'
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_brain_lint import clean_brain, page

HOOKS = Path(__file__).resolve().parent.parent / "overmind" / "git-hooks"


def git(root, *args, check=True):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          check=check)


class GitHookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        clean_brain(self.root)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.name", "Test")
        git(self.root, "config", "user.email", "t@example.invalid")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "chore: base")  # before the hooks are on
        git(self.root, "config", "core.hooksPath", str(HOOKS))

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, msg="docs: change"):
        r = git(self.root, "commit", "-qm", msg, check=False)
        return r.returncode, r.stdout + r.stderr

    def stage(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        git(self.root, "add", "-f", rel)

    def assertRefused(self, needle, msg="docs: change"):
        rc, out = self.commit(msg)
        self.assertNotEqual(rc, 0, out)
        self.assertIn(needle, out)
        return out

    def assertAccepted(self, msg="docs: change"):
        rc, out = self.commit(msg)
        self.assertEqual(rc, 0, out)

    # pre-commit: brain_lint --staged
    def test_clean_commit_passes(self):
        page(self.root, "raw/pages/topics/topic-b.md", "topic-b")
        git(self.root, "add", "raw/pages/topics/topic-b.md")
        self.assertAccepted()

    def test_lint_error_in_staged_page_is_refused(self):
        page(self.root, "raw/pages/topics/topic-b.md", "topic-b")
        p = self.root / "raw/pages/topics/topic-b.md"
        p.write_text(p.read_text().replace("agent: claude-code\n", ""))
        git(self.root, "add", "raw/pages/topics/topic-b.md")
        self.assertRefused("FM001")

    def test_unstaged_bad_page_does_not_block(self):
        (self.root / "raw/pages/topics/bare.md").write_text("# no frontmatter\n")
        page(self.root, "raw/pages/topics/topic-b.md", "topic-b")
        git(self.root, "add", "raw/pages/topics/topic-b.md")
        self.assertAccepted()

    # pre-commit: private/
    def test_private_path_is_refused(self):
        self.stage("private/contacts.md", "a contact\n")
        self.assertRefused("private/")

    # pre-commit: secrets
    def test_secret_file_names_are_refused(self):
        for rel in (".env", "config/.env.local", "keys/server.pem", "id_rsa", "id_ed25519",
                    "x/credentials.json", ".credentials.json", "a/b.key"):
            with self.subTest(rel=rel):
                self.stage(rel, "harmless\n")
                self.assertRefused(rel)
                git(self.root, "rm", "-q", "--cached", rel)

    def test_secret_content_is_refused(self):
        samples = {
            "private key": "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n",
            "anthropic": "token = sk-ant-api03-" + "a" * 40 + "\n",
            "github": "ghp_" + "A1b2C3d4E5" * 4 + "\n",
            "aws": "AKIA" + "ABCDEFGHIJKLMNOP" + "\n",
            "slack": "xoxb-1234567890-abcdefghij\n",
        }
        for name, text in samples.items():
            with self.subTest(name=name):
                self.stage("notes/leak.md", text)
                self.assertRefused("notes/leak.md")
                git(self.root, "rm", "-q", "--cached", "notes/leak.md")

    def test_words_about_secrets_pass(self):
        self.stage("notes/ok.md", "Never commit .env or id_rsa; keys start with sk-ant-.\n")
        self.assertAccepted()

    # pre-commit: raw/sources is append-only
    def test_new_raw_source_is_allowed(self):
        self.stage("raw/sources/2026-10-28-new.md", "new raw\n")
        self.assertAccepted()

    def test_modified_raw_source_is_refused(self):
        self.stage("raw/sources/2026-10-01-a.md", "edited\n")
        self.assertRefused("raw/sources/2026-10-01-a.md")

    def test_deleted_raw_source_is_refused(self):
        git(self.root, "rm", "-q", "raw/sources/2026-10-01-a.md")
        self.assertRefused("raw/sources/2026-10-01-a.md")

    def test_renamed_raw_source_is_refused(self):
        git(self.root, "mv", "raw/sources/2026-10-01-a.md", "raw/sources/2026-10-01-b.md")
        self.assertRefused("raw/sources/2026-10-01-a.md")

    # commit-msg: AI trailers, opt-in
    def test_trailers_pass_by_default(self):
        page(self.root, "raw/pages/topics/topic-b.md", "topic-b")
        git(self.root, "add", "raw/pages/topics/topic-b.md")
        self.assertAccepted("docs: x\n\nClaude-Session: https://claude.ai/code/session_1")

    def test_claude_trailers_are_refused(self):
        git(self.root, "config", "brain.blockAiTrailers", "true")
        page(self.root, "raw/pages/topics/topic-b.md", "topic-b")
        git(self.root, "add", "raw/pages/topics/topic-b.md")
        for msg in ("docs: x\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
                    "docs: x\n\nco-authored-by: claude <noreply@anthropic.com>",
                    "docs: x\n\nClaude-Session: https://claude.ai/code/session_1",
                    "docs: x\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)"):
            with self.subTest(msg=msg):
                self.assertRefused("trailer", msg)

    def test_claude_in_subject_is_fine(self):
        page(self.root, "raw/pages/topics/topic-b.md", "topic-b")
        git(self.root, "add", "raw/pages/topics/topic-b.md")
        self.assertAccepted("docs: note on Claude Code hooks\n\nCo-Authored-By: A Person <a@b.c>")


if __name__ == "__main__":
    unittest.main()
