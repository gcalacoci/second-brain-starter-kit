"""Black-box tests for hooks/security-guard.py.

The hook is copied to a temp dir with {{KB_DIR}} replaced by a temp brain
directory, then run as a subprocess with HOME pointing at a temp home.
Standard library only.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_SRC = Path(__file__).resolve().parent.parent / "hooks" / "security-guard.py"


class SecurityGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="guard-test-")
        base = Path(cls._tmp.name)
        cls.home = base / "home"
        cls.home.mkdir()
        cls.brain = cls.home / "brain"
        cls.brain.mkdir()
        cls.script = base / "security-guard.py"
        cls.script.write_text(
            HOOK_SRC.read_text().replace("{{KB_DIR}}", str(cls.brain))
        )
        cls.env = dict(os.environ, HOME=str(cls.home))

        # Ordinary files used by the allow cases.
        cls.notes = cls.home / "notes.txt"
        cls.notes.write_text("hello\n")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_guard(self, tool_name, tool_input, cwd=None):
        payload = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "cwd": str(cwd if cwd is not None else self.home),
        }
        return subprocess.run(
            [sys.executable, str(self.script)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=self.env,
            cwd=str(self.home),
        )

    def assert_blocked(self, result, fragment=None):
        self.assertEqual(result.returncode, 2, result.stderr)
        if fragment:
            self.assertIn(fragment, result.stderr)

    def assert_allowed(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)

    # --- Secrets: Read tool -------------------------------------------------
    def test_read_env_blocked(self):
        self.assert_blocked(
            self.run_guard("Read", {"file_path": str(self.home / ".env")})
        )

    def test_read_pem_blocked(self):
        self.assert_blocked(
            self.run_guard("Read", {"file_path": str(self.home / "server.pem")})
        )

    def test_read_key_blocked(self):
        self.assert_blocked(
            self.run_guard("Read", {"file_path": str(self.home / "id.key")})
        )

    # --- Secrets: Write / Edit tools ---------------------------------------
    def test_write_env_blocked(self):
        self.assert_blocked(
            self.run_guard(
                "Write",
                {"file_path": str(self.home / ".env"), "content": "SECRET=1"},
            )
        )

    def test_write_key_blocked(self):
        self.assert_blocked(
            self.run_guard(
                "Write",
                {"file_path": str(self.home / "private.key"), "content": "x"},
            )
        )

    def test_edit_pem_blocked(self):
        self.assert_blocked(
            self.run_guard(
                "Edit",
                {
                    "file_path": str(self.home / "server.pem"),
                    "old_string": "a",
                    "new_string": "b",
                },
            )
        )

    # --- Secrets: shell reads ----------------------------------------------
    def test_bash_cat_env_blocked(self):
        self.assert_blocked(self.run_guard("Bash", {"command": "cat .env"}))

    def test_bash_cat_pem_blocked(self):
        self.assert_blocked(
            self.run_guard("Bash", {"command": "cat ~/server.pem"})
        )

    def test_bash_head_key_blocked(self):
        self.assert_blocked(
            self.run_guard("Bash", {"command": "head -5 " + str(self.home / "a.key")})
        )

    def test_bash_chained_cat_env_blocked(self):
        self.assert_blocked(
            self.run_guard("Bash", {"command": "echo ok && cat .env"})
        )

    def test_git_add_env_blocked(self):
        self.assert_blocked(self.run_guard("Bash", {"command": "git add .env"}))

    # --- Path boundaries ----------------------------------------------------
    def test_write_outside_home_and_tmp_blocked(self):
        self.assert_blocked(
            self.run_guard(
                "Write",
                {"file_path": "/etc/guard-test.conf", "content": "x"},
            )
        )

    def test_write_in_usr_local_blocked(self):
        # /usr/local is readable for the guard, but not writable.
        self.assert_blocked(
            self.run_guard(
                "Write",
                {"file_path": "/usr/local/guard-test.conf", "content": "x"},
            )
        )

    def test_read_outside_allowed_roots_blocked(self):
        self.assert_blocked(
            self.run_guard("Read", {"file_path": "/etc/passwd"})
        )

    def test_bash_cat_outside_allowed_roots_blocked(self):
        self.assert_blocked(
            self.run_guard("Bash", {"command": "cat /etc/passwd"})
        )

    def test_grep_outside_allowed_roots_blocked(self):
        self.assert_blocked(
            self.run_guard("Grep", {"pattern": "root", "path": "/etc"})
        )

    def test_bash_redirect_outside_blocked(self):
        self.assert_blocked(
            self.run_guard("Bash", {"command": "echo hi > /etc/guard-test"})
        )

    # --- Brain local-only guarantee ----------------------------------------
    def test_git_stash_push_inside_brain_allowed(self):
        # `stash push` is not a push
        self.assert_allowed(
            self.run_guard("Bash", {"command": "git stash push -q"}, cwd=self.brain)
        )

    def test_commit_message_with_push_inside_brain_allowed(self):
        self.assert_allowed(
            self.run_guard("Bash", {"command": "git commit -m 'push later'"}, cwd=self.brain)
        )

    def test_git_dash_c_brain_push_blocked(self):
        self.assert_blocked(
            self.run_guard("Bash", {"command": "git -C %s push" % self.brain}, cwd=self.home)
        )

    def test_sibling_folder_of_brain_push_allowed(self):
        # brain path as a prefix of another folder is not the brain
        sibling = str(self.brain) + "-starter-kit"
        self.assert_allowed(
            self.run_guard("Bash", {"command": "git -C %s push origin main" % sibling}, cwd=self.home)
        )

    def test_force_push_variants_blocked(self):
        for cmd in ("git push -uf origin x", "git push origin +main",
                    "git push --force-with-lease"):
            with self.subTest(cmd=cmd):
                self.assert_blocked(self.run_guard("Bash", {"command": cmd}, cwd=self.home))

    def test_git_push_inside_brain_blocked(self):
        self.assert_blocked(
            self.run_guard(
                "Bash", {"command": "git push origin main"}, cwd=self.brain
            )
        )

    def test_git_push_outside_brain_allowed(self):
        self.assert_allowed(
            self.run_guard(
                "Bash", {"command": "git push origin main"}, cwd=self.home
            )
        )

    def test_git_push_with_brain_path_in_command_blocked(self):
        self.assert_blocked(
            self.run_guard(
                "Bash",
                {"command": "cd %s && git push" % self.brain},
                cwd=self.home,
            )
        )

    def test_force_push_outside_brain_blocked(self):
        self.assert_blocked(
            self.run_guard(
                "Bash", {"command": "git push --force origin main"}, cwd=self.home
            )
        )

    # --- Destructive commands ----------------------------------------------
    def test_rm_outside_allowed_roots_blocked(self):
        self.assert_blocked(
            self.run_guard("Bash", {"command": "rm -rf /etc/passwd"})
        )

    def test_mv_outside_allowed_roots_blocked(self):
        self.assert_blocked(
            self.run_guard(
                "Bash", {"command": "mv /etc/hosts /tmp/hosts.bak"}
            )
        )

    def test_rm_inside_tmp_allowed(self):
        self.assert_allowed(
            self.run_guard("Bash", {"command": "rm -f /tmp/guard-test-file"})
        )

    def test_mkdir_outside_allowed_roots_blocked(self):
        # The script treats mkdir (among others) as a destructive command.
        self.assert_blocked(
            self.run_guard("Bash", {"command": "mkdir /etc/guard-dir"})
        )

    # --- Ordinary use allowed ----------------------------------------------
    def test_read_inside_home_allowed(self):
        self.assert_allowed(
            self.run_guard("Read", {"file_path": str(self.notes)})
        )

    def test_write_inside_home_allowed(self):
        self.assert_allowed(
            self.run_guard(
                "Write",
                {"file_path": str(self.home / "draft.md"), "content": "hi"},
            )
        )

    # --- Relative paths resolve against the agent's cwd, not the hook's ----
    def test_relative_read_from_outside_cwd_blocked(self):
        # the hook process runs in the temp home; the agent is in /etc
        self.assert_blocked(
            self.run_guard("Bash", {"command": "cat ./passwd"}, cwd="/etc")
        )

    def test_relative_rm_from_outside_cwd_blocked(self):
        self.assert_blocked(
            self.run_guard("Bash", {"command": "rm ./hosts"}, cwd="/etc")
        )

    def test_relative_read_from_home_cwd_allowed(self):
        self.assert_allowed(
            self.run_guard("Bash", {"command": "cat ./notes.txt"}, cwd=self.home)
        )

    def test_write_inside_tmp_allowed(self):
        self.assert_allowed(
            self.run_guard(
                "Write",
                {"file_path": "/tmp/guard-draft.md", "content": "hi"},
            )
        )

    def test_bash_cat_inside_home_allowed(self):
        self.assert_allowed(
            self.run_guard("Bash", {"command": "cat notes.txt"})
        )

    def test_passthrough_websearch_allowed(self):
        self.assert_allowed(
            self.run_guard("WebSearch", {"query": "anything at all"})
        )


if __name__ == "__main__":
    unittest.main()
