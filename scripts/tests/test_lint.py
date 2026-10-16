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
    """Each test mutates its own copy of the fixture and asserts which codes appear where."""
    git = False

    def setUp(self):
        self.p = Project(git=self.git)
        self.addCleanup(self.p.cleanup)

    def problems(self, scope=None):
        return lint.lint(Repo(self.p.root), scope)

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
        self._add_symbols(10)       # 93 lines, well past the old fixed 60, at 6 lines a symbol
        self.assertEqual(self.budget_messages(CONTRACT), [])
        self.p.edit(CONTRACT, "- **Used by:** PL-03", "- **Used by:** PL-03\n" + "filler\n" * 90)
        self.assertEqual(self.budget_messages(CONTRACT), ["184 lines, budget 124 (8 per symbol × 14 + 12)"])

    def test_pipelines_budget_is_per_pipeline(self):
        self.p.edit(PIPES, "**Covers:** PORT-01, PORT-02", "**Covers:** PORT-01, PORT-02\n" + "filler\n" * 70)
        self.assertEqual(self.budget_messages(PIPES), ["135 lines, budget 127 (35 per pipeline × 3 + 10 + 12 layout)"])

    def test_pipelines_layout_section_is_extra(self):
        layout = "## Planned layout (pre-build — removed by spine task)"
        self.p.edit(PIPES, layout, layout + "\n" + "- line\n" * 100)
        self.assertEqual(self.budget_messages(PIPES), [])

    def test_tests_budget_is_per_case(self):
        self.p.edit("docs/packages/quant/tests.md", "## Open questions", "filler\n" * 20 + "## Open questions")
        self.assertCode("docs/packages/quant/tests.md", "budget")

    def test_grow_ceiling_is_a_separate_warning(self):
        self._add_symbols(30)
        self.assertEqual(self.budget_messages(CONTRACT), [
            "213 lines, over the 200-line ceiling for one package's contract doc: architecture-design should "
            "consider a Grow"])
        code, _ = run_main("--root", str(self.p.root), "lint")
        self.assertEqual(code, 0)

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
    def test_entry_sketch_after_spine_checked(self):
        self.p.edit(TODO, "- [ ] M1-T02", "- [x] M1-T02")
        lines = {(p.path, p.line) for p in self.problems() if p.code == "prebuild-left"}
        self.assertEqual(lines, {(PIPES, 28)})   # Planned layout stays: PL-03 has no spine task yet

    def test_planned_layout_after_every_spine(self):
        text = self.p.read(PIPES)
        start, end = text.index("## PL-03"), text.index("## Planned layout")
        self.p.write(PIPES, text[:start] + text[end:])
        self.p.edit(TODO, "- [ ] M1-T02", "- [x] M1-T02")
        lines = {p.line for p in self.problems() if p.code == "prebuild-left"}
        self.assertEqual(len(lines), 2)

    def test_pipeline_built_in_an_earlier_milestone(self):
        # PL-03 has no spine task in the active plan: it counts as built once its entry file exists.
        self.p.edit(PIPES, "## Planned layout", "### Entry sketch (pre-build — removed by spine task)\nx\n\n## Planned layout")
        self.assertNotIn((PIPES, "prebuild-left"), self.found())
        self.p.write("src/quant/portfolio/pipeline.py", "def run_backtest(): ...\n")
        self.assertIn((PIPES, "prebuild-left"), self.found())

    def test_unchecked_spine_is_fine(self):
        self.assertNotIn((PIPES, "prebuild-left"), self.found())


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
    def test_task_size_not_xs_to_m(self):
        self.p.edit(PLAN, "**Size:** XS", "**Size:** L")
        self.assertCode(PLAN, "task-size")

    def test_task_size_files_count(self):
        self.p.edit(PLAN, "src/quant/data/steps.py, tests/unit/quant/test_universe.py",
                    "src/quant/data/steps.py, tests/unit/quant/test_universe.py, src/quant/data/x.py")
        msgs = [p.message for p in self.problems() if p.code == "task-size"]
        self.assertEqual(msgs, ["M1-T03 Size S wants 1–2 Files likely, has 3"])

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

    def test_milestone_size_counts_spine_plus_longest_chain(self):
        self._add_tasks(12, lambda k: "M1-T05" if k == 7 else f"M1-T{k - 1:02d}")
        chain = " → ".join(f"M1-T{k:02d}" for k in [4, 5] + list(range(7, 19)))
        self.assertEqual(self.size_messages(), [
            f"track is 16 tasks, cap 15: Phase 0 2 + chain {chain} (14). Shorten the chain, or split the milestone "
            "where a later part needs an earlier part's outputs; never split independent tracks"])

    def test_milestone_size_at_cap_is_fine(self):
        self._add_tasks(11, lambda k: "M1-T05" if k == 7 else f"M1-T{k - 1:02d}")
        self.assertEqual(self.size_messages(), [])

    def test_parallel_tracks_do_not_add_up(self):
        self._add_tasks(20, lambda k: "M1-T02")
        self.assertEqual(self.size_messages(), [])

    def test_parallel_shared_file(self):
        self.p.edit(PLAN, "src/quant/stats/rmt.py, tests/unit/quant/test_rmt.py", "src/quant/stats/rmt.py, src/quant/data/steps.py")
        msgs = [p.message for p in self.problems() if p.code == "parallel"]
        self.assertEqual(msgs, ["M1-T04 and M1-T03 are both in G1 but share src/quant/data/steps.py"])

    def test_parallel_shared_contract_symbol(self):
        self.p.edit(PLAN, "**Read:** PL-02, TC-02, STAT-03, stats.clean_eigen",
                    "**Read:** PL-02, TC-02, STAT-03, stats.clean_eigen, data.load_prices")
        self.assertCode(PLAN, "parallel")

    def test_parallel_different_groups_is_fine(self):
        self.p.edit(PLAN, "src/quant/stats/rmt.py, tests/unit/quant/test_rmt.py", "src/quant/stats/rmt.py, src/quant/data/steps.py")
        self.p.edit(PLAN, "**Depends on:** M1-T02 · **Parallel:** G1", "**Depends on:** M1-T02 · **Parallel:** G2")
        self.assertClean()

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


class PlanChecks(LintCase):
    def test_todo_mismatch(self):
        self.p.edit(TODO, "- [ ] M1-T06 Planted-factor PCA check (quant, XS, split)", "- [ ] M1-T09 Extra (quant, XS, split)")
        self.assertEqual({(p.path, p.code) for p in self.problems()}, {(PLAN, "todo-mismatch"), (TODO, "todo-mismatch")})

    def test_finding_disposition(self):
        self.p.edit(PLAN, "### M1-T05:", "**Findings:**\n- M1-R01 Critical · CR-21 · rmt.py complexity 14 → fix task M1-T05\n"
                    "- M1-R02 Nit · naming\n\n### M1-T05:")
        msgs = [p.message for p in self.problems() if p.code == "finding-disposition"]
        self.assertEqual(len(msgs), 1)
        self.assertTrue(msgs[0].startswith("M1-R02"))

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
        self.p.edit(TODO, "- [ ] M1-T02", "- [x] M1-T02")           # makes PL-02's sketch leftover
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


if __name__ == "__main__":
    unittest.main()
