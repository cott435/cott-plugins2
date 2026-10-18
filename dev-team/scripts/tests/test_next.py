"""dt next and dt route on copies of the quant fixture. Run: python3 -m unittest discover -s scripts/tests"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dt_helpers import FixtureCopy, run_dt

HERE = Path(__file__).resolve().parent


class NextCase(FixtureCopy):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ)
        env.start()
        os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        self.addCleanup(env.stop)

    def next(self, *args: str) -> dict:
        rc, out, _ = self.dt("next", "--json", *args)
        self.assertEqual(rc, 0)
        return json.loads(out)

    def status(self, skill: str) -> dict:
        return json.loads(self.dt("status", "--skill", skill, "--json")[1])

    def skip_tests(self) -> dict:
        return self.next("--skip", "test-planning")


class NextTest(NextCase):
    def test_empty_project_starts_with_idea_refine(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, out, _ = run_dt(Path(tmp), "next", "--json")
        self.assertEqual(json.loads(out), {"skill": "idea-refine", "mode": "new", "reason": "no brief yet",
                                           "waiting_on_user": False})

    def test_quant_fixture(self):
        # Mid-M1 with a pipeline that has no tests; without test-planning, nothing is left to plan.
        d = self.next()
        self.assertEqual((d["skill"], d["mode"], d["packages"]), ("test-planning", "extend", ["quant"]))
        d = self.skip_tests()
        self.assertEqual((d["skill"], d["mode"], d["waiting_on_user"]), (None, "done", True))
        _, text, _ = self.dt("next", "--skip", "test-planning")
        self.assertIn("next: none (done)\n", text)

    def test_text_output(self):
        self.replace("docs/spec.md", "**Status:** Approved", "**Status:** Draft")
        _, text, _ = self.dt("next")
        self.assertEqual(text, "next: spec-writing (gate)\n"
                               "reason: docs/spec.md is Draft: answer its questions or approve it\n"
                               "waiting on user: yes\nrun: /dev-team:spec-writing\n")

    def test_draft_waits_at_its_owners_gate_in_planning_order(self):
        self.replace("docs/packages/quant/pipelines.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.next()["skill"], "pipeline-design")
        self.replace("CONSTRAINTS.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.next()["skill"], "pipeline-design")
        self.replace("docs/brief.md", "**Status:** Accepted", "**Status:** Draft")
        d = self.next()
        self.assertEqual((d["skill"], d["mode"], d["waiting_on_user"]), ("idea-refine", "gate", True))

    def test_accepted_idea_goes_to_spec_writing(self):
        self.replace("docs/ideas/classical-portfolios.md", "**Status:** Specced", "**Status:** Accepted")
        d = self.skip_tests()
        self.assertEqual((d["skill"], d["mode"]), ("spec-writing", "extend"))
        self.assertIn("docs/ideas/classical-portfolios.md", d["reason"])

    def test_references_waiting(self):
        self.write("references/new_loader.py", "def load():\n    return 1\n")
        d = self.next()
        self.assertEqual((d["skill"], d["mode"]), ("reference-intake", "extend"))

    def test_uncovered_spec_id_goes_to_architecture_then_pipelines(self):
        self.replace("docs/spec.md", "### Quality", "- **PORT-03** Risk-parity weights equalize risk contributions.\n\n"
                     "### Quality")
        d = self.skip_tests()
        self.assertEqual((d["skill"], d["mode"]), ("architecture-design", "extend"))
        self.assertIn("PORT-03", d["reason"])

    def test_unowned_component_alone_is_not_work(self):
        self.replace("docs/architecture.md", "| `stats` |", "| `extra` | Unused helper | — | — |\n| `stats` |")
        self.assertEqual(self.status("pipeline-design")["mode"], "extend")
        self.assertNotEqual(self.skip_tests()["skill"], "pipeline-design")

    def test_test_planning_skipped_once_a_plan_exists_without_tests(self):
        for p in ("docs/packages/quant/tests.md",):
            (self.root / p).unlink()
        self.assertEqual(self.status("test-planning")["mode"], "new")
        self.assertIsNone(self.next()["skill"])
        (self.root / "tasks/plan.md").unlink()
        (self.root / "tasks/todo.md").unlink()
        self.assertEqual(self.next()["skill"], "test-planning")

    LAB = {"pipelines": "## PL-06: Feature screen\n**Entry:** `src/lab/pipeline.py::run_screen` · **Trigger:** "
                        "`python -m lab screen`\n**Covers:** PORT-02\n\n"
                        "| # | Step | Owner | In → Out | Spine version | Covers |\n|---|---|---|---|---|---|\n"
                        "| 1 | `screen` | screen | Returns → Screen | no screen | PORT-02 |\n",
           "architecture": "| Component | Responsibility | Covers | Depends on |\n|---|---|---|---|\n"
                           "| `screen` | Screen features | PORT-02 | — |\n",
           "contract": "## screen\n\n### screen.Screen: type\n`class Screen: ranked: list[str]`\n"}

    def add_lab(self):
        """A `lab` package (PL-06, no tests.md) on a third milestone, M3."""
        for name, body in self.LAB.items():
            self.write(f"docs/packages/lab/{name}.md", f"# lab — {name.title()}\n\n**Package:** lab · **Status:** "
                       f"Approved · **Last updated:** 2026-10-16\n\n{body}")
        self.replace("docs/roadmap.md", "| quant | PL-03 | M1 | Designed |", "| quant | PL-03 | M1 | Designed |\n"
                     "| M3 | Feature lab | ideas/classical-portfolios.md | lab | PL-06 | M2 | Designed |")
        self.write("docs/roadmap.md", self.read("docs/roadmap.md") + "\n## M3: Feature lab\n**Exit:** A screen.\n")

    def test_test_planning_covers_the_next_milestones_packages_only(self):
        # A third milestone's package with no tests.md waits until that milestone is the next one to plan.
        self.add_lab()
        self.assertEqual(self.dt("lint", "docs/")[0], 0)
        self.assertEqual(self.status("test-planning")["packages"]["lab"], "new")
        d = self.next()
        self.assertEqual((d["skill"], d["mode"], d["packages"]), ("test-planning", "extend", ["quant"]))
        self.assertIn("for M1, M2 (optional)", d["reason"])
        # M2 planned and queued: M3 is next, and its package is offered.
        self.write("tasks/queued/M2-plan.md", (self.root / "tasks/plan.md").read_text(encoding="utf-8")
                   .replace("# M1", "# M2", 1).replace("**Milestone:** M1", "**Milestone:** M2"))
        d = self.next()
        self.assertEqual((d["skill"], d["mode"]), ("test-planning", "new"))
        self.assertIn("lab", d["packages"])
        self.assertIn("for M1, M3 (optional)", d["reason"])


class AllAtOnceTest(NextCase):
    def test_stage_below_designed_goes_to_pipeline_design(self):
        (self.root / "tasks/plan.md").unlink()
        (self.root / "tasks/todo.md").unlink()
        self.write("docs/roadmap.md", "# Quant Lab — Roadmap\n\n**Last updated:** 2026-10-16\n\n"
                   "| Stage | Name | Source | Status* |\n|---|---|---|---|\n"
                   "| S1 | Data + stats | brief | Designed |\n| S2 | Classical portfolios | brief | Designed |\n\n"
                   "## S1: Data + stats\n**Outline:** PCA.\n\n## S2: Classical portfolios\n**Outline:** Min-var.\n")
        self.replace("docs/spec.md", "| ideas/classical-portfolios.md | PORT-01", "| brief.md | PORT-01")
        self.assertEqual(self.skip_tests()["skill"], "build-planning")
        # S2 adds PORT-03, which the architecture names but no component or pipeline covers: pipeline-design reports
        # nothing to do, and build-planning's block sends the run there.
        self.replace("docs/spec.md", "### Quality", "- **PORT-03** Risk-parity weights equalize risk contributions.\n\n"
                     "### Quality")
        self.replace("docs/spec.md", "| PORT-01, PORT-02; DATA-03 (removed) |", "| PORT-01–PORT-03; DATA-03 (removed) |")
        self.replace("docs/architecture.md", "## Risks and open questions", "## Risks and open questions\n\n- PORT-03 "
                     "needs a risk model.")
        self.assertEqual(self.status("architecture-design")["mode"], "current")
        self.assertEqual(self.status("pipeline-design")["mode"], "current")
        self.assertEqual(self.status("build-planning")["mode"], "blocked")
        d = self.skip_tests()
        self.assertEqual((d["skill"], d["mode"]), ("pipeline-design", "extend"))
        self.assertIn("below Designed", d["reason"])


class RouteTest(NextCase):
    def test_routed_change_goes_to_its_owners_revise(self):
        rc, out, _ = self.dt("route", "architecture-design", "stats.Cov needs a window field (PL-02.estimate)",
                             "--from", "pipeline-design")
        self.assertEqual((rc, out), (0, "routed: architecture-design · stats.Cov needs a window field "
                                       "(PL-02.estimate)\n"))
        self.assertIn("- [ ] architecture-design · stats.Cov needs a window field (PL-02.estimate) (from "
                      "pipeline-design, ", self.read("docs/routes.md"))
        r = self.status("architecture-design")
        self.assertEqual((r["mode"], r["routed_changes"]),
                         ("revise", ["stats.Cov needs a window field (PL-02.estimate) (from pipeline-design)"]))
        self.assertEqual(self.dt("lint", "docs/")[0], 0)
        d = self.next()
        self.assertEqual((d["skill"], d["mode"]), ("architecture-design", "revise"))
        self.assertIn("stats.Cov needs a window field", d["reason"])
        # A Draft from the Revise waits at the gate first; approval ticks the route.
        self.replace("docs/architecture.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.next()["mode"], "gate")
        self.replace("docs/architecture.md", "**Status:** Draft", "**Status:** Approved")
        self.assertEqual(self.dt("route", "--done", "architecture-design")[1],
                         "ticked: 1 change(s) routed to architecture-design\n")
        self.assertEqual(self.status("architecture-design")["mode"], "current")
        self.assertEqual(self.next()["skill"], "test-planning")
        self.assertEqual(self.dt("route")[1], "routed: none\n")

    def test_owner_modes_and_listing(self):
        self.dt("route", "pipeline-design", "split PL-02.estimate")
        self.dt("route", "test-planning", "TC-02 tolerance for the new window", "--from", "pipeline-design")
        self.dt("route", "spec-writing", "STAT-02 names a 60-day window")
        self.assertEqual(self.status("pipeline-design")["mode"], "revise")
        self.assertEqual(self.status("test-planning")["mode"], "revise")
        self.assertEqual(self.status("spec-writing")["routed_changes"], ["STAT-02 names a 60-day window"])
        # Owners in planning order: the spec first.
        self.assertEqual((self.next()["skill"], self.next()["mode"]), ("spec-writing", "extend"))
        rows = json.loads(self.dt("route", "--json")[1])
        self.assertEqual([r["skill"] for r in rows], ["pipeline-design", "test-planning", "spec-writing"])
        self.assertEqual(self.dt("route", "architecture-design", "  ")[0], 2)
        self.assertEqual(self.dt("route", "build-setup", "x")[0], 2)


class ProbeNextTest(NextCase):
    probes = True

    def test_open_probe_waits_on_the_user(self):
        self.replace("docs/architecture.md", "**Status:** Proposed · **Date:** 2026-10-17",
                     "**Status:** Accepted · **Date:** 2026-10-17")
        self.assertEqual(self.status("build-planning")["mode"], "blocked")
        d = self.next()
        self.assertEqual((d["skill"], d["mode"], d["waiting_on_user"]), ("api-probe", "record", False))
        # Once the agent's run is recorded, the user's checks are what build-planning waits for.
        self.replace("docs/probes.md", "**Milestones:** M2 · **Last run:** —", "**Milestones:** M2 · **Last run:** 2026-10-17T09:30:00Z")
        d = self.skip_tests()
        self.assertEqual((d["skill"], d["mode"], d["waiting_on_user"]), ("api-probe", "waiting", True))
        self.assertIn("PB-02", d["reason"])


if __name__ == "__main__":
    unittest.main()
