"""devteam.code: docstrings, entry-function calls, pipeline drift and source folders (ast only)."""
from __future__ import annotations

import ast
import textwrap
import unittest

from dt_helpers import QUANT, FixtureCopy

from devteam import code, model
from devteam.repo import Repo


def calls_of(src: str, func: str = "run") -> list[str]:
    tree = ast.parse(textwrap.dedent(src))
    return code.entry_calls(tree, code.find_function(tree, func))


class EntryCallsTest(unittest.TestCase):
    def test_outermost_calls_in_order(self):
        self.assertEqual(calls_of("""
            def run(cfg):
                prices = load_prices(cfg.universe, cfg.start, cfg.end)
                cov = estimate_cov(prices.returns())
                cov = clean_eigen(cov, n_obs=len(prices))
                return write_report(pca(cov), cfg.out)
        """), ["load_prices", "estimate_cov", "clean_eigen", "write_report"])

    def test_attribute_and_import_alias_use_final_name(self):
        self.assertEqual(calls_of("""
            from quant.data import load_prices as lp
            import quant.stats as st

            def run(cfg):
                \"\"\"Docstring is not a call.\"\"\"
                p = lp(cfg)
                return st.estimate_cov(p)
        """), ["load_prices", "estimate_cov"])

    def test_nested_defs_skipped_compound_bodies_kept(self):
        self.assertEqual(calls_of("""
            def run(cfg):
                def helper():
                    hidden()
                if cfg.clean:
                    cov = clean_eigen(cfg)
                await_me = lambda: ignored()
                for x in items():
                    step(x)
        """), ["clean_eigen", "items", "step"])

    def test_async_entry(self):
        self.assertEqual(calls_of("async def run(c):\n    a = await fetch(c)\n    return save(a)\n"),
                         ["fetch", "save"])

    def test_missing_function(self):
        self.assertIsNone(code.find_function(ast.parse("def other(): pass"), "run"))


class DocstringTest(unittest.TestCase):
    def test_first_line(self):
        self.assertEqual(code.module_docstring(QUANT / "src/quant/data/pipeline.py"), "PL-01 entry: load prices.")


class DriftTest(FixtureCopy):
    def pipeline(self, pid: str) -> tuple[model.Pipeline, Repo]:
        repo = Repo(self.root)
        return next(p for p in model.all_pipelines(repo) if p.id == pid), repo

    def test_fixture_has_no_drift(self):
        repo = Repo(QUANT)
        for p in model.all_pipelines(repo):
            self.assertIsNone(code.pipeline_drift(repo, p), p.id)
        checks = {p.id: code.check_pipeline(repo, p).status for p in model.all_pipelines(repo)}
        self.assertEqual(checks, {"PL-01": "ok", "PL-02": "missing", "PL-03": "missing"})

    def test_reordered_calls_drift(self):
        self.write("src/quant/data/pipeline.py",
                   '"""PL-01 entry."""\n\ndef run_load_prices(cfg):\n'
                   '    rows = apply_universe(cfg)\n    return read_raw(rows)\n')
        p, repo = self.pipeline("PL-01")
        self.assertEqual(code.pipeline_drift(repo, p),
                         "calls [apply_universe, read_raw] vs steps [read_raw, apply_universe]")

    def test_extra_call_drifts(self):
        self.replace("src/quant/data/pipeline.py", "    return apply_universe",
                     "    log(rows)\n    return apply_universe")
        p, repo = self.pipeline("PL-01")
        self.assertIn("calls [read_raw, log, apply_universe]", code.pipeline_drift(repo, p))

    def test_undefined_entry_function_and_syntax_error(self):
        self.replace("src/quant/data/pipeline.py", "def run_load_prices", "def run_other")
        p, repo = self.pipeline("PL-01")
        self.assertEqual(code.pipeline_drift(repo, p), "run_load_prices not defined in src/quant/data/pipeline.py")
        self.write("src/quant/data/pipeline.py", "def run_load_prices(:\n")
        p, repo = self.pipeline("PL-01")
        self.assertEqual(code.pipeline_drift(repo, p), "cannot parse src/quant/data/pipeline.py")
        self.assertIsNone(code.module_docstring(self.root / "src/quant/data/pipeline.py"))
        self.assertIsNone(code.module_docstring(self.root / "src/quant/data/nope.py"))


class SourceFolderTest(FixtureCopy):
    def test_single_package_with_components(self):
        self.assertEqual(code.source_folder(Repo(QUANT), "quant"), "src/quant")

    def test_package_named_in_entry_path(self):
        self.write("docs/packages/stats/pipelines.md",
                   "# stats — Pipelines\n\n**Package:** stats · **Status:** Draft\n\n"
                   "## PL-09: X\n**Entry:** `src/quant/stats/cli/pipeline.py::run_x`\n")
        self.assertEqual(code.source_folder(Repo(self.root), "stats"), "src/quant/stats")

    def test_common_prefix_when_package_not_in_path(self):
        self.write("docs/packages/api/pipelines.md",
                   "# api — Pipelines\n\n**Package:** api · **Status:** Draft\n\n"
                   "## PL-09: X\n**Entry:** `server/app/a/pipeline.py::run_x`\n\n"
                   "## PL-10: Y\n**Entry:** `server/app/b/pipeline.py::run_y`\n")
        self.assertEqual(code.source_folder(Repo(self.root), "api"), "server/app")

    def test_fallback(self):
        self.assertEqual(code.source_folder(Repo(QUANT), "nopkg"), "src/nopkg")


if __name__ == "__main__":
    unittest.main()
