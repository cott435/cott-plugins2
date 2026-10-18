"""planmap.py on the sample plan (`fixtures/plan.json`, design §5.3's quant M1) and on the
shapes an older or partial producer writes.

Run: python3 workflow-analyzer/tests/test_planmap.py
"""

from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import planmap  # noqa: E402

TMP = tempfile.TemporaryDirectory(prefix="planmap-")  # removed when the tests exit
SAMPLE = json.loads((HERE / "fixtures" / "plan.json").read_text(encoding="utf-8"))
VOID = {"meta", "br", "input", "img", "hr", "link", "col", "path", "rect", "line", "circle", "polygon"}


class Balance(HTMLParser):
    """Every non-void tag closes in order."""

    def __init__(self):
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"</{tag}> closes {self.stack[-1] if self.stack else 'nothing'}")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
            return
        self.stack.pop()


def render(doc: dict | str | None, index: dict | None = None) -> tuple[Path, Path | None]:
    out = Path(tempfile.mkdtemp(dir=TMP.name))
    if doc is not None:
        (out / "plan.json").write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
    if index is not None:
        (out / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return out, planmap.write(out)


def pages(out: Path) -> dict[str, str]:
    return {f.name: f.read_text(encoding="utf-8") for f in sorted((out / "plan").glob("*.html"))}


class Sample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, cls.index = render(SAMPLE)
        cls.pages = pages(cls.out)
        cls.plan = planmap.load(cls.out)

    def test_every_page_is_written(self):
        self.assertEqual(self.index, self.out / "plan" / "index.html")
        changed = [s["turn"] for s in SAMPLE["snapshots"] if s["turn"] not in (2, 7, 13, 14)]
        want = {"index.html", "M1.html", *(f"T{n:02d}.html" for n in changed)}
        self.assertEqual(set(self.pages), want)

    def test_pages_are_static_and_balanced(self):
        for name, text in self.pages.items():
            self.assertNotIn("<script", text, name)
            self.assertIn('prefers-color-scheme:dark', text, name)
            p = Balance()
            p.feed(text)
            self.assertEqual(p.errors, [], name)
            self.assertEqual(p.stack, [], name)

    def test_links_resolve(self):
        for name, text in self.pages.items():
            for href in re.findall(r'href="([^"#]+)', text):
                if href.startswith("../"):
                    continue  # the run's pages: absent here
                self.assertTrue((self.out / "plan" / href).exists(), f"{name} → {href}")

    def test_diffs(self):
        by = {s.turn: s for s in self.plan.snaps}
        self.assertEqual(by[2].kind, "status")
        self.assertEqual(by[7].kind, "same")
        self.assertEqual(by[10].removed, ["M1-T15"])
        self.assertEqual({c[0] for c in by[10].changed["M1-T11"]}, {"depends", "order", "data"})
        self.assertEqual([c[0] for c in by[8].changed["stats.Cov"]], ["fields"])
        self.assertEqual(by[13].status["M1-T01"], ("Todo", "Done"))

    def test_m1_is_the_interface_first_graph(self):
        g = planmap.Graph(planmap.last_with_tasks(self.plan, "M1"), "M1")
        m = g.metrics()
        self.assertEqual((m["tasks"], m["cp"], m["waves"], m["width"]), (14, 4, 4, [1, 10, 6, 1]))
        self.assertEqual(g.cp, ["M1-T01", "M1-T05", "M1-T11", "M1-T14"])
        self.assertAlmostEqual(m["parallelism"], 3.5)
        self.assertEqual((m["mitigated"], m["edges"]), (6, 11))
        self.assertIn("Recomputed here from <code>depends</code> edges: the same.", self.pages["M1.html"])

    def test_status_only_changes_are_hidden_by_default(self):
        idx = self.pages["index.html"]
        self.assertRegex(idx, r'class="chip sts st"[^>]*>M1-T01 Todo→Done')
        self.assertIn(".chip.st{display:none}", idx)

    def test_turn_link_and_section(self):
        self.assertIn("plan/index.html", planmap.section(self.out))
        self.assertIn("../plan/T06.html", planmap.turn_link(self.out, 7))
        self.assertIn("this turn changed the plan", planmap.turn_link(self.out, 6))
        self.assertEqual(planmap.turn_link(self.out, 0), "")


class OlderProducers(unittest.TestCase):
    def test_no_levels_hashes_builds_or_kinds(self):
        doc = copy.deepcopy(SAMPLE)
        doc.pop("levels")
        doc["schema"] = "plan-map/0"
        for s in doc["snapshots"]:
            s.pop("builds", None)
            for n in s.get("nodes", []):
                n.pop("hash", None)
                n.get("attrs", {}).pop("kind", None)
        out, index = render(doc)
        self.assertIsNotNone(index)
        m1 = (out / "plan" / "M1.html").read_text(encoding="utf-8")
        self.assertIn("(no kind)", m1)
        self.assertIn("each tester half waits on everything", m1)
        self.assertIn("plan-map/0", (out / "plan" / "index.html").read_text(encoding="utf-8"))
        # without kinds the testers wait on everything: critical path T01 → spine → tester → impl → T14
        g = planmap.Graph(planmap.last_with_tasks(planmap.load(out), "M1"), "M1")
        self.assertEqual(g.metrics()["waves"], 5)

    def test_tasks_without_milestone_nodes(self):
        doc = copy.deepcopy(SAMPLE)
        for s in doc["snapshots"]:
            if "nodes" in s:
                s["nodes"] = [n for n in s["nodes"] if n["level"] == "task"]
        out, index = render(doc)
        self.assertTrue((out / "plan" / "M1.html").exists())

    def test_same_as_a_missing_turn(self):
        doc = copy.deepcopy(SAMPLE)
        doc["snapshots"].append({"turn": 20, "same_as": 99})
        out, index = render(doc)
        self.assertIn("T20 is same_as T99", (out / "plan" / "index.html").read_text(encoding="utf-8"))

    def test_a_cycle_is_drawn_and_named(self):
        doc = copy.deepcopy(SAMPLE)
        last = [s for s in doc["snapshots"] if "nodes" in s][-1]
        last["edges"].append({"from": "M1-T01", "to": "M1-T14", "kind": "depends"})
        out, _ = render(doc)
        self.assertIn("Cycle in depends", (out / "plan" / "M1.html").read_text(encoding="utf-8"))

    def test_nothing_to_draw(self):
        self.assertIsNone(render(None)[1])
        self.assertIsNone(render("{not json")[1])
        self.assertIsNone(render({"schema": "plan-map/1"})[1])
        self.assertIsNone(render({"schema": "plan-map/1", "snapshots": []})[1])


class TesterAfterInterface(unittest.TestCase):
    """Iteration 7's R1, R2, R4 and R5 on `fixtures/plan-tester-after-interface.json`: split tasks
    whose only dependency is a spine (T04) or nothing (T05) once had testers drawn in W0."""

    @classmethod
    def setUpClass(cls):
        doc = json.loads((HERE / "fixtures" / "plan-tester-after-interface.json").read_text(encoding="utf-8"))
        cls.out, _ = render(doc)
        cls.g = planmap.Graph(planmap.last_with_tasks(planmap.load(cls.out), "M1"), "M1")
        cls.page = (cls.out / "plan" / "M1.html").read_text(encoding="utf-8")

    def test_no_tester_starts_beside_the_interface(self):
        self.assertEqual(self.g.waves[0], [("M1-T01", ""), ("M1-T02", "")])
        self.assertEqual(self.g.preds[("M1-T04", "test")], [("M1-T01", "")])  # through the T03 spine
        self.assertEqual(self.g.preds[("M1-T05", "test")], [("M1-T01", ""), ("M1-T02", "")])  # no deps: all of them
        self.assertEqual(self.g.preds[("M1-T06", "test")], [("M1-T02", "")])  # its own direct interface
        self.assertEqual(self.g.metrics()["width"], [2, 4, 3, 1])

    def test_an_interface_chain_keeps_only_its_last(self):
        doc = json.loads((HERE / "fixtures" / "plan-tester-after-interface.json").read_text(encoding="utf-8"))
        doc["snapshots"][0]["edges"].append({"from": "M1-T02", "to": "M1-T01", "kind": "depends"})
        out, _ = render(doc)
        g = planmap.Graph(planmap.last_with_tasks(planmap.load(out), "M1"), "M1")
        self.assertEqual(g.tester_waits_on("M1-T05"), ["M1-T02"])
        self.assertEqual(g.tester_waits_on("M1-T04"), ["M1-T01"])

    def test_mitigated_counts_data_and_call_edges_and_classes_the_rest(self):
        m = self.g.metrics()
        self.assertEqual((m["dc_mitigated"], m["dc"], m["mitigated"], m["edges"]), (1, 2, 1, 6))
        self.assertEqual(m["unmitigated"], {"integration": 2, "same module": 1, "across steps": 1,
                                            "data or call, not mitigated": 1})
        self.assertIn("data and call edges mitigated", self.page)
        self.assertIn("integration 2", self.page)
        self.assertIn("<th>Why it stays</th>", self.page)

    def test_the_wave_tile_names_its_unit(self):
        self.assertIn("waves of boxes (tester and implementer apart)", self.page)
        self.assertIn("whole tasks: 4", self.page)

    def test_box_titles_wrap(self):
        self.assertEqual(planmap.wrap2("Price-row flag checks on every symbol", 22),
                         ("Price-row flag checks", "on every symbol"))
        self.assertIn(">Price-row flag checks</tspan>", self.page)
        self.assertIn('class="ntl">on every symbol</text>', self.page)
        self.assertEqual(planmap.wrap2("Bulk download"), ("Bulk download", ""))


def n(id_: str, level: str, parent: str | None = None, title: str = "", attrs: dict | None = None) -> dict:
    return {"id": id_, "level": level, "parent": parent, "title": title or id_, "attrs": attrs or {}, "expects": {}}


def traced() -> dict:
    """A plan-map/2 plan: goals at T01, then the whole chain from goals to tasks at T02."""
    goals = [n("G1", "goal", title="Trust the data"), n("G2", "goal", title="Honest risk"),
             n("G3", "goal", title="A goal no feature serves")]
    rest = [n("S1", "stage", title="Data"), n("S2", "stage", title="Risk"),
            n("DATA", "feature", "S1", "Prices", {"stages": ["S1"], "stage_via": "spec heading"}),
            n("STAT", "feature", "S2", "Statistics", {"stages": ["S2"], "stage_via": "stage source"}),
            n("PORT", "feature", None, "Portfolios", {"stages": ["S1", "S2"], "stage_via": "milestone pipelines"}),
            n("DATA-01", "requirement", "DATA"), n("DATA-02", "requirement", "DATA"),
            n("STAT-01", "requirement", "STAT"), n("PORT-01", "requirement", "PORT"),
            n("QR-01", "requirement", None, attrs={"section": "Quality"}),
            n("M1", "milestone", "S1", "Data", {"pipelines": ["PL-01"]}), n("M2", "milestone", "S2", "Nothing yet"),
            n("M1-T01", "task", "M1", "load spine", {"kind": "spine"}),
            n("PL-01", "pipeline", "M1", "Load"), n("PL-01.load", "step", "PL-01"), n("PL-02", "pipeline", None, "Risk"),
            n("TC-01", "test", "PL-01")]
    edges = [{"from": a, "to": b, "kind": k} for a, b, k in [
        ("DATA", "G1", "serves"), ("STAT", "G1", "serves"), ("STAT", "G2", "serves"), ("PORT", "G2", "serves"),
        ("PL-01.load", "DATA-01", "covers"), ("PL-01", "DATA-02", "covers"), ("TC-01", "DATA-01", "covers"),
        ("M1-T01", "DATA-01", "covers"), ("PL-02", "STAT-01", "covers"), ("PL-02", "PORT-01", "covers"),
        ("TC-01", "PL-01", "verifies")]]
    return {"schema": "plan-map/2", "producer": "test", "levels": planmap.LEVELS, "snapshots": [
        {"turn": 1, "skill": "idea-refine", "nodes": goals, "edges": []},
        {"turn": 2, "skill": "build-planning", "nodes": goals + rest, "edges": edges}]}


class GoalsToBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, _ = render(traced())
        cls.pages = pages(cls.out)
        cls.trace = cls.pages["trace.html"]
        cls.t = planmap.Trace(planmap.load(cls.out).final)

    def test_pages_are_static_balanced_and_linked(self):
        self.assertEqual(set(self.pages), {"index.html", "trace.html", "M1.html", "T01.html", "T02.html"})
        for name, text in self.pages.items():
            self.assertNotIn("<script", text, name)
            p = Balance()
            p.feed(text)
            self.assertEqual((p.errors, p.stack), ([], []), name)
            for href in re.findall(r'href="([^"#]+)', text):
                self.assertTrue(href.startswith("../") or (self.out / "plan" / href).exists(), f"{name} → {href}")
        self.assertIn('href="trace.html"', self.pages["index.html"])
        self.assertNotIn("is not plan-map", self.pages["index.html"])
        self.assertIn("plan/trace.html", planmap.section(self.out))

    def test_coverage(self):
        c = self.t.cov["DATA-01"]
        self.assertEqual((c["pipeline"], c["step"], c["test"], c["task"]), ({"PL-01"}, {"PL-01.load"}, {"TC-01"}, {"M1-T01"}))
        data = self.t.freqs["DATA"]
        self.assertEqual([self.t.covered(data, k) for k in planmap.COVER], [2, 1, 1])
        self.assertEqual(self.t.feature_ms(data), ["M1"])
        self.assertEqual(self.t.cov["QR-01"]["pipeline"], set())

    def test_gaps_are_named(self):
        self.assertRegex(self.trace, r'G3</a></td><td>A goal no feature serves</td><td class="bad">none')
        self.assertIn("Features with no single stage", self.trace)
        self.assertIn("PORT: covered by pipelines of S1, S2", self.trace)
        self.assertIn("Requirements outside any feature", self.trace)

    def test_unlinked_boxes_stay_on_the_page(self):
        h = float(re.search(r'<svg class="mg tr"[^>]*height="([\d.]+)"', self.trace).group(1))
        self.assertLess(h, 1000)

    def test_turn_page_links_both_ways(self):
        t2 = self.pages["T02.html"]
        row = re.search(r'id="n-DATA-01".*?</details>|id="n-DATA-01".*?</div>', t2, re.S).group(0)
        self.assertRegex(row, r"covered by</td><td>.*M1-T01.*PL-01.*PL-01\.load.*TC-01")
        self.assertRegex(t2, r'id="n-STAT".*?<td>serves</td><td><a href="#n-G1">G1</a>, <a href="#n-G2">G2</a>')
        self.assertRegex(t2, r'id="n-G1".*?served by</td><td><a href="#n-DATA">DATA</a>, <a href="#n-STAT">STAT</a>')


def tied_lanes() -> dict:
    """Iteration 8's R6, R7, R8 and F1 in one milestone: two lanes of five tie for the critical path,
    T03 and T04 interchangeable in the first; each lane ends in two wiring tasks that write one
    pipeline.py; T12 is a split task behind a spine, so its tester shares a wave with T11."""
    tasks = [("T01", "interface", "", [], []), ("T02", "interface", "", [], []),
             ("T03", "thicken", "split", ["T01"], ["a/x.py"]), ("T04", "thicken", "split", ["T01"], ["a/y.py"]),
             ("T05", "thicken", "split", ["T02"], ["b/x.py"]),
             ("T06", "wiring", "", ["T03", "T04"], ["a/pipeline.py", "tests/test_t06.py"]),
             ("T07", "wiring", "", ["T06"], ["a/pipeline.py", "a/__main__.py"]),
             ("T08", "wiring", "", ["T05"], ["b/pipeline.py"]), ("T09", "wiring", "", ["T08"], ["b/pipeline.py"]),
             ("T10", "system", "", ["T07", "T09"], ["b/pipeline.py"]),
             ("T11", "spine", "", ["T01"], ["c/z.py"]), ("T12", "thicken", "split", ["T11"], ["c/w.py"])]
    nodes = [n("M1", "milestone", None, "Tied")]
    edges = []
    for tid, kind, mode, deps, writes in tasks:
        node = n(f"M1-{tid}", "task", "M1", f"task {tid}", {"kind": kind, "mode": mode or "solo"})
        node["expects"] = {"writes": writes}
        nodes.append(node)
        edges += [{"from": f"M1-{tid}", "to": f"M1-{d}", "kind": "depends"} for d in deps]
    edges += [{"from": f"M1-{a}", "to": f"M1-{b}", "kind": k, "reason": r} for a, b, k, r in [
        ("T07", "T06", "file", "both write a/pipeline.py"), ("T06", "T03", "order", "integration: the smoke runs it"),
        ("T03", "T04", "order", "the fixture T04 writes"), ("T08", "T05", "order", "")]]
    return {"schema": "plan-map/2", "producer": "test", "snapshots": [
        {"turn": 1, "skill": "build-planning", "nodes": nodes, "edges": edges}]}


class TiedLanes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, _ = render(tied_lanes())
        cls.g = planmap.Graph(planmap.load(cls.out).final, "M1")
        cls.page = (cls.out / "plan" / "M1.html").read_text(encoding="utf-8")

    def test_file_and_integration_come_before_order(self):
        self.assertEqual(self.g.metrics()["unmitigated"], {"integration": 1, "shared file": 1,
                                                           "side-effect order": 1, "order, no reason": 1})

    def test_every_tied_lane_is_drawn(self):
        lanes = [[[planmap.short(t, "M1") for t in alt] for alt in lane] for lane in self.g.cp_lanes]
        self.assertEqual(lanes, [[["T01"], ["T03", "T04"], ["T06"], ["T07"], ["T10"]],
                                 [["T02"], ["T05"], ["T08"], ["T09"], ["T10"]]])
        self.assertEqual(self.g.cp_paths, 3)
        self.assertEqual(self.g.cp, ["M1-T01", "M1-T03", "M1-T06", "M1-T07", "M1-T10"])
        bold = {k[0] for k in self.g.cp_segments}
        self.assertEqual(bold, {f"M1-T{i:02d}" for i in range(1, 11)})
        self.assertIn("critical paths (2 lanes tie) T01 → (T03 | T04) → T06 → T07 → T10; "
                      "T02 → T05 → T08 → T09 → T10", self.page)
        self.assertIn("2 lanes tie", self.page)
        self.assertEqual(len(re.findall(r'<path [^>]*class="e cp', self.page)), len(self.g.cp_pairs))

    def test_the_widest_wave_counts_boxes_and_whole_tasks(self):
        m = self.g.metrics()
        self.assertEqual((m["widest"], m["widest_tasks"]), (5, 4))
        self.assertIn("5 boxes<i>(4 whole tasks)</i>", self.page)

    def test_shared_entry_edges_are_marked(self):
        self.assertEqual(self.g.entry_pairs, {("M1-T07", "M1-T06"): ["a/pipeline.py"],
                                              ("M1-T09", "M1-T08"): ["b/pipeline.py"]})
        self.assertEqual(self.page.count(">entry</text>"), 2)
        self.assertIn("2 wiring → wiring edges through a shared entry module, 2 on the critical path", self.page)
        self.assertIn("shared file · shared entry module", self.page)


class WithARun(unittest.TestCase):
    def test_axis_and_skills_come_from_the_run(self):
        index = {"title": "a run", "project": "/p", "turns": [
            {"turn": f"T{n:02d}", "n": n, "skills": ["dev-team:spec-writing"] if n == 2 else []} for n in range(1, 17)]}
        out, _ = render(SAMPLE, index)
        idx = (out / "plan" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Plan map · a run", idx)
        self.assertIn(">T16</text>", idx)


if __name__ == "__main__":
    unittest.main()
