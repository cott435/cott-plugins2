"""Probe replays for the dry run (design/probes.md §10), no model calls.

- `quant-incremental-probe`: the interface-first sample (its M1-T02 also reading `PB-01:samples`, since PB-01 is
  routed to M1) with a Sharadar decision that cites PB-01 and stays Proposed;
  api-probe New writes PB-01 (selftest/quant-probe/); the user's "ran it" runs its probe.py against the fake Sharadar
  (fakevendor/) with a canary key, through driver.run_user_checks; api-probe Record answers it from the evidence;
  architecture-design Revise folds the planted facts into the decision and accepts it. Every probe check passes.
- `quant-incremental-probebad`: the same run broken once per probe check: the decision Accepted before the probe,
  a check without a Pass criterion and DATA-02 not informed, no official docs and no contradiction before the run,
  a Verdict without the missing names, public.py reading the environment, a .gitignore without .env (the canary is
  committed), a tool call reading .env and one running probe.py, a user result written in the Record turn, an email
  in a sample, a 400+-line probe imported from tests/, pyproject.toml changed, and probe code edited in a Revise turn.

- `api-probe-good`, `api-probe-bad`: the api-probe skill fixture (probe_skill.py, §10.2) replayed with a good
  PB-03 and with one broken once per check. Every check passes in the first and fails in the second.

`run(out, tmp, ifd_fixture)` returns the unexpected results, as dryrun.verdict does.
"""
import json, pathlib, re, shutil

import driver, fakevendor, probe_skill, probefacts as pf
from dryrun import CONTENT, PLANNING, USER_RUN, copy_layer, replay, task_line, verdict

HERE = pathlib.Path(__file__).resolve().parent
OVERLAY = HERE / "selftest" / "quant-probe"
KIT = HERE / "selftest" / "probe_kit.py"
FOLDER = "probes/PB-01-sharadar"
CANARY = "sk-canary-dryrun0000"
# Probe checks that only dt can make pass (plan_blocked_while_open needs dt's probes_blocking): either way on a
# deliberately broken project.
DT_DEPENDENT = {"plan_blocked_while_open"}
PROBE_FAIL = {"probe_not_guess", "probe_checks_cover", "docs_before_probe", "planted_facts_reached_design",
              "no_secret_seen", "runner_split", "probe_small_isolated", "probe_code_in_probe_turns", "evidence_scan_clean"}
# dt lints the same planted defects (probe-fields, probe-leak, probe-runner), so its lint and the archived plan's
# lint fail too in the broken run.
PROBEBAD_DT_FAIL = {"dt_lint_clean", "sim_advance_3"}
# PB-01 is routed to M1 (its Milestones), so a task of M1's plan reads its samples (refs_skills_routed).
PROBE_READ = ("M1-T02", "**Read:** PL-01, data.Universe", "**Read:** PL-01, PB-01:samples, data.Universe")

AD04 = """### AD-04: Sharadar SEP for daily prices
**Status:** {status} · **Date:** 2026-10-15 · **Scope:** data
**Probe:** PB-01 — does Sharadar deliver 2006+ history, delisted members and raw and adjusted prices we can tell apart?
- **Context:** The user already subscribes to Sharadar.{docs}
- **Decision:** Sharadar's SEP, TICKERS and SP500 tables, read by `data`.
- **Alternatives:** EODHD — kept as the cross-check source.
- **Consequences:** History depth, delisted coverage and the membership start are unconfirmed until PB-01 is answered (Risks).

"""
DOCS_NOTE = (" Its docs (sharadar.com/docs/stocks, read 2026-10-15) say `close` is split-adjusted and only `closeunadj` "
             "is raw, so raw prices need `closeunadj`.")
RISK = "- Sharadar's history depth, delisted coverage and membership start: PB-01 (C2, C3, C6).\n"
FINDING = ("- **Finding:** PB-01 (2026-10-16): `close` is split-adjusted and raw prices come only from `closeunadj` (C4); "
           "prices and S&P 500 membership start 2007-01-03 (C2, C6), so DATA-01's 2006 target moves to 2007 and its 2011 "
           "floor holds; MER and WYE are missing (C3), so DATA-02's known-delisted list is checked against the cross-check source.\n")
RESULTS = {"C2": "fail: earliest 2007-01-03 for all five", "C3": "fail: 8 of 10; MER and WYE missing; BUD has two permatickers",
           "C4": "pass: closeunadj/close 4.0 before, 1.0 after; close is split-adjusted", "C6": "fail: earliest record 2007-01-03"}
VERDICT = ("fail — C2, C6: prices and membership start 2007-01-03 (DATA-01's 2011 floor met); C3: MER and WYE missing; "
           "C4: close is split-adjusted, raw only closeunadj")


def _sub(path, old, new):
    t = path.read_text()
    if old not in t:
        raise SystemExit(f"dryrun_probe: {old[:60]!r} not in {path.name}")
    path.write_text(t.replace(old, new, 1))


def arch_layer(fixture, accepted=False, docs=True):
    def f(proj):
        copy_layer(fixture, proj, ["docs/architecture.md", "docs/packages/quant/contract.md"])
        a = proj / "docs" / "architecture.md"
        _sub(a, "\n## Risks and open questions\n", "\n" + AD04.format(status="Accepted" if accepted else "Proposed",
                                                                     docs=DOCS_NOTE if docs else "") + "## Risks and open questions\n")
        _sub(a, "## Risks and open questions\n", "## Risks and open questions\n" + RISK)
    return f


def new_layer(bad=False):
    def f(proj):
        pf.install_tree(OVERLAY, proj)
        shutil.copy(KIT, proj / FOLDER / "probe_kit.py")
        if not bad:
            return
        pb = proj / "docs" / "probes.md"
        _sub(pb, "- **Informs:** AD-04 · DATA-01, DATA-02 ·", "- **Informs:** AD-04 · DATA-01 ·")
        _sub(pb, "(DATA-02)", "")
        _sub(pb, "| ≤ 2006-01-03 (DATA-02's point-in-time universe) |", "| — |")
        _sub(pb, "sharadar.com/docs/stocks; sharadar.com/blog/posts/sharadar-stock-prices-fund-prices-and-adjustments",
             "a forum thread on adjusted prices")
        (proj / ".gitignore").unlink()
        (proj / FOLDER / "public.py").write_text('import os\nKEY = os.environ.get("SHARADAR_API_KEY")\nprint("no public checks")\n')
        with open(proj / FOLDER / "probe.py", "a") as fh:
            fh.write("\n" + "\n".join(f"PAD_{i} = {i}" for i in range(420)) + "\n")
        (proj / "tests").mkdir(exist_ok=True)
        (proj / "tests" / "conftest.py").write_text('import sys\nsys.path.insert(0, "probes/PB-01-sharadar")\n')
        (proj / "pyproject.toml").write_text('[project]\nname = "quant"\nversion = "0.1.0"\ndependencies = ["requests"]\n')
    return f


def user_run_layer(vendors, log):
    return lambda proj: driver.run_user_checks(proj, vendors, log)


def record_layer(bad=False):
    def f(proj):
        res = json.loads((proj / FOLDER / "evidence" / "results.json").read_text())
        pb = proj / "docs" / "probes.md"
        _sub(pb, "**Hash:** —", f"**Hash:** {res['script_hash']}")
        _sub(pb, "**Status:** Ready", "**Status:** Answered · fail · 2026-10-16")
        _sub(pb, "**Last run:** —", f"**Last run:** {res['run_at']}")
        lines = pb.read_text().splitlines(keepends=True)
        for i, l in enumerate(lines):
            m = re.match(r"^\| (C\d+) \|", l)
            if m and l.rstrip().endswith("| — |"):
                lines[i] = l.rstrip()[:-3] + ("fail |" if bad else f"{RESULTS[m.group(1)]} |") + "\n"
        pb.write_text("".join(lines))
        _sub(pb, "- **Verdict:** —", "- **Verdict:** " + ("fail — 8 of 10 found" if bad else VERDICT))
        if bad:  # the agent rewrites a user check's result and leaks an email into a sample
            res["checks"]["C3"]["observed"]["found"] = 10
            (proj / FOLDER / "evidence" / "results.json").write_text(json.dumps(res, indent=1) + "\n")
            (proj / FOLDER / "evidence" / "samples" / "sep.json").write_text('[{"note": "ask ops@example.com"}]\n')
    return f


def revise_layer(bad=False):
    def f(proj):
        a = proj / "docs" / "architecture.md"
        t = a.read_text()
        t = t.replace("### AD-04: Sharadar SEP for daily prices\n**Status:** Proposed", "### AD-04: Sharadar SEP for daily prices\n**Status:** Accepted")
        t = t.replace(RISK, "")
        t = t.replace("- **Decision:** Sharadar's SEP", ("- **Finding:** PB-01 answered.\n" if bad else FINDING) + "- **Decision:** Sharadar's SEP")
        a.write_text(t)
        if bad:  # probe code edited outside an api-probe turn
            with open(proj / FOLDER / "probe.py", "a") as fh:
                fh.write("RETRIES = 3\n")
    return f


def stream(bad):
    """agent_stream.jsonl: one init per turn; the bad run reads .env in the New turn and runs probe.py in Record."""
    lines, calls = [], {4: [("Read", {"file_path": f"{FOLDER}/.env"}), ("Grep", {"pattern": "close", "path": f"{FOLDER}/out"})],
                        5: [("Bash", {"command": f"cd {FOLDER} && python3 probe.py"})]} if bad else {}
    for n in range(1, 7):
        lines.append({"type": "system", "subtype": "init"})
        for name, inp in calls.get(n, []):
            lines.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}})
        if bad and n == 4:
            lines.append({"type": "user", "message": {"content": [{"type": "tool_result", "content": f"SHARADAR_API_KEY={CANARY}"}]}})
    return "\n".join(json.dumps(l) for l in lines) + "\n"


def probe_fixture(tmp, good_fixture):
    """The interface-first sample whose M1 plan reads PB-01's samples (the probe is routed to M1)."""
    fx = tmp / "fixture-probe"
    shutil.copytree(good_fixture, fx, dirs_exist_ok=True)
    tid, old, new = PROBE_READ
    task_line(fx / "tasks" / "plan.md", tid, old, new)
    return fx


def run(out, tmp, good_fixture):
    scn = json.loads((HERE / "scenarios.json").read_text())
    cfg = scn["projects"]["quant"]["fake_vendors"]["sharadar"]
    good_fixture = probe_fixture(tmp, good_fixture)
    bad = []
    for name, broken in (("quant-incremental-probe", False), ("quant-incremental-probebad", True)):
        url, server = fakevendor.start("sharadar", out / f"{name}.vendor.jsonl", expect_key=CANARY)
        vendors = {"sharadar": {"url": url + cfg["path"], "server": server, "key": CANARY, "cfg": cfg}}
        try:
            layers = (PLANNING[:2] + [("architecture-design", arch_layer(good_fixture, accepted=broken, docs=not broken)),
                                      ("api-probe", new_layer(broken)),
                                      (USER_RUN, user_run_layer(vendors, out / f"{name}.user_runs.jsonl")),
                                      ("api-probe", record_layer(broken)), ("architecture-design", revise_layer(broken))]
                      + PLANNING[3:])
            run_dir, res, summ = replay(out, name, good_fixture, layers,
                                        summary_extra={"fake_vendors": ["sharadar"], "probe_canary": CANARY},
                                        stream=stream(broken))
        finally:
            server.shutdown()
        runs = [json.loads(l) for l in (out / f"{name}.user_runs.jsonl").read_text().splitlines() if l.strip()]
        if not any(r["script"].endswith("probe.py") and r["rc"] == 0 for r in runs):
            bad.append(f"{name}: the user run of probe.py failed: {runs}")
        bad += verdict(name, res, summ, CONTENT | (PROBE_FAIL | PROBEBAD_DT_FAIL if broken else set()),
                       either=DT_DEPENDENT if broken else ())
    for name, broken in (("api-probe-good", False), ("api-probe-bad", True)):
        g = probe_skill.replay(out, name, broken)
        res = {c["id"]: c for c in g["expectations"]}
        bad += verdict(name, res, g["summary"], set(res) if broken else set())
    return bad
