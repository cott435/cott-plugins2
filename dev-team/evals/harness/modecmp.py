#!/usr/bin/env python3
"""Incremental vs all-at-once on the interface-first planning metrics (design/interface-first-design.md §9.1).

Reads both trajectories' grading.json (the `metrics` grade.py stores on each check) and, when given, the averaged
blind-judge result for the pair (`judge_prompt.py average`), and writes `<iteration>/mode_delta.json`, keyed by
project, with every metric for both modes, their delta and the band:
- |Δ N/CP| ≤ 20% (of the larger of the two);
- |Δ max wave width| ≤ 1;
- both modes pass interface_coverage, types_in_contract and writes_disjoint;
- judge |Δ| ≤ 1 on interface_quality and dependency_graph_soundness.
frozen_interface_churn is reported with the expectation all-at-once ≤ incremental. Outside the band is a finding,
not a failure (n is small), so the exit code is 0 whenever both runs were graded.

Usage: modecmp.py <iteration> <project> [--judge <averaged judge json>]   (iteration relative to $EVAL_WS)
"""
import argparse, json, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
WS = pathlib.Path(os.environ.get("EVAL_WS", HERE.parents[3] / "dev-team-workspace"))
MODES = ("incremental", "all_at_once")
CHECKS = ["graph_metrics", "plan_parallelism", "wave_width", "writes_disjoint", "edges_mitigated", "unmitigated_reasoned",
          "no_edge_to_code_when_interface", "edge_table_consistent", "phase0_split", "step_tasks_small",
          "tester_starts_early", "fakes_only_cross_pipeline", "tasks_not_editing_plan", "interface_coverage",
          "types_in_contract", "frozen_interface_churn", "milestone_size", "tasks_well_formed", "no_code_during_planning",
          "doc_budgets"]
MUST_PASS = ["interface_coverage", "types_in_contract", "writes_disjoint"]
JUDGE_ITEMS = ["interface_quality", "dependency_graph_soundness", "task_buildability"]


def metrics_of(grading):
    by = {c["id"]: c for c in grading.get("expectations", [])}
    gm = (by.get("graph_metrics") or {}).get("metrics") or {}
    m = {"tasks": gm.get("tasks"), "critical_path": gm.get("critical_path"),
         "critical_path_weighted": gm.get("critical_path_weighted"), "parallelism": gm.get("parallelism"),
         "max_width": gm.get("width"), "widths": gm.get("widths")}
    for cid, key in [("wave_width", "ready_after_interface"), ("wave_width", "steps"), ("edges_mitigated", "edges_mitigated"),
                     ("tester_starts_early", "tester_early"), ("frozen_interface_churn", "churn"),
                     ("writes_disjoint", "conflicts"), ("no_edge_to_code_when_interface", "violations"),
                     ("interface_coverage", "missing"), ("types_in_contract", "unresolved")]:
        m[f"{cid}.{key}"] = ((by.get(cid) or {}).get("metrics") or {}).get(key)
    m["checks"] = {c: (by[c].get("passed") if c in by else None) for c in CHECKS}
    return m


def judge_scores(path):
    """{mode: {item: score}} from an averaged judge file whose labels name the modes."""
    d = json.loads(pathlib.Path(path).read_text())
    out = {}
    for label, sc in (d.get("scores") or {}).items():
        mode = "all_at_once" if "all" in label.replace("-", "_") else "incremental" if "incr" in label else label
        out[mode] = {k: v for part in ("content", "structure") for k, v in (sc.get(part) or {}).items()}
        out[mode]["overall_score"] = sc.get("overall_score")
    return out


def compare(iteration, project, judge=None):
    it = WS / iteration
    runs = {m: it / f"{project}-{m.replace('_', '-')}" / "with_skill" / "grading.json" for m in MODES}
    missing = [str(p) for p in runs.values() if not p.exists()]
    if missing:
        sys.exit(f"modecmp: not graded yet: {missing}")
    met = {m: metrics_of(json.loads(p.read_text())) for m, p in runs.items()}
    inc, aao = met["incremental"], met["all_at_once"]
    delta = {k: round(aao[k] - inc[k], 3) for k in inc if isinstance(inc.get(k), (int, float)) and isinstance(aao.get(k), (int, float))}

    band, findings = {}, []
    a, b = inc.get("parallelism"), aao.get("parallelism")
    rel = round(abs(a - b) / max(a, b), 3) if a and b else None
    band["parallelism_within_20pct"] = {"incremental": a, "all_at_once": b, "relative_delta": rel,
                                        "ok": rel is not None and rel <= 0.2}
    a, b = inc.get("max_width"), aao.get("max_width")
    band["max_width_within_1"] = {"incremental": a, "all_at_once": b,
                                  "ok": a is not None and b is not None and abs(a - b) <= 1}
    band["both_pass_coverage_types_writes"] = {c: {m: met[m]["checks"].get(c) for m in MODES} for c in MUST_PASS}
    band["both_pass_coverage_types_writes"]["ok"] = all(met[m]["checks"].get(c) is True for c in MUST_PASS for m in MODES)
    js = judge_scores(judge) if judge else {}
    if js and all(m in js for m in MODES):
        jd = {i: (js["incremental"].get(i), js["all_at_once"].get(i)) for i in JUDGE_ITEMS}
        band["judge_within_1"] = {i: {"incremental": x, "all_at_once": y,
                                      "delta": round(y - x, 2) if x is not None and y is not None else None}
                                  for i, (x, y) in jd.items()}
        band["judge_within_1"]["ok"] = all(x is not None and y is not None and abs(y - x) <= 1
                                           for i, (x, y) in jd.items() if i != "task_buildability")
    else:
        band["judge_within_1"] = {"ok": None, "note": "not judged (pass --judge with judge_prompt.py average output)"}
    a, b = inc.get("frozen_interface_churn.churn"), aao.get("frozen_interface_churn.churn")
    churn = {"incremental": a, "all_at_once": b, "expect": "all_at_once <= incremental",
             "as_expected": a is not None and b is not None and b <= a}
    for k, v in band.items():
        if v.get("ok") is False:
            findings.append(k)
    if churn["as_expected"] is False:
        findings.append("frozen_interface_churn: all-at-once revised frozen interfaces more than incremental")
    return {"iteration": iteration, "project": project, "metrics": met, "delta_all_at_once_minus_incremental": delta,
            "band": band, "frozen_interface_churn": churn, "judge": js or None, "findings": findings,
            "in_band": not findings}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("iteration")
    ap.add_argument("project", choices=["rl", "quant"])
    ap.add_argument("--judge", help="averaged judge result (judge_prompt.py average); default <iteration>/judge-<project>.json if averaged")
    a = ap.parse_args()
    judge = a.judge
    default = WS / a.iteration / f"judge-{a.project}.json"
    if not judge and default.exists() and "scores" in json.loads(default.read_text()):
        judge = default
    res = compare(a.iteration, a.project, judge)
    path = WS / a.iteration / "mode_delta.json"
    doc = json.loads(path.read_text()) if path.exists() else {}
    doc[a.project] = res
    path.write_text(json.dumps(doc, indent=1))
    m = res["metrics"]
    print(f"{a.project}: N/CP {m['incremental']['parallelism']} vs {m['all_at_once']['parallelism']} · max width "
          f"{m['incremental']['max_width']} vs {m['all_at_once']['max_width']} · churn {res['frozen_interface_churn']} · "
          + ("in band" if res["in_band"] else f"findings: {res['findings']}"))
    print(path)


if __name__ == "__main__":
    main()
