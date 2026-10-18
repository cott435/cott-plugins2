"""Noise measurement for the plan-review fixer (v5 harness as committed in f021648).

phase setup   : fresh copies review-ab-n{1,2,3}/<traj>/with_skill, quant-aao reset to 9ece2e6, prepare, seed v3 review,
                package and check byte-identical to iteration-9/bench.
phase fix     : 12 fixer runs (plan_review.py fix), 6 at a time.
phase judgeextra : judge-only reps of the committed v5 rl pairing (2 pairs) and iteration-9 baseline reps (2 pairs
                per project). Runs alongside fix.
phase judgeruns  : package each run, write prompts, judge both orders.
Each judge order is retried once on a malformed reply; retries are logged.
"""
import json, os, pathlib, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

EV = pathlib.Path("/Users/connorott/plugins/cott-plugins2/.claude/worktrees/eloquent-goldberg-32427c/dev-team/evals")
H = EV / "harness"
sys.path.insert(0, str(H))
import judge_prompt  # noqa: E402

W = pathlib.Path("/Users/connorott/plugins/dev-team-workspace")
S = pathlib.Path(__file__).resolve().parent / "noise"
OUT = EV / "results-iteration-9/review-ab/noise"
TRAJ = ["rl-incremental", "rl-all-at-once", "quant-incremental", "quant-all-at-once"]
RUNS = ["n1", "n2", "n3"]
LOG = S / "log.txt"


def log(*a):
    S.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        print(time.strftime("%H:%M:%S"), *a, file=f, flush=True)


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        log("FAIL", cmd, r.stdout[-500:], r.stderr[-500:])
    return r


def setup(run):
    for t in TRAJ:
        d = W / f"review-ab-{run}" / t / "with_skill"
        assert not d.exists(), d
        (d / "review").mkdir(parents=True)
        for f in ["project", "plugin", "turns.json", "grading.json", "scenario.json", "summary.json"]:
            sh(["cp", "-a", str(W / "iteration-9" / t / "with_skill" / f), str(d) + "/"])
        if t == "quant-all-at-once":
            sh(["git", "-C", str(d / "project"), "reset", "-q", "--hard", "9ece2e6"])
            sh(["git", "-C", str(d / "project"), "clean", "-qfd"])
            # the in-place build of the original left an ignored packages/ tree; turn 50 had none
            sh(["git", "-C", str(d / "project"), "clean", "-qfdx", "--", "packages"])
        sh([sys.executable, str(H / "plan_review.py"), str(d), "prepare"])
        src = EV / "results-iteration-9/review-ab/v3" / t / "review.json"
        shutil.copy(src, d / "review" / "review.json")
        shutil.copy(src, d / "project" / ".review" / "review.json")
    sh([sys.executable, str(H / "package.py"), f"review-ab-{run}"], env={**os.environ, "EVAL_WS": str(W)})
    r = subprocess.run(["diff", "-rq", str(W / "iteration-9/bench"), str(W / f"review-ab-{run}/bench")],
                       capture_output=True, text=True)
    log("setup", run, "IDENTICAL" if r.returncode == 0 else "DIFFERS\n" + r.stdout[:2000])
    return r.returncode == 0


def fix(job):
    """One attempt: a failed fixer may have left partial edits, so it is never rerun on the same copy."""
    run, t = job
    d = W / f"review-ab-{run}" / t / "with_skill"
    r = sh([sys.executable, str(H / "plan_review.py"), str(d), "fix"], cwd=str(EV))
    log("fix", run, t, "rc", r.returncode, r.stdout.strip()[-300:])
    return r.returncode == 0


def judge_pair(prompt_dir, out):
    """Both orders, each retried up to twice on a malformed reply."""
    out = pathlib.Path(out)
    res = {}
    for order in ("AB", "BA"):
        for attempt in (1, 2, 3):
            try:
                res[order] = judge_prompt.judge(pathlib.Path(prompt_dir), order, out)
                log("judge", out.name, order, "ok", f"attempt {attempt}")
                break
            except SystemExit as e:
                log("judge", out.name, order, "malformed", f"attempt {attempt}", str(e)[:200])
    if len(res) == 2:
        judge_prompt.average(str(out))
        return True
    return False


def prompts(project, d1, d2, out, pdir):
    out.parent.mkdir(parents=True, exist_ok=True)
    sh([sys.executable, str(H / "judge_prompt.py"), project, str(d1), str(d2), str(out), "--both", str(pdir),
        "--labels", "incremental", "all_at_once"])


def extra_jobs():
    jobs = []
    # judge-only: committed v5 rl pairing, same prompt dir, new outputs with copies of the key
    v5 = EV / "results-iteration-9/review-ab/v5"
    for rep in ("j1", "j2"):
        out = OUT / f"v5-rl-{rep}" / "judge-rl.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(v5 / "judge-rl.key.json", out.with_name("judge-rl.key.json"))
        jobs.append((S.parent / "v5" / "judge-rl", out))
    # baseline: iteration-9 original pairing
    B = W / "iteration-9/bench"
    for rep in ("b1", "b2"):
        for i, p in enumerate(["rl", "quant"]):
            out = OUT / f"it9-{rep}" / f"judge-{p}.json"
            pdir = S / f"base-{rep}" / f"judge-{p}"
            prompts(p, B / f"eval-{i}-{p}/incremental/run-1/outputs", B / f"eval-{i}-{p}/all_at_once/run-1/outputs",
                    out, pdir)
            jobs.append((pdir, out))
    return jobs


def run_jobs():
    jobs = []
    for run in RUNS:
        sh([sys.executable, str(H / "package.py"), f"review-ab-{run}"], env={**os.environ, "EVAL_WS": str(W)})
        B = W / f"review-ab-{run}/bench"
        for i, p in enumerate(["rl", "quant"]):
            out = OUT / run / f"judge-{p}.json"
            pdir = S / run / f"judge-{p}"
            prompts(p, B / f"eval-{i}-{p}/incremental/run-1/outputs", B / f"eval-{i}-{p}/all_at_once/run-1/outputs",
                    out, pdir)
            jobs.append((pdir, out))
        for t in TRAJ:
            d = W / f"review-ab-{run}" / t / "with_skill"
            rec = OUT / run / t
            rec.mkdir(parents=True, exist_ok=True)
            for f in ("fix.json", "cost.json"):
                if (d / "review" / f).exists():
                    shutil.copy(d / "review" / f, rec / f)
            (rec / "fix.diff").write_text(sh(["git", "-C", str(d / "project"), "diff", "HEAD~1", "HEAD"]).stdout)
    return jobs


if __name__ == "__main__":
    phase = sys.argv[1]
    if phase == "setup":
        ok = [setup(r) for r in RUNS]
        print("setup", ok)
    elif phase == "fix+extra":
        with ThreadPoolExecutor(max_workers=10) as pool:
            fx = [pool.submit(fix, (r, t)) for r in RUNS for t in TRAJ[:2]]  # rl first: short
            fx += [pool.submit(fix, (r, t)) for r in RUNS for t in TRAJ[2:]]
            ex = [pool.submit(judge_pair, *j) for j in extra_jobs()]
            print("fix", [f.result() for f in fx])
            print("extra", [f.result() for f in ex])
    elif phase == "judgeruns":
        jobs = run_jobs()
        with ThreadPoolExecutor(max_workers=6) as pool:
            print("judgeruns", list(pool.map(lambda j: judge_pair(*j), jobs)))
