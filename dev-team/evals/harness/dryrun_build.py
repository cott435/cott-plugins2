#!/usr/bin/env python3
"""Build-eval dry run, no model calls: check the minilab fixture, replay a good build of it from solution/
for every arm, grade each replay, then replay five bad builds and check the grader catches each one.

A replay does what the arm's orchestrator would: per round, one builder job per task half (tester,
implementer, solo), each on its own `worktree-*` branch for parallel arms (merged in plan order by the
"merge step") or straight on the main checkout for serial arms; every job commits as `M1-Tnn <role>: …` and
runs the fixture's real `scripts/check.sh` (collect or gate), which writes `.dt/gates/<task>.json`; after
each round the orchestrator ticks the finished tasks; checkpoints split the rounds into segments, one
driver turn each. The planted interface flaw is handled the designed way: before the drawdown task's tester
the orchestrator replans (`dt: replan`) and a new interface task re-freezes risk.Drawdown with the field.

fake_claude.py (FAKE_MODE=build) calls `Replayer.run_segment` once per agent turn, so build_driver.py's loop
runs for free.

Usage:
  dryrun_build.py [out-dir]          fixture checks, every arm's good replay, the bad replays
  dryrun_build.py --fixture-only     only the fixture checks
  dryrun_build.py --arm A3 [out]     one good replay (graded)
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grade_build  # noqa: E402

FIX = HERE / "fixtures" / "build" / "minilab"
SOL = FIX / "solution"
REPLAY = json.loads((FIX / "replay.json").read_text())
SCN = json.loads((HERE / "scenarios.json").read_text())
START = 1792227600  # 2026-10-17 09:00 UTC: the replay's clock
JOB_SECONDS = 120
BADS = {
    "merge_conflict": "merge_conflicts",
    "tester_edits_oracle": "protected_edits_landed",
    "implementer_edits_types": "writes_respected",
    "branch_touches_tasks": "builders_never_edit_tasks",
    "importerror_red": "red_import_errors",
}


# ---- file contents --------------------------------------------------------------------------------------

def sol(rel: str) -> str:
    return (SOL / rel).read_text()


def stub_module(src: str, task: str) -> str:
    """The interface task's version of a step or entry module: signatures and docstrings kept, every
    top-level function body replaced by `raise NotImplementedError("<task>")` (CR-02's carve-out)."""
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node)
            raise_ = ast.parse(f"raise NotImplementedError({task!r})").body[0]
            node.body = ([ast.Expr(ast.Constant(doc))] if doc else []) + [raise_]
    return ast.unparse(tree) + "\n"


def interface_version(rel: str, text: str) -> str:
    """Before the contract change: types without the planted field, samples without it."""
    flaw = json.loads((FIX / "planted.json").read_text())["interface_flaw"]["field"]
    if rel.endswith("types.py"):
        return "".join(l for l in text.splitlines(True) if "# contract-change" not in l)
    if rel.endswith("sample.json") and flaw in text:
        data = json.loads(text)
        strip = lambda d: {k: v for k, v in d.items() if k != flaw}
        data = strip(data) if "rows" not in data else dict(data, rows=[strip(r) for r in data["rows"]])
        return json.dumps(data, indent=1) + "\n"
    return text


def variant(spec: str) -> tuple[str, str]:
    """`path@spine` / `path@interface` / `path` → (path, content)."""
    rel, _, how = spec.partition("@")
    if how == "spine":
        return rel, (SOL / "spine" / rel).read_text()
    if how == "interface":
        return rel, interface_version(rel, sol(rel))
    return rel, sol(rel)


def solution_files(prefix: str) -> list[str]:
    base = SOL / prefix
    return sorted(str(p.relative_to(SOL)) for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


# ---- jobs -----------------------------------------------------------------------------------------------

class Job:
    def __init__(self, task: str, role: str, title: str, files: dict[str, str | None], kind: str = ""):
        self.task, self.role, self.title, self.files, self.kind = task, role, title, files, kind

    @property
    def check_mode(self) -> str:
        return "collect" if self.role == "tester" else "gate"

    def __repr__(self):
        return f"{self.task}:{self.role}"


class Replayer:
    def __init__(self, proj: pathlib.Path, arm_id: str, bad: str | None = None, quiet: bool = True):
        self.proj, self.arm_id, self.bad, self.quiet = proj, arm_id, bad, quiet
        self.arm = SCN["arms"][arm_id]
        self.variant = "plan-" + self.arm["plan"]
        self.state_path = proj / ".git" / "replay_state.json"
        # The schedule comes from the plan as it was at turn 0: a replan mid-build must not reshuffle it.
        root = self.git("rev-list", "--max-parents=0", "HEAD").stdout.split()[0]
        self.plan = grade_build.parse_plan(self.git("show", f"{root}:tasks/plan.md").stdout)
        self.by = grade_build.plan_by(self.plan)
        self.cc = REPLAY["contract_change"]
        # The task that needs the missing field: the split (thicken) task of the flawed step, not its spine.
        self.flaw_task = next((t["id"] for t in self.plan["tasks"] if t["step"] == self.cc["before_step"]
                               and t["mode"] == "split"), None)
        self.cc_id = "M1-T%02d" % (max(int(t["id"].split("T")[1]) for t in self.plan["tasks"]) + 1)
        self.log: list[str] = []

    # -- state (fake_claude runs one segment per process) --

    def state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text())
        except (OSError, ValueError):
            return {"segment": 0, "clock": START, "events": []}

    def save(self, st: dict):
        self.state_path.write_text(json.dumps(st))

    # -- what each task half writes --

    def stub_owner(self, rel: str) -> str:
        for t in self.plan["tasks"]:
            if t["kind"] != "interface" and rel in t["writes"]:
                return t["id"]
        return self.plan["tasks"][0]["id"]

    def files_of(self, t: dict, role: str) -> dict[str, str | None]:
        if self.variant == "plan-spine":
            m = REPLAY["plan-spine"][t["id"]]
            specs = m.get("tester", []) if role == "tester" else m["files"] + (m.get("tester", []) if role == "solo" and t["mode"] == "split" else [])
            return dict(variant(s) for s in specs)
        out = {}
        for w in t["writes"]:
            if w.endswith("/**"):
                for rel in solution_files(w[:-3]):
                    out[rel] = interface_version(rel, sol(rel))
                continue
            intent = w.startswith("tests/intent/")
            if role == "tester" and not intent or role == "implementer" and intent:
                continue
            if t["kind"] == "interface":
                text = sol(w)
                out[w] = interface_version(w, text) if w.endswith(("types.py", "__init__.py")) else stub_module(text, self.stub_owner(w))
            elif t["kind"] == "spine" and (SOL / "spine" / w).exists():
                out[w] = (SOL / "spine" / w).read_text()
            else:
                out[w] = sol(w)
        if role == "solo" and t["mode"] == "split":
            # One builder, Mode overridden: tests/intent/ is protected from it (CR-06), so the golden-case tests
            # go into the task's own unit-test file.
            unit = next((w for w in t["writes"] if w.startswith("tests/unit/")), None)
            for w in [w for w in list(out) if w.startswith("tests/intent/")]:
                text = out.pop(w)
                if unit:
                    out[unit] = out.get(unit, sol(unit)) + "\n\n" + text
        return out

    def jobs_of(self, tid: str, roles: list[str]) -> list[Job]:
        t = self.by[tid]
        return [self.mutate(Job(tid, r, t["title"], self.files_of(t, r), t["kind"])) for r in roles]

    def roles(self, t: dict) -> list[str]:
        if t["mode"] == "split" and self.arm.get("tdd") == "split":
            return ["tester", "implementer"]
        return ["solo"]

    # -- the five bad replays: one defect each, on top of the good A3 replay --

    def mutate(self, job: Job) -> Job:
        """A file value may be a function of the checkout it lands in, applied when the job runs."""
        b, f = self.bad, job.files
        step = self.by.get(job.task, {}).get("step", "")
        if b == "merge_conflict" and job.role == "solo" and step in ("PL-02.log_returns", "PL-02.rolling_vol"):
            init, tag = "packages/risk/src/risk/__init__.py", job.task
            f[init] = lambda root: (root / init).read_text() + f"# touched by {tag}\n"
        if b == "tester_edits_oracle" and job.role == "tester" and step == "PL-02.rolling_vol":
            rel = "tests/fixtures/risk/TC-05/expected.json"
            exp = json.loads((FIX / "project" / rel).read_text())
            exp["values"]["X"][-1] = 0.03
            f[rel] = json.dumps(exp, indent=1) + "\n"
        if b == "implementer_edits_types" and job.role == "implementer" and step == "PL-02.rolling_vol":
            rel = "packages/risk/src/risk/types.py"
            vals = "    values: Mapping[str, tuple[float | None, ...]]  # None until `window` earlier returns exist\n"
            f[rel] = lambda root: (root / rel).read_text().replace(vals, vals + "    min_periods: int = 0\n", 1)
        if b == "branch_touches_tasks" and job.role == "solo" and step == "PL-02.log_returns":
            tag = job.task
            f["tasks/todo.md"] = lambda root: (root / "tasks" / "todo.md").read_text().replace(f"- [ ] {tag} ", f"- [x] {tag} ", 1)
        if b == "importerror_red" and job.role == "tester" and step == "PL-02.log_returns":
            rel = next(k for k in f if k.startswith("tests/intent/"))
            f[rel] = f[rel].replace("from risk.returns import log_returns", "from risk.returns import log_return")
        return job

    # -- the schedule: rounds of jobs, by arm --

    def rounds(self) -> list[list]:
        tasks = self.plan["tasks"]
        out: list[list] = []
        cc = lambda: out.append(["contract-change"])
        if self.arm["dispatch"] == "serial":
            for t in tasks:
                if t["id"] == self.flaw_task:
                    cc()
                for r in self.roles(t):
                    out.append(self.jobs_of(t["id"], [r]))
            return out
        groups = grade_build.dispatch_rounds(self.plan, self.arm)
        interface_first = any(t["kind"] == "interface" and t["claims_exclusive"] for t in tasks)
        early_testers = interface_first and self.arm.get("tdd") == "split"
        done_testers: set[str] = set()
        for gi, group in enumerate(groups):
            flaw_here = self.flaw_task in group
            if early_testers and gi == 1:
                # Wave 1: every spine, and every split task's tester against the frozen interface, except the
                # flaw task's: its tester finds the missing field and escalates (the contract change, below).
                testers = [t["id"] for t in tasks if t["mode"] == "split" and t["id"] != self.flaw_task]
                out.append([j for tid in group for j in self.jobs_of(tid, self.roles(self.by[tid]) if self.by[tid]["mode"] != "split" else [])]
                           + [j for tid in testers for j in self.jobs_of(tid, ["tester"])])
                done_testers |= set(testers)
                continue
            if flaw_here or (early_testers and self.flaw_task and gi == 2):
                cc()
            first, second = [], []
            for tid in group:
                t = self.by[tid]
                roles = self.roles(t)
                if roles == ["tester", "implementer"]:
                    if tid in done_testers:
                        (second if tid == self.flaw_task else first).extend(self.jobs_of(tid, ["implementer"]))
                    elif early_testers:
                        first.extend(self.jobs_of(tid, ["tester"]))
                        second.extend(self.jobs_of(tid, ["implementer"]))
                    else:
                        first.extend(self.jobs_of(tid, ["tester"]))
                        second.extend(self.jobs_of(tid, ["implementer"]))
                else:
                    first.extend(self.jobs_of(tid, roles))
            out += [r for r in (first, second) if r]
        return out

    # -- execution --

    def git(self, *a, cwd=None, env=None, check=True):
        r = subprocess.run(["git", *a], cwd=cwd or self.proj, capture_output=True, text=True, env=env)
        if check and r.returncode:
            raise RuntimeError(f"git {' '.join(a)}: {r.stderr.strip()}")
        return r

    def commit(self, msg: str, when: int, cwd=None, paths=None):
        env = dict(os.environ, GIT_AUTHOR_DATE=f"@{when} +0000", GIT_COMMITTER_DATE=f"@{when} +0000")
        self.git("add", "-A", *(paths or []), cwd=cwd)
        self.git("-c", "user.email=e@e", "-c", "user.name=eval", "commit", "-q", "--allow-empty", "--no-verify",
                 "-m", msg, cwd=cwd, env=env)

    def write(self, root: pathlib.Path, files: dict[str, str | None]):
        for rel, text in files.items():
            p = root / rel
            if callable(text):
                text = text(root)
            if text is None:
                p.unlink(missing_ok=True)
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)

    def check(self, job: Job, cwd: pathlib.Path) -> bool:
        r = subprocess.run(["bash", "scripts/check.sh", job.check_mode, "--task", job.task], cwd=cwd,
                           capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        if r.returncode and not self.bad:
            self.log.append(f"{job} {job.check_mode} FAILED:\n{r.stderr[-1500:]}")
        return r.returncode == 0

    def run_job_here(self, job: Job, when: int):
        self.git("update-ref", "refs/checks/base", "HEAD")   # the orchestrator, before each builder
        self.write(self.proj, job.files)
        self.commit(f"{job.task} {job.role}: {job.title}", when)
        self.check(job, self.proj)

    def run_round(self, jobs: list, st: dict) -> list[str]:
        """One round; returns the events (for the fake CLI's stream)."""
        t0 = st["clock"]
        if jobs == ["contract-change"]:
            self.contract_change(t0)
            st["clock"] = t0 + JOB_SECONDS
            return [f"contract-change {self.cc_id}"]
        if self.arm["dispatch"] == "serial":
            for j in jobs:
                self.run_job_here(j, t0 + JOB_SECONDS)
            st["clock"] = t0 + JOB_SECONDS + 10
            return [f"{j} on main" for j in jobs]
        base = self.git("rev-parse", "HEAD").stdout.strip()
        # refs/ are shared by every worktree, so one base serves the whole wave: the commit it dispatches from.
        self.git("update-ref", "refs/checks/base", base)
        branches = []
        for k, j in enumerate(jobs):
            name = f"{j.task.lower()}-{j.role}-{st['segment']}{k}"
            wt = self.proj / ".claude" / "worktrees" / name
            self.git("worktree", "add", "-q", "-b", f"worktree-{name}", str(wt), base)
            self.write(wt, j.files)
            self.commit(f"{j.task} {j.role}: {j.title}", t0 + JOB_SECONDS + k, cwd=wt)
            self.check(j, wt)
            branches.append((j, f"worktree-{name}", wt))
        events = []
        for k, (j, br, wt) in enumerate(branches):   # the merge step, in plan order
            when = t0 + JOB_SECONDS + 30 + k
            env = dict(os.environ, GIT_AUTHOR_DATE=f"@{when} +0000", GIT_COMMITTER_DATE=f"@{when} +0000")
            r = self.git("-c", "user.email=e@e", "-c", "user.name=merge", "merge", "--no-ff", "-q", "-m",
                         f"merge {j.task}: {br}", br, env=env, check=False)
            if r.returncode:
                self.git("merge", "--abort", check=False)
                events.append(f"{br} conflict")
                if not self.bad:
                    self.log.append(f"merge conflict on {br}: {r.stdout[-400:]}")
            else:
                events.append(f"{br} merged")
            self.git("worktree", "remove", "--force", str(wt))
        st["clock"] = t0 + JOB_SECONDS + 60
        return events

    def contract_change(self, when: int):
        """architecture-design Revise of the planted type, then a new interface task re-freezing it."""
        cc, tid = self.cc, self.cc_id
        doc = self.proj / cc["contract_doc"]
        plan, todo = self.proj / "tasks" / "plan.md", self.proj / "tasks" / "todo.md"
        writes = cc["files"] + [cc["contract_doc"]]
        block = (f"### {tid}: {cc['task_title']}\n**Package:** risk · **Step:** contract · **Kind:** interface · "
                 f"**Size:** S · **Mode:** solo\n**Reason:** contract-change: risk.Drawdown misses trough_date (RISK-05, TC-08)\n"
                 f"**Read:** risk.Drawdown, RISK-05, TC-08\n**Acceptance:**\n- [ ] risk.Drawdown carries trough_date; "
                 f"its samples and the contract section say so\n**Verify:** `pytest tests/contracts` · `scripts/check.sh gate`\n"
                 f"**Depends on:** — · **Writes:** {', '.join(writes)}\n\n")
        text = plan.read_text()
        anchor = f"### {self.flaw_task}:"
        plan.write_text(text.replace(anchor, block + anchor, 1))
        todo.write_text(todo.read_text().rstrip("\n") + f"\n- [ ] {tid} {cc['task_title']} (risk, S, solo)\n")
        self.commit(f"dt: replan: add {tid} (contract-change before {self.flaw_task})", when)
        doc.write_text(doc.read_text().replace(cc["doc_find"], cc["doc_replace"], 1))
        files = {rel: sol(rel) for rel in cc["files"]}
        job = Job(tid, "interface", f"contract-change: {cc['task_title']}", files, "interface")
        # A re-freeze writes contracts frozen at the base (CR-09), so it runs in the main session, not as an
        # implementer: commit, then gate with the new freeze as the base.
        self.write(self.proj, job.files)
        self.commit(f"{job.task} {job.role}: {job.title}", when + JOB_SECONDS // 2)
        self.git("update-ref", "refs/checks/base", "HEAD")
        self.check(job, self.proj)
        self.tick([tid], when + JOB_SECONDS - 1)

    def tick(self, ids: list[str], when: int):
        todo = self.proj / "tasks" / "todo.md"
        text = todo.read_text()
        for i in ids:
            text = re.sub(rf"^- \[ \] {i}\b", f"- [x] {i}", text, flags=re.M)
        todo.write_text(text)
        self.commit(f"dt: tick {', '.join(ids)}", when, paths=["tasks/todo.md"])

    def done(self) -> set[str]:
        return set(re.findall(r"^- \[x\] (M\d+-T\d+)", (self.proj / "tasks" / "todo.md").read_text(), re.M))

    def segments(self) -> list[list]:
        """Rounds grouped into checkpoint segments: a segment ends once every task up to the next checkpoint
        is finished (its last job ran)."""
        rounds = self.rounds()
        order = [t["id"] for t in self.plan["tasks"]]
        stops = [order.index(c["after"]) for c in self.plan["checkpoints"] if c["after"] in order]
        finished, segs, cur, si = set(), [], [], 0
        last_job = {}
        for i, r in enumerate(rounds):
            for j in r:
                if isinstance(j, Job):
                    last_job[j.task] = i
        for i, r in enumerate(rounds):
            cur.append(r)
            finished |= {t for t, k in last_job.items() if k == i}
            while si < len(stops) and set(order[:stops[si] + 1]) <= finished:
                si += 1
                if cur:
                    segs.append(cur)
                    cur = []
        return segs + ([cur] if cur else [])

    def run_segment(self, n: int | None = None) -> dict:
        st = self.state()
        segs = self.segments()
        n = st["segment"] if n is None else n
        if n >= len(segs):
            return {"segment": n, "segments": len(segs), "events": [], "done": True}
        events = []
        for r in segs[n]:
            st["segment"] = n
            events += self.run_round(r, st)
            finished = [j.task for j in r if isinstance(j, Job) and j.role in ("implementer", "solo")]
            if finished:
                self.tick(sorted(set(finished)), st["clock"])
                st["clock"] += 10
        st["segment"] = n + 1
        self.save(st)
        return {"segment": n, "segments": len(segs), "events": events, "done": n + 1 >= len(segs)}


# ---- a replay run folder ---------------------------------------------------------------------------------

def setup_project(proj: pathlib.Path, arm_id: str):
    """The fixture at "planning done" plus the arm's plan, as a git repo with one commit, `turn 0`."""
    if proj.exists():
        shutil.rmtree(proj)
    shutil.copytree(FIX / "project", proj)
    shutil.copytree(FIX / ("plan-" + SCN["arms"][arm_id]["plan"]) / "tasks", proj / "tasks")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=proj, check=True)
    env = dict(os.environ, GIT_AUTHOR_DATE=f"@{START - 60} +0000", GIT_COMMITTER_DATE=f"@{START - 60} +0000")
    subprocess.run(["git", "add", "-A"], cwd=proj, check=True)
    subprocess.run(["git", "-c", "user.email=e@e", "-c", "user.name=eval", "commit", "-q", "-m", "turn 0"], cwd=proj, env=env, check=True)


def replay(run: pathlib.Path, arm_id: str, bad: str | None = None) -> Replayer:
    run.mkdir(parents=True, exist_ok=True)
    proj = run / "project"
    setup_project(proj, arm_id)
    rp = Replayer(proj, arm_id, bad)
    turns, n = [], 0
    while True:
        res = rp.run_segment()
        if res["events"] or not res["done"]:
            n += 1
            turns.append({"turn": n, "user": "Build M1." if n == 1 else "Checkpoint approved. Continue.",
                          "assistant": f"(replayed) segment {res['segment'] + 1}/{res['segments']}: " + "; ".join(res["events"][:30]),
                          "persona": "start" if n == 1 else "approve", "tools": [], "skills": [], "seconds": 0,
                          "usage": {}, "tool_errors": [], "agents": []})
        if res["done"]:
            break
    st = rp.state()
    (run / "turns.json").write_text(json.dumps(turns, indent=1))
    (run / "summary.json").write_text(json.dumps({"arm": arm_id, "target": "minilab", "turns": len(turns), "fake": True,
                                                  "total_seconds": st["clock"] - START, "finished": True,
                                                  "stop_reason": "dry run", "bad": bad}, indent=1))
    return rp


# ---- fixture checks -------------------------------------------------------------------------------------

def fixture_checks() -> list[str]:
    problems = []
    for script in ("oracle/make_cases.py", "scripts/gen_plan_interface.py"):
        r = subprocess.run([sys.executable, str(FIX / script), "--check"], capture_output=True, text=True)
        if r.returncode:
            problems.append(f"{script} --check: {r.stdout.strip()[-300:]}")
    src = [SOL / "packages" / p / "src" for p in ("mdata", "risk")]
    for name in ("oracle/test_visible.py", "holdout/test_holdout.py"):
        res = grade_build.pytest_junit([FIX / name], src, FIX)
        bad = [r["name"] for r in res if r["outcome"] != "pass"]
        if not res or bad:
            problems.append(f"solution fails {name}: {bad or 'no tests ran'}")
    muts = json.loads((FIX / "mutants" / "mutants.json").read_text())["mutants"]
    with tempfile.TemporaryDirectory(prefix="mut-") as tmp:
        t = pathlib.Path(tmp)
        shutil.copytree(SOL / "packages", t / "packages")
        for m in muts:
            f = t / m["file"]
            orig = f.read_text()
            if orig.count(m["find"]) != 1:
                problems.append(f"{m['id']}: `find` occurs {orig.count(m['find'])} times in {m['file']}")
                continue
            f.write_text(orig.replace(m["find"], m["replace"]))
            res = grade_build.pytest_junit([FIX / "oracle" / "test_visible.py", FIX / "holdout" / "test_holdout.py"],
                                           [t / "packages" / p / "src" for p in ("mdata", "risk")], FIX)
            f.write_text(orig)
            if res and all(r["outcome"] == "pass" for r in res):
                problems.append(f"{m['id']} survives every visible and holdout case")
        # The reference suite on the reference solution, and the interface tree's contract tests.
        tree = t / "full"
        shutil.copytree(FIX / "project", tree)
        shutil.copytree(SOL / "packages", tree / "packages")
        shutil.copytree(SOL / "tests", tree / "tests", dirs_exist_ok=True)
        res = grade_build.pytest_junit(["tests"], [tree / "packages" / p / "src" for p in ("mdata", "risk")], tree, cwd=tree)
        bad = [r["name"] for r in res if r["outcome"] != "pass"]
        if not res or bad:
            problems.append(f"solution's own suite fails: {bad[:6]}")
    return problems


# ---- main -----------------------------------------------------------------------------------------------

def grade(run: pathlib.Path) -> dict:
    return grade_build.Grader(run, FIX, quiet=True).grade()


def failed(g: dict) -> list[str]:
    return [r["id"] for r in g["expectations"] if not r["passed"] and r["category"] != "harness"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?")
    ap.add_argument("--fixture-only", action="store_true")
    ap.add_argument("--arm")
    a = ap.parse_args()
    probs = fixture_checks()
    print("fixture: " + ("ok (cases match the oracle, plan generator in sync, solution passes 8 visible + 6 holdout "
                         "cases and its own suite, every mutant killed)" if not probs else "\n  ".join(["PROBLEMS"] + probs)))
    if a.fixture_only:
        sys.exit(1 if probs else 0)
    out = pathlib.Path(a.out or tempfile.mkdtemp(prefix="dt-dryrun-build-")).resolve()
    arms = [a.arm] if a.arm else list(SCN["arms"])
    ok = not probs
    for arm in arms:
        run = out / "minilab" / arm / "replay"
        rp = replay(run, arm)
        g = grade(run)
        bad = failed(g)
        hf = g["harness_summary"]["failures"]
        gf = g["extra"].get("graph", {})
        print(f"{arm} good replay: {g['summary']['passed']}/{g['summary']['total']} design checks"
              f"{' — FAILED ' + str(bad) if bad else ''}{' — harness ' + str(hf) if hf else ''}  "
              f"({gf.get('tasks')} tasks, {len(gf.get('dispatch_rounds', []))} dispatch rounds, width {gf.get('dispatch_width')}, "
              f"mutants killed {len(g['extra'].get('mutants', {}).get('killed', []))})")
        for line in rp.log:
            print("   replay: " + line[:600])
        ok &= not bad and not hf and not rp.log
    if not a.arm:
        for bad_name, check_id in BADS.items():
            run = out / "minilab" / "A3" / f"bad-{bad_name}"
            replay(run, "A3", bad=bad_name)
            g = grade(run)
            hit = [r for r in g["expectations"] if r["id"] == check_id]
            caught = bool(hit) and not hit[0]["passed"]
            print(f"bad replay {bad_name}: {'caught by ' + check_id if caught else 'NOT CAUGHT (' + check_id + ')'}"
                  f"; all failing: {failed(g)}")
            ok &= caught
    print(f"runs: {out}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
