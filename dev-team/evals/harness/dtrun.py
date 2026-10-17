"""Shared helpers for calling the plugin's `dt` CLI from the harness (driver, grade, simulate).

`dt` is resolved per run: the plugin snapshot the trajectory ran with (<run>/plugin/dev-team/scripts/dt.py, or plugin/dev-team2/ for runs staged under the old name),
else $DT, else this repo's scripts/dt.py. Grading with the run's own snapshot keeps the parser identical.
"""
import json, os, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_DT = HERE.parents[1] / "scripts" / "dt.py"


def dt_path(run_dir=None):
    if run_dir is not None:
        for name in ("dev-team", "dev-team2"):
            snap = pathlib.Path(run_dir) / "plugin" / name / "scripts" / "dt.py"
            if snap.exists():
                return snap
    return pathlib.Path(os.environ.get("DT", REPO_DT))


def run(proj, *args, dt=None, stdin=None):
    """(returncode, stdout, stderr) of `dt --root <proj> <args>`."""
    r = subprocess.run([sys.executable, str(dt or REPO_DT), "--root", str(proj), *args],
                       capture_output=True, text=True, input=stdin, timeout=300)
    return r.returncode, r.stdout, r.stderr


def run_json(proj, *args, dt=None):
    """Parsed `--json` output, or {"_error": …} when dt crashed or printed no JSON."""
    rc, out, err = run(proj, *args, "--json", dt=dt)
    try:
        d = json.loads(out)
        d["_rc"] = rc
        return d
    except Exception:
        return {"_error": f"rc={rc} {err.strip()[-400:]}", "_rc": rc}


def probe(proj, dt=None):
    """dtprobe.py facts (live spec IDs, pipelines, plans and tasks, derived roadmap rows, doc statuses)."""
    scripts = pathlib.Path(dt or REPO_DT).parent
    r = subprocess.run([sys.executable, str(HERE / "dtprobe.py"), str(scripts), str(proj)],
                       capture_output=True, text=True, timeout=300)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"_error": r.stderr.strip()[-600:], "live_spec": [], "removed_spec": [], "pipelines": [],
                "plans": [], "roadmap": [], "stages": [], "references": [], "symbols": [], "tests": [], "docs": {},
                "packages": []}


def skill_name(s):
    """Plugin skills are invoked namespaced (`dev-team:pipeline-design`); compare on the bare name."""
    return (s or "").split(":")[-1]


# ---- the task graph, worked out by the harness itself (dt's numbers are only a cross-check) --------------
# Pure functions over probe task dicts ({id, depends_on, size, ...}). Only `Depends on` orders tasks; graph-table
# rows with a mitigation are documentation. Depends on IDs outside the given tasks (an earlier milestone) are ignored.

SIZE_WEIGHT = {"XS": 1, "S": 2, "M": 4, "L": 8, "XL": 16}


def deps_of(tasks):
    ids = {t["id"] for t in tasks}
    return {t["id"]: [d for d in t.get("depends_on", []) if d in ids and d != t["id"]] for t in tasks}


def cycles(tasks):
    """Task IDs that sit on a Depends-on cycle."""
    deps, out = deps_of(tasks), set()
    def walk(i, path):
        if i in path:
            out.update(path[path.index(i):])
            return
        for d in deps[i]:
            walk(d, path + [i])
    for t in tasks:
        walk(t["id"], [])
    return sorted(out)


def levels(tasks):
    """Task ID → wave (longest Depends-on chain below it); tasks on a cycle, or after one, are left out."""
    deps, bad, memo = deps_of(tasks), set(cycles(tasks)), {}
    up = ancestors(tasks)
    clean = {t["id"] for t in tasks if t["id"] not in bad and not (up[t["id"]] & bad)}
    def lvl(i):
        if i not in memo:
            memo[i] = 0 if not deps[i] else 1 + max(lvl(d) for d in deps[i])
        return memo[i]
    return {i: lvl(i) for i in [t["id"] for t in tasks] if i in clean}


def waves(tasks):
    lv = levels(tasks)
    out = [[] for _ in range(max(lv.values()) + 1)] if lv else []
    for t in tasks:
        if t["id"] in lv:
            out[lv[t["id"]]].append(t["id"])
    return out


def critical_path(tasks, weight=None):
    """The longest Depends-on chain, root first; `weight(task)` makes it the heaviest instead (default: 1 each)."""
    deps, bad = deps_of(tasks), set(cycles(tasks))
    by_id = {t["id"]: t for t in tasks}
    w = weight or (lambda t: 1)
    memo = {}
    def best(i):
        if i not in memo:
            subs = [best(d) for d in deps[i] if d not in bad]
            tail = max(subs, key=lambda x: x[0], default=(0, []))
            memo[i] = (tail[0] + w(by_id[i]), tail[1] + [i])
        return memo[i]
    ends = [best(t["id"]) for t in tasks if t["id"] not in bad]
    return max(ends, key=lambda x: x[0], default=(0, []))[1]


def ancestors(tasks):
    """Task ID → every task it transitively depends on (cycles included)."""
    deps, out = deps_of(tasks), {}
    for t in tasks:
        seen, stack = set(), list(deps[t["id"]])
        while stack:
            d = stack.pop()
            if d not in seen:
                seen.add(d)
                stack.extend(deps[d])
        out[t["id"]] = seen
    return out


def ready(tasks, done):
    deps = deps_of(tasks)
    return [t["id"] for t in tasks if t["id"] not in done and all(d in done for d in deps[t["id"]])]


def graph_metrics(tasks):
    """N, critical path (unweighted and size-weighted XS=1 S=2 M=4), waves, width per wave, N/CP."""
    cp = critical_path(tasks)
    cpw = critical_path(tasks, lambda t: SIZE_WEIGHT.get(t.get("size", ""), 4))
    wv = waves(tasks)
    by_id = {t["id"]: t for t in tasks}
    return {"tasks": len(tasks), "critical_path": len(cp), "critical_path_ids": cp,
            "critical_path_weighted": sum(SIZE_WEIGHT.get(by_id[i].get("size", ""), 4) for i in cpw),
            "critical_path_weighted_ids": cpw, "waves": wv, "widths": [len(x) for x in wv],
            "width": max((len(x) for x in wv), default=0),
            "parallelism": round(len(tasks) / len(cp), 2) if cp else 0.0, "cycles": cycles(tasks)}
