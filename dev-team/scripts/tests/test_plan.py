"""dt ready and dt plan --json on the quant fixture (interface-first M1) and the old-style plan."""
from __future__ import annotations

import json
import unittest

from dt_helpers import QUANT, FixtureCopy, run_dt


class ReadyTest(FixtureCopy):
    def ready(self):
        code, out, _ = self.dt("ready", "--json")
        self.assertEqual(code, 0)
        return json.loads(out)

    def test_after_the_interface_task(self):
        rows = self.ready()
        self.assertEqual([(r["id"], r["part"]) for r in rows],
                         [(f"M1-T{k:02d}", "task") for k in range(2, 8)] + [(f"M1-T{k}", "tester") for k in range(10, 14)])
        self.assertEqual(rows[3], {"id": "M1-T05", "title": "clean_eigen spine (no cleaning)", "kind": "spine",
                                   "writes": ["src/quant/stats/rmt.py", "tests/unit/quant/test_rmt.py"], "part": "task"})

    def test_fresh_plan(self):
        self.replace("tasks/todo.md", "- [x] M1-T01", "- [ ] M1-T01")
        self.assertEqual([r["id"] for r in self.ready()], ["M1-T01"])

    def test_wiring_waits_for_its_spines(self):
        todo = self.read("tasks/todo.md")
        self.write("tasks/todo.md", todo.replace("- [ ] M1-T02", "- [x] M1-T02").replace("- [ ] M1-T03", "- [x] M1-T03"))
        ids = [r["id"] for r in self.ready()]
        self.assertIn("M1-T08", ids)
        self.assertNotIn("M1-T09", ids)
        self.assertEqual({r["part"] for r in self.ready() if r["id"] == "M1-T10"}, {"task"})

    def test_text(self):
        code, out, _ = self.dt("ready")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], "M1-T02 [spine] read_raw spine on a synthetic CSV · writes: src/quant/data/raw.py, "
                                   "tests/unit/quant/test_raw.py")
        self.assertIn("M1-T11 [thicken, tester half] Marchenko–Pastur cleaning · writes: src/quant/stats/rmt.py, "
                      "tests/unit/quant/test_rmt.py", lines)

    def test_all_done(self):
        self.write("tasks/todo.md", self.read("tasks/todo.md").replace("- [ ]", "- [x]"))
        self.assertEqual(self.dt("ready")[:2], (0, "ready: none\n"))
        self.assertEqual(self.ready(), [])

    def test_no_active_plan(self):
        self.write("tasks/plan.md", "# Between milestones\n\n**Status:** Between milestones · **Roadmap:** x\n")
        code, out, err = self.dt("ready", "--json")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("no active plan", err)


class ReadyLegacyTest(FixtureCopy):
    legacy = True

    def test_old_plan(self):
        rows = json.loads(self.dt("ready", "--json")[1])
        self.assertEqual([(r["id"], r["kind"], r["part"]) for r in rows],
                         [("M1-T02", "", "task"), ("M1-T03", "", "task")])
        self.assertEqual(rows[1]["writes"], ["src/quant/data/steps.py", "tests/unit/quant/test_universe.py"])


class PlanSnapshotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code, out, _ = run_dt(QUANT, "plan", "--json")
        assert code == 0
        cls.snap = json.loads(out)

    def nodes(self, level):
        return [n for n in self.snap["nodes"] if n["level"] == level]

    def test_envelope(self):
        self.assertEqual(self.snap["schema"], "plan-map/1")
        self.assertRegex(self.snap["producer"], r"^dt \d+\.\d+\.\d+$")
        self.assertEqual(self.snap["levels"], ["stage", "milestone", "task", "pipeline", "step", "test", "type", "symbol"])
        self.assertNotIn("turn", self.snap)
        self.assertEqual([n["level"] for n in self.snap["nodes"]],
                         sorted((n["level"] for n in self.snap["nodes"]), key=self.snap["levels"].index))

    def test_counts(self):
        counts = {lv: len(self.nodes(lv)) for lv in self.snap["levels"]}
        self.assertEqual(counts, {"stage": 0, "milestone": 2, "task": 14, "pipeline": 3, "step": 10, "test": 3,
                                  "type": 8, "symbol": 4})

    def test_task_node(self):
        t5 = next(n for n in self.nodes("task") if n["id"] == "M1-T05")
        self.assertEqual((t5["parent"], t5["title"]), ("M1", "clean_eigen spine (no cleaning)"))
        self.assertEqual(t5["attrs"], {"kind": "spine", "size": "XS", "mode": "solo", "package": "quant",
                                       "step": "PL-02.clean_eigen", "status": "open"})
        self.assertEqual(t5["expects"]["writes"], ["src/quant/stats/rmt.py", "tests/unit/quant/test_rmt.py"])
        self.assertEqual(t5["expects"]["reads"], ["PL-02", "stats.Cov", "stats.clean_eigen"])
        self.assertRegex(t5["hash"], r"^[0-9a-f]{12}$")
        t1 = next(n for n in self.nodes("task") if n["id"] == "M1-T01")
        self.assertEqual(t1["attrs"]["status"], "done")
        t13 = next(n for n in self.nodes("task") if n["id"] == "M1-T13")
        self.assertEqual((t13["expects"]["tests"], t13["expects"]["covers"]), (["TC-03"], ["STAT-01", "QR-01"]))

    def test_other_levels(self):
        step = next(n for n in self.nodes("step") if n["id"] == "PL-02.clean_eigen")
        self.assertEqual((step["parent"], step["attrs"]["owner"], step["expects"]["in_types"]), ("PL-02", "stats", ["Cov"]))
        self.assertEqual(next(n for n in self.nodes("pipeline") if n["id"] == "PL-03")["parent"], "M2")
        cov = next(n for n in self.nodes("type") if n["id"] == "stats.Cov")
        self.assertEqual(cov["attrs"], {"package": "quant", "sample": "tests/contracts/stats.Cov/"})
        self.assertEqual(next(n for n in self.nodes("test") if n["id"] == "TC-02")["parent"], "PL-02")

    def test_edges(self):
        edges = self.snap["edges"]
        kinds = {e["kind"] for e in edges}
        self.assertEqual(kinds, {"depends", "implements", "verifies", "data", "call", "code", "file", "order"})
        self.assertIn({"from": "M1-T05", "to": "M1-T01", "kind": "depends"}, edges)
        self.assertIn({"from": "M1-T05", "to": "PL-02.clean_eigen", "kind": "implements"}, edges)
        self.assertIn({"from": "M1-T09", "to": "PL-02", "kind": "implements"}, edges)
        self.assertIn({"from": "TC-01", "to": "PL-01", "kind": "verifies"}, edges)
        self.assertIn({"from": "M1-T05", "to": "M1-T04", "kind": "data", "mitigated_by": "stats.Cov sample (M1-T01)",
                       "reason": ""}, edges)
        self.assertIn({"from": "M1-T11", "to": "M1-T05", "kind": "code", "mitigated_by": "",
                       "reason": "thickens the same module"}, edges)

    def test_builds(self):
        (b,) = self.snap["builds"]
        self.assertEqual((b["milestone"], b["state"], b["tasks"], b["width"], b["parallelism"]), ("M1", "active", 14, 6, 3.5))
        self.assertEqual(len(b["critical_path"]), 4)
        self.assertEqual(b["waves"][0], ["M1-T01"])
        self.assertEqual(b["waves"][-1], ["M1-T14"])

    def test_text(self):
        code, out, _ = run_dt(QUANT, "plan")
        self.assertEqual(code, 0)
        self.assertIn("M1 (active): 14 tasks · critical path 4", out)
        self.assertIn("  wave 1: M1-T02, M1-T03, M1-T04, M1-T05, M1-T06, M1-T07\n", out)


class PlanSnapshotCopyTest(FixtureCopy):
    def test_queued_plan_gets_a_build(self):
        self.write("tasks/queued/M2-portfolios.md",
                   "# M2: Classical portfolios — Plan\n\n**Milestone:** M2 · **Status:** Approved\n\n"
                   "### M2-T01: Min-variance spine\n**Package:** quant · **Step:** PL-03.min_variance · **Kind:** spine\n"
                   "**Depends on:** —\n\n### M2-T02: Wire PL-03\n**Package:** quant · **Step:** PL-03 · **Kind:** wiring\n"
                   "**Depends on:** M2-T01\n")
        snap = json.loads(self.dt("plan", "--json")[1])
        self.assertEqual([(b["milestone"], b["state"], b["critical_path"]) for b in snap["builds"]][1],
                         ("M2", "queued", ["M2-T01", "M2-T02"]))
        self.assertEqual(next(n for n in snap["nodes"] if n["id"] == "M2-T01")["parent"], "M2")

    def test_hash_changes_with_the_task(self):
        before = {n["id"]: n["hash"] for n in json.loads(self.dt("plan", "--json")[1])["nodes"]}
        self.replace("tasks/todo.md", "- [ ] M1-T05", "- [x] M1-T05")
        after = {n["id"]: n["hash"] for n in json.loads(self.dt("plan", "--json")[1])["nodes"]}
        self.assertEqual({k for k in before if before[k] != after[k]}, {"M1-T05"})

    def test_no_plan(self):
        (self.root / "tasks/plan.md").unlink()
        snap = json.loads(self.dt("plan", "--json")[1])
        self.assertEqual((snap["builds"], [n for n in snap["nodes"] if n["level"] == "task"]), ([], []))


class PlanSnapshotLegacyTest(FixtureCopy):
    legacy = True

    def test_old_plan(self):
        snap = json.loads(self.dt("plan", "--json")[1])
        tasks = [n for n in snap["nodes"] if n["level"] == "task"]
        self.assertEqual(len(tasks), 6)
        self.assertEqual({t["attrs"]["kind"] for t in tasks}, {""})
        self.assertNotIn("data", {e["kind"] for e in snap["edges"]})
        self.assertEqual(snap["builds"][0]["critical_path"], ["M1-T01", "M1-T02", "M1-T04", "M1-T05"])


if __name__ == "__main__":
    unittest.main()
