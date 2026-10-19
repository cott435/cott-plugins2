"""A throwaway git repo of fixtures/buildmini for the build-command tests, with a stub `scripts/check.sh`.

The stub's verdicts come from files outside the repo (so neither checkout is ever dirty): `<ctl>/<mode>` holds
one exit code per line, used first to last, then 0; every call is appended to `<ctl>/calls` as `<cwd> <args>`.
`protected` prints a fixed protected list.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dt_helpers import HERE, run_dt, run_main

BUILDMINI = HERE / "fixtures" / "buildmini"
PROTECTED = ("tests/intent/**", "tests/fixtures/**", "tests/conftest.py", "pyproject.toml", "uv.lock",
             "CONSTRAINTS.md", "scripts/**", ".claude/agents/**", ".claude/settings.json")
STUB = """#!/usr/bin/env bash
# Test stub for scripts/check.sh: see build_helpers.py.
mode="${1:-gate}"
ctl="${STUB_DIR:?}"
echo "$(pwd -P) $*" >>"$ctl/calls"
if [ "$mode" = protected ]; then
  printf '%s\\n' PROTECTED_LIST
  exit 0
fi
if [ -s "$ctl/$mode" ]; then
  rc=$(head -n 1 "$ctl/$mode")
  tail -n +2 "$ctl/$mode" >"$ctl/$mode.tmp" && mv "$ctl/$mode.tmp" "$ctl/$mode"
  echo "stub $mode: exit $rc" >&2
  exit "$rc"
fi
echo "stub $mode: pass" >&2
exit 0
""".replace("PROTECTED_LIST", " ".join(f"'{g}'" for g in PROTECTED))
TC01_TEST = '"""Intent: TC-01."""\n\n\ndef test_tc01() -> None:\n    assert False\n'


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


class BuildCase(unittest.TestCase):
    """`self.root`: the main checkout, a git repo of buildmini on `main` (`start=True`: on `build/M1`)."""
    start = True

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.root, self.ctl, self.wts = tmp / "repo", tmp / "ctl", tmp / "wts"
        self.ctl.mkdir()
        self.wts.mkdir()
        shutil.copytree(BUILDMINI, self.root, ignore=shutil.ignore_patterns("README.md", "make_live.py"))
        self.write("scripts/check.sh", STUB)
        (self.root / "scripts/check.sh").chmod(0o755)
        git(self.root, "init", "-q", "-b", "main")
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("commit.gpgsign", "false")):
            git(self.root, "config", k, v)
        self.commit("fixture")
        env = mock.patch.dict(os.environ, {"STUB_DIR": str(self.ctl)})
        env.start()
        self.addCleanup(env.stop)
        if self.start:
            code, out = self.dt_json("build", "start", "M1")
            assert code == 0, out

    def tearDown(self):
        self._tmp.cleanup()

    # ---- files and git ----------------------------------------------------------------------------

    def write(self, rel: str, text: str, root: Path | None = None) -> None:
        p = (root or self.root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def read(self, rel: str, root: Path | None = None) -> str:
        return ((root or self.root) / rel).read_text(encoding="utf-8")

    def edit(self, rel: str, old: str, new: str) -> None:
        text = self.read(rel)
        assert old in text, f"{old!r} not in {rel}"
        self.write(rel, text.replace(old, new, 1))

    def commit(self, msg: str, root: Path | None = None) -> str:
        git(root or self.root, "add", "-A")
        git(root or self.root, "commit", "-q", "-m", msg)
        return git(root or self.root, "rev-parse", "HEAD")

    def head(self, root: Path | None = None) -> str:
        return git(root or self.root, "rev-parse", "HEAD")

    def status(self) -> str:
        return git(self.root, "status", "--porcelain")

    def stub(self, mode: str, *codes: int) -> None:
        (self.ctl / mode).write_text("".join(f"{c}\n" for c in codes), encoding="utf-8")

    def calls(self) -> list[str]:
        p = self.ctl / "calls"
        return p.read_text(encoding="utf-8").splitlines() if p.exists() else []

    def worktree(self, name: str) -> Path:
        path = self.wts / name
        git(self.root, "worktree", "add", "-q", str(path), "-b", f"wt-{name}")
        return path

    def fake_land(self, task: str, role: str = "solo") -> str:
        """Tick the task and commit with its trailer on the main checkout, as `dt land` would."""
        self.edit("tasks/todo.md", f"- [ ] {task}", f"- [x] {task}")
        return self.commit(f"{task}: landed\n\nDt-Landed: {task} {role}")

    def pass_barrier(self) -> None:
        empty = self.ctl / "M1-T01.mini.md"
        empty.write_text("No findings.\n", encoding="utf-8")
        code, out = self.dt_json("finding", "--from", str(empty))
        assert code == 0 and out["outcome"] == "passed", out

    # ---- dt -----------------------------------------------------------------------------------------

    def dt(self, *args: str, root: Path | None = None) -> tuple[int, str, str]:
        return run_dt(root or self.root, *args)

    def dt_json(self, *args: str, root: Path | None = None):
        code, out, err = self.dt(*args, root=root)
        try:
            return code, json.loads(out)
        except ValueError:
            raise AssertionError(f"not JSON (exit {code}): {out!r} {err!r}") from None

    def ready(self, *extra: str) -> dict:
        code, out = self.dt_json("ready", "--halves", *extra)
        self.assertEqual(code, 0, out)
        return out

    def reserve(self, *extra: str) -> list[tuple[str, str]]:
        code, out = self.dt_json("ready", "--reserve", *extra)
        self.assertEqual(code, 0, out)
        return [(r["id"], r["role"]) for r in out["rows"]]

    def claim(self, task: str, role: str, wt: Path) -> tuple[int, str, str]:
        return self.dt("claim", task, "--role", role, root=wt)

    def land(self, task: str, role: str, *extra: str) -> dict:
        code, out = self.dt_json("land", task, "--role", role, *extra)
        self.assertEqual(code, 0, out)
        return out

    def hook(self, *argv: str, stdin: str = "") -> tuple[int, str]:
        return run_main(*argv, stdin=stdin)

    def state(self) -> Path:
        return self.root / ".git" / "dt-build"

    def records(self, kind: str) -> list[str]:
        folder = self.state() / kind
        return sorted(p.stem for p in folder.glob("*.json")) if folder.is_dir() else []

    # ---- a whole half -------------------------------------------------------------------------------

    def run_half(self, task: str, role: str, files: dict[str, str], name: str | None = None) -> Path:
        """Reserve (if needed), make a worktree, claim, write the files; returns the worktree."""
        if f"{task}.{role}" not in self.records("reserved") + self.records("claims"):
            self.assertIn((task, role), self.reserve())
        wt = self.worktree(name or f"{task}-{role}")
        code, out, err = self.claim(task, role, wt)
        self.assertEqual(code, 0, err)
        for rel, text in files.items():
            self.write(rel, text, root=wt)
        return wt

    def to_phase1(self) -> None:
        """M1-T01 landed and its barrier review passed."""
        self.fake_land("M1-T01")
        self.pass_barrier()
