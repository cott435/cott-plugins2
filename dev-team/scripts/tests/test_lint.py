"""dt lint: every check code, positive and negative, on mutated copies of fixtures/quant."""
from __future__ import annotations

import json
import unittest
from unittest import mock

from dt_helpers import HAS_GIT, QUANT, Project, run_main

from devteam.commands import lint  # noqa: E402
from devteam.repo import Repo  # noqa: E402

PLAN, TODO, PIPES = "tasks/plan.md", "tasks/todo.md", "docs/packages/quant/pipelines.md"
ARCH, SPEC, CONTRACT = "docs/architecture.md", "docs/spec.md", "docs/packages/quant/contract.md"


class FixtureTest(unittest.TestCase):
    def test_fixture_is_clean(self):
        self.assertEqual([str(p) for p in lint.lint(Repo(QUANT))], [])

    def test_cli_text_and_json(self):
        code, out = run_main("--root", str(QUANT), "lint")
        self.assertEqual((code, out.strip()), (0, "0 errors, 0 warnings"))
        code, out = run_main("--root", str(QUANT), "lint", "--json")
        self.assertEqual(json.loads(out), {"problems": [], "errors": 0, "warnings": 0})


class LintCase(unittest.TestCase):
    """Each test mutates its own copy of the fixture and asserts which codes appear where. `legacy` swaps in the
    old-style plan; its `deprecated` warnings are left out unless a test asks for them."""
    git = False
    legacy = False

    def setUp(self):
        self.p = Project(git=self.git, legacy=self.legacy)
        self.addCleanup(self.p.cleanup)

    def problems(self, scope=None):
        out = lint.lint(Repo(self.p.root), scope)
        return [p for p in out if p.code != "deprecated"] if self.legacy else out

    def found(self, scope=None) -> set[tuple[str, str]]:
        return {(p.path, p.code) for p in self.problems(scope)}

    def assertCode(self, path, code, scope=None):
        self.assertIn((path, code), self.found(scope), [str(p) for p in self.problems(scope)])

    def assertClean(self, scope=None):
        self.assertEqual([str(p) for p in self.problems(scope)], [])


class IdChecks(LintCase):
    def test_dup_id(self):
        self.p.edit(ARCH, "## Risks and open questions", "### AD-03: Again\n\n## Risks and open questions")
        self.assertCode(ARCH, "dup-id")

    def test_dup_id_retired_but_still_defined(self):
        self.p.edit(PIPES, "## Planned layout", "## PL-04: Back again\nx\n\n## Planned layout")
        self.assertCode(PIPES, "dup-id")

    def test_missing_ref_in_fields_and_tables(self):
        self.p.edit(PLAN, "**Read:** PL-01, TC-01, DATA-02", "**Read:** PL-01, TC-09, DATA-02")
        self.p.edit(ARCH, "| PORT-01, PORT-02 |", "| PORT-01, PORT-07 |")
        self.p.edit(CONTRACT, "**Used by:** PL-03", "**Used by:** PL-08")
        found = {(p.path, p.message) for p in self.problems() if p.code == "missing-ref"}
        self.assertEqual(found, {(PLAN, "Read: TC-09 is not defined"), (ARCH, "Covers: PORT-07 is not defined"),
                                 (CONTRACT, "Used by: PL-08 is not defined")})

    def test_missing_ref_ignores_paths_in_read(self):
        self.p.edit(PLAN, "**Read:** PL-01, TC-01, DATA-02", "**Read:** PL-01, TC-01, pyproject.toml, src/x.py, DATA-02")
        self.assertClean()

    def test_missing_ref_step_names_unknown_pipeline(self):
        self.p.edit(PLAN, "**Step:** PL-01.apply_universe", "**Step:** PL-07.apply_universe")
        self.assertCode(PLAN, "missing-ref")

    def test_retired_ref(self):
        self.p.edit(ARCH, "One Python package", "AD-02 aside, one Python package")
        self.p.edit(PLAN, "**Read:** PL-01, TC-01, DATA-02", "**Read:** PL-04, TC-01, DATA-02")
        self.assertCode(ARCH, "retired-ref")
        self.assertCode(PLAN, "retired-ref")

    def test_retired_ref_exemptions(self):
        # The fixture already mentions AD-02 inside AD-03 (its superseder), DATA-03 in the spec Changelog,
        # PL-04 on its own retired line: all clean. Mentioning AD-02 in another decision is not.
        self.assertClean()
        self.p.edit(ARCH, "- **Decision:** One package, uv.", "- **Decision:** One package, uv, not AD-02.")
        self.assertCode(ARCH, "retired-ref")

    def test_removed_requirement_reference(self):
        self.p.edit(ARCH, "| DATA-01, DATA-02, QR-01 |", "| DATA-01, DATA-03, QR-01 |")
        self.assertCode(ARCH, "retired-ref")


class BudgetChecks(LintCase):
    def test_contract_over_budget_is_a_warning(self):
        self.p.edit(CONTRACT, "- **Used by:** PL-03", "- **Used by:** PL-03\n" + "filler\n" * 40)
        self.assertCode(CONTRACT, "budget")
        code, _ = run_main("--root", str(self.p.root), "lint")
        self.assertEqual(code, 0)

    def _add_symbols(self, n: int):
        self.p.edit(CONTRACT, "## portfolio", "".join(
            f"### stats.extra{k}: Extra {k}\n`def extra{k}() -> None`\n- **Invariants:** none\n"
            f"- **Errors:** none\n- **Used by:** PL-02\n\n" for k in range(n)) + "## portfolio")

    def budget_messages(self, rel):
        return [p.message for p in self.problems() if p.path == rel and p.code in ("budget", "grow-size")]

    def test_contract_budget_is_per_symbol(self):
        self._add_symbols(10)       # 139 lines, well past the old fixed 60, at 6 lines a symbol
        self.assertEqual(self.budget_messages(CONTRACT), [])
        self.p.edit(CONTRACT, "- **Used by:** PL-03", "- **Used by:** PL-03\n" + "filler\n" * 57)
        self.assertEqual(self.budget_messages(CONTRACT), ["196 lines, budget 188 (8 per symbol × 22 + 12)"])

    def test_pipelines_budget_is_per_pipeline(self):
        self.p.edit(PIPES, "**Covers:** PORT-01, PORT-02", "**Covers:** PORT-01, PORT-02\n" + "filler\n" * 70)
        self.assertEqual(self.budget_messages(PIPES), ["135 lines, budget 127 (35 per pipeline × 3 + 10 + 12 layout)"])

    def test_pipelines_budget_grows_with_step_rows(self):
        # iteration 10 D6: a pipeline of 20 step rows gets 20 + 1.5 × 20 = 50 lines, not 35.
        rows = "".join(f"| {k} | `extra{k}` | portfolio | Weights → Weights | identity | — |\n" for k in range(4, 21))
        self.p.edit(PIPES, "| realized variance only | PORT-02 |\n", "| realized variance only | PORT-02 |\n" + rows)
        self.assertEqual(self.budget_messages(PIPES), [])
        self.p.edit(PIPES, "**Covers:** PORT-01, PORT-02", "**Covers:** PORT-01, PORT-02\n" + "filler\n" * 61)
        self.assertEqual(self.budget_messages(PIPES), ["143 lines, budget 142 (35 per pipeline × 2 + (20 + 1.5 per "
                                                       "step row) × 1 (20 rows) + 10 + 12 layout)"])

    def test_pipelines_layout_section_is_extra(self):
        layout = "## Planned layout (pre-build — removed by spine task)"
        self.p.edit(PIPES, layout, layout + "\n" + "- line\n" * 100)
        self.assertEqual(self.budget_messages(PIPES), [])

    def test_tests_budget_is_per_case(self):
        self.p.edit("docs/packages/quant/tests.md", "## Open questions", "filler\n" * 20 + "## Open questions")
        self.assertCode("docs/packages/quant/tests.md", "budget")

    def test_grow_ceiling_is_a_separate_warning(self):
        self._add_symbols(22)
        self.p.edit(CONTRACT, "- **Used by:** PL-03", "- **Used by:** PL-03\nfiller\nfiller")
        self.assertEqual(self.budget_messages(CONTRACT), [
            "212 lines, over the 200-line ceiling for one package's contract doc: size alone never splits a "
            "package; trim the doc, or split a module"])
        code, _ = run_main("--root", str(self.p.root), "lint")
        self.assertEqual(code, 0)

    def test_grow_ceiling_held_by_the_users_one_package(self):
        self._add_symbols(22)
        self.p.write("docs/requests.md", "# Quant Lab — User requests\n\n**Last updated:** 2026-10-18\n\n"
                     '- **UR-01** architecture · "Keep it as one package, no split." · architecture-design 2026-10-18 '
                     "→ AD-01\n")
        self.assertEqual(self.budget_messages(CONTRACT), [])

    def test_plan_over_budget(self):
        self.p.edit(PLAN, "## Replan notes", "## Replan notes\n" + "- note\n" * 400)
        self.assertCode(PLAN, "budget")

    def test_roadmap_section(self):
        self.p.edit("docs/roadmap.md", "**Exit:** Min-var", "a\nb\nc\nd\ne\nf\n**Exit:** Min-var")
        self.assertCode("docs/roadmap.md", "budget")

    def test_agents_doc_map(self):
        self.p.edit("AGENTS.md", "## Project skills", "- more\n" * 20 + "## Project skills")
        self.assertCode("AGENTS.md", "budget")


@unittest.skipUnless(HAS_GIT, "git not installed")
class ApprovedEdit(LintCase):
    git = True

    def test_edited_while_approved(self):
        self.p.edit(CONTRACT, "long only", "long only; no leverage")
        self.assertCode(CONTRACT, "approved-edit")

    def test_back_to_draft_or_header_only_is_fine(self):
        self.p.edit(CONTRACT, "**Last updated:** 2026-10-15", "**Last updated:** 2026-10-17")
        self.assertClean()
        self.p.edit(CONTRACT, "long only", "long only; no leverage")
        self.p.edit(CONTRACT, "**Status:** Approved", "**Status:** Draft")
        self.assertClean()

    def test_contract_used_by_appends_are_exempt(self):
        self.p.edit(CONTRACT, "- **Used by:** PL-02, PL-03", "- **Used by:** PL-02, PL-03, PL-01")
        self.assertClean()
        self.p.edit(CONTRACT, "long only", "long only; no leverage")
        self.assertCode(CONTRACT, "approved-edit")

    def test_used_by_exemption_is_contract_only(self):
        self.p.edit(PIPES, "**Covers:** PORT-01, PORT-02", "**Covers:** PORT-01, PORT-02\n- **Used by:** PL-01")
        self.assertCode(PIPES, "approved-edit")

    def test_plan_is_exempt(self):
        self.p.edit(PLAN, "## Open questions", "## Open questions\n- one")
        self.assertClean()

    def test_outside_git_is_skipped(self):
        p = Project(git=False)
        self.addCleanup(p.cleanup)
        p.edit(CONTRACT, "long only", "long only; no leverage")
        self.assertEqual(lint.lint(Repo(p.root)), [])


class PrebuildLeft(LintCase):
    def test_entry_sketch_after_wiring_checked(self):
        self.p.edit(TODO, "- [ ] M1-T09", "- [x] M1-T09")
        lines = {(p.path, p.line) for p in self.problems() if p.code == "prebuild-left"}
        self.assertEqual(lines, {(PIPES, 28)})   # Planned layout stays: PL-03 has no spine task yet

    def test_planned_layout_after_every_spine(self):
        text = self.p.read(PIPES)
        start, end = text.index("## PL-03"), text.index("## Planned layout")
        self.p.write(PIPES, text[:start] + text[end:])
        self.p.edit(TODO, "- [ ] M1-T08", "- [x] M1-T08")
        self.p.edit(TODO, "- [ ] M1-T09", "- [x] M1-T09")
        lines = {p.line for p in self.problems() if p.code == "prebuild-left"}
        self.assertEqual(len(lines), 2)

    def test_pipeline_built_in_an_earlier_milestone(self):
        # PL-03 has no spine task in the active plan: it counts as built once its entry file exists.
        self.p.edit(PIPES, "## Planned layout", "### Entry sketch (pre-build — removed by spine task)\nx\n\n## Planned layout")
        self.assertNotIn((PIPES, "prebuild-left"), self.found())
        self.p.write("src/quant/portfolio/pipeline.py", "def run_backtest(): ...\n")
        self.assertIn((PIPES, "prebuild-left"), self.found())

    def test_unchecked_wiring_is_fine(self):
        self.p.edit(TODO, "- [ ] M1-T05", "- [x] M1-T05")          # a step spine doesn't build the pipeline
        self.assertNotIn((PIPES, "prebuild-left"), self.found())


class PrebuildLeftLegacy(LintCase):
    legacy = True

    def test_entry_sketch_after_phase0_spine_checked(self):
        self.p.edit(TODO, "- [ ] M1-T02", "- [x] M1-T02")
        lines = {(p.path, p.line) for p in self.problems() if p.code == "prebuild-left"}
        self.assertEqual(lines, {(PIPES, 28)})


TESTS = "docs/packages/quant/tests.md"


class PipelineAndFixtureChecks(LintCase):
    def test_pipeline_without_trigger(self):
        self.p.edit(PIPES, "`src/quant/portfolio/pipeline.py::run_backtest` · **Trigger:** `python -m quant.portfolio backtest`",
                    "`src/quant/portfolio/pipeline.py::run_backtest`")
        msgs = [p.message for p in self.problems() if p.code == "pipeline-fields"]
        self.assertEqual(msgs, ["PL-03 has no Trigger"])

    def test_step_with_empty_owner_or_spine(self):
        self.p.edit(PIPES, "| 3 | `compare` | portfolio | Weights, Returns → Comparison | realized variance only |",
                    "| 3 | `compare` |  | Weights, Returns → Comparison | — |")
        msgs = [p.message for p in self.problems() if p.code == "pipeline-fields"]
        self.assertEqual(msgs, ["PL-03 step `compare` has an empty Owner and Spine version cell"])

    SYSTEM = ("\n## System pipelines\n### PL-09: Nightly report\n"
              "**Trigger:** cron, 06:00 · **Covers:** STAT-04\n"
              "1. `data` → `stats`: `data.load_prices`\n2. `stats` → `portfolio`: `stats.estimate_cov`\n")

    def append(self, rel: str, text: str) -> None:
        self.p.write(rel, self.p.read(rel) + text)

    def test_system_pipeline_needs_only_trigger_and_steps(self):
        self.append(ARCH, self.SYSTEM)
        self.assertClean()
        self.append(ARCH, "\n### PL-10: Table form\n**Trigger:** called by hand\n\n"
                    "| # | From → To | Contract | Spine version |\n|---|---|---|---|\n"
                    "| 1 | `data` → `stats` | `data.load_prices` | stub |\n")
        self.assertClean()      # no Entry, Owner or Spine version needed; no spine-mock either

    def test_system_pipeline_without_trigger_or_steps(self):
        self.append(ARCH, "\n## System pipelines\n### PL-09: Nightly report\n**Covers:** STAT-04\n")
        msgs = [p.message for p in self.problems() if p.code == "pipeline-fields"]
        self.assertEqual(msgs, ["PL-09 has no Trigger or step table"])

    def test_package_pipeline_still_needs_entry(self):
        self.p.edit(PIPES, "**Entry:** `src/quant/portfolio/pipeline.py::run_backtest` · ", "")
        msgs = [p.message for p in self.problems() if p.code == "pipeline-fields"]
        self.assertEqual(msgs, ["PL-03 has no Entry"])

    def test_spine_mock_is_a_warning(self):
        self.p.edit(PIPES, "| equal weight |", "| stub returning ones |")
        found = {(p.code, p.severity) for p in self.problems()}
        self.assertEqual(found, {("spine-mock", "W")})

    def test_part_of_reference(self):
        self.p.edit(PIPES, "**Covers:** PORT-01, PORT-02", "**Covers:** PORT-01, PORT-02 · **Part of:** PL-09")
        self.assertCode(PIPES, "missing-ref")

    def test_fixture_missing_folder_or_file_is_an_error(self):
        (self.p.root / "tests/fixtures/quant/TC-03/expected.json").unlink()
        self.p.edit(TESTS, "**Fixture:** tests/fixtures/quant/TC-01/", "**Fixture:** tests/fixtures/quant/TC-09/")
        found = sorted((p.message, p.severity) for p in self.problems() if p.code == "fixture-size")
        self.assertEqual(found, [("TC-01 Fixture folder tests/fixtures/quant/TC-09/ doesn't exist", "E"),
                                 ("TC-03 Fixture tests/fixtures/quant/TC-03/ has no expected.json", "E")])
        code, _ = run_main("--root", str(self.p.root), "lint")
        self.assertEqual(code, 1)

    def test_fixture_over_100kb_is_a_warning(self):
        self.p.path("tests/fixtures/quant/TC-02/big.csv").write_bytes(b"x" * 120_000)
        self.p.path("tests/fixtures/quant/TC-07/big.csv").parent.mkdir()
        self.p.path("tests/fixtures/quant/TC-07/big.csv").write_bytes(b"x" * 120_000)
        found = {(p.path, p.severity) for p in self.problems() if p.code == "fixture-size"}
        self.assertEqual(found, {(TESTS, "W"), ("tests/fixtures/quant/TC-07/", "W")})

    def test_parse_and_skills_fields_are_fine(self):
        self.p.edit(TESTS, "**Tolerance:** property, no tolerance",
                    "**Tolerance:** property, no tolerance\n**Parse:** `json.load` · **Skills:** data-science")
        self.assertClean()


class TaskChecks(LintCase):
    """Task rules on the old-style plan (Phase 0 spines, `Parallel`, `Files likely`), which still parses."""
    legacy = True

    def test_task_size_not_xs_to_m(self):
        self.p.edit(PLAN, "**Size:** XS", "**Size:** L")
        self.assertCode(PLAN, "task-size")

    def test_task_size_files_count(self):
        # Test files don't count: S takes 1–2 source files.
        self.p.edit(PLAN, "src/quant/data/steps.py, tests/unit/quant/test_universe.py",
                    "src/quant/data/steps.py, tests/unit/quant/test_universe.py, src/quant/data/x.py")
        self.assertNotIn((PLAN, "task-size"), self.found())
        self.p.edit(PLAN, "src/quant/data/x.py", "src/quant/data/x.py, src/quant/data/y.py")
        msgs = [p.message for p in self.problems() if p.code == "task-size"]
        self.assertEqual(msgs, ["M1-T03 Size S wants 1–2 source files in Files likely, has 3"])

    def test_task_acceptance(self):
        self.p.edit(PLAN, "- [ ] PL-01 smoke test still passes", "- [ ] PL-01 smoke test still passes\n- [ ] c\n- [ ] d")
        self.assertCode(PLAN, "task-acceptance")

    def test_sub_bullets_do_not_count(self):
        self.p.edit(PLAN, "- [ ] TC-01 passes", "- [ ] TC-01 passes\n  - detail\n  - detail")
        self.assertClean()

    def test_task_title(self):
        self.p.edit(PLAN, "### M1-T05: Shrinkage covariance", "### M1-T05: Shrinkage and sample covariance")
        self.assertCode(PLAN, "task-title")

    def test_task_fields_missing(self):
        self.p.edit(PLAN, "**Verify:** `pytest tests/intent/quant -k pca` · `python -m quant.stats cov-report --smoke` "
                    "· `scripts/check.sh gate`\n", "")
        msgs = [p.message for p in self.problems() if p.code == "task-fields"]
        self.assertEqual(msgs, ["M1-T06 missing Verify"])

    def test_task_fields_bad_mode(self):
        self.p.edit(PLAN, "**Size:** XS · **Mode:** split", "**Size:** XS · **Mode:** pair")
        self.assertCode(PLAN, "task-fields")

    def test_task_step_unknown_step_is_a_warning(self):
        self.p.edit(PLAN, "**Step:** PL-01.apply_universe", "**Step:** PL-01.drop_delisted")
        found = {p.code: p.severity for p in self.problems()}
        self.assertEqual(found, {"task-step": "W"})

    def test_depends_forward(self):
        self.p.edit(PLAN, "**Depends on:** M1-T01 · **Parallel:** G1", "**Depends on:** M1-T05 · **Parallel:** G1")
        msgs = [p.message for p in self.problems() if p.code == "depends"]
        self.assertEqual(msgs, ["M1-T03 depends on M1-T05, which comes later (or is itself)"])

    def test_depends_uses_plan_position_not_id_number(self):
        # Replan reorders without renumbering: M1-T06 moved above M1-T03 may be depended on by it.
        text = self.p.read(PLAN)
        t6 = text[text.index("### M1-T06"):text.index("### Checkpoint: milestone exit")]
        text = text.replace(t6, "").replace("### M1-T03", t6 + "### M1-T03")
        self.p.write(PLAN, text.replace("**Depends on:** M1-T01 · **Parallel:** G1", "**Depends on:** M1-T06 · **Parallel:** G1"))
        self.assertNotIn((PLAN, "depends"), self.found())
        self.p.edit(PLAN, "**Depends on:** M1-T02 · **Files likely:** src/quant/stats/pca.py",
                    "**Depends on:** M1-T04 · **Files likely:** src/quant/stats/pca.py")
        msgs = [p.message for p in self.problems() if p.code == "depends"]
        self.assertEqual(msgs, ["M1-T06 depends on M1-T04, which comes later (or is itself)"])

    def test_depends_unresolved(self):
        self.p.edit(PLAN, "**Depends on:** M1-T01 · **Parallel:** G1", "**Depends on:** M1-T99 · **Parallel:** G1")
        self.assertCode(PLAN, "depends")

    def test_depends_cycle(self):
        self.p.edit(PLAN, "**Depends on:** — ·", "**Depends on:** M1-T02 ·")
        msgs = [p.message for p in self.problems() if p.code == "depends"]
        self.assertIn("cycle: M1-T01 → M1-T02 → M1-T01", msgs)

    def _add_tasks(self, n: int, depends):
        """n XS tasks M1-T07… before the exit checkpoint; `depends(k)` gives task k's Depends on."""
        blocks = []
        for k in range(7, 7 + n):
            blocks.append(f"### M1-T{k:02d}: Extra step {k}\n"
                          "**Package:** quant · **Step:** PL-02.pca · **Size:** XS · **Mode:** solo\n"
                          "**Read:** PL-02\n**Acceptance:**\n- [ ] TC-03 passes\n"
                          "**Verify:** `python -m quant.stats cov-report --smoke`\n"
                          f"**Depends on:** {depends(k)} · **Files likely:** src/quant/stats/x{k}.py\n\n")
        self.p.edit(PLAN, "### Checkpoint: milestone exit", "".join(blocks) + "### Checkpoint: milestone exit")

    def size_messages(self):
        return [p.message for p in self.problems() if p.code == "milestone-size"]

    def test_milestone_size_is_the_critical_path(self):
        self._add_tasks(12, lambda k: "M1-T05" if k == 7 else f"M1-T{k - 1:02d}")
        chain = " → ".join(f"M1-T{k:02d}" for k in [1, 2, 4, 5] + list(range(7, 19)))
        self.assertEqual(self.size_messages(), [
            f"critical path is 16 tasks, cap 15: {chain}. Freeze an interface for an edge on it so both sides "
            "start at once, or cut the stage into another milestone where a later part needs an earlier part's "
            "outputs; never split independent tracks"])

    def test_milestone_size_at_cap_is_fine(self):
        self._add_tasks(11, lambda k: "M1-T05" if k == 7 else f"M1-T{k - 1:02d}")
        self.assertEqual(self.size_messages(), [])

    def test_parallel_tracks_do_not_add_up(self):
        self._add_tasks(20, lambda k: "M1-T02")
        self.assertEqual(self.size_messages(), [])

    def test_files_likely_conflict_is_a_warning(self):
        # M1-T04 and M1-T03 have no Depends-on path; Files likely is advisory, so sharing a file only warns.
        self.p.edit(PLAN, "src/quant/stats/rmt.py, tests/unit/quant/test_rmt.py", "src/quant/stats/rmt.py, src/quant/data/steps.py")
        found = [(p.severity, p.message) for p in self.problems() if p.code == "writes"]
        self.assertEqual(found, [("W", "M1-T04 and M1-T03 both write src/quant/data/steps.py with no Depends on path "
                                       "between them: move the shared part to the interface or wiring task, or "
                                       "order them (and give the edge a graph row)")])

    def test_files_likely_shared_along_a_path_is_fine(self):
        # M1-T05 (cov.py) depends on M1-T04, which depends on M1-T02 (cov.py): one runs after the other.
        self.assertNotIn((PLAN, "writes"), self.found())

    def test_old_fields_are_deprecated_warnings(self):
        found = [p for p in lint.lint(Repo(self.p.root)) if p.code == "deprecated"]
        self.assertEqual({p.severity for p in found}, {"W"})
        self.assertIn("M1-T03 **Parallel:** is deprecated: groups are derived from Depends on (`dt ready`, `dt status` "
                      "waves)", [p.message for p in found])
        self.assertEqual(sum(1 for p in found if "Files likely" in p.message), 6)
        self.assertEqual(run_main("--root", str(self.p.root), "lint")[0], 0)

    def test_verify_smoke(self):
        self.p.edit(PLAN, "**Verify:** `pytest tests/intent/quant tests/unit/quant -k cov` · `python -m quant.stats cov-report --smoke`",
                    "**Verify:** `pytest tests/intent/quant tests/unit/quant -k cov`")
        msgs = [p.message for p in self.problems() if p.code == "verify-smoke"]
        self.assertEqual(msgs, ["M1-T05 Verify lacks PL-02's smoke command `python -m quant.stats cov-report --smoke`"])

    def test_verify_smoke_falls_back_to_trigger(self):
        # PL-03 has no Strategy row, so its smoke command is its Trigger + --smoke.
        self.p.edit(PLAN, "**Step:** PL-02.pca", "**Step:** PL-03.min_variance")
        msgs = [p.message for p in self.problems() if p.code == "verify-smoke"]
        self.assertEqual(msgs, ["M1-T06 Verify lacks PL-03's smoke command `python -m quant.portfolio backtest --smoke`"])

    def test_spine_task_needs_no_smoke(self):
        self.p.edit(PLAN, "**Verify:** `python -m quant.data load --smoke` · `scripts/check.sh gate`",
                    "**Verify:** `scripts/check.sh gate`")
        self.assertClean()


class InterfaceFirstChecks(LintCase):
    """`writes`, `edges`, `step-io-types` and the Kind/Writes task rules on the interface-first fixture plan."""

    def messages(self, code):
        return [p.message for p in self.problems() if p.code == code]

    def test_fixture_plan_is_interface_first(self):
        self.assertClean()

    def test_kind_and_writes_required(self):
        self.p.edit(PLAN, "**Step:** PL-02.pca · **Kind:** spine · ", "**Step:** PL-02.pca · ")
        self.p.edit(PLAN, "**Depends on:** M1-T01 · **Writes:** src/quant/stats/report.py, tests/unit/quant/test_report.py",
                    "**Depends on:** M1-T01")
        self.assertEqual(self.messages("task-fields"), ["M1-T06 missing Kind", "M1-T07 missing Writes"])

    def test_unknown_kind(self):
        self.p.edit(PLAN, "**Kind:** spine · **Covers:** STAT-04", "**Kind:** stub · **Covers:** STAT-04")
        self.assertEqual(self.messages("task-fields"),
                         ["M1-T07 Kind 'stub': must be one of interface, spine, wiring, thicken, system"])

    def test_spine_writes_owner_module_and_test_at_xs(self):
        # XS counts source files only, so a spine's owner module plus its unit test is XS.
        self.assertEqual(self.messages("task-size"), [])

    def test_writes_conflict_without_a_path(self):
        self.p.edit(PLAN, "**Writes:** src/quant/stats/pca.py, tests/intent/quant/test_pca.py",
                    "**Writes:** src/quant/stats/pca.py, src/quant/stats/report.py, tests/intent/quant/test_pca.py")
        found = [(p.severity, p.message) for p in self.problems() if p.code == "writes"]
        self.assertEqual(found, [("E", "M1-T13 and M1-T07 both write src/quant/stats/report.py with no Depends on "
                                       "path between them: move the shared part to the interface or wiring task, or "
                                       "order them (and give the edge a graph row)")])

    def test_writes_conflict_across_groups(self):
        # Old Parallel groups don't matter: two tasks with no Depends-on path never share a file.
        self.p.edit(PLAN, "**Depends on:** M1-T03 · **Writes:**", "**Depends on:** M1-T03 · **Parallel:** G1 · **Writes:**")
        self.p.edit(PLAN, "**Depends on:** M1-T04 · **Writes:** src/quant/stats/cov.py,",
                    "**Depends on:** M1-T04 · **Parallel:** G2 · **Writes:** src/quant/data/universe.py,")
        self.assertEqual({m.split(" with")[0] for m in self.messages("writes")},
                         {"M1-T12 and M1-T03 both write src/quant/data/universe.py",
                          "M1-T12 and M1-T10 both write src/quant/data/universe.py"})
        self.assertEqual(len(self.messages("deprecated")), 2)

    def test_writes_folder_glob_overlaps(self):
        self.p.edit(PLAN, "**Writes:** src/quant/stats/rmt.py, tests/unit/quant/test_rmt.py\n\n### M1-T06",
                    "**Writes:** src/quant/stats/**, tests/unit/quant/test_rmt.py\n\n### M1-T06")
        conflicts = {m.split(" both")[0] for m in self.messages("writes")}
        self.assertEqual(conflicts, {"M1-T05 and M1-T04", "M1-T06 and M1-T05", "M1-T07 and M1-T05",
                                     "M1-T12 and M1-T05", "M1-T13 and M1-T05"})

    def test_shared_file_belongs_to_interface_or_wiring(self):
        self.p.edit(PLAN, "**Writes:** src/quant/stats/rmt.py, tests/unit/quant/test_rmt.py\n\n### M1-T06",
                    "**Writes:** src/quant/stats/rmt.py, src/quant/stats/types.py\n\n### M1-T06")
        self.assertIn("M1-T05 (spine) writes the shared file src/quant/stats/types.py: only the interface task may",
                      self.messages("writes"))

    def test_entry_module_belongs_to_wiring(self):
        self.p.edit(PLAN, "**Writes:** src/quant/stats/pca.py, tests/intent/quant/test_pca.py",
                    "**Writes:** src/quant/stats/pipeline.py")
        self.assertIn("M1-T13 (thicken) writes the shared file src/quant/stats/pipeline.py: only an interface, wiring "
                      "or system task may", self.messages("writes"))

    def test_depends_on_a_mitigated_edge(self):
        self.p.edit(PLAN, "**Read:** PL-02, stats.Cov, stats.clean_eigen\n**Acceptance:**\n- [ ] `clean_eigen` returns its "
                    "input on the stats.Cov sample; signature unchanged\n**Verify:** `pytest tests/unit/quant -k "
                    "clean_eigen` · `scripts/check.sh gate`\n**Depends on:** M1-T01",
                    "**Read:** PL-02, stats.Cov, stats.clean_eigen\n**Acceptance:**\n- [ ] `clean_eigen` returns its "
                    "input on the stats.Cov sample; signature unchanged\n**Verify:** `pytest tests/unit/quant -k "
                    "clean_eigen` · `scripts/check.sh gate`\n**Depends on:** M1-T01, M1-T04")
        self.assertEqual(self.messages("edges"), [
            "M1-T05 depends on M1-T04, but its graph row is mitigated by stats.Cov sample (M1-T01): a mitigated "
            "edge doesn't order, drop the dependency"])

    def test_missing_graph_row(self):
        self.p.edit(PLAN, "| M1-T10 delisting universe | M1-T03 apply_universe spine | code | none: thickens the same module |\n", "")
        self.assertEqual(self.messages("edges"),
                         ["M1-T10 depends on M1-T03 with no graph row saying why (kind, `none: <reason>`)"])

    def test_dependency_on_the_interface_task_needs_no_row(self):
        self.assertNotIn("M1-T02 depends on M1-T01", " ".join(self.messages("edges")))

    def test_no_graph_section(self):
        text = self.p.read(PLAN)
        self.p.write(PLAN, text[:text.index("## Dependency graph")] + text[text.index("## Risks"):])
        msgs = self.messages("edges")
        self.assertEqual(len(msgs), 16)
        self.assertIn("M1-T08 depends on M1-T02 with no ## Dependency graph section saying why (kind, `none: <reason>`)", msgs)

    def test_none_without_reason(self):
        self.p.edit(PLAN, "| M1-T13 PCA check | M1-T06 pca spine | code | none: thickens the same module |",
                    "| M1-T13 PCA check | M1-T06 pca spine | code | none |")
        self.assertEqual(self.messages("edges"), ["graph row M1-T13 → M1-T06 is `none` with no reason (`none: <why>`)"])

    def test_bad_edge_kind(self):
        self.p.edit(PLAN, "| M1-T13 PCA check | M1-T06 pca spine | code |", "| M1-T13 PCA check | M1-T06 pca spine | blocks |")
        self.assertEqual(self.messages("edges"), [
            "graph row M1-T13 → M1-T06: Kind 'blocks' must be one of data, call, file, code, contract-change, order"])

    def test_mitigation_the_interface_task_does_not_produce(self):
        self.p.edit(PLAN, "stats.Cov, stats.Factors, stats.CovReport, data.load_prices", "stats.Cov, stats.CovReport, data.load_prices")
        self.assertEqual(self.messages("edges"), [
            "graph row M1-T07 → M1-T06: stats.Factors isn't frozen by an interface task (not in its Read: or a "
            "tests/contracts/ folder it Writes)"])

    def test_mitigation_from_a_contracts_folder_in_writes(self):
        self.p.edit(PLAN, "stats.Cov, stats.Factors, stats.CovReport, data.load_prices", "stats.Cov, stats.CovReport, data.load_prices")
        self.p.edit(PLAN, "src/quant/stats/**, tests/contracts/**",
                    "src/quant/stats/**, tests/contracts/stats.Factors/sample.json, tests/contracts/**")
        self.assertEqual(self.messages("edges"), [])

    def test_mitigation_names_no_interface(self):
        self.p.edit(PLAN, "| data | stats.Factors sample (M1-T01) |", "| data | a sample (M1-T01) |")
        self.assertEqual(self.messages("edges"), [
            "graph row M1-T07 → M1-T06: mitigation names no interface (`pkg.Symbol sample|fake`)"])

    def test_edge_to_a_code_task_when_an_interface_exists(self):
        self.p.edit(PLAN, "| data | stats.Cov sample (M1-T01) |\n| M1-T06", "| data | none: wants the real covariance |\n| M1-T06")
        self.p.edit(PLAN, "clean_eigen` · `scripts/check.sh gate`\n**Depends on:** M1-T01",
                    "clean_eigen` · `scripts/check.sh gate`\n**Depends on:** M1-T01, M1-T04")
        self.assertEqual(self.messages("edges"), [
            "M1-T05 waits on code task M1-T04 across stats.Cov, which an interface task freezes: mitigate the edge "
            "and drop the dependency"])

    def test_call_edge_covered_by_a_fake(self):
        self.p.edit(PLAN, "| call | data.load_prices fake (M1-T01) |", "| call | none: needs PL-01 |")
        self.p.edit(PLAN, "**Depends on:** M1-T04, M1-T05, M1-T06, M1-T07", "**Depends on:** M1-T04, M1-T05, M1-T06, M1-T07, M1-T08")
        self.assertEqual(self.messages("edges"), [
            "M1-T09 waits on code task M1-T08 across data.load_prices, which an interface task freezes: mitigate "
            "the edge and drop the dependency"])

    def test_milestone_size_ignores_mitigated_edges(self):
        # Fourteen tasks, but the critical path is four: the mitigated edges don't order anything.
        self.assertEqual(self.messages("milestone-size"), [])

    def test_wiring_needs_smoke_spine_and_thicken_do_not(self):
        self.p.edit(PLAN, "**Verify:** `python -m quant.data load --smoke` · `scripts/check.sh gate`\n**Depends on:** M1-T02",
                    "**Verify:** `scripts/check.sh gate`\n**Depends on:** M1-T02")
        self.assertEqual(self.messages("verify-smoke"),
                         ["M1-T08 Verify lacks PL-01's smoke command `python -m quant.data load --smoke`"])

    def test_thicken_after_the_wiring_needs_smoke(self):
        # Smoke is due once a task's Depends on reaches its pipeline's wiring task.
        self.p.edit(PLAN, "**Depends on:** M1-T06 · **Writes:**", "**Depends on:** M1-T06, M1-T09 · **Writes:**")
        self.assertEqual(self.messages("verify-smoke"),
                         ["M1-T13 Verify lacks PL-02's smoke command `python -m quant.stats cov-report --smoke`"])
        self.p.edit(PLAN, "**Depends on:** M1-T06, M1-T09", "**Depends on:** M1-T06, M1-T08")    # PL-01's wiring
        self.assertEqual(self.messages("verify-smoke"), [])

    def test_files_likely_in_an_interface_first_plan(self):
        self.p.edit(PLAN, "**Depends on:** M1-T06 · **Writes:**", "**Depends on:** M1-T06 · **Files likely:**")
        self.assertEqual(self.messages("task-fields"), ["M1-T13 missing Writes"])
        self.assertEqual(self.messages("deprecated"),
                         ["M1-T13 **Files likely:** is deprecated: use **Writes:**, the task's exclusive claim"])


class StepIoTypes(LintCase):
    def messages(self):
        return [(p.severity, p.message) for p in self.problems() if p.code == "step-io-types"]

    def test_unknown_type(self):
        self.p.edit(PIPES, "| Cov → Factors |", "| Cov → Loadings |")
        self.assertEqual(self.messages(), [("E", "PL-02 step `pca` names Loadings, which no contract.md type section "
                                                 "defines (`### <component>.Loadings: type`)")])

    def test_routed_type_is_a_warning(self):
        # A type pipeline-design routed to architecture-design waits for that Revise: W until it lands, E once ticked.
        self.p.edit(PIPES, "| Cov → Factors |", "| Cov → Loadings |")
        self.p.write("docs/routes.md", "# Routed changes\n\n- [ ] architecture-design · add stats.Loadings, the "
                     "factor loadings PL-02.pca returns (from pipeline-design, 2026-10-18)\n")
        self.assertEqual(self.messages(), [("W", "PL-02 step `pca` names Loadings, which no contract.md type section "
                                                 "defines (`### <component>.Loadings: type`); routed, waiting for its "
                                                 "owner's Revise")])
        self.p.edit("docs/routes.md", "- [ ]", "- [x]")
        self.assertEqual([sev for sev, _ in self.messages()], ["E"])

    def test_qualified_type_resolves(self):
        self.p.edit(PIPES, "| Cov → Factors |", "| stats.Cov → quant.stats.Factors |")
        self.assertEqual(self.messages(), [])

    def test_every_out_names_a_type(self):
        self.p.edit(PIPES, "| dates → RawPrices |", "| dates → raw rows |")
        self.p.edit(PIPES, "| RawPrices, dates → Prices |", "| raw rows, dates → Prices |")
        self.assertEqual(self.messages(), [("E", "PL-01 step `read_raw`: its Out names no contract type")])

    def test_entry_arguments_may_stay_plain(self):
        self.p.edit(PIPES, "| RawPrices, dates → Prices |", "| RawPrices, dates, a universe file → Prices |")
        self.assertEqual(self.messages(), [])

    def test_project_without_types_gets_warnings(self):
        text = self.p.read(CONTRACT)
        self.p.write(CONTRACT, text.replace(": type\n", ": A shape\n"))
        found = self.messages()
        self.assertTrue(found and {sev for sev, _ in found} == {"W"}, found)


class TypeCases(LintCase):
    COV_BOUNDARY = "- **Boundary:** stats, portfolio · **Fixtures:** tests/contracts/stats.Cov/ · **Cases:** a 2×2 covariance\n"

    def messages(self):
        return [(p.severity, p.line, p.message) for p in self.problems() if p.code == "type-cases"]

    def test_type_crossing_step_owners_needs_a_case(self):
        # stats.Cov passes from stats' estimate_cov to portfolio's min_variance (PL-03).
        self.p.edit(CONTRACT, self.COV_BOUNDARY, "- **Boundary:** stats, portfolio · **Fixtures:** tests/contracts/stats.Cov/\n")
        line = self.p.read(CONTRACT).splitlines().index("### stats.Cov: type") + 1
        self.assertEqual(self.messages(), [
            ("E", line, "stats.Cov crosses step owners (steps of portfolio, stats pass it) but names no case: add "
                        "`**Cases:** <the payloads a sample must show>` to its `- **Boundary:** … · **Fixtures:** "
                        "tests/contracts/stats.Cov/` line")])
        self.p.edit(CONTRACT, "- **Boundary:** stats, portfolio · **Fixtures:** tests/contracts/stats.Cov/\n", "")
        self.assertEqual(len(self.messages()), 1)            # no Boundary line at all: the steps still cross

    def test_one_owner_needs_no_case(self):
        # portfolio.Weights passes between two portfolio steps only.
        self.assertEqual(self.messages(), [])
        self.p.edit(CONTRACT, "`@dataclass(frozen=True) class Weights: values: np.ndarray; tickers: tuple[str, ...]`\n",
                    "`@dataclass(frozen=True) class Weights: values: np.ndarray; tickers: tuple[str, ...]`\n"
                    "- **Boundary:** report · **Fixtures:** tests/contracts/portfolio.Weights/\n")
        self.assertEqual([m[2].split(" but ")[0] for m in self.messages()],
                         ["portfolio.Weights crosses step owners (its Boundary names report)"])

    def test_cases_none_is_no_case(self):
        self.p.edit(CONTRACT, "**Cases:** a 2×2 covariance", "**Cases:** —")
        self.assertEqual([m[2].split()[0] for m in self.messages()], ["stats.Cov"])

    def test_project_without_cases_gets_warnings(self):
        text = self.p.read(CONTRACT)
        self.p.write(CONTRACT, "\n".join(line.split(" · **Cases:**")[0] for line in text.splitlines()) + "\n")
        found = self.messages()
        self.assertTrue(found and {sev for sev, _, _ in found} == {"W"}, found)


class TaskRefs(LintCase):
    def messages(self):
        return [(p.line, p.message) for p in self.problems() if p.code == "task-ref"]

    def test_stale_task_in_acceptance(self):
        old = "- [ ] Both smoke commands pass; TC-01–TC-03 pass"
        self.p.edit(PLAN, old, "- [ ] Both smoke commands pass on the version T41 built; M1-T05 and T09 stay green")
        line = self.p.read(PLAN).splitlines().index(
            "- [ ] Both smoke commands pass on the version T41 built; M1-T05 and T09 stay green") + 1
        self.assertEqual(self.messages(), [(line, "M1-T14 Acceptance names M1-T41, which isn't a task")])
        self.p.edit(PLAN, "the version T41 built", "the version M2-T03 built")
        self.assertEqual([m[1] for m in self.messages()], ["M1-T14 Acceptance names M2-T03, which isn't a task"])

    def test_stale_task_in_graph_reason(self):
        old = "| none: swaps the fake for the real PL-01 |"
        self.p.edit(PLAN, old, "| none: swaps the fake for the real PL-01 that T41 built |")
        self.assertEqual([m[1] for m in self.messages()],
                         ["graph row M1-T14 → M1-T08 names M1-T41, which isn't a task"])

    def test_tasks_of_the_plan_resolve(self):
        self.p.edit(PLAN, "| none: swaps the fake for the real PL-01 |", "| none: swaps the fake for the real PL-01 (T08) |")
        self.assertEqual(self.messages(), [])


class PlanChecks(LintCase):
    def test_todo_mismatch(self):
        self.p.edit(TODO, "- [ ] M1-T13 Planted-factor PCA check (quant, XS, split)", "- [ ] M1-T19 Extra (quant, XS, split)")
        self.assertEqual({(p.path, p.code) for p in self.problems()}, {(PLAN, "todo-mismatch"), (TODO, "todo-mismatch")})

    def test_finding_disposition(self):
        self.p.edit(PLAN, "## Phase 3: System", "**Findings:**\n- M1-R01 Critical · CR-21 · rmt.py complexity 14 → fix "
                    "task M1-T11\n- M1-R02 Nit · naming\n\n## Phase 3: System")
        msgs = [p.message for p in self.problems() if p.code == "finding-disposition"]
        self.assertEqual(len(msgs), 1)
        self.assertTrue(msgs[0].startswith("M1-R02"))

    def test_step_unplanned(self):
        # iteration 10 D7: a step added to a milestone pipeline after the plan, on no task and not Deferred by name.
        self.p.edit(PIPES, "| 5 | `write_report` | stats | Factors → CovReport | print table | STAT-04 |",
                    "| 5 | `write_report` | stats | Factors → CovReport | print table | STAT-04 |\n"
                    "| 6 | `plot_spectrum` | stats | Factors → Figure | no plot | — |")
        msgs = [(p.path, p.line, p.message) for p in self.problems() if p.code == "step-unplanned"]
        self.assertEqual(msgs, [(PLAN, 7, "PL-02 steps on no task and not Deferred by name: plot_spectrum: give each "
                                         "a task, or defer it (`PL-02.plot_spectrum (to M<n>: why)`)")])
        self.assertEqual(lint.SEVERITY["step-unplanned"], "W")
        self.p.edit(PLAN, "**Deferred:** none", "**Deferred:** PL-02.plot_spectrum (to M2: the report comes first)")
        self.assertEqual([p for p in self.problems() if p.code == "step-unplanned"], [])

    BARRIER = ("### Checkpoint after M1-T01 (barrier)\n- [x] Every frozen type and signature matches contract.md; "
               "no test pins a stub\n\n")

    def test_interface_barrier(self):
        # Contract-gap proposal 2: an interface task followed straight by a non-interface task needs a checkpoint.
        self.assertEqual([p for p in self.problems() if p.code == "interface-barrier"], [])
        self.p.edit(PLAN, self.BARRIER, "")
        got = [(p.path, p.line, p.severity, p.message) for p in self.problems() if p.code == "interface-barrier"]
        self.assertEqual(got, [(PLAN, 12, "W", "M1-T01 (interface) is followed by M1-T02 with no checkpoint between: "
                                              "add `### Checkpoint after M1-T01 (barrier)` so the interface is "
                                              "reviewed before it is built on")])
        # A second interface task straight after the first needs none between them; the last one does.
        self.p.edit(PLAN, "**Step:** PL-01.read_raw · **Kind:** spine", "**Step:** PL-01.read_raw · **Kind:** interface")
        got = [p.message.split(" ")[0] for p in self.problems() if p.code == "interface-barrier"]
        self.assertEqual(got, ["M1-T02"])

    def test_foreign_plan(self):
        self.p.write(PLAN, "# Plan\n\n## Tasks\n- [ ] Task 1: do the thing and the other thing\n")
        self.assertEqual({(p.path, p.code, p.severity) for p in self.problems()}, {(PLAN, "foreign-plan", "W")})


class FormatChecks(LintCase):
    def test_unclosed_fence(self):
        self.p.edit(ARCH, "tests/\n```", "tests/\n")
        self.assertCode(ARCH, "broken-fence")

    def test_fence_holding_a_heading(self):
        self.p.edit(ARCH, "## Interfaces", "```\nsrc/\n## Interfaces")
        self.p.edit(ARCH, "## Decisions", "```\n## Decisions")
        self.assertCode(ARCH, "broken-fence")

    def test_markdown_fence_may_hold_headings(self):
        self.p.edit(ARCH, "## Interfaces", "````markdown\n## Example\n````\n\n## Interfaces")
        self.assertClean()

    def test_missing_header(self):
        self.p.edit(SPEC, "**Status:** Approved · **Last updated:** 2026-10-15 · **Brief:** [brief.md](brief.md)\n", "")
        self.assertCode(SPEC, "header")

    def test_header_without_status(self):
        self.p.edit(CONTRACT, "**Status:** Approved · ", "")
        self.assertCode(CONTRACT, "header")

    def test_contract_heading_naming_several_symbols(self):
        self.p.edit(CONTRACT, "### stats.clean_eigen: Random-matrix cleaning",
                    "### stats.clean_eigen / shrink, stats.ledoit_wolf: Cleaning")
        found = [p.message for p in self.problems() if p.code == "contract-heading"]
        self.assertEqual(found, ["heading names 3 symbols (stats.clean_eigen, shrink, stats.ledoit_wolf): "
                                 "give each its own `### <pkg>.<symbol>: <title>` section"])

    def test_contract_heading_without_title(self):
        self.p.edit(CONTRACT, "### stats.clean_eigen: Random-matrix cleaning", "### stats.clean_eigen")
        self.assertCode(CONTRACT, "contract-heading")

    def test_contract_heading_check_is_contract_only(self):
        self.p.edit(ARCH, "## Interfaces", "### stats.a / stats.b: Two\n\n## Interfaces")
        self.assertNotIn((ARCH, "contract-heading"), self.found())

    def test_roadmap_and_todo_need_no_status(self):
        self.assertNotIn(("docs/roadmap.md", "header"), self.found())
        self.assertNotIn((TODO, "header"), self.found())

    def test_unreadable(self):
        self.p.path("docs/ideas/bad.md").write_bytes(b"# Bad\n\xff\xfe\n")
        self.assertCode("docs/ideas/bad.md", "unreadable")

    def test_crashing_check_becomes_internal_warning(self):
        def boom(ctx):
            raise RuntimeError("bug")
            yield
        with mock.patch.object(lint, "CHECKS", [boom] + lint.CHECKS):
            problems = self.problems()
        self.assertEqual([(p.code, p.severity) for p in problems], [("internal", "W")])


class Scope(LintCase):
    def test_paths_report_only_their_files_with_cross_doc_checks(self):
        self.p.edit(TODO, "- [ ] M1-T09", "- [x] M1-T09")           # makes PL-02's sketch leftover
        self.p.edit(SPEC, "**Status:** Approved · ", "")             # header problem elsewhere
        self.assertEqual(self.found({PIPES}), {(PIPES, "prebuild-left")})
        self.assertEqual(self.found({TODO}), set())

    def test_cli_paths_and_folders(self):
        self.p.edit(SPEC, "**Status:** Approved · ", "")
        code, out = run_main("--root", str(self.p.root), "lint", str(self.p.path(SPEC)))
        self.assertEqual(code, 1)
        self.assertIn("docs/spec.md:3: header", out)
        code, _ = run_main("--root", str(self.p.root), "lint", "tasks")
        self.assertEqual(code, 0)
        code, out = run_main("--root", str(self.p.root), "lint", "docs")
        self.assertEqual(code, 1)
        code, out = run_main("--root", str(self.p.root), "lint", "docs/packages/")   # a folder: every doc under it
        self.assertEqual(code, 0)
        self.p.edit(CONTRACT, "**Status:** Approved · ", "")
        code, out = run_main("--root", str(self.p.root), "lint", "docs/packages")
        self.assertEqual((code, out.splitlines()[0]), (1, "docs/packages/quant/contract.md:3: header no **Status:** in the header line"))


@unittest.skipUnless(HAS_GIT, "git not installed")
class Changed(LintCase):
    git = True

    def test_changed_vs_head(self):
        self.p.edit(SPEC, "**Status:** Approved · ", "")
        self.p.write("docs/ideas/new.md", "# New\n\n```\nunclosed\n")
        code, out = run_main("--root", str(self.p.root), "lint", "--changed", "--json")
        data = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual({(x["path"], x["code"]) for x in data["problems"]},
                         {(SPEC, "header"), ("docs/ideas/new.md", "header"), ("docs/ideas/new.md", "broken-fence")})

    def test_changed_outside_git_is_a_usage_error(self):
        p = Project(git=False)
        self.addCleanup(p.cleanup)
        self.assertEqual(run_main("--root", str(p.root), "lint", "--changed")[0], 2)

    def test_nothing_changed(self):
        code, out = run_main("--root", str(self.p.root), "lint", "--changed")
        self.assertEqual((code, out.strip()), (0, "0 errors, 0 warnings"))


class Hook(LintCase):
    def hook(self, event) -> tuple[int, dict | None]:
        code, out = run_main("lint", "--hook", stdin=json.dumps(event) if isinstance(event, dict) else event)
        return code, (json.loads(out) if out.strip() else None)

    def post(self, rel):
        return {"hook_event_name": "PostToolUse", "cwd": str(self.p.root),
                "tool_input": {"file_path": str(self.p.path(rel))}}

    def test_post_errors_block(self):
        self.p.edit(SPEC, "**Status:** Approved · ", "")
        code, out = self.hook(self.post(SPEC))
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "block")
        self.assertIn("docs/spec.md:3: header", out["reason"])

    def test_post_warnings_add_context(self):
        self.p.edit(CONTRACT, "- **Used by:** PL-03", "- **Used by:** PL-03\n" + "filler\n" * 40)
        code, out = self.hook(self.post(CONTRACT))
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("budget", out["hookSpecificOutput"]["additionalContext"])

    def test_post_clean_or_not_a_doc_prints_nothing(self):
        self.assertEqual(self.hook(self.post(SPEC)), (0, None))
        self.p.edit(SPEC, "**Status:** Approved · ", "")
        self.assertEqual(self.hook(self.post("src/quant/__init__.py")), (0, None))

    def test_bad_input_fails_open(self):
        self.assertEqual(self.hook("not json"), (0, None))
        self.assertEqual(self.hook({"hook_event_name": "PostToolUse"}), (0, None))

    @unittest.skipUnless(HAS_GIT, "git not installed")
    def test_stop_reports_changed_docs(self):
        p = Project(git=True)
        self.addCleanup(p.cleanup)
        p.edit(SPEC, "**Status:** Approved · ", "")
        code, out = self.hook({"hook_event_name": "Stop", "cwd": str(p.root)})
        self.assertEqual(code, 0)
        self.assertTrue(out["systemMessage"].startswith("dt lint: 1 problem\n"))
        self.assertNotIn("decision", out)


class PacketTypeClosure(LintCase):
    """`packet-type-closure`: a name contract signatures use that no section defines (and no library does)."""
    LOAD = "`def load_prices(universe: tuple[str, ...], start: date, end: date) -> Prices`"

    def messages(self):
        return [(p.path, p.line, p.severity, p.message) for p in self.problems() if p.code == "packet-type-closure"]

    def test_undefined_name_is_reported_once_per_doc(self):
        self.p.edit(CONTRACT, self.LOAD, self.LOAD.replace("tuple[str, ...]", "Universe"))
        self.p.edit(CONTRACT, "`def min_variance(cov: Cov) -> Weights`", "`def min_variance(cov: Cov, u: Universe) -> Weights`")
        self.assertEqual(self.messages(), [(CONTRACT, 19, "W", "Universe (named by data.load_prices, "
                                            "portfolio.min_variance) has no contract section, so no packet shows it: "
                                            "add a `### data.Universe: type` section (or a `class Universe(…)` line in "
                                            "one), or qualify a library type (`pd.DataFrame`)")])

    def test_preamble_alias_is_reported(self):
        self.p.edit(CONTRACT, self.LOAD, self.LOAD.replace("tuple[str, ...]", "Universe"))
        self.p.edit(CONTRACT, "## data\n", "`Universe = tuple[str, ...]` is used throughout.\n\n## data\n")
        [(_, _, _, msg)] = self.messages()
        self.assertIn("Universe (named by data.load_prices) is defined outside any section "
                      "(docs/packages/quant/contract.md:5), so no packet shows it", msg)

    def test_a_section_or_an_inline_definition_closes_it(self):
        self.p.edit(CONTRACT, self.LOAD, self.LOAD.replace("tuple[str, ...]", "Universe"))
        self.p.edit(CONTRACT, "### data.load_prices:", "### data.Universe: type\n`Universe = tuple[str, ...]`\n"
                    "- **Used by:** PL-01\n\n### data.load_prices:")
        self.assertEqual(self.messages(), [])
        self.p.edit(CONTRACT, "### data.Universe: type\n`Universe = tuple[str, ...]`",
                    "### data.Calendar: type\n`Calendar = tuple[date, ...]; class Universe(tuple)`")
        self.assertEqual(self.messages(), [])

    def test_library_names_strings_and_comments_are_not_types(self):
        self.p.edit(CONTRACT, self.LOAD, "`def load_prices(universe: Sequence[str], start: date, end: date, *, "
                    "path: Path, mode: Literal[\"Raw\", \"Adjusted\"] = \"Raw\", rng: np.random.Generator) -> Prices  "
                    "# Prices is a DataFrame Wrapper`")
        self.assertEqual(self.messages(), [])

    def test_errors_bullet_counts_other_bullets_do_not(self):
        self.p.edit(CONTRACT, "- **Errors:** `KeyError` for an unknown ticker", "- **Errors:** `UnknownTicker` for an unknown ticker")
        self.p.edit(CONTRACT, "- **Invariants:** T×N; a name", "- **Invariants:** `Panel` T×N; a name")
        self.assertEqual([m[3].split(" (")[0] for m in self.messages()], ["UnknownTicker"])


class ParallelStep(LintCase):
    """`parallel-step`: two thicken tasks on one step with no Depends on path between them."""

    def messages(self):
        return [(p.line, p.severity, p.message) for p in self.problems() if p.code == "parallel-step"]

    def test_two_thickens_of_one_step_in_parallel(self):
        self.p.edit(PLAN, "**Step:** PL-02.pca · **Kind:** thicken", "**Step:** PL-02.estimate_cov · **Kind:** thicken")
        self.assertEqual(self.messages(), [(123, "W", "M1-T13 and M1-T12 both thicken PL-02.estimate_cov with no Depends "
                                                      "on path between them: the step's code is one function, so order "
                                                      "them (a `code` graph row) or fold one into the other")])

    def test_ordered_thickens_are_fine(self):
        self.p.edit(PLAN, "**Step:** PL-02.pca · **Kind:** thicken", "**Step:** PL-02.estimate_cov · **Kind:** thicken")
        self.p.edit(PLAN, "**Depends on:** M1-T06 · **Writes:** src/quant/stats/pca.py",
                    "**Depends on:** M1-T06, M1-T12 · **Writes:** src/quant/stats/pca.py")
        self.assertEqual(self.messages(), [])


class SpineClaim(LintCase):
    """`spine-claim`: a spine's Reason claims a contract function no step owns, and the task writes outside its
    step's owner (iteration 9's rl all-at-once: M1-T08 built `methods.make_learner` in `methods/factory.py`)."""
    T02 = "**Depends on:** M1-T01 · **Writes:** src/quant/data/raw.py, tests/unit/quant/test_raw.py"

    def setUp(self):
        super().setUp()
        self.p.edit(CONTRACT, "### stats.clean_eigen:", "### stats.shrink: Shrinkage target\n"
                    "`def shrink(cov: Cov) -> Cov`\n- **Used by:** PL-02\n\n### stats.clean_eigen:")
        self.p.edit(PLAN, "**Read:** PL-01, data.RawPrices, DATA-01",
                    "**Reason:** also builds `stats.shrink`, which read_raw's tests need\n"
                    "**Read:** PL-01, data.RawPrices, DATA-01")

    def messages(self):
        return [(p.line, p.severity, p.message) for p in self.problems() if p.code == "spine-claim"]

    def test_claimed_function_written_outside_the_owner(self):
        self.p.edit(PLAN, self.T02, self.T02.replace("raw.py,", "raw.py, src/quant/stats/shrink.py,"))
        self.assertEqual(self.messages(), [(29, "W", "M1-T02 (spine on data) claims stats.shrink in its Reason, which "
                                                    "no pipeline step owns, and writes src/quant/stats/shrink.py "
                                                    "outside its step's owner: give each its own step, or put it in "
                                                    "the step's folder owner")])

    def test_beside_the_steps_own_module_is_fine(self):
        self.assertEqual(self.messages(), [])

    def test_a_step_of_its_own_is_fine(self):
        self.p.edit(PLAN, self.T02, self.T02.replace("raw.py,", "raw.py, src/quant/stats/shrink.py,"))
        self.p.edit(PIPES, "| 3 | `clean_eigen` |", "| 3 | `shrink` | stats | Cov → Cov | identity | STAT-03 |\n"
                    "| 4 | `clean_eigen` |")
        self.assertEqual(self.messages(), [])


class MilestoneChecks(LintCase):
    """`milestone-lines` and `milestone-order` on the roadmap."""
    ROADMAP = "docs/roadmap.md"
    M2_ROW = "| M2 | Classical portfolios | ideas/classical-portfolios.md | quant | PL-03 | M1 | Designed |"

    def messages(self, code):
        return [(p.line, p.message) for p in self.problems() if p.code == code]

    def staged(self, m2_section: str):
        """The staged roadmap with S1 cut into M1 and M2 (Designed: PL-02's pipelines.md is Approved)."""
        from test_roadmap import STAGED
        text = STAGED.read_text(encoding="utf-8").replace(
            "| — | Building |\n", "| — | Building |\n| M2 | S1 | Shrinkage | quant | PL-02 | M1 | Designed |\n")
        self.p.write(self.ROADMAP, text.replace("**Plan:** [../tasks/plan.md](../tasks/plan.md)\n",
                                                "**Skills:** data-science\n**References:** —\n"
                                                "**Plan:** [../tasks/plan.md](../tasks/plan.md)\n\n" + m2_section))

    def test_fixture_roadmap_is_clean(self):
        self.assertEqual(self.messages("milestone-lines") + self.messages("milestone-order"), [])

    def test_designed_milestone_without_exit(self):
        self.p.edit(self.ROADMAP, "**Exit:** Min-var beats equal weight on out-of-sample variance.", "**Outline:** Min-var.")
        self.assertEqual(self.messages("milestone-lines"), [(17, "M2 has no **Exit:** line (Designed)")])

    def test_cut_stage_needs_skills_and_references(self):
        self.staged("## M2: Shrinkage\n**Outline:** Shrinkage beats the sample estimate.\n")
        self.assertEqual(self.messages("milestone-lines"), [
            (31, "M2 has no **Exit:** line (Designed); no **Skills:** or **References:** line (S1 is cut into 2 "
                 "milestones)")])

    def test_cut_stage_with_every_line_is_clean(self):
        self.staged("## M2: Shrinkage\n**Outline:** Shrinkage.\n**Skills:** —\n**References:** —\n**Exit:** TC-02 passes.\n")
        self.assertEqual(self.messages("milestone-lines"), [])

    def test_designed_milestone_without_a_section(self):
        text = self.p.read(self.ROADMAP)
        self.p.write(self.ROADMAP, text[:text.index("## M2:")])
        self.assertEqual(self.messages("milestone-lines"), [(8, "M2 (Designed) has no `## M2: <name>` section")])

    def test_rows_out_of_build_order(self):
        row1 = "| M1 | Data + stats | brief | quant | PL-01, PL-02 | — | Building |"
        self.p.edit(self.ROADMAP, row1 + "\n" + self.M2_ROW, self.M2_ROW.replace("| M1 |", "| — |") + "\n" + row1)
        self.assertEqual(self.messages("milestone-order"), [
            (8, "M1 comes after M2 in the table: rows run in build order, so renumber the milestones that have no "
                "plan yet")])

    def test_depends_on_a_later_milestone(self):
        self.p.edit(self.ROADMAP, self.M2_ROW, self.M2_ROW.replace("| M1 |", "| M1, M3 (its prices) |")
                    + "\n| M3 | Later | ideas/classical-portfolios.md | quant | PL-03 | — | Designed |")
        self.assertEqual(self.messages("milestone-order"), [
            (8, "M2 depends on M3, not an earlier milestone: renumber so a milestone comes after those it needs")])


class ScopeAndTitleChecks(LintCase):
    """`exit-cases-in-scope`, `kind-title` and `covers-vs-deferred`."""
    ROADMAP = "docs/roadmap.md"

    def messages(self, code):
        return [(p.path, p.line, p.severity, p.message) for p in self.problems() if p.code == code]

    def test_fixture_is_clean(self):
        for code in ("exit-cases-in-scope", "kind-title", "covers-vs-deferred"):
            self.assertEqual(self.messages(code), [])

    def test_exit_range_with_a_gap(self):
        self.p.edit(PLAN, "**Exit:** PCA and MP cleaning run on 10y of daily returns; TC-01–TC-03 pass.",
                    "**Exit:** PCA and MP cleaning run on 10y of daily returns; TC-01–TC-05 pass.")
        self.assertEqual(self.messages("exit-cases-in-scope"), [
            (PLAN, 6, "E", "M1's Exit names TC-04, TC-05, which no tests.md defines (a gap in a range?)")])

    def test_exit_case_of_another_milestones_pipeline(self):
        self.p.edit(self.ROADMAP, "**Exit:** Min-var beats equal weight on out-of-sample variance.",
                    "**Exit:** Min-var beats equal weight on out-of-sample variance; TC-02 still passes.")
        self.assertEqual(self.messages("exit-cases-in-scope"), [
            (self.ROADMAP, 18, "E", "M2's Exit names TC-02 of PL-02, which isn't in M2's Pipelines")])

    def test_title_names_another_kind(self):
        self.p.edit(PLAN, "### M1-T10: Delisting-aware universe", "### M1-T10: Delisting-aware universe spine")
        self.assertEqual(self.messages("kind-title"), [
            (PLAN, 95, "E", "M1-T10 title says 'spine' but its Kind is thicken: retitle it or fix the Kind")])

    def test_title_naming_its_own_kind_is_fine(self):
        self.p.edit(PLAN, "### M1-T10: Delisting-aware universe", "### M1-T10: Delisting-aware universe (thicken)")
        self.assertEqual(self.messages("kind-title"), [])

    def test_covers_a_deferred_id(self):
        self.p.edit(PLAN, "**Deferred:** none", "**Deferred:** STAT-04 (to M2: the report waits for portfolios)")
        self.assertEqual(self.messages("covers-vs-deferred"), [
            (PLAN, 7, "E", "Scope Covers and Deferred both list STAT-04: pick one"),
            (PLAN, 68, "E", "M1-T07 covers STAT-04, which the plan's Scope defers: drop it from the task, or from "
                            "Deferred")])

    def test_covers_another_steps_requirement(self):
        self.p.edit(PLAN, "**Step:** PL-02.pca · **Kind:** thicken · **Covers:** STAT-01, QR-01",
                    "**Step:** PL-02.pca · **Kind:** thicken · **Covers:** STAT-01, STAT-03, QR-01")
        self.assertEqual(self.messages("covers-vs-deferred"), [
            (PLAN, 124, "W", "M1-T13 covers STAT-03, which the Covers cells of PL-02.clean_eigen list, not "
                             "PL-02.pca's: cover what the step delivers, or route the step table to pipeline-design")])


class NarrationChecks(LintCase):
    """`closed-open-question` (a warning) and `process-narration` (an error, a warning for wording that can also
    state a fact)."""
    ROUTES = "docs/routes.md"
    QUESTION = "- Should `clean_eigen` take T from Returns instead of a parameter? (assumed: parameter)"

    def messages(self, code):
        return [(p.path, p.line, p.message) for p in self.problems() if p.code == code]

    def severities(self, code):
        return [(p.line, p.severity, p.message.split("'")[1]) for p in self.problems() if p.code == code]

    def route(self, box: str):
        self.p.write(self.ROUTES, "# Routed changes\n\nWritten by `dt route`.\n\n"
                     f"- [{box}] architecture-design · stats: clean_eigen takes n_obs (from pipeline-design, 2026-10-16)\n")
        self.p.edit(PIPES, self.QUESTION, self.QUESTION + " (routed to `architecture-design`)")

    def test_question_routed_to_a_closed_revise(self):
        self.route("x")
        self.assertEqual(self.messages("closed-open-question"), [
            (PIPES, 61, "routed to architecture-design, whose routed changes are all done (docs/routes.md): drop "
                        "the question or say what is still open")])

    def test_question_routed_to_an_open_revise(self):
        self.route(" ")
        self.assertEqual(self.messages("closed-open-question"), [])

    def test_narration(self):
        self.p.edit(ARCH, "- **Decision:** Parquet via pyarrow.",
                    "- **Decision:** Parquet via pyarrow, revised 2026-10-18; TC-01–TC-03 don't change.")
        self.p.edit(ARCH, "## Risks and open questions", "## Replan notes\n- moved\n\n## Risks and open questions")
        self.assertEqual(self.messages("process-narration"), [
            (ARCH, 44, "'revised 2026-10-18' narrates history: state what holds now (the Changelog holds what changed, "
                       "docs/routes.md what goes back)"),
            (ARCH, 48, "a `## Replan notes` section outside a plan: the doc states what holds, the Changelog what "
                       "changed")])

    def test_what_narration_leaves_alone(self):
        self.p.edit(ARCH, "- **Consequences:** Binary files; needs pyarrow.",
                    "- **Consequences:** Binary files; the stored values don't change on read; approved by the user "
                    "before M1 merges.")
        self.p.edit("docs/packages/quant/tests.md", "(given 2026-10-15)", "(confirmed by the user 2026-10-15)")
        self.p.edit(PLAN, "## Replan notes\n", "## Replan notes\n- 2026-10-16: AD-03 adopted before M1 is built\n")
        self.assertEqual(self.messages("process-narration"), [])

    def test_stale_process_text_fails(self):
        """The phrases iteration 11's judges quoted are errors; "previously" stays a warning."""
        self.p.edit(ARCH, "- **Decision:** Parquet via pyarrow.",
                    "- **Decision:** Parquet via pyarrow. Nothing is built yet (M1 has 0 of 22 tasks done).")
        self.p.edit(ARCH, "- **Consequences:** Binary files; needs pyarrow.",
                    "- **Consequences:** Binary files. Docs to rework: the build waits for pipeline-design.")
        self.p.edit(ARCH, "## Risks and open questions",
                    "With the table as it stood, M1-T03 would fail CR-04. The user chose to add it.\n"
                    "The format was previously CSV.\n\n## Risks and open questions")
        self.assertEqual(self.severities("process-narration"), [
            (44, "E", "Nothing is built"), (46, "E", "Docs to rework"), (48, "E", "With the table as it stood"),
            (49, "W", "previously")])
        self.assertEqual([p.code for p in self.problems() if p.severity == "E"], ["process-narration"] * 3)

    def test_user_choice_with_its_request_passes(self):
        self.p.edit(ARCH, "- **Decision:** Parquet via pyarrow.",
                    "- **Decision:** Parquet via pyarrow; the user chose it (UR-04).")
        self.assertEqual(self.messages("process-narration"), [])
        self.p.edit(ARCH, "the user chose it (UR-04)", "the user chose it")
        self.assertEqual(self.severities("process-narration"), [(44, "E", "the user chose")])

    def test_changelog_rows_and_ideas_are_exempt(self):
        self.p.edit(ARCH, "## Risks and open questions",
                    "## Changelog\n- 2026-10-18: Docs to rework; nothing is built yet\n\n## Risks and open questions")
        self.p.write("docs/ideas/x.md", "# Idea: x\n\n**Status:** Specced · **Last updated:** 2026-10-18\n\n"
                     "Nothing is built yet, and the user chose the parquet store.\n")
        self.assertEqual(self.messages("process-narration"), [])


if __name__ == "__main__":
    unittest.main()
