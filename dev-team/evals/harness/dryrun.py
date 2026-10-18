#!/usr/bin/env python3
"""Dry run of the harness with no model calls: stage and check the plugin, then fake trajectories from dt's sample
project (scripts/tests/fixtures/quant, a valid single-package project mid-M1), grade them, and compare every check
with the result pinned here. It is also the grader's self-test for the interface-first checks.

Each replay copies one planning layer per turn (brief → spec → architecture → reference intake → M2 idea →
pipelines → tests → plan → build setup), keeps the plan snapshot per turn as driver.py does, grades the run and
exports its plan.json. The replays:
- `quant-incremental`: the sample as it is (its interface-first M1), then its M1 code as a final "build" turn.
- `quant-incremental-ifd`: the sample with an interface-first M1 (§5.3 of design/interface-first-design.md):
  selftest/quant-interface-first/ laid over it. No code. Every interface-first check passes.
- `quant-incremental-ifdbad`: the same plan broken once per check (shared Writes, a mitigated edge in Depends on,
  a `none:` without a valid reason, a missing row, an M-size spine, a fake on a data edge, a type missing from the
  contract, a types.py written during planning, a frozen type revised later, ...). Each of those checks fails.
- `quant-incremental-ifdserial`: the spines chained one after another and the testers made solo. The parallelism
  and wave-width checks fail.
- `quant-incremental-requests`: the interface-first sample with the user's words recorded (design/requests.md):
  the replayed user states scenario facts and each skill appends them to docs/requests.md and traces them. The three
  requests_* checks pass.
- `quant-incremental-requestsbad`: the same record rewritten (a quote reworded, a line deleted), a stated fact never
  recorded, a trace to no ID, a malformed line. The requests_* checks fail, and dt's lint with them.
- the probe replays (dryrun_probe.py): `quant-incremental-probe` and `-probebad` (design/probes.md §10.1, a user run
  against the fake Sharadar), and the api-probe fixture's `api-probe-good` and `-bad` (§10.2, probe_skill.py).
Every check is pinned, pass or fail: the checks the sample can't meet (it isn't a finished four-stage quant run)
fail in every replay, and in the broken replays dt itself (lint, `dt ready`, `dt archive`) catches the planted
defects alongside the grader. Before the replays it runs selftest/checks.py: a good and a bad case for each
structural rule (dtrun.py, probefacts.py) that the iteration-7 and -8 findings changed; selftest/sessions.py: when the driver opens a
fresh agent session; and selftest/yahoo.py: the fake Yahoo's planted facts through the HTTPS proxy.

Usage: dryrun.py [out-dir]   (default: a fresh temp dir; printed at the end). Exit 1 on any unexpected result.
"""
import json, re, shutil, subprocess, sys, tempfile, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver, dtrun, planexport, plugin  # noqa: E402

FIXTURE = plugin.PLUGIN_SRC / "scripts" / "tests" / "fixtures" / "quant"  # the sample of the dt being staged
IFD_OVERLAY = HERE / "selftest" / "quant-interface-first"
# (skill, paths) per turn, in planning order; the user approves each.
LAYERS = [
    ("idea-refine", ["docs/brief.md", "docs/roadmap.md"]),
    ("spec-writing", ["docs/spec.md"]),
    ("architecture-design", ["docs/architecture.md", "docs/packages/quant/contract.md"]),
    ("reference-intake", ["references", "docs/references.md"]),  # M2's reference arrives with the M2 idea
    ("idea-refine", ["docs/ideas"]),
    ("pipeline-design", ["docs/packages/quant/pipelines.md"]),
    ("test-planning", ["docs/packages/quant/tests.md", "tests/fixtures"]),
    ("build-planning", ["tasks", "AGENTS.md"]),
    ("build-setup", ["CONSTRAINTS.md", ".claude"]),
    (None, ["src"]),  # M1-T01 already built: the fixture is mid-M1
]
PLANNING = [l for l in LAYERS if l[0]]

# What a single-package sample mid-M1 can't meet, in every replay.
CONTENT = {"quant_multi_from_data", "approval_after_user", "nh_named", "nh_at_features", "nh_routed_in_plan",
           "spec_bias_guards", "spec_classical", "spec_ml_beats_classical", "spec_oos", "data_sources_suggested", "arch_viz_boundary",
           "refs_milestones", "skills_on_data_tasks", "skills_on_structure_tasks"}
BAD_FAIL = {"graph_metrics", "writes_disjoint", "edges_mitigated", "unmitigated_reasoned", "no_edge_to_code_when_interface",
            "edge_table_consistent", "phase0_split", "step_tasks_small", "tester_starts_early", "fakes_only_cross_pipeline",
            "tasks_not_editing_plan", "interface_coverage", "types_in_contract", "tasks_well_formed",
            "no_code_during_planning", "doc_budgets",
            # dt sees the same defects: lint errors, no `dt ready` past the cycle, an archive that isn't lint-clean.
            "dt_lint_clean", "sim_ready_2", "sim_ready_3", "sim_advance_3"}
# Chained spines also contradict their mitigated rows (dt's `edges` lint agrees), and solo testers break the Mode rule.
SERIAL_FAIL = {"plan_parallelism", "wave_width", "dt_lint_clean", "sim_ready_2", "tasks_well_formed",
               "no_edge_to_code_when_interface", "edge_table_consistent"}
# The user's words (design/requests.md). dt's sample has no docs/requests.md and the replayed user says only "Plan my
# quant lab." and "Approved.", so outside the requests replays each check is n/a: captured (no scenario fact stated),
# honoured (no record to lint), append-only (no record ever committed).
REQUESTS_NA = {"requests_captured", "requests_honoured", "requests_append_only"}
# The broken record: a quote reworded and a line deleted (append-only), WebSocket and minimum-variance said but not on
# any line (captured), a trace to an undefined DATA-99 and a malformed line (honoured). dt sees the same errors:
# dt_lint_clean, and sim_advance_3's archive that isn't lint-clean.
REQUESTS_BAD_FAIL = REQUESTS_NA | {"dt_lint_clean", "sim_advance_3"}
REQ_USERS = {1: "Plan my quant lab: daily US equities from my Sharadar subscription, delisted names included, and "
                "minimum-variance portfolios before any ML.",
             2: "Approved. The viz app gets live progress over a WebSocket."}
REQ_HEAD = ("# Quant Lab — User requests\n\n**Last updated:** 2026-10-15\n\nThe user's words, verbatim: one line per "
            "fact, constraint, tool, choice or answer, with the skill that heard it and the date. The words never change; "
            "only the trace after → does. Written with `dt request`.\n\n")
UR = {1: 'architecture · "daily US equities from my Sharadar subscription" · idea-refine 2026-10-15',
      2: 'spec · "delisted names included" · idea-refine 2026-10-15',
      3: 'spec · "minimum-variance portfolios before any ML" · idea-refine 2026-10-15',
      4: 'architecture · "The viz app gets live progress over a WebSocket." · spec-writing 2026-10-15'}
REQ_GOOD = {1: [f"- **UR-0{i}** {UR[i]}" for i in (1, 2, 3)],  # recorded untraced, then traced: only traces change
            2: [f"- **UR-01** {UR[1]}", f"- **UR-02** {UR[2]} → DATA-02", f"- **UR-03** {UR[3]} → PORT-01",
                f"- **UR-04** {UR[4]}"],
            3: [f"- **UR-01** {UR[1]} → §Tech stack", f"- **UR-02** {UR[2]} → DATA-02", f"- **UR-03** {UR[3]} → PORT-01",
                f'- **UR-04** {UR[4]} → changed: no viz app in M1 (approved "fine, later", architecture-design 2026-10-15)']}
REQ_BAD = {1: REQ_GOOD[1],
           2: ['- **UR-01** architecture · "Sharadar data" · idea-refine 2026-10-15', f"- **UR-02** {UR[2]} → DATA-99",
               "- **UR-04** spec · no quotes · spec-writing 2026-10-15"]}


def copy_layer(fixture, proj, paths):
    """Copy a layer's paths from the fixture; a path the fixture doesn't have (yet) is skipped."""
    for p in paths:
        src, dst = fixture / p, proj / p
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy(src, dst)


def intake_agents(proj):
    """What reference-intake's stream would show: one read-only subagent per reference file."""
    refs = sorted(p for p in (proj / "references").rglob("*") if p.is_file()) if (proj / "references").is_dir() else []
    return [{"subagent_type": "general-purpose", "description": f"Summarize {p.name}",
             "prompt": f"Read {p.relative_to(proj)} and draft its reference entry."} for p in refs]


def ifd_fixture(tmp):
    """The interface-first sample: the overlay laid over dt's sample, whichever plan the sample has, so the
    good, bad and serial replays (and their mutations) don't depend on the sample's own plan text."""
    fx = tmp / "fixture-ifd"
    shutil.copytree(FIXTURE, fx, ignore=shutil.ignore_patterns("src"))
    shutil.copytree(IFD_OVERLAY, fx, dirs_exist_ok=True)
    return fx


def sub(path, old, new, count=1):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f"dryrun: mutation target not found in {path.name}: {old[:70]!r}")
    path.write_text(text.replace(old, new, count))


def task_line(plan, tid, old, new):
    """Replace text inside one task's section."""
    text = plan.read_text()
    m = re.search(rf"^### {tid}:.*?(?=^#{{2,3}} )", text, re.S | re.M)
    if not m or old not in m.group(0):
        raise SystemExit(f"dryrun: {old!r} not in {tid}")
    plan.write_text(text[:m.start()] + m.group(0).replace(old, new, 1) + text[m.end():])


def break_shape(fx):
    """One defect per interface-first check (see the module docstring)."""
    plan, pls = fx / "tasks" / "plan.md", fx / "docs" / "packages" / "quant" / "pipelines.md"
    task_line(plan, "M1-T06", "**Writes:** src/quant/stats/pca.py", "**Writes:** src/quant/stats/pca.py, src/quant/stats/rmt.py")
    task_line(plan, "M1-T05", "**Size:** XS", "**Size:** M")
    task_line(plan, "M1-T09", "**Depends on:** M1-T04", "**Depends on:** M1-T08, M1-T04")
    task_line(plan, "M1-T03", "**Depends on:** M1-T01", "**Depends on:** M1-T01, M1-T10")  # a cycle
    task_line(plan, "M1-T08", "**Writes:** src/quant/data/pipeline.py, ", "**Writes:** ")
    task_line(plan, "M1-T11", "stats.clean_eigen\n", "stats.clean_eigen, stats.shrink_target\n")
    task_line(plan, "M1-T12", "stats.estimate_cov\n", "stats.estimate_cov, stats.shrink_target\n")
    task_line(plan, "M1-T14", "tests/unit/quant/test_system_smoke.py", "tests/unit/quant/test_system_smoke.py, tasks/todo.md")
    task_line(plan, "M1-T07", "**Kind:** spine · ", "")
    sub(plan, "| M1-T05 clean_eigen spine | M1-T04 estimate_cov spine | data | stats.Cov sample (M1-T01) |",
        "| M1-T05 clean_eigen spine | M1-T04 estimate_cov spine | data | stats.CovMatrix sample (M1-T01) |")
    sub(plan, "| M1-T06 pca spine | M1-T05 clean_eigen spine | data | stats.Cov sample (M1-T01) |",
        "| M1-T06 pca spine | M1-T05 clean_eigen spine | data | stats.clean_eigen fake (M1-T01) |")
    # A code edge between two different steps' tasks (unmitigated_reasoned judges structure, not wording).
    task_line(plan, "M1-T12", "**Depends on:** M1-T04", "**Depends on:** M1-T04, M1-T05")
    sub(plan, "| M1-T12 shrinkage | M1-T04 estimate_cov spine | code | none: thickens the same module |\n",
        "| M1-T12 shrinkage | M1-T04 estimate_cov spine | code | none: thickens the same module |\n"
        "| M1-T12 shrinkage | M1-T05 clean_eigen spine | code | none: simpler this way |\n")
    sub(plan, "| M1-T13 PCA check | M1-T06 pca spine | code | none: thickens the same module |\n",
        "| M1-T99 ghost | M1-T01 | data | none: same module |\n")
    sub(plan, "## Open questions", "\n".join(f"- filler risk line {i}" for i in range(300)) + "\n\n## Open questions")
    # A type no contract section defines (types_in_contract), and a cross-owner boundary (load_prices' Prices into
    # estimate_cov) whose type names no case (interface_coverage).
    sub(pls, "| 3 | `compare` | portfolio | Weights, Returns → Comparison |", "| 3 | `compare` | portfolio | Weights, Returns → ComparisonFrame |")
    sub(pls, "| 2 | `estimate_cov` | stats | Returns → Cov |", "| 2 | `estimate_cov` | stats | Prices → Cov |")
    sub(fx / "docs" / "packages" / "quant" / "contract.md", "- **Sample:** tests/contracts/data.Prices/sample.json\n", "")


def break_serial(fx):
    """Spines chained one after another, testers solo: no width."""
    plan = fx / "tasks" / "plan.md"
    for tid, dep in [("M1-T03", "M1-T02"), ("M1-T04", "M1-T03"), ("M1-T05", "M1-T04"), ("M1-T06", "M1-T05"), ("M1-T07", "M1-T06")]:
        task_line(plan, tid, "**Depends on:** M1-T01", f"**Depends on:** {dep}")
    for tid in ("M1-T10", "M1-T11", "M1-T12", "M1-T13"):
        task_line(plan, tid, "**Mode:** split", "**Mode:** solo")


def code_in_planning(proj):
    """A planning turn that writes the interface task's types: never planning's job."""
    p = proj / "src" / "quant" / "stats" / "types.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("from dataclasses import dataclass\n\n\n@dataclass\nclass Cov:\n    n_obs: int\n")


def revise_frozen_type(proj):
    """A later stage revises a type the M1 plan froze."""
    sub(proj / "docs" / "packages" / "quant" / "contract.md", "- **Invariants:** N×N; symmetric; positive semi-definite\n- **Sample:**",
        "- **Invariants:** N×N; symmetric; positive semi-definite; carries its estimation window\n- **Sample:**")


USER_RUN = "(user run)"  # a layer that is the user's "ran it", committed between turns as driver.py does


def with_record(fixture, paths, record):
    """A planning layer whose skill also left docs/requests.md holding `record` (its UR lines)."""
    def layer(proj):
        copy_layer(fixture, proj, paths)
        (proj / "docs").mkdir(exist_ok=True)
        (proj / "docs" / "requests.md").write_text(REQ_HEAD + "".join(line + "\n" for line in record))
    return layer


def recorded(fixture, records):
    """PLANNING with turn N's layer also writing records[N]."""
    return [(skill, with_record(fixture, paths, records[n]) if n in records else paths)
            for n, (skill, paths) in enumerate(PLANNING, 1)]


def replay(out, name, fixture, layers, summary_extra=None, stream=None, users=None):
    """Fake one trajectory from (skill, paths or function) layers; return the grading.json results by id. A
    USER_RUN layer's function runs the user's checks and is committed as `user run before turn N`; `stream` is
    written as the run's agent_stream.jsonl (tool calls the probe checks read); `users` gives turn N's user message
    (default "Plan my quant lab." then "Approved.")."""
    run = out / name / "with_skill"
    if run.exists():
        shutil.rmtree(run)
    run.mkdir(parents=True)
    root = plugin.stage(run / "plugin")
    dt = root / "scripts" / "dt.py"
    proj = run / "project"
    proj.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=proj)
    driver.commit(proj, "turn 0")
    scn = json.loads((HERE / "scenarios.json").read_text())
    (run / "scenario.json").write_text(json.dumps(driver.scenario_snapshot(scn, "quant", "incremental"), indent=1))
    turns, stage, n, user_run = [], "data", 0, None
    for skill, what in layers:
        if skill == USER_RUN:
            user_run = what(proj)
            driver.commit(proj, f"user run before turn {n + 1}")
            continue
        n += 1
        what(proj) if callable(what) else copy_layer(fixture, proj, what)
        driver.commit(proj, f"turn {n}")
        _, status = driver.snapshot(proj, dt, keep=run / "plans" / f"T{n:03d}.json")
        stage = "structure_portfolios" if skill == "reference-intake" else stage
        turns.append({"turn": n, "user": (users or {}).get(n) or ("Approved." if n > 1 else "Plan my quant lab."), "assistant": "(replayed)",
                      "skills": [f"dev-team:{skill}"] if skill else [], "tools": [], "seconds": 0,
                      "usage": {}, "docs_changed": "", "status": status, "stage": stage,
                      "agents": intake_agents(proj) if skill == "reference-intake" else []})
        if user_run is not None:
            turns[-1]["user_run"], user_run = user_run, None
    (run / "turns.json").write_text(json.dumps(turns, indent=1))
    if stream is not None:
        (run / "agent_stream.jsonl").write_text(stream)
    (run / "summary.json").write_text(json.dumps({"trajectory": f"{name} (dry run)", "turns": len(turns),
                                                  "stages_reached": 2, "finished": True, "stop_reason": "dry run",
                                                  "references": [p.name for p in sorted((proj / "references").glob("*"))],
                                                  **(summary_extra or {})}))
    r = subprocess.run([sys.executable, str(HERE / "grade.py"), str(run)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"dryrun: grade.py failed on {name}:\n{r.stderr[-2000:]}")
    plan_json = planexport.export(run)
    snaps = json.loads(plan_json.read_text())["snapshots"]
    last = next(s for s in reversed(snaps) if "nodes" in s)
    print(f"  plan.json: {len(snaps)} turns, {sum('nodes' in s for s in snaps)} snapshots, last at turn {last['turn']} "
          f"with {sum(1 for x in last['nodes'] if x['level'] == 'task')} tasks")
    g = json.loads((run / "grading.json").read_text())
    return run, {c["id"]: c for c in g["expectations"]}, g["summary"]


def verdict(name, res, summary, must_fail, either=(), na=()):
    """Compare a replay's checks with the pinned expectations; return the unexpected ones. Checks in `either` may
    go both ways (a dt-dependent check on a deliberately broken project); checks in `na` must be n/a."""
    bad = [f"{cid} graded, expected n/a: {res[cid]['evidence'][:160]}" for cid in na if cid in res and not res[cid].get("na")]
    bad += [f"{cid} missing from grading.json" for cid in na if cid not in res]
    for cid, c in res.items():
        if c.get("na") or cid in either:
            continue
        if cid in must_fail and c["passed"]:
            bad.append(f"{cid} passed, expected to fail")
        if cid not in must_fail and not c["passed"]:
            bad.append(f"{cid} failed: {c['evidence'][:220]}")
    bad += [f"{cid} missing from grading.json" for cid in must_fail if cid not in res]
    print(f"{name}: {summary['passed']}/{summary['total']} pass" + ("; as pinned" if not bad else f"; UNEXPECTED: {len(bad)}"))
    for b in bad:
        print("  " + b)
    return bad


def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="dt-dryrun-")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    root = plugin.stage(out / "plugin-check")
    probs = plugin.check(root)
    print(f"plugin staged at {root}: {'ok' if not probs else probs}")
    for s in plugin.skills_missing(root):
        print(f"  warning: skills/{s} has no SKILL.md yet")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dt-dryrun-fx-"))
    sys.path.insert(0, str(HERE / "selftest"))
    import checks  # noqa: E402  (the structural rules' good and bad cases, no dt)
    import sessions  # noqa: E402  (driver.session_step: when a turn opens a fresh agent session)
    bad = [f"selftest/checks.py: {c[0]} {c[1]}: {c[2]}" for c in checks.run()]
    bad += [f"selftest/sessions.py: {c[0]}" for c in sessions.run()]
    import yahoo  # noqa: E402  (the fake Yahoo behind the HTTPS proxy, over urllib)
    bad += [f"selftest/yahoo.py: {w}" for w in yahoo.run()]
    try:
        _, res, summ = replay(out, "quant-incremental", FIXTURE, LAYERS)
        bad += verdict("quant-incremental", res, summ, CONTENT | {"no_code_during_planning"}, na=REQUESTS_NA)  # the M1 code turn

        good = ifd_fixture(tmp)
        _, res, summ = replay(out, "quant-incremental-ifd", good, PLANNING)
        bad += verdict("quant-incremental-ifd", res, summ, CONTENT, na=REQUESTS_NA)
        churn = res["frozen_interface_churn"].get("metrics", {}).get("churn")
        if churn != 0:
            bad.append(f"ifd: frozen_interface_churn {churn}, expected 0")

        fx = tmp / "fixture-ifdbad"
        shutil.copytree(good, fx, ignore=shutil.ignore_patterns("src"))
        break_shape(fx)
        layers = PLANNING[:-1] + [("architecture-design", code_in_planning), PLANNING[-1],
                                  ("architecture-design", revise_frozen_type)]
        _, res, summ = replay(out, "quant-incremental-ifdbad", fx, layers)
        bad += verdict("quant-incremental-ifdbad", res, summ, CONTENT | BAD_FAIL, na=REQUESTS_NA)
        churn = res["frozen_interface_churn"].get("metrics", {}).get("churn")
        if not churn:
            bad.append(f"ifdbad: frozen_interface_churn {churn}, expected the revised stats.Cov to count")

        fx = tmp / "fixture-ifdserial"
        shutil.copytree(good, fx, ignore=shutil.ignore_patterns("src"))
        break_serial(fx)
        _, res, summ = replay(out, "quant-incremental-ifdserial", fx, PLANNING)
        bad += verdict("quant-incremental-ifdserial", res, summ, CONTENT | SERIAL_FAIL, na=REQUESTS_NA)

        _, res, summ = replay(out, "quant-incremental-requests", good, recorded(good, REQ_GOOD), users=REQ_USERS)
        bad += verdict("quant-incremental-requests", res, summ, CONTENT)
        bad += [f"requests: {cid} n/a, expected graded" for cid in REQUESTS_NA if res.get(cid, {}).get("na")]
        _, res, summ = replay(out, "quant-incremental-requestsbad", good, recorded(good, REQ_BAD), users=REQ_USERS)
        bad += verdict("quant-incremental-requestsbad", res, summ, CONTENT | REQUESTS_BAD_FAIL)

        import dryrun_probe  # noqa: E402  (imports this module's helpers)
        bad += dryrun_probe.run(out, tmp, good)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"run dirs: {out}")
    print("dry run: as pinned" if not bad else f"dry run: {len(bad)} unexpected results")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
