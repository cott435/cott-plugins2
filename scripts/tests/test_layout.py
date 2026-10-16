"""dt layout: real tree with docstrings, entry-call drift, never running project code."""
from __future__ import annotations

import json
import unittest

from dt_helpers import QUANT, FixtureCopy, run_dt


class LayoutFixtureTest(unittest.TestCase):
    def test_text(self):
        code, out, _ = run_dt(QUANT, "layout", "quant")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "package: quant",
            "root: src/quant/",
            "  __init__.py — Quant Lab.",
            "  data/",
            "    __init__.py — Point-in-time prices: the data component's contract exports.",
            "    pipeline.py — PL-01 entry: load prices.",
            "    steps.py — PL-01 steps: read raw rows, apply the universe.",
            "  stats/",
            "    __init__.py — Covariance and factor estimates.",
            "PL-01: ok",
            "PL-02: not built (src/quant/stats/pipeline.py missing)",
            "PL-03: not built (src/quant/portfolio/pipeline.py missing)",
        ])

    def test_json(self):
        code, out, _ = run_dt(QUANT, "layout", "quant", "--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["root"], "src/quant/")
        self.assertIn({"path": "data/pipeline.py", "dir": False, "doc": "PL-01 entry: load prices."}, data["tree"])
        p1 = data["pipelines"][0]
        self.assertEqual((p1["id"], p1["status"], p1["calls"]), ("PL-01", "ok", ["read_raw", "apply_universe"]))

    def test_unknown_package(self):
        code, out, _ = run_dt(QUANT, "layout", "nopkg")
        self.assertEqual(code, 2)
        self.assertIn("unknown package", out)


class LayoutCopyTest(FixtureCopy):
    def test_drift_exits_1(self):
        self.replace("src/quant/data/pipeline.py", "    return apply_universe(rows, cfg.start, cfg.end)",
                     "    return rows")
        code, out, _ = self.dt("layout", "quant")
        self.assertEqual(code, 1)
        self.assertIn("PL-01: drift — calls [read_raw] vs steps [read_raw, apply_universe]", out)

    def test_skips_caches_and_marks_missing_docstrings(self):
        self.write("src/quant/stats/cov.py", "def estimate_cov(r):\n    return r\n")
        self.write("src/quant/__pycache__/x.cpython-311.pyc", "")
        self.write("src/quant/.hidden/y.py", "")
        _, out, _ = self.dt("layout", "quant")
        self.assertIn("    cov.py — (no docstring)", out)
        self.assertNotIn("__pycache__", out)
        self.assertNotIn(".hidden", out)

    def test_project_code_is_never_run(self):
        marker = self.root / "ran.txt"
        self.write("src/quant/stats/pipeline.py",
                   f'"""PL-02 entry."""\nopen({str(marker)!r}, "w").write("x")\n\n'
                   "def run_cov_report(cfg):\n    load_prices(cfg)\n")
        code, out, _ = self.dt("layout", "quant")
        self.assertFalse(marker.exists())
        self.assertEqual(code, 1)
        self.assertIn("PL-02: drift — calls [load_prices] vs steps [load_prices, estimate_cov", out)

    def test_cross_component_step_via_module_attribute(self):
        self.write("src/quant/stats/pipeline.py",
                   '"""PL-02 entry."""\nfrom quant import data\nfrom quant.stats.pca import pca as run_pca\n\n'
                   "def run_cov_report(cfg):\n"
                   "    prices = data.load_prices(cfg.universe, cfg.start, cfg.end)\n"
                   "    cov = estimate_cov(prices.returns())\n"
                   "    cov = clean_eigen(cov, n_obs=len(prices))\n"
                   "    factors = run_pca(cov)\n"
                   "    return write_report(factors, cfg.out)\n")
        code, out, _ = self.dt("layout", "quant")
        self.assertEqual(code, 0)
        self.assertIn("PL-02: ok", out)


if __name__ == "__main__":
    unittest.main()
