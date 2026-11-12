"""lib/cron.sh: shared lock, PATH, log rotation, status file and failure notice.

Run: python3 -m unittest discover -s tests -p 'test_cron_lib.py'
"""
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parent.parent / "overmind" / "lib" / "cron.sh"


class CronLibTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.logs, self.state, self.home = t / "logs", t / "state", t / "home"
        self.notified = t / "notified.txt"
        notify = t / "notify.sh"
        notify.write_text(f'#!/bin/sh\necho "$1" >> {self.notified}\n')
        notify.chmod(0o755)
        for v in ("v9.1.0", "v26.11.1", "v10.2.0"):
            (self.home / ".nvm/versions/node" / v / "bin").mkdir(parents=True)
        self.env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin",
                    "CRON_LOG_DIR": str(self.logs), "CRON_STATE_DIR": str(self.state),
                    "CRON_NOTIFY": str(notify)}

    def tearDown(self):
        self.tmp.cleanup()

    def run_job(self, body, name="demo", args=(), env=None):
        script = f'source "{LIB}"\ncron_init {name} "$@"\n{body}\n'
        return subprocess.run(["bash", "-c", script, "job", *args], capture_output=True,
                              text=True, env={**self.env, **(env or {})}, timeout=20)

    def status(self, name="demo"):
        return json.loads((self.state / f"{name}.json").read_text())

    def test_log_file_and_status_on_success(self):
        r = self.run_job('echo "hello from job"')
        self.assertEqual(r.returncode, 0, r.stderr)
        log = self.logs / f"demo-{time.strftime('%Y-%m-%d')}.log"
        self.assertIn("hello from job", log.read_text())
        s = self.status()
        self.assertEqual(s["name"], "demo")
        self.assertEqual(s["rc"], 0)
        for key in ("started", "finished", "seconds", "log"):
            self.assertIn(key, s)
        self.assertEqual(s["log"], log.name)
        self.assertFalse(self.notified.exists())

    def test_extra_json_merged_into_status(self):
        # a job can add its own fields (e.g. a backup snapshot count) to the status file
        extra = Path(self.tmp.name) / "extra.json"
        body = (f'CRON_EXTRA_JSON={extra}\n'
                f'echo \'{{"last_snapshot": "2026-11-03T10:00:00+01:00", "snapshots": 3, "rc": 99}}\' > {extra}')
        r = self.run_job(body)
        self.assertEqual(r.returncode, 0, r.stderr)
        s = self.status()
        self.assertEqual(s["last_snapshot"], "2026-11-03T10:00:00+01:00")
        self.assertEqual(s["snapshots"], 3)
        self.assertEqual(s["rc"], 0)  # extra fields never override the lib's own

    def test_missing_extra_json_is_ignored(self):
        r = self.run_job(f'CRON_EXTRA_JSON={self.tmp.name}/nope.json')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.status()["rc"], 0)

    def test_failure_keeps_rc_writes_status_and_notifies(self):
        r = self.run_job("exit 3")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(self.status()["rc"], 3)
        text = self.notified.read_text()
        self.assertIn("demo", text)
        self.assertIn("FAILED", text)
        self.assertIn("rc=3", text)

    def test_notify_on_fail_off_for_jobs_with_their_own_notice(self):
        r = self.run_job("exit 4", env={"CRON_NOTIFY_ON_FAIL": "0"})
        self.assertEqual(r.returncode, 4)
        self.assertEqual(self.status()["rc"], 4)
        self.assertFalse(self.notified.exists())

    def test_cron_cleanup_runs_on_exit_and_keeps_rc(self):
        marker = Path(self.tmp.name) / "cleaned"
        r = self.run_job(f'cron_cleanup() {{ touch "{marker}"; false; }}\nexit 5')
        self.assertEqual(r.returncode, 5)
        self.assertTrue(marker.exists())
        self.assertEqual(self.status()["rc"], 5)

    def test_dry_run_flag_is_exposed_and_never_notifies(self):
        r = self.run_job('[ "$CRON_DRY_RUN" = 1 ] && echo DRY; exit 2', args=("--dry-run",))
        self.assertEqual(r.returncode, 2)
        self.assertIn("DRY", r.stdout + (self.logs / f"demo-{time.strftime('%Y-%m-%d')}.log").read_text())
        self.assertFalse(self.notified.exists())
        r = self.run_job('[ "$CRON_DRY_RUN" = 0 ] && echo REAL')
        self.assertIn("REAL", (self.logs / f"demo-{time.strftime('%Y-%m-%d')}.log").read_text())

    def test_dry_run_output_goes_to_stdout_too(self):
        r = self.run_job('echo visible', args=("--dry-run",))
        self.assertIn("visible", r.stdout)

    def test_lock_skips_a_second_run(self):
        self.logs.mkdir(parents=True)
        (self.logs / ".demo.lockdir").mkdir()
        r = self.run_job("echo SHOULD-NOT-RUN")
        self.assertEqual(r.returncode, 0)
        log = (self.logs / f"demo-{time.strftime('%Y-%m-%d')}.log").read_text()
        self.assertIn("skipped", log)
        self.assertNotIn("SHOULD-NOT-RUN", log)
        self.assertTrue((self.logs / ".demo.lockdir").is_dir())  # not ours: left alone

    def test_lock_is_removed_after_the_run(self):
        self.run_job("true")
        self.run_job("exit 1")
        self.assertFalse((self.logs / ".demo.lockdir").exists())

    def test_path_has_newest_node_then_local_bin(self):
        r = self.run_job('echo "PATH=$PATH"')
        line = [l for l in (self.logs / f"demo-{time.strftime('%Y-%m-%d')}.log").read_text().splitlines()
                if l.startswith("PATH=")][0]
        parts = line[5:].split(":")
        self.assertEqual(parts[0], str(self.home / ".nvm/versions/node/v26.11.1/bin"))
        self.assertIn(str(self.home / ".local/bin"), parts)
        self.assertIn("/usr/bin", parts)

    def test_cron_path_goes_first(self):
        self.run_job('echo "PATH=$PATH"', env={"CRON_PATH": "/opt/agent/bin:/opt/x"})
        log = (self.logs / f"demo-{time.strftime('%Y-%m-%d')}.log").read_text()
        line = [l for l in log.splitlines() if l.startswith("PATH=")][0]
        self.assertTrue(line.startswith("PATH=/opt/agent/bin:/opt/x:"))

    def test_missing_notifier_is_skipped(self):
        r = self.run_job("exit 3", env={"CRON_NOTIFY": str(self.home / "none.sh")})
        self.assertEqual(r.returncode, 3)
        self.assertEqual(self.status()["rc"], 3)

    def test_old_logs_of_this_job_are_rotated(self):
        self.logs.mkdir(parents=True)
        old, other, recent = (self.logs / "demo-2026-01-01.log", self.logs / "other-2026-01-01.log",
                              self.logs / "demo-2026-10-20.log")
        for p in (old, other, recent):
            p.write_text("x\n")
        long_ago = time.time() - 40 * 86400
        os.utime(old, (long_ago, long_ago))
        os.utime(other, (long_ago, long_ago))
        os.utime(recent, (time.time() - 5 * 86400,) * 2)
        self.run_job("true")
        self.assertFalse(old.exists())
        self.assertTrue(other.exists())
        self.assertTrue(recent.exists())

    def test_keep_days_override(self):
        self.logs.mkdir(parents=True)
        p = self.logs / "demo-2026-10-20.log"
        p.write_text("x\n")
        os.utime(p, (time.time() - 5 * 86400,) * 2)
        self.run_job("true", env={"CRON_KEEP_DAYS": "3"})
        self.assertFalse(p.exists())

    def test_kb_dir_is_the_brain_root(self):
        self.run_job('echo "KB=$KB_DIR"')
        log = (self.logs / f"demo-{time.strftime('%Y-%m-%d')}.log").read_text()
        self.assertIn(f"KB={LIB.parent.parent.parent}\n", log)

    def test_cron_status_lists_every_job(self):
        self.run_job("true", name="alpha")
        self.run_job("exit 4", name="beta")
        r = subprocess.run(["bash", "-c", f'source "{LIB}"; cron_status'], capture_output=True,
                           text=True, env=self.env, timeout=20)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.strip().splitlines()
        alpha = [l for l in lines if l.startswith("alpha")][0]
        beta = [l for l in lines if l.startswith("beta")][0]
        self.assertIn("ok", alpha)
        self.assertIn("FAILED rc=4", beta)



class ClaudeToken(unittest.TestCase):
    """cron_claude_token exports CLAUDE_CODE_OAUTH_TOKEN from a token file."""

    def run_fn(self, path):
        code = (f"unset CLAUDE_CODE_OAUTH_TOKEN; source {LIB}; "
                f"CRON_CLAUDE_TOKEN_FILE={path} cron_claude_token; echo \"[${{CLAUDE_CODE_OAUTH_TOKEN-unset}}]\"")
        r = subprocess.run(["bash", "-c", code], capture_output=True, text=True, timeout=20)
        return r.stdout.strip(), r.returncode

    def test_token_file_is_exported_without_whitespace(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "tok"
            f.write_text("  fake-token-123\n")
            self.assertEqual(self.run_fn(f), ("[fake-token-123]", 0))

    def test_missing_or_empty_file_leaves_it_unset(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_fn(Path(d) / "none"), ("[unset]", 0))
            (Path(d) / "empty").write_text("\n")
            self.assertEqual(self.run_fn(Path(d) / "empty"), ("[unset]", 0))

    def test_cron_init_does_not_call_it(self):
        body = LIB.read_text().split("cron_init() {", 1)[1]
        self.assertNotIn("cron_claude_token", body.split("\n}\n", 1)[0])


if __name__ == "__main__":
    unittest.main()
