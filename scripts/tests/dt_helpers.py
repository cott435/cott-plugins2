"""Shared helpers for command tests: run `dt` in-process, and work on a throwaway copy of the quant fixture
(`FixtureCopy` as a TestCase base, or `Project` when a test needs git)."""
from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import dt  # noqa: E402

QUANT = HERE / "fixtures" / "quant"
HAS_GIT = shutil.which("git") is not None


def run_dt(root: Path, *args: str) -> tuple[int, str, str]:
    """(exit code, stdout, stderr) of `dt --root root args…`."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = dt.main(["--root", str(root), *args])
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 2
    return code, out.getvalue(), err.getvalue()


class FixtureCopy(unittest.TestCase):
    """Each test gets its own copy of fixtures/quant at self.root; the shared fixture is never touched."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "quant"
        shutil.copytree(QUANT, self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def dt(self, *args: str) -> tuple[int, str, str]:
        return run_dt(self.root, *args)

    def read(self, rel: str) -> str:
        with open(self.root / rel, encoding="utf-8", newline="") as f:
            return f.read()

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def replace(self, rel: str, old: str, new: str) -> None:
        text = self.read(rel)
        self.assertIn(old, text)
        self.write(rel, text.replace(old, new, 1))


class Project:
    """A copy of fixtures/quant in a temp dir. Call cleanup() (or use addCleanup) when done."""

    def __init__(self, git: bool = False):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "quant"
        shutil.copytree(QUANT, self.root)
        if git:
            self.git("init", "-q")
            self.git("add", "-A")
            self.commit("fixture")

    def cleanup(self):
        self._tmp.cleanup()

    def path(self, rel: str) -> Path:
        return self.root / rel

    def read(self, rel: str) -> str:
        return self.path(rel).read_text(encoding="utf-8")

    def write(self, rel: str, text: str):
        self.path(rel).parent.mkdir(parents=True, exist_ok=True)
        self.path(rel).write_text(text, encoding="utf-8")

    def edit(self, rel: str, old: str, new: str):
        text = self.read(rel)
        assert old in text, f"{old!r} not in {rel}"
        self.write(rel, text.replace(old, new, 1))

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t",
                               *args], check=True, capture_output=True, text=True).stdout

    def commit(self, msg: str):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)


def run_main(*argv: str, stdin: str = "") -> tuple[int, str]:
    """Run dt.main with raw argv and stdin (for hook modes); returns (exit code, stdout)."""
    out = io.StringIO()
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try:
                code = dt.main(list(argv))
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else 2
    finally:
        sys.stdin = old_stdin
    return code, out.getvalue()
