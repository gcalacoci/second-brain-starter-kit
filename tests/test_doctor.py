"""doctor.py on a fake state dir and a throwaway brain.

Run: python3 -m unittest discover -s tests -p 'test_doctor.py'
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "overmind"))
import doctor  # noqa: E402

NOW = datetime.fromisoformat("2026-11-03T10:00:00+01:00").timestamp()


class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.state = Path(tempfile.mkdtemp())
        (self.state / "cron-status").mkdir()
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.state)
        shutil.rmtree(self.root)

    def status(self, name, **data):
        (self.state / "cron-status" / ("%s.json" % name)).write_text(json.dumps(data))

    def levels(self, rows):
        return {what: level for level, what, _ in rows}

    def test_crons(self):
        self.status("brain-maint", rc=0, started="2026-10-30T17:00:00+01:00", finished="2026-10-30T17:20:00+01:00")
        self.status("backup", rc=0, finished="2026-11-01T06:31:00+01:00")  # 51h > 48h default
        self.status("export", rc=2, finished="2026-11-03T07:31:00+01:00", log="export.log")
        self.status("sync", rc=None, started="2026-11-03T09:59:00+01:00")  # running
        self.status(".backup.extra", last_snapshot="x")  # temp file: skipped
        (self.state / "cron-status" / "broken.json").write_text("{broken")
        got = self.levels(doctor.crons(self.state, NOW))
        self.assertEqual(got, {"cron brain-maint": "OK", "cron backup": "WARN", "cron export": "FAIL",
                               "cron sync": "OK", "cron broken": "FAIL"})

    def test_max_age_override(self):
        self.status("backup", rc=0, finished="2026-11-01T06:31:00+01:00")
        with mock.patch.dict(os.environ, {"BRAIN_DOCTOR_MAX_AGE": "backup=72, junk"}):
            self.assertEqual(self.levels(doctor.crons(self.state, NOW)), {"cron backup": "OK"})

    def test_no_crons_yet(self):
        self.assertEqual(self.levels(doctor.crons(self.state, NOW)), {"crons": "OK"})

    def test_gates(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.assertEqual(self.levels(doctor.gates(self.root)), {"git gates": "FAIL"})
        (self.root / ".overmind/git-hooks").mkdir(parents=True)
        (self.root / ".overmind/git-hooks/pre-commit").write_text("#!/bin/sh\n")
        subprocess.run(["git", "-C", str(self.root), "config", "core.hooksPath", ".overmind/git-hooks"], check=True)
        self.assertEqual(self.levels(doctor.gates(self.root)), {"git gates": "OK"})

    def test_inbox(self):
        (self.root / "inbox").mkdir()
        (self.root / "inbox/README.md").write_text("x")
        self.assertEqual(doctor.inbox(self.root)[0][2], "0 files waiting")
        for i in range(doctor.INBOX_WARN + 1):
            (self.root / ("inbox/n%d.md" % i)).write_text("x")
        self.assertEqual(self.levels(doctor.inbox(self.root)), {"inbox": "WARN"})

    def test_lint(self):
        (self.root / "wiki").mkdir()
        self.assertEqual(self.levels(doctor.lint(self.root)), {"brain lint": "OK"})
        (self.root / "wiki/stray.md").write_text("x")
        self.assertEqual(self.levels(doctor.lint(self.root)), {"brain lint": "FAIL"})

    def test_epoch_formats(self):
        self.assertEqual(doctor._epoch("1793685243\n"), 1793685243.0)
        self.assertEqual(doctor._epoch("2026-11-03T10:00:00+01:00"), NOW)


if __name__ == "__main__":
    unittest.main()
