#!/usr/bin/env python3
"""Write minilab's plan variants, so they stay in step: `python3 gen_plans.py [--check]`.

- plan-interface/: M1 cut interface-first (§5–§6 of dev-team/design/interface-first-design.md), 21 tasks, a
  barrier checkpoint after the interface task and one at each phase end.
- plan-interface-solo/ (arm A4): the same tasks, every Mode solo with a `**Reason:** mode:` line, each intent
  test moved under tests/unit/ (`tests/unit/<pkg>/test_<step>_golden.py`).
- plan-interface-pertask/ (arm A3-RT): the same tasks, a (non-barrier) checkpoint after every task.
- plan-spine/: plan-spine/legacy/ (the M1 cut the way build-planning did before interface-first) converted for
  the build: `Files likely` becomes `Writes` (the files each task writes, from replay.json; a split task's
  tests/intent/ path added), `Kind` (the contract task and the three pipeline spines `interface`, which they are:
  they create and freeze the step modules) and a barrier checkpoint after the contract task added, `Parallel` removed,
  a `## Dependency graph` row per `Depends on` so `dt lint` reads the order as declared, and the smoke tests'
  shape-only rule (SMOKE_SHAPE, as in the interface plans); the `dt layout` pointer bullet dropped (`dt land` runs
  prebuild-clear for a wiring task, and pipelines.md is in no task's Writes); nothing else moves.

The output is hand-checked and committed; `--check` fails if any file drifts.
"""
import json
import pathlib
import re
import sys

FIX = pathlib.Path(__file__).resolve().parents[1]
M, R = "packages/mdata/src/mdata", "packages/risk/src/risk"

# step: (task, pipeline, step, owner module, unit test, spine title, read, covers)
STEPS = [
    ("T02", "PL-01", "read_csv", f"{M}/io.py", "tests/unit/mdata/test_io.py", "read every row",
     "PL-01, mdata.read_csv, mdata.RawRow, DATA-01", "DATA-01"),
    ("T03", "PL-01", "validate_rows", f"{M}/validate.py", "tests/unit/mdata/test_validate.py",
     "keep rows with a close, sorted", "PL-01, mdata.validate_rows, mdata.RawRow", ""),
    ("T04", "PL-01", "align_calendar", f"{M}/calendar.py", "tests/unit/mdata/test_calendar.py",
     "dates every ticker has, no fill", "PL-01, mdata.align_calendar, mdata.RawRow, mdata.Prices", ""),
    ("T05", "PL-02", "log_returns", f"{R}/returns.py", "tests/unit/risk/test_returns.py", "simple returns",
     "PL-02, risk.log_returns, mdata.Prices, risk.Returns", ""),
    ("T06", "PL-02", "rolling_vol", f"{R}/vol.py", "tests/unit/risk/test_vol.py",
     "expanding stdev of earlier returns", "PL-02, risk.rolling_vol, risk.Returns, risk.VolSeries", ""),
    ("T07", "PL-02", "annualize", f"{R}/annualize.py", "tests/unit/risk/test_annualize.py",
     "daily values pass through", "PL-02, risk.annualize, risk.VolSeries", ""),
    ("T08", "PL-03", "summary_stats", f"{R}/summary.py", "tests/unit/risk/test_summary.py",
     "daily mean, stdev", "PL-03, risk.summary_stats, risk.VolSeries, risk.TickerSummary", ""),
    ("T09", "PL-03", "max_drawdown", f"{R}/drawdown.py", "tests/unit/risk/test_drawdown.py", "depth only",
     "PL-03, risk.max_drawdown, risk.Returns, risk.Drawdown", ""),
    ("T10", "PL-03", "write_report", f"{R}/report.py", "tests/unit/risk/test_report.py", "JSON rows",
     "PL-03, risk.write_report, risk.TickerSummary, risk.Drawdown, risk.Report, REP-01", "REP-01"),
]
SPINE_IN = {"T03": "mdata.RawRow", "T04": "mdata.RawRow", "T05": "mdata.Prices", "T06": "risk.Returns",
            "T07": "risk.VolSeries", "T08": "risk.VolSeries", "T09": "risk.Returns", "T10": "risk.TickerSummary"}
SPINE_FROM = {"T03": ["T02"], "T04": ["T03"], "T05": ["T04"], "T06": ["T05"], "T07": ["T06"], "T08": ["T07"],
              "T09": ["T05"], "T10": ["T08", "T09"]}
SPINE_SAMPLE = {("T10", "T09"): "risk.Drawdown"}

# thicken: (task, spine task, title, TCs, covers, intent test, acceptance)
THICKEN = [
    ("T14", "T03", "Drop unusable rows, resolve duplicates", "TC-01", "DATA-02", "tests/intent/mdata/test_validate.py",
     ["TC-01 passes", "A requested ticker with no usable row is a `KeyError` naming it"]),
    ("T15", "T04", "Forward fill with a gap limit", "TC-02, TC-03", "DATA-03, DATA-04",
     "tests/intent/mdata/test_calendar.py", ["TC-02 and TC-03 pass"]),
    ("T16", "T05", "Log returns", "TC-04", "RISK-01", "tests/intent/risk/test_returns.py",
     ["TC-04 passes within 1e-12"]),
    ("T17", "T06", "Rolling volatility from earlier returns", "TC-05", "RISK-02", "tests/intent/risk/test_vol.py",
     ["TC-05 passes within 1e-12", "A window below 2 is a `ValueError`"]),
    ("T18", "T07", "Annualize over trading days", "TC-06", "RISK-03", "tests/intent/risk/test_annualize.py",
     ["TC-06 passes within 1e-12", "Annualizing an annualized series is a `ValueError`"]),
    ("T19", "T08", "Annualized summary with Sharpe", "TC-07", "RISK-04", "tests/intent/risk/test_summary.py",
     ["TC-07 passes within 1e-9"]),
    ("T20", "T09", "Drawdown with its dates", "TC-08", "RISK-05", "tests/intent/risk/test_drawdown.py",
     ["TC-08 passes: depth within 1e-12, both dates exact"]),
]
STEP_OF = {s[0]: s for s in STEPS}

# wiring: (task, pipeline, package, entry module, smoke test, spines, call)
WIRING = [
    ("T11", "PL-01", "mdata", f"{M}/pipeline.py", "tests/unit/mdata/test_pl01_smoke.py", ["T02", "T03", "T04"], None),
    ("T12", "PL-02", "risk", f"{R}/vol_pipeline.py", "tests/unit/risk/test_pl02_smoke.py", ["T05", "T06", "T07"],
     ("T11", "mdata.load_prices")),
    ("T13", "PL-03", "risk", f"{R}/report_pipeline.py", "tests/unit/risk/test_pl03_smoke.py", ["T08", "T09", "T10"],
     ("T12", "risk.vol_series")),
]

INTERFACE_WRITES = [f"{M}/{f}" for f in ("__init__.py", "types.py", "io.py", "validate.py", "calendar.py", "pipeline.py")] + \
    [f"{R}/{f}" for f in ("__init__.py", "types.py", "returns.py", "vol.py", "annualize.py", "summary.py",
                          "drawdown.py", "report.py", "vol_pipeline.py", "report_pipeline.py")] + ["tests/contracts/**"]
INTERFACE_READ = ("PL-01, PL-02, PL-03, mdata.RawRow, mdata.Prices, mdata.GapError, risk.Returns, risk.VolSeries, "
                  "risk.TickerSummary, risk.Drawdown, risk.Report, mdata.load_prices, risk.vol_series")

BARRIER = """- [ ] The interface code is the contract: types, signatures, stubs, samples, fakes and exports match contract.md, no more and no less
- [ ] Every split task's tester can write its tests from what is frozen
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition"""
PER_TASK = """- [ ] The task's acceptance holds; its tests prove it (mutation-checked)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition"""
# A smoke test outlives the spine it first ran on: the thickens change the values, and they can't edit it.
SMOKE_SHAPE = ("The smoke test checks that the pipeline runs and its output's shape (type, tickers, lengths), never a "
               "value a thicken changes: the golden cases check values")
SOLO_REASON = "mode: arm A4, one builder writes the golden-case tests and the code"
CHECKPOINT = """- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] Every stub names an open task (`scripts/check.sh gate`)
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition"""


def solo_golden(intent):
    """Where a solo thicken writes its golden-case tests: tests/intent/risk/test_vol.py → tests/unit/risk/test_vol_golden.py."""
    return intent.replace("tests/intent/", "tests/unit/", 1).removesuffix(".py") + "_golden.py"


def pkg_of(path):
    return "mdata" if "/mdata/" in path else "risk"


def task(tid, title, pkg, step, kind, size, mode, read, acceptance, verify, depends, writes, covers="", reason=""):
    head = f"**Package:** {pkg} · **Step:** {step} · **Kind:** {kind}" + (f" · **Covers:** {covers}" if covers else "")
    lines = [f"### M1-{tid}: {title}", f"{head} · **Size:** {size} · **Mode:** {mode}",
             *([f"**Reason:** {reason}"] if reason else []), f"**Read:** {read}",
             "**Acceptance:**", *[f"- [ ] {a}" for a in acceptance], f"**Verify:** {verify}",
             f"**Depends on:** {', '.join('M1-' + d for d in depends) or '—'} · **Writes:** {', '.join(writes)}", ""]
    return lines, (tid, title, pkg, size, mode)


def checkpoint(after, items, barrier=False):
    return [f"### Checkpoint after M1-{after}" + (" (barrier)" if barrier else ""), items, ""]


def build(variant="interface"):
    """plan.md and todo.md of one interface-first variant: interface, solo or pertask."""
    body, todo, graph = [], [], []

    def add(lines_meta):
        body.extend(lines_meta[0])
        todo.append(lines_meta[1])
        tid = lines_meta[1][0]
        if variant == "pertask" and tid != "T01":
            body.extend(checkpoint(tid, PER_TASK))
    body += ["## Phase 0: Interface", ""]
    add(task("T01", "Freeze the M1 interfaces", "mdata", "contract", "interface", "M", "solo", INTERFACE_READ,
             ["Boundary types in `mdata/types.py` and `risk/types.py`, one sample each under `tests/contracts/<pkg>.<Type>/`",
              "Every M1 step and entry signature in its owner module, body `raise NotImplementedError(\"<task>\")` naming the task that replaces it",
              "`mdata.load_prices` and `risk.vol_series` fakes backed by the samples; `__init__` exports"],
             "`pytest tests/contracts` · `scripts/check.sh gate`", [], INTERFACE_WRITES))
    body += checkpoint("T01", BARRIER, barrier=True)
    body += ["## Phase 1: Step spines", ""]
    for tid, pl, step, mod, unit, spine, read, covers in STEPS:
        sample = SPINE_IN.get(tid)
        acc = (f"`{step}` turns the {sample} sample into a valid output (its spine version: {spine}); signature unchanged"
               if sample else f"`{step}` returns valid output on a synthetic input (its spine version: {spine}); signature unchanged")
        add(task(tid, f"{step} spine ({spine})", pkg_of(mod), f"{pl}.{step}", "spine", "XS", "solo", read, [acc],
                 f"`pytest {unit}` · `scripts/check.sh gate`", ["T01"], [mod, unit], covers))
        for src in SPINE_FROM.get(tid, []):
            sym = SPINE_SAMPLE.get((tid, src), sample)
            graph.append((tid, f"{step} spine", src, f"{STEP_OF[src][2]} spine", "data", f"{sym} sample (M1-T01)"))
    if variant != "pertask":
        body += checkpoint("T10", CHECKPOINT)
    body += ["## Phase 2: Wiring", ""]
    for tid, pl, pkg, entry, smoke, spines, call in WIRING:
        fake = f" on the {call[1]} fake" if call else ""
        acc = [f"`pytest {smoke}` runs {pl} end to end{fake}", SMOKE_SHAPE]
        add(task(tid, f"Wire {pl}{fake}", pkg, pl, "wiring", "S", "solo",
                 f"{pl}, " + ", ".join(f"{pkg_of(STEP_OF[s][3])}.{STEP_OF[s][2]}" for s in spines) + (f", {call[1]}" if call else ""),
                 acc, f"`pytest {smoke}` · `scripts/check.sh gate`", spines, [entry, smoke]))
        if call:
            graph.append((tid, f"wire {pl}", call[0], f"wire {[w for w in WIRING if w[0] == call[0]][0][1]}", "call",
                          f"{call[1]} fake (M1-T01)"))
        for s in spines:
            graph.append((tid, f"wire {pl}", s, f"{STEP_OF[s][2]} spine", "code", f"none: the smoke test runs the real {STEP_OF[s][2]}"))
    body += ["## Phase 2: Thicken", ""]
    for tid, spine_t, title, tcs, covers, intent, acc in THICKEN:
        _, pl, step, mod, unit, _, read, _ = STEP_OF[spine_t]
        reads = ", ".join(x for x in read.split(", ") if x not in ("DATA-01", "REP-01"))
        rf = ", RF-01" if tid in ("T17", "T18", "T19", "T20") else ""
        if variant == "solo":
            golden = solo_golden(intent)
            add(task(tid, title, pkg_of(mod), f"{pl}.{step}", "thicken", "S", "solo", f"{reads}, {tcs}, {covers}{rf}",
                     acc, f"`pytest {golden} {unit}` · `scripts/check.sh gate`", [spine_t], [mod, golden, unit],
                     covers, SOLO_REASON))
        else:
            add(task(tid, title, pkg_of(mod), f"{pl}.{step}", "thicken", "S", "split", f"{reads}, {tcs}, {covers}{rf}",
                     acc, f"`pytest {intent} {unit}` · `scripts/check.sh gate`", [spine_t], [mod, intent, unit], covers))
        graph.append((tid, title.lower(), spine_t, f"{step} spine", "code", "none: thickens the same module"))
    if variant != "pertask":
        body += checkpoint("T20", CHECKPOINT)
    body += ["## Phase 3: System", ""]
    deps = ["T11", "T12", "T13"] + [t[0] for t in THICKEN]
    add(task("T21", "Risk report on the real pipelines", "mdata", "PL-03", "system", "S", "solo",
             "PL-01, PL-02, PL-03, TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, mdata.load_prices, risk.vol_series, risk.risk_report",
             ["`risk.risk_report` runs PL-03 → PL-02 → PL-01 on a CSV with no fakes; the fakes are used only by smoke and contract tests",
              "All smoke tests and TC-01–TC-08 pass"],
             "`pytest tests/unit/mdata/test_pl01_smoke.py` · `pytest tests/unit/risk/test_pl02_smoke.py` · "
             "`pytest tests/unit/risk/test_pl03_smoke.py` · "
             "`pytest tests` · `scripts/check.sh full --exit`", deps,
             [f"{R}/report_pipeline.py", "tests/system/test_e2e.py", "tests/unit/risk/test_risk_report.py"]))
    for d in deps[:3]:
        graph.append(("T21", "system", d, f"wire {[w for w in WIRING if w[0] == d][0][1]}", "code",
                      "none: runs the real pipeline end to end, no fakes"))
    for d in deps[3:]:
        graph.append(("T21", "system", d, [t for t in THICKEN if t[0] == d][0][2].lower(), "order",
                      "none: the golden cases run on the finished steps"))
    if variant == "pertask":
        body = body[:-3]                     # the last task's checkpoint is the milestone exit
    body += ["### Checkpoint: milestone exit",
             "- [ ] Every pipeline in the milestone runs end to end (smoke commands)",
             "- [ ] All golden cases pass; no `NotImplementedError` stub is left (`scripts/check.sh full --exit`)",
             "- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition", ""]
    body += ["## Dependency graph", "| From | To | Kind | Mitigated by |", "|---|---|---|---|"]
    body += [f"| M1-{a} {at} | M1-{b} {bt} | {k} | {m} |" for a, at, b, bt, k, m in graph]
    head = ["# M1: Risk report — Plan", "",
            "**Milestone:** M1 · **Status:** Approved · **Base:** — · **Last updated:** 2026-10-17 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)",
            "", "## Scope", "**Exit:** `risk.risk_report` writes the report for a prices CSV; TC-01–TC-08 pass.",
            "**Covers:** DATA-01–DATA-04, RISK-01–RISK-05, REP-01, QR-01 · **Deferred:** none", ""]
    tail = ["", "## Risks", "| Risk | Impact | Mitigation |", "|---|---|---|",
            "| A frozen type misses a field a later step needs | a contract change mid-milestone | testers start on the interface and escalate as `contract-change` |",
            "", "## Open questions", "", "## Replan notes", ""]
    plan = "\n".join(head + body + tail)
    todo_md = "\n".join(["# M1: Risk report — Todo", ""] +
                        [f"- [ ] M1-{t} {title} ({pkg}, {size}, {mode})" for t, title, pkg, size, mode in todo]) + "\n"
    return {"plan.md": plan, "todo.md": todo_md}


# ---- plan-spine, converted ----------------------------------------------------------------------------

# The legacy pipeline spines create and freeze their step modules (and write types.py, __init__.py and the entry
# modules), as an interface task does; marked spine, dt would release the thickens' testers before the modules
# they import exist.
SPINE_KIND = {"M1-T01": "interface", "M1-T02": "interface", "M1-T03": "interface", "M1-T04": "interface",
              "M1-T05": "system"}
SPINE_EDGE = {("M1-T04", "M1-T03"): ("call", "none: integration: PL-03's spine runs on PL-02 as built"),
              ("M1-T05", "M1-T02"): ("code", "none: swaps the load_prices fake for the real PL-01"),
              ("M1-T05", "M1-T04"): ("code", "none: runs PL-03 → PL-02 → PL-01 end to end")}


SPINE_UNIT = {"M1-T05": ["tests/unit/risk/test_risk_report.py"]}     # a system task writes unit tests too


def spine_writes(tid, likely):
    """`Files likely`, plus every file the task writes (replay.json), plus a split task's intent test."""
    m = json.loads((FIX / "replay.json").read_text())["plan-spine"][tid]
    files = likely + [f.split("@")[0] for f in m["files"] + m.get("tester", [])] + SPINE_UNIT.get(tid, [])
    return list(dict.fromkeys(files))


def convert_spine():
    """plan-spine/legacy/ → plan-spine/tasks/: see the module docstring."""
    src = (FIX / "plan-spine" / "legacy" / "plan.md").read_text()
    blocks = re.split(r"(?m)^(?=### M1-T\d+:)", src)
    out, edges = [blocks[0]], []
    for b in blocks[1:]:
        tid = re.match(r"### (M1-T\d+):", b).group(1)
        title = b.splitlines()[0].split(": ", 1)[1]
        kind = SPINE_KIND.get(tid, "thicken")
        b = re.sub(r"(\*\*Step:\*\* [^·\n]+?) ·", rf"\1 · **Kind:** {kind} ·", b, count=1)
        b = re.sub(r" · \*\*Parallel:\*\* G\d+", "", b)
        b = re.sub(r"(- \[ \] `pytest tests/unit/\w+/test_pl0\d_smoke\.py` runs [^\n]*)", r"\1\n- [ ] " + SMOKE_SHAPE, b)
        b = re.sub(r"- \[ \] [^\n]*replaced by a `dt layout` pointer\n", "", b)
        likely = [f.strip() for f in re.search(r"\*\*Files likely:\*\* ([^\n]*)", b).group(1).split(",")]
        b = re.sub(r"\*\*Files likely:\*\* [^\n]*", "**Writes:** " + ", ".join(spine_writes(tid, likely)), b)
        deps = re.findall(r"M1-T\d+", re.search(r"\*\*Depends on:\*\* ([^·\n]*)", b).group(1))
        for d in deps:
            if SPINE_KIND.get(d) == "interface":
                continue
            k, why = SPINE_EDGE.get((tid, d), ("code", "none: thickens the step the spine built"))
            edges.append(f"| {tid} {title.lower()} | {d} | {k} | {why} |")
        if tid == "M1-T01":
            b = b.rstrip("\n") + "\n\n" + "\n".join(checkpoint("T01", BARRIER, barrier=True)) + "\n"
        out.append(b)
    plan = "".join(out)
    graph = ["## Dependency graph", "| From | To | Kind | Mitigated by |", "|---|---|---|---|", *edges, ""]
    plan = plan.replace("## Risks\n", "\n".join(graph) + "\n## Risks\n", 1)
    return {"plan.md": plan, "todo.md": (FIX / "plan-spine" / "legacy" / "todo.md").read_text()}


def outputs():
    return {"plan-interface": build("interface"), "plan-interface-solo": build("solo"),
            "plan-interface-pertask": build("pertask"), "plan-spine": convert_spine()}


if __name__ == "__main__":
    files = outputs()
    if "--check" in sys.argv:
        bad = [f"{v}/{n}" for v, fs in files.items() for n, t in fs.items()
               if not (FIX / v / "tasks" / n).exists() or (FIX / v / "tasks" / n).read_text() != t]
        print("\n".join(f"differs: {b}" for b in bad) or "ok")
        sys.exit(1 if bad else 0)
    for v, fs in files.items():
        out = FIX / v / "tasks"
        out.mkdir(parents=True, exist_ok=True)
        for n, t in fs.items():
            (out / n).write_text(t)
    print(f"wrote {', '.join(files)}")
