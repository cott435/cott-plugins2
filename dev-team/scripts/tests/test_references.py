"""References (design/references.md): the index parser, `dt outline`, `dt references --stamp`, the status keys,
`dt context` rendering and the reference lint checks, on copies of fixtures/quant."""
from __future__ import annotations

import json
import os
import re
import unittest
from unittest import mock

from dt_helpers import HAS_GIT, QUANT, FixtureCopy, Project, run_dt

from devteam import model  # noqa: E402
from devteam import references as refs  # noqa: E402
from devteam.commands import lint  # noqa: E402
from devteam.repo import Repo  # noqa: E402

INDEX, ROADMAP, PLAN, SPEC = "docs/references.md", "docs/roadmap.md", "tasks/plan.md", "docs/spec.md"
MD_FILE = "references/market_decomposition.py"
BANNER = ("> Reference, not part of the project. Reuse what fits the contract and step table as is, adapt it, "
          "or ignore it: your call.\n"
          "> Never import from references/. Anything you bring over meets the same bar as the rest of the code.\n")


class Base(FixtureCopy):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ)
        env.start()
        os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        self.addCleanup(env.stop)

    def status(self, skill: str | None = None) -> dict:
        args = ["status", "--json"] + (["--skill", skill] if skill else [])
        return json.loads(self.dt(*args)[1])

    def add_entry(self, id_: str, rel: str, milestones: str = "—", stamp: bool = True, extra: str = "") -> None:
        text = self.read(INDEX)
        entry = (f"\n### {id_}: Added\n**File:** `{rel}` · **Hash:** 00000000 · **Kind:** code · "
                 f"**Milestones:** {milestones}\n- **Purpose:** test\n{extra}")
        self.write(INDEX, text + entry)
        if stamp:
            self.assertEqual(self.dt("references", "--stamp", id_)[0], 0)

    def set_read(self, value: str) -> None:
        """Replace M1-T06's Read line (the only task that reads RF-01 in the fixture)."""
        text = self.read(PLAN)
        start = text.index("### M1-T06")
        line = re.search(r"\*\*Read:\*\*[^\n]*", text[start:])
        a, b = start + line.start(), start + line.end()
        self.write(PLAN, text[:a] + f"**Read:** {value}" + text[b:])


# ---- parser -------------------------------------------------------------------------------------

class ParserTest(unittest.TestCase):
    def test_entries(self):
        repo = Repo(QUANT)
        self.assertEqual(repo.references.kind, "references")
        rf1, rf2 = model.all_references(repo)
        self.assertEqual((rf1.id, rf1.file, rf1.kind, rf1.milestones), ("RF-01", MD_FILE, "code", ["M1"]))
        self.assertEqual(rf1.hash, refs.file_hash(QUANT / MD_FILE))
        self.assertEqual(rf1.caveats, "fits PCA on the whole sample (look-ahead); the project must fit per window")
        self.assertEqual((rf2.milestones, rf2.caveats), ([], ""))
        self.assertEqual(model.milestone_references(repo, "M1"), ["RF-01"])
        self.assertEqual(repo.next_id("RF"), "RF-03")

    def test_roadmap_skills(self):
        ms = {m.id: m for m in model.milestones(Repo(QUANT).roadmap)}
        self.assertEqual((ms["M1"].skills, ms["M2"].skills), (["data-science"], []))

    def test_split_ref(self):
        self.assertEqual(model.split_ref("RF-01:pca_factors"), ("RF-01", "pca_factors"))
        self.assertEqual(model.split_ref("RF-03:Data model"), ("RF-03", "Data model"))
        self.assertEqual(model.split_ref("PL-02"), ("PL-02", ""))


class ParserCopyTest(Base):
    def test_all_retired_and_milestone_lists(self):
        self.replace(INDEX, "**Milestones:** —", "**Milestones:** all")
        self.replace(INDEX, "**Milestones:** M1", "**Milestones:** M1, M3")
        self.write(INDEX, self.read(INDEX) + "\n## Retired\n- ~~RF-03: Old loader~~ Retired 2026-10-01: file removed\n")
        repo = Repo(self.root)
        self.assertEqual(model.milestone_references(repo, "M3"), ["RF-01", "RF-02"])
        self.assertEqual(model.milestone_references(repo, "M2"), ["RF-02"])
        self.assertTrue(repo.is_retired("RF-03"))
        self.assertEqual(repo.next_id("RF"), "RF-04")
        self.assertEqual([r.id for r in model.all_references(repo)], ["RF-01", "RF-02"])


# ---- dt outline ---------------------------------------------------------------------------------

class OutlineTest(Base):
    def test_python(self):
        code, out, _ = self.dt("outline", MD_FILE)
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], f"{MD_FILE} · python · 38 lines")
        self.assertIn("6: def demean_returns(returns: pd.DataFrame) -> pd.DataFrame — Subtract each column's mean.",
                      lines)
        self.assertIn("26: class MarketRemover — Fits PCA once on the whole sample, then residualizes any panel.", lines)
        self.assertIn("37:   def transform(self, returns: pd.DataFrame) -> pd.DataFrame", lines)
        self.assertEqual(self.dt("outline", "RF-01"), (0, out, ""))

    def test_never_runs_the_file(self):
        self.write("references/boom.py", "import os\nos.makedirs('ran')\n\n\nasync def f(x, *a, k=1, **kw):\n"
                                         "    '''Doc.'''\n\n\nclass C(Base, metaclass=M):\n    pass\n")
        code, out, _ = self.dt("outline", "references/boom.py")
        self.assertEqual(code, 0)
        self.assertIn("5: async def f(x, *a, k=1, **kw) — Doc.", out)
        self.assertIn("9: class C(Base, metaclass=M)", out)
        self.assertFalse((self.root / "ran").exists())

    def test_markdown_text_and_errors(self):
        code, out, _ = self.dt("outline", "docs/references.md")
        self.assertEqual(out.splitlines()[:3], ["docs/references.md · markdown · 18 lines",
                                                "1: # Quant Lab — References",
                                                "5: ### RF-01: Market decomposition transforms"])
        self.write("references/build.sh", "".join(f"echo {n}\n" for n in range(60)))
        code, out, _ = self.dt("outline", "references/build.sh")
        self.assertEqual(out.splitlines()[0], "references/build.sh · text · 60 lines · first 40 lines")
        self.assertEqual(len(out.splitlines()), 41)
        self.write("references/bad.py", "def (:\n")
        self.assertIn("cannot parse", self.dt("outline", "references/bad.py")[1])
        self.assertEqual(self.dt("outline", "references/nope.py")[0], 1)
        self.assertEqual(self.dt("outline", "RF-09")[0], 1)


# ---- dt references --stamp ----------------------------------------------------------------------

class StampTest(Base):
    def test_stamp_after_change(self):
        before = self.read(INDEX)
        self.assertEqual(self.dt("references", "--stamp"), (0, "references: nothing to stamp\n", ""))
        self.write(MD_FILE, self.read(MD_FILE) + "# changed\n")
        new = refs.file_hash(self.root / MD_FILE)
        code, out, _ = self.dt("references", "--stamp")
        self.assertEqual((code, out), (0, f"RF-01: {new}\nreferences: stamped 1\n"))
        after = self.read(INDEX)
        old = refs.file_hash(QUANT / MD_FILE)
        self.assertEqual(after, before.replace(f"**Hash:** {old}", f"**Hash:** {new}"))
        self.assertIn("**Status:** Approved", after)

    def test_inserts_missing_hash_and_keeps_crlf(self):
        text = self.read(INDEX).replace("· **Hash:** d6ef7c17 ", "").replace("\n", "\r\n")
        self.write(INDEX, text)
        self.assertEqual(self.dt("references", "--stamp", "RF-02")[0], 0)
        self.assertIn("**File:** `references/tft_targets.py` · **Hash:** d6ef7c17 · **Kind:** code · **Milestones:** —\r\n",
                      self.read(INDEX))
        self.assertEqual(self.read(INDEX).count("\r\n"), text.count("\r\n"))

    def test_missing_file_and_unknown_id(self):
        (self.root / "references/tft_targets.py").unlink()
        code, out, _ = self.dt("references", "--stamp")
        self.assertEqual(code, 1)
        self.assertIn("RF-02: references/tft_targets.py missing (not stamped)", out)
        self.assertEqual(self.dt("references", "--stamp", "RF-09")[0], 1)

    def test_list(self):
        self.write("references/new.py", "x = 1\n")
        self.write(MD_FILE, "x = 2\n")
        code, out, _ = self.dt("references")
        self.assertEqual(code, 0)
        self.assertIn(f"RF-01: {MD_FILE} · changed (now {refs.file_hash(self.root / MD_FILE)}) · M1", out)
        self.assertIn("RF-02: references/tft_targets.py · ok · —", out)
        self.assertIn("unindexed: references/new.py", out)

    def test_no_index(self):
        (self.root / INDEX).unlink()
        self.assertEqual(self.dt("references", "--stamp")[0], 1)


# ---- dt status ----------------------------------------------------------------------------------

class StatusTest(Base):
    def test_fixture_nothing_waiting(self):
        for skill in (None, "idea-refine", "build-planning", "reference-intake"):
            d = self.status(skill)
            for k in ("references_unindexed", "references_changed", "references_missing"):
                self.assertEqual(d[k], [], (skill, k))
        d = self.status("reference-intake")
        self.assertEqual((d["mode"], d["index"], d["files_to_read"], d["next_id"]), ("current", "Approved", [], "RF-03"))
        self.assertEqual(d["milestones"], [{"id": "M1", "name": "Data + stats"},
                                           {"id": "M2", "name": "Classical portfolios"}])
        self.assertEqual(self.status("idea-refine")["references_unassigned"], ["RF-02"])
        self.assertIn("RF", self.status("spec-writing")["reserved_prefixes"])

    def test_waiting_files(self):
        self.write("references/notes/hrp.md", "# HRP\n")
        self.write("references/.DS_Store", "x")
        self.write("references/big.py", "x = 1\n" * 401)
        self.write(MD_FILE, "x = 2\n")
        (self.root / "references/tft_targets.py").unlink()
        d = self.status("reference-intake")
        self.assertEqual(d["mode"], "extend")
        self.assertEqual(d["references_unindexed"], ["references/big.py", "references/notes/hrp.md"])
        self.assertEqual(d["references_changed"], [f"RF-01 ({MD_FILE})"])
        self.assertEqual(d["references_missing"], ["RF-02 (references/tft_targets.py)"])
        self.assertEqual(d["files_to_read"], ["references/big.py", MD_FILE, "references/notes/hrp.md"])
        self.assertEqual(d["outline_first"], ["references/big.py"])
        self.assertEqual(self.status("test-planning")["references_changed"], [f"RF-01 ({MD_FILE})"])
        _, out, _ = self.dt("status", "--summary")
        lines = out.splitlines()
        self.assertEqual(lines[-2], "references: 4 waiting → reference-intake")
        self.assertTrue(lines[-1].startswith("dt: python3"))

    def test_new_mode(self):
        (self.root / INDEX).unlink()
        d = self.status("reference-intake")
        self.assertEqual((d["mode"], d["index"], d["next_id"]), ("new", "missing", "RF-01"))
        self.assertEqual(d["files_to_read"], [MD_FILE, "references/tft_targets.py"])

    def test_summary_silent_outside_dev_team_projects(self):
        other = self.root.parent / "other"
        (other / "references").mkdir(parents=True)
        (other / "references" / "x.py").write_text("x = 1\n", encoding="utf-8")
        self.assertEqual(run_dt(other, "status", "--summary")[1], "")
        self.assertNotIn("references:", self.dt("status", "--summary")[1])

    def test_build_planning_routing(self):
        d = self.status("build-planning")
        self.assertEqual(d["mode"], "extend")         # focus is M2, the milestone to queue
        self.assertEqual((d["milestone_references"], d["milestone_skills"]), ([], []))
        self.assertEqual((d["references_unrouted"], d["skills_unrouted"]), ([], []))
        self.replace(INDEX, "**Milestones:** —", "**Milestones:** M1, M2")
        self.replace(ROADMAP, "**Skills:** data-science", "**Skills:** data-science, null-hypothesis-testing")
        self.set_read("PL-02, TC-03, STAT-01, QR-01")
        d = self.status("build-planning")
        self.assertEqual(d["references_unrouted"], ["RF-01 (M1)", "RF-02 (M1)"])
        self.assertEqual(d["skills_unrouted"], ["null-hypothesis-testing (M1)"])
        self.assertEqual(d["milestone_references"], ["RF-02"])
        self.replace(ROADMAP, "**Exit:** Min-var", "**Skills:** portfolio-math\n**Exit:** Min-var")
        d = self.status("build-planning")
        self.assertEqual(d["milestone_skills"], ["portfolio-math"])
        self.assertEqual(d["skills_missing"], ["portfolio-math"])

    def test_queued_plan_is_checked(self):
        self.replace(INDEX, "**Milestones:** —", "**Milestones:** M2")
        self.write("tasks/queued/M2-classical.md",
                   "# M2: Classical portfolios — Plan\n\n**Milestone:** M2 · **Status:** Draft\n\n"
                   "### M2-T01: Min-var weights\n**Read:** PL-03, RF-02:forward_returns\n")
        self.assertEqual(self.status("build-planning")["references_unrouted"], [])
        self.replace("tasks/queued/M2-classical.md", ", RF-02:forward_returns", "")
        self.assertEqual(self.status("build-planning")["references_unrouted"], ["RF-02 (M2)"])


# ---- dt context ---------------------------------------------------------------------------------

class ContextTest(Base):
    def context(self, read: str) -> tuple[int, str, str]:
        self.set_read(read)
        return self.dt("context", "M1-T06")

    def test_symbol_selector(self):
        code, out, _ = self.context("PL-02, RF-01:pca_factors")
        self.assertEqual(code, 0)
        self.assertIn("<!-- docs/references.md:5 -->\n### RF-01: Market decomposition transforms\n", out)
        self.assertIn(f"### Reference RF-01: {MD_FILE}\n{BANNER}> Caveats: fits PCA on the whole sample "
                      "(look-ahead); the project must fit per window\n(pca_factors · lines 11–17 of 38)\n"
                      "```python\ndef pca_factors(", out)
        self.assertNotIn("def residualize", out)
        self.assertLess(out.index("**Caveats:**"), out.index("### Reference RF-01"))

    def test_whole_method_outline_and_one_entry(self):
        code, out, _ = self.context("RF-02, RF-01:MarketRemover.fit, RF-01:outline")
        self.assertEqual(code, 0)
        self.assertIn(f"### Reference RF-02: references/tft_targets.py\n{BANNER}```python\n\"\"\"TFT target", out)
        self.assertIn("(MarketRemover.fit · lines 32–35 of 38)\n```python\n    def fit(self", out)
        self.assertIn("(outline)\n```\n6: def demean_returns", out)
        self.assertEqual(out.count("### RF-01: Market decomposition transforms"), 1)
        self.assertEqual(out.count("### Reference RF-01"), 2)

    def test_large_code_gets_outline(self):
        self.write("references/big.py", "def f():\n    '''F.'''\n" + "x = 1\n" * 320)
        self.add_entry("RF-03", "references/big.py")
        code, out, _ = self.context("RF-03")
        self.assertEqual(code, 0)
        self.assertIn("(322 lines, so outline only; name a part: RF-03:<symbol or heading>)\n```\n1: def f() — F.\n```",
                      out)
        self.assertNotIn("x = 1", out)

    def test_doc_reference(self):
        self.write("references/notes/hrp.md", "# HRP\nintro\n\n## Derivation\nstep one\n\n## Use\nlater\n")
        self.add_entry("RF-03", "references/notes/hrp.md")
        _, out, _ = self.context("RF-03")
        self.assertIn("```markdown\n# HRP\nintro\n", out)
        self.assertNotIn("> Caveats", out)
        code, out, _ = self.context("RF-03:derivation")
        self.assertEqual(code, 0)
        self.assertIn("(derivation · lines 4–5 of 8)\n```markdown\n## Derivation\nstep one\n```", out)

    def test_unknown_selector_and_missing_file(self):
        code, out, err = self.context("RF-01:nope")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("RF-01:nope names nothing", err)
        (self.root / "references/tft_targets.py").unlink()
        code, out, _ = self.context("RF-02")
        self.assertEqual(code, 0)
        self.assertIn("(missing: the entry's file isn't in references/; run reference-intake)", out)
        self.assertEqual(self.context("RF-07:x")[0], 1)

    def test_json(self):
        self.set_read("RF-01:residualize")
        data = json.loads(self.dt("context", "M1-T06", "--json")[1])
        self.assertEqual(data["read"], [{"ref": "RF-01:residualize", "kind": "reference",
                                         "where": "docs/references.md:5", "file": MD_FILE,
                                         "selector": "residualize", "shown": "part"}])


# ---- dt lint ------------------------------------------------------------------------------------

class LintTest(Base):
    def problems(self) -> set[tuple[str, str, str]]:
        return {(p.path, p.code, p.severity) for p in lint.lint(Repo(self.root))}

    def test_fixture_clean(self):
        self.assertEqual(self.problems(), set())

    def test_missing_ref_strips_selector(self):
        self.set_read("PL-02, RF-09:pca_factors")
        self.assertIn((PLAN, "missing-ref", "E"), self.problems())
        self.replace("docs/packages/quant/pipelines.md", "**Covers:** STAT-01–STAT-04, QR-02",
                     "**Covers:** STAT-01–STAT-04, QR-02 · **References:** RF-08 (remove_market)")
        self.assertIn(("docs/packages/quant/pipelines.md", "missing-ref", "E"), self.problems())

    def test_ref_file_and_hash(self):
        self.write(MD_FILE, "x = 2\n")
        self.assertIn((INDEX, "ref-hash", "W"), self.problems())
        (self.root / MD_FILE).unlink()
        found = self.problems()
        self.assertIn((INDEX, "ref-file", "E"), found)
        self.assertNotIn((INDEX, "ref-hash", "W"), found)

    def test_ref_large(self):
        self.write("references/big.py", "x = 1\n" * 301)
        self.add_entry("RF-03", "references/big.py")
        self.set_read("PL-02, RF-03")
        self.assertIn((PLAN, "ref-large", "W"), self.problems())
        self.set_read("PL-02, RF-03:outline")
        self.assertEqual(self.problems(), set())

    def test_ref_prefix(self):
        self.replace(SPEC, "- **QR-01** Every", "- **RF-01** Every")
        self.assertIn((SPEC, "ref-prefix", "E"), self.problems())

    def test_roadmap_skill(self):
        self.replace(ROADMAP, "**Skills:** data-science", "**Skills:** data-science, null-hypothesis-testing")
        found = [p for p in lint.lint(Repo(self.root)) if p.code == "roadmap-skill"]
        self.assertEqual([(p.path, p.line, p.severity) for p in found], [(ROADMAP, 14, "W")])
        self.assertIn("null-hypothesis-testing", found[0].message)

    def test_garbage_index_never_crashes(self):
        self.write(INDEX, "# R\n\n**Status:** Draft\n\n### RF-01: x\n**File:** · **Milestones:** ???\n### RF-02:\n")
        found = self.problems()
        self.assertIn((INDEX, "ref-file", "E"), found)
        self.assertFalse(any(code == "internal" for _, code, _ in found), found)


@unittest.skipUnless(HAS_GIT, "git not installed")
class StampIsNotAnApprovedEditTest(unittest.TestCase):
    def test_stamp(self):
        p = Project(git=True)
        self.addCleanup(p.cleanup)
        p.write(MD_FILE, "x = 2\n")
        self.assertEqual(run_dt(p.root, "references", "--stamp")[0], 0)
        self.assertEqual([str(x) for x in lint.lint(Repo(p.root)) if x.code == "approved-edit"], [])
        p.edit(INDEX, "- **Purpose:** forward", "- **Purpose:** backward")
        self.assertIn("approved-edit", {x.code for x in lint.lint(Repo(p.root))})


if __name__ == "__main__":
    unittest.main()
