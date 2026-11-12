"""brain-maint.sh on a throwaway brain with a fake agent.

Run: python3 -m unittest discover -s tests -p 'test_brain_maint.py'
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent


class BrainMaintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.kb, self.home = t / "brain", t / "home"
        shutil.copytree(KIT / "overmind", self.kb / ".overmind")
        for d in ("wiki", "inbox", "raw/pages/topics"):
            (self.kb / d).mkdir(parents=True)
        subprocess.run(["python3", "-I", str(self.kb / ".overmind/indexgen.py"), "--root", str(self.kb)],
                       check=True, capture_output=True)
        subprocess.run(["git", "init", "-q", str(self.kb)], check=True)
        self.home.mkdir()
        self.prompt = t / "prompt.txt"
        self.agent = t / "fake-claude"
        self.agent.write_text(
            "#!/bin/sh\n"
            f'printf "%s" "$2" > {self.prompt}\n'
            'echo \'{"total_cost_usd": 0.12, "num_turns": 7, "subtype": "success", "result": "done"}\'\n')
        self.agent.chmod(0o755)
        self.env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin",
                    "CRON_STATE_DIR": str(t / "state"), "CRON_NOTIFY": str(t / "none"),
                    "CLAUDE_MEMORY_DIR": str(self.home / "memory")}

    def tearDown(self):
        self.tmp.cleanup()

    def run_maint(self, *args, **env):
        return subprocess.run(["bash", str(self.kb / ".overmind/brain-maint.sh"), *args],
                              capture_output=True, text=True, timeout=60,
                              env={**self.env, **env})

    def log(self):
        return next((self.kb / ".overmind/logs").glob("brain-maint-*.log")).read_text()

    def test_dry_run_runs_part_a_only(self):
        r = self.run_maint("--dry-run", AGENT_BIN=str(self.agent))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("### brain_lint (rc=0)", r.stdout)
        self.assertIn("### doctor (rc=1)", r.stdout)  # hooksPath unset in the throwaway repo
        self.assertIn("part A: 1 of 6 checks failed: doctor", r.stdout)
        self.assertIn("dry run: no agent call", r.stdout)
        self.assertFalse(self.prompt.exists())

    def test_agent_gets_part_a_and_cost_is_logged(self):
        (self.kb / "inbox/note.md").write_text("x")
        r = self.run_maint(AGENT_BIN=str(self.agent))
        self.assertEqual(r.returncode, 0, self.log())
        prompt = self.prompt.read_text()
        self.assertIn("skills/kb-dream/SKILL.md", prompt)
        self.assertIn("inbox files: 1", prompt)
        self.assertIn("Never run git push", prompt)
        csv = (self.kb / ".overmind/logs/claude-costs.csv").read_text().splitlines()
        self.assertEqual(csv[0], "date,job,cost_usd,turns,subtype")
        self.assertTrue(csv[1].endswith(",brain-maint,0.1200,7,success"))
        self.assertIn("part B: rc=0, $0.12, 7 turns", self.log())

    def test_missing_agent_fails_after_part_a(self):
        r = self.run_maint(AGENT_BIN=str(self.home / "nope"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("part B skipped", self.log())

    def test_memory_audit(self):
        m = self.home / "memory"
        m.mkdir()
        (m / "MEMORY.md").write_text("- [A](a.md) — x\n- [Gone](gone.md) — y\n")
        (m / "a.md").write_text("a")
        (m / "orphan.md").write_text("o")
        r = self.run_maint("--dry-run")
        self.assertIn("index line without file: gone.md", r.stdout)
        self.assertIn("file without index line: orphan.md", r.stdout)
        self.assertIn("### memory index (rc=1)", r.stdout)


if __name__ == "__main__":
    unittest.main()
