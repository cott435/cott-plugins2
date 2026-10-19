#!/usr/bin/env python3
"""Build-eval dry run, no model calls: check the minilab fixture against build-setup's real bar, replay a good
build of it from solution/ for every arm through the real `dt`, grade each replay, then replay five bad builds and
check each defect is caught.

A replay does what the arm's driver and agents would (build-phase.md §5–§7). For a build-skill arm:
`dt build start M1`, then rounds of `dt ready --reserve --cap N`; for each builder row a git worktree under
.claude/worktrees/ (the Agent tool's), `dt claim` in it, the half's files from solution/ written there and put
through `scripts/check.sh fast` (the post-edit hook), the claim marked finished (`dt build mark-finished`, the
SubagentStop hook); then `dt land` for each, in reservation order. Review rows get an empty findings file through
`dt build submit-review` and `dt finding --from`. The planted interface flaw goes the designed way: the drawdown
thicken's first half runs `dt escalate CONTRACT-CHANGE --type risk.Drawdown`, the rest drains, then
architecture-design Revise of the contract section and a build-planning Replan adding a re-freeze interface task
(both committed on build/M1), `dt build resolve` and `dt build go`. A0 does the same work in one checkout, in plan
order, with `dt context`, `scripts/check.sh collect|gate`, `dt tick` and a commit with a `Dt-Landed:` trailer.

fake_claude.py (FAKE_MODE=build) drives a `Replay` one driver turn at a time, so build_driver.py's loop runs for
free.

Usage:
  dryrun_build.py [out-dir]          fixture checks, every arm's good replay, the bad replays
  dryrun_build.py --fixture-only     only the fixture checks
  dryrun_build.py --arm A3 [out]     one good replay (graded)
  dryrun_build.py --bad NAME [out]   one bad replay (graded)
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
import time

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE / "fixtures" / "build" / "minilab"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(FIX / "scripts"))
import grade_build  # noqa: E402
import make_live  # noqa: E402

SOL = FIX / "solution"
REPLAY = json.loads((FIX / "replay.json").read_text())
PLANTED = json.loads((FIX / "planted.json").read_text())
SCN = json.loads((HERE / "scenarios.json").read_text())
DT = make_live.PLUGIN / "scripts" / "dt.py"
FLAW = PLANTED["interface_flaw"]
# bad replay → the grader check that must fail on it
BADS = {
    "merge_conflict": "merge_conflicts",
    "tester_edits_oracle": "protected_edit_attempts",
    "implementer_edits_types": "writes_respected",
    "branch_touches_tasks": "builders_never_edit_tasks",
    "importerror_red": "red_import_errors",
}
BAD_STEP = {"merge_conflict": "PL-02.rolling_vol", "tester_edits_oracle": "PL-02.rolling_vol",
            "implementer_edits_types": "PL-02.rolling_vol", "branch_touches_tasks": "PL-02.log_returns",
            "importerror_red": "PL-02.log_returns"}


class ReplayError(RuntimeError):
    pass


# ---- file contents --------------------------------------------------------------------------------------

def sol(rel: str) -> str:
    return (SOL / rel).read_text()


def stub_module(src: str, task: str) -> str:
    """The interface task's version of a step or entry module: signatures and docstrings kept, every top-level
    function body replaced by `raise NotImplementedError("<task>")` (CR-02's carve-out). Imports the bodies used
    are dropped by `check.sh fast` (ruff --fix), as the post-edit hook would."""
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node)
            raise_ = ast.parse(f"raise NotImplementedError({task!r})").body[0]
            node.body = ([ast.Expr(ast.Constant(doc))] if doc else []) + [raise_]
    head = ast.get_docstring(tree)
    return ast.unparse(tree) + "\n" if head else ast.unparse(tree) + "\n"


def interface_version(rel: str, text: str) -> str:
    """Before the contract change: types without the planted field, samples without it."""
    if rel.endswith("types.py"):
        return "".join(line for line in text.splitlines(True) if "# contract-change" not in line)
    if rel.endswith("sample.json") and FLAW["field"] in text:
        data = json.loads(text)

        def strip(d):
            return {k: v for k, v in d.items() if k != FLAW["field"]}
        data = strip(data) if "rows" not in data else dict(data, rows=[strip(r) for r in data["rows"]])
        return json.dumps(data, indent=1) + "\n"
    return text


def variant(spec: str) -> tuple[str, str]:
    """`path@spine` / `path@interface` / `path@stub:<task>` / `path` → (path, content)."""
    rel, _, how = spec.partition("@")
    if how.startswith("stub:"):
        return rel, stub_module(sol(rel), how.split(":", 1)[1])
    if how == "spine":
        return rel, (SOL / "spine" / rel).read_text()
    if how == "interface":
        return rel, interface_version(rel, sol(rel))
    return rel, sol(rel)


def solution_files(prefix: str) -> list[str]:
    base = SOL / prefix
    return sorted(str(p.relative_to(SOL)) for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def intent_of_golden(rel: str) -> str:
    """tests/unit/risk/test_vol_golden.py (a solo thicken's golden tests) → tests/intent/risk/test_vol.py."""
    return rel.replace("tests/unit/", "tests/intent/", 1).removesuffix("_golden.py") + ".py"


# ---- the replay -----------------------------------------------------------------------------------------

class Replay:
    """A good (or one-defect) build of minilab in <run>/project, through the real dt."""

    def __init__(self, run: pathlib.Path, arm_id: str, bad: str | None = None, dt: pathlib.Path = DT):
        self.run, self.arm_id, self.bad, self.dt_py = run, arm_id, bad, dt
        self.proj = run / "project"
        self.arm = SCN["arms"][arm_id]
        self.cap = 16 if bad == "merge_conflict" else self.arm.get("cap", 6)
        self.problems: list[str] = []          # anything a good replay must not see
        self.events: list[str] = []            # what happened, for the fake CLI's stream
        self.n = 0
        self.stopped = False                   # a bad replay stops once its defect is handled
        self.state_path = self.proj / ".git" / "replay_state.json"

    # -- processes --

    def sh(self, *cmd, cwd=None, check=True, input=None) -> subprocess.CompletedProcess:
        env = dict(os.environ, NO_COLOR="1", PYTHONDONTWRITEBYTECODE="1")
        env.pop("VIRTUAL_ENV", None)
        r = subprocess.run(cmd, cwd=cwd or self.proj, capture_output=True, text=True, input=input, env=env)
        if check and r.returncode:
            raise ReplayError(f"{' '.join(map(str, cmd))} (exit {r.returncode}):\n{(r.stdout + r.stderr)[-2000:]}")
        return r

    def git(self, *a, cwd=None, check=True):
        return self.sh("git", *a, cwd=cwd, check=check)

    def dt(self, *a, cwd=None, check=True, input=None):
        root = cwd or self.proj
        return self.sh(sys.executable, str(self.dt_py), "--root", str(root), *a, cwd=root, check=check, input=input)

    def dtj(self, *a, cwd=None, check=True):
        r = self.dt(*a, cwd=cwd, check=check)
        try:
            return json.loads(r.stdout)
        except ValueError as e:
            raise ReplayError(f"dt {' '.join(a)}: not JSON: {r.stdout[-500:]} {r.stderr[-500:]}") from e

    # -- state, for the fake CLI (one process per driver turn) --

    def state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text())
        except (OSError, ValueError):
            return {"phase": "build", "turn": 0}

    def save(self, st: dict) -> None:
        self.state_path.write_text(json.dumps(st))

    # -- the plan --

    def plan(self) -> dict:
        return grade_build.parse_plan((self.proj / "tasks" / "plan.md").read_text())

    def task(self, tid: str) -> dict:
        return grade_build.plan_by(self.plan())[tid]

    def flaw_task(self) -> str | None:
        """The drawdown thicken: the first task that needs the planted field."""
        return next((t["id"] for t in self.plan()["tasks"] if t["step"] == "PL-03.max_drawdown"
                     and t["kind"] == "thicken"), None)

    def cc_task(self) -> str | None:
        """The re-freeze task, once the Replan added it."""
        return next((t["id"] for t in self.plan()["tasks"] if t["title"] == REPLAY["contract_change"]["task_title"]),
                    None)

    def done(self) -> set[str]:
        return set(re.findall(r"^- \[x\] (M\d+-T\d+)", (self.proj / "tasks" / "todo.md").read_text(), re.M))

    # -- what each half writes --

    def stub_owner(self, rel: str, plan: dict) -> str:
        for t in plan["tasks"]:
            if t["kind"] != "interface" and rel in t["writes"]:
                return t["id"]
        return plan["tasks"][0]["id"]

    def files_of(self, tid: str, role: str) -> dict:
        plan = self.plan()
        t = grade_build.plan_by(plan)[tid]
        if tid == self.cc_task():                       # the re-freeze: the solution's types and samples
            return {rel: sol(rel) for rel in REPLAY["contract_change"]["files"]}
        if self.arm["plan"] == "spine":
            m = REPLAY["plan-spine"][tid]
            specs = m.get("tester", []) if role == "tester" else m["files"] + (m.get("tester", []) if role == "solo" else [])
            out = dict(variant(s) for s in specs)
            if role != "tester":                        # the unit tests the converted Writes name
                out.update({w: sol(w) for w in t["writes"] if w not in out and w.startswith("tests/unit/")
                            and (SOL / w).exists()})
            return out
        out = {}
        for w in t["writes"]:
            if w.endswith("/**"):
                for rel in solution_files(w[:-3]):
                    out[rel] = interface_version(rel, sol(rel))
                continue
            intent = w.startswith("tests/intent/")
            if (role == "tester" and not intent) or (role == "implementer" and intent):
                continue
            if t["kind"] == "interface":
                text = sol(w)
                out[w] = (interface_version(w, text) if w.endswith(("types.py", "__init__.py"))
                          else stub_module(text, self.stub_owner(w, plan)))
            elif w.endswith("_golden.py"):
                out[w] = sol(intent_of_golden(w))
            elif t["kind"] == "spine" and (SOL / "spine" / w).exists():
                out[w] = (SOL / "spine" / w).read_text()
            elif (SOL / w).exists():
                out[w] = sol(w)
            else:
                self.problems.append(f"{tid} {role}: no solution file for {w}")
        return out

    def defect(self, tid: str, role: str, files: dict) -> bool:
        """Apply this bad replay's defect to the half, if it is the one; True when it was applied."""
        b = self.bad
        if not b or self.task(tid)["step"] != BAD_STEP[b]:
            return False
        kind = self.task(tid)["kind"]
        if b == "merge_conflict" and kind == "spine":
            rel = "packages/risk/src/risk/returns.py"     # the plan gave this task returns.py too (setup)
            files[rel] = (SOL / "spine" / rel).read_text().replace('"""', '"""Rolling vol reads these. ', 1)
            return True
        if b == "tester_edits_oracle" and role == "tester":
            rel = "tests/fixtures/risk/TC-05/expected.json"
            exp = json.loads((self.proj / rel).read_text())
            exp["values"]["X"][-1] = 0.03
            files[rel] = json.dumps(exp, indent=1) + "\n"
            return True
        if b == "implementer_edits_types" and role == "implementer":
            rel = "packages/risk/src/risk/types.py"
            text = (self.proj / rel).read_text()
            files[rel] = text.replace("    window: int\n", "    window: int\n    min_periods: int = 0\n", 1)
            return True
        if b == "branch_touches_tasks" and role == "solo" and kind == "spine":
            files["tasks/todo.md"] = (self.proj / "tasks" / "todo.md").read_text().replace(
                f"- [ ] {tid} ", f"- [x] {tid} ", 1)
            return True
        if b == "importerror_red" and role == "tester":
            rel = next(k for k in files if k.startswith("tests/intent/"))
            files[rel] = files[rel].replace("from risk.returns import log_returns", "from risk.returns import log_return")
            return True
        return False

    def write(self, root: pathlib.Path, files: dict) -> None:
        for rel, text in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        py = [rel for rel in files if rel.endswith(".py")]
        if py:
            self.sh("bash", "scripts/check.sh", "fast", *py, cwd=root, check=False)   # the post-edit hook

    # -- one builder half in its worktree --

    def start_half(self, row: dict) -> dict:
        self.n += 1
        tid, role = row["id"], row["role"]
        name = f"agent-{tid.lower()}-{role}-{self.n}"
        wt = self.proj / ".claude" / "worktrees" / name
        self.git("worktree", "add", "-q", "-b", f"worktree-{name}", str(wt), "HEAD")
        r = self.dt("claim", tid, "--role", role, cwd=wt, check=False)
        if r.returncode:
            self.problems.append(f"dt claim {tid} {role}: {r.stderr.strip()[-300:]}")
        return {"id": tid, "role": role, "wt": wt, "claimed": r.returncode == 0}

    def work_half(self, h: dict) -> None:
        tid, role, wt = h["id"], h["role"], h["wt"]
        first_half = role in ("tester", "solo")
        if tid == self.flaw_task() and first_half and not self.cc_task():
            self.dt("escalate", "CONTRACT-CHANGE", f"{FLAW['type']} has no {FLAW['field']}; {FLAW['surfaces_at']} needs it",
                    "--type", FLAW["type"], cwd=wt)
            h["status"] = f"STOPPED {tid} {role}: see dt escalate"
        else:
            files = self.files_of(tid, role)
            h["defect"] = self.defect(tid, role, files)
            self.write(wt, files)
            h["status"] = f"DONE {tid} {role}"
        agent = "tester" if role == "tester" else "implementer"
        self.dt("build", "mark-finished", input=json.dumps({"cwd": str(wt), "agent_type": agent}))

    def land_half(self, h: dict) -> dict:
        res = self.dtj("land", h["id"], "--role", h["role"], check=False)
        what = "landed" if res.get("landed") else f"reject {res.get('reject')}" + (f" {res['kind']}" if res.get("kind") else "")
        self.events.append(f"{h['id']} {h['role']}: {what}")
        expected = res.get("reject") == "escalated" and res.get("kind") == "CONTRACT-CHANGE"
        if not res.get("landed") and not expected and not self.bad:
            detail = pathlib.Path(res["detail_file"]).read_text()[-1500:] if res.get("detail_file") else res
            self.problems.append(f"{h['id']} {h['role']}: {what}\n{detail}")
        if h.get("defect"):
            self.stopped = True
        return res

    def review(self, row: dict) -> None:
        rid = row["id"]
        f = self.run / "reviews" / f"{rid}.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("No findings.\n")
        self.dtj("build", "submit-review", rid, str(f))
        common = pathlib.Path(self.git("rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
        self.dtj("finding", "--from", str(common / "dt-build" / "reviews" / f"{rid}.md"),
                 "--checkpoint", row["checkpoint"], "--pkg", row["pkg"])
        self.events.append(f"REVIEW {row['checkpoint']} {row['pkg']}: 0 findings, 0 Critical")

    # -- the planted flaw: Revise, Replan, resolve, go --

    def contract_change(self, escalated: str | None) -> None:
        cc = REPLAY["contract_change"]
        doc = self.proj / cc["contract_doc"]
        doc.write_text(doc.read_text().replace(cc["doc_find"], cc["doc_replace"], 1))
        self.commit(f"architecture-design: Revise {FLAW['type']} (contract-change from {escalated or 'the build'})")
        plan = self.plan()
        new = "M1-T%02d" % (max(int(t["id"].split("T")[1]) for t in plan["tasks"]) + 1)
        flaw = self.flaw_task()
        writes = ["packages/risk/src/risk/types.py", "tests/contracts/risk.Drawdown/**", "tests/contracts/risk.Report/**"]
        block = (f"### {new}: {cc['task_title']}\n**Package:** risk · **Step:** contract · **Kind:** interface · "
                 f"**Size:** S · **Mode:** solo\n**Read:** {FLAW['type']}, RISK-05, TC-08\n**Acceptance:**\n"
                 f"- [ ] `{FLAW['type']}` carries `{FLAW['field']}`; its samples and the Report sample show it\n"
                 f"**Verify:** `pytest tests/contracts` · `scripts/check.sh gate`\n"
                 f"**Depends on:** — · **Writes:** {', '.join(writes)}\n\n")
        path = self.proj / "tasks" / "plan.md"
        text = path.read_text().replace(f"### {flaw}:", block + f"### {flaw}:", 1)
        done = self.done()
        for t in plan["tasks"]:
            if t["id"] in done or not (t["id"] == flaw or FLAW["type"] in t["read"]):
                continue
            head = text.index(f"### {t['id']}:")
            m = re.compile(r"\*\*Depends on:\*\* ([^·\n]*)").search(text, head)
            deps = m.group(1).strip()
            text = text[:m.start(1)] + (new if deps in ("—", "-", "") else f"{deps}, {new}") + " " + text[m.end(1):]
        path.write_text(text)
        todo = self.proj / "tasks" / "todo.md"
        todo.write_text(todo.read_text().rstrip("\n") + f"\n- [ ] {new} {cc['task_title']} (risk, S, solo)\n")
        self.commit(f"M1: Replan adds {new}, re-freezing {FLAW['type']} before {flaw}")
        if escalated:
            self.dtj("build", "resolve", escalated, "--note", "Yes: change the contract.")
            self.dtj("build", "go", "--note", "Go.")
        self.events.append(f"contract-change: Revise {FLAW['type']}, Replan adds {new}")

    def commit(self, msg: str, root=None) -> None:
        self.git("add", "-A", cwd=root)
        self.git("-c", "user.email=d@d", "-c", "user.name=driver", "commit", "-q", "--no-verify", "-m", msg, cwd=root)

    # -- the build-skill loop --

    def loop(self) -> str:
        """Dispatch and land until a stop: `contract-change` (the escalation drained, the user's yes needed),
        `exit` (every task landed and the exit review recorded), `stuck` or `defect` (a bad replay's)."""
        while not self.stopped:
            ready = self.dtj("ready", "--reserve", "--cap", str(self.cap), "--json")
            rows = ready["rows"]
            if not rows:
                if ready["all_landed"]:
                    return "exit"
                esc = [h for h in ready["held"] if h["why"].startswith("escalation:") or "CONTRACT-CHANGE" in h["why"]]
                if esc:
                    return "contract-change"
                self.problems.append(f"nothing ready, not all landed: holds {ready['holds']}, held {ready['held'][:6]}")
                return "stuck"
            for r in [r for r in rows if r["role"] == "reviewer"]:
                self.review(r)
            halves = [self.start_half(r) for r in rows if r["role"] != "reviewer"]
            for h in halves:
                if h["claimed"]:
                    self.work_half(h)
            for h in halves:
                self.land_half(h)
                if self.stopped:
                    break
        return "defect"

    def escalated_task(self) -> str | None:
        common = pathlib.Path(self.git("rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
        for f in sorted((common / "dt-build" / "escalations").glob("*.json")):
            e = json.loads(f.read_text())
            if e.get("kind") == "CONTRACT-CHANGE":
                return e["task"]
        return None

    # -- A0: one session, plan order, no subagents --

    def serial_session(self) -> str:
        self.dt("build", "start", "M1")
        while True:
            done = self.done()
            todo = [t for t in self.plan()["tasks"] if t["id"] not in done]
            if not todo:
                return "exit"
            t = todo[0]
            if t["id"] == self.flaw_task() and not self.cc_task():
                self.events.append(f"{t['id']}: {FLAW['type']} has no {FLAW['field']}; asking")
                self.contract_change(None)
                continue
            self.serial_task(t)

    def serial_task(self, t: dict) -> None:
        tid, pkg = t["id"], t["package"]
        self.dt("context", tid)
        base = lambda: self.git("update-ref", "refs/worktree/checks-base", "HEAD")  # noqa: E731
        base()
        roles = ["tester", "implementer"] if t["mode"] == "split" else ["solo"]
        for role in roles:
            files = self.files_of(tid, role)
            self.write(self.proj, files)
            claim = self.proj / ".claude" / ".task_writes"
            if tid == self.cc_task():                   # a re-freeze names the frozen folders it writes
                claim.write_text("".join(f"{w}\n" for w in t["writes"]))
            mode = ["collect"] if role == "tester" else ["gate", "--pkg", pkg]
            r = self.sh("bash", "scripts/check.sh", *mode, check=False)
            claim.unlink(missing_ok=True)
            if r.returncode:
                self.problems.append(f"{tid} {role}: check.sh {' '.join(mode)} failed:\n{r.stderr[-1500:]}")
            if role != "tester":
                self.dt("tick", tid)
            msg = f"{tid}: {'tests' if role == 'tester' else t['title']}\n\nDt-Landed: {tid} {role}\n"
            self.commit(msg)
            base()
            self.events.append(f"{tid} {role}: committed")

    # -- driving --

    def setup(self) -> None:
        """A live minilab with the arm's plan (and a bad replay's plan change), as build_driver.py makes it."""
        if self.proj.exists():
            shutil.rmtree(self.proj)
        make_live.make(self.proj, self.arm["plan"], self.dt_py.parents[1])
        if self.bad == "merge_conflict":           # a lint gap: two spines both claim returns.py
            path = self.proj / "tasks" / "plan.md"
            text = path.read_text()
            m = re.search(r"(### M1-T\d+: rolling_vol spine.*?\*\*Writes:\*\* )", text, re.S)
            path.write_text(text[:m.end()] + "packages/risk/src/risk/returns.py, " + text[m.end():])
            self.commit("M1: (bad replay) the rolling_vol spine also writes returns.py")

    def turn(self) -> str:
        """One driver turn: until the next stop, picking up after the previous one. Returns the stop."""
        st = self.state()
        st["turn"] += 1
        if self.arm["dispatch"] == "session":
            stop = self.serial_session()
        else:
            if st["phase"] == "build" and st["turn"] == 1:
                self.dt("build", "start", "M1")
            if st["phase"] == "contract-change":
                self.contract_change(self.escalated_task())
            stop = self.loop()
        st["phase"] = stop
        self.save(st)
        return stop

    def replay(self) -> str:
        """Setup and every turn, as the persona answers: yes to the contract change, then to the exit."""
        t0 = time.time()
        self.setup()
        stops = []
        while True:
            stop = self.turn()
            stops.append(stop)
            if stop != "contract-change" or len(stops) > 3:
                break
        if stop == "exit" and self.arm["dispatch"] != "session":
            self.check_exit()
        turns = [{"turn": i + 1, "user": "Build M1. Go." if i == 0 else "Yes: change the contract.",
                  "assistant": f"(replayed) stop: {s}", "persona": "start" if i == 0 else "contract_change",
                  "tools": [], "skills": [], "seconds": 0, "usage": {}, "tool_errors": [], "agents": []}
                 for i, s in enumerate(stops)]
        (self.run / "turns.json").write_text(json.dumps(turns, indent=1))
        (self.run / "summary.json").write_text(json.dumps({
            "arm": self.arm_id, "target": "minilab", "plan": self.arm["plan"], "turns": len(turns), "fake": True,
            "total_seconds": round(time.time() - t0, 1), "finished": stop == "exit", "stop_reason": stop,
            "bad": self.bad, "events": self.events[-60:]}, indent=1))
        return stop

    def check_exit(self) -> None:
        status = self.dtj("build", "status")
        if status["progress"].split("/")[0] != status["progress"].split("/")[1]:
            self.problems.append(f"exit with {status['progress']} landed")


# ---- fixture checks -------------------------------------------------------------------------------------

def fixture_checks() -> list[str]:
    problems = []
    for script in ("oracle/make_cases.py", "scripts/gen_plans.py"):
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
    problems += real_bar_checks()
    return problems


def real_bar_checks() -> list[str]:
    """build-setup's real bar on a live minilab: solution/ passes `check.sh full --exit` (its own suite included),
    solution/spine/ over it passes `check.sh full` with the unit and contract tests (the intent and system tests
    need the thickened steps), and every plan variant lints clean."""
    problems = []
    with tempfile.TemporaryDirectory(prefix="minilab-bar-") as tmp:
        live = pathlib.Path(tmp) / "live"
        make_live.make(live, "interface")
        for plan in make_live.PLANS:
            shutil.copytree(FIX / f"plan-{plan}" / "tasks", live / "tasks", dirs_exist_ok=True)
            r = subprocess.run([sys.executable, str(DT), "--root", str(live), "lint"], capture_output=True, text=True)
            errs = [line for line in r.stdout.splitlines() if re.search(r":\d+: \S+ ", line)]
            if errs:
                problems.append(f"dt lint plan-{plan}: " + "; ".join(errs[:4]))
        shutil.copytree(FIX / "plan-interface" / "tasks", live / "tasks", dirs_exist_ok=True)
        for spine, mode in ((False, ["full", "--exit"]), (True, ["full"])):
            make_live.render_solution(live, spine=spine)
            if spine:                                   # a spine passes its unit and contract tests, not the TCs
                for d in ("tests/intent", "tests/system"):
                    shutil.rmtree(live / d, ignore_errors=True)
            r = subprocess.run(["bash", "scripts/check.sh", *mode], cwd=live, capture_output=True, text=True,
                               env={k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"})
            if r.returncode:
                failed = [line for line in r.stderr.splitlines() if line.startswith("FAILED")]
                problems.append(f"solution{'/spine' if spine else ''} fails check.sh {' '.join(mode)}: {failed}")
    return problems


# ---- main -----------------------------------------------------------------------------------------------

def grade(run: pathlib.Path) -> dict:
    return grade_build.Grader(run, FIX, quiet=True).grade()


def failed(g: dict) -> list[str]:
    return [r["id"] for r in g["expectations"] if not r.get("na") and not r["passed"] and r["category"] != "harness"]


def good(out: pathlib.Path, arm: str) -> bool:
    run = out / "minilab" / arm / "replay"
    rp = Replay(run, arm)
    try:
        stop = rp.replay()
    except ReplayError as e:
        print(f"{arm} good replay: ERROR {e}")
        return False
    g = grade(run)
    bad = failed(g)
    hf = g["harness_summary"]["failures"]
    gf = g["extra"].get("graph", {})
    print(f"{arm} good replay: stop {stop}; {g['summary']['passed']}/{g['summary']['total']} design checks"
          f"{' — FAILED ' + str(bad) if bad else ''}{' — harness ' + str(hf) if hf else ''}  "
          f"({gf.get('tasks')} tasks, width {gf.get('width')}, concurrency "
          f"{g['extra'].get('efficiency', {}).get('achieved_max_concurrency')}, "
          f"mutants killed {len(g['extra'].get('mutants', {}).get('killed', []))})")
    for line in rp.problems:
        print("   replay: " + line[:800])
    return stop == "exit" and not bad and not rp.problems


def bad_replay(out: pathlib.Path, name: str) -> bool:
    run = out / "minilab" / "A3" / f"bad-{name}"
    rp = Replay(run, "A3", bad=name)
    try:
        stop = rp.replay()
    except ReplayError as e:
        print(f"bad replay {name}: ERROR {e}")
        return False
    g = grade(run)
    check = BADS[name]
    hit = [r for r in g["expectations"] if r["id"] == check]
    caught = stop == "defect" and bool(hit) and not hit[0]["passed"]
    print(f"bad replay {name}: {'caught by ' + check if caught else 'NOT CAUGHT (' + check + ')'}"
          f" — {hit[0]['evidence'][:160] if hit else 'no such check'}; stop {stop}")
    return caught


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?")
    ap.add_argument("--fixture-only", action="store_true")
    ap.add_argument("--arm")
    ap.add_argument("--bad", choices=list(BADS))
    a = ap.parse_args()
    if not (a.arm or a.bad):
        probs = fixture_checks()
        print("fixture: " + ("ok (cases match the oracle, plans in sync and lint-clean, solution passes 8 visible + "
                             "6 holdout cases, every mutant killed, the real bar passes on solution/ and its spine)"
                             if not probs else "\n  ".join(["PROBLEMS"] + probs)))
        if a.fixture_only:
            sys.exit(1 if probs else 0)
        ok = not probs
    else:
        ok = True
    out = pathlib.Path(a.out or tempfile.mkdtemp(prefix="dt-dryrun-build-")).resolve()
    if a.bad:
        ok &= bad_replay(out, a.bad)
    else:
        arms = [a.arm] if a.arm else [k for k, v in SCN["arms"].items() if v.get("replay", True)]
        for arm in arms:
            ok &= good(out, arm)
        if not a.arm:
            for name in BADS:
                ok &= bad_replay(out, name)
    print(f"runs: {out}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
