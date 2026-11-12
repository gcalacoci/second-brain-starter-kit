"""unsaved_sessions.py: interactive sessions that did real work and were never saved.
Synthetic transcripts only: real transcripts are personal data.

    python3 -I -m unittest discover -s tests -p 'test_unsaved_sessions.py'
"""
import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "overmind"))
import unsaved_sessions as us  # noqa: E402

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)


def ts(hours_ago):
    return (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def user(text, h, origin="human", **kw):
    r = {"type": "user", "timestamp": ts(h), "entrypoint": "cli",
         "message": {"role": "user", "content": text}}
    if origin:
        r["origin"] = {"kind": origin}
    r.update(kw)
    return r


def tool(name, inp, h):
    return {"type": "assistant", "timestamp": ts(h), "entrypoint": "cli",
            "message": {"role": "assistant",
                        "content": [{"type": "tool_use", "id": "x", "name": name, "input": inp}]}}


def say(text, h):
    return {"type": "assistant", "timestamp": ts(h), "entrypoint": "cli",
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


def commit(h, cmd="git -C ~/prj/second-brain commit -q -m 'feat: x'"):
    return tool("Bash", {"command": cmd}, h)


def turns(n, start_h):
    return [user(f"turn {i}", start_h - i * 0.01) for i in range(n)]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "projects"
        self.state = Path(self.tmp.name) / "state" / "unsaved-sessions.json"
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, records, sid=None, title=None, project="-home-u-prj", mtime=None):
        self.n += 1
        sid = sid or f"sess-{self.n}"
        recs = [dict(r, sessionId=sid) for r in records]
        if title:
            recs.append({"type": "custom-title", "customTitle": title, "sessionId": sid})
        p = self.root / project / f"{sid}.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("".join(json.dumps(r) + "\n" for r in recs))
        t = mtime if mtime is not None else NOW.timestamp() - 13 * 3600
        os.utime(p, (t, t))
        return p

    def scan(self):
        return us.scan(self.root, self.state, now=NOW)

    def ids(self):
        return sorted(s["session_id"] for s in self.scan())


class Listing(Base):
    def test_commit_session_unsaved_is_listed(self):
        self.write([user("do it", 20), commit(19)], sid="a", title="tech-foo")
        got = self.scan()
        self.assertEqual(len(got), 1)
        s = got[0]
        self.assertEqual((s["session_id"], s["name"], s["track"]), ("a", "tech-foo", "tech"))
        self.assertEqual((s["turns"], s["commits"]), (1, 1))
        self.assertEqual(s["last_work"], ts(19))
        self.assertTrue(s["path"].endswith("a.jsonl"))
        self.assertEqual(set(s), {"session_id", "name", "track", "last_work", "turns",
                                  "commits", "path"})

    def test_twenty_turns_is_real_work(self):
        self.write(turns(20, 30), sid="b")
        self.write(turns(19, 30), sid="c")
        self.assertEqual(self.ids(), ["b"])

    def test_idle_threshold(self):
        self.write([user("x", 11), commit(11)], sid="recent", mtime=NOW.timestamp() - 3600)
        self.write([user("x", 13), commit(13)], sid="idle")
        self.assertEqual(self.ids(), ["idle"])

    def test_headless_runs_skipped(self):
        recs = [dict(r, entrypoint="sdk-cli") for r in [user("x", 20), commit(19)]]
        self.write(recs, sid="cron")
        desk = [dict(r, entrypoint="claude-desktop") for r in [user("x", 20), commit(19)]]
        self.write(desk, sid="desk")
        self.assertEqual(self.ids(), ["desk"])

    def test_peer_and_meta_records_are_not_turns(self):
        recs = [user(f"p{i}", 30, origin="peer", isMeta=True) for i in range(25)]
        recs += [user(f"n{i}", 30, origin="task-notification") for i in range(25)]
        recs += [user(f"m{i}", 30, isMeta=True) for i in range(25)]
        self.write(recs, sid="noise")
        self.assertEqual(self.ids(), [])

    def test_commit_must_be_own_bash_call(self):
        recs = [user("x", 20), tool("Bash", {"command": "git log -1 --oneline"}, 19),
                say("I ran git commit earlier", 19),
                tool("Bash", {"command": "git status && git commit -F /tmp/m"}, 18)]
        self.write(recs, sid="own")
        got = self.scan()
        self.assertEqual([(s["session_id"], s["commits"]) for s in got], [("own", 1)])

    def test_sidechain_records_ignored(self):
        recs = [user("x", 20)] + [dict(commit(19), isSidechain=True)]
        self.write(recs, sid="side")
        self.assertEqual(self.ids(), [])

    def test_subagent_depth_skipped(self):
        p = self.root / "-home-u-prj" / "sid" / "subagents" / "agent-1.jsonl"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps(dict(commit(19), sessionId="deep")) + "\n")
        os.utime(p, (NOW.timestamp() - 13 * 3600,) * 2)
        self.assertEqual(self.ids(), [])


class Saves(Base):
    def work(self):
        return [user("start", 30), commit(29)]

    def test_skill_capture(self):
        self.write(self.work() + [tool("Skill", {"skill": "kb-session-capture"}, 28)], sid="s")
        self.assertEqual(self.ids(), [])

    def test_write_session_note_or_briefing(self):
        self.write(self.work() + [tool("Write", {"file_path":
                   "/h/prj/second-brain/raw/session-notes/2026-11-07-x.md", "content": "c"}, 28)])
        self.write(self.work() + [tool("Edit", {"file_path":
                   "/h/brain/outputs/briefings/infra.md"}, 28)])
        self.assertEqual(self.ids(), [])

    def test_commit_touching_notes(self):
        self.write(self.work() + [commit(28, "git add raw/session-notes/x.md && git commit -m 'docs: note'")])
        self.assertEqual(self.ids(), [])

    def test_save_request_typed(self):
        self.write(self.work() + [user("ok save this session", 28)], sid="typed")
        self.write(self.work() + [user("ok save this session", 28, origin="peer", isMeta=True)],
                   sid="relayed")
        self.assertEqual(self.ids(), ["relayed"])

    def test_work_after_save_relists(self):
        self.write(self.work() + [tool("Skill", {"skill": "kb-session-capture"}, 28),
                                  user("one more thing", 27), commit(26)], sid="again")
        self.assertEqual(self.ids(), ["again"])

    def test_commit_right_after_save_request_stays_saved(self):
        self.write(self.work() + [user("save this session", 28),
                                  tool("Write", {"file_path": "/x/raw/session-notes/n.md"}, 27.9),
                                  commit(27.8, "git -C /x commit -q -F /tmp/msg")], sid="tail")
        self.assertEqual(self.ids(), [])


class Names(Base):
    def test_name_order(self):
        sid = "n1"
        recs = [user("x", 20), commit(19),
                {"type": "ai-title", "aiTitle": "Ai name"},
                {"type": "agent-name", "agentName": "infra-agent"},
                {"type": "custom-title", "customTitle": "job-old"},
                {"type": "custom-title", "customTitle": "job-new"}]
        self.write(recs, sid=sid)
        self.write([user("x", 20), commit(19), {"type": "ai-title", "aiTitle": "Inbox sweep"},
                    {"type": "agent-name", "agentName": "infra-agent"}], sid="n2")
        self.write([user("x", 20), commit(19), {"type": "ai-title", "aiTitle": "Inbox sweep"}],
                   sid="n3")
        self.write([user("secret user words", 20), commit(19)], sid="n4")
        got = {s["session_id"]: (s["name"], s["track"]) for s in self.scan()}
        self.assertEqual(got, {"n1": ("job-new", "job"), "n2": ("infra-agent", "infra"),
                               "n3": ("Inbox sweep", ""), "n4": ("n4", "")})


class State(Base):
    def test_dismiss_until_new_work(self):
        p = self.write([user("x", 30), commit(29)], sid="d")
        self.assertEqual(self.ids(), ["d"])
        self.assertTrue(us.dismiss(self.state, "d"))
        self.assertEqual(self.ids(), [])
        self.assertFalse(us.dismiss(self.state, "unknown"))
        with p.open("a") as f:
            f.write(json.dumps(dict(commit(20), sessionId="d")) + "\n")
        os.utime(p, (NOW.timestamp() - 13 * 3600 + 5,) * 2)
        self.assertEqual(self.ids(), ["d"])

    def test_state_has_no_content(self):
        self.write([user("secret user words", 30), commit(29, "git commit -m 'secret msg'")],
                   sid="priv")
        self.scan()
        raw = self.state.read_text()
        self.assertNotIn("secret", raw)
        data = json.loads(raw)
        self.assertEqual(set(data), {"files", "dismissed"})

    def test_cache_reused_when_unchanged(self):
        p = self.write([user("x", 30), commit(29)], sid="c")
        self.scan()
        calls = []
        orig = us.analyze
        us.analyze = lambda path: calls.append(path) or orig(path)
        try:
            self.assertEqual(self.ids(), ["c"])
            self.assertEqual(calls, [])
            os.utime(p, (NOW.timestamp() - 13 * 3600 + 9,) * 2)
            self.scan()
            self.assertEqual(len(calls), 1)
        finally:
            us.analyze = orig

    def test_old_files_skipped_unless_known(self):
        old = NOW.timestamp() - 15 * 86400
        self.write([user("x", 400), commit(399)], sid="old", mtime=old)
        self.assertEqual(self.ids(), [])


class Cli(Base):
    def run_cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = us.main(["--projects", str(self.root), "--state", str(self.state),
                            "--now", NOW.isoformat(), *args])
        return code, out.getvalue()

    def test_list_and_dismiss(self):
        self.write([user("secret user words", 30), commit(29)], sid="cli1", title="tech-x")
        code, out = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("unsaved sessions: 1", out)
        self.assertIn("tech-x", out)
        self.assertIn("cli1", out)
        self.assertNotIn("secret", out)
        self.assertEqual(self.run_cli("dismiss", "cli1")[0], 0)
        self.assertIn("unsaved sessions: 0", self.run_cli("list")[1])
        self.assertEqual(self.run_cli("dismiss", "nope")[0], 1)

    def test_default_is_list(self):
        self.assertIn("unsaved sessions: 0", self.run_cli()[1])


if __name__ == "__main__":
    unittest.main()
