#!/usr/bin/env python3
"""Tests for scripts/media-to-text.sh."""

import os
import shlex
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "media-to-text.sh"
CORE_TOOLS = ["bash", "basename", "dirname", "mkdir", "cp", "tr", "mktemp", "rm"]

WHISPER_CLI_BODY = textwrap.dedent(
    """\
    out=""
    prev=""
    for arg in "$@"; do
      if [[ "$prev" == "-of" ]]; then out="$arg"; fi
      prev="$arg"
    done
    mkdir -p "$(dirname "$out")"
    printf 'cli transcript\\n' > "$out.txt"
    """
)

WHISPER_BODY = textwrap.dedent(
    """\
    input=""
    outdir=""
    prev=""
    for arg in "$@"; do
      if [[ -z "$input" ]]; then input="$arg"; fi
      if [[ "$prev" == "--output_dir" ]]; then outdir="$arg"; fi
      prev="$arg"
    done
    stem="${input##*/}"
    stem="${stem%.*}"
    mkdir -p "$outdir"
    printf 'python whisper transcript\\n' > "$outdir/$stem.txt"
    """
)

FFMPEG_BODY = textwrap.dedent(
    """\
    for last in "$@"; do :; done
    printf 'RIFF' > "$last"
    """
)

PDFTOTEXT_BODY = textwrap.dedent(
    """\
    out="${!#}"
    printf 'pdf text\\n' > "$out"
    """
)


class MediaToTextTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.sysbin = self.tmp / "sysbin"
        self.sysbin.mkdir()
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.tmpdir = self.tmp / "tmp"
        self.tmpdir.mkdir()
        self.media = self.tmp / "media"
        self.media.mkdir()
        self.out = self.tmp / "out"
        self.log = self.tmp / "calls.log"
        self.log.write_text("")

        for name in CORE_TOOLS:
            src = shutil.which(name)
            self.assertIsNotNone(src, f"test environment needs {name}")
            (self.sysbin / name).symlink_to(src)

        self.bash = str(self.sysbin / "bash")

    def write_fake(self, name, body):
        path = self.bin / name
        path.write_text(
            "#!/usr/bin/env bash\n"
            f"printf '%s' {name} >> \"$CALL_LOG\"\n"
            'for arg in "$@"; do printf " %s" "$arg" >> "$CALL_LOG"; done\n'
            'printf "\\n" >> "$CALL_LOG"\n'
            + textwrap.dedent(body)
        )
        path.chmod(0o755)
        return path

    def make_media(self, name):
        path = self.media / name
        path.write_bytes(b"fake media")
        return path

    def write_model(self, path=None):
        if path is None:
            path = self.home / ".local/share/whisper.cpp/models/ggml-base.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"model")
        return path

    def run_script(self, source, extra_env=None):
        env = os.environ.copy()
        env["PATH"] = os.pathsep.join([str(self.bin), str(self.sysbin)])
        env["HOME"] = str(self.home)
        env["TMPDIR"] = str(self.tmpdir)
        env["CALL_LOG"] = str(self.log)
        env.pop("WHISPER_MODEL", None)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [self.bash, str(SCRIPT), str(source), str(self.out)],
            text=True,
            capture_output=True,
            env=env,
            timeout=30,
        )

    def call_args(self, tool):
        prefix = tool + " "
        return [
            shlex.split(line)
            for line in self.log.read_text().splitlines()
            if line.startswith(prefix)
        ]

    def test_whisper_cli_with_model_is_preferred(self):
        self.write_fake("whisper-cli", WHISPER_CLI_BODY)
        source = self.make_media("talk.mp3")
        model = self.tmp / "models" / "custom.bin"
        model.parent.mkdir()
        model.write_bytes(b"model")

        result = self.run_script(source, {"WHISPER_MODEL": str(model)})

        self.assertEqual(result.returncode, 0, result.stderr)
        expected = self.out / "talk.txt"
        self.assertTrue(expected.is_file())
        self.assertEqual(expected.read_text(), "cli transcript\n")
        self.assertIn(f"OK: {self.out}/talk.txt", result.stdout)

        calls = self.call_args("whisper-cli")
        self.assertEqual(len(calls), 1)
        args = calls[0]
        self.assertEqual(args[0], "whisper-cli")
        self.assertEqual(args[args.index("-m") + 1], str(model))
        self.assertEqual(args[args.index("-f") + 1], str(source))
        self.assertIn("-otxt", args)
        self.assertEqual(args[args.index("-of") + 1], str(self.out / "talk"))
        self.assertEqual(self.call_args("ffmpeg"), [])
        self.assertEqual(self.call_args("whisper"), [])

    def test_mp4_is_converted_and_temp_wav_is_removed(self):
        self.write_fake("whisper-cli", WHISPER_CLI_BODY)
        self.write_fake("ffmpeg", FFMPEG_BODY)
        model = self.write_model()
        source = self.make_media("clip.mp4")

        result = self.run_script(source)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.out / "clip.txt").read_text(), "cli transcript\n")

        ffmpeg_calls = self.call_args("ffmpeg")
        self.assertEqual(len(ffmpeg_calls), 1)
        ffmpeg_args = ffmpeg_calls[0]
        self.assertIn("-vn", ffmpeg_args)
        self.assertEqual(ffmpeg_args[ffmpeg_args.index("-ac") + 1], "1")
        self.assertEqual(ffmpeg_args[ffmpeg_args.index("-ar") + 1], "16000")
        temp_wav = Path(ffmpeg_args[-1])
        self.assertTrue(temp_wav.name.startswith("media-to-text."))
        self.assertTrue(temp_wav.name.endswith(".wav"))
        self.assertEqual(temp_wav.parent, self.tmpdir)
        self.assertFalse(temp_wav.exists())

        cli_args = self.call_args("whisper-cli")[0]
        self.assertEqual(cli_args[cli_args.index("-m") + 1], str(model))
        self.assertEqual(cli_args[cli_args.index("-f") + 1], str(temp_wav))
        self.assertEqual(cli_args[cli_args.index("-of") + 1], str(self.out / "clip"))

    def test_missing_model_falls_back_to_python_whisper(self):
        self.write_fake("whisper-cli", WHISPER_CLI_BODY)
        self.write_fake("whisper", WHISPER_BODY)
        source = self.make_media("memo.m4a")

        result = self.run_script(source)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.out / "memo.txt").read_text(), "python whisper transcript\n"
        )
        self.assertEqual(self.call_args("whisper-cli"), [])
        whisper_calls = self.call_args("whisper")
        self.assertEqual(len(whisper_calls), 1)
        self.assertEqual(whisper_calls[0][0], "whisper")

    def test_no_transcriber_installed_exits_with_both_hints(self):
        source = self.make_media("note.mp3")

        result = self.run_script(source)

        self.assertEqual(result.returncode, 3)
        self.assertIn("whisper-cli", result.stderr)
        self.assertIn("whisper", result.stderr)
        self.assertIn("whisper.cpp", result.stderr)
        self.assertIn("pip install openai-whisper", result.stderr)
        self.assertFalse((self.out / "note.txt").exists())

    def test_txt_branch_still_copies(self):
        source = self.media / "note.txt"
        source.write_text("hello text\n")

        result = self.run_script(source)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.out / "note.txt").read_text(), "hello text\n")
        self.assertIn(f"OK: {self.out}/note.txt", result.stdout)

    def test_pdf_branch_still_uses_pdftotext(self):
        self.write_fake("pdftotext", PDFTOTEXT_BODY)
        source = self.make_media("doc.pdf")

        result = self.run_script(source)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.out / "doc.txt").read_text(), "pdf text\n")
        args = self.call_args("pdftotext")[0]
        self.assertIn("-layout", args)
        self.assertEqual(args[-1], str(self.out / "doc.txt"))


if __name__ == "__main__":
    unittest.main()
