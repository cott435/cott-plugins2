"""The build commands on a git repo of fixtures/buildmini with a stub check.sh: dt ready --halves/--reserve,
dt claim, dt land, dt escalate, dt build, dt finding --from (build-phase.md §6)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from build_helpers import TC01_TEST, BuildCase, git
from dt_helpers import HAS_GIT

from devteam import buildstate as bs
from devteam import dispatch

SPINE = '"""The summarize step."""\n\n\ndef summarize(numbers):\n    return numbers\n'
UNIT = '"""Unit tests."""\n\n\ndef test_x() -> None:\n    assert True\n'


@unittest.skipUnless(HAS_GIT, "git not installed")
class StartTest(BuildCase):
    start = False

    def test_start(self):
        self.write("scratch.txt", "x")
        code, out = self.dt_json("build", "start", "M1")
        self.assertEqual((code, "isn't clean" in out["error"]), (1, True))
        (self.root / "scratch.txt").unlink()
        code, out = self.dt_json("build", "start", "M1")
        self.assertEqual((code, out["branch"]), (0, "build/M1"))
        self.assertEqual(git(self.root, "branch", "--show-current"), "build/M1")
        self.assertIn("**Build:** build/M1 started ", self.read("tasks/plan.md").splitlines()[2])
        self.assertEqual(self.status(), "")
        self.assertEqual(self.dt_json("build", "start", "M1")[0], 1)            # already started
        self.assertEqual(self.dt_json("build", "start", "M2")[0], 1)            # not the plan's milestone


@unittest.skipUnless(HAS_GIT, "git not installed")
class ReadyTest(BuildCase):
    def test_interface_first_then_barrier(self):
        r = self.ready()
        self.assertEqual([(x["id"], x["role"], x["agent_type"]) for x in r["rows"]], [("M1-T01", "solo", "implementer")])
        row = r["rows"][0]
        self.assertEqual(row["prompt"], f"You are the solo for M1-T01. Run `python3 {bs.DT_PY} claim M1-T01 --role solo`, "
                                        "then read the packet it names.")
        self.assertEqual((row["pkg"], row["kind"], row["remaining_cp"]), ("mini", "interface", 6))
        self.fake_land("M1-T01")
        r = self.ready()
        # rl9: testers found the interface's missing seams first, so they run during its review; code waits.
        self.assertEqual([(x["id"], x["role"]) for x in r["rows"]], [("M1-T01.mini", "reviewer"), ("M1-T03", "tester")])
        review = r["rows"][0]
        self.assertEqual((review["kind"], review["tasks"], review["lead"]), ("interface", ["M1-T01"], True))
        self.assertTrue(review["findings_file"].endswith("dt-build/reviews/M1-T01.mini.md"))
        self.assertIn("REVIEW M1-T01 mini: <n> findings, <c> Critical", review["prompt"])
        self.assertEqual({(h["id"], h["role"]) for h in r["held"]}, {("M1-T02", "solo")})
        self.assertTrue(all(h["why"].startswith("barrier:") for h in r["held"]))
        self.pass_barrier()
        r = self.ready()
        self.assertEqual([(x["id"], x["role"]) for x in r["rows"]], [("M1-T02", "solo"), ("M1-T03", "tester")])
        self.assertEqual(r["held"], [])

    def test_interface_review_gets_what_later_tasks_need(self):
        """rl9: the review checked the interface against the contract and missed the seams testers needed. Its
        prompt names `dt build needs`, which lists each later task's Read:, acceptance and golden cases."""
        self.fake_land("M1-T01")
        review = self.ready()["rows"][0]
        self.assertIn(f"`python3 {bs.DT_PY} build needs M1-T01`", review["prompt"])
        rows = self.dt_json("build", "needs", "M1-T01", "--json")[1]["tasks"]
        self.assertEqual([r["id"] for r in rows], ["M1-T02", "M1-T03", "M1-T04"])
        t03 = rows[1]
        self.assertEqual((t03["kind"], t03["mode"]), ("thicken", "split"))
        self.assertIn("core.summarize", t03["read"])
        self.assertEqual(t03["cases"], [{"id": "TC-01", "title": "Mean of four numbers",
                                         "expected": "count 4, total 10, mean 2.5"}])
        code, text, _ = self.dt("build", "needs", "M1-T01")
        self.assertEqual(code, 0)
        self.assertIn("## M1-T03: Mean in the summary (thicken, split)", text)
        self.assertIn("- TC-01 Mean of four numbers: expected count 4", text)
        code, out = self.dt_json("build", "needs", "M1-T09")
        self.assertEqual((code, "no checkpoint M1-T09" in out["error"]), (1, True))

    BARRIER = ("### Checkpoint after M1-T01 (barrier)\n"
               "- [ ] The interface code matches contract.md exactly: types, signatures, stubs, samples, exports\n"
               "- [ ] M1-T03's tester can write its tests from what is frozen\n\n")

    def test_interface_review_without_a_barrier_in_the_plan(self):
        """A plan with no barrier after the interface task (rl9): dt adds one, so nothing builds on the frozen
        interface before its review, and the review's findings write the checkpoint into the plan."""
        self.edit("tasks/plan.md", self.BARRIER, "")
        self.commit("plan without the interface barrier")
        self.fake_land("M1-T01")
        r = self.ready()
        self.assertEqual([(x["id"], x["kind"]) for x in r["rows"]], [("M1-T01.mini", "interface"), ("M1-T03", "thicken")])
        self.assertEqual({h["why"] for h in r["held"]}, {"barrier: checkpoint after M1-T01 not passed"})
        found = self.ctl / "M1-T01.mini.md"
        found.write_text("Important · Interface · tests/contracts/test_x.py the fake drops a field → keep it\n")
        code, out = self.dt_json("finding", "--from", str(found))
        self.assertEqual((code, out["outcome"], out["findings"]), (0, "passed", ["M1-R01"]))
        plan = self.read("tasks/plan.md")
        self.assertIn("tests/contracts/**\n\n### Checkpoint after M1-T01 (barrier)\n**Findings:**\n- M1-R01 Important", plan)
        self.assertLess(plan.index("Checkpoint after M1-T01"), plan.index("## Phase 1"))
        r = self.ready()
        self.assertEqual(([(x["id"], x["role"]) for x in r["rows"]], r["holds"]),
                         ([("M1-T02", "solo"), ("M1-T03", "tester")], []))     # the go still holds

    def test_a_checkpoint_straight_after_the_interface_is_a_barrier(self):
        self.edit("tasks/plan.md", "### Checkpoint after M1-T01 (barrier)", "### Checkpoint after M1-T01")
        self.commit("plain checkpoint")
        self.fake_land("M1-T01")
        r = self.ready()
        self.assertEqual([(x["id"], x["role"]) for x in r["rows"]], [("M1-T01.mini", "reviewer"), ("M1-T03", "tester")])
        self.assertTrue(r["held"] and all(h["why"].startswith("barrier:") for h in r["held"]))

    def test_reserve_and_cap(self):
        self.to_phase1()
        self.assertEqual(self.reserve("--cap", "1"), [("M1-T02", "solo")])
        out = self.ready("--cap", "1")
        self.assertEqual((out["rows"], out["over_cap"], out["in_flight"]), ([], 1, ["M1-T02.solo"]))
        self.assertEqual(self.reserve(), [("M1-T03", "tester")])                  # never listed twice
        self.assertEqual(self.reserve(), [])
        log = [json.loads(x)["event"] for x in (self.state() / "log.jsonl").read_text().splitlines()]
        self.assertEqual(log.count("reserve"), 2)

    def test_implementer_waits_for_its_tests_and_dependencies(self):
        self.to_phase1()
        git(self.root, "branch", "dt/M1-T03-tests")                               # the tester half landed
        self.assertEqual([(x["id"], x["role"]) for x in self.ready()["rows"]], [("M1-T02", "solo")])
        self.fake_land("M1-T02")
        self.assertEqual([(x["id"], x["role"]) for x in self.ready()["rows"]],
                         [("M1-T03", "implementer"), ("M1-T04", "solo")])

    def test_risk_external_needs_a_yes(self):
        self.edit("tasks/plan.md", "**Package:** mini · **Step:** PL-01 · **Kind:** wiring",
                  "**Risk:** external (writes to a server)\n**Package:** mini · **Step:** PL-01 · **Kind:** wiring")
        self.commit("risk")
        self.dt("build", "go")                          # the plan changed after the go
        self.to_phase1()
        self.fake_land("M1-T02")
        held = {h["id"]: h["why"] for h in self.ready()["held"]}
        self.assertTrue(held["M1-T04"].startswith("Risk: external"))
        self.assertEqual(self.dt_json("build", "resolve", "M1-T04", "--note", "yes, go")[0], 0)
        self.assertIn(("M1-T04", "solo"), [(x["id"], x["role"]) for x in self.ready()["rows"]])

    def test_a_replan_needs_a_new_go(self):
        self.to_phase1()
        self.edit("tasks/plan.md", "- [ ] TC-01 passes", "- [ ] TC-01 passes, mean rounded to 2 places")
        self.commit("replan")
        out = self.ready()
        self.assertEqual(out["rows"], [])
        self.assertTrue(out["holds"][0].startswith("go: the plan's tasks changed"))
        self.assertFalse(self.dt_json("build", "status")[1]["go_current"])
        self.assertEqual(self.dt_json("build", "go", "--note", "go with the replan")[0], 0)
        self.assertTrue(self.ready()["rows"])
        self.fake_land("M1-T02")                                 # a todo tick isn't a replan
        self.assertTrue(self.dt_json("build", "status")[1]["go_current"])

    def test_no_git(self):
        import shutil
        shutil.rmtree(self.root / ".git")
        code, out, err = self.dt("ready", "--halves")
        self.assertEqual(code, 1)
        self.assertIn("needs git", err)


@unittest.skipUnless(HAS_GIT, "git not installed")
class ClaimTest(BuildCase):
    def test_refuses_without_reservation_or_in_main(self):
        wt = self.worktree("a")
        code, _, err = self.claim("M1-T01", "solo", wt)
        self.assertEqual(code, 1)
        self.assertIn("not reserved", err)
        self.reserve()
        code, _, err = self.claim("M1-T01", "solo", self.root)
        self.assertIn("not the main checkout", err)
        code, _, err = self.claim("M1-T01", "tester", wt)
        self.assertIn("its halves are solo", err)

    def test_claim_writes_the_boundary_and_packet(self):
        self.reserve()
        wt = self.worktree("a")
        code, out, err = self.claim("M1-T01", "solo", wt)
        self.assertEqual(code, 0, err)
        self.assertRegex(out.splitlines()[0], r"^packet: /.*/wts/a/\.claude/packet\.md \(\d+ lines; read it in full\)$")
        self.assertIn("done: Done when `scripts/check.sh gate` passes", out)
        self.assertEqual(self.read(".claude/.task_writes", wt).splitlines(),
                         ["src/mini/__init__.py", "src/mini/__main__.py", "src/mini/types.py", "src/mini/summary.py",
                          "src/mini/pipeline.py", "tests/contracts/**"])
        self.assertEqual(self.read(".claude/.check_pkg", wt), "mini\n")
        self.assertEqual(self.read(".claude/.dt", wt), f"{bs.DT_PY}\n")
        self.assertEqual(git(wt, "rev-parse", "refs/worktree/checks-base"), self.head(wt))
        self.assertTrue(self.read(".claude/packet.md", wt).startswith("# Packet: M1-T01 solo\n"))
        self.assertEqual(git(wt, "status", "--porcelain"), "")                     # dt's files are excluded
        self.assertEqual((self.records("reserved"), self.records("claims")), ([], ["M1-T01.solo"]))
        claim = json.loads((self.state() / "claims/M1-T01.solo.json").read_text())
        self.assertEqual((claim["role"], claim["base"], claim["finished"], claim["branch"]),
                         ("solo", self.head(wt), False, "wt-a"))
        self.assertEqual(self.claim("M1-T01", "solo", wt)[0], 0)                   # idempotent in its own worktree
        other = self.worktree("b")
        self.assertIn("already claimed", self.claim("M1-T01", "solo", other)[2])

    def test_stale_base(self):
        old = self.worktree("old")                                               # before M1-T01 landed
        self.to_phase1()
        self.reserve()
        code, _, err = self.claim("M1-T02", "solo", old)
        self.assertEqual(code, 1)
        self.assertIn("stale base", err)
        self.assertIn("M1-T01", err)

    def test_tester_packet_has_no_source(self):
        self.edit("tasks/plan.md", "**Read:** PL-01, TC-01, SUM-02, core.Summary, core.summarize",
                  "**Read:** PL-01, TC-01, SUM-02, core.Summary, core.summarize, src/mini/__init__.py")
        self.commit("read a source file")
        self.dt("build", "go")                          # the plan changed after the go
        self.to_phase1()
        wt = self.run_half("M1-T03", "tester", {})
        packet = self.read(".claude/packet.md", wt)
        self.assertNotIn("### src/mini/__init__.py", packet)
        self.assertNotIn("## Layout", packet)
        self.assertIn("### TC-01: Mean of four numbers", packet)
        self.assertIn("- tests/intent/mini/test_tc01.py (new)", packet)
        self.assertNotIn("- src/mini/summary.py", packet)
        self.assertEqual(self.read(".claude/.task_writes", wt), "tests/intent/mini/test_tc01.py\n")

    def test_worktree_links(self):
        self.write("CONSTRAINTS.md", "# Constraints\n\n**Status:** Approved\n\n**Worktree links:** `data/raw/`, .env\n")
        self.commit("constraints")
        (self.root / "data/raw").mkdir(parents=True)
        (self.root / "data/raw/prices.csv").write_text("x\n")
        git(self.root, "update-index", "--refresh")
        self.write(".git/info/exclude", "/data/\n")
        self.reserve()
        wt = self.worktree("a")
        code, out, err = self.claim("M1-T01", "solo", wt)
        self.assertIn("links: data/raw: linked; .env: never linked", out)
        self.assertTrue((wt / "data/raw").is_symlink())
        self.assertEqual((wt / "data/raw/prices.csv").read_text(), "x\n")


@unittest.skipUnless(HAS_GIT, "git not installed")
class LandTest(BuildCase):
    def test_solo_squash_with_trailer_tick_and_release(self):
        self.to_phase1()
        pre = self.head()
        wt = self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE, "tests/unit/mini/test_summary.py": UNIT})
        git(wt, "add", "-A")
        git(wt, "commit", "-q", "-m", "one")                                     # committed and uncommitted both land
        self.write("tests/unit/mini/test_summary.py", UNIT + "\n# more\n", root=wt)
        out = self.land("M1-T02", "solo")
        self.assertEqual((out["landed"], out["reject"], out["flaky"]), (True, None, False))
        self.assertEqual(git(self.root, "rev-parse", "HEAD^"), pre)                # one commit, not a merge
        self.assertEqual(git(self.root, "log", "-1", "--format=%P").count(" "), 0)
        msg = git(self.root, "log", "-1", "--format=%B")
        self.assertEqual(msg.splitlines()[0], "M1-T02: summarize spine (count, total)")
        self.assertIn("Dt-Landed: M1-T02 solo", msg)
        self.assertEqual(sorted(git(self.root, "show", "--name-only", "--format=", "HEAD").splitlines()),
                         ["src/mini/summary.py", "tasks/todo.md", "tests/unit/mini/test_summary.py"])
        self.assertIn("- [x] M1-T02", self.read("tasks/todo.md"))
        self.assertEqual(self.read("tests/unit/mini/test_summary.py"), UNIT + "\n# more\n")
        self.assertEqual(self.status(), "")
        self.assertEqual(self.records("claims"), [])
        self.assertFalse(wt.exists())
        self.assertNotIn("wt-M1-T02-solo", git(self.root, "branch"))
        self.assertEqual(git(self.root, "rev-parse", "refs/worktree/checks-base"), self.head())
        gates = [c for c in self.calls() if c.endswith(" gate --pkg mini")]
        self.assertEqual(len(gates), 2)                                          # worktree, then merged tree
        self.assertTrue(gates[1].startswith(str(self.root.resolve())))
        self.assertEqual(bs.landings(self.root)["M1-T02"]["role"], "solo")

    def test_split_task_end_to_end(self):
        self.to_phase1()
        before = self.head()
        wt = self.run_half("M1-T03", "tester", {"tests/intent/mini/test_tc01.py": TC01_TEST})
        out = self.land("M1-T03", "tester")
        self.assertTrue(out["landed"])
        self.assertEqual(self.head(), before)                                     # the build branch isn't touched
        self.assertFalse((self.root / "tests/intent").exists())
        tests = git(self.root, "rev-parse", "dt/M1-T03-tests")
        self.assertEqual(git(self.root, "rev-parse", "dt/M1-T03-tests^"), before)
        self.assertIn("Dt-Landed: M1-T03 tester", git(self.root, "log", "-1", "--format=%B", tests))
        self.assertEqual(git(self.root, "show", "--name-only", "--format=", tests), "tests/intent/mini/test_tc01.py")
        self.assertTrue(any(c.endswith(" collect") for c in self.calls()))
        self.assertFalse(wt.exists())
        self.assertEqual(self.dt_json("build", "status")[1]["tests_landed"], ["M1-T03"])

        self.fake_land("M1-T02")
        wt = self.run_half("M1-T03", "implementer", {"src/mini/summary.py": SPINE + "# mean\n"})
        self.assertEqual(self.read("tests/intent/mini/test_tc01.py", wt), TC01_TEST)   # merged in by dt claim
        self.assertEqual(self.read(".claude/.task_writes", wt),
                         "src/mini/summary.py\ntests/unit/mini/test_summary.py\n")
        out = self.land("M1-T03", "implementer")
        self.assertTrue(out["landed"], out)
        files = sorted(git(self.root, "show", "--name-only", "--format=", "HEAD").splitlines())
        self.assertEqual(files, ["src/mini/summary.py", "tasks/todo.md", "tests/intent/mini/test_tc01.py"])
        self.assertIn("Dt-Landed: M1-T03 implementer", git(self.root, "log", "-1", "--format=%B"))
        # The merged tree's gate ran against a base holding the tests, so they weren't the implementer's change.
        base_line = [c for c in self.calls() if c.startswith(str(self.root.resolve()) + " gate")]
        self.assertEqual(len(base_line), 1)

    def test_prune_leaves_live_work_alone(self):
        self.to_phase1()
        self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE, "src/mini/extra.py": "x = 1\n"})
        self.assertEqual(self.land("M1-T02", "solo")["reject"], "writes")      # its branch is left behind
        self.run_half("M1-T03", "tester", {"tests/intent/mini/test_tc01.py": TC01_TEST})
        self.assertTrue(self.land("M1-T03", "tester")["landed"])
        live = self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE}, name="live")
        code, out = self.dt_json("build", "prune", "--dry-run")
        self.assertEqual([r["branch"] for r in out["would_prune"]], ["wt-M1-T02-solo"])
        self.assertIn("wt-M1-T02-solo", git(self.root, "branch"))               # a dry run deletes nothing
        self.assertEqual(self.dt_json("build", "prune")[0], 0)
        branches = git(self.root, "branch")
        self.assertNotIn("wt-M1-T02-solo", branches)
        self.assertIn("wt-live", branches)                                     # a live claim's
        self.assertIn("dt/M1-T03-tests", branches)                             # M1-T03 isn't done
        self.assertTrue(live.exists())
        self.assertTrue(self.land("M1-T02", "solo")["landed"])
        self.run_half("M1-T03", "implementer", {"src/mini/summary.py": SPINE + "# mean\n"})
        self.assertTrue(self.land("M1-T03", "implementer")["landed"])
        self.dt_json("build", "prune")
        self.assertNotIn("dt/M1-T03-tests", git(self.root, "branch"))

    def test_writes_reject_then_redispatch(self):
        self.to_phase1()
        wt = self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE, "src/mini/extra.py": "x = 1\n"})
        out = self.land("M1-T02", "solo")
        self.assertEqual((out["landed"], out["reject"], out["rejects"]), (False, "writes", 1))
        detail = open(out["detail_file"]).read()
        self.assertIn("- src/mini/extra.py", detail)
        self.assertNotIn("- src/mini/summary.py", detail.split("reject: writes")[1])
        self.assertFalse(wt.exists())
        self.assertIn("wt-M1-T02-solo", git(self.root, "branch"))                # kept after a reject
        self.assertEqual((self.records("claims"), self.records("reserved")), ([], ["M1-T03.tester"]))
        self.assertEqual(self.status(), "")
        self.assertIn(("M1-T02", "solo"), self.reserve())                          # re-dispatched once
        wt2 = self.worktree("again")
        code, msg, _ = self.claim("M1-T02", "solo", wt2)
        self.assertIn("previous rejection: writes, details in", msg)
        self.write("src/mini/extra.py", "x = 1\n", root=wt2)
        self.assertEqual(self.land("M1-T02", "solo")["reject"], "writes")
        held = {h["id"]: h["why"] for h in self.ready()["held"]}
        self.assertEqual(held["M1-T02"], "rejected 2 times (last: writes)")         # second time: blocked
        self.assertEqual(self.dt_json("build", "resolve", "M1-T02")[0], 0)
        self.assertIn(("M1-T02", "solo"), [(r["id"], r["role"]) for r in self.ready()["rows"]])

    def test_protected_reject_and_tester_allowance(self):
        self.edit("tasks/plan.md", "**Depends on:** M1-T01 · **Writes:** src/mini/summary.py, tests/unit/mini/test_summary.py",
                  "**Depends on:** M1-T01 · **Writes:** src/mini/summary.py, tests/unit/mini/test_summary.py, pyproject.toml")
        self.commit("a protected path in Writes")
        self.dt("build", "go")                          # the plan changed after the go
        self.to_phase1()
        self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE, "pyproject.toml": "[project]\n"})
        out = self.land("M1-T02", "solo")
        self.assertEqual(out["reject"], "writes")
        self.assertIn("on the protected list:\n- pyproject.toml", open(out["detail_file"]).read())
        # tests/intent/** is protected, but it is the tester's own allowance.
        self.run_half("M1-T03", "tester", {"tests/intent/mini/test_tc01.py": TC01_TEST})
        self.assertTrue(self.land("M1-T03", "tester")["landed"])

    def test_gate_reject_and_verdict_reuse(self):
        self.to_phase1()
        wt = self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE})
        self.assertEqual(self.hook("--root", str(wt), "build", "verdict", "--mode", "gate", "--rc", "1")[0], 0)
        gate = json.loads((self.state() / "gates/M1-T02.solo.json").read_text())
        self.assertEqual((gate["passed"], gate["tree"]), (False, bs.tree_hash(wt)))
        before = len(self.calls())
        out = self.land("M1-T02", "solo")
        self.assertEqual(out["reject"], "gate")
        self.assertIn("reused the Stop gate's verdict", open(out["detail_file"]).read())
        self.assertFalse(any(" gate" in c for c in self.calls()[before:]))          # the stub never ran the gate
        self.assertEqual(self.records("gates"), [])

        wt = self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE}, name="second")
        self.hook("--root", str(wt), "build", "verdict", "--mode", "gate", "--rc", "0")
        self.write("src/mini/summary.py", SPINE + "# changed after the verdict\n", root=wt)
        self.stub("gate", 1)
        out = self.land("M1-T02", "solo")
        self.assertEqual(out["reject"], "gate")                                    # the tree changed: gate re-ran
        self.assertIn("stub gate: exit 1", open(out["detail_file"]).read())

    def test_escalated(self):
        self.to_phase1()
        git(self.root, "branch", "dt/M1-T03-tests")
        self.fake_land("M1-T02")
        wt = self.run_half("M1-T03", "implementer", {})
        self.assertEqual(self.hook("--root", str(wt), "build", "escalated")[0], 1)
        code, out, _ = self.dt("escalate", "test-wrong", "TC-01's `mean` uses the wrong count", root=wt)
        self.assertEqual(code, 0)
        self.assertIn("STOPPED M1-T03 implementer: see dt escalate", out)
        self.assertEqual(self.hook("--root", str(wt), "build", "escalated")[0], 0)
        self.assertEqual(self.hook("--root", str(wt / "src"), "build", "escalated")[0], 0)   # from a subfolder
        out = self.land("M1-T03", "implementer")
        self.assertEqual((out["reject"], out["kind"]), ("escalated", "TEST-WRONG"))
        held = {(h["id"], h["role"]): h["why"] for h in self.ready()["held"]}
        self.assertTrue(held[("M1-T03", "implementer")].startswith("escalated TEST-WRONG"))
        code, res = self.dt_json("build", "resolve", "M1-T03", "--note", "the test is wrong")
        self.assertEqual((res["reopened_tester"], res["escalations_cleared"]), (True, ["M1-T03.implementer"]))
        self.assertIn(("M1-T03", "tester"), [(r["id"], r["role"]) for r in self.ready()["rows"]])

    def test_escalated_with_its_worktree_gone(self):
        self.to_phase1()
        wt = self.run_half("M1-T02", "solo", {})
        self.dt("escalate", "needs-dep", "needs numpy", root=wt)
        git(self.root, "worktree", "remove", "--force", str(wt))               # Claude Code drops a clean worktree
        out = self.land("M1-T02", "solo")
        self.assertEqual((out["reject"], out["kind"], out["harness_failures"]), ("escalated", "NEEDS-DEP", 0))

    def test_test_stands_retries_the_implementer(self):
        self.to_phase1()
        git(self.root, "branch", "dt/M1-T03-tests")
        self.fake_land("M1-T02")
        wt = self.run_half("M1-T03", "implementer", {})
        self.dt("escalate", "test-wrong", "TC-01 looks off", root=wt)
        self.land("M1-T03", "implementer")
        code, res = self.dt_json("build", "resolve", "M1-T03", "--test-stands", "--note", "TC-01 is right")
        self.assertEqual((res["reopened_tester"], res["test_stands"]), (False, True))
        self.assertIn("refs/heads/dt/M1-T03-tests", git(self.root, "for-each-ref", "refs/heads/dt"))
        rows = [(r["id"], r["role"]) for r in self.ready()["rows"]]
        self.assertIn(("M1-T03", "implementer"), rows)
        self.assertNotIn(("M1-T03", "tester"), rows)
        self.reserve()
        code, out, _ = self.claim("M1-T03", "implementer", self.worktree("again"))
        self.assertIn("the user decided the intent tests stand", out)

    def test_two_escalations_on_one_claim_keep_both(self):
        self.to_phase1()
        wt = self.run_half("M1-T03", "tester", {})
        self.dt("escalate", "CONTRACT-CHANGE", "summarize can't take a window", "--type", "core.summarize", root=wt)
        self.dt("escalate", "NEEDS-DEP", "needs numpy", root=wt)
        out = self.land("M1-T03", "tester")
        self.assertEqual((out["reject"], out["kind"]), ("escalated", "NEEDS-DEP"))
        _, st = self.dt_json("build", "status")
        esc = st["escalations"][0]
        self.assertEqual([e["kind"] for e in esc["earlier"]], ["CONTRACT-CHANGE"])
        self.assertEqual(esc["types"], ["core.summarize"])

    def test_escalate_needs_a_claim_and_the_right_role(self):
        self.to_phase1()
        wt = self.worktree("loose")
        self.assertEqual(self.dt("escalate", "NEEDS-DEP", "numpy", root=wt)[0], 1)
        wt = self.run_half("M1-T03", "tester", {})
        self.assertEqual(self.dt("escalate", "TEST-WRONG", "x", root=wt)[0], 2)
        self.assertEqual(self.dt("escalate", "NEEDS-DEP", "needs numpy", root=wt)[0], 0)
        self.assertEqual(self.land("M1-T03", "tester")["kind"], "NEEDS-DEP")
        ready = self.ready()
        self.assertEqual(ready["rows"], [])                                        # NEEDS-DEP drains everything
        self.assertTrue(ready["holds"][0].startswith("escalation: M1-T03.tester NEEDS-DEP"))

    def test_contract_change_holds_readers_and_dependents_of_its_type(self):
        self.to_phase1()
        self.assertEqual(self.reserve(), [("M1-T02", "solo"), ("M1-T03", "tester")])
        wt = self.worktree("t03")
        self.assertEqual(self.claim("M1-T03", "tester", wt)[0], 0)
        self.assertEqual(self.dt("escalate", "CONTRACT-CHANGE", "x", "--type", "core.Nope", root=wt)[0], 2)
        self.assertEqual(self.dt("escalate", "NEEDS-DEP", "x", "--type", "core.Summary", root=wt)[0], 2)
        code, _, _ = self.dt("escalate", "CONTRACT-CHANGE", "summarize can't take a window", "--type",
                             "core.summarize", root=wt)
        self.assertEqual(code, 0)
        self.assertEqual(self.land("M1-T03", "tester")["kind"], "CONTRACT-CHANGE")
        self.dt("build", "release", "M1-T02", "solo")
        ready = self.ready()
        held = {(h["id"], h["role"]): h["why"] for h in ready["held"]}
        self.assertEqual((ready["rows"], ready["holds"]), ([], []))            # held by type, not globally
        self.assertEqual(held[("M1-T02", "solo")],
                         "escalation: M1-T03.tester CONTRACT-CHANGE on core.summarize, which M1-T02 reads")
        self.assertTrue(held[("M1-T03", "tester")].startswith("escalated CONTRACT-CHANGE"))
        self.dt("build", "resolve", "M1-T03")
        self.assertEqual({(r["id"], r["role"]) for r in self.ready()["rows"]},
                         {("M1-T02", "solo"), ("M1-T03", "tester")})

    def test_contract_change_holds_the_escalating_tasks_dependents(self):
        self.to_phase1()
        self.reserve()
        wt = self.worktree("t02")
        self.assertEqual(self.claim("M1-T02", "solo", wt)[0], 0)
        self.dt("escalate", "CONTRACT-CHANGE", "Numbers needs a unit", "--type", "core.Numbers", root=wt)
        self.land("M1-T02", "solo")
        self.dt("build", "release", "M1-T03", "tester")
        held = {(h["id"], h["role"]): h["why"] for h in self.ready()["held"]}
        self.assertEqual(held[("M1-T03", "tester")],                          # M1-T03 doesn't read core.Numbers
                         "escalation: M1-T02.solo CONTRACT-CHANGE on core.Numbers; M1-T03 depends on M1-T02")
        code, out = self.dt_json("build", "status")
        self.assertEqual([b["id"] for b in out["blocked"]], ["M1-T02"])        # the hold isn't a block

    def test_integration_reject_resets(self):
        self.to_phase1()
        pre = self.head()
        self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE, "tests/unit/mini/test_summary.py": UNIT})
        self.stub("gate", 0, 1, 1)                                                 # worktree passes; merged fails twice
        out = self.land("M1-T02", "solo")
        self.assertEqual(out["reject"], "integration")
        self.assertEqual((self.head(), self.status()), (pre, ""))
        self.assertNotIn("- [x] M1-T02", self.read("tasks/todo.md"))
        self.assertIn("dependents: M1-T03, M1-T04", open(out["detail_file"]).read())
        self.assertEqual(git(self.root, "rev-parse", "refs/worktree/checks-base"), pre)

    def test_flaky_rerun_lands_with_a_finding(self):
        self.to_phase1()
        self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE, "tests/unit/mini/test_summary.py": UNIT})
        self.stub("gate", 0, 1, 0)
        out = self.land("M1-T02", "solo")
        self.assertEqual((out["landed"], out["flaky"]), (True, True))
        plan = self.read("tasks/plan.md")
        self.assertIn("- M1-R01 Important · flaky · M1-T02 the integration gate failed, then passed on its rerun", plan)
        self.assertLess(plan.index("Checkpoint: milestone exit"), plan.index("M1-R01"))
        self.assertIn("tasks/plan.md", git(self.root, "show", "--name-only", "--format=", "HEAD"))

    def test_conflict_resets(self):
        self.to_phase1()
        self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE})
        self.write("src/mini/summary.py", "something else\n")
        pre = self.commit("another task wrote the same file")
        out = self.land("M1-T02", "solo")
        self.assertEqual(out["reject"], "conflict")
        self.assertEqual((self.head(), self.status()), (pre, ""))

    def test_harness(self):
        self.to_phase1()
        self.assertEqual(self.reserve(), [("M1-T02", "solo"), ("M1-T03", "tester")])
        out = self.land("M1-T02", "solo")                                          # reserved, never claimed
        self.assertEqual((out["reject"], out["harness_failures"], out["rejects"]), ("harness", 1, 0))
        self.assertNotIn("M1-T02.solo", self.records("reserved"))
        wt = self.run_half("M1-T02", "solo", {})
        self.assertEqual(self.land("M1-T02", "solo")["reject"], "harness")         # unfinished, no changes
        self.assertFalse(wt.exists())
        self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE}, name="third")
        self.assertEqual(self.land("M1-T02", "solo", "--harness")["harness_failures"], 3)
        held = {h["id"]: h["why"] for h in self.ready()["held"]}
        self.assertEqual(held["M1-T02"], "3 harness failures in a row")

    def test_preconditions(self):
        self.to_phase1()
        self.write("dirty.txt", "x")
        code, out = self.dt_json("land", "M1-T02", "--role", "solo")
        self.assertEqual(code, 1)
        self.assertIn("isn't clean", out["error"])
        (self.root / "dirty.txt").unlink()
        self.assertEqual(self.dt_json("land", "M1-T09", "--role", "solo")[0], 2)
        self.assertEqual(self.dt_json("land", "M1-T02", "--role", "tester")[0], 2)
        wt = self.worktree("x")
        self.assertEqual(self.dt_json("land", "M1-T02", "--role", "solo", root=wt)[0], 2)

    def test_lock(self):
        self.to_phase1()
        self.run_half("M1-T02", "solo", {"src/mini/summary.py": SPINE})
        state = bs.State(self.root)
        held, release = threading.Event(), threading.Event()

        def hold():
            with state.lock(5):
                held.set()
                release.wait(5)

        t = threading.Thread(target=hold)
        t.start()
        held.wait(5)
        try:
            code, out = self.dt_json("land", "M1-T02", "--role", "solo", "--lock-timeout", "0.3")
            self.assertEqual(code, 3)
            self.assertIn("land.lock", out["error"])
            self.assertEqual(self.records("claims"), ["M1-T02.solo"])               # nothing happened
        finally:
            release.set()
            t.join()
        self.assertTrue(self.land("M1-T02", "solo")["landed"])

    def test_wiring_runs_prebuild_clear(self):
        self.to_phase1()
        self.fake_land("M1-T02")
        self.run_half("M1-T04", "solo", {"src/mini/pipeline.py": "x = 1\n", "tests/unit/mini/test_pipeline.py": UNIT})
        self.assertTrue(self.land("M1-T04", "solo")["landed"])
        pipelines = self.read("docs/packages/mini/pipelines.md")
        self.assertNotIn("Entry sketch (pre-build", pipelines)
        self.assertIn("Layout: `dt layout mini`", pipelines)
        self.assertIn("docs/packages/mini/pipelines.md", git(self.root, "show", "--name-only", "--format=", "HEAD"))


@unittest.skipUnless(HAS_GIT, "git not installed")
class HookTest(BuildCase):
    def test_mark_finished_by_cwd(self):
        self.to_phase1()
        wt = self.run_half("M1-T02", "solo", {})
        self.assertEqual(self.hook("build", "mark-finished", stdin="not json"), (0, ""))
        self.assertEqual(self.hook("build", "mark-finished", stdin=json.dumps({"cwd": str(self.root)})), (0, ""))
        self.assertFalse(json.loads((self.state() / "claims/M1-T02.solo.json").read_text())["finished"])
        code, out = self.hook("build", "mark-finished",
                              stdin=json.dumps({"cwd": str(wt / "src"), "agent_type": "implementer"}))
        self.assertEqual((code, out), (0, ""))
        claim = json.loads((self.state() / "claims/M1-T02.solo.json").read_text())
        self.assertEqual((claim["finished"], claim["stop_agent_type"]), (True, "implementer"))
        status = self.dt_json("build", "status")[1]
        self.assertEqual([(c["id"], c["finished"]) for c in status["claims"]], [("M1-T02.solo", True)])
        self.assertEqual(self.ready()["in_flight"], ["M1-T03.tester"])           # a finished claim isn't in flight
        # A finished claim with no changes goes to the gate, not to harness.
        self.assertEqual(self.land("M1-T02", "solo")["reject"], None)

    def test_submit_review_copies_into_the_common_dir(self):
        wt = self.worktree("rev")
        self.write(".dt/review.md", "Nit · readability · `src/mini/x.py:1::f` name → rename\n", root=wt)
        code, out, _ = self.dt("build", "submit-review", "M1-T01.mini", ".dt/review.md", root=wt)
        self.assertEqual(code, 0, out)
        dest = Path(json.loads(out)["file"])
        self.assertEqual(dest.parent.name, "reviews")
        self.assertIn("`src/mini/x.py:1::f`", dest.read_text())
        self.assertEqual(self.dt("build", "submit-review", "bogus", ".dt/review.md", root=wt)[0], 2)

    def test_verdict_and_escalated_outside_a_claim(self):
        wt = self.worktree("loose")
        self.assertEqual(self.hook("--root", str(wt), "build", "verdict", "--mode", "gate", "--rc", "0"), (0, ""))
        self.assertEqual(self.records("gates"), [])
        self.assertEqual(self.hook("--root", str(wt), "build", "escalated")[0], 1)


@unittest.skipUnless(HAS_GIT, "git not installed")
class FindingFromTest(BuildCase):
    LINES = ("# Review M1-T01 mini\n\n"
             "Critical · CR-09 · `src/mini/types.py:3::Summary` has no `mean` field → add `mean: float | None`\n"
             "- Important · tests · `tests/contracts/core.Summary/sample.json` holds no mean → add one\n"
             "Checklist: [x] types\n")

    def test_records_commits_and_holds(self):
        self.fake_land("M1-T01")
        self.reserve("--cap", "1")
        path = self.state() / "reviews" / "M1-T01.mini.md"
        path.write_text(self.LINES, encoding="utf-8")
        code, out = self.dt_json("finding", "--from", str(path))
        self.assertEqual(code, 0, out)
        self.assertEqual((out["outcome"], out["findings"], out["critical"], out["tasks"]),
                         ("critical", ["M1-R01", "M1-R02"], ["M1-R01"], ["M1-T01"]))
        plan = self.read("tasks/plan.md")
        self.assertIn("**Findings:**\n- M1-R01 Critical · CR-09 · `src/mini/types.py:3::Summary` has no `mean` field "
                      "→ add `mean: float | None`\n- M1-R02 Important · tests · "
                      "`tests/contracts/core.Summary/sample.json` holds no mean → add one\n", plan)
        self.assertLess(plan.index("M1-R02"), plan.index("## Phase 1"))
        self.assertEqual(self.status(), "")
        self.assertEqual(git(self.root, "log", "-1", "--format=%s"), "M1-T01 review, mini: 2 findings, 1 Critical")
        self.assertEqual(self.records("reserved"), [])
        self.assertEqual(json.loads((self.state() / "reviews/M1-T01.mini.json").read_text())["outcome"], "critical")
        ready = self.ready()
        self.assertEqual(ready["rows"], [])
        self.assertTrue(ready["holds"][0].startswith("critical: M1-R01"))
        self.assertEqual(self.dt_json("finding", "--from", str(path))[1]["already_recorded"], True)
        self.assertEqual(self.read("tasks/plan.md"), plan)
        self.assertEqual(self.dt_json("build", "resolve", "m1-r01", "--note", "fixed by a re-freeze")[0], 0)
        self.assertEqual([(r["id"], r["role"]) for r in self.ready()["rows"]], [("M1-T02", "solo"), ("M1-T03", "tester")])
        status = self.dt_json("build", "status")[1]
        self.assertEqual(status["findings"], {"Critical": 1, "Important": 1})
        self.assertEqual(status["reviews"][0]["critical_open"], [])

    def test_the_file_decides_not_the_status_line(self):
        """A3-RT r2, r3: the reviewer's line said `1 Critical` while its file filed the finding as Important. The
        driver acts on what dt records from the file (loop.md), so nothing stops."""
        self.fake_land("M1-T01")
        path = self.ctl / "M1-T01.mini.md"
        path.write_text("Important · correctness · `src/mini/summary.py:4::summarize` could be Critical: an empty "
                        "list raises → return a zero summary\n", encoding="utf-8")
        code, out = self.dt_json("finding", "--from", str(path))
        self.assertEqual((code, out["outcome"], out["critical"]), (0, "passed", []))
        self.assertEqual(self.ready()["holds"], [])

    def test_explicit_checkpoint_and_errors(self):
        self.fake_land("M1-T01")
        path = self.ctl / "findings.md"
        path.write_text("Nit · naming · `a` → b\n", encoding="utf-8")
        self.assertEqual(self.dt_json("finding", "--from", str(path))[0], 2)          # no checkpoint in the name
        code, out = self.dt_json("finding", "--from", str(path), "--checkpoint", "exit", "--pkg", "mini")
        self.assertEqual((code, out["checkpoint"], out["outcome"]), (0, "exit", "passed"))
        self.assertEqual(self.dt_json("finding", "--from", str(self.ctl / "missing.md"))[0], 1)

    def test_exit_review_after_all_landed(self):
        for t in ("M1-T01", "M1-T02", "M1-T03", "M1-T04"):
            self.fake_land(t, "implementer" if t == "M1-T03" else "solo")
        self.pass_barrier()
        rows = self.ready()["rows"]
        self.assertEqual([(r["id"], r["kind"], r["tasks"]) for r in rows],
                         [("exit.mini", "exit", ["M1-T01", "M1-T02", "M1-T03", "M1-T04"])])
        self.assertEqual(len(rows[0]["commits"]), 4)
        self.assertEqual(rows[0]["end"], self.head())
        # minilab: the exit review repeated what the checkpoints had reviewed. It covers the whole diff, but
        # reviews and mutation-checks code only for tasks no checkpoint covered.
        self.assertEqual(rows[0]["reviewed"], ["M1-T01"])
        self.assertIn("A checkpoint already reviewed M1-T01: run the Milestone exit list over the whole diff, and "
                      "review and mutation-check code only for M1-T02, M1-T03, M1-T04.", rows[0]["prompt"])

    def test_phase_review_rows_name_no_reviewed_tasks(self):
        self.fake_land("M1-T01")
        row = self.ready()["rows"][0]
        self.assertEqual((row["kind"], row["reviewed"]), ("interface", []))
        self.assertNotIn("already reviewed", row["prompt"])


@unittest.skipUnless(HAS_GIT, "git not installed")
class StatusTest(BuildCase):
    def test_resume_view(self):
        self.to_phase1()
        self.reserve()
        wt = self.worktree("t03")
        self.claim("M1-T03", "tester", wt)
        self.assertEqual(self.dt_json("build", "release", "M1-T02", "solo")[1]["dropped"], ["reserved"])
        code, s = self.dt_json("build", "status")
        self.assertEqual(code, 0)
        self.assertEqual((s["milestone"], s["branch"], s["progress"]), ("M1", "build/M1", "1/4"))
        self.assertTrue(s["go"].startswith("build/M1 started"))
        self.assertEqual(s["landed"][0]["task"], "M1-T01")
        self.assertEqual(s["reserved"], [])
        self.assertEqual([(c["id"], c["finished"]) for c in s["claims"]], [("M1-T03.tester", False)])
        self.assertEqual(s["ready"], [{"id": "M1-T02", "role": "solo"}])
        self.assertEqual(s["next_checkpoint"]["checkpoint"], "exit")
        self.assertEqual(s["reviews"][0]["review"], "M1-T01.mini")
        events = [json.loads(x)["event"] for x in (self.state() / "log.jsonl").read_text().splitlines()]
        self.assertEqual(events[:1] + events[-3:], ["start", "reserve", "claim", "release"])


# Runs an emitted workflow script in node with a scripted agent(): dispatch rows from a queue, builders that finish
# after a delay (T02's first run without a status line), a land/record/status agent per call. Prints the result and
# every call, with the most main-checkout agents (dispatch, land, record, status) and builders ever alive at once.
NODE_SIM = r"""
const fs = require('fs')
const src = fs.readFileSync(process.argv[2], 'utf8').replace(/^export const meta/m, 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const run = new AsyncFunction('agent', 'log', 'phase', 'parallel', 'pipeline', 'args', 'budget', src)
const queue = [
  { rows: [{ id: 'M1-T01', role: 'solo', agent_type: 'implementer', prompt: 'p' },
           { id: 'M1-T02', role: 'tester', agent_type: 'tester', prompt: 'p' }], holds: [], all_landed: false },
  { rows: [{ id: 'M1-T02', role: 'tester', agent_type: 'tester', prompt: 'p' }], holds: [], all_landed: false },
  { rows: [], holds: [], all_landed: false },
  { rows: [{ id: 'M1-T01.mini', role: 'reviewer', agent_type: 'reviewer', prompt: 'review it', checkpoint: 'M1-T01', pkg: 'mini' }],
    holds: [], all_landed: false },
]
const calls = []
let main = 0, maxMain = 0, builders = 0, maxBuilders = 0, t02 = 0
const sleep = ms => new Promise(r => setTimeout(r, ms))
const MAIN = /^(dispatch|land|record|release|status)/
async function agent(prompt, opts) {
  calls.push({ prompt, opts })
  const label = opts.label
  if (MAIN.test(label)) {
    main += 1; maxMain = Math.max(maxMain, main); await sleep(2); main -= 1
    if (label.startsWith('dispatch')) return queue.shift() || { rows: [], holds: [], all_landed: true }
    if (label.startsWith('land')) return prompt.includes('--harness') ? { landed: false, reject: 'harness', kind: null, detail_file: '/d/1' }
                                                                       : { landed: true, reject: null, kind: null, detail_file: '/d/2' }
    if (label.startsWith('record')) return { outcome: 'passed', findings: ['M1-R01'], critical: [] }
    return { progress: '2/2', all_landed: true, go_current: true, next_checkpoint: 'exit', holds: [], blocked: [], held: [],
             escalations: [], critical_open: [], claims: [] }
  }
  builders += 1; maxBuilders = Math.max(maxBuilders, builders)
  const [id, role] = label.split(' ')
  let text = 'DONE ' + id + ' ' + role
  if (role === 'reviewer') { await sleep(5); text = 'REVIEW M1-T01 mini: 1 findings, 0 Critical' }
  else if (id === 'M1-T02') { await sleep(5); t02 += 1; if (t02 === 1) text = 'I ran out of turns' }
  else await sleep(60)
  builders -= 1
  return 'some report\n\n`' + text + '`'
}
run(agent, () => {}, () => {}, null, null, undefined, { total: null })
  .then(result => console.log(JSON.stringify({ result, calls, maxMain, maxBuilders })))
  .catch(e => { console.error(e && e.stack || e); process.exit(1) })
"""


@unittest.skipUnless(HAS_GIT, "git not installed")
class WorkflowTest(BuildCase):
    def emit(self, *extra: str) -> str:
        code, out, err = self.dt("build", "workflow", "M1", *extra)
        self.assertEqual(code, 0, out + err)
        return out

    def test_script(self):
        text = self.emit("--cap", "4")
        self.assertTrue(text.startswith("export const meta = {"))
        self.assertIn(json.dumps(f"python3 {bs.DT_PY} --root {self.root.resolve()}"), text)
        self.assertIn(str(bs.DT_PY), text)
        self.assertIn("const CAP = 4\n", text)
        self.assertIn(" ready --reserve --cap ' + CAP + ' --json", text)
        self.assertIn(json.dumps(dispatch.builder_prompt("@@TASK@@", "@@ROLE@@")), text)
        self.assertIn("dt-build/reviews", text)
        self.assertIsNone(re.search(r"M\d+-T\d+", text), "the script must not hold the plan's tasks")
        self.assertIn("const CAP = 6\n", self.emit())

    def test_out_and_refusals(self):
        code, out = self.dt_json("build", "workflow", "M1", "--out", ".dt/build.workflow.js")
        self.assertEqual((code, out["cap"], out["build_started"]), (0, 6, True))
        self.assertEqual(Path(out["workflow"]), self.root.resolve() / ".dt/build.workflow.js")
        self.assertEqual(self.read(".dt/build.workflow.js"), self.emit())
        self.assertEqual(self.dt_json("build", "workflow", "M2")[0], 1)          # not the active plan's milestone
        self.assertEqual(self.dt_json("build", "workflow", "M1", "--cap", "0")[0], 2)
        wt = self.worktree("wf")
        self.assertEqual(self.dt_json("build", "workflow", "M1", root=wt)[0], 2)  # only in the main checkout

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_runs_as_dataflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "build.workflow.js"
            path.write_text(self.emit(), encoding="utf-8")
            sim = Path(tmp) / "sim.js"
            sim.write_text(NODE_SIM, encoding="utf-8")
            r = subprocess.run(["node", str(sim), str(path)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        res, calls = out["result"], out["calls"]
        self.assertEqual(out["maxMain"], 1)                       # the main checkout: one dt call at a time
        self.assertEqual(out["maxBuilders"], 2)                   # T01 and T02 built at once
        self.assertEqual([(x["id"], x["role"], x["status"], x["landed"], x["reject"]) for x in res["landings"]],
                         [("M1-T02", "tester", "none", False, "harness"), ("M1-T02", "tester", "DONE", True, None),
                          ("M1-T01", "solo", "DONE", True, None)])
        self.assertEqual(res["reviews"], [{"review": "M1-T01.mini", "outcome": "passed", "findings": 1, "critical": []}])
        self.assertEqual((res["all_landed"], res["exit_ready"], res["next_checkpoint"]), (True, False, "exit"))
        builds = [c for c in calls if c["opts"].get("isolation")]
        self.assertTrue(all(c["opts"]["isolation"] == "worktree" for c in builds))
        self.assertEqual([(c["opts"]["label"], c["opts"]["agentType"]) for c in builds],
                         [("M1-T01 solo", "implementer"), ("M1-T02 tester", "tester"), ("M1-T02 tester", "tester"),
                          ("M1-T01.mini reviewer", "reviewer")])
        self.assertEqual(builds[0]["prompt"], dispatch.builder_prompt("M1-T01", "solo"))
        self.assertEqual(builds[-1]["prompt"], "review it")
        lands = [c["prompt"] for c in calls if c["opts"]["label"].startswith(("land", "record"))]
        self.assertIn(f"--root {self.root.resolve()} land M1-T02 --role tester --harness`", lands[0])
        self.assertIn("land M1-T02 --role tester`", lands[1])
        self.assertIn("finding --from ", lands[3])
        self.assertIn("/dt-build/reviews/M1-T01.mini.md --checkpoint M1-T01 --pkg mini`", lands[3])
        labels = [c["opts"]["label"] for c in calls]
        self.assertEqual(sum(x.startswith("dispatch") for x in labels), 5)   # once, then after every landing
        self.assertEqual(labels[-1], "status")
        self.assertTrue(all(c["opts"].get("effort") == "low" for c in calls if not c["opts"].get("isolation")))


if __name__ == "__main__":
    unittest.main()
