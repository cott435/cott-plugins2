"""Mechanical edits: dt prebuild-clear, dt archive, dt finding, and the file modes every edit keeps. Each runs
on a copy of the fixture."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dt_helpers import FixtureCopy

from devteam import edit

PIPELINES = "docs/packages/quant/pipelines.md"
SKETCH = """### Entry sketch (pre-build — removed by spine task)
```python
def run_cov_report(cfg: CovConfig) -> CovReport:
    prices = load_prices(cfg.universe, cfg.start, cfg.end)
    cov = estimate_cov(prices.returns())
    cov = clean_eigen(cov, n_obs=len(prices))
    factors = pca(cov)
    return write_report(factors, cfg.out)
```
"""


class PrebuildClearTest(FixtureCopy):
    def test_replaces_sketch_and_preserves_the_rest(self):
        before = self.read(PIPELINES)
        code, out, _ = self.dt("prebuild-clear", "PL-02")
        self.assertEqual(code, 0)
        self.assertIn("removed PL-02 entry sketch", out)
        self.assertIn("kept Planned layout (not built: PL-02, PL-03)", out)
        self.assertEqual(self.read(PIPELINES), before.replace(SKETCH, "Layout: `dt layout quant`\n"))

    def test_idempotent(self):
        self.dt("prebuild-clear", "PL-02")
        once = self.read(PIPELINES)
        code, out, _ = self.dt("prebuild-clear", "PL-02")
        self.assertEqual(code, 0)
        self.assertIn("nothing to clear", out)
        self.assertEqual(self.read(PIPELINES), once)

    def test_existing_pointer_not_duplicated(self):
        self.replace(PIPELINES, SKETCH, "Layout: `dt layout quant`\n\n" + SKETCH)
        self.dt("prebuild-clear", "PL-02")
        text = self.read(PIPELINES)
        self.assertEqual(text.count("Layout: `dt layout quant`"), 2)     # PL-01's and PL-02's
        self.assertNotIn("Entry sketch", text)
        self.assertNotIn("\n\n\n", text)

    def test_planned_layout_removed_once_every_pipeline_is_built(self):
        self.replace("tasks/todo.md", "- [ ] M1-T02", "- [x] M1-T02")
        self.write("src/quant/portfolio/pipeline.py", "def run_backtest(cfg):\n    pass\n")
        before = self.read(PIPELINES)
        code, out, _ = self.dt("prebuild-clear", "PL-02")
        self.assertEqual(code, 0)
        self.assertIn("removed Planned layout", out)
        text = self.read(PIPELINES)
        self.assertNotIn("(pre-build", text)
        self.assertIn("| 3 | `compare` | portfolio | Weights, Returns → Comparison | realized variance only | PORT-02 |\n"
                      "\n## Open questions\n", text)
        self.assertEqual(text.splitlines()[2], before.splitlines()[2])   # header (Status) untouched

    def test_crlf_kept(self):
        self.write(PIPELINES, self.read(PIPELINES).replace("\n", "\r\n"))
        self.dt("prebuild-clear", "PL-02")
        raw = (self.root / PIPELINES).read_bytes()
        self.assertIn(b"Layout: `dt layout quant`\r\n", raw)
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))

    def test_unknown_pipeline(self):
        self.assertEqual(self.dt("prebuild-clear", "PL-77")[0], 1)
        self.assertEqual(self.dt("prebuild-clear", "nope")[0], 2)


class ArchiveTest(FixtureCopy):
    def check_all(self):
        self.write("tasks/todo.md", self.read("tasks/todo.md").replace("- [ ]", "- [x]"))

    def test_refuses_with_unchecked_items(self):
        before = {p: self.read(p) for p in ("tasks/plan.md", "tasks/todo.md", "docs/roadmap.md")}
        code, out, _ = self.dt("archive")
        self.assertEqual(code, 1)
        self.assertIn("M1-T02, M1-T03", out)
        self.assertEqual({p: self.read(p) for p in before}, before)
        self.assertFalse((self.root / "tasks/archive").exists())

    def test_archives(self):
        self.check_all()
        plan, todo = self.read("tasks/plan.md"), self.read("tasks/todo.md")
        code, out, _ = self.dt("archive", "--date", "2026-11-02")
        self.assertEqual((code, out), (0, "tasks/archive/M1-data-stats.md\n"))
        archived = self.read("tasks/archive/M1-data-stats.md")
        self.assertTrue(archived.startswith(plan))
        self.assertEqual(archived[len(plan):], "\n## Todo\n\n" + todo.split("\n\n", 1)[1])

        stub = self.read("tasks/plan.md")
        self.assertEqual(stub.splitlines()[:3], [
            "# Between milestones", "",
            "**Status:** Between milestones · **Last updated:** 2026-11-02 · "
            "**Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)"])
        self.assertEqual(self.read("tasks/todo.md"), "# Todo\n")

        roadmap = self.read("docs/roadmap.md")
        self.assertIn("**Plan:** [../tasks/archive/M1-data-stats.md](../tasks/archive/M1-data-stats.md)\n"
                      "**Outcome:** Done 2026-11-02\n\n## M2", roadmap)

        # A second run refuses and leaves the stub in place.
        code, out, _ = self.dt("archive")
        self.assertEqual(code, 1)
        self.assertEqual(self.read("tasks/plan.md"), stub)
        self.assertEqual(self.dt("next-id", "M1-T")[1], "M1-T07\n")     # archive still counted

    def test_existing_outcome_kept(self):
        self.check_all()
        self.replace("docs/roadmap.md", "**Plan:** [../tasks/plan.md](../tasks/plan.md)\n",
                     "**Outcome:** Done 2026-11-01 — switched to Ledoit-Wolf\n")
        self.dt("archive", "--date", "2026-11-02")
        roadmap = self.read("docs/roadmap.md")
        self.assertEqual(roadmap.count("**Outcome:**"), 1)
        self.assertIn("Done 2026-11-01", roadmap)

    def test_refuses_to_overwrite_archive(self):
        self.check_all()
        self.write("tasks/archive/M1-data-stats.md", "# old\n")
        plan = self.read("tasks/plan.md")
        self.assertEqual(self.dt("archive")[0], 1)
        self.assertEqual(self.read("tasks/plan.md"), plan)
        self.assertEqual(self.read("tasks/archive/M1-data-stats.md"), "# old\n")


class FindingTest(FixtureCopy):
    def test_creates_findings_label_then_appends(self):
        before = self.read("tasks/plan.md")
        self.assertEqual(self.dt("finding", "M1-T04", "critical", "CR-21 · `rmt.py` complexity 14",
                                 "--disposition", "fix task M1-T09")[:2], (0, "M1-R01\n"))
        self.assertEqual(self.dt("finding", "M1-T04", "Nit", "naming")[1], "M1-R02\n")
        added = ("**Findings:**\n"
                 "- M1-R01 Critical · CR-21 · `rmt.py` complexity 14 → fix task M1-T09\n"
                 "- M1-R02 Nit · naming\n")
        anchor = "- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition\n"
        self.assertEqual(self.read("tasks/plan.md"), before.replace(anchor, anchor + added, 1))

    def test_exit_checkpoint(self):
        code, out, _ = self.dt("finding", "exit", "Suggestion", "docs", "--disposition", "won't fix: fine")
        self.assertEqual((code, out), (0, "M1-R01\n"))
        self.assertIn("**Findings:**\n- M1-R01 Suggestion · docs → won't fix: fine\n\n## Risks",
                      self.read("tasks/plan.md"))

    def test_existing_findings_counted(self):
        self.replace("tasks/plan.md", "### M1-T05", "**Findings:**\n- M1-R04 Nit · old → ok\n\n### M1-T05")
        self.assertEqual(self.dt("finding", "M1-T04", "Important", "new")[1], "M1-R05\n")
        self.assertIn("- M1-R04 Nit · old → ok\n- M1-R05 Important · new\n", self.read("tasks/plan.md"))

    def test_errors(self):
        before = self.read("tasks/plan.md")
        self.assertEqual(self.dt("finding", "M1-T04", "Major", "x")[0], 2)
        self.assertEqual(self.dt("finding", "PL-02", "Nit", "x")[0], 2)
        self.assertEqual(self.dt("finding", "M1-T02", "Nit", "x")[0], 1)
        self.assertEqual(self.read("tasks/plan.md"), before)


class FileModeTest(FixtureCopy):
    """`edit.write_text` keeps a file's permission bits (mkstemp alone leaves 0600); new files get 0644 less the
    umask."""

    def mode(self, rel: str) -> int:
        return (self.root / rel).stat().st_mode & 0o777

    def umask(self) -> int:
        old = os.umask(0)
        os.umask(old)
        return old

    def test_write_text_keeps_mode(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.md"
            path.write_text("a\n")
            path.chmod(0o664)
            edit.write_text(path, "b\n")
            self.assertEqual((path.read_text(), path.stat().st_mode & 0o777), ("b\n", 0o664))
            fresh = Path(d) / "new.md"
            edit.write_text(fresh, "c\n")
            self.assertEqual(fresh.stat().st_mode & 0o777, 0o644 & ~self.umask())
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["new.md", "x.md"])   # no temp left

    def test_mechanical_commands_keep_modes(self):
        for rel in ("tasks/todo.md", "tasks/plan.md", "docs/roadmap.md", PIPELINES):
            (self.root / rel).chmod(0o664)
        self.assertEqual(self.dt("tick", "M1-T03")[0], 0)
        self.assertEqual(self.dt("finding", "exit", "nit", "rename x")[0], 0)
        self.assertEqual(self.dt("prebuild-clear", "PL-01")[0], 0)
        self.write("tasks/todo.md", self.read("tasks/todo.md").replace("- [ ]", "- [x]"))
        (self.root / "tasks/todo.md").chmod(0o664)
        self.assertEqual(self.dt("archive", "--date", "2026-11-02")[0], 0)
        for rel in ("tasks/todo.md", "tasks/plan.md", "docs/roadmap.md", PIPELINES):
            self.assertEqual(self.mode(rel), 0o664, rel)
        self.assertEqual(self.mode("tasks/archive/M1-data-stats.md"), 0o644 & ~self.umask())
