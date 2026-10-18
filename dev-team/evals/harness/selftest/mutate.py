#!/usr/bin/env python3
"""Plan mutation tests for the grader: plant one defect at a time in a known-good interface-first plan, replay it
as the dry run does, and check that the check owning that defect is the one that fails. No model calls.

The good plan is selftest/quant-interface-first/ laid over dt's quant sample (dryrun.ifd_fixture), with a
`**Boundary:**` line on the two types that cross step owners (stats.Returns and stats.Cov pass from stats to
portfolio in PL-03; architecture-design/references/contracts.md requires one). The probe mutation starts from the
dry run's good probe replay instead (dryrun_probe: PB-01 against the fake Sharadar). Each baseline must fail only
what the sample can't meet (dryrun.CONTENT, plus the Yahoo cross-check for the probe replay).

Each mutation names the check that owns the defect: the one design/interface-first-design.md §9.1 or the findings
that found it in a real run give it to. Its outcome against its baseline is:
- `exact`: the owner fails, and nothing else does except dt's own mirrors (dt_lint_clean and the sim_* checks,
  which run dt over the plan and see the same defect, plus any check a mutation names in DT_SEES: one that fails
  only through its own dt clause);
- `overlap`: the owner fails, and so do other grader checks;
- `other`: the owner passes, but another grader check fails;
- `dt-only`: only dt's mirrors fail; the grader has no check of its own for it;
- `gap`: nothing fails.
Outcomes are pinned in PINNED, as the dry run pins its checks: a gap stays visible here until a grader fix
moves its pin. No check is added to make a mutation pass.

Usage: mutate.py [out-dir] [--only NAME ...]   exit 1 if any outcome differs from its pin
"""
import argparse, json, pathlib, shutil, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import dryrun as dr  # noqa: E402
import dryrun_probe as dp  # noqa: E402
import fakevendor  # noqa: E402

DT_MIRRORS = {"dt_lint_clean", "sim_replan_1", "sim_replan_2", "sim_replan_3", "sim_replan_4", "sim_replan_5",
              "sim_advance_1", "sim_advance_2", "sim_advance_3", "sim_ready_1", "sim_ready_2", "sim_ready_3",
              "sim_contract_1"}
BOUNDARIES = [
    ("- **Sample:** tests/contracts/stats.Returns/sample.json\n",
     "- **Boundary:** portfolio · **Fixtures:** tests/contracts/stats.Returns/ · **Cases:** 10 days × 3 tickers of "
     "simple returns, one name delisted mid-window\n"),
    ("- **Sample:** tests/contracts/stats.Cov/sample.json\n",
     "- **Boundary:** portfolio · **Fixtures:** tests/contracts/stats.Cov/ · **Cases:** the 3×3 sample covariance of "
     "the stats.Returns case\n"),
]


def contract(fx):
    return fx / "docs" / "packages" / "quant" / "contract.md"


def with_boundaries(fx):
    """The good plan's types that cross step owners get their Boundary line (beside the Sample the dry run keys on)."""
    for sample, line in BOUNDARIES:
        dr.sub(contract(fx), sample, sample + line)


# ---- the mutations: each plants one defect in a copy of the good fixture

def wiring_shared_entry(fx):
    """Two wiring tasks write one entry trigger (`__main__.py`) and chain on it by a `file` edge, which replaces
    their fake-mitigated `call` row: iteration 8's F1, which set the critical path in all four runs while no check
    failed. (Keeping the `call` row too would trip dt's `edges` lint on the row, not on the shared file.)"""
    plan = fx / "tasks" / "plan.md"
    dr.task_line(plan, "M1-T08", "**Writes:** src/quant/data/pipeline.py,", "**Writes:** src/quant/__main__.py, src/quant/data/pipeline.py,")
    dr.task_line(plan, "M1-T09", "**Writes:** src/quant/stats/pipeline.py,", "**Writes:** src/quant/__main__.py, src/quant/stats/pipeline.py,")
    dr.task_line(plan, "M1-T09", "**Depends on:** M1-T04,", "**Depends on:** M1-T08, M1-T04,")
    dr.sub(plan, "| M1-T09 wire PL-02 | M1-T08 wire PL-01 | call | data.load_prices fake (M1-T01) |",
           "| M1-T09 wire PL-02 | M1-T08 wire PL-01 | file | none: both write src/quant/__main__.py |")


def wiring_shared_entry_parallel(fx):
    """The same shared trigger with no edge between the two wiring tasks: an exclusive-Writes conflict."""
    plan = fx / "tasks" / "plan.md"
    dr.task_line(plan, "M1-T08", "**Writes:** src/quant/data/pipeline.py,", "**Writes:** src/quant/__main__.py, src/quant/data/pipeline.py,")
    dr.task_line(plan, "M1-T09", "**Writes:** src/quant/stats/pipeline.py,", "**Writes:** src/quant/__main__.py, src/quant/stats/pipeline.py,")


def boundary_removed(fx):
    """stats.Cov crosses from stats to portfolio (PL-03) and loses its Boundary line, cases included."""
    dr.sub(contract(fx), BOUNDARIES[1][1], "")


def false_spine_edge(fx):
    """The pca spine waits on the clean_eigen spine although the stats.Cov sample freezes the data between them
    (its row stays `data`, mitigated): iteration 7's F1 serialization in one edge."""
    dr.task_line(fx / "tasks" / "plan.md", "M1-T06", "**Depends on:** M1-T01", "**Depends on:** M1-T01, M1-T05")


def type_missing_from_interface(fx):
    """write_report's Out, stats.CovReport, is not in the interface task's Read: iteration 8's F12 (evaluate.CrossPlay,
    an Out type). No split task reads it and no graph row cites its sample, so only the interface rule can see it
    (dropping data.RawPrices instead also breaks the T03→T02 row its sample mitigates)."""
    dr.task_line(fx / "tasks" / "plan.md", "M1-T01", ", stats.CovReport,", ",")


def depends_cycle(fx):
    """M1 depends on M2 and M2 on M1: a real Depends cycle (iteration 8's F13, once its build-order note is read the
    way dt now reads it)."""
    dr.sub(fx / "docs" / "roadmap.md", "| PL-01, PL-02 | — | Planned |", "| PL-01, PL-02 | M2 | Planned |")


def depends_order_note(fx):
    """M1's Depends cell carries a build-order note naming M2 (iteration 8's F13 as written). dt reads no ID inside
    parentheses, so there is no cycle; the skill rule says Depends holds no build-order notes."""
    dr.sub(fx / "docs" / "roadmap.md", "| PL-01, PL-02 | — | Planned |", "| PL-01, PL-02 | — (build order: before M2) | Planned |")


def accepted_while_ready(proj):
    """architecture-design accepts AD-04 while its probe PB-01 is Ready, before the user's run (iteration 8 quant
    incremental t47); the later Revise has nothing left to accept."""
    a = proj / "docs" / "architecture.md"
    dr.sub(a, "### AD-04: Sharadar SEP for daily prices\n**Status:** Proposed", "### AD-04: Sharadar SEP for daily prices\n**Status:** Accepted")


# (name, owner, plant, base); base "ifd" mutates the fixture, "probe" adds a turn to the probe replay.
MUTATIONS = [
    ("wiring-shared-entry", "no_edge_to_code_when_interface", wiring_shared_entry, "ifd"),
    ("wiring-shared-entry-parallel", "writes_disjoint", wiring_shared_entry_parallel, "ifd"),
    ("boundary-removed", "interface_coverage", boundary_removed, "ifd"),
    ("false-spine-edge", "no_edge_to_code_when_interface", false_spine_edge, "ifd"),
    ("accepted-while-probe-ready", "probe_not_guess", accepted_while_ready, "probe"),
    ("type-missing-from-interface", "phase0_split", type_missing_from_interface, "ifd"),
    ("depends-cycle", "milestone_depends", depends_cycle, "ifd"),
    ("depends-order-note", "milestone_depends", depends_order_note, "ifd"),
]
PINNED = {
    "wiring-shared-entry": "exact",
    "wiring-shared-entry-parallel": "exact",
    "boundary-removed": "dt-only",
    "false-spine-edge": "exact",
    "accepted-while-probe-ready": "exact",
    "type-missing-from-interface": "exact",
    "depends-cycle": "exact",
    "depends-order-note": "gap",
}


# Checks that fail on a mutation only through a dt clause of their own: roadmap_rows requires `dt roadmap --check`
# to exit 0, and dt's roadmap check errors on a Depends cycle.
DT_SEES = {"depends-cycle": {"roadmap_rows"}}


def failing(res):
    return {cid for cid, c in res.items() if c.get("passed") is False}


def outcome(owner, new, mirrors=frozenset()):
    others = new - DT_MIRRORS - mirrors - {owner}
    if owner in new:
        return "overlap" if others else "exact"
    return "other" if others else ("dt-only" if new else "gap")


def probe_replay(out, name, fixture, extra=None):
    """dryrun_probe's good probe replay (the grader reads project and mode from a run named quant-incremental-*); `extra` is a turn added after api-probe New, while PB-01 is Ready."""
    cfg = json.loads((dr.HERE / "scenarios.json").read_text())["projects"]["quant"]["fake_vendors"]["sharadar"]
    url, server = fakevendor.start("sharadar", out / f"{name}.vendor.jsonl", expect_key=dp.CANARY)
    vendors = {"sharadar": {"url": url + cfg["path"], "server": server, "key": dp.CANARY, "cfg": cfg}}
    try:
        layers = (dr.PLANNING[:2] + [("architecture-design", dp.arch_layer(fixture)), ("api-probe", dp.new_layer())]
                  + ([("architecture-design", extra)] if extra else [])
                  + [(dr.USER_RUN, dp.user_run_layer(vendors, out / f"{name}.user_runs.jsonl")),
                     ("api-probe", dp.record_layer()), ("architecture-design", dp.revise_layer())] + dr.PLANNING[3:])
        _, res, summ = dr.replay(out, name, fixture, layers, summary_extra={"fake_vendors": ["sharadar"],
                                                                          "probe_canary": dp.CANARY}, stream=dp.stream(False))
    finally:
        server.shutdown()
    return res, summ


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", nargs="?", type=pathlib.Path)
    ap.add_argument("--only", action="append")
    a = ap.parse_args()
    out = (a.out or pathlib.Path(tempfile.mkdtemp(prefix="dt-mutate-"))).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dt-mutate-fx-"))
    muts = [m for m in MUTATIONS if not a.only or m[0] in a.only]
    rows, bad = [], []
    try:
        good = dr.ifd_fixture(tmp)
        with_boundaries(good)
        base = {}
        if any(m[3] == "ifd" for m in muts):
            res, summ = dr.replay(out, "quant-incremental-mutbase", good, dr.PLANNING)[1:]
            bad += dr.verdict("quant-incremental-mutbase", res, summ, dr.CONTENT)
            base["ifd"] = failing(res)
        if any(m[3] == "probe" for m in muts):
            pfx = dp.probe_fixture(tmp, good)
            res, summ = probe_replay(out, "quant-incremental-mutprobebase", pfx)
            bad += dr.verdict("quant-incremental-mutprobebase", res, summ, dr.CONTENT | dp.NO_CROSSCHECK)
            base["probe"] = failing(res)
        if bad:
            raise SystemExit("mutate: a baseline is not clean; fix it before reading the mutations")
        for name, owner, plant, kind in muts:
            if kind == "ifd":
                fx = tmp / f"fixture-{name}"
                shutil.copytree(good, fx)
                plant(fx)
                res = dr.replay(out, f"quant-incremental-mut-{name}", fx, dr.PLANNING)[1]
            else:
                res = probe_replay(out, f"quant-incremental-mut-{name}", pfx, plant)[0]
            new, cured = failing(res) - base[kind], base[kind] - failing(res)
            got = outcome(owner, new, DT_SEES.get(name, frozenset())) if owner in res else "gap (no such check)"
            rows.append((name, owner, got, sorted(new), sorted(cured), res.get(owner, {}).get("evidence", "")))
            if got != PINNED.get(name):
                bad.append(f"{name}: {got}, pinned {PINNED.get(name)}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    for name, owner, got, new, cured, ev in rows:
        print(f"{name:<30} owner {owner:<32} {got.upper()}")
        print(f"  newly failing: {', '.join(new) or 'nothing'}" + (f"; newly passing: {', '.join(cured)}" if cured else ""))
        if owner in new:
            print(f"  {owner}: {ev[:300]}")
    gaps = [r for r in rows if r[2] in ("gap", "dt-only", "other") or r[2].startswith("gap")]
    print(f"\n{len(rows)} mutations; not caught by their owner: {', '.join(r[0] for r in gaps) or 'none'}")
    print(f"run dirs: {out}")
    print("mutations: as pinned" if not bad else "mutations: " + "; ".join(bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
