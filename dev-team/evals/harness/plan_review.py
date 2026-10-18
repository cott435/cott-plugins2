#!/usr/bin/env python3
"""A final plan-review pass on a copy of a finished run: a read-only reviewer lists defects against the user's own
messages (plan_review_prompt.md), then a fixer applies them to the copy's docs and plan (plan_fix_prompt.md).

Usage: plan_review.py <run-copy> [review|fix|all]   (default all)
  <run-copy> is a with_skill folder laid out like a driver run (project/, plugin/, turns.json), never the original.
  prepare (part of review) writes project/.review/: user_messages.md (each turn's user message from turns.json),
  packets/context__<task>.md (`dt context` for every task) and lint.txt (`dt lint`).
  review runs the reviewer (`claude -p`, REVIEW_MODEL, default claude-opus-5-5, Read/Glob/Grep only) from project/
  and saves its JSON to <run-copy>/review/review.json and project/.review/review.json.
  fix runs the fixer (Read/Edit/Glob/Grep, Bash only for the run's dt) from project/, saves its reply to
  <run-copy>/review/fix.json, removes project/.review/ and commits the edits in the copy as "plan review fixes".
  Each step's cost, turns and seconds go to <run-copy>/review/cost.json.
"""
import json, os, pathlib, re, shutil, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver, dtrun  # noqa: E402  (driver: the isolated environment the eval's own sessions get)

MODEL = os.environ.get("REVIEW_MODEL", "claude-opus-5-5")


def prepare(run):
    proj, dt = run / "project", dtrun.dt_path(run)
    rv = proj / ".review"
    if rv.exists():
        shutil.rmtree(rv)
    (rv / "packets").mkdir(parents=True)
    turns = json.loads((run / "turns.json").read_text())
    (rv / "user_messages.md").write_text("# The developer's messages, in order\n\n" + "\n".join(
        f"## Turn {t['turn']}\n\n{t['user'].strip()}\n" for t in turns))
    n = 0
    for plan in dtrun.probe(proj, dt)["plans"]:
        for t in plan["tasks"]:
            rc, packet, err = dtrun.run(proj, "context", t["id"], dt=dt)
            (rv / "packets" / f"context__{t['id']}.md").write_text(packet if rc == 0 else f"(dt context failed: {err.strip()})\n")
            n += 1
    rc, out, err = dtrun.run(proj, "lint", dt=dt)
    (rv / "lint.txt").write_text(out + err)
    return n


def claude(prompt, cwd, tools, allowed):
    cmd = [driver.CLAUDE_BIN, "-p", prompt, "--model", MODEL, "--tools", tools, "--allowedTools", *allowed,
           "--strict-mcp-config", "--output-format", "json", "--no-session-persistence", *driver.ISOLATE]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd, env=driver.ENV, capture_output=True, text=True, timeout=7200)
    try:
        res = json.loads(r.stdout)
        reply = json.loads(re.search(r"\{.*\}", res["result"], re.S).group(0))
    except (ValueError, KeyError, TypeError, AttributeError):
        raise SystemExit(f"plan_review: no JSON reply (rc {r.returncode}): {(r.stdout or r.stderr)[-800:]}")
    cost = {"cost_usd": res.get("total_cost_usd"), "turns": res.get("num_turns"), "seconds": round(time.time() - t0),
            "usage": res.get("usage")}
    return reply, cost


def record(run, step, cost):
    f = run / "review" / "cost.json"
    data = json.loads(f.read_text()) if f.exists() else {}
    data[step] = cost
    f.write_text(json.dumps(data, indent=1))


def review(run):
    n = prepare(run)
    proj = run / "project"
    reply, cost = claude((HERE / "plan_review_prompt.md").read_text(), proj, "Read,Glob,Grep", ["Read", "Glob", "Grep"])
    (run / "review").mkdir(exist_ok=True)
    for f in (run / "review" / "review.json", proj / ".review" / "review.json"):
        f.write_text(json.dumps(reply, indent=1))
    record(run, "review", {**cost, "packets": n})
    print(run.parent.name, "review:", len(reply.get("defects", [])), "defects", f"${cost['cost_usd']:.2f}")


def fix(run):
    proj, dt = run / "project", dtrun.dt_path(run).resolve()
    dtcmd = f"python3 {dt} --root {proj.resolve()}"
    prompt = (HERE / "plan_fix_prompt.md").read_text().replace("{DT}", dtcmd)
    reply, cost = claude(prompt, proj, "Read,Edit,Glob,Grep,Bash",
                         ["Read", "Edit", "Glob", "Grep", f"Bash(python3 {dt}:*)"])
    (run / "review" / "fix.json").write_text(json.dumps(reply, indent=1))
    record(run, "fix", cost)
    shutil.rmtree(proj / ".review", ignore_errors=True)
    subprocess.run(["git", "add", "-A", "docs", "tasks"], cwd=proj, check=True)
    subprocess.run(["git", "commit", "-qm", "plan review fixes"], cwd=proj)
    print(run.parent.name, "fix:", len(reply.get("applied", [])), "applied,", len(reply.get("skipped", [])), "skipped",
          f"${cost['cost_usd']:.2f}")


if __name__ == "__main__":
    run = pathlib.Path(sys.argv[1]).resolve()
    if re.search(r"/iteration-\d+/", str(run)):
        sys.exit(f"plan_review: {run} is an original run; review a copy")
    step = sys.argv[2] if len(sys.argv) > 2 else "all"
    if step in ("review", "all"):
        review(run)
    if step in ("fix", "all"):
        fix(run)
