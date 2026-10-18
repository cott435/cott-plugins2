"""The iteration-9 rules on copies of fixtures/gridload (design/example-domains.md), an interface-first M1 laid out
as design/interface-first-design.md §4.1 has it: the interface task writes `__init__.py`, `__main__.py`, the
re-exporting `pipeline.py` and the types; each wiring task writes only its own entry module and smoke test.

`dt lint`: `writes`, `boundaries`, `probe-open`, the brief `budget`, `milestone-depends`; `dt roadmap --check`'s
cycle; `Milestone.depends`; `dt status --skill build-planning`'s `no_spine` and `boundaries_unfrozen`."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dt_helpers import HERE, run_dt

from devteam import model  # noqa: E402
from devteam.commands import lint  # noqa: E402
from devteam.repo import Repo  # noqa: E402

GRIDLOAD = HERE / "fixtures" / "gridload"
PLAN, ARCH, BRIEF, ROADMAP = "tasks/plan.md", "docs/architecture.md", "docs/brief.md", "docs/roadmap.md"
CONTRACT, PIPES, PROBES = ("docs/packages/gridload/contract.md", "docs/packages/gridload/pipelines.md",
                           "docs/probes.md")
T07_WRITES = "**Writes:** src/gridload/pipelines/pl02_seasonality.py, tests/unit/gridload/test_pl02_smoke.py"
SYSTEM = """
## System pipelines
### PL-03: Day-ahead run
**Trigger:** `python -m gridload dayahead`
1. `ingest` → `profile` over `ingest.load_readings`

### PL-04: Reserve plan
**Trigger:** `python -m gridload reserves`
1. `profile` → `forecast` over `profile.Profile`
"""


class GridLoadCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "gridload"
        shutil.copytree(GRIDLOAD, self.root)
        env = mock.patch.dict(os.environ)
        env.start()
        os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        self.addCleanup(env.stop)

    def edit(self, rel: str, old: str, new: str) -> None:
        p = self.root / rel
        text = p.read_text(encoding="utf-8")
        self.assertIn(old, text)
        p.write_text(text.replace(old, new, 1), encoding="utf-8")

    def problems(self):
        return lint.lint(Repo(self.root))

    def messages(self, code: str) -> list[str]:
        return [p.message for p in self.problems() if p.code == code]

    def status(self) -> dict:
        return json.loads(run_dt(self.root, "status", "--skill", "build-planning", "--json")[1])


class FixtureTest(GridLoadCase):
    def test_clean(self):
        self.assertEqual([str(p) for p in lint.lint(Repo(GRIDLOAD))], [])
        self.assertEqual(run_dt(GRIDLOAD, "roadmap", "--check")[:2], (0, "roadmap: ok\n"))
        d = self.status()
        self.assertEqual((d["no_spine"], d["boundaries_unfrozen"]), ([], []))


class WritesTest(GridLoadCase):
    """interface-F1: wiring tasks never share a file; the shared modules are the interface task's."""

    def test_wiring_tasks_never_share_a_file_even_ordered(self):
        self.edit(PLAN, "**Writes:** src/gridload/pipelines/pl01_ingest.py,",
                  "**Writes:** src/gridload/pipelines/pl01_ingest.py, src/gridload/cli.py,")
        self.edit(PLAN, T07_WRITES, T07_WRITES.replace("pl02_seasonality.py,", "pl02_seasonality.py, src/gridload/cli.py,"))
        wiring = ("M1-T07 and M1-T06 are wiring tasks that both write src/gridload/cli.py: each writes only its own "
                  "pipeline's entry module and smoke test, and the interface task writes `__main__.py` and any "
                  "re-exporting `pipeline.py`")
        self.assertEqual(self.messages("writes"), [wiring])          # with no path: this message, not both
        self.edit(PLAN, "**Depends on:** M1-T04, M1-T05 ·", "**Depends on:** M1-T04, M1-T05, M1-T06 ·")
        self.edit(PLAN, "| M1-T07 wire PL-02 | M1-T06 wire PL-01 | call | ingest.load_readings fake (M1-T01) |",
                  "| M1-T07 wire PL-02 | M1-T06 wire PL-01 | file | none: both write src/gridload/cli.py |")
        self.assertEqual(self.messages("writes"), [wiring])          # a Depends on path doesn't excuse it
        self.assertEqual(self.messages("edges"), [])

    def test_shared_modules_belong_to_the_interface_task(self):
        self.edit(PLAN, T07_WRITES, T07_WRITES + ", src/gridload/__main__.py")
        self.edit(PLAN, "**Writes:** src/gridload/pipelines/pl02_seasonality.py, tests/unit/gridload/test_system_smoke.py",
                  "**Writes:** src/gridload/pipeline.py, tests/unit/gridload/test_system_smoke.py")
        self.edit(PLAN, "**Writes:** src/gridload/ingest/units.py,", "**Writes:** src/gridload/ingest/types.py,")
        self.assertEqual(self.messages("writes"), [
            "M1-T03 (spine) writes the shared file src/gridload/ingest/types.py: only the interface task may",
            "M1-T07 (wiring) writes the shared file src/gridload/__main__.py: only the interface task may",
            "M1-T08 (system) writes the shared file src/gridload/pipeline.py: only the interface task may"])

    def test_a_pipeline_py_two_pipelines_enter_through_is_shared(self):
        self.edit(PIPES, "`src/gridload/pipelines/pl01_ingest.py::run_ingest`", "`src/gridload/pipeline.py::run_ingest`")
        self.edit(PIPES, "`src/gridload/pipelines/pl02_seasonality.py::run_seasonality`",
                  "`src/gridload/pipeline.py::run_seasonality`")
        self.edit(PLAN, "**Writes:** src/gridload/pipelines/pl01_ingest.py,", "**Writes:** src/gridload/pipeline.py,")
        self.assertEqual(self.messages("writes"), [
            "M1-T06 (wiring) writes the shared file src/gridload/pipeline.py: only the interface task may "
            "(src/gridload/pipeline.py is the entry of PL-01, PL-02: give each pipeline its own entry module)"])

    def test_entry_module_stays_with_wiring_or_system(self):
        # The fixture's system task M1-T08 writes PL-02's entry module, and lints clean; a spine may not.
        self.edit(PLAN, "**Writes:** src/gridload/profile/report.py,", "**Writes:** src/gridload/pipelines/pl02_seasonality.py,")
        self.assertEqual(self.messages("writes"), [
            "M1-T05 (spine) writes the shared file src/gridload/pipelines/pl02_seasonality.py: only an interface, "
            "wiring or system task may"])


class BoundariesTest(GridLoadCase):
    """interface-F2: a function another component or pipeline calls has a Boundary line, so it gets a fake."""
    LOAD_BOUNDARY = ("- **Boundary:** profile · **Fixtures:** tests/contracts/ingest.load_readings/ · "
                     "**Cases:** one region's week\n- **Used by:** profile; PL-01, PL-02")
    FIT_USED_BY = "- **Errors:** `ValueError` with under two weeks of readings\n- **Used by:** PL-02"

    def fit_used_by(self, value: str) -> None:
        self.edit(CONTRACT, self.FIT_USED_BY, self.FIT_USED_BY.replace("PL-02", value))

    def test_call_into_another_pipeline_needs_a_boundary(self):
        self.edit(CONTRACT, self.LOAD_BOUNDARY, "- **Used by:** profile; PL-01, PL-02")
        # PL-02 runs load_readings as `PL-01 as built`: a call across pipelines and components.
        self.assertEqual(self.messages("boundaries"), [
            "ingest.load_readings is used by profile, PL-02 but has no **Boundary:** line: add `- **Boundary:** "
            "<consumers> · **Fixtures:** tests/contracts/ingest.load_readings/ · **Cases:** …` so the interface "
            "task freezes its fake"])
        self.assertEqual({p.severity for p in self.problems() if p.code == "boundaries"}, {"E"})

    def test_used_by_its_own_component_and_pipeline_is_fine(self):
        self.fit_used_by("profile; PL-02")
        self.assertEqual(self.messages("boundaries"), [])

    def test_used_by_another_component_or_pipeline(self):
        self.fit_used_by("forecast; PL-01, PL-02")
        self.assertEqual([m.split(" but")[0] for m in self.messages("boundaries")],
                         ["profile.fit_seasonality is used by forecast, PL-01"])

    def test_types_are_left_to_type_cases(self):
        self.edit(CONTRACT, "- **Invariants:** `table` lists every term in `profile`\n- **Used by:** PL-02",
                  "- **Invariants:** `table` lists every term in `profile`\n- **Used by:** forecast; PL-01")
        self.assertEqual(self.messages("boundaries"), [])

    def test_pipeline_entry(self):
        entry = ("\n### ingest.run_ingest: PL-01 entry\n`def run_ingest(regions: tuple[str, ...]) -> Readings`\n"
                 "- **Used by:** PL-01\n")
        self.edit(CONTRACT, "\n## profile\n", entry + "\n## profile\n")
        self.assertEqual(self.messages("boundaries"), [])        # its own pipeline's entry
        self.edit(CONTRACT, "- **Used by:** PL-01\n\n## profile", "- **Used by:** PL-01, PL-02\n\n## profile")
        self.assertEqual([m.split(" but")[0] for m in self.messages("boundaries")],
                         ["ingest.run_ingest is used by PL-02"])

    def test_pipeline_section_used_by(self):
        self.edit(PIPES, "**Covers:** LOAD-01, LOAD-02\n", "**Covers:** LOAD-01, LOAD-02\n**Used by:** PL-02\n")
        self.assertEqual(self.messages("boundaries"), [
            "PL-01's entry is used by PL-02 but has no **Boundary:** line: add `**Boundary:** <consumers> · "
            "**Fixtures:** tests/contracts/<pkg.entry>/` so the interface task freezes its fake"])
        self.edit(PIPES, "**Used by:** PL-02\n",
                  "**Used by:** PL-02 · **Boundary:** PL-02 · **Fixtures:** tests/contracts/ingest.run_ingest/\n")
        self.assertEqual(self.messages("boundaries"), [])


class ProbeOpenTest(GridLoadCase):
    """flow-F6: a decision stays Proposed while the probe it cites is open."""
    PB01 = "**Status:** Draft · **Milestones:** M2"

    def accept_ad02(self):
        self.edit(ARCH, "**Status:** Proposed · **Date:** 2026-10-17 · **Scope:** ingest",
                  "**Status:** Accepted · **Date:** 2026-10-17 · **Scope:** ingest")

    def test_accepted_while_the_probe_is_open(self):
        self.accept_ad02()
        self.assertEqual(self.messages("probe-open"), [
            "AD-02 is Accepted while its probe PB-01 is Draft: keep it Proposed until PB-01 is Answered or Waived"])
        (self.root / "probes" / "PB-01-weather-history").mkdir(parents=True)
        self.edit(PROBES, self.PB01, "**Status:** Ready · **Milestones:** M2")
        self.assertEqual([m.split(":")[0] for m in self.messages("probe-open")],
                         ["AD-02 is Accepted while its probe PB-01 is Ready"])

    def test_answered_or_waived_lets_it_be_accepted(self):
        self.accept_ad02()
        (self.root / "probes" / "PB-01-weather-history").mkdir(parents=True)
        for status in ("Answered · pass · 2026-10-17", "Answered · fail · 2026-10-17", "Waived"):
            self.edit(PROBES, self.PB01, f"**Status:** {status} · **Milestones:** M2")
            self.assertEqual(self.messages("probe-open"), [], status)
            self.PB01 = f"**Status:** {status} · **Milestones:** M2"

    def test_proposed_is_fine(self):
        self.assertEqual(self.messages("probe-open"), [])          # the fixture: Proposed AD-02, Draft PB-01


class BriefBudgetTest(GridLoadCase):
    """flow-F8: the brief is about one page (500 words, the count `dt status` prints) with at most 5 goals."""
    LAST_GOAL = "3. Day-ahead forecasts that beat seasonal-naive on held-out weeks.\n"

    def budget(self) -> list[str]:
        return [p.message for p in self.problems() if p.code == "budget" and p.path == BRIEF]

    def test_goals(self):
        self.edit(BRIEF, self.LAST_GOAL, self.LAST_GOAL + "4. Reserve plans from the forecasts.\n"
                  "5. Explain each day's forecast in one paragraph.\n")
        self.assertEqual(self.budget(), [])
        self.edit(BRIEF, "5. Explain", "6. A weather-aware forecast.\n5. Explain")
        self.assertEqual(self.budget(), ["6 goals, at most 5: a new stage is not a new goal; ask the user which to "
                                         "merge"])
        self.assertEqual(run_dt(self.root, "lint")[0], 0)             # a warning

    def test_words(self):
        self.edit(BRIEF, "## Users", "Filler words for the test. " * 90 + "\n\n## Users")
        words = json.loads(run_dt(self.root, "status", "--skill", "idea-refine", "--json")[1])["brief_words"]
        self.assertGreater(words, 500)
        self.assertEqual(self.budget(), [f"{words} words, budget 500 (about one page)"])


class MilestoneDependsTest(GridLoadCase):
    """interface-F13: Depends notes in parentheses aren't dependencies; a real cycle is an error."""
    M2_ROW = "| M2 | Seasonal-naive forecast | brief | gridload | — | M1 (profile.Profile from PL-02) | Designed |"

    def depends(self) -> dict[str, list[str]]:
        return {m.id: m.depends for m in model.milestones(Repo(self.root).roadmap)}

    def test_notes_in_parentheses_are_not_dependencies(self):
        self.edit(ROADMAP, self.M2_ROW, self.M2_ROW.replace(
            "M1 (profile.Profile from PL-02)", "M1 (build order: after M1, before M3, by the user's choice)") +
            "\n| M3 | Reserve plans | brief | gridload | — | M2 (build order: M1 → M2 → M3 (then M4)) | Idea |")
        self.assertEqual(self.depends(), {"M1": [], "M2": ["M1"], "M3": ["M2"]})
        self.assertEqual(self.messages("milestone-depends"), [])
        self.edit(ROADMAP, "| M2 (build order:", "| M2, M1 (unclosed note naming M3 |")
        self.assertEqual(self.depends()["M3"], ["M2", "M1"])

    def test_cycle(self):
        self.edit(ROADMAP, "| PL-01, PL-02 | — |", "| PL-01, PL-02 | M2 (its forecast checks the profile) |")
        self.assertEqual(self.messages("milestone-depends"), [
            "Depends cycle: M1 → M2 → M1: Depends lists only the milestones whose outputs are needed; a build order "
            "goes in the milestone's section"])
        code, out, _ = run_dt(self.root, "roadmap", "--check")
        self.assertEqual((code, out.splitlines()[-2:]),
                         (1, ["Depends cycle: M1 → M2 → M1 (Depends lists only the milestones whose outputs are "
                              "needed)", "roadmap: Depends cycle"]))


class SystemSpineTest(GridLoadCase):
    """interface-F4 residue: one system task runs every system pipeline its Read or Reason names."""

    def setUp(self):
        super().setUp()
        self.edit(ARCH, "## Decisions", SYSTEM.lstrip() + "\n## Decisions")
        self.edit(ROADMAP, "| PL-01, PL-02 | — |", "| PL-01, PL-02, PL-03, PL-04 | — |")
        self.edit(PLAN, "**Step:** PL-02 · **Kind:** system", "**Step:** PL-03 · **Kind:** system")

    def test_no_spine_counts_named_system_pipelines(self):
        self.assertEqual(self.status()["no_spine"], ["PL-04"])
        self.edit(PLAN, "**Read:** PL-01, PL-02, ingest.load_readings", "**Read:** PL-01, PL-02, PL-04, ingest.load_readings")
        self.assertEqual(self.status()["no_spine"], [])

    def test_reason_counts_and_package_pipelines_do_not(self):
        t08 = next(t for t in model.tasks(Repo(self.root).plan) if t.id == "M1-T08")
        self.assertEqual(model.spine_pipelines(t08, {"PL-03", "PL-04"}), ["PL-03"])       # PL-01, PL-02 have wiring
        self.edit(PLAN, "**Step:** PL-03 · **Kind:** system · **Size:** S · **Mode:** solo",
                  "**Step:** PL-03 · **Kind:** system · **Size:** S · **Mode:** solo\n**Reason:** runs PL-04 too")
        t08 = next(t for t in model.tasks(Repo(self.root).plan) if t.id == "M1-T08")
        self.assertEqual(model.spine_pipelines(t08, {"PL-03", "PL-04"}), ["PL-03", "PL-04"])
        self.assertEqual(model.spine_pipeline(t08, {"PL-03", "PL-04"}), "PL-03")


class BoundariesUnfrozenTest(GridLoadCase):
    """interface-F12: the interface task declares every type a milestone step's In → Out names."""
    READ = "profile.Profile, profile.Report, ingest.load_readings"

    def test_step_type_missing_from_the_interface(self):
        self.edit(PLAN, self.READ, "profile.Profile, ingest.load_readings")
        self.assertEqual(self.status()["boundaries_unfrozen"], ["profile.Report (PL-02.write_report)"])
        self.edit(PLAN, "src/gridload/pipelines/**, tests/contracts/**",
                  "src/gridload/pipelines/**, tests/contracts/**, tests/contracts/profile.Report/")
        self.assertEqual(self.status()["boundaries_unfrozen"], [])     # its Writes freezes it

    def test_frozen_by_an_earlier_milestone(self):
        self.edit(PLAN, self.READ, "profile.Profile, ingest.load_readings")
        (self.root / "tests" / "contracts" / "profile.Report").mkdir(parents=True)
        self.assertEqual(self.status()["boundaries_unfrozen"], [])

    def test_boundary_symbols_are_listed_once(self):
        self.edit(PLAN, self.READ, "profile.Report, ingest.load_readings")
        # profile.Profile is both a Boundary to the component forecast and a type PL-02's steps name: one item.
        self.assertEqual(self.status()["boundaries_unfrozen"], ["profile.Profile (forecast)"])


if __name__ == "__main__":
    unittest.main()
