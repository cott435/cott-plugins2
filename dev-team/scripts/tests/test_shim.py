"""scripts/dt, the executable shim: one word that runs dt.py, so `DT=…/dt; $DT next` works in zsh, which doesn't
word-split `$DT` (iteration 9's 25 exit-127 calls held `python3 …/dt.py` in the variable)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dt_helpers import QUANT, run_dt

SCRIPTS = Path(__file__).resolve().parents[1]
SHIM = SCRIPTS / "dt"
SHELLS = [s for s in ("zsh", "bash", "sh") if shutil.which(s)]


def in_shell(shell: str, dt: str, root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([shell, "-c", f'DT="{dt}"; $DT --root "{root}" next'], capture_output=True, text=True)


class ShimTest(unittest.TestCase):
    def test_executable_with_a_python_shebang(self):
        self.assertTrue(os.access(SHIM, os.X_OK))
        self.assertEqual(SHIM.read_text(encoding="utf-8").splitlines()[0], "#!/usr/bin/env python3")

    def test_a_variable_holding_the_shim_runs_in_every_shell(self):
        for shell in SHELLS:
            r = in_shell(shell, str(SHIM), QUANT)
            self.assertEqual((shell, r.returncode), (shell, 0), r.stderr)
            self.assertTrue(r.stdout.startswith("next: "), r.stdout)

    @unittest.skipUnless(shutil.which("zsh"), "zsh not installed")
    def test_python3_and_a_path_in_one_variable_fails_in_zsh(self):
        r = in_shell("zsh", f"python3 {SCRIPTS / 'dt.py'}", QUANT)
        self.assertEqual(r.returncode, 127)


class SummaryLineTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "q"
        shutil.copytree(QUANT, self.root)

    def test_names_the_shim(self):
        self.assertEqual(run_dt(self.root, "status", "--summary")[1].splitlines()[-1], f"dt: {SHIM}")

    def test_falls_back_to_python3_when_the_shim_is_not_executable(self):
        with mock.patch("os.access", return_value=False):
            last = run_dt(self.root, "status", "--summary")[1].splitlines()[-1]
        self.assertEqual(last, f"dt: python3 {SCRIPTS / 'dt.py'}")


if __name__ == "__main__":
    unittest.main()
