#!/usr/bin/env python3
"""Dry run of the harness with no model calls: stage and check the plugin, then fake trajectories from dt's sample
project (scripts/tests/fixtures/quant, a valid single-package project mid-M1), grade them, and compare every check
with the result pinned here. It is also the grader's self-test for the interface-first checks.

Each replay copies one planning layer per turn (brief → spec → architecture → reference intake → M2 idea →
pipelines → tests → plan → build setup), keeps the plan snapshot per turn as driver.py does, grades the run and
exports its plan.json. The replays:
- `quant-incremental`: the sample as it is, then its M1 code as a final "build" turn.
- `quant-incremental-ifd`: the sample with an interface-first M1 (§5.3 of design/interface-first-design.md):
  selftest/quant-interface-first/ laid over it. No code. Every interface-first check passes.
- `quant-incremental-ifdbad`: the same plan broken once per check (shared Writes, a mitigated edge in Depends on,
  a `none:` without a valid reason, a missing row, an M-size spine, a fake on a data edge, a type missing from the
  contract, a types.py written during planning, a frozen type revised later, ...). Each of those checks fails.
- `quant-incremental-ifdserial`: the spines chained one after another and the testers made solo. The parallelism
  and wave-width checks fail.
Checks the sample can't meet (it isn't a finished four-stage quant run) are pinned as expected failures; checks
that need the interface-first dt (`dt ready`, `Writes:` in task-size) are pinned as pending until it lands.

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
           "spec_bias_guards", "spec_classical", "spec_ml_beats_classical", "spec_oos", "arch_viz_boundary",
           "refs_milestones", "skills_on_data_tasks", "skills_on_structure_tasks"}
# The interface-first checks an old-format plan (no Kind, Writes or dependency graph) fails.
IFD_CHECKS = {"tasks_well_formed", "wave_width", "writes_disjoint", "edges_mitigated", "unmitigated_reasoned",
              "edge_table_consistent", "phase0_split", "step_tasks_small", "tester_starts_early", "interface_coverage",
              "types_in_contract", "sim_ready_1"}
# Pass only once dt-core lands: `dt ready`, contract-change readers, and task-size counting Writes.
DT_CORE = {"dt_lint_clean", "sim_ready_1", "sim_ready_2", "sim_ready_3", "sim_contract_1"}
BAD_FAIL = {"graph_metrics", "writes_disjoint", "edges_mitigated", "unmitigated_reasoned", "no_edge_to_code_when_interface",
            "edge_table_consistent", "phase0_split", "step_tasks_small", "tester_starts_early", "fakes_only_cross_pipeline",
            "tasks_not_editing_plan", "interface_coverage", "types_in_contract", "tasks_well_formed",
            "no_code_during_planning", "doc_budgets"}
SERIAL_FAIL = {"plan_parallelism", "wave_width"}


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


def native_ifd():
    plan = FIXTURE / "tasks" / "plan.md"
    return plan.exists() and "**Kind:**" in plan.read_text()


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
    sub(plan, "| M1-T10 universe | M1-T03 apply_universe spine | code | none: thickens the same module |",
        "| M1-T10 universe | M1-T03 apply_universe spine | code | none: simpler this way |")
    sub(plan, "| M1-T13 PCA check | M1-T06 pca spine | code | none: thickens the same module |\n",
        "| M1-T99 ghost | M1-T01 | data | none: same module |\n")
    sub(plan, "## Open questions", "\n".join(f"- filler risk line {i}" for i in range(300)) + "\n\n## Open questions")
    sub(pls, "| 1 | `load_prices` | data | Universe, dates → Prices |", "| 1 | `load_prices` | data | Universe, dates → PriceFrame |")


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


def replay(out, name, fixture, layers):
    """Fake one trajectory from (skill, paths or function) layers; return the grading.json results by id."""
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
    turns, stage = [], "data"
    for n, (skill, what) in enumerate(layers, 1):
        what(proj) if callable(what) else copy_layer(fixture, proj, what)
        driver.commit(proj, f"turn {n}")
        _, status = driver.snapshot(proj, dt, keep=run / "plans" / f"T{n:03d}.json")
        stage = "structure_portfolios" if skill == "reference-intake" else stage
        turns.append({"turn": n, "user": "Approved." if n > 1 else "Plan my quant lab.", "assistant": "(replayed)",
                      "skills": [f"dev-team:{skill}"] if skill else [], "tools": [], "seconds": 0,
                      "usage": {}, "docs_changed": "", "status": status, "stage": stage,
                      "agents": intake_agents(proj) if skill == "reference-intake" else []})
    (run / "turns.json").write_text(json.dumps(turns, indent=1))
    (run / "summary.json").write_text(json.dumps({"trajectory": f"{name} (dry run)", "turns": len(turns),
                                                  "stages_reached": 2, "finished": True, "stop_reason": "dry run",
                                                  "references": [p.name for p in sorted((proj / "references").glob("*"))]}))
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


def verdict(name, res, summary, must_fail, either=()):
    """Compare a replay's checks with the pinned expectations; return the unexpected ones."""
    bad = []
    for cid, c in res.items():
        if c.get("na"):
            continue
        if cid in either:
            continue
        if cid in must_fail and c["passed"]:
            bad.append(f"{cid} passed, expected to fail")
        if cid not in must_fail and not c["passed"]:
            bad.append(f"{cid} failed: {c['evidence'][:220]}")
    bad += [f"{cid} missing from grading.json" for cid in must_fail if cid not in res]
    pending = sorted(f"{cid}={'pass' if res[cid]['passed'] else 'fail'}" for cid in either if cid in res and cid in DT_CORE)
    print(f"{name}: {summary['passed']}/{summary['total']} pass"
          + (f"; dt-core pending: {', '.join(pending)}" if pending else "")
          + ("; as pinned" if not bad else f"; UNEXPECTED: {len(bad)}"))
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
    bad = []
    try:
        native = native_ifd()
        _, res, summ = replay(out, "quant-incremental", FIXTURE, LAYERS)
        # With dt-core's interface-first fixture the sample's own M1 meets the new checks; its code turn still fails.
        bad += verdict("quant-incremental", res, summ, CONTENT | {"no_code_during_planning"} | (set() if native else IFD_CHECKS),
                       either=(IFD_CHECKS | DT_CORE) if native else DT_CORE)

        good = ifd_fixture(tmp)
        _, res, summ = replay(out, "quant-incremental-ifd", good, PLANNING)
        bad += verdict("quant-incremental-ifd", res, summ, CONTENT, either=DT_CORE)
        churn = res["frozen_interface_churn"].get("metrics", {}).get("churn")
        if churn != 0:
            bad.append(f"ifd: frozen_interface_churn {churn}, expected 0")

        fx = tmp / "fixture-ifdbad"
        shutil.copytree(good, fx, ignore=shutil.ignore_patterns("src"))
        break_shape(fx)
        layers = PLANNING[:-1] + [("architecture-design", code_in_planning), PLANNING[-1],
                                  ("architecture-design", revise_frozen_type)]
        _, res, summ = replay(out, "quant-incremental-ifdbad", fx, layers)
        bad += verdict("quant-incremental-ifdbad", res, summ, CONTENT | BAD_FAIL,
                       either=DT_CORE | {"gate_discipline", "sim_replan_1", "sim_replan_2", "sim_replan_3", "sim_replan_4",
                                         "sim_replan_5", "sim_advance_1", "sim_advance_2", "sim_advance_3",
                                         "context_packets_small", "milestone_size", "plan_parallelism", "wave_width"})
        churn = res["frozen_interface_churn"].get("metrics", {}).get("churn")
        if not churn:
            bad.append(f"ifdbad: frozen_interface_churn {churn}, expected the revised stats.Cov to count")

        fx = tmp / "fixture-ifdserial"
        shutil.copytree(good, fx, ignore=shutil.ignore_patterns("src"))
        break_serial(fx)
        _, res, summ = replay(out, "quant-incremental-ifdserial", fx, PLANNING)
        bad += verdict("quant-incremental-ifdserial", res, summ, CONTENT | SERIAL_FAIL,
                       either=DT_CORE | {"tasks_well_formed", "no_edge_to_code_when_interface", "tester_starts_early",
                                         "edge_table_consistent"})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"run dirs: {out}")
    print("dry run: as pinned" if not bad else f"dry run: {len(bad)} unexpected results")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
