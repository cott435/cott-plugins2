"""fixtures/buildmini, the live smoke-test project: clean for dt as it stands, and (DT_LIVE_FIXTURE=1) its
make_live.py builds a repo whose bar passes."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from build_helpers import BUILDMINI
from dt_helpers import run_dt

from devteam import model  # noqa: E402
from devteam.repo import Repo  # noqa: E402


class BuildminiTest(unittest.TestCase):
    def test_lint_and_roadmap_clean(self):
        self.assertEqual(run_dt(BUILDMINI, "lint")[:2], (0, "0 errors, 0 warnings\n"))
        self.assertEqual(run_dt(BUILDMINI, "roadmap", "--check")[0], 0)

    def test_build_planning_status(self):
        code, out, _ = run_dt(BUILDMINI, "status", "--skill", "build-planning", "--json")
        d = json.loads(out)
        self.assertEqual((code, d["mode"], d["progress"]), (0, "current", "0/4"))
        for k in ("blocked_tasks", "uncovered", "no_spine", "mode_violations", "boundaries_unfrozen", "skills_missing"):
            self.assertEqual(d[k], [], k)
        self.assertEqual(d["critical_path_halves"], ["M1-T01.solo", "M1-T02.solo", "M1-T03.implementer"])

    def test_plan_shape(self):
        tasks = model.tasks(Repo(BUILDMINI).plan)
        self.assertEqual({t.id: (t.kind, t.mode) for t in tasks},
                         {"M1-T01": ("interface", "solo"), "M1-T02": ("spine", "solo"),
                          "M1-T03": ("thicken", "split"), "M1-T04": ("wiring", "solo")})

    @unittest.skipUnless(os.environ.get("DT_LIVE_FIXTURE") and shutil.which("uv"), "set DT_LIVE_FIXTURE=1 (needs uv)")
    def test_make_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "live"
            subprocess.run([sys.executable, str(BUILDMINI / "make_live.py"), str(dest)], check=True,
                           capture_output=True)
            gate = subprocess.run(["bash", "scripts/check.sh", "gate", "--pkg", "mini"], cwd=dest, capture_output=True)
            self.assertEqual(gate.returncode, 0, gate.stderr.decode()[-2000:])
            code, out, _ = run_dt(dest, "status", "--skill", "build-setup", "--json")
            self.assertEqual(json.loads(out)["mode"], "current")


if __name__ == "__main__":
    unittest.main()
