#!/usr/bin/env python3
"""Write plan-interface/tasks/{plan.md,todo.md}: minilab's M1 cut interface-first (§5–§6 of
dev-team/design/interface-first-design.md). Kept as a generator so the 21 tasks and their graph rows stay
consistent; the output is hand-checked and committed, and `--check` fails if it drifts.
"""
import pathlib
import sys

OUT = pathlib.Path(__file__).resolve().parents[1] / "plan-interface" / "tasks"
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

CHECKPOINT = """- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] Every stub names an open task (`scripts/check.sh gate`)
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition"""


def pkg_of(path):
    return "mdata" if "/mdata/" in path else "risk"


def task(tid, title, pkg, step, kind, size, mode, read, acceptance, verify, depends, writes, covers=""):
    head = f"**Package:** {pkg} · **Step:** {step} · **Kind:** {kind}" + (f" · **Covers:** {covers}" if covers else "")
    lines = [f"### M1-{tid}: {title}", f"{head} · **Size:** {size} · **Mode:** {mode}", f"**Read:** {read}",
             "**Acceptance:**", *[f"- [ ] {a}" for a in acceptance], f"**Verify:** {verify}",
             f"**Depends on:** {', '.join('M1-' + d for d in depends) or '—'} · **Writes:** {', '.join(writes)}", ""]
    return lines, (tid, title, pkg, size, mode)


def build():
    body, todo, graph = [], [], []
    add = lambda lines_meta: (body.extend(lines_meta[0]), todo.append(lines_meta[1]))
    body += ["## Phase 0: Interface", ""]
    add(task("T01", "Freeze the M1 interfaces", "mdata", "contract", "interface", "M", "solo", INTERFACE_READ,
             ["Boundary types in `mdata/types.py` and `risk/types.py`, one sample each under `tests/contracts/<pkg>.<Type>/`",
              "Every M1 step and entry signature in its owner module, body `raise NotImplementedError(\"<task>\")` naming the task that replaces it",
              "`mdata.load_prices` and `risk.vol_series` fakes backed by the samples; `__init__` exports"],
             "`pytest tests/contracts` · `scripts/check.sh gate`", [], INTERFACE_WRITES))
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
    body += ["### Checkpoint after M1-T10", CHECKPOINT, "", "## Phase 2: Wiring", ""]
    for tid, pl, pkg, entry, smoke, spines, call in WIRING:
        fake = f" on the {call[1]} fake" if call else ""
        acc = [f"`pytest {smoke}` runs {pl} end to end{fake}", f"{pl} entry sketch replaced by a `dt layout` pointer"]
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
        add(task(tid, title, pkg_of(mod), f"{pl}.{step}", "thicken", "S", "split", f"{reads}, {tcs}, {covers}{rf}",
                 acc, f"`pytest {intent} {unit}` · `scripts/check.sh gate`", [spine_t], [mod, intent, unit], covers))
        graph.append((tid, title.lower(), spine_t, f"{step} spine", "code", "none: thickens the same module"))
    body += ["### Checkpoint after M1-T20", CHECKPOINT, "", "## Phase 3: System", ""]
    deps = ["T11", "T12", "T13"] + [t[0] for t in THICKEN]
    add(task("T21", "Risk report on the real pipelines", "mdata", "PL-03", "system", "S", "solo",
             "PL-01, PL-02, PL-03, TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, mdata.load_prices, risk.vol_series, risk.risk_report",
             ["`risk.risk_report` runs PL-03 → PL-02 → PL-01 on a CSV with no fakes; the fakes are used only by smoke and contract tests",
              "All smoke tests and TC-01–TC-08 pass"],
             "`pytest tests/unit/mdata/test_pl01_smoke.py` · `pytest tests/unit/risk/test_pl02_smoke.py` · "
             "`pytest tests/unit/risk/test_pl03_smoke.py` · "
             "`pytest tests` · `scripts/check.sh full --exit`", deps, [f"{R}/report_pipeline.py", "tests/system/test_e2e.py"]))
    for d in deps[:3]:
        graph.append(("T21", "system", d, f"wire {[w for w in WIRING if w[0] == d][0][1]}", "code",
                      "none: runs the real pipeline end to end, no fakes"))
    for d in deps[3:]:
        graph.append(("T21", "system", d, [t for t in THICKEN if t[0] == d][0][2].lower(), "order",
                      "none: the golden cases run on the finished steps"))
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


if __name__ == "__main__":
    files = build()
    if "--check" in sys.argv:
        bad = [n for n, t in files.items() if (OUT / n).read_text() != t]
        print("\n".join(f"differs: {b}" for b in bad) or "ok")
        sys.exit(1 if bad else 0)
    OUT.mkdir(parents=True, exist_ok=True)
    for n, t in files.items():
        (OUT / n).write_text(t)
    print(f"wrote {', '.join(files)} to {OUT}")
