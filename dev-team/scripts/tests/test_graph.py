"""devteam.graph on hand-built plans: waves, width, critical path, the ready set and tester halves."""
from __future__ import annotations

import unittest

from dt_helpers import QUANT  # noqa: F401  (puts scripts/ on sys.path)

from devteam import graph, model  # noqa: E402
from devteam.repo import Doc  # noqa: E402


def plan(*tasks: tuple) -> list[model.Task]:
    """Tasks from (id, depends, size, kind, mode) tuples, in plan order; trailing fields may be left out."""
    text = "# M1: Hand — Plan\n\n**Milestone:** M1 · **Status:** Approved\n\n"
    for t in tasks:
        tid, deps, size, kind, mode = (list(t) + ["S", "", "solo"][len(t) - 2:])[:5]
        kind_field = f" · **Kind:** {kind}" if kind else ""
        text += (f"### {tid}: Task {tid}\n**Package:** p · **Step:** PL-01{kind_field} · **Size:** {size} · "
                 f"**Mode:** {mode}\n**Depends on:** {', '.join(deps) or '—'}\n\n")
    return model.tasks(Doc(QUANT, "tasks/plan.md", text))


class WavesTest(unittest.TestCase):
    def test_diamond(self):
        ts = plan(("M1-T01", []), ("M1-T02", ["M1-T01"]), ("M1-T03", ["M1-T01"]), ("M1-T04", ["M1-T02", "M1-T03"]))
        self.assertEqual(graph.waves(ts), [["M1-T01"], ["M1-T02", "M1-T03"], ["M1-T04"]])
        self.assertEqual(graph.width(ts), 2)
        self.assertEqual(len(graph.critical_path(ts)), 3)
        self.assertEqual(graph.parallelism(ts), 1.33)

    def test_wave_is_one_past_the_deepest_dependency(self):
        ts = plan(("M1-T01", []), ("M1-T02", ["M1-T01"]), ("M1-T03", ["M1-T02"]), ("M1-T04", ["M1-T01", "M1-T03"]))
        self.assertEqual(graph.waves(ts), [["M1-T01"], ["M1-T02"], ["M1-T03"], ["M1-T04"]])
        self.assertEqual(graph.width(ts), 1)
        self.assertEqual(graph.serial_warning(ts),
                         "4 of 4 waves have width 1: freeze interfaces so more tasks can start at once")

    def test_independent_tasks_share_wave_zero(self):
        ts = plan(("M1-T01", []), ("M1-T02", []), ("M1-T03", []))
        self.assertEqual(graph.waves(ts), [["M1-T01", "M1-T02", "M1-T03"]])
        self.assertEqual((graph.width(ts), graph.parallelism(ts), graph.serial_warning(ts)), (3, 3.0, ""))

    def test_outside_dependencies_are_ignored(self):
        # A dependency on another plan or the archive (M0-T07) doesn't order this plan.
        ts = plan(("M1-T01", ["M0-T07"]), ("M1-T02", ["M1-T01"]))
        self.assertEqual(graph.waves(ts), [["M1-T01"], ["M1-T02"]])
        self.assertEqual(graph.ready(ts, set()), ["M1-T01"])

    def test_cycle_does_not_hang(self):
        ts = plan(("M1-T01", ["M1-T02"]), ("M1-T02", ["M1-T01"]), ("M1-T03", ["M1-T03"]))
        self.assertEqual(sorted(i for w in graph.waves(ts) for i in w), ["M1-T01", "M1-T02", "M1-T03"])
        self.assertLessEqual(len(graph.critical_path(ts)), 2)
        self.assertEqual(graph.ready(ts, set()), ["M1-T03"])           # a self-dependency is ignored

    def test_empty(self):
        self.assertEqual((graph.waves([]), graph.width([]), graph.critical_path([]), graph.parallelism([])),
                         ([], 0, [], 0.0))
        self.assertEqual(graph.metrics([]), {"critical_path": [], "waves": [], "width": 0, "parallelism": 0.0})


class CriticalPathTest(unittest.TestCase):
    def test_longest_chain(self):
        ts = plan(("M1-T01", []), ("M1-T02", ["M1-T01"]), ("M1-T03", []), ("M1-T04", ["M1-T02"]), ("M1-T05", ["M1-T03"]))
        self.assertEqual(graph.critical_path(ts), ["M1-T01", "M1-T02", "M1-T04"])

    def test_tie_goes_to_the_heavier_chain(self):
        ts = plan(("M1-T01", [], "XS"), ("M1-T02", ["M1-T01"], "XS"), ("M1-T03", [], "M"), ("M1-T04", ["M1-T03"], "XS"))
        self.assertEqual(graph.critical_path(ts), ["M1-T03", "M1-T04"])

    def test_then_to_plan_order(self):
        ts = plan(("M1-T01", []), ("M1-T02", []), ("M1-T03", ["M1-T02"]), ("M1-T04", ["M1-T01"]))
        self.assertEqual(graph.critical_path(ts), ["M1-T01", "M1-T04"])

    def test_mitigated_edges_never_order(self):
        # Only Depends on orders: the quant M1 has 22 graph rows, but its critical path is four tasks.
        from devteam.repo import Repo
        ts = model.tasks(Repo(QUANT).plan)
        self.assertEqual(len(ts), 14)
        self.assertEqual(len(graph.critical_path(ts)), 4)
        self.assertEqual([len(w) for w in graph.waves(ts)], [1, 6, 6, 1])
        self.assertEqual(graph.width(ts), 6)


class ReadyTest(unittest.TestCase):
    def setUp(self):
        self.ts = plan(("M1-T01", [], "S", "interface"),
                       ("M1-T02", ["M1-T01"], "XS", "spine"), ("M1-T03", ["M1-T01"], "XS", "spine"),
                       ("M1-T04", ["M1-T02", "M1-T03"], "S", "wiring"),
                       ("M1-T05", ["M1-T02"], "S", "thicken", "split"),
                       ("M1-T06", ["M1-T03"], "S", "thicken", "solo"),
                       ("M1-T07", ["M1-T04", "M1-T05", "M1-T06"], "S", "system"))

    def test_fresh_plan_readies_only_the_interface(self):
        self.assertEqual(graph.ready(self.ts, set()), ["M1-T01"])
        self.assertEqual(graph.tester_ready(self.ts, set()), [])

    def test_after_the_interface(self):
        done = {"M1-T01"}
        self.assertEqual(graph.ready(self.ts, done), ["M1-T02", "M1-T03"])
        self.assertEqual(graph.tester_ready(self.ts, done), ["M1-T05"])    # split only; M1-T06 is solo

    def test_wiring_waits_for_every_spine(self):
        self.assertEqual(graph.ready(self.ts, {"M1-T01", "M1-T02"}), ["M1-T03", "M1-T05"])
        self.assertEqual(graph.tester_ready(self.ts, {"M1-T01", "M1-T02"}), [])   # M1-T05 is ready whole
        self.assertEqual(graph.ready(self.ts, {"M1-T01", "M1-T02", "M1-T03"}), ["M1-T04", "M1-T05", "M1-T06"])

    def test_done_tasks_are_not_ready(self):
        everything = {t.id for t in self.ts}
        self.assertEqual(graph.ready(self.ts, everything), [])
        self.assertEqual(graph.ready(self.ts, everything - {"M1-T07"}), ["M1-T07"])

    def test_no_interface_upstream_means_no_tester_half(self):
        ts = plan(("M1-T01", [], "S", "spine"), ("M1-T02", ["M1-T01"], "S", "thicken", "split"))
        self.assertEqual(graph.tester_ready(ts, set()), [])

    def test_paths(self):
        self.assertEqual(graph.ancestors(self.ts, "M1-T04"), {"M1-T01", "M1-T02", "M1-T03"})
        self.assertTrue(graph.path_between(self.ts, "M1-T07", "M1-T02"))
        self.assertTrue(graph.path_between(self.ts, "M1-T02", "M1-T07"))
        self.assertFalse(graph.path_between(self.ts, "M1-T05", "M1-T06"))


class HalvesTest(unittest.TestCase):
    """build-phase.md §6.1, §13: a split task runs tester then implementer; a tester waits only on interfaces."""

    def setUp(self):
        self.ts = plan(("M1-T01", [], "M", "interface"),
                       ("M1-T02", ["M1-T01"], "XS", "spine"),
                       ("M1-T03", ["M1-T02"], "S", "thicken", "split"),
                       ("M1-T04", ["M1-T02"], "XS", "wiring"))

    def test_half_graph(self):
        self.assertEqual(graph.roles(self.ts[2]), ["tester", "implementer"])
        self.assertEqual(graph.half_graph(self.ts), {
            "M1-T01.solo": ["M1-T02.solo", "M1-T03.tester"],
            "M1-T02.solo": ["M1-T03.implementer", "M1-T04.solo"],
            "M1-T03.tester": ["M1-T03.implementer"],
            "M1-T03.implementer": [],
            "M1-T04.solo": []})

    def test_critical_path_in_halves(self):
        self.assertEqual(graph.critical_path(self.ts), ["M1-T01", "M1-T02", "M1-T03"])
        # Two chains of three halves; the tester's is heavier (S before S, against XS before S).
        self.assertEqual(graph.critical_path_halves(self.ts), ["M1-T01.solo", "M1-T03.tester", "M1-T03.implementer"])
        ts = plan(("M1-T01", [], "S", "interface"), ("M1-T02", ["M1-T01"], "S", "thicken", "split"))
        self.assertEqual(graph.critical_path_halves(ts), ["M1-T01.solo", "M1-T02.tester", "M1-T02.implementer"])

    def test_remaining_weight(self):
        rem = graph.remaining_weight(self.ts)
        self.assertEqual((rem["M1-T01.solo"], rem["M1-T02.solo"], rem["M1-T03.tester"], rem["M1-T04.solo"]),
                         (4 + 2 + 2, 1 + 2, 2 + 2, 1))


if __name__ == "__main__":
    unittest.main()
