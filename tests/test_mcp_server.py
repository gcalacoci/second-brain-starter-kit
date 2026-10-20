"""Tests for the path-safety and inbox-write boundary in scripts/mcp_server.py.

The real `mcp` package is not installed in this environment, so a minimal stub
is installed in sys.modules before the server module is imported with
importlib.  A throwaway workspace containing SCHEMA.md, inbox/ and wiki/ is
created because the server reads SECOND_BRAIN_DIR at import time.
"""

import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


# ── mcp stub (must be installed before importing the server) ─────────

def _install_mcp_stub() -> None:
    mcp_module = types.ModuleType("mcp")
    server_module = types.ModuleType("mcp.server")
    fastmcp_module = types.ModuleType("mcp.server.fastmcp")

    class FastMCP:
        def __init__(self, *args, **kwargs):
            pass

        def tool(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

        def resource(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    fastmcp_module.FastMCP = FastMCP
    server_module.fastmcp = fastmcp_module
    mcp_module.server = server_module

    sys.modules["mcp"] = mcp_module
    sys.modules["mcp.server"] = server_module
    sys.modules["mcp.server.fastmcp"] = fastmcp_module


SERVER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "mcp_server.py"

# Populated by setUpModule().
server = None
KB = None
_workspace_tmp = None
_outside_tmp = None
_previous_second_brain_dir = None


def setUpModule() -> None:
    global server, KB, _workspace_tmp, _outside_tmp, _previous_second_brain_dir

    _install_mcp_stub()

    _workspace_tmp = tempfile.TemporaryDirectory()
    KB = Path(_workspace_tmp.name).resolve()
    (KB / "SCHEMA.md").write_text("# schema\n", encoding="utf-8")
    (KB / "inbox").mkdir()
    (KB / "wiki").mkdir()
    (KB / "wiki" / "index.md").write_text("# index\n", encoding="utf-8")

    _outside_tmp = tempfile.TemporaryDirectory()
    outside_file = Path(_outside_tmp.name) / "outside.txt"
    outside_file.write_text("outside\n", encoding="utf-8")

    # Fixtures used by safe_path tests.
    (KB / ".git").mkdir()
    (KB / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (KB / ".overmind" / "logs").mkdir(parents=True)
    (KB / ".overmind" / "logs" / "run.log").write_text("log\n", encoding="utf-8")
    (KB / ".envs").mkdir()
    (KB / ".environment-setup.md").write_text("setup\n", encoding="utf-8")
    for name in (".env", ".env.local", "x.secret", "x.key", "x.pem"):
        (KB / name).write_text("secret\n", encoding="utf-8")

    os.symlink(outside_file, KB / "outside-link")
    os.symlink(KB / ".git" / "config", KB / "git-config-link")

    _previous_second_brain_dir = os.environ.get("SECOND_BRAIN_DIR")
    os.environ["SECOND_BRAIN_DIR"] = str(KB)

    spec = importlib.util.spec_from_file_location("mcp_server_under_test", SERVER_PATH)
    server = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(server)


def tearDownModule() -> None:
    if _previous_second_brain_dir is None:
        os.environ.pop("SECOND_BRAIN_DIR", None)
    else:
        os.environ["SECOND_BRAIN_DIR"] = _previous_second_brain_dir

    for name in ("mcp.server.fastmcp", "mcp.server", "mcp"):
        sys.modules.pop(name, None)

    if _outside_tmp is not None:
        _outside_tmp.cleanup()
    if _workspace_tmp is not None:
        _workspace_tmp.cleanup()


class SafePathTests(unittest.TestCase):
    def test_plain_relative_file_allowed(self):
        result = server.safe_path("wiki/index.md")
        self.assertEqual(result, (KB / "wiki" / "index.md").resolve())
        self.assertTrue(result == KB or KB in result.parents)

    def test_absolute_path_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path(str(KB / "SCHEMA.md"))

    def test_dotdot_segment_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path("wiki/../SCHEMA.md")

    def test_leading_dotdot_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path("../outside.txt")

    def test_symlink_pointing_outside_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path("outside-link")

    def test_symlink_pointing_at_git_config_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path("git-config-link")

    def test_file_under_git_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path(".git/config")

    def test_file_under_overmind_logs_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path(".overmind/logs/run.log")

    def test_dot_env_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path(".env")

    def test_dot_env_local_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path(".env.local")

    def test_dot_envrc_refused(self):
        # direnv files often export secrets
        with self.assertRaises(ValueError):
            server.safe_path(".envrc")

    def test_secret_extension_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path("x.secret")

    def test_key_extension_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path("x.key")

    def test_pem_extension_refused(self):
        with self.assertRaises(ValueError):
            server.safe_path("x.pem")

    def test_dot_environment_setup_md_allowed(self):
        result = server.safe_path(".environment-setup.md")
        self.assertEqual(result, (KB / ".environment-setup.md").resolve())

    def test_envs_directory_allowed(self):
        result = server.safe_path(".envs")
        self.assertEqual(result, (KB / ".envs").resolve())

    def test_file_inside_envs_directory_allowed(self):
        result = server.safe_path(".envs/note.md")
        self.assertEqual(result, (KB / ".envs" / "note.md").resolve())


class InboxWriteTests(unittest.TestCase):
    def _inbox_files(self, filename):
        # write_inbox prefixes the name with YYYY-MM-DD-, so match that shape
        # exactly rather than using a loose suffix match.
        return list((KB / "inbox").glob(f"????-??-??-{filename}"))

    def _today(self):
        from datetime import datetime

        return datetime.now().astimezone().strftime("%Y-%m-%d")

    def test_valid_name_creates_file_with_content(self):
        filename = "valid-note.md"
        content = "# Hello\n\nbody text\n"
        result = server.write_inbox(filename, content)

        self.assertTrue(result.startswith("Written: inbox/"), result)
        dest = KB / "inbox" / f"{self._today()}-{filename}"
        self.assertTrue(dest.is_file())
        written = dest.read_text(encoding="utf-8")
        self.assertTrue(written.endswith(content))
        self.assertIn("captured:", written)
        self.assertEqual(result, f"Written: inbox/{dest.name}")

    def test_existing_name_refused_and_file_unchanged(self):
        filename = "duplicate-note.md"
        first = server.write_inbox(filename, "first content\n")
        self.assertTrue(first.startswith("Written:"), first)
        dest = KB / "inbox" / f"{self._today()}-{filename}"
        before = dest.read_text(encoding="utf-8")

        second = server.write_inbox(filename, "second content\n")

        self.assertIn("already exists", second)
        self.assertEqual(dest.read_text(encoding="utf-8"), before)
        self.assertNotIn("second content", dest.read_text(encoding="utf-8"))

    def test_uppercase_name_refused(self):
        result = server.write_inbox("Upper.md", "content\n")
        self.assertTrue(result.startswith("Error:"), result)
        self.assertEqual(self._inbox_files("Upper.md"), [])

    def test_slash_in_name_refused(self):
        result = server.write_inbox("sub/note.md", "content\n")
        self.assertTrue(result.startswith("Error:"), result)
        self.assertEqual(self._inbox_files("note.md"), [])

    def test_dotdot_in_name_refused(self):
        result = server.write_inbox("../note.md", "content\n")
        self.assertTrue(result.startswith("Error:"), result)

    def test_trailing_newline_in_name_refused(self):
        result = server.write_inbox("note.md\n", "content\n")
        self.assertTrue(result.startswith("Error:"), result)
        self.assertEqual(self._inbox_files("note.md"), [])

    def test_non_markdown_name_refused(self):
        result = server.write_inbox("note.txt", "content\n")
        self.assertTrue(result.startswith("Error:"), result)

    def test_oversized_content_refused(self):
        filename = "too-big.md"
        content = "x" * (server.MAX_CONTENT_BYTES + 1)
        result = server.write_inbox(filename, content)
        self.assertTrue(result.startswith("Error:"), result)
        self.assertIn("exceeds", result)
        self.assertEqual(self._inbox_files(filename), [])

    def test_read_capped_refuses_file_over_one_mb(self):
        path = KB / "big-read.txt"
        path.write_bytes(b"x" * (server.MAX_READ_BYTES + 1))
        with self.assertRaises(ValueError):
            server.read_capped(path)

    def test_read_capped_reads_small_file(self):
        path = KB / "small-read.txt"
        path.write_text("small\n", encoding="utf-8")
        self.assertEqual(server.read_capped(path), "small\n")


if __name__ == "__main__":
    unittest.main()
