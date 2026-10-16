"""Parser tests on the sample project in fixtures/quant. Run: python3 -m unittest discover -s scripts/tests"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from devteam import md, model  # noqa: E402
from devteam.repo import Doc, Repo  # noqa: E402

QUANT = HERE / "fixtures" / "quant"


class MdTest(unittest.TestCase):
    def test_header_on_line_2_or_3(self):
        for text in ("# T\n**Status:** Draft · **Package:** stats\n", "# T\n\n**Status:** Draft · **Package:** stats\n"):
            fields, line, title, _ = md.header(text.splitlines())
            self.assertEqual(fields, {"Status": "Draft", "Package": "stats"})
            self.assertEqual(title, "T")

    def test_unknown_header_keys_kept(self):
        fields, *_ = md.header(["# T", "**Status:** Approved · **Owner:** me"])
        self.assertEqual(fields["Owner"], "me")

    def test_headings_inside_fences_ignored(self):
        lines = ["# T", "```markdown", "## PL-09: Not real", "```", "## PL-01: Real", "text"]
        hs = md.headings(lines)
        self.assertEqual([h.id for h in hs if h.id], ["PL-01"])

    def test_section_runs_to_next_same_or_higher_heading(self):
        lines = ["# T", "## PL-01: A", "x", "### Entry sketch", "y", "## PL-02: B", "z"]
        h = [h for h in md.headings(lines) if h.id == "PL-01"][0]
        self.assertEqual((h.line, h.end), (1, 5))

    def test_id_forms(self):
        for text, id_ in [("M2-T03: x", "M2-T03"), ("M2: x", "M2"), ("M2-R01: x", "M2-R01"),
                          ("stats.estimate_cov: x", "stats.estimate_cov"), ("TC-06: x", "TC-06"),
                          ("CR-01: x", "CR-01"), ("AD-12: x", "AD-12")]:
            self.assertEqual(md.headings(["## " + text])[0].id, id_)
        self.assertIsNone(md.headings(["## Phase 0: Spine"])[0].id)
        self.assertIsNone(md.headings(["### Checkpoint after M2-T04"])[0].id)

    def test_ranges_expand(self):
        self.assertEqual(md.expand_refs("STAT-01–STAT-03, QR-02"), ["STAT-01", "STAT-02", "STAT-03", "QR-02"])
        self.assertEqual(md.expand_refs("ENV-01–03"), ["ENV-01", "ENV-02", "ENV-03"])

    def test_fields(self):
        f = md.split_fields("**Package:** stats · **Step:** PL-02.estimate_cov · **Size:** S")
        self.assertEqual(f, {"Package": "stats", "Step": "PL-02.estimate_cov", "Size": "S"})

    def test_retired_line(self):
        lines = ["- ~~PL-01: Raw eigen dump~~ Retired 2026-11-02: folded into PL-02 (AD-09)"]
        r = md.retired_lines(lines, md.code_mask(lines))[0]
        self.assertEqual((r.id, r.title, r.date), ("PL-01", "Raw eigen dump", "2026-11-02"))


class RepoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Repo(QUANT)

    def test_doc_kinds(self):
        kinds = {d.rel: d.kind for d in self.repo.docs()}
        self.assertEqual(kinds["docs/packages/quant/pipelines.md"], "pipelines")
        self.assertEqual(kinds["tasks/plan.md"], "plan")
        self.assertEqual(kinds["CONSTRAINTS.md"], "constraints")
        self.assertEqual(self.repo.packages(), ["quant"])

    def test_no_duplicate_live_ids(self):
        dups = {k: v for k, v in self.repo.index.items() if len([d for d in v if not d.retired]) > 1}
        self.assertEqual(dups, {})

    def test_lookup_kinds(self):
        self.assertEqual(self.repo.lookup("PL-02").doc.kind, "pipelines")
        self.assertEqual(self.repo.lookup("STAT-02").how, "requirement")
        self.assertEqual(self.repo.lookup("stats.estimate_cov").doc.kind, "contract")
        self.assertEqual(self.repo.lookup("CR-21").how, "table")
        self.assertEqual(self.repo.lookup("M1").doc.kind, "roadmap")
        self.assertEqual(self.repo.lookup("M1-T03").doc.kind, "plan")

    def test_retired(self):
        self.assertTrue(self.repo.is_retired("PL-04"))
        self.assertTrue(self.repo.is_retired("AD-02"))
        self.assertTrue(self.repo.is_retired("DATA-03"))
        self.assertFalse(self.repo.is_retired("PL-02"))

    def test_section_text_stops_at_next_pipeline(self):
        text = self.repo.lookup("PL-02").text
        self.assertIn("Entry sketch (pre-build", text)
        self.assertNotIn("## PL-03", text)

    def test_next_id_counts_retired(self):
        self.assertEqual(self.repo.next_id("PL"), "PL-05")
        self.assertEqual(self.repo.next_id("AD"), "AD-04")
        self.assertEqual(self.repo.next_id("TC"), "TC-04")
        self.assertEqual(self.repo.next_id("DATA"), "DATA-04")
        self.assertEqual(self.repo.next_id("M"), "M3")
        self.assertEqual(self.repo.next_id("M1-T"), "M1-T07")


class ModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Repo(QUANT)

    def test_tasks(self):
        ts = model.tasks(self.repo.plan)
        self.assertEqual([t.id for t in ts], [f"M1-T0{i}" for i in range(1, 7)])
        t3 = ts[2]
        self.assertEqual((t3.package, t3.step, t3.size, t3.mode), ("quant", "PL-01.apply_universe", "S", "split"))
        self.assertEqual(t3.read, ["PL-01", "TC-01", "DATA-02", "data.load_prices"])
        self.assertEqual(t3.depends_on, ["M1-T01"])
        self.assertEqual(t3.parallel, "G1")
        self.assertEqual(len(t3.acceptance), 2)
        self.assertTrue(ts[0].is_spine)
        self.assertFalse(t3.is_spine)
        self.assertEqual(ts[0].depends_on, [])
        self.assertIn("python -m quant.data load --smoke", t3.verify)
        self.assertEqual(ts[3].skills, ["data-science"])
        self.assertEqual(t3.skills, [])

    def test_checkpoints(self):
        cps = model.checkpoints(self.repo.plan)
        self.assertEqual([c.after for c in cps], ["M1-T04", ""])
        self.assertEqual(len(cps[0].items), 7)

    def test_findings(self):
        doc = Doc(QUANT, "tasks/plan.md", "# M1: X — Plan\n**Milestone:** M1\n## Phase 1: T\n"
                  "### Checkpoint after M1-T02 — reviewed 2026-11-03\n- [x] ok\n**Findings:**\n"
                  "- M1-R01 Critical · CR-21 · `rmt.py` complexity 14 → fix task M1-T09\n"
                  "- M1-R02 Nit · naming\n")
        f = model.checkpoints(doc)[0].findings
        self.assertEqual([(x.id, x.severity, x.disposition) for x in f],
                         [("M1-R01", "Critical", "fix task M1-T09"), ("M1-R02", "Nit", "")])

    def test_todo(self):
        items = model.todo_items(self.repo.todo)
        self.assertEqual(len(items), 6)
        self.assertTrue(items[0].checked)
        self.assertEqual(model.milestone_of(self.repo.plan), "M1")
        self.assertTrue(model.is_dev_team_plan(self.repo.plan))

    def test_pipelines(self):
        pls = {p.id: p for p in model.all_pipelines(self.repo)}
        self.assertEqual(sorted(pls), ["PL-01", "PL-02", "PL-03"])
        p2 = pls["PL-02"]
        self.assertEqual(p2.entry_file, "src/quant/stats/pipeline.py")
        self.assertEqual(p2.entry_function, "run_cov_report")
        self.assertEqual([s.name for s in p2.steps], ["load_prices", "estimate_cov", "clean_eigen", "pca", "write_report"])
        self.assertEqual(p2.steps[2].owner, "stats")
        self.assertEqual(p2.covers, ["STAT-01", "STAT-02", "STAT-03", "STAT-04", "QR-02"])
        self.assertEqual([h.text for h in self.repo.package_doc("quant", "pipelines").prebuild_sections()],
                         ["Entry sketch (pre-build — removed by spine task)",
                          "Planned layout (pre-build — removed by spine task)"])

    def test_test_cases(self):
        doc = self.repo.package_doc("quant", "tests")
        tcs = model.test_cases(doc)
        self.assertEqual([t.id for t in tcs], ["TC-01", "TC-02", "TC-03"])
        self.assertEqual(tcs[1].pipeline, "PL-02")
        self.assertEqual(tcs[1].fixture, "tests/fixtures/quant/TC-02/")
        self.assertEqual([r["Pipeline"] for r in model.strategy_rows(doc)], ["PL-01", "PL-02"])

    def test_roadmap(self):
        ms = model.milestones(self.repo.roadmap)
        self.assertEqual([m.id for m in ms], ["M1", "M2"])
        self.assertEqual(ms[0].pipelines, ["PL-01", "PL-02"])
        self.assertEqual(ms[1].depends, ["M1"])
        self.assertIn("Exit", ms[0].fields)

    def test_contract_and_components(self):
        syms = model.symbols(self.repo.package_doc("quant", "contract"))
        self.assertEqual([s.id for s in syms], ["data.load_prices", "stats.estimate_cov", "stats.clean_eigen",
                                                "portfolio.min_variance"])
        comps = {c.id: c for c in model.components(self.repo.architecture)}
        self.assertEqual(sorted(comps), ["data", "portfolio", "stats"])
        self.assertEqual(comps["portfolio"].depends_on, ["stats", "data"])
        self.assertEqual(comps["data"].depends_on, [])


if __name__ == "__main__":
    unittest.main()
