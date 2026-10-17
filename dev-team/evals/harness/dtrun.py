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
                "plans": [], "roadmap": [], "references": [], "docs": {}, "packages": []}


def skill_name(s):
    """Plugin skills are invoked namespaced (`dev-team:pipeline-design`); compare on the bare name."""
    return (s or "").split(":")[-1]
