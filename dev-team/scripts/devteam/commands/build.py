"""Run a milestone build: start, status, resolve, release; verdict, escalated, mark-finished for hooks.

build-phase.md §6.5, §10. The last three are called by the project's hook scripts.

- `start M<n>`: refuses a dirty tree; creates and switches to `build/M<n>` from HEAD; records `**Build:**` in the
  plan header and commits it there.
- `go [--note TEXT]`: the user's new go after a Replan; `dt ready` holds everything while the plan's tasks differ
  from the ones the last go saw (`go_current` in status).
- `status`: the run's state as one JSON object (landed, tests landed, reserved, claims with `finished`, ready,
  held and why, reviews, findings by severity, the next checkpoint).
- `resolve <finding|task> [--note TEXT]`: the user's decision. A finding: a Critical stops holding the build. A
  task: its escalations and reject counts clear, a `**Risk:** external` task may be released, and after a
  TEST-WRONG its tests branch is dropped so a fresh tester rewrites the tests, or, with `--test-stands`, kept
  and the implementer retried; its next `dt claim` prints the user's decision.
- `prune [--dry-run]`: in the main checkout, deletes a done task's tests branch and the branch and worktree of
  every claim no longer live (a rejected half's, for one); Exit runs it after the merge.
- `release <task> <role>`: drops a reservation or claim the driver gave up on (`<checkpoint>.<pkg> reviewer`
  for a review).
- `workflow M<n> [--cap N] [--out FILE]`: a Workflow script that drives the build with dt as the decider
  (devteam/workflow.py; the A3-WF eval arm, build-phase.md §5): printed, or written to FILE.
- `submit-review <checkpoint>.<pkg> FILE`: run by the reviewer in its worktree; copies its findings file into
  `reviews/<checkpoint>.<pkg>.md`. A worktree agent's Write tool can't reach the git common directory, so the
  reviewer writes inside its worktree and dt moves the file.
- `verdict --mode collect|gate --rc N`: run by stop_gate.sh in a worktree; records the gate's verdict with the
  worktree's tree hash (`gates/<claim>.json`), which `dt land` reuses when the tree hasn't changed.
- `escalated`: exit 0 when this worktree's claim has an escalation record, else 1 (stop_gate.sh lets it stop).
- `mark-finished`: a SubagentStop hook; reads the hook JSON on stdin and marks the claim whose worktree is its
  `cwd` finished. Silent, and always exits 0.
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

from .. import buildstate as bs
from .. import dispatch, edit, md, model, workflow as wf
from .roadmap import active_plan


def add_arguments(parser):
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("start", help="create build/M<n> and record the go")
    p.add_argument("milestone", help="M<n>, the active plan's milestone")
    sub.add_parser("status", help="the run's state as JSON")
    p = sub.add_parser("go", help="record the user's new go after a Replan changed the plan's tasks")
    p.add_argument("--note", default="", help="the go, in the user's words")
    p = sub.add_parser("resolve", help="record the user's decision on a finding or a blocked task")
    p.add_argument("id", help="a finding (M1-R03) or a task (M1-T05)")
    p.add_argument("--note", default="", help="the decision, in the user's words")
    p.add_argument("--test-stands", action="store_true",
                   help="after a TEST-WRONG: the user says the test is right; keep it and retry the implementer")
    p = sub.add_parser("prune", help="delete the branches and worktrees a finished build left behind")
    p.add_argument("--dry-run", action="store_true", help="list what would go, delete nothing")
    p = sub.add_parser("release", help="drop a reservation or claim")
    p.add_argument("task", help="task ID, or <checkpoint>.<pkg> for a review")
    p.add_argument("role", choices=bs.ROLES + ("reviewer",))
    p = sub.add_parser("workflow", help="a Workflow script that runs the build loop, dt deciding (eval arm A3-WF)")
    p.add_argument("milestone", help="M<n>, the active plan's milestone")
    p.add_argument("--cap", type=int, default=dispatch.DEFAULT_CAP, help="agents in flight (dt ready --cap)")
    p.add_argument("--out", help="write the script to this file (relative: to the project root) instead of printing it")
    p = sub.add_parser("verdict", help="(stop_gate.sh) record this worktree's gate verdict")
    p.add_argument("--mode", required=True, choices=("collect", "gate", "full"))
    p.add_argument("--rc", required=True, type=int)
    p = sub.add_parser("submit-review", help="(reviewer) copy a findings file into reviews/<checkpoint>.<pkg>.md")
    p.add_argument("review", help="<checkpoint>.<pkg>, as the reviewer's prompt names it")
    p.add_argument("file", help="the findings file, inside the reviewer's worktree")
    sub.add_parser("escalated", help="(stop_gate.sh) exit 0 if this worktree's claim escalated")
    sub.add_parser("mark-finished", help="(SubagentStop hook) mark the claim of the hook's cwd finished")


def emit(obj) -> None:
    print(json.dumps(obj, indent=2))


def fail(msg: str, code: int = 1) -> int:
    emit({"error": msg})
    return code


# ---- start -------------------------------------------------------------------------------------

def start(args, repo) -> int:
    mid = args.milestone.upper()
    if not re.fullmatch(md.MILESTONE_ID, mid):
        return fail(f"dt build start: {args.milestone!r} is not a milestone (M<n>)", 2)
    root = bs.toplevel(repo.root)
    if not bs.is_main_checkout(root):
        return fail("dt build start: run it in the main checkout", 2)
    dirty = bs.status_lines(root)
    if dirty:
        return fail("dt build start: the tree isn't clean:\n" + "\n".join(dirty[:20]))
    plan = active_plan(repo)
    if plan is None or model.milestone_of(plan) != mid or plan.header_line is None:
        return fail(f"dt build start: tasks/plan.md isn't {mid}'s active plan")
    branch = f"build/{mid}"
    if bs.ref_exists(root, f"refs/heads/{branch}"):
        return fail(f"dt build start: {branch} already exists (resume with dt build status)")
    bs.git(root, "switch", "-q", "-c", branch)
    value = f"{branch} started {datetime.date.today().isoformat()}"
    lines = edit.read_lines(plan.path)
    raw = lines[plan.header_line]
    line = raw.rstrip("\r\n")
    if "**Build:**" in line:
        new = re.sub(r"\*\*Build:\*\*\s*[^·]*?(\s*·|\s*$)", lambda m: f"**Build:** {value}{m.group(1)}", line, count=1)
    else:
        new = f"{line} · **Build:** {value}"
    lines[plan.header_line] = new + raw[len(line):]
    edit.write_lines(plan.path, lines)
    bs.git(root, "commit", "-q", "--no-verify", "-F", "-", "--", plan.rel, input=f"{mid}: build started\n")
    commit = bs.head(root)
    state = bs.State(root)
    for kind in bs.KINDS:
        state.path(kind).mkdir(parents=True, exist_ok=True)
    # Agent-tool worktrees live under .claude/worktrees/; they must never make the main checkout look dirty.
    state.exclude(["# dt build: agent worktrees", "/.claude/worktrees/"])
    state.write("go", "go", {"milestone": mid, "tasks": dispatch.tasks_fingerprint(model.tasks(active_plan(repo))),
                             "commit": commit, "time": bs.now()})
    state.log("start", milestone=mid, branch=branch, commit=commit)
    emit({"milestone": mid, "branch": branch, "build": value, "commit": commit})
    return 0


# ---- status ------------------------------------------------------------------------------------

def status(args, repo) -> int:
    plan = active_plan(repo)
    if plan is None:
        return fail("dt build status: no active plan (tasks/plan.md)")
    build = dispatch.Build(repo)
    root = repo.root
    lands = bs.landings(root)
    landed = [{"task": t.id, "role": lands.get(t.id, {}).get("role"), "commit": lands.get(t.id, {}).get("sha")}
              for t in build.tasks if t.id in build.done]
    ready = build.ready(cap=None)
    blocked = [h for h in ready["held"] if not h["why"].startswith(("barrier:", "critical:", "escalation:"))]
    result = {
        "milestone": model.milestone_of(plan),
        "branch": bs.current_branch(root),
        "go": md.strip_md(plan.header.get("Build", "")) or None,
        "go_current": build.go_current(),
        "progress": f"{len(build.done & set(build.by_id))}/{len(build.tasks)}",
        "landed": landed,
        "tests_landed": [t.id for t in build.tasks if t.mode == "split" and t.id not in build.done
                         and build.tester_landed(t.id)],
        "reserved": sorted(build.reserved),
        "claims": [{"id": c["id"], "task": c["task"], "role": c["role"], "worktree": c["worktree"],
                    "finished": bool(c.get("finished")), "since": c.get("time")} for c in build.claims.values()],
        "ready": [{"id": r["id"], "role": r["role"]} for r in ready["rows"]],
        "holds": ready["holds"],
        "blocked": blocked,
        "held": [h for h in ready["held"] if h not in blocked],
        "escalations": list(build.escalations.values()),
        "reviews": [{"review": k, "outcome": r.get("outcome"), "critical": r.get("critical", []),
                     "critical_open": [f for f in r.get("critical", []) if f not in build.resolved],
                     "tasks": r.get("tasks", [])} for k, r in sorted(build.reviews.items())],
        "findings": dispatch.finding_counts(plan),
        "next_checkpoint": build.next_checkpoint(),
        "all_landed": ready["all_landed"],
    }
    emit(result)
    return 0


# ---- resolve, release --------------------------------------------------------------------------

def resolve(args, repo) -> int:
    rid = args.id.upper()
    state = bs.State(repo.root)
    note = " ".join(args.note.split())
    if re.fullmatch(md.FINDING_ID, rid):
        state.write("resolved", rid, {"id": rid, "kind": "finding", "note": note, "time": bs.now()})
        state.log("resolve", id=rid, kind="finding", note=note)
        emit({"resolved": rid, "kind": "finding"})
        return 0
    if not re.fullmatch(md.TASK_ID, rid):
        return fail(f"dt build resolve: {args.id!r} is neither a finding (M1-R03) nor a task (M1-T05)", 2)
    escalations = [e for e in state.all("escalations") if e.get("task") == rid]
    for e in escalations:
        state.remove("escalations", e["claim"])
    for role in bs.ROLES:
        state.remove("rejects", dispatch.half_id(rid, role))
    reopened = False
    test_stands = bool(getattr(args, "test_stands", False))
    if any(e.get("kind") == "TEST-WRONG" for e in escalations) and not test_stands:
        branch = bs.tests_branch(rid)
        if bs.ref_exists(repo.root, f"refs/heads/{branch}"):
            bs.git(repo.root, "branch", "-D", branch, check=False)
            reopened = True
    state.write("resolved", rid, {"id": rid, "kind": "task", "note": note, "escalations": escalations,
                                  "reopened_tester": reopened, "test_stands": test_stands, "time": bs.now()})
    state.log("resolve", id=rid, kind="task", note=note, reopened_tester=reopened, test_stands=test_stands)
    emit({"resolved": rid, "kind": "task", "escalations_cleared": [e["claim"] for e in escalations],
          "reopened_tester": reopened, "test_stands": test_stands})
    return 0


def go(args, repo) -> int:
    plan = active_plan(repo)
    state = bs.State(repo.root)
    if plan is None or state.read("go", "go") is None:
        return fail("dt build go: no build started (dt build start M<n>)")
    note = " ".join(args.note.split())
    fp = dispatch.tasks_fingerprint(model.tasks(plan))
    state.write("go", "go", {"milestone": model.milestone_of(plan), "tasks": fp, "note": note,
                             "commit": bs.head(repo.root), "time": bs.now()})
    state.log("go", tasks=fp, note=note)
    emit({"go": model.milestone_of(plan), "tasks": fp})
    return 0


def prune(args, repo) -> int:
    """Branches the build made and no longer needs: a done task's tests branch, and the branch (and worktree) of
    every claim that isn't live. A branch a live claim or reservation uses is never touched."""
    root = bs.toplevel(repo.root)
    if not bs.is_main_checkout(root):
        return fail("dt build prune: run it in the main checkout", 2)
    state = bs.State(root)
    build = dispatch.Build(repo, state)
    live = {c.get("branch") for c in build.claims.values()} | {c.get("worktree") for c in build.claims.values()}
    worktrees = {}                                            # branch -> worktree path
    path = None
    for line in bs.out(root, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.startswith("branch refs/heads/") and path:
            worktrees[line[len("branch refs/heads/"):]] = path
    claimed = {}
    for e in state.events():
        if e.get("event") == "claim":
            br = e.get("branch") or ("worktree-" + Path(e["worktree"]).name if e.get("worktree") else "")
            if br:
                claimed[br] = e.get("worktree", "")
    branches = [b for b in bs.out(root, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()]
    gone = [b for b in branches if b in claimed and b not in live and claimed[b] not in live]
    gone += [bs.tests_branch(t.id) for t in build.tasks if t.id in build.done and bs.tests_branch(t.id) in branches]
    removed = []
    for br in gone:
        wt = worktrees.get(br)
        if wt and wt != str(root) and not args.dry_run:
            bs.git(root, "worktree", "remove", "--force", wt, check=False)
        if not args.dry_run:
            bs.git(root, "branch", "-D", br, check=False)
        removed.append({"branch": br, "worktree": wt})
    if not args.dry_run:
        bs.git(root, "worktree", "prune", check=False)
        state.log("prune", branches=[r["branch"] for r in removed])
    emit({"pruned" if not args.dry_run else "would_prune": removed})
    return 0


def release(args, repo) -> int:
    rid = f"{args.task}.{args.role}"
    state = bs.State(repo.root)
    claim = state.read("claims", rid)
    dropped = [k for k in ("reserved", "claims", "gates") if state.remove(k, rid)]
    state.log("release", claim=rid, dropped=dropped, by="driver")
    emit({"released": rid, "dropped": dropped, "worktree": claim.get("worktree") if claim else None})
    return 0


def submit_review(args, repo) -> int:
    if not re.fullmatch(r"(M\d+-T\d{2,}|exit)\.[\w-]+", args.review):
        return fail(f"not a review id: {args.review} (want <checkpoint>.<pkg>)", 2)
    src = Path(args.file)
    if not src.is_absolute() and not src.exists():
        src = repo.root / src                                    # relative to the worktree dt runs for
    try:
        text = src.read_text(encoding="utf-8")
    except OSError as e:
        return fail(f"can't read {args.file}: {e}")
    state = bs.State(repo.root)
    dest = state.path("reviews", f"{args.review}.md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    lines = sum(1 for line in text.splitlines() if line.strip())
    state.log("submit-review", review=args.review, lines=lines)
    emit({"submitted": args.review, "file": str(dest), "lines": lines})
    return 0


def workflow(args, repo) -> int:
    mid = args.milestone.upper()
    if not re.fullmatch(md.MILESTONE_ID, mid):
        return fail(f"dt build workflow: {args.milestone!r} is not a milestone (M<n>)", 2)
    if args.cap < 1:
        return fail("dt build workflow: --cap must be at least 1", 2)
    root = bs.toplevel(repo.root)
    if not bs.is_main_checkout(root):
        return fail("dt build workflow: run it in the main checkout", 2)
    plan = active_plan(repo)
    if plan is None or model.milestone_of(plan) != mid:
        return fail(f"dt build workflow: tasks/plan.md isn't {mid}'s active plan")
    text = wf.script(root, mid, args.cap)
    if not args.out:
        sys.stdout.write(text)
        return 0
    out = Path(args.out)
    out = out if out.is_absolute() else root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    emit({"workflow": str(out), "milestone": mid, "cap": args.cap, "dt": str(bs.DT_PY),
          "build_started": bs.State(root).read("go", "go") is not None})
    return 0


# ---- hook-facing -------------------------------------------------------------------------------

def verdict(args, repo) -> int:
    try:
        state = bs.State(repo.root)
        claim = state.claim_for(repo.root)
        if claim is None:
            return 0
        tree = bs.tree_hash(bs.toplevel(repo.root))
        state.write("gates", claim["id"], {"claim": claim["id"], "mode": args.mode, "passed": args.rc == 0,
                                           "rc": args.rc, "tree": tree, "time": bs.now()})
        state.log("verdict", claim=claim["id"], mode=args.mode, passed=args.rc == 0)
    except (bs.GitError, OSError) as e:
        print(f"dt build verdict: {e}", file=sys.stderr)
    return 0


def escalated(args, repo) -> int:
    try:
        state = bs.State(repo.root)
        claim = state.claim_for(repo.root)
        return 0 if claim and state.read("escalations", claim["id"]) else 1
    except (bs.GitError, OSError):
        return 1


def mark_finished(args, repo) -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
        cwd = data.get("cwd") if isinstance(data, dict) else None
        if not cwd:
            return 0
        state = bs.State(cwd)
        claim = state.claim_for(cwd)
        if claim is None or claim.get("finished"):
            return 0
        claim.update(finished=True, finished_time=bs.now(), stop_agent_type=data.get("agent_type"))
        state.write("claims", claim["id"], claim)
        state.log("finished", claim=claim["id"], agent_type=data.get("agent_type"))
    except Exception:  # noqa: BLE001 - a hook never fails
        pass
    return 0


ACTIONS = {"start": start, "status": status, "go": go, "prune": prune, "resolve": resolve, "release": release, "workflow": workflow,
           "verdict": verdict,
           "escalated": escalated, "mark-finished": mark_finished, "submit-review": submit_review}


def run(args, repo) -> int:
    try:
        return ACTIONS[args.action](args, repo)
    except bs.GitError as e:
        if args.action in ("verdict", "escalated", "mark-finished"):
            return 0 if args.action != "escalated" else 1
        return fail(f"dt build {args.action}: {e}")
