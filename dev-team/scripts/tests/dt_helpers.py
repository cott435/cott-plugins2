"""Shared helpers for command tests: run `dt` in-process, and work on a throwaway copy of the quant fixture
(`FixtureCopy` as a TestCase base, or `Project` when a test needs git). Either can swap in the old-style M1 plan
(`fixtures/legacy-plan/`: Phase 0 spines, `Parallel` groups, `Files likely`) so backward-compatible parsing stays
tested; the quant fixture's own plan is interface-first."""
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
LEGACY_PLAN = HERE / "fixtures" / "legacy-plan"
PROBES = HERE / "fixtures" / "probes"

# What `add_probes` writes into the architecture: PB-01 on the Accepted AD-03, and AD-04 (Proposed) citing PB-02.
AD03_PROBE = "- **Probe:** PB-01 — are Sharadar's raw and adjusted closes told apart?\n"
AD04 = """### AD-04: FRED for the risk-free rate
**Status:** Proposed · **Date:** 2026-10-17 · **Scope:** portfolio
- **Context:** PORT-02 compares portfolios on excess returns.
- **Decision:** FRED's DTB3 series, read daily.
- **Alternatives:** A constant rate — hides the 2008 drop.
- **Consequences:** One free key, held by the user.
- **Probe:** PB-02 — does DTB3 reach 2006, under terms that allow local storage?

"""
FAKE_KEY = "fk7Qp2xLm9Rt4Wz8"           # the probe's .env value: evidence must never hold it


def copy_quant(dest: Path, legacy: bool = False) -> None:
    """Copy the quant fixture to dest; `legacy` replaces its tasks/plan.md and todo.md with the old-style plan."""
    shutil.copytree(QUANT, dest)
    if legacy:
        for name in ("plan.md", "todo.md"):
            shutil.copyfile(LEGACY_PLAN / name, dest / "tasks" / name)
def add_probes(root: Path) -> None:
    """Lay fixtures/probes over a quant copy: docs/probes.md (PB-01 Answered pass, PB-02 Ready with the agent's
    C1 run, PB-03 retired) and probes/ (PB-02's sample holds a planted email); cite them from the architecture;
    and write what git must never hold: PB-02's `.env` and `.env.example`, and PB-01's `out/`."""
    shutil.copytree(PROBES, root, dirs_exist_ok=True)
    arch = root / "docs" / "architecture.md"
    text = arch.read_text(encoding="utf-8")
    text = text.replace("- **Consequences:** Binary files; needs pyarrow.\n",
                        "- **Consequences:** Binary files; needs pyarrow.\n" + AD03_PROBE, 1)
    text = text.replace("## Risks and open questions", AD04 + "## Risks and open questions", 1)
    arch.write_text(text, encoding="utf-8")
    pb02 = root / "probes" / "PB-02-fred-rates"
    (pb02 / ".env").write_text(f"FRED_API_KEY={FAKE_KEY}\nFRED_ENV=production\n", encoding="utf-8")
    (pb02 / ".env.example").write_text("FRED_API_KEY=\n", encoding="utf-8")
    out = root / "probes" / "PB-01-sharadar-prices" / "out"
    out.mkdir()
    (out / "raw.json").write_text('{"access_token": "access-production-0000"}\n', encoding="utf-8")


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
    """Each test gets its own copy of fixtures/quant at self.root; the shared fixture is never touched. A subclass
    sets `legacy = True` for the old-style plan, or `probes = True` to lay fixtures/probes over it (`add_probes`)."""
    legacy = False
    probes = False

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "quant"
        copy_quant(self.root, self.legacy)
        if self.probes:
            add_probes(self.root)

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

    def __init__(self, git: bool = False, legacy: bool = False):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "quant"
        copy_quant(self.root, legacy)
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
