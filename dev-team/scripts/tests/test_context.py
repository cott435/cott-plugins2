"""dt context: the builder's packet — Read: sections, layout, interfaces, Writes:, then the task last."""
from __future__ import annotations

import json
import unittest

from dt_helpers import QUANT, FixtureCopy, run_dt


class ContextFixtureTest(unittest.TestCase):
    def test_order_and_content(self):
        code, out, err = run_dt(QUANT, "context", "M1-T10")
        self.assertEqual((code, err), (0, ""))
        lines = out.splitlines()
        self.assertEqual(lines[0], "# Context for M1-T10: package quant · mode split · kind thicken")
        self.assertTrue(lines[1].startswith("Read only what is below"))
        order = ["<!-- docs/packages/quant/pipelines.md:5 -->", "## PL-01: Load prices",
                 "### TC-01: Delisted name drops out", "- **DATA-02** Delisted names",
                 "### data.Prices: Point-in-time price panel", "## Layout (`dt layout quant`)",
                 "## Interfaces (frozen", "### data.RawPrices: Raw price rows",
                 "## Writes (edit only these files", "<!-- tasks/plan.md:94 -->", "### M1-T10: Delisting-aware universe"]
        positions = [out.index(s) for s in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Sample: tests/contracts/data.RawPrices/sample.json (exists)\n", out)
        self.assertIn("- src/quant/data/universe.py (new)\n- tests/unit/quant/test_universe.py (new)\n", out)
        self.assertIn("    pipeline.py — PL-01 entry: load prices.\n", out)
        self.assertEqual(out.count("### data.Prices:"), 1)          # read already: not repeated as an interface
        self.assertNotIn("## Files likely", out)
        self.assertNotIn("## PL-02", out)          # only what Read: lists

    def test_wiring_gets_every_step_interface(self):
        code, out, _ = run_dt(QUANT, "context", "M1-T09", "--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([i["id"] for i in data["interfaces"]],
                         ["data.Prices", "stats.Returns", "stats.Cov", "stats.Factors", "stats.estimate_cov",
                          "stats.clean_eigen"])
        self.assertEqual(data["kind"], "wiring")
        self.assertEqual(data["writes"], [{"path": "src/quant/stats/pipeline.py", "exists": False, "folder": False},
                                          {"path": "src/quant/stats/__main__.py", "exists": False, "folder": False}])

    def test_deterministic(self):
        self.assertEqual(run_dt(QUANT, "context", "M1-T11"), run_dt(QUANT, "context", "M1-T11"))

    def test_json(self):
        code, out, _ = run_dt(QUANT, "context", "M1-T11", "--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([r["ref"] for r in data["read"]], ["PL-02", "TC-02", "STAT-03", "stats.Cov", "stats.clean_eigen"])
        self.assertEqual(data["lines"], data["text"].count("\n"))
        self.assertEqual(data["interfaces"], [])
        self.assertEqual(data["writes"][0], {"path": "src/quant/stats/rmt.py", "exists": False, "folder": False})
        self.assertEqual(data["files_likely"], [])

    def test_missing_task(self):
        code, out, err = run_dt(QUANT, "context", "M1-T99")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("M1-T99 not found", err)


class ContextLegacyTest(FixtureCopy):
    """A task from before Writes: its Files likely list, no Kind in the preamble."""
    legacy = True

    def test_files_likely(self):
        code, out, err = self.dt("context", "M1-T03")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out.splitlines()[0], "# Context for M1-T03: package quant · mode split")
        self.assertIn("## Files likely\n- src/quant/data/steps.py (exists)\n- tests/unit/quant/test_universe.py (new)\n", out)
        self.assertLess(out.index("## Files likely"), out.index("### M1-T03: Delisting-aware universe"))
        self.assertTrue(out.rstrip().endswith("**Files likely:** src/quant/data/steps.py, "
                                              "tests/unit/quant/test_universe.py"))
        data = json.loads(self.dt("context", "M1-T03", "--json")[1])
        self.assertEqual((data["kind"], data["writes"]), ("", []))
        self.assertEqual(data["files_likely"][0], {"path": "src/quant/data/steps.py", "exists": True})


class ContextCopyTest(FixtureCopy):
    def set_read(self, value: str) -> None:
        self.replace("tasks/plan.md", "**Read:** PL-01, TC-01, DATA-02, data.Prices", f"**Read:** {value}")

    def test_retired_read_id_fails(self):
        self.set_read("PL-01, PL-04")
        code, out, err = self.dt("context", "M1-T10")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("PL-04 is retired", err)

    def test_undefined_read_id_fails(self):
        self.set_read("PL-01, NOPE-01")
        code, _, err = self.dt("context", "M1-T10")
        self.assertEqual(code, 1)
        self.assertIn("NOPE-01 is not defined", err)

    def test_file_entries_are_fenced(self):
        self.write("notes/data.md", "# Notes\n```python\nx = 1\n```\n")
        self.set_read("PL-01, notes/data.md, `src/quant/data/steps.py` (current code), missing/file.py")
        code, out, _ = self.dt("context", "M1-T10")
        self.assertEqual(code, 0)
        self.assertIn("### notes/data.md\n````markdown\n# Notes\n```python\nx = 1\n```\n````\n", out)
        self.assertIn("### src/quant/data/steps.py\n```python\n\"\"\"PL-01 steps", out)
        self.assertIn("### missing/file.py\n(missing: not in the repo yet)\n", out)

    def test_budget_warning(self):
        self.write("big.txt", "line\n" * 2100)
        self.set_read("PL-01, big.txt")
        code, out, err = self.dt("context", "M1-T10")
        self.assertEqual(code, 0)
        self.assertIn("budget 2000", err)
        self.assertGreater(out.count("\n"), 2000)


if __name__ == "__main__":
    unittest.main()
