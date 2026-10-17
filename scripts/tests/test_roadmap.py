"""dt roadmap on copies of the quant fixture. Run: python3 -m unittest discover -s scripts/tests"""
from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import dt  # noqa: E402
from devteam import md, model  # noqa: E402
from devteam.commands import roadmap  # noqa: E402
from devteam.repo import Repo  # noqa: E402

QUANT = HERE / "fixtures" / "quant"


def run_dt(root: Path, *args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = dt.main(["--root", str(root), *args])
    return code, out.getvalue(), err.getvalue()


class QuantCopy(unittest.TestCase):
    """A throwaway copy of the quant fixture at self.root."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "quant"
        shutil.copytree(QUANT, self.root)

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

    def statuses(self) -> dict[str, str]:
        repo = Repo(self.root)
        return {m.id: roadmap.milestone_status(repo, m) for m in model.milestones(repo.roadmap)}


class RoadmapTest(QuantCopy):
    def test_fixture_is_current(self):
        self.assertEqual(self.statuses(), {"M1": "Building", "M2": "Designed"})
        code, out, _ = run_dt(self.root, "roadmap", "--check")
        self.assertEqual((code, out.strip()), (0, "roadmap: ok"))

    def test_check_reports_without_writing(self):
        self.edit("docs/roadmap.md", "| M1 | Designed |", "| M1 | Idea |")
        before = (self.root / "docs/roadmap.md").read_text(encoding="utf-8")
        code, out, _ = run_dt(self.root, "roadmap", "--check")
        self.assertEqual(code, 1)
        self.assertIn("M2: Idea → Designed", out)
        self.assertEqual((self.root / "docs/roadmap.md").read_text(encoding="utf-8"), before)

    def test_write_rewrites_only_status_cells(self):
        self.edit("docs/roadmap.md", "| — | Building |", "| — | Planned |")
        self.edit("docs/roadmap.md", "| M1 | Designed |", "| M1 |  |")
        before = (self.root / "docs/roadmap.md").read_text(encoding="utf-8").splitlines()
        code, out, _ = run_dt(self.root, "roadmap")
        self.assertEqual(code, 0)
        self.assertIn("M1: Planned → Building", out)
        self.assertIn("M2: — → Designed", out)
        after = (self.root / "docs/roadmap.md").read_text(encoding="utf-8")
        self.assertTrue(after.endswith("\n"))
        changed = [(a, b) for a, b in zip(before, after.splitlines()) if a != b]
        self.assertEqual([b for _, b in changed],
                         ["| M1 | Data + stats | brief | quant | PL-01, PL-02 | — | Building |",
                          "| M2 | Classical portfolios | ideas/classical-portfolios.md | quant | PL-03 | M1 | Designed |"])
        self.assertEqual(run_dt(self.root, "roadmap", "--check")[0], 0)

    def test_planned_when_active_plan_has_no_checked_task(self):
        self.edit("tasks/todo.md", "- [x] M1-T01", "- [ ] M1-T01")
        self.assertEqual(self.statuses()["M1"], "Planned")

    def test_planned_when_queued(self):
        self.write("tasks/queued/M2-classical-portfolios.md",
                   "# M2: Classical portfolios — Plan\n\n**Milestone:** M2 · **Status:** Approved\n")
        self.assertEqual(self.statuses()["M2"], "Planned")

    def test_done_by_archive_or_outcome(self):
        self.write("tasks/archive/M2-classical-portfolios.md", "# M2: Classical portfolios — Plan\n\n"
                   "**Milestone:** M2 · **Status:** Done\n")
        self.assertEqual(self.statuses()["M2"], "Done")
        shutil.rmtree(self.root / "tasks/archive")
        self.edit("docs/roadmap.md", "**Exit:** Min-var", "**Outcome:** Done 2026-11-02\n**Exit:** Min-var")
        self.assertEqual(self.statuses()["M2"], "Done")

    def test_specced_and_idea(self):
        self.edit("docs/packages/quant/pipelines.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.statuses()["M2"], "Specced")
        self.edit("docs/ideas/classical-portfolios.md", "**Status:** Specced", "**Status:** Accepted")
        self.assertEqual(self.statuses()["M2"], "Idea")

    def test_brief_row(self):
        (self.root / "tasks/plan.md").unlink()
        self.edit("docs/packages/quant/pipelines.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.statuses()["M1"], "Specced")
        self.edit("docs/spec.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.statuses()["M1"], "Idea")

    def test_retired_pipeline_ignored(self):
        self.edit("docs/roadmap.md", "| PL-03 |", "| PL-03, PL-04 |")
        self.assertEqual(self.statuses()["M2"], "Designed")

    def test_pipelines_inferred_from_source_when_cell_is_empty(self):
        # idea-refine writes `—`; the spec Changelog rows for the row's Source give the IDs, and the pipelines
        # covering them (Covers or step Covers) are the milestone's.
        self.edit("docs/roadmap.md", "| quant | PL-01, PL-02 |", "| — | — |")
        self.edit("docs/roadmap.md", "| quant | PL-03 |", "| — | — |")
        repo = Repo(self.root)
        m1, m2 = model.milestones(repo.roadmap)
        self.assertEqual(roadmap.milestone_pipelines(repo, m1), (["PL-01", "PL-02"], True))
        self.assertEqual(roadmap.milestone_pipelines(repo, m2), (["PL-03"], True))
        self.assertEqual(self.statuses()["M2"], "Designed")
        self.edit("docs/packages/quant/pipelines.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.statuses()["M2"], "Specced")

    def test_explicit_pipelines_cell_wins(self):
        self.edit("docs/roadmap.md", "| quant | PL-03 |", "| quant | PL-09 |")
        repo = Repo(self.root)
        self.assertEqual(roadmap.milestone_pipelines(repo, model.milestones(repo.roadmap)[1]), (["PL-09"], False))
        self.assertEqual(self.statuses()["M2"], "Specced")

    def test_nothing_inferred_until_a_pipeline_covers_the_ids(self):
        self.edit("docs/roadmap.md", "| quant | PL-03 |", "| — | — |")
        self.edit("docs/packages/quant/pipelines.md", "**Covers:** PORT-01, PORT-02", "**Covers:** —")
        text = (self.root / "docs/packages/quant/pipelines.md").read_text(encoding="utf-8")
        self.write("docs/packages/quant/pipelines.md", text.replace("| PORT-01 |", "| — |").replace("| PORT-02 |", "| — |"))
        repo = Repo(self.root)
        self.assertEqual(roadmap.inferred_pipelines(repo, model.milestones(repo.roadmap)[1]), [])
        self.assertEqual(self.statuses()["M2"], "Specced")

    def test_write_keeps_crlf_and_file_mode(self):
        path = self.root / "docs/roadmap.md"
        text = path.read_text(encoding="utf-8").replace("| M1 | Designed |", "| M1 | Idea |")
        path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
        path.chmod(0o640)
        self.assertEqual(run_dt(self.root, "roadmap")[0], 0)
        after = path.read_bytes().decode("utf-8")
        self.assertIn("| PL-03 | M1 | Designed |\r\n", after)
        self.assertNotIn("\n", after.replace("\r\n", ""))
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_no_roadmap(self):
        (self.root / "docs/roadmap.md").unlink()
        code, _, err = run_dt(self.root, "roadmap", "--check")
        self.assertEqual(code, 1)
        self.assertIn("no docs/roadmap.md", err)


STAGED = HERE / "fixtures" / "staged-roadmap.md"     # the quant roadmap with stages S1, S2 and S1 cut into M1


class StagedRoadmapTest(QuantCopy):
    """Stages (idea-refine's rows) cut into milestones (build-planning's rows)."""

    def setUp(self):
        super().setUp()
        self.write("docs/roadmap.md", STAGED.read_text(encoding="utf-8"))

    def stage_statuses(self) -> dict[str, str]:
        repo = Repo(self.root)
        return {s.id: roadmap.stage_status(repo, s) for s in model.stages(repo.roadmap)}

    def cut_s2(self, stage: str = "S2") -> None:
        self.edit("docs/roadmap.md", "| M1 | S1 | Prices to covariance | quant | PL-01, PL-02 | — | Building |",
                  "| M1 | S1 | Prices to covariance | quant | PL-01, PL-02 | — | Building |\n"
                  f"| M2 | {stage} | Equal weight vs min-var | quant | PL-03 | M1 | |")

    def test_fixture_is_current(self):
        self.assertEqual(self.statuses(), {"M1": "Building"})
        self.assertEqual(self.stage_statuses(), {"S1": "Building", "S2": "Designed"})
        code, out, _ = run_dt(self.root, "roadmap", "--check")
        self.assertEqual((code, out.strip()), (0, "roadmap: ok"))

    def test_milestone_inherits_stage_source_and_skills(self):
        repo = Repo(self.root)
        m1 = model.milestones(repo.roadmap)[0]
        self.assertEqual((m1.stage, md.strip_md(m1.source), m1.skills), ("S1", "brief", ["data-science"]))
        self.edit("docs/roadmap.md", "**Plan:** [../tasks", "**Skills:** —\n**Plan:** [../tasks")
        self.assertEqual(model.milestones(Repo(self.root).roadmap)[0].skills, [])

    def test_cut_stage_and_write_both_tables(self):
        self.cut_s2()
        self.assertEqual(self.stage_statuses()["S2"], "Cut")
        code, out, _ = run_dt(self.root, "roadmap")
        self.assertEqual(code, 0)
        self.assertIn("S2: Designed → Cut", out)
        self.assertIn("M2: — → Designed", out)
        text = (self.root / "docs/roadmap.md").read_text(encoding="utf-8")
        self.assertIn("| S2 | Classical portfolios | ideas/classical-portfolios.md | Cut |", text)
        self.assertIn("| M2 | S2 | Equal weight vs min-var | quant | PL-03 | M1 | Designed |", text)
        self.write("tasks/queued/M2-equal-weight.md", "# M2: Equal weight — Plan\n\n**Milestone:** M2 · **Status:** Approved\n")
        self.assertEqual(self.stage_statuses()["S2"], "Planned")

    def test_stage_done_when_every_milestone_is(self):
        self.edit("docs/roadmap.md", "**Exit:** PCA", "**Outcome:** Done 2026-11-02\n**Exit:** PCA")
        self.assertEqual(self.stage_statuses()["S1"], "Done")

    def test_uncut_stage_specced_and_idea(self):
        self.edit("docs/packages/quant/pipelines.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual(self.stage_statuses()["S2"], "Specced")
        self.edit("docs/ideas/classical-portfolios.md", "**Status:** Specced", "**Status:** Accepted")
        self.assertEqual(self.stage_statuses()["S2"], "Idea")

    def test_next_unit_is_the_stage_to_cut(self):
        repo = Repo(self.root)
        unit = roadmap.next_unit(repo)
        self.assertEqual((type(unit).__name__, unit.id), ("Stage", "S2"))
        self.assertEqual(roadmap.milestone_pipelines(repo, unit), (["PL-03"], True))
        self.cut_s2()
        unit = roadmap.next_unit(Repo(self.root))
        self.assertEqual((type(unit).__name__, unit.id), ("Milestone", "M2"))

    def test_next_ids(self):
        code, out, _ = run_dt(self.root, "next-id", "S", "M")
        self.assertEqual((code, out.split()), (0, ["S3", "M2"]))

    def test_stage_references_serve_its_milestones(self):
        self.edit("docs/references.md", "**Milestones:** M1", "**Milestones:** S1")
        repo = Repo(self.root)
        self.assertEqual(model.milestone_references(repo, "M1"), ["RF-01"])
        self.assertEqual(model.milestone_references(repo, "S1"), ["RF-01"])
        self.edit("docs/roadmap.md", "**Plan:** [../tasks", "**References:** —\n**Plan:** [../tasks")
        self.assertEqual(model.milestone_references(Repo(self.root), "M1"), [])

    def test_lint_roadmap_stage(self):
        self.cut_s2("S9")
        code, out, _ = run_dt(self.root, "lint", "docs/roadmap.md")
        self.assertEqual(code, 1)
        self.assertIn("M2 Stage S9: no such stage row", out)


if __name__ == "__main__":
    unittest.main()
