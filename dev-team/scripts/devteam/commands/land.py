"""Land a claimed task half from its worktree onto the build branch; prints one JSON object.

build-phase.md §6.3. Run by the driver, in the main checkout, on the build branch.

Under `dt-build/land.lock`, with a clean main checkout, from the claim record:
0. No claim, `--harness`, or an unfinished claim with no changes → reject `harness`. An escalation record for the
   claim → reject `escalated`, with its kind.
1. Writes: every path changed since the claim's base (committed, uncommitted, untracked) must be in the role's
   share of `Writes:` (re-derived from the plan) and off the protected list (`scripts/check.sh protected`, run in
   the worktree), the tester's own intent paths excepted → else reject `writes`.
2. Gate: the Stop gate's verdict (`gates/<claim>.json`) when its tree hash and mode match the worktree's, else
   `scripts/check.sh collect` (tester) or `gate --pkg <pkg>` (implementer, solo) run in the worktree → reject `gate`.
3. Tester: the worktree's changes squashed into one commit on `dt/<task>-tests`, on the build branch head, trailer
   `Dt-Landed: <task> tester`. The build branch isn't touched.
4. Implementer, solo: `git merge --squash` into the current branch (conflict → reset, reject `conflict`); the
   main checkout's `refs/worktree/checks-base` set to the pre-merge HEAD (for an implementer, plus the task's tests,
   which the half doesn't own), `scripts/check.sh gate --pkg <pkg>` on the merged tree, rerun once on failure (a pass
   records an Important flaky finding; a second failure resets → reject `integration`); then one commit with the
   trailer `Dt-Landed: <task> <role>`, the todo.md tick and, for a task that builds a pipeline, `dt prebuild-clear`.
5. Every outcome: a log event, the claim released, the worktree removed; its branch deleted after a landing.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

from .. import buildstate as bs
from .. import dispatch, graph, model
from ..repo import Repo
from . import finding as finding_cmd
from . import prebuild_clear
from .tick import _set_checkbox

LOCK_TIMEOUT = float(os.environ.get("DT_LAND_LOCK_TIMEOUT", "600"))
GATE_TIMEOUT = float(os.environ.get("DT_GATE_TIMEOUT", "3600"))


def add_arguments(parser):
    parser.add_argument("task", help="task ID, e.g. M1-T03")
    parser.add_argument("--role", required=True, choices=bs.ROLES)
    parser.add_argument("--harness", action="store_true",
                        help="the agent ended without a status line or on an API error: reject `harness`")
    parser.add_argument("--lock-timeout", type=float, default=LOCK_TIMEOUT,
                        help=f"seconds to wait for another landing (default {LOCK_TIMEOUT:g})")


def emit(obj: dict) -> None:
    print(json.dumps(obj, indent=2))


def error(msg: str, code: int = 1) -> int:
    emit({"landed": False, "reject": None, "kind": None, "detail_file": None, "error": msg})
    return code


def run_check(cwd: Path, *args: str, stdout_only: bool = False) -> tuple[int, str]:
    """`bash scripts/check.sh <args>` in `cwd`: (exit code, output)."""
    env = {**os.environ, "NO_COLOR": "1"}
    env.pop("VIRTUAL_ENV", None)
    try:
        res = subprocess.run(["bash", "scripts/check.sh", *args], cwd=cwd, capture_output=True, text=True,
                             env=env, timeout=GATE_TIMEOUT)
    except subprocess.TimeoutExpired as e:
        return 124, f"timed out after {GATE_TIMEOUT:g} s\n{e.stdout or ''}{e.stderr or ''}"
    except OSError as e:
        return 127, str(e)
    return res.returncode, res.stdout if stdout_only else res.stdout + res.stderr


class Lander:
    def __init__(self, repo, root: Path, state: bs.State, task: model.Task, role: str):
        self.repo, self.root, self.state, self.task, self.role = repo, root, state, task, role
        self.cid = dispatch.half_id(task.id, role)
        self.claim = state.read("claims", self.cid)
        self.detail: list[str] = [f"dt land {task.id} --role {role}", f"claim: {self.cid}"]

    # ---- outcomes -----------------------------------------------------------------------------

    def note(self, title: str, body: str = "") -> None:
        self.detail.append(f"\n## {title}")
        if body:
            self.detail.append(body.rstrip())

    def write_detail(self) -> str:
        path = self.state.detail_file(self.cid)
        path.write_text("\n".join(self.detail) + "\n", encoding="utf-8")
        return str(path)

    def release(self, landed: bool) -> None:
        for kind in ("claims", "reserved", "gates"):
            self.state.remove(kind, self.cid)
        if landed:
            self.state.remove("rejects", self.cid)
        claim = self.claim or {}
        wt = claim.get("worktree")
        if wt and Path(wt).is_dir() and bs.real(wt) != bs.real(self.root):
            bs.git(self.root, "worktree", "remove", "--force", wt, check=False)
        branch = claim.get("branch", "")
        if landed and branch not in ("", "HEAD") and bs.ref_exists(self.root, f"refs/heads/{branch}") \
                and branch != bs.current_branch(self.root):
            bs.git(self.root, "branch", "-D", branch, check=False)
        self.state.log("release", claim=self.cid, landed=landed)

    def reject(self, kind: str, why: str, esc_kind: str | None = None) -> int:
        self.note(f"reject: {kind}", why)
        detail = self.write_detail()
        rec = self.state.read("rejects", self.cid) or {"id": self.cid, "count": 0, "harness": 0}
        if kind == "harness":
            rec["harness"] = rec.get("harness", 0) + 1
        elif kind != "escalated":
            rec["count"] = rec.get("count", 0) + 1
            rec["harness"] = 0
        rec["last"] = {"reject": kind, "kind": esc_kind, "detail_file": detail, "time": bs.now()}
        self.state.write("rejects", self.cid, rec)
        self.state.log("reject", claim=self.cid, task=self.task.id, role=self.role, reject=kind, kind=esc_kind,
                       detail_file=detail)
        self.release(landed=False)
        emit({"landed": False, "reject": kind, "kind": esc_kind, "detail_file": detail, "task": self.task.id,
              "role": self.role, "rejects": rec["count"], "harness_failures": rec["harness"]})
        return 0

    def landed(self, commit: str, flaky: bool = False) -> int:
        self.note("landed", f"commit {commit}" + (" (flaky: the gate passed on its rerun)" if flaky else ""))
        detail = self.write_detail()
        self.state.log("land", claim=self.cid, task=self.task.id, role=self.role, commit=commit, flaky=flaky,
                       detail_file=detail)
        self.release(landed=True)
        emit({"landed": True, "reject": None, "kind": None, "detail_file": detail, "task": self.task.id,
              "role": self.role, "commit": commit, "flaky": flaky})
        return 0

    # ---- steps --------------------------------------------------------------------------------

    def land(self, harness: bool) -> int:
        if harness:
            return self.reject("harness", "the driver reports the agent ended without a status line")
        if self.claim is None:
            return self.reject("harness", "no claim: the agent never ran dt claim")
        wt = Path(self.claim["worktree"])
        self.detail += [f"worktree: {wt}", f"base: {self.claim['base']}"]
        if not wt.is_dir():
            return self.reject("harness", f"the worktree {wt} is gone")
        esc = self.state.read("escalations", self.cid)
        if esc:
            return self.reject("escalated", f"{esc.get('kind')}: {esc.get('why', '')}", esc.get("kind"))
        base = self.claim["base"]
        changed = bs.changed_paths(wt, base)
        self.note("changed since base", "\n".join(changed) or "(nothing)")
        if not changed and not self.claim.get("finished"):
            return self.reject("harness", "no changes, and the agent never finished (no SubagentStop)")
        problem = self.check_writes(wt, changed)
        if problem:
            return self.reject("writes", problem)
        if not self.gate(wt):
            return self.reject("gate", "the role's gate failed in the worktree (output above)")
        work = self.commit_worktree(wt)
        return self.land_tests(work, base) if self.role == "tester" else self.land_merge(work)

    def check_writes(self, wt: Path, changed: list[str]) -> str:
        allowed = bs.role_writes(self.task, self.role)
        outside = [p for p in changed if not bs.covered(p, allowed)]
        rc, listing = run_check(wt, "protected", stdout_only=True)
        if rc != 0:
            return f"cannot read the protected list (scripts/check.sh protected exited {rc}):\n{listing}"
        globs = [g.strip() for g in listing.splitlines() if g.strip()]
        allowance = bs.role_writes(self.task, "tester") if self.role == "tester" else []
        protected = [p for p in changed if bs.glob_match(p, globs) and not bs.covered(p, allowance)]
        out = []
        if outside:
            out.append(f"outside the {self.role}'s Writes ({', '.join(allowed) or 'none'}):\n"
                       + "\n".join(f"- {p}" for p in outside))
        if protected:
            out.append("on the protected list:\n" + "\n".join(f"- {p}" for p in protected))
        return "\n".join(out)

    def gate_args(self) -> list[str]:
        return ["collect"] if self.role == "tester" else ["gate", "--pkg", self.task.package]

    def gate(self, wt: Path) -> bool:
        mode = self.gate_args()[0]
        tree = bs.tree_hash(wt)
        verdict = self.state.read("gates", self.cid)
        if verdict and verdict.get("tree") == tree and verdict.get("mode") == mode:
            self.note(f"gate ({mode})", f"reused the Stop gate's verdict from {verdict.get('time')}: "
                      f"{'passed' if verdict.get('passed') else 'failed'} (rc {verdict.get('rc')})")
            return bool(verdict.get("passed"))
        rc, output = run_check(wt, *self.gate_args())
        self.note(f"gate: scripts/check.sh {' '.join(self.gate_args())} (rc {rc})", output)
        return rc == 0

    def commit_worktree(self, wt: Path) -> str:
        bs.git(wt, "add", "-A")
        if bs.git(wt, "diff", "--cached", "--quiet", check=False).returncode != 0:
            bs.git(wt, "commit", "-q", "--no-verify", "-m", f"{self.task.id} {self.role}: worktree at land")
        return bs.head(wt)

    def message(self) -> str:
        what = "tests" if self.role == "tester" else self.task.title
        return f"{self.task.id}: {what}\n\n{bs.TRAILER}: {self.task.id} {self.role}\n"

    def land_tests(self, work: str, base: str) -> int:
        tip = bs.head(self.root)
        mt = bs.git(self.root, "merge-tree", "--write-tree", "--merge-base", base, tip, work, check=False)
        if mt.returncode != 0:
            return self.reject("conflict", f"the tests don't apply on {tip[:12]}:\n{mt.stdout}{mt.stderr}")
        tree = mt.stdout.split()[0]
        commit = bs.out(self.root, "commit-tree", tree, "-p", tip, input=self.message())
        bs.git(self.root, "update-ref", f"refs/heads/{bs.tests_branch(self.task.id)}", commit)
        return self.landed(commit)

    def tests_on(self, pre: str) -> str:
        """A commit of `pre` plus the task's tests branch: the implementer's gate base, so the tests it merged
        aren't counted as its own change to the protected list."""
        ref = f"refs/heads/{bs.tests_branch(self.task.id)}"
        if not bs.ref_exists(self.root, ref):
            return pre
        tip = bs.out(self.root, "rev-parse", ref)
        mt = bs.git(self.root, "merge-tree", "--write-tree", "--merge-base", f"{tip}^", pre, tip, check=False)
        if mt.returncode != 0:
            return pre
        return bs.out(self.root, "commit-tree", mt.stdout.split()[0], "-p", pre,
                      input=f"dt: {self.task.id} tests on {pre[:12]} (gate base)\n")

    def reset(self, pre: str) -> None:
        bs.git(self.root, "reset", "-q", "--hard", "HEAD", check=False)
        bs.git(self.root, "update-ref", "refs/worktree/checks-base", pre, check=False)

    def land_merge(self, work: str) -> int:
        pre = bs.head(self.root)
        merged = bs.git(self.root, "merge", "--squash", work, check=False)
        if merged.returncode != 0:
            self.reset(pre)
            return self.reject("conflict", "two tasks wrote one path (a plan-lint gap):\n"
                               + (merged.stdout + merged.stderr).strip())
        base = self.tests_on(pre) if self.role == "implementer" else pre
        bs.git(self.root, "update-ref", "refs/worktree/checks-base", base)
        args = ["gate", "--pkg", self.task.package]
        rc, output = run_check(self.root, *args)
        self.note(f"integration: scripts/check.sh {' '.join(args)} on the merged tree (rc {rc})", output)
        flaky = False
        if rc != 0:
            rc, output = run_check(self.root, *args)
            self.note(f"integration rerun (rc {rc})", output)
            if rc != 0:
                self.reset(pre)
                tasks = self.build_tasks()
                deps = sorted(t.id for t in tasks if self.task.id in graph.ancestors(tasks, t.id))
                return self.reject("integration", "the merged tree fails the gate twice; dependents: "
                                   + (", ".join(deps) or "none"))
            flaky = True
        self.finish_docs(flaky)
        bs.git(self.root, "add", "-A")
        bs.git(self.root, "commit", "-q", "--no-verify", "-F", "-", input=self.message())
        commit = bs.head(self.root)
        bs.git(self.root, "update-ref", "refs/worktree/checks-base", commit)
        return self.landed(commit, flaky)

    def build_tasks(self) -> list[model.Task]:
        return model.tasks(self.repo.plan) if self.repo.plan else []

    def finish_docs(self, flaky: bool) -> None:
        """The todo.md tick, `dt prebuild-clear` for a task that builds a pipeline, the flaky finding."""
        repo = self.repo
        item = next((i for i in model.todo_items(repo.todo) if i.id == self.task.id), None) if repo.todo else None
        if item is not None and not item.checked:
            _set_checkbox(repo.todo.path, item.line, True)
            repo.reload(repo.todo.rel)
        pl = model.spine_pipeline(self.task, model.system_pipeline_ids(repo))
        if pl:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                prebuild_clear.run(Namespace(pipeline=pl), repo)
            self.note(f"dt prebuild-clear {pl}", buf.getvalue())
        if flaky and repo.plan:
            which = dispatch.checkpoint_after(repo.plan, self.task) or "exit"
            code, fid = finding_cmd.record(repo, which, "Important",
                                           f"flaky · {self.task.id} the integration gate failed, then passed on its "
                                           f"rerun → find the flaky test (dt-build/details/{self.cid}-*.txt)")
            self.note("flaky finding", fid)
            self.state.log("flaky", claim=self.cid, task=self.task.id, finding=fid if code == 0 else None)


def run(args, repo) -> int:
    task_id, role = args.task.upper(), args.role
    try:
        root = bs.toplevel(repo.root)
        state = bs.State(root)
        if not bs.is_main_checkout(root):
            return error("run dt land in the main checkout, not a worktree", 2)
    except bs.GitError as e:
        return error(f"needs git: {e}", 2)
    try:
        with state.lock(args.lock_timeout):
            repo = Repo(root)            # re-read the docs under the lock: an earlier landing may have changed them
            task = dispatch.task_of(repo, task_id)
            if task is None:
                return error(f"{task_id} is not a task of the active plan", 2)
            if role not in graph.roles(task):
                return error(f"{task_id} is Mode {task.mode or '—'}: its halves are {', '.join(graph.roles(task))}", 2)
            dirty = bs.status_lines(root)
            if dirty:
                return error("the main checkout isn't clean:\n" + "\n".join(dirty[:20]))
            return Lander(repo, root, state, task, role).land(args.harness)
    except TimeoutError as e:
        return error(str(e), 3)
    except bs.GitError as e:
        print(f"dt land: {e}", file=sys.stderr)
        return error(f"git failed: {e}")
