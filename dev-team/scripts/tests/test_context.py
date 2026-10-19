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
                 "### data.Prices: type", "## Layout (`dt layout quant`)",
                 "## Interfaces (frozen", "### data.RawPrices: type",
                 "## Writes (edit only these files", "<!-- tasks/plan.md:95 -->", "### M1-T10: Delisting-aware universe"]
        positions = [out.index(s) for s in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Sample: tests/contracts/data.RawPrices/ (exists)\n", out)
        self.assertIn("- src/quant/data/universe.py (from M1-T03)\n- tests/unit/quant/test_universe.py (from M1-T03)\n",
                      out)          # its spine task wrote them first: extend, don't start over
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
        self.assertEqual(data["writes"], [{"path": "src/quant/stats/pipeline.py", "exists": False, "folder": False,
                                           "from": []},           # M1-T01's src/quant/stats/** folder doesn't count
                                          {"path": "tests/unit/quant/test_pl02_smoke.py", "exists": False,
                                           "folder": False, "from": []}])

    def test_deterministic(self):
        self.assertEqual(run_dt(QUANT, "context", "M1-T11"), run_dt(QUANT, "context", "M1-T11"))

    def test_json(self):
        code, out, _ = run_dt(QUANT, "context", "M1-T11", "--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([r["ref"] for r in data["read"]], ["PL-02", "TC-02", "STAT-03", "stats.Cov", "stats.clean_eigen"])
        self.assertEqual(data["lines"], data["text"].count("\n"))
        self.assertEqual(data["interfaces"], [])
        self.assertEqual(data["writes"][0], {"path": "src/quant/stats/rmt.py", "exists": False, "folder": False,
                                             "from": ["M1-T05"]})
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

    def test_a_file_an_upstream_task_writes_names_it(self):
        """M1-T10 waits on M1-T03, which waits on M1-T01, whose Writes claim src/quant/data/**: the seam is there
        once the builder starts, so the packet says who writes it, not "missing"."""
        self.set_read("PL-01, src/quant/data/seams.py")
        code, out, _ = self.dt("context", "M1-T10")
        self.assertEqual(code, 0)
        self.assertIn("### src/quant/data/seams.py\n(not in the repo yet: M1-T01 writes it before this task starts)\n",
                      out)

    def long_table(self, rows: int) -> None:
        """PL-01 with `rows` step rows: read_raw, apply_universe, then helpers 3, 4, …"""
        last = "| 2 | `apply_universe` | data | RawPrices, dates → Prices | static universe, no delistings | DATA-02 |"
        extra = "".join(f"\n| {n} | `helper_{n}` | data | Prices → Prices | identity | DATA-01 |" for n in range(3, rows + 1))
        self.replace("docs/packages/quant/pipelines.md", last, last + extra)

    def test_long_step_table_keeps_the_tasks_own_rows(self):
        self.long_table(13)
        code, out, _ = self.dt("context", "M1-T10")          # Step: PL-01.apply_universe
        self.assertEqual(code, 0)
        self.assertIn("| # | Step | Owner | In → Out | Spine version | Covers |\n|---|---|---|---|---|---|\n"
                      "| 2 | `apply_universe` | data | RawPrices, dates → Prices | static universe, no delistings | DATA-02 |\n"
                      "(1 of 13 step rows: the ones M1-T10 builds; the rest are other tasks')\n", out)
        self.assertNotIn("`read_raw`", out.split("## Interfaces")[0])
        self.assertNotIn("helper_13", out)
        data = json.loads(self.dt("context", "M1-T10", "--json")[1])
        self.assertEqual(data["read"][0]["rows"], "1 of 13")

    def test_wiring_task_gets_the_whole_table(self):
        self.long_table(13)
        _, out, _ = self.dt("context", "M1-T08")             # Step: PL-01, the wiring task
        self.assertIn("helper_13", out)
        self.assertNotIn("step rows: the ones", out)

    def test_short_table_is_whole(self):
        self.long_table(12)
        _, out, _ = self.dt("context", "M1-T10")
        self.assertIn("`read_raw`", out)
        self.assertNotIn("step rows: the ones", out)

    def test_nested_types_are_pulled_until_closed(self):
        # Read names stats.CovReport; its signature names Factors, whose signature (edited) names Returns.
        self.set_read("PL-01, stats.CovReport")
        self.replace("docs/packages/quant/contract.md", "class Factors: loadings: np.ndarray;",
                     "class Factors: loadings: np.ndarray; source: Returns;")
        code, out, _ = self.dt("context", "M1-T10", "--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([(i["id"], i["named_by"]) for i in data["interfaces"]],
                         [("data.RawPrices", None), ("data.Prices", None), ("stats.Factors", "stats.CovReport"),
                          ("stats.Returns", "stats.Factors")])
        self.assertIn("<!-- docs/packages/quant/contract.md:40 · named by stats.CovReport -->\n### stats.Factors: type",
                      data["text"])

    def test_a_name_defined_inline_pulls_its_section(self):
        self.set_read("PL-01, stats.clean_eigen")
        self.replace("docs/packages/quant/contract.md", "`def clean_eigen(cov: Cov, *, n_obs: int) -> Cov`",
                     "`def clean_eigen(cov: Cov, *, n_obs: int, edge: Edge) -> Cov`")
        self.replace("docs/packages/quant/contract.md", "class Weights: values: np.ndarray; tickers: tuple[str, ...]`",
                     "class Weights: values: np.ndarray; tickers: tuple[str, ...]` and `Edge = float`")
        data = json.loads(self.dt("context", "M1-T10", "--json")[1])
        self.assertIn(("portfolio.Weights", "stats.clean_eigen"), [(i["id"], i["named_by"]) for i in data["interfaces"]])

    def test_writes_from_an_ancestor(self):
        code, out, _ = self.dt("context", "M1-T14")
        self.assertEqual(code, 0)
        self.assertIn("- src/quant/stats/pipeline.py (from M1-T09)\n", out)

    def test_budget_warning(self):
        self.write("big.txt", "line\n" * 2100)
        self.set_read("PL-01, big.txt")
        code, out, err = self.dt("context", "M1-T10")
        self.assertEqual(code, 0)
        self.assertIn("budget 2000", err)
        self.assertGreater(out.count("\n"), 2000)


if __name__ == "__main__":
    unittest.main()


class ContextConformanceTest(FixtureCopy):
    """A system task's packet names each fake it replaces with the real provider, so it runs the fake's cases on it."""

    def test_system_task_runs_the_fakes_cases_on_the_real_provider(self):
        self.write("tests/contracts/data.load_prices/fake.py", '"""Fake."""\n')
        self.write("tests/contracts/data.load_prices/test_load_prices_contract.py", '"""Cases."""\n')
        code, out, err = self.dt("context", "M1-T14")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("## Conformance (each fake's contract cases, run on the real provider)\n", out)
        self.assertIn("- data.load_prices: tests/contracts/data.load_prices/ (fake.py, test_load_prices_contract.py)\n",
                      out)
        self.assertIn("--type <symbol>", out)
        self.assertLess(out.index("## Conformance"), out.index("## Writes"))
        self.assertNotIn("## Conformance", self.dt("context", "M1-T09")[1])        # wiring: still on the fakes

    def test_no_fake_no_conformance(self):
        code, out, _ = self.dt("context", "M1-T14")
        self.assertEqual(code, 0)
        self.assertNotIn("## Conformance", out)
