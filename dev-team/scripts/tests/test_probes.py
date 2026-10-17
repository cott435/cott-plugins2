"""Probes (design/probes.md): the parser, `dt status` keys, `dt context`, `dt probes --stamp/--scan`, the guard,
the lint codes and the results.json validator, on the quant fixture with fixtures/probes laid over it: PB-01
Answered pass, PB-02 Ready with the agent's C1 run and a planted email in a sample, PB-03 retired."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

from dt_helpers import FAKE_KEY, FixtureCopy, HERE, run_main

sys.path.insert(0, str(HERE.parent))

from devteam import model, probes as pb  # noqa: E402
from devteam.repo import Repo  # noqa: E402

PB01 = "probes/PB-01-sharadar-prices"
PB02 = "probes/PB-02-fred-rates"
SAMPLE = f"{PB02}/evidence/samples/observations.json"
CLEAN_SAMPLE = '{"realtime_start": "2001-10-17", "units": "<str:7>", "observations": []}\n'


class ProbeCase(FixtureCopy):
    probes = True

    def status(self, skill: str) -> dict:
        code, out, err = self.dt("status", "--skill", skill, "--json")
        self.assertEqual(err, "")
        return json.loads(out)

    def lint_codes(self, prefix: str = "probe-") -> list[tuple[str, int, str]]:
        _, out, _ = self.dt("lint", "--json")
        return [(p["path"], p["line"], p["code"]) for p in json.loads(out)["problems"] if p["code"].startswith(prefix)]

    def clean_sample(self):
        self.write(SAMPLE, CLEAN_SAMPLE)

    def stamp(self):
        self.assertEqual(self.dt("probes", "--stamp")[0], 0)


class ParserTest(ProbeCase):
    def test_entries(self):
        repo = Repo(self.root)
        p1, p2 = model.all_probes(repo)
        self.assertEqual((p1.id, p1.state, p1.verdict, p1.folder), ("PB-01", "Answered", "pass", PB01))
        self.assertEqual(p1.informs, ["AD-03", "DATA-01", "DATA-02", "data.RawPrices"])
        self.assertEqual((p1.decisions, p1.types, p1.milestones), (["AD-03"], ["data.RawPrices"], ["M1"]))
        self.assertEqual(p1.last_run, "2026-10-16T18:02:11Z")
        self.assertEqual((p2.state, p2.verdict, p2.last_run, p2.is_open), ("Ready", "", "", True))
        self.assertEqual([(c.id, c.runner) for c in p2.checks], [("C1", "agent"), ("C2", "user"), ("C3", "user")])
        self.assertEqual(p2.checks[1].passes, "First observation ≤ 2006-01-03")
        self.assertEqual(p2.checks[0].result, "")

    def test_check_rows_are_sections(self):
        code, out, _ = self.dt("section", "PB-01.C2", "--no-path")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("| C2 | History depth |"))

    def test_citations(self):
        cites = model.probe_citations(Repo(self.root))
        self.assertEqual([(c.decision, c.probe) for c in cites], [("AD-03", "PB-01"), ("AD-04", "PB-02")])

    def test_next_id_counts_retired_and_cited(self):
        self.assertEqual(self.dt("next-id", "PB")[1].strip(), "PB-04")
        self.replace("docs/architecture.md", "- **Probe:** PB-02", "- **Probe:** PB-07")
        self.assertEqual(self.dt("next-id", "PB")[1].strip(), "PB-08")

    def test_split_ref(self):
        self.assertEqual(model.split_ref("PB-01:probe.py:get"), ("PB-01", "probe.py:get"))
        self.assertEqual(model.split_ref("PB-01:samples"), ("PB-01", "samples"))


class HashTest(ProbeCase):
    def test_probe_kit_computes_the_same_hash(self):
        folder = self.root / PB01
        kit = subprocess.run([sys.executable, "-B", str(folder / "probe_kit.py")], capture_output=True, text=True)
        self.assertEqual(kit.returncode, 0, kit.stderr)
        spec = importlib.util.spec_from_file_location("probe_kit_fixture", folder / "probe_kit.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.code_hash(str(folder)), pb.code_hash(folder))
        self.assertEqual(pb.code_hash(folder), "5c7242e5")

    def test_hash_ignores_evidence_out_env_and_markdown(self):
        folder = self.root / PB02
        before = pb.code_hash(folder)
        self.write(f"{PB02}/README.md", "changed\n")
        self.write(f"{PB02}/evidence/extra.json", "{}\n")
        self.write(f"{PB02}/out/x.json", "{}\n")
        self.write(f"{PB02}/.env.local", "X=1\n")
        self.assertEqual(pb.code_hash(folder), before)
        self.write(f"{PB02}/probe.py", self.read(f"{PB02}/probe.py") + "# more\n")
        self.assertNotEqual(pb.code_hash(folder), before)
        self.assertEqual(pb.code_files(folder), ["probe.py", "probe_kit.py", "public.py"])


class ApiProbeStatusTest(ProbeCase):
    def test_fixture(self):
        r = self.status("api-probe")
        self.assertEqual(r["mode"], "record")
        self.assertEqual(r["probes_unwritten"], [])
        self.assertEqual(r["probes_open"], ["PB-02 (user: C2–C3)"])
        self.assertEqual(r["probes_results"], ["PB-02 (2026-10-17T09:30:00Z)"])
        self.assertEqual(r["probes_stale"], [])
        self.assertEqual(r["evidence_leaks"], [f"{SAMPLE}:2 (email)"])
        self.assertEqual(r["next_id"], "PB-04")

    def test_waiting_once_recorded(self):
        self.replace("docs/probes.md", "**Milestones:** M2 · **Last run:** —", "**Milestones:** M2 · **Last run:** 2026-10-17T09:30:00Z")
        r = self.status("api-probe")
        self.assertEqual((r["mode"], r["probes_results"]), ("waiting", []))
        self.assertEqual(r["probes_open"], ["PB-02 (user: C2–C3)"])

    def test_newer_run_is_results_again(self):
        self.replace("docs/probes.md", "**Last run:** —", "**Last run:** 2026-10-16")
        self.assertEqual(self.status("api-probe")["probes_results"], ["PB-02 (2026-10-17T09:30:00Z)"])

    def test_unwritten_is_new(self):
        self.replace("docs/architecture.md", "- **Probe:** PB-02", "- **Probe:** PB-04")
        r = self.status("api-probe")
        self.assertEqual((r["mode"], r["probes_unwritten"]), ("new", ["PB-04 (AD-04)"]))

    def test_changed_code_is_revise(self):
        self.write(f"{PB02}/public.py", self.read(f"{PB02}/public.py") + "# edited\n")
        r = self.status("api-probe")
        self.assertEqual(r["mode"], "revise")
        self.assertEqual(len(r["probes_stale"]), 1)
        self.assertTrue(r["probes_stale"][0].startswith("PB-02 (results "))

    def test_current_when_answered(self):
        self.replace("docs/probes.md", "**Status:** Ready · **Milestones:** M2 · **Last run:** —",
                     "**Status:** Answered · pass · 2026-10-17 · **Milestones:** M2 · **Last run:** 2026-10-17T09:30:00Z")
        self.clean_sample()
        r = self.status("api-probe")
        self.assertEqual((r["mode"], r["probes_open"], r["evidence_leaks"]), ("current", [], []))

    def test_invalid_results_listed(self):
        self.write(f"{PB02}/evidence/results.json", "{not json")
        self.assertTrue(self.status("api-probe")["probes_results"][0].startswith("PB-02 (results.json invalid: "))

    def test_summary_line(self):
        _, out, _ = self.dt("status", "--summary")
        self.assertIn("probes: 1 waiting → api-probe\n", out)


class OtherSkillsStatusTest(ProbeCase):
    def test_architecture_design_revise_on_fail(self):
        self.assertEqual(self.status("architecture-design")["probes_answered"], [])
        self.replace("docs/probes.md", "**Status:** Ready ·", "**Status:** Answered · fail · 2026-10-18 ·")
        r = self.status("architecture-design")
        self.assertEqual(r["mode"], "revise")
        self.assertEqual(r["probes_answered"], ["PB-02 fail (AD-04)"])
        self.assertEqual(r["probes_failed"], ["PB-02 (AD-04)"])
        self.replace("docs/architecture.md", "**Status:** Proposed · **Date:** 2026-10-17", "**Status:** Accepted · **Date:** 2026-10-18")
        r = self.status("architecture-design")
        self.assertEqual((r["probes_answered"], r["probes_failed"]), ([], []))
        self.assertNotEqual(r["mode"], "revise")

    def test_architecture_design_waived(self):
        self.replace("docs/probes.md", "**Status:** Ready ·", "**Status:** Waived · 2026-10-18 — I'll take the risk ·")
        r = self.status("architecture-design")
        self.assertEqual((r["mode"], r["probes_answered"], r["probes_failed"]), ("revise", ["PB-02 waived (AD-04)"], []))

    def test_build_planning_blocked_while_open(self):
        r = self.status("build-planning")
        self.assertEqual((r["mode"], r["blocked"]), ("blocked", "waiting for PB-02"))
        self.assertEqual(r["probes_blocking"], ["PB-02 → portfolio, portfolio.Comparison (M2)"])
        self.assertEqual(r["milestone_references"], ["PB-02"])
        self.assertEqual(r["references_unrouted"], ["PB-01 (M1)"])

    def test_build_planning_unblocked_when_answered_or_waived(self):
        self.replace("docs/probes.md", "**Status:** Ready ·", "**Status:** Answered · pass · 2026-10-18 ·")
        r = self.status("build-planning")
        self.assertEqual((r["mode"], r["probes_blocking"]), ("extend", []))
        self.replace("docs/probes.md", "**Status:** Answered · pass · 2026-10-18 ·", "**Status:** Waived · 2026-10-18 — mine ·")
        self.assertEqual(self.status("build-planning")["mode"], "extend")

    def test_build_planning_failed_blocks_until_revised(self):
        self.replace("docs/probes.md", "**Status:** Ready ·", "**Status:** Answered · fail · 2026-10-18 ·")
        self.assertEqual(self.status("build-planning")["mode"], "blocked")
        self.replace("docs/architecture.md", "**Status:** Proposed · **Date:** 2026-10-17", "**Status:** Accepted · **Date:** 2026-10-18")
        self.assertEqual(self.status("build-planning")["mode"], "extend")

    def test_build_planning_unmet_probe_does_not_block(self):
        self.replace("docs/architecture.md", "**Scope:** portfolio", "**Scope:** data")
        self.replace("docs/probes.md", "- **Informs:** AD-04 · PORT-02 · portfolio.Comparison", "- **Informs:** AD-04 · PORT-02")
        r = self.status("build-planning")
        self.assertEqual((r["mode"], r["probes_blocking"]), ("extend", []))

    def test_build_planning_unwritten_and_system_scope_block(self):
        self.replace("docs/architecture.md", "**Scope:** portfolio", "**Scope:** system")
        self.replace("docs/architecture.md", "- **Probe:** PB-02", "- **Probe:** PB-04")
        r = self.status("build-planning")
        self.assertEqual((r["mode"], r["probes_blocking"]), ("blocked", ["PB-02 → system, portfolio.Comparison (M2)",
                                                                         "PB-04 → system (M2)"]))

    def test_spec_writing_reserves_pb(self):
        self.assertIn("PB", self.status("spec-writing")["reserved_prefixes"])


class ContextTest(ProbeCase):
    def packet(self, read: str) -> tuple[int, str, str]:
        self.replace("tasks/plan.md", "**Read:** PL-01, data.RawPrices, DATA-01\n",
                     f"**Read:** PL-01, data.RawPrices, DATA-01, {read}\n")
        return self.dt("context", "M1-T02")

    def test_files_and_banner(self):
        code, out, err = self.packet("PB-01")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("### PB-01: Sharadar delivers raw", out)               # the entry, checks table included
        self.assertIn("| C2 | History depth |", out)
        self.assertIn(f"### Reference PB-01: {PB01}/\n", out)
        self.assertIn("> Never import from probes/.", out)
        self.assertIn("> Probe code: written to answer PB-01's checks, not to production standard.", out)
        self.assertIn("> Verdict: pass\n> Caveats: licensed data", out)
        self.assertIn("probe.py (24 lines)\nprobe_kit.py (21 lines)\nevidence/samples/sep.json (sample)", out)
        self.assertNotIn("out/raw.json", out)

    def test_samples(self):
        code, out, _ = self.packet("PB-01:samples")
        self.assertEqual(code, 0)
        self.assertIn(f"#### {PB01}/evidence/samples/sep.json\n```json\n[", out)

    def test_file_symbol(self):
        code, out, _ = self.packet("PB-01:probe.py:c1_raw_vs_adjusted")
        self.assertEqual(code, 0)
        self.assertIn(f"### Reference PB-01: {PB01}/probe.py\n", out)
        self.assertIn("(c1_raw_vs_adjusted · lines 15–19 of 24)", out)
        self.assertIn("def c1_raw_vs_adjusted():", out)
        self.assertNotIn("def c2_history_depth", out)

    def test_whole_file_and_outline(self):
        code, out, _ = self.packet("PB-01:probe.py")
        self.assertEqual(code, 0)
        self.assertIn("def c2_history_depth():", out)
        code, out, _ = self.dt("context", "M1-T02")
        self.replace("tasks/plan.md", "PB-01:probe.py\n", "PB-01:outline\n")
        code, out, _ = self.dt("context", "M1-T02", "--json")
        data = json.loads(out)
        read = [r for r in data["read"] if r["ref"] == "PB-01:outline"][0]
        self.assertEqual((read["kind"], read["shown"]), ("reference", "outline"))
        self.assertIn("def get(table, **params)", data["text"])

    def test_out_and_env_never_shown(self):
        for ref in ("PB-01:out/raw.json", "PB-02:.env", "PB-01:../PB-02-fred-rates/.env"):
            with self.subTest(ref=ref):
                self.setUp()
                code, out, err = self.packet(ref)
                self.assertEqual((code, out), (1, ""))
                self.assertIn("never shown", err)
                self.assertNotIn(FAKE_KEY, err)

    def test_unknown_file_or_symbol(self):
        code, _, err = self.packet("PB-01:nope.py")
        self.assertEqual(code, 1)
        self.assertIn("names no file", err)


class ProbesCommandTest(ProbeCase):
    def test_stamp(self):
        self.assertEqual(self.dt("probes", "--stamp")[1], "probes: nothing to stamp\n")
        self.write(f"{PB02}/probe.py", self.read(f"{PB02}/probe.py") + "# edited\n")
        new = pb.code_hash(self.root / PB02)
        code, out, _ = self.dt("probes", "--stamp", "PB-02")
        self.assertEqual((code, out), (0, f"PB-02: {new}\nprobes: stamped 1\n"))
        self.assertIn(f"**Folder:** `{PB02}/` · **Hash:** {new} · **Status:** Ready", self.read("docs/probes.md"))

    def test_stamp_inserts_missing_hash(self):
        self.replace("docs/probes.md", "**Hash:** bdf9f525 · ", "")
        self.assertEqual(self.dt("probes", "--stamp")[0], 0)
        self.assertIn(f"**Folder:** `{PB02}/` · **Hash:** bdf9f525 · **Status:** Ready", self.read("docs/probes.md"))

    def test_scan_names_pattern_never_text(self):
        code, out, _ = self.dt("probes", "--scan")
        self.assertEqual(code, 1)
        self.assertEqual(out, f"{SAMPLE}:2 (email)\nscan: 1 hit\n")
        self.assertNotIn("jane", out)
        self.clean_sample()
        self.assertEqual(self.dt("probes", "--scan"), (0, "scan: clean\n", ""))

    def test_scan_finds_env_value(self):
        self.write(f"{PB02}/evidence/samples/observations.json", f'{{"key": "{FAKE_KEY}"}}\n')
        code, out, _ = self.dt("probes", "--scan", "PB-02")
        self.assertEqual((code, out), (1, f"{SAMPLE}:1 (.env value)\nscan: 1 hit\n"))
        self.assertNotIn(FAKE_KEY, out)

    def test_list(self):
        _, out, _ = self.dt("probes")
        self.assertIn("PB-02: probes/PB-02-fred-rates · Ready · hash ok · results 2026-10-17T09:30:00Z "
                      "(current; 1/3 checks) · M2", out)


class ScanTest(unittest.TestCase):
    def test_patterns(self):
        cases = {
            '"t": "access-production-1234-abcd"': "token",
            "https://x.test/v1?api_key=abc&f=json": "credential in URL",
            '"k": "sk-canary-run42"': "secret key",
            "card 4111 1111 1111 1111": "card number",
            '"acct": "000123456789"': "long digit run",
            "call (555) 123-4567": "phone number",
            "id 5f1e09ab5f1e09ab5f1e09ab5f1e": "hex run",
            "b64 Zm9vYmFyQmF6UXV4MTIzNDU2Nzg5MEFCQ0RFRg==": "base64 run",
        }
        for text, name in cases.items():
            with self.subTest(text=text):
                self.assertEqual(pb.scan_text(text), [(1, name)])

    def test_shape_faithful_sample_is_clean(self):
        text = ('{"name": "<str:23>", "id": "<id>", "amount": -1.00, "date": "2001-03-05", "run_at": '
                '"2026-10-20T18:02:11Z", "script_hash": "5c1e09ab", "personal_finance_category_primary": "FOOD",'
                ' "counts": [12, 2024, 365], "base_url": "https://production.plaid.com"}')
        self.assertEqual(pb.scan_text(text), [])

    def test_env_secret_matched(self):
        self.assertEqual(pb.scan_text("x\nhas s3cr3tvalue in it", ["s3cr3tvalue"]), [(2, ".env value")])


class ResultsTest(unittest.TestCase):
    GOOD = {"probe": "PB-01", "script_hash": "5c1e09ab", "run_at": "2026-10-20T18:02:11Z", "runner": "user",
            "checks": {"C1": {"pass": True, "observed": {"n": 6}, "note": "ok"}, "C2": {"pass": None, "observed": 3}}}

    def check(self, data) -> list[str]:
        return [m for _, m in pb.validate(json.dumps(data, indent=1), "PB-01", ["C1", "C2", "C3"])[1]]

    def test_good(self):
        self.assertEqual(self.check(self.GOOD), [])

    def test_problems(self):
        bad = dict(self.GOOD, probe="PB-02", script_hash="xyz", run_at="yesterday", runner="robot",
                   checks={"C9": {"pass": "yes"}, "C1": []})
        self.assertEqual(self.check(bad), [
            "`probe` is 'PB-02', not PB-01", "`script_hash` is not 8 hex digits",
            "`run_at` is not an ISO 8601 date or time", "`runner` is 'robot', not agent or user",
            "check C9 is not in PB-01's checks table", "C9 `pass` must be true, false or null",
            "C9 has no `observed`", "C1 is not an object"])
        missing = {k: v for k, v in self.GOOD.items() if k not in ("runner", "checks")}
        self.assertEqual(self.check(missing), ["no `runner`", "no `checks`"])
        self.assertEqual(pb.validate("[1]", "PB-01", [])[1], [(1, "not a JSON object")])
        self.assertTrue(pb.validate("{", "PB-01", [])[1][0][1].startswith("not valid JSON"))

    def test_newer(self):
        self.assertTrue(pb.newer("2026-10-20T18:02:11Z", ""))
        self.assertFalse(pb.newer("2026-10-20T18:02:11Z", "2026-10-20T18:02:11Z"))
        self.assertTrue(pb.newer("2026-10-21T08:00:00Z", "2026-10-20T18:02:11Z"))
        self.assertFalse(pb.newer("2026-10-20T18:02:11Z", "2026-10-20"))
        self.assertTrue(pb.newer("2026-10-21T00:00:00Z", "2026-10-20"))


class GuardTest(ProbeCase):
    def guard(self, tool: str, path: str) -> str:
        code, out = run_main("--root", str(self.root), "guard", "--tool", tool, "--path", path)
        self.assertEqual(code, 0)
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "allow"

    def test_secrets_and_out(self):
        for tool in ("Read", "Edit", "Write"):
            for path in (".env", f"{PB02}/.env", ".env.local", "sub/project/.env.prod", f"{PB01}/out/raw.json",
                         f"{PB01}/out"):
                with self.subTest(tool=tool, path=path):
                    self.assertEqual(self.guard(tool, path), "deny")
            self.assertEqual(self.guard(tool, f"{PB02}/.env.example"), "allow")
        self.assertEqual(self.guard("Read", "docs/.environment.md"), "allow")

    def test_evidence_read_only(self):
        self.assertEqual(self.guard("Read", f"{PB01}/evidence/results.json"), "allow")
        for tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            self.assertEqual(self.guard(tool, f"{PB01}/evidence/results.json"), "deny")
        self.assertEqual(self.guard("Write", f"{PB01}/probe.py"), "allow")

    def test_read_skips_write_rules(self):
        self.assertEqual(self.guard("Read", "tasks/archive/M0-x.md"), "allow")
        self.assertEqual(self.guard("Read", "tests/fixtures/quant/TC-01/expected.json"), "allow")
        self.assertEqual(self.guard("Write", "tasks/archive/M0-x.md"), "deny")

    def test_hook_json(self):
        event = {"tool_name": "Read", "cwd": str(self.root), "tool_input": {"file_path": str(self.root / PB02 / ".env")}}
        code, out = run_main("guard", stdin=json.dumps(event))
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertNotIn(FAKE_KEY, out)
        event["tool_input"]["file_path"] = str(self.root / "tests/fixtures/quant/TC-01/expected.json")
        self.assertEqual(run_main("guard", stdin=json.dumps(event)), (0, ""))

    def test_hook_matcher_has_read(self):
        hooks = json.loads((HERE.parents[1] / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        matchers = [h["matcher"] for h in hooks["hooks"]["PreToolUse"] if "guard" in h["hooks"][0]["command"]]
        self.assertEqual(matchers, ["Read|Edit|Write|MultiEdit|NotebookEdit"])


class LintTest(ProbeCase):
    def test_fixture_only_the_planted_leak(self):
        self.assertEqual(self.lint_codes(), [(SAMPLE, 2, "probe-leak")])
        self.assertEqual([c for c in self.lint_codes("") if c[2] in ("missing-ref", "header", "budget")], [])

    def test_fields(self):
        self.clean_sample()
        self.replace("docs/probes.md", "| ≤ 2006-01-03 (DATA-01) | user |", "|  | user |")
        self.replace("docs/probes.md", "- **Question:** Does FRED", "- Question: Does FRED")
        self.replace("docs/probes.md", "**Status:** Answered · pass · 2026-10-16", "**Status:** Done")
        self.assertEqual([c[2] for c in self.lint_codes()], ["probe-fields"] * 3)

    def test_informs(self):
        self.replace("docs/probes.md", "AD-04 · PORT-02 · portfolio.Comparison", "AD-04 · PORT-09 · portfolio.Nope")
        codes = [c for c in self.lint_codes() if c[2] == "probe-informs"]
        self.assertEqual(len(codes), 2)

    def test_cite(self):
        self.replace("docs/architecture.md", "- **Probe:** PB-02 — does DTB3", "- **Probe:** PB-03 — does DTB3")
        self.replace("docs/architecture.md", "- **Probe:** PB-01 — are Sharadar's raw and adjusted closes told apart?",
                     "- **Probe:** none")
        codes = sorted(c[2] for c in self.lint_codes() if c[0] == "docs/architecture.md")
        self.assertEqual(codes, ["probe-cite", "probe-cite"])
        self.replace("docs/architecture.md", "- **Probe:** none", "- **Probe:** none — Sharadar's docs settle it")
        self.assertEqual(len([c for c in self.lint_codes() if c[2] == "probe-cite"]), 1)

    def test_runner(self):
        self.write(f"{PB02}/public.py", 'import os\nKEY = os.environ.get("FRED_API_KEY")  # read the key\n')
        self.replace("docs/probes.md", "| Public CSV, no key | DTB3 header row returned | agent |",
                     "| Public CSV, no key | DTB3 header row returned | me |")
        found = [(c[0], c[2]) for c in self.lint_codes() if c[2] == "probe-runner"]
        self.assertEqual(found, [("docs/probes.md", "probe-runner"), (f"{PB02}/public.py", "probe-runner")])

    def test_results_shape(self):
        self.write(f"{PB01}/evidence/results.json", json.dumps({
            "probe": "PB-01", "script_hash": "5c7242e5", "run_at": "2026-10-16T18:02:11Z", "runner": "user",
            "checks": {"C7": {"pass": True, "observed": 1}}}, indent=1))
        self.assertIn((f"{PB01}/evidence/results.json", 7, "probe-results"), self.lint_codes())

    def test_sample(self):
        self.replace("docs/packages/quant/contract.md", "**Cases:** two raw rows",
                     "**Cases:** two raw rows (PB-01 samples/sep.json#0, #1), a gap (PB-01 samples/gap.json#0)")
        found = [c for c in self.lint_codes() if c[2] == "probe-sample"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], "docs/packages/quant/contract.md")

    def test_stale_and_large(self):
        self.write(f"{PB01}/probe.py", self.read(f"{PB01}/probe.py") + "x = 1\n" * 400)
        found = [c[2] for c in self.lint_codes() if c[0] == "docs/probes.md"]
        self.assertEqual(sorted(found), ["probe-large", "probe-stale", "probe-stale"])
        _, out, _ = self.dt("lint", "--json")
        severities = {p["code"]: p["severity"] for p in json.loads(out)["problems"]}
        self.assertEqual((severities["probe-large"], severities["probe-stale"]), ("W", "W"))

    def test_missing_ref_covers_pb(self):
        self.replace("tasks/plan.md", "**Read:** PL-01, data.RawPrices, DATA-01\n",
                     "**Read:** PL-01, data.RawPrices, DATA-01, PB-01:samples, PB-07:probe.py:get\n")
        found = [c for c in self.lint_codes("missing-ref")]
        self.assertEqual(len(found), 1)
        _, out, _ = self.dt("lint", "tasks/plan.md")
        self.assertIn("missing-ref Read: PB-07 is not defined", out)

    def test_unwritten_citation_is_not_missing_ref(self):
        self.replace("docs/architecture.md", "- **Probe:** PB-02", "- **Probe:** PB-04")
        self.assertEqual(self.lint_codes("missing-ref"), [])

    def test_hook_lints_probe_files(self):
        self.write(f"{PB02}/public.py", "import os\nos.getenv('X')\n")
        event = {"hook_event_name": "PostToolUse", "cwd": str(self.root),
                 "tool_input": {"file_path": str(self.root / PB02 / "public.py")}}
        _, out = run_main("lint", "--hook", stdin=json.dumps(event))
        self.assertEqual(json.loads(out)["decision"], "block")
        self.assertIn("probe-runner", json.loads(out)["reason"])


if __name__ == "__main__":
    unittest.main()
