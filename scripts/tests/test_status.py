"""dt status on copies of the quant fixture. Run: python3 -m unittest discover -s scripts/tests"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import dt  # noqa: E402
from devteam import code, specdocs  # noqa: E402
from devteam.commands import status  # noqa: E402
from devteam.status.tomlread import parse_toml  # noqa: E402

QUANT = HERE / "fixtures" / "quant"
HAS_GIT = shutil.which("git") is not None

# Keys each skill promises to print (scripts/README.md, dt status table).
KEYS = {
    "idea-refine": ["brief_words", "brief_goals", "ideas", "roadmap_rows", "references_unassigned"],
    "spec-writing": ["ideas_ready", "prefixes", "reserved_prefixes", "skills"],
    "architecture-design": ["uncovered", "changed_since", "spec_rows_pending", "stale", "package_docs",
                            "packages_found", "skills", "broken_fences", "contracts_missing", "legacy_layout",
                            "grow_triggers", "stale_contracts", "next_decision"],
    "pipeline-design": ["packages", "uncovered_ids", "components_unowned", "drift", "retired_refs", "misplaced"],
    "test-planning": ["packages", "pipelines_no_smoke", "pipelines_no_golden", "cases_no_source",
                      "cases_no_tolerance", "fixtures_missing", "fixtures_orphan", "skills"],
    "build-planning": ["milestone", "progress", "next_task", "blocked_tasks", "uncovered", "no_spine",
                       "mode_violations", "draft_pipelines", "changed_since_plan", "pipelines_inferred",
                       "milestone_references", "milestone_skills", "references_unrouted", "skills_unrouted",
                       "skills_missing", "skills_available",
                       "grow_triggers", "drift", "stale_contracts", "queued", "base"],
    "build-setup": ["constraints", "config_mismatches", "contract_mismatches", "optional_layers_existing",
                    "deptry_missing", "protected_gaps", "ignores_without_exception", "agents_missing", "hooks_missing",
                    "not_executable", "expired_exceptions", "tools_missing", "dependents", "base"],
    "reference-intake": ["index", "files_to_read", "outline_first", "next_id", "milestones"],
}
# Every skill's report also carries these (reference files waiting for reference-intake).
COMMON_KEYS = ["references_unindexed", "references_changed", "references_missing"]


def run_dt(root: Path, *args: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        rc = dt.main(["--root", str(root), *args])
    return rc, out.getvalue()


def git(root: Path, *args: str, date: str | None = None) -> None:
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "quant"
        shutil.copytree(QUANT, self.root)
        env = mock.patch.dict(os.environ)
        env.start()
        os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        self.addCleanup(env.stop)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, rel: str, old: str, new: str) -> None:
        p = self.root / rel
        text = p.read_text(encoding="utf-8")
        self.assertIn(old, text)
        p.write_text(text.replace(old, new, 1), encoding="utf-8")

    def write(self, rel: str, text: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def status(self, skill: str | None = None) -> dict:
        rc, out = run_dt(self.root, "status", *(["--skill", skill] if skill else []), "--json")
        data = json.loads(out)
        self.assertEqual(rc, 1 if data["mode"] == "blocked" else 0)
        return data


class CommonTest(Base):
    def test_common_lines(self):
        rc, out = run_dt(self.root, "status", "--skill", "build-planning")
        self.assertEqual(rc, 0)
        lines = out.splitlines()
        self.assertEqual(lines[:2], ["skill: build-planning", "mode: extend"])
        self.assertIn("docs: brief Accepted · spec Approved · architecture Approved (Single package) · roadmap ok"
                      " · plan M1 In progress", out)
        self.assertIn("next ids: AD-04 PL-05 TC-04 M3 M1-T07", out)
        self.assertNotIn("blocked:", out.replace("blocked_tasks", ""))

    def test_every_key_printed_even_when_empty(self):
        for skill, keys in KEYS.items():
            data = self.status(skill)
            for k in ["skill", "mode", "blocked", "docs", "next_ids"] + COMMON_KEYS + keys:
                self.assertIn(k, data, f"{skill}: {k}")
            _, text = run_dt(self.root, "status", "--skill", skill)
            for k in COMMON_KEYS + keys:
                self.assertRegex(text, rf"(?m)^{k}: \S", f"{skill}: {k}")

    def test_no_skill(self):
        data = self.status()
        self.assertEqual((data["skill"], data["mode"]), ("—", "—"))

    def test_roadmap_stale_shows_in_docs(self):
        self.edit("docs/roadmap.md", "| M1 | Designed |", "| M1 | Idea |")
        self.assertEqual(self.status()["docs"]["roadmap"], "stale (run dt roadmap)")

    def test_next_ad_survives_broken_fence(self):
        self.edit("docs/architecture.md", "## Decisions", "```\n## Decisions")
        self.assertEqual(self.status()["next_ids"][0], "AD-04")


class EarlySkillsTest(Base):
    def test_idea_refine(self):
        d = self.status("idea-refine")
        self.assertEqual(d["mode"], "extend")
        self.assertEqual(d["brief_goals"], 3)
        self.assertGreater(d["brief_words"], 50)
        self.assertEqual(d["ideas"], {"docs/ideas/classical-portfolios.md": "Specced"})
        self.assertEqual([r["id"] for r in d["roadmap_rows"]], ["M1", "M2"])
        (self.root / "docs/brief.md").unlink()
        self.assertEqual(self.status("idea-refine")["mode"], "new")

    def test_spec_writing(self):
        self.edit("docs/ideas/classical-portfolios.md", "Specced", "Accepted")
        d = self.status("spec-writing")
        self.assertEqual(d["mode"], "extend")
        self.assertEqual(d["ideas_ready"], ["docs/ideas/classical-portfolios.md"])
        self.assertEqual(d["prefixes"]["DATA"], {"highest": "DATA-03", "next": "DATA-04"})
        self.assertEqual(d["skills"], ["data-science"])
        (self.root / "docs/spec.md").unlink()
        self.assertEqual(self.status("spec-writing")["mode"], "new")
        (self.root / "docs/brief.md").unlink()
        d = self.status("spec-writing")
        self.assertEqual(d["mode"], "blocked")
        self.assertIn("brief", d["blocked"])


class ArchitectureTest(Base):
    def test_fixture_current(self):
        d = self.status("architecture-design")
        self.assertEqual(d["mode"], "current")
        self.assertEqual(d["spec"]["live_requirements"], 10)
        self.assertEqual(d["next_decision"], "AD-04")
        for k in ("uncovered", "changed_since", "spec_rows_pending", "stale", "broken_fences",
                  "contracts_missing", "legacy_layout", "grow_triggers"):
            self.assertEqual(d[k], [], k)

    def test_gaps(self):
        # A spec round the architecture hasn't absorbed: a new ID and a changed one.
        self.edit("docs/spec.md", "- **QR-02**", "- **QR-03** New.\n- **QR-02**")
        self.edit("docs/spec.md", "| PORT-01, PORT-02; DATA-03 (removed) |",
                  "| PORT-01, PORT-02; DATA-03 (removed) |\n| 2026-10-16 | Faster | ideas/fast.md | QR-03; STAT-02 (changed) |")
        self.edit("docs/architecture.md", "One Python package", "DATA-03 is gone. One Python package")
        self.write("docs/architecture/legacy.md", "# legacy\n\n**Package:** legacy · **Status:** Draft\n\n```\n## oops\n```\n")
        d = self.status("architecture-design")
        self.assertEqual(d["mode"], "extend")
        self.assertEqual(d["uncovered"], ["QR-03"])
        self.assertEqual(d["changed_since"], ["STAT-02"])
        self.assertEqual(d["spec_rows_pending"], ["2026-10-16 | Faster | ideas/fast.md"])
        self.assertEqual(d["stale"], ["DATA-03"])
        self.assertEqual(d["package_docs"], ["docs/architecture/legacy.md"])
        self.assertEqual(d["legacy_layout"], ["docs/architecture/legacy.md"])
        self.assertEqual(d["broken_fences"], ["docs/architecture/legacy.md:5"])
        self.assertEqual(d["contracts_missing"], ["legacy"])

    def test_contract_migration_is_extend(self):
        (self.root / "docs/packages/quant/contract.md").unlink()
        d = self.status("architecture-design")
        self.assertEqual((d["mode"], d["contracts_missing"]), ("extend", ["quant"]))

    def test_inferred_package_id(self):
        shutil.rmtree(self.root / "docs/packages")
        (self.root / "docs/roadmap.md").unlink()
        d = self.status("architecture-design")
        self.assertEqual((d["mode"], d["contracts_missing"]), ("extend", ["quant"]))   # from Project layout
        self.assertEqual(self.status("pipeline-design")["packages"], {"quant": "new"})
        self.edit("docs/architecture.md", "src/quant/data/  src/quant/stats/  src/quant/portfolio/", "lib/")
        self.write("pyproject.toml", '[project]\nname = "quant-lab"\nversion = "0"\n\n[tool.x]\nname = "no"\n')
        self.assertEqual(self.status("architecture-design")["contracts_missing"], ["quant-lab"])
        (self.root / "pyproject.toml").unlink()
        self.assertEqual(self.status("architecture-design")["contracts_missing"], ["quant"])   # src/quant/
        shutil.rmtree(self.root / "src")
        self.assertEqual(self.status("architecture-design")["contracts_missing"], ["(no package id yet)"])
        self.assertEqual(self.status("pipeline-design")["packages"], {})

    def test_blocked_and_new(self):
        (self.root / "docs/architecture.md").unlink()
        self.assertEqual(self.status("architecture-design")["mode"], "new")
        (self.root / "docs/spec.md").unlink()
        self.assertEqual(self.status("architecture-design")["mode"], "blocked")

    def test_grow_triggers(self):
        for n in range(13):
            self.write(f"src/quant/stats/m{n}.py", '"""m."""\n')
        self.assertEqual(self.status("architecture-design")["grow_triggers"], ["quant: 15 modules > 12"])

    def test_changelog_same_day_order(self):
        spec = [specdocs.ChangelogRow("2026-10-15", "a", "brief.md", {"brief.md"}, {"A-01": "added"}),
                specdocs.ChangelogRow("2026-10-15", "b", "ideas/x.md", {"ideas/x.md"}, {"B-01": "added"}),
                specdocs.ChangelogRow("2026-10-15", "c", "ideas/x.md", {"ideas/x.md"}, {"B-02": "added"})]
        arch = [specdocs.ChangelogRow("2026-10-15", "", "brief.md", {"brief.md"}, {}),
                specdocs.ChangelogRow("2026-10-15", "", "ideas/x.md", {"ideas/x.md"}, {})]
        self.assertEqual([r.change for r in specdocs.pending_rows(spec, arch, "2026-10-15")], ["c"])
        self.assertEqual(specdocs.marked_ids("TANK-01–TANK-02; QR-03, CORE-04 (changed)"),
                         {"TANK-01": "added", "TANK-02": "added", "QR-03": "changed", "CORE-04": "changed"})


class ArchitectureChangelogTest(Base):
    """Changelog matching and fence checks (ported from arch-status.py, whose output dt matched before it was removed)."""

    def test_pending_rounds_and_fences(self):
        self.edit("docs/spec.md", "| PORT-01, PORT-02; DATA-03 (removed) |",
                  "| PORT-01, PORT-02; DATA-03 (removed) |\n"
                  "| 2026-10-15 | Tweak | user request | STAT-02, QR-01 (changed) |\n"
                  "| 2026-10-16 | More | ideas/more.md | PORT-03; STAT-03 (changed) |")
        self.edit("docs/spec.md", "### Quality", "- **PORT-03** More.\n\n### Quality")
        self.edit("docs/architecture.md", "## Risks", "```\n## Not a heading\n```\n\n## Risks")
        self.write("docs/architecture/data.md", "# data\n\n**Package:** data · **Status:** Draft\n\nPORT-03 lives here.\n")
        st = self.status("architecture-design")
        self.assertEqual(st["changed_since"], ["QR-01", "STAT-02", "STAT-03"])
        self.assertEqual(len(st["spec_rows_pending"]), 2)
        self.assertEqual(st["uncovered"], [])
        self.assertTrue(any(b.startswith("docs/architecture.md:") for b in st["broken_fences"]), st["broken_fences"])
        self.assertEqual([Path(p).name for p in st["package_docs"]], ["data.md"])


class PipelineDesignTest(Base):
    def test_fixture(self):
        d = self.status("pipeline-design")
        self.assertEqual(d["mode"], "current")
        self.assertEqual(d["packages"], {"quant": "current"})
        self.assertEqual((d["uncovered_ids"], d["components_unowned"], d["retired_refs"]), ([], [], []))

    def test_drift_unknown_until_layout_lands(self):
        with mock.patch.object(code, "pipeline_drift", side_effect=NotImplementedError):
            d = self.status("pipeline-design")
        self.assertEqual(d["drift"], "unknown")
        with mock.patch.object(code, "pipeline_drift", side_effect=lambda repo, p:
                               "drift — calls [a] vs steps [b]" if p.id == "PL-01" else None):
            d = self.status("pipeline-design")
        self.assertEqual(d["drift"], ["PL-01: drift — calls [a] vs steps [b]"])
        self.assertEqual(d["packages"], {"quant": "sync"})

    def test_gaps(self):
        self.edit("docs/architecture.md", "| `portfolio` | Build and compare portfolios | PORT-01, PORT-02 |",
                  "| `portfolio` | Build and compare portfolios | PORT-01, PORT-02 |\n| `risk` | Risk | QR-01 | — |")
        self.edit("docs/packages/quant/pipelines.md", "**Covers:** DATA-01, DATA-02, QR-01",
                  "**Covers:** DATA-01, DATA-02 · see PL-04")
        d = self.status("pipeline-design")
        self.assertEqual(d["mode"], "extend")
        self.assertEqual(d["uncovered_ids"], ["QR-01"])
        self.assertEqual(d["components_unowned"], ["risk"])
        self.assertEqual(d["retired_refs"], ["docs/packages/quant/pipelines.md:7 PL-04"])

    def test_misplaced_pipeline_is_grow(self):
        self.write("docs/packages/other/pipelines.md", "# other — Pipelines\n\n**Package:** other · **Status:** Approved\n\n"
                   "## PL-09: Stray\n**Entry:** `src/quant/data/x.py::run` · **Trigger:** `x`\n")
        d = self.status("pipeline-design")
        self.assertEqual(d["misplaced"], ["PL-09 (other → quant: src/quant/data/x.py)"])
        self.assertEqual((d["mode"], d["packages"]["other"]), ("grow", "grow"))

    @unittest.skipUnless(HAS_GIT, "git not installed")
    def test_revise_when_head_was_approved(self):
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs")
        self.edit("docs/packages/quant/pipelines.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.status("pipeline-design")["packages"], {"quant": "revise"})
        git(self.root, "checkout", "-q", "--", ".")
        self.edit("docs/packages/quant/tests.md", "**Status:** Approved", "**Status:** Draft")
        d = self.status("test-planning")
        self.assertEqual((d["mode"], d["packages"]), ("revise", {"quant": "revise"}))

    def test_blocked_and_new(self):
        (self.root / "docs/packages/quant/pipelines.md").unlink()
        self.assertEqual(self.status("pipeline-design")["packages"], {"quant": "new"})
        self.edit("docs/architecture.md", "**Status:** Approved", "**Status:** Draft")
        d = self.status("pipeline-design")
        self.assertEqual(d["mode"], "blocked")
        self.assertIn("Draft", d["blocked"])


class TestPlanningTest(Base):
    def test_fixture(self):
        d = self.status("test-planning")
        self.assertEqual(d["mode"], "extend")
        self.assertEqual((d["pipelines_no_smoke"], d["pipelines_no_golden"]), (["PL-03"], ["PL-03"]))
        self.assertEqual((d["cases_no_source"], d["cases_no_tolerance"], d["fixtures_missing"],
                          d["fixtures_orphan"]), ([], [], [], []))

    def test_part_of_system_pipeline_needs_no_own_cases(self):
        self.edit("docs/packages/quant/pipelines.md", "**Covers:** PORT-01, PORT-02", "**Covers:** PORT-01, PORT-02 · **Part of:** PL-09")
        d = self.status("test-planning")
        self.assertEqual((d["mode"], d["pipelines_no_smoke"], d["pipelines_no_golden"]), ("current", [], []))
        self.assertEqual(d["skills"], ["data-science"])

    def test_cases_and_fixtures(self):
        self.edit("docs/packages/quant/tests.md", "**Source:** generator `noise(T=250, N=50, seed=7)`; "
                  "Marchenko–Pastur closed form λ+ = σ²(1+√(N/T))²\n", "")
        self.edit("docs/packages/quant/tests.md", " · **Tolerance:** property, no tolerance", "")
        (self.root / "tests/fixtures/quant/TC-01/expected.json").unlink()
        shutil.rmtree(self.root / "tests/fixtures/quant/TC-03")
        (self.root / "tests/fixtures/quant/TC-09").mkdir()
        d = self.status("test-planning")
        self.assertEqual(d["cases_no_source"], ["TC-02"])
        self.assertEqual(d["cases_no_tolerance"], ["TC-03"])
        self.assertEqual(d["fixtures_missing"], ["TC-01 (no expected.json)", "TC-03 (tests/fixtures/quant/TC-03/)"])
        self.assertEqual(d["fixtures_orphan"], ["tests/fixtures/quant/TC-09/"])

    def test_blocked(self):
        self.edit("docs/packages/quant/pipelines.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.status("test-planning")["mode"], "blocked")


class BuildPlanningTest(Base):
    def test_fixture(self):
        d = self.status("build-planning")
        self.assertEqual(d["mode"], "extend")         # M1 building, M2 designed and unplanned
        self.assertEqual(d["milestone"], "M1 In progress")
        self.assertEqual(d["progress"], "1/6")
        self.assertEqual(d["next_task"], "M1-T02 PL-02 spine with sample covariance")
        self.assertEqual(d["base"], "3f2c1ab")
        self.assertEqual(d["skills_available"], ["data-science"])
        for k in ("blocked_tasks", "uncovered", "no_spine", "mode_violations", "skills_missing", "queued"):
            self.assertEqual(d[k], [], k)

    def test_task_checks(self):
        self.edit("tasks/plan.md", "**Skills:** —\n", "**Skills:** —\n**Blocked:** waiting on PL-02 Revise\n")
        self.edit("tasks/plan.md", "**Size:** S · **Mode:** split\n**Skills:** data-science\n**Read:** PL-02, TC-02",
                  "**Size:** S · **Mode:** solo\n**Skills:** rmt-tools\n**Read:** PL-02, TC-02")
        self.edit("tasks/plan.md", "**Covers:** STAT-01, QR-01 · **Size:** XS", "**Covers:** STAT-01 · **Size:** XS")
        self.edit("tasks/plan.md", "**Step:** PL-02 · **Covers:** STAT-04", "**Step:** PL-01.read_raw · **Covers:** STAT-04")
        self.edit("tasks/plan.md", "**Deferred:** none", "**Deferred:** QR-01 (later)")
        self.edit("tasks/plan.md", "**Covers:** DATA-02 · **Size:** S", "**Covers:** DATA-02, QR-02 · **Size:** S")
        self.edit("tasks/plan.md", "**Covers:** STAT-02, QR-02", "**Covers:** STAT-02")
        self.edit("tasks/plan.md", "**Covers:** STAT-03 ·", "**Covers:** ·")
        d = self.status("build-planning")
        self.assertEqual(d["mode"], "replan")
        self.assertEqual(d["blocked_tasks"], ["M1-T03 (waiting on PL-02 Revise)"])
        self.assertEqual(d["mode_violations"], ["M1-T04: solo, expected split (covers behaviour)"])
        self.assertEqual(d["skills_missing"], ["rmt-tools"])
        self.assertEqual(d["no_spine"], ["PL-02"])
        self.assertEqual(d["uncovered"], ["STAT-03"])

    def test_reason_overrides_mode_rule(self):
        self.edit("tasks/plan.md", "**Size:** XS · **Mode:** split", "**Size:** XS · **Mode:** solo\n**Reason:** doc-only")
        self.assertEqual(self.status("build-planning")["mode_violations"], [])

    def test_blocked_while_revise_in_progress(self):
        self.edit("docs/packages/quant/pipelines.md", "**Status:** Approved", "**Status:** Draft")
        d = self.status("build-planning")
        self.assertEqual((d["mode"], d["draft_pipelines"]), ("blocked", ["PL-01", "PL-02"]))
        self.assertEqual(d["blocked"], "waiting for docs/packages/quant/pipelines.md approval (Revise in progress)")
        self.edit("docs/packages/quant/pipelines.md", "**Status:** Draft", "**Status:** Approved")
        self.edit("docs/packages/quant/tests.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.status("build-planning")["blocked"],
                         "waiting for docs/packages/quant/tests.md approval (Revise in progress)")

    def test_replan_when_docs_approved_after_the_plan(self):
        self.assertEqual(self.status("build-planning")["changed_since_plan"], [])   # same day is not later
        self.edit("docs/packages/quant/pipelines.md", "**Last updated:** 2026-10-16", "**Last updated:** 2026-10-20")
        self.edit("docs/packages/quant/contract.md", "**Last updated:** 2026-10-15", "**Last updated:** 2026-10-18")
        d = self.status("build-planning")
        self.assertEqual(d["mode"], "replan")
        self.assertEqual(d["changed_since_plan"], ["docs/packages/quant/pipelines.md", "docs/packages/quant/contract.md"])
        _, text = run_dt(self.root, "status", "--skill", "build-planning")
        self.assertIn("changed_since_plan: docs/packages/quant/pipelines.md, docs/packages/quant/contract.md", text)
        self.edit("tasks/plan.md", "**Last updated:** 2026-10-16", "**Last updated:** 2026-10-20")
        d = self.status("build-planning")
        self.assertEqual((d["mode"], d["changed_since_plan"]), ("extend", []))

    def test_pipelines_inferred_for_an_empty_roadmap_cell(self):
        self.edit("docs/roadmap.md", "| quant | PL-03 |", "| — | — |")
        d = self.status("build-planning")
        self.assertEqual((d["mode"], d["pipelines_inferred"]), ("extend", ["PL-03"]))   # M2 is the one to queue
        _, text = run_dt(self.root, "status", "--skill", "build-planning")
        self.assertIn("pipelines_inferred: PL-03\n", text)
        # No plan yet: M1's empty cell is inferred from the brief's spec rows and gates `new`.
        (self.root / "tasks/plan.md").unlink()
        (self.root / "tasks/todo.md").unlink()
        self.edit("docs/roadmap.md", "| quant | PL-01, PL-02 |", "| — | — |")
        d = self.status("build-planning")
        self.assertEqual((d["mode"], d["pipelines_inferred"]), ("new", ["PL-01", "PL-02"]))
        self.edit("docs/packages/quant/pipelines.md", "**Status:** Approved", "**Status:** Draft")
        d = self.status("build-planning")
        self.assertEqual(d["mode"], "blocked")
        self.assertEqual(d["blocked"], "M1 pipelines not all Approved (PL-01, PL-02); run pipeline-design")

    def test_explicit_pipelines_cell_is_not_reported_as_inferred(self):
        (self.root / "tasks/plan.md").unlink()
        (self.root / "tasks/todo.md").unlink()
        self.assertEqual(self.status("build-planning")["pipelines_inferred"], [])

    def test_advance(self):
        todo = self.root / "tasks/todo.md"
        todo.write_text(todo.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
        self.assertNotEqual(self.status("build-planning")["mode"], "advance")   # exit checkpoint not ticked
        plan = self.root / "tasks/plan.md"
        text = plan.read_text(encoding="utf-8")
        head, exit_block = text.split("### Checkpoint: milestone exit")
        plan.write_text(head + "### Checkpoint: milestone exit" + exit_block.replace("- [ ]", "- [x]", 3),
                        encoding="utf-8")
        self.assertEqual(self.status("build-planning")["mode"], "advance")
        # A finished milestone advances even while a Revise is open (it belongs to the next plan).
        self.edit("docs/packages/quant/pipelines.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.status("build-planning")["mode"], "advance")

    def test_foreign(self):
        self.write("tasks/plan.md", "# Plan\n\n- [ ] Task 1: do it\n")
        self.assertEqual(self.status("build-planning")["mode"], "foreign")

    def test_new_and_blocked(self):
        (self.root / "tasks/plan.md").unlink()
        (self.root / "tasks/todo.md").unlink()
        d = self.status("build-planning")
        self.assertEqual((d["mode"], d["base"], d["progress"]), ("new", "pending", "0/0"))
        self.edit("docs/packages/quant/pipelines.md", "**Status:** Approved", "**Status:** Draft")
        d = self.status("build-planning")
        self.assertEqual(d["mode"], "blocked")
        self.assertIn("M1", d["blocked"])

    def test_plugin_skills(self):
        plugin = self.tmp / "plugin"
        for name in ("null-hypothesis-testing", "build-setup"):
            self.write(str(Path("..") / "plugin" / "skills" / name / "SKILL.md"), "---\nname: x\n---\n")
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(plugin)}):
            d = self.status("build-planning")
        self.assertEqual(d["skills_available"], ["data-science", "null-hypothesis-testing"])

    def test_drift_listed_for_milestone_pipelines(self):
        with mock.patch.object(code, "pipeline_drift", side_effect=lambda repo, p: f"{p.id}: drift — x"):
            d = self.status("build-planning")
        self.assertEqual(d["drift"], ["PL-01: drift — x", "PL-02: drift — x"])
        with mock.patch.object(code, "pipeline_drift", side_effect=NotImplementedError):
            self.assertEqual(self.status("build-planning")["drift"], "unknown")


@unittest.skipUnless(HAS_GIT, "git not installed")
class ContractFreshnessTest(Base):
    def test_stale_contract(self):
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "docs", date="2026-10-15T10:00:00")
        self.assertEqual(self.status("build-planning")["stale_contracts"], [])
        self.write("src/quant/stats/__init__.py", '"""Covariance and factor estimates."""\nfrom x import y\n')
        git(self.root, "commit", "-qam", "code", date="2026-10-16T10:00:00")
        self.assertEqual(self.status("architecture-design")["stale_contracts"],
                         ["quant (contract.md 2026-10-15, code 2026-10-16)"])
        self.edit("docs/packages/quant/contract.md", "## stats", "## stats\n")
        git(self.root, "commit", "-qam", "sync", date="2026-10-16T11:00:00")
        self.assertEqual(self.status("build-planning")["stale_contracts"], [])


class BuildSetupTest(Base):
    PYPROJECT = ("[tool.ruff.lint.mccabe]\nmax-complexity = 12\n\n"
                 "[tool.size_limits]\nmax_module_lines = 500\nmax_function_lines = 60\n")

    def test_fixture(self):
        d = self.status("build-setup")
        self.assertEqual((d["mode"], d["constraints"], d["base"]), ("current", "Approved", "3f2c1ab"))
        self.assertEqual(d["agents_missing"], ["tester", "implementer", "reviewer"])
        self.assertIn("scripts/check.sh", d["hooks_missing"])
        self.assertEqual(d["config_mismatches"], ["pyproject.toml missing (2 rules name a config key)"])

    def test_config_and_scripts(self):
        self.write("pyproject.toml", self.PYPROJECT)
        self.write(".claude/agents/tester.md", "---\nhooks: bash scripts/hooks/extra.sh\n---\n")
        self.write("scripts/hooks/path_guard.sh", "#!/bin/sh\n")
        self.assertEqual(self.status("build-setup")["config_mismatches"],
                         ["CR-21: CONSTRAINTS.md 10 vs tool.ruff.lint.mccabe.max-complexity = 12"])
        d = self.status("build-setup")
        self.assertIn("scripts/hooks/extra.sh", d["hooks_missing"])
        self.assertEqual(d["not_executable"], ["scripts/hooks/path_guard.sh"])
        self.assertEqual(d["agents_missing"], ["implementer", "reviewer"])

    def test_expired_exception(self):
        self.edit("CONSTRAINTS.md", "| ID | Rule | Path | Reason | Owner | Expires |\n|---|---|---|---|---|---|",
                  "| ID | Rule | Path | Reason | Owner | Expires |\n|---|---|---|---|---|---|\n"
                  "| EX-01 | CR-21 | src/quant/stats/rmt.py | port | @c | 2020-01-01 |\n"
                  "| EX-02 | CR-22 | src/quant/x.py | port | @c | 2999-01-01 |")
        self.assertEqual(self.status("build-setup")["expired_exceptions"],
                         ["EX-01 CR-21 src/quant/stats/rmt.py (expired 2020-01-01)"])

    def test_modes(self):
        self.edit("tasks/plan.md", "**Status:** In progress", "**Status:** Draft")
        self.assertEqual(self.status("build-setup")["mode"], "blocked")
        self.edit("tasks/plan.md", "**Status:** Draft", "**Status:** Approved")
        self.edit("tasks/todo.md", "- [x] M1-T01", "- [ ] M1-T01")
        self.assertEqual(self.status("build-setup")["mode"], "current")     # Base recorded: the bar is in place
        self.edit("tasks/plan.md", "**Base:** 3f2c1ab", "**Base:** —")
        self.assertEqual(self.status("build-setup")["mode"], "extend")
        self.edit("tasks/plan.md", "**Base:** — · ", "")
        self.assertEqual(self.status("build-setup")["mode"], "extend")
        os.rename(self.root / "CONSTRAINTS.md", self.root / "C.md")
        self.assertEqual(self.status("build-setup")["mode"], "new")
        os.rename(self.root / "C.md", self.root / "CONSTRAINTS.md")
        # Advance-ready: ratchet until CONSTRAINTS.md records this milestone as ratcheted.
        todo = self.root / "tasks/todo.md"
        todo.write_text(todo.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
        plan = self.root / "tasks/plan.md"
        head, exit_block = plan.read_text(encoding="utf-8").split("### Checkpoint: milestone exit")
        plan.write_text(head + "### Checkpoint: milestone exit" + exit_block.replace("- [ ]", "- [x]", 3),
                        encoding="utf-8")
        self.assertEqual(self.status("build-setup")["mode"], "ratchet")
        self.edit("CONSTRAINTS.md", "**Status:** Approved", "**Status:** Approved · **Ratcheted:** M1")
        self.assertEqual(self.status("build-setup")["mode"], "current")
        (self.root / "tasks/plan.md").unlink()
        self.assertEqual(self.status("build-setup")["mode"], "blocked")

    GENERATED = (
        '[tool.ruff.lint.per-file-ignores]\n"tests/**" = ["S101"]\n"__init__.py" = ["F401"]\n'
        '"src/quant/stats/rmt.py" = ["C901"]\n\n'
        '[tool.deptry]\nknown_first_party = ["quant"]\n\n[tool.deptry.per_rule_ignores]\nDEP002 = ["numpy", "pandas"]\n\n'
        '[tool.importlinter]\nroot_package = "quant"\n\n[[tool.importlinter.contracts]]\nname = "Layers"\n'
        'type = "layers"\nlayers = [\n    "(quant.portfolio)",\n    "quant.stats",\n    "quant.data",\n]\n')
    EXCEPTION = "| EX-01 | CR-25 DEP002 | `numpy`, `pandas` | M1 dependencies | @c | M1 exit |"

    def add_exception(self, row: str) -> None:
        self.edit("CONSTRAINTS.md", "| ID | Rule | Path | Reason | Owner | Expires |\n|---|---|---|---|---|---|",
                  "| ID | Rule | Path | Reason | Owner | Expires |\n|---|---|---|---|---|---|\n" + row)

    def test_dependents(self):
        d = self.status("build-setup")
        self.assertEqual(d["dependents"], {"data": ["stats", "portfolio"], "stats": ["portfolio"], "portfolio": []})
        _, text = run_dt(self.root, "status", "--skill", "build-setup")
        self.assertIn("dependents: data<-stats,portfolio, stats<-portfolio, portfolio<-", text)

    def test_generated_checks_unknown_without_inputs(self):
        d = self.status("build-setup")
        for k in ("contract_mismatches", "optional_layers_existing", "deptry_missing", "protected_gaps",
                  "ignores_without_exception"):
            self.assertEqual(d[k], "unknown", k)

    def test_generated_config_checks(self):
        self.write("pyproject.toml", self.GENERATED)
        self.add_exception(self.EXCEPTION)
        self.write("scripts/check.sh", "#!/usr/bin/env bash\nPROTECTED=('tests/intent/**' 'tests/conftest.py')\n")
        self.edit("CONSTRAINTS.md", "## Exceptions", "**Protected list** (`PROTECTED` in `scripts/check.sh`): "
                  "`tests/intent/**`, `tests/fixtures/**`, `tests/conftest.py`.\n\n## Exceptions")
        d = self.status("build-setup")
        self.assertEqual(d["contract_mismatches"], [])
        self.assertEqual(d["optional_layers_existing"], [])
        self.assertEqual(d["deptry_missing"], [])
        self.assertEqual(d["ignores_without_exception"], ["src/quant/stats/rmt.py (C901)"])
        self.assertEqual(d["protected_gaps"], ["tests/fixtures/** not in check.sh",
                                               "check.sh and CONSTRAINTS.md differ: tests/fixtures/**"])
        self.write("src/quant/portfolio/__init__.py", "")
        self.assertEqual(self.status("build-setup")["optional_layers_existing"], ["quant.portfolio"])

    def test_contract_mismatches(self):
        self.write("pyproject.toml", self.GENERATED.replace('"quant.stats",\n    "quant.data"', '"quant.data",\n    "quant.stats"')
                   .replace("[tool.deptry]\nknown_first_party", "[tool.other]\nknown_first_party")
                   .replace("[tool.deptry.per_rule_ignores]", "[tool.other.per_rule_ignores]"))
        d = self.status("build-setup")
        self.assertEqual(d["contract_mismatches"], ["data → stats: allowed by the contracts, not by the architecture",
                                                    "stats → data: forbidden by a contract, allowed by the architecture"])
        self.assertEqual(d["deptry_missing"], ["quant"])
        self.write("pyproject.toml", "[project]\nname = 'q'\n")
        self.assertEqual(self.status("build-setup")["contract_mismatches"],
                         ["no [[tool.importlinter.contracts]] in pyproject.toml"])

    def test_exception_expires_at_milestone_exit(self):
        self.add_exception(self.EXCEPTION)
        self.assertEqual(self.status("build-setup")["expired_exceptions"], [])
        self.write("tasks/archive/M1-data-stats.md", "# M1: Data + stats — Plan\n\n**Milestone:** M1 · **Status:** Done\n")
        self.assertEqual(self.status("build-setup")["expired_exceptions"],
                         ["EX-01 CR-25 DEP002 numpy, pandas (expired M1 exit)"])

    def test_toml_fallback_parser(self):
        data = parse_toml('[tool.ruff]\nline-length = 100\nlint.mccabe.max-complexity = 10  # c\n'
                                 'select = [\n  "E",\n  "F",\n]\n[tool."size_limits"]\nmodule = 500\n'
                                 'strict = true\nname = "x"\nratio = 71.2\n')
        self.assertEqual(data["tool"]["ruff"]["lint"]["mccabe"]["max-complexity"], 10)
        self.assertEqual(data["tool"]["ruff"]["line-length"], 100)
        self.assertEqual(data["tool"]["size_limits"],
                         {"module": 500, "strict": True, "name": "x", "ratio": 71.2})


class SummaryTest(Base):
    def summary(self, root: Path | None = None) -> tuple[int, list[str]]:
        rc, out = run_dt(root or self.root, "status", "--summary")
        return rc, out.splitlines()

    def test_fixture(self):
        rc, lines = self.summary()
        self.assertEqual(rc, 0)
        self.assertLessEqual(len(lines), 8)
        self.assertEqual(lines[0], "milestone: M1 Data + stats · plan In progress")
        self.assertEqual(lines[1], "progress: 1/6 · next: M1-T02 PL-02 spine with sample covariance")
        self.assertEqual(lines[2], "blocked: none")
        self.assertTrue(lines[-1].startswith("dt: python3 /") and lines[-1].endswith("dt.py"))

    def test_drafts_blocked_queued(self):
        self.edit("docs/spec.md", "**Status:** Approved", "**Status:** Draft")
        self.edit("tasks/plan.md", "**Skills:** —\n", "**Skills:** —\n**Blocked:** oracle question\n")
        self.write("tasks/queued/M2-x.md", "# M2: X — Plan\n\n**Milestone:** M2 · **Status:** Approved\n")
        _, lines = self.summary()
        self.assertIn("blocked: M1-T03 (oracle question)", lines)
        self.assertIn("draft (waiting for approval): docs/spec.md", lines)
        self.assertIn("queued: M2", lines)
        self.assertLessEqual(len(lines), 8)

    def test_not_a_dev_team_project(self):
        empty = self.tmp / "other"
        (empty / "docs").mkdir(parents=True)
        (empty / "docs" / "notes.md").write_text("# notes\n", encoding="utf-8")
        self.assertEqual(self.summary(empty), (0, []))
        self.assertEqual(self.summary(self.tmp / "missing"), (0, []))

    def test_never_crashes(self):
        with mock.patch.object(status, "summary", side_effect=RuntimeError("boom")):
            rc, lines = self.summary()
        self.assertEqual((rc, lines), (0, ["dt status: error: RuntimeError: boom"]))

    def test_always_exit_0_when_blocked(self):
        (self.root / "docs/brief.md").unlink()
        self.assertEqual(self.summary()[0], 0)

    def test_between_milestones(self):
        self.write("tasks/plan.md", "# Between milestones\n\n**Status:** Between milestones · **Roadmap:** x\n")
        self.write("tasks/todo.md", "# Todo\n")
        rc, lines = self.summary()
        self.assertEqual(lines[0], "milestone: none (between milestones)")


if __name__ == "__main__":
    unittest.main()
