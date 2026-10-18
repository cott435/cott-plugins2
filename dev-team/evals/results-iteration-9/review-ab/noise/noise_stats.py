import json, math, pathlib, statistics as st, sys

R = pathlib.Path("/Users/connorott/plugins/cott-plugins2/.claude/worktrees/eloquent-goldberg-32427c/dev-team/evals/results-iteration-9")
N = R / "review-ab/noise"
SETS = [("rl", "incremental", "rl-incremental"), ("rl", "all_at_once", "rl-all-at-once"),
        ("quant", "incremental", "quant-incremental"), ("quant", "all_at_once", "quant-all-at-once")]


def score(d, p, lab):
    f = d / f"judge-{p}.json"
    return json.loads(f.read_text())["scores"][lab]["overall_score"] if f.exists() else None


def sd(xs):
    return st.stdev(xs) if len(xs) > 1 else float("nan")


runs = {"n1": N / "n1", "n2": N / "n2", "n3": N / "n3", "v5": R / "review-ab/v5"}
base = {"it9": R, "b1": N / "it9-b1", "b2": N / "it9-b2"}
jonly = {"v5": R / "review-ab/v5", "j1": N / "v5-rl-j1", "j2": N / "v5-rl-j2"}
single = {"v1": R / "review-ab/calibration", "v3": R / "review-ab/v3", "v4": R / "review-ab/v4"}

out = {"sets": {}}
var_run, var_judge_b, var_judge_j = [], [], []
for p, lab, name in SETS:
    rr = {k: score(d, p, lab) for k, d in runs.items()}
    bb = {k: score(d, p, lab) for k, d in base.items()}
    jj = {k: score(d, p, lab) for k, d in jonly.items()} if p == "rl" else {}
    xs = [v for v in rr.values() if v is not None]
    bs = [v for v in bb.values() if v is not None]
    js = [v for v in jj.values() if v is not None]
    var_run.append((st.variance(xs), len(xs) - 1))
    var_judge_b.append((st.variance(bs), len(bs) - 1))
    if js:
        var_judge_j.append((st.variance(js), len(js) - 1))
    s1 = {k: score(d, p, lab) for k, d in single.items()}
    out["sets"][name] = {"runs": rr, "run_mean": round(st.mean(xs), 3), "run_min": min(xs), "run_max": max(xs),
                         "run_sd": round(sd(xs), 3), "base": bb, "base_mean": round(st.mean(bs), 3),
                         "base_min": min(bs), "base_max": max(bs), "base_sd": round(sd(bs), 3),
                         "judge_only": jj, "judge_only_sd": round(sd(js), 3) if js else None,
                         "singles": {k: (v, "inside" if min(xs) <= v <= max(xs) else "outside") for k, v in s1.items()}}


def pooled(vs):
    df = sum(d for _, d in vs)
    return sum(v * d for v, d in vs) / df, df


vr, dfr = pooled(var_run)
vj, dfj = pooled(var_judge_b + var_judge_j)
vjb, _ = pooled(var_judge_b)
vjj, _ = pooled(var_judge_j)
vf = max(0.0, vr - vj)
out["pooled"] = {"run_sd": round(math.sqrt(vr), 3), "run_df": dfr, "judge_sd": round(math.sqrt(vj), 3), "judge_df": dfj,
                 "judge_sd_baseline_only": round(math.sqrt(vjb), 3), "judge_sd_v5rl_only": round(math.sqrt(vjj), 3),
                 "fixer_sd": round(math.sqrt(vf), 3), "fixer_share": round(vf / vr, 2) if vr else None,
                 "judge_share": round(min(1, vj / vr), 2) if vr else None}

# the 4-set mean per run and per baseline draw
rk = [k for k in runs if all(score(runs[k], p, lab) is not None for p, lab, _ in SETS)]
run_means = {k: round(st.mean(score(runs[k], p, lab) for p, lab, _ in SETS), 4) for k in rk}
base_means = {k: round(st.mean(score(base[k], p, lab) for p, lab, _ in SETS), 4) for k in base}
single_means = {k: round(st.mean(score(d, p, lab) for p, lab, _ in SETS), 4) for k, d in single.items()}
rm, bm = list(run_means.values()), list(base_means.values())
diff = st.mean(rm) - st.mean(bm)
se = math.sqrt(st.variance(rm) / len(rm) + st.variance(bm) / len(bm))
# Welch df
a, b = st.variance(rm) / len(rm), st.variance(bm) / len(bm)
wdf = (a + b) ** 2 / (a * a / (len(rm) - 1) + b * b / (len(bm) - 1))
out["overall"] = {"run_means": run_means, "v5_mean_of_runs": round(st.mean(rm), 3), "v5_sd_of_run_means": round(sd(rm), 3),
                  "base_means": base_means, "base_mean": round(st.mean(bm), 3), "base_sd": round(sd(bm), 3),
                  "diff": round(diff, 3), "se": round(se, 3), "t": round(diff / se, 2) if se else None,
                  "welch_df": round(wdf, 1),
                  "singles": {k: (v, "inside" if min(rm) <= v <= max(rm) else "outside") for k, v in single_means.items()}}

# runs needed to detect +0.25 (two-sided 5%, 80% power): sigma_v^2/n + sigma_b^2/m <= (0.25/2.80)^2
target = (0.25 / (1.96 + 0.84)) ** 2
sv, sb = st.variance(rm), st.variance(bm)
need_equal = math.ceil((sv + sb) / target)
need_set_equal = math.ceil((vr + vj) / target)
out["power"] = {"delta": 0.25, "sd_run_mean": round(math.sqrt(sv), 3), "sd_base_mean": round(math.sqrt(sb), 3),
                "n_each_for_4set_mean": need_equal,
                "n_each_for_one_set": need_set_equal,
                "n_runs_vs_10_base_pairs": (math.ceil(sv / (target - sb / 10)) if target > sb / 10 else None)}
print(json.dumps(out, indent=1))
