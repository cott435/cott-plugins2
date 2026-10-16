"""dt context: the builder's packet — Read: sections, layout, files, then the task last."""
from __future__ import annotations

import json
import unittest

from dt_helpers import QUANT, FixtureCopy, run_dt


class ContextFixtureTest(unittest.TestCase):
    def test_order_and_content(self):
        code, out, err = run_dt(QUANT, "context", "M1-T03")
        self.assertEqual((code, err), (0, ""))
        lines = out.splitlines()
        self.assertEqual(lines[0], "# Context for M1-T03: package quant · mode split")
        self.assertTrue(lines[1].startswith("Read only what is below"))
        order = ["<!-- docs/packages/quant/pipelines.md:5 -->", "## PL-01: Load prices",
                 "### TC-01: Delisted name drops out", "- **DATA-02** Delisted names",
                 "### data.load_prices: Point-in-time prices", "## Layout (`dt layout quant`)",
                 "## Files likely", "<!-- tasks/plan.md:32 -->", "### M1-T03: Delisting-aware universe"]
        positions = [out.index(s) for s in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("- src/quant/data/steps.py (exists)\n- tests/unit/quant/test_universe.py (new)\n", out)
        self.assertIn("    pipeline.py — PL-01 entry: load prices.\n", out)
        self.assertTrue(out.rstrip().endswith("**Files likely:** src/quant/data/steps.py, "
                                              "tests/unit/quant/test_universe.py"))
        self.assertNotIn("## PL-02", out)          # only what Read: lists

    def test_deterministic(self):
        self.assertEqual(run_dt(QUANT, "context", "M1-T04"), run_dt(QUANT, "context", "M1-T04"))

    def test_json(self):
        code, out, _ = run_dt(QUANT, "context", "M1-T04", "--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([r["ref"] for r in data["read"]], ["PL-02", "TC-02", "STAT-03", "stats.clean_eigen"])
        self.assertEqual(data["lines"], data["text"].count("\n"))
        self.assertEqual(data["files_likely"][0], {"path": "src/quant/stats/rmt.py", "exists": False})

    def test_missing_task(self):
        code, out, err = run_dt(QUANT, "context", "M1-T99")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("M1-T99 not found", err)


class ContextCopyTest(FixtureCopy):
    def set_read(self, value: str) -> None:
        self.replace("tasks/plan.md", "**Read:** PL-01, TC-01, DATA-02, data.load_prices", f"**Read:** {value}")

    def test_retired_read_id_fails(self):
        self.set_read("PL-01, PL-04")
        code, out, err = self.dt("context", "M1-T03")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("PL-04 is retired", err)

    def test_undefined_read_id_fails(self):
        self.set_read("PL-01, NOPE-01")
        code, _, err = self.dt("context", "M1-T03")
        self.assertEqual(code, 1)
        self.assertIn("NOPE-01 is not defined", err)

    def test_file_entries_are_fenced(self):
        self.write("notes/data.md", "# Notes\n```python\nx = 1\n```\n")
        self.set_read("PL-01, notes/data.md, `src/quant/data/steps.py` (current code), missing/file.py")
        code, out, _ = self.dt("context", "M1-T03")
        self.assertEqual(code, 0)
        self.assertIn("### notes/data.md\n````markdown\n# Notes\n```python\nx = 1\n```\n````\n", out)
        self.assertIn("### src/quant/data/steps.py\n```python\n\"\"\"PL-01 steps", out)
        self.assertIn("### missing/file.py\n(missing: not in the repo yet)\n", out)

    def test_budget_warning(self):
        self.write("big.txt", "line\n" * 2100)
        self.set_read("PL-01, big.txt")
        code, out, err = self.dt("context", "M1-T03")
        self.assertEqual(code, 0)
        self.assertIn("budget 2000", err)
        self.assertGreater(out.count("\n"), 2000)


if __name__ == "__main__":
    unittest.main()
