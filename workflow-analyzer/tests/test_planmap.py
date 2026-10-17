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
