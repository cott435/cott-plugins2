"""dt base: records HEAD's sha in the plan header."""
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


@unittest.skipUnless(shutil.which("git"), "git not installed")
class BaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "q"
        shutil.copytree(QUANT, self.root)
        git = ["git", "-C", str(self.root), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(git + ["init", "-q"], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "init"], check=True)
        self.sha = subprocess.run(git + ["rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_base(self) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return dt.main(["--root", str(self.root), "base"])

    def header(self) -> str:
        return (self.root / "tasks" / "plan.md").read_text().splitlines()[2]

    def test_replaces_existing_base(self):
        self.assertEqual(self.run_base(), 0)
        self.assertIn(f"**Base:** {self.sha} · **Last updated:**", self.header())

    def test_replaces_pending_base(self):
        plan = self.root / "tasks" / "plan.md"
        plan.write_text(plan.read_text().replace("**Base:** 3f2c1ab", "**Base:** —"))
        self.run_base()
        self.assertIn(f"**Base:** {self.sha} ·", self.header())
        self.assertNotIn("—", self.header())

    def test_adds_missing_base_after_status(self):
        plan = self.root / "tasks" / "plan.md"
        plan.write_text(plan.read_text().replace("**Base:** 3f2c1ab · ", ""))
        self.run_base()
        self.assertIn(f"**Status:** In progress · **Base:** {self.sha} ·", self.header())

    def test_keeps_crlf_and_mode(self):
        plan = self.root / "tasks" / "plan.md"
        plan.write_bytes(plan.read_bytes().replace(b"\n", b"\r\n"))
        plan.chmod(0o640)
        self.assertEqual(self.run_base(), 0)
        data = plan.read_bytes()
        self.assertIn(f"**Base:** {self.sha} ·".encode(), data)
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        self.assertEqual(plan.stat().st_mode & 0o777, 0o640)


if __name__ == "__main__":
    unittest.main()
