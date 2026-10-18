#!/usr/bin/env python3
"""Grade one build-eval run (interface-first-design.md §9.2, build-phase.md §15): writes <run>/grading.json in the
planning grader's shape (expectations, summary, execution_metrics, timing, extra), so runviz and package read it
unchanged.

Every graph fact is recomputed here from the plan text and git, never taken from `dt` (a dt bug can't grade
itself). Each expectation carries a `category`: efficiency, integration, correctness, tdd, process or harness.
`harness` checks are summarised apart in `harness_summary` and never count in `summary`.

What the run is read from (build_driver.py writes it; dryrun_build.py replays it):
- <run>/project: the git repo. The base (the state before the build) is the commit `dt build start` branched from
  (its `start` log event's parent), else build/M1's merge-base with `main` or `master`; `build/M1` the build branch, whose first
  parent holds every landing: a commit with the trailer `Dt-Landed: <task> <role>` (implementer, solo; and, in A0,
  tester), and `dt/<task>-tests` each split task's tester landing. Tasks and roles come only from those trailers,
  never from commit subjects or branch names. A0 writes its own trailers: weaker evidence, marked in `extra`.
- <project>/.git/dt-build/log.jsonl: claims, finished agents, landings, rejects (writes, gate, conflict,
  integration, escalated, harness, each with its detail file), escalations, resolves, the go, reviews.
- <run>/agent_stream.jsonl: the main session's stream-json (result events: cost, usage, permission_denials);
  the session's subagent transcripts beside its transcript under ~/.claude/projects/; <run>/flow/index.json
  (workflow-analyzer units: each agent's time and tokens); turns.json, summary.json.

A target with a fixture (minilab) is graded against its oracle, holdout, mutants and planted.json. A project target
(`"project"` in scenarios.json, a planning run's project) has none of them: those checks are `na` (kept for lining up
with fixture runs, never counted), and correctness is the project's own golden cases instead: the build's
tests/intent run on build/M1's tree in the project's venv with every marker, `oracle_unchanged` over tests/fixtures,
and `interface_changes` counted with no planted flaw. Everything keyed on dt is the same for both.

Usage: grade_build.py <run-dir> [--fixture DIR] [--quiet]
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime

HERE = pathlib.Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "build"
TASK = re.compile(r"\bM\d+-T\d+\b")
SIZE_W = {"XS": 1, "S": 2, "M": 4}
TRAILER = re.compile(r"^Dt-Landed:\s*(M\d+-T\d+)\s+(tester|implementer|solo)\b", re.M)
INTERFACE_PATHS = ["packages/*/src/*/types.py", "packages/*/src/*/protocols.py", "src/*/types.py", "src/*/protocols.py",
                   "tests/contracts/*"]
PROTECTED = ["tests/intent/*", "tests/fixtures/*", "tests/conftest.py", "pyproject.toml", "uv.lock", "CONSTRAINTS.md",
             "scripts/*", ".claude/agents/*", ".claude/settings.json", "references/*", "packages/*/pyproject.toml"]
WRONG_RED = ("ImportError", "ModuleNotFoundError", "AttributeError", "NameError")
GOLDEN_TIMEOUT = int(os.environ.get("GOLDEN_TIMEOUT", "1800"))   # a project's intent tests may train for real


# ---- the plan -------------------------------------------------------------------------------------------

def field(block: str, name: str) -> str:
    m = re.search(rf"\*\*{re.escape(name)}:\*\*\s*(.*?)(?=\s+·\s+\*\*|\n|$)", block)
    return m.group(1).strip() if m else ""


def paths(cell: str) -> list[str]:
    return [p.strip().strip("`") for p in cell.split(",") if p.strip() and p.strip() not in ("—", "-")]


def parse_plan(text: str) -> dict:
    """Tasks (in plan order), checkpoints (after which task) and dependency-graph rows of a plan.md."""
    tasks, checkpoints = [], []
    heads = list(re.finditer(r"^### (.+)$", text, re.M))
    for i, h in enumerate(heads):
        block = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        block = block.split("\n## ")[0]
        title = h.group(1)
        m = re.match(r"(M\d+-T\d+):\s*(.*)", title)
        if m:
            writes = paths(field(block, "Writes"))
            t = {"id": m.group(1), "title": m.group(2), "package": field(block, "Package"),
                 "step": field(block, "Step"), "kind": field(block, "Kind").lower(), "size": field(block, "Size"),
                 "mode": field(block, "Mode").lower(), "reason": field(block, "Reason"),
                 "depends": TASK.findall(field(block, "Depends on")), "writes": writes,
                 "files_likely": paths(field(block, "Files likely")), "claims_exclusive": bool(writes),
                 "parallel": field(block, "Parallel"), "read": paths(field(block, "Read")),
                 "verify": re.findall(r"`([^`]+)`", field(block, "Verify"))}
            t["claims"] = writes or t["files_likely"]
            t["kind"] = t["kind"] or derive_kind(t)
            tasks.append(t)
        elif title.lower().startswith("checkpoint"):
            after = TASK.search(title)
            checkpoints.append({"title": title, "after": after.group(0) if after else (tasks[-1]["id"] if tasks else None),
                                "exit": "exit" in title.lower(), "barrier": "(barrier)" in title.lower()})
    graph = []
    gm = re.search(r"^## Dependency graph\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    for line in (gm.group(1).splitlines() if gm else []):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and TASK.search(cells[0]) and TASK.search(cells[1]):
            graph.append({"src": TASK.search(cells[0]).group(0), "dst": TASK.search(cells[1]).group(0),
                          "kind": cells[2], "mitigated_by": "" if cells[3].lower().startswith("none") else cells[3]})
    return {"tasks": tasks, "checkpoints": checkpoints, "graph": graph}


def derive_kind(t: dict) -> str:
    """A plan without `**Kind:**`: contract → interface, a system spine → system, a whole pipeline → spine,
    a step of a pipeline → thicken."""
    if t["step"] == "contract":
        return "interface"
    if "system" in t["reason"].lower():
        return "system"
    if re.fullmatch(r"PL-\d+", t["step"]):
        return "spine"
    return "thicken"


def waves(tasks: list[dict]) -> list[list[str]]:
    """Topological levels by `Depends on` only (mitigated edges don't order)."""
    ids = [t["id"] for t in tasks]
    deps = {t["id"]: [d for d in t["depends"] if d in ids] for t in tasks}
    level: dict[str, int] = {}

    def lv(i, seen=()):
        if i not in level:
            if i in seen:
                raise ValueError(f"dependency cycle through {i}")
            level[i] = 1 + max((lv(d, seen + (i,)) for d in deps[i]), default=-1)
        return level[i]
    for i in ids:
        lv(i)
    out = [[] for _ in range(max(level.values(), default=-1) + 1)]
    for i in ids:
        out[level[i]].append(i)
    return out


def critical_path(tasks: list[dict], weight=lambda t: 1) -> tuple[list[str], int]:
    by = {t["id"]: t for t in tasks}
    best: dict[str, tuple[int, list[str]]] = {}
    for wave in waves(tasks):
        for i in wave:
            prev = max((best[d] for d in by[i]["depends"] if d in best), default=(0, []), key=lambda x: x[0])
            best[i] = (prev[0] + weight(by[i]), prev[1] + [i])
    w, path = max(best.values(), default=(0, []), key=lambda x: x[0])
    return path, w


def graph_facts(plan: dict, arm: dict | None = None) -> dict:
    tasks = plan["tasks"]
    w = waves(tasks)
    cp, n_cp = critical_path(tasks)
    cpw, n_cpw = critical_path(tasks, lambda t: SIZE_W.get(t["size"], 2))
    split = [t["id"] for t in tasks if t["mode"] == "split"]
    iface = [t["id"] for t in tasks if t["kind"] == "interface"]
    ready_after_iface = [t["id"] for t in tasks if t["id"] not in iface and set(t["depends"]) <= set(iface)]
    testers_early = [i for i in split if i not in ready_after_iface] if iface else []
    cap = (arm or {}).get("cap", 6)
    return {"tasks": len(tasks), "halves": len(tasks) + len(split), "critical_path": cp, "cp_tasks": n_cp,
            "cp_weighted": n_cpw, "cp_weighted_path": cpw, "waves": w, "width": max((len(x) for x in w), default=0),
            "parallelism": round(len(tasks) / max(n_cp, 1), 2), "split_tasks": split,
            "ready_after_interface": ready_after_iface,
            "wave1_halves": len(ready_after_iface) + len(testers_early), "cap": cap,
            "planned_max_concurrency": min(cap, len(ready_after_iface) + len(testers_early)) if cap else 0}


def plan_by(plan: dict) -> dict:
    return {t["id"]: t for t in plan["tasks"]}


def match(path: str, globs: list[str]) -> bool:
    for g in globs:
        g = g.strip("/")
        if path == g or fnmatch.fnmatch(path, g) or (g.endswith("/**") and path.startswith(g[:-3] + "/")) \
                or (g.endswith("/") and path.startswith(g)):
            return True
    return False


def role_writes(task: dict, role: str) -> list[str]:
    """dt's split of `Writes:`: tester the tests/intent/ paths, implementer the rest, solo all."""
    intent = [w for w in task["writes"] if w.startswith("tests/intent/")]
    if role == "tester":
        return intent
    if role == "implementer":
        return [w for w in task["writes"] if w not in intent]
    return list(task["writes"]) or list(task["files_likely"])


# ---- git ------------------------------------------------------------------------------------------------

class Repo:
    def __init__(self, root: pathlib.Path):
        self.root = root

    def git(self, *a) -> str:
        return subprocess.run(["git", *a], cwd=self.root, capture_output=True, text=True).stdout

    def rc(self, *a) -> int:
        return subprocess.run(["git", *a], cwd=self.root, capture_output=True, text=True).returncode

    def ref(self, name: str) -> str | None:
        out = self.git("rev-parse", "-q", "--verify", f"{name}^{{commit}}").strip()
        return out or None

    def show(self, rev: str, path: str) -> str | None:
        r = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=self.root, capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None

    def commit(self, sha: str) -> dict:
        """sha, parents, time, subject, body, files changed against the first parent."""
        head = self.git("show", "-s", "--format=%H%x1f%P%x1f%ct%x1f%s%x1f%B", sha)
        h, parents, ct, subject, body = (head.split("\x1f") + [""] * 5)[:5]
        first = parents.split()[0] if parents.split() else None
        files = self.git("diff", "--name-only", "--no-renames", first, sha).split() if first else \
            self.git("show", "--name-only", "--format=", sha).split()
        return {"sha": h.strip(), "parents": parents.split(), "time": int(ct or 0), "subject": subject,
                "body": body, "files": files}

    def first_parent(self, rev: str) -> list[str]:
        return self.git("rev-list", "--first-parent", "--reverse", rev).split()

    def branches(self, pattern: str) -> dict[str, str]:
        out = self.git("for-each-ref", "--format=%(refname:short) %(objectname)", f"refs/heads/{pattern}")
        return dict(line.split() for line in out.splitlines() if line.strip())


def landings(repo: Repo, build: str, base: str | None) -> list[dict]:
    """Every `Dt-Landed:` landing: on build's first parent after the base, and each dt/<task>-tests tip."""
    out = []
    shas = repo.first_parent(build)
    if base and base in shas:
        shas = shas[shas.index(base) + 1:]
    for sha in shas:
        c = repo.commit(sha)
        for task, role in TRAILER.findall(c["body"]):
            out.append(dict(c, task=task, role=role, where="build"))
    for br, tip in repo.branches("dt/*-tests").items():
        c = repo.commit(tip)
        for task, role in TRAILER.findall(c["body"]):
            out.append(dict(c, task=task, role=role, where=br))
    return sorted(out, key=lambda c: c["time"])


def build_base(repo: Repo, build: str | None, log: list[dict] | None = None) -> str | None:
    """The commit the build started from, never assuming a branch name: the parent of the commit `dt build start`
    made (its `start` log event), else build's merge-base with `main` or `master`, else the parent of the first
    `M<n>: build started` commit on build's first parent."""
    if not build:
        return None
    for e in log or []:
        if e.get("event") == "start" and e.get("commit"):
            parent = repo.ref(f"{e['commit']}^")
            if parent:
                return parent
    for name in ("main", "master"):
        if repo.ref(f"refs/heads/{name}"):
            mb = repo.git("merge-base", build, f"refs/heads/{name}").strip()
            if mb:
                return mb
    for sha in repo.first_parent(build):
        if re.match(r"M\d+: build started", repo.git("show", "-s", "--format=%s", sha).strip()):
            return repo.ref(f"{sha}^")
    return None


def src_dirs(tree: pathlib.Path) -> list[pathlib.Path]:
    """A tree's source roots: `src` (single package) and every `packages/*/src` (a workspace)."""
    return [d for d in [tree / "src", *sorted(tree.glob("packages/*/src"))] if d.is_dir()]


# ---- the grader -----------------------------------------------------------------------------------------

class Grader:
    def __init__(self, run: pathlib.Path, fixture: pathlib.Path | None = None, quiet=False):
        self.run, self.quiet = run, quiet
        self.proj = run / "project"
        self.repo = Repo(self.proj)
        self.summary = self.load("summary.json") or {}
        self.turns = self.load("turns.json") or []
        scn = json.loads((HERE / "scenarios.json").read_text())
        self.arm_id = self.summary.get("arm") or os.environ.get("BUILD_ARM", "A3")
        self.arm = dict((scn.get("arms") or {}).get(self.arm_id, {}), id=self.arm_id)
        target = self.summary.get("target", "minilab")
        tcfg = (scn.get("build_targets") or {}).get(target, {})
        if fixture:
            self.fixture = fixture
        elif tcfg.get("fixture"):
            self.fixture = HERE / tcfg["fixture"]
        elif tcfg.get("project"):
            self.fixture = None            # a planning run's project: its own golden cases, no oracle/holdout/mutants
        else:
            self.fixture = FIXTURES / "minilab"
        self.planted = json.loads((self.fixture / "planted.json").read_text()) if self.fixture else None
        self.R, self.extra = [], {}
        self.build = self.repo.ref("build/M1") or self.repo.ref("HEAD")
        self.log = self.read_log()
        self.base = build_base(self.repo, self.build, self.log) or self.repo.ref("main")
        self.plan0 = parse_plan(self.repo.show(self.base, "tasks/plan.md") or "") if self.base else {"tasks": []}
        final = self.repo.show(self.build, "tasks/plan.md") if self.build else None
        self.plan = parse_plan(final) if final else self.plan0
        self.lands = landings(self.repo, self.build, self.base) if self.build else []
        self.python = self.venv_python()

    def load(self, name):
        try:
            return json.loads((self.run / name).read_text())
        except (OSError, ValueError):
            return None

    def read_log(self) -> list[dict]:
        p = self.proj / ".git" / "dt-build" / "log.jsonl"
        out = []
        for line in (p.read_text().splitlines() if p.exists() else []):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
        return out

    def venv_python(self) -> str:
        """The project's own interpreter (pytest, hypothesis); the grader's when the venv is gone."""
        py = self.proj / ".venv" / "bin" / "python"
        return str(py) if py.exists() else sys.executable

    def rejects(self, kind: str | None = None) -> list[dict]:
        return [e for e in self.log if e.get("event") == "reject" and (kind is None or e.get("reject") == kind)]

    def detail(self, e: dict) -> str:
        try:
            return pathlib.Path(e.get("detail_file") or "").read_text()
        except OSError:
            return ""

    def check(self, id_, category, text, passed, evidence, value=None):
        r = {"id": id_, "category": category, "text": text, "passed": bool(passed), "evidence": str(evidence)[:600]}
        if value is not None:
            r["value"] = value
        self.R.append(r)

    def na(self, id_, category, text, why):
        """A check this target can't run (no fixture oracle): kept so ids line up across targets, never counted."""
        self.R.append({"id": id_, "category": category, "text": text, "passed": None, "na": True, "evidence": why})

    # -- efficiency --------------------------------------------------------------------------------------

    def intervals(self) -> list[dict]:
        """One per claim: its half, claim and finish times (finish: SubagentStop, else its land or reject) and the
        most claims in flight while it was. Concurrency counts by log order, so ties within a second count."""
        out, live, peak = {}, set(), 0
        for e in self.log:
            ev, cid = e.get("event"), e.get("claim")
            if ev == "claim":
                live.add(cid)
                peak = max(peak, len(live))
                out[cid + f"#{len(out)}"] = {"claim": cid, "start": ts(e["time"]), "end": None}
            elif ev in ("finished", "land", "reject", "release") and cid in live:
                live.discard(cid)
                for v in reversed(list(out.values())):
                    if v["claim"] == cid and v["end"] is None:
                        v["end"] = ts(e["time"])
                        break
        self.extra["log_peak_in_flight"] = peak
        return [v for v in out.values() if v["end"] is not None]

    def efficiency(self):
        g0 = graph_facts(self.plan0, self.arm)
        self.extra["graph"] = g0
        ivs = self.intervals()
        peak = self.extra.get("log_peak_in_flight", 0)
        agent_s = sum(v["end"] - v["start"] for v in ivs)
        idx = self.load("flow/index.json") or {}
        per_role: dict[str, dict] = {}
        tokens = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}
        for u in idx.get("units", []):
            r = per_role.setdefault(u.get("type") or "agent", {"units": 0, "seconds": 0.0, "output_tokens": 0})
            r["units"] += 1
            try:
                r["seconds"] += ts(u["last_ts"]) - ts(u["first_ts"])
            except (KeyError, TypeError, ValueError):
                pass
            t = u.get("tokens") or {}
            r["output_tokens"] += t.get("output", 0) or t.get("output_tokens", 0) or 0
        stream = self.stream_results()
        for res in stream:
            for k, src in (("input", "input_tokens"), ("output", "output_tokens"),
                           ("cache_read", "cache_read_input_tokens"), ("cache_creation", "cache_creation_input_tokens")):
                tokens[k] += ((res.get("usage") or {}).get(src) or 0)
        wall = self.summary.get("total_seconds") or 0
        width = g0["planned_max_concurrency"] or 1
        eff = round(agent_s / (wall * width), 3) if wall and agent_s else None
        if self.arm.get("dispatch") == "session":
            peak = 1 if self.lands else 0
        self.extra["efficiency"] = {
            "wall_seconds": wall, "agent_seconds": round(agent_s, 1), "claims": len(ivs),
            "cost_usd": self.summary.get("agent_cost_usd"), "main_session_tokens": tokens,
            "per_role_units": per_role, "achieved_max_concurrency": peak, "planned_max_concurrency": width,
            "parallel_efficiency": eff, "planned_cp_tasks": g0["cp_tasks"], "planned_waves": len(g0["waves"]),
            "tasks_landed": len({c["task"] for c in self.lands}),
            "landings_from": "trailers the A0 session wrote itself (weaker evidence)" if self.arm.get("dispatch") ==
                             "session" else "dt land"}
        self.check("wall_clock", "efficiency", "Wall clock and agent time measured (informational)", bool(wall),
                   f"wall {wall}s, agent {round(agent_s)}s over {len(ivs)} claims, cost {self.summary.get('agent_cost_usd')}",
                   value=wall)
        if self.arm.get("cap", 1) > 1:
            self.check("achieved_concurrency", "efficiency",
                       "Builders overlap in time: ≥ 2 claims in flight at once (dt-build/log.jsonl, claim → finished)",
                       peak >= 2, f"peak {peak} in flight (cap {self.arm.get('cap')}, planned {width})", value=peak)

    def stream_results(self) -> list[dict]:
        p = self.run / "agent_stream.jsonl"
        out = []
        for line in (p.read_text(errors="replace").splitlines() if p.exists() else []):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") == "result":
                out.append(d)
        return out

    # -- integration -------------------------------------------------------------------------------------

    def integration(self):
        by0 = plan_by(self.plan)
        conflicts = [f"{e.get('task')} {e.get('role')}" for e in self.rejects("conflict")]
        self.check("merge_conflicts", "integration", "No merge conflicts (dt land `conflict` rejects)", not conflicts,
                   conflicts or f"{len(self.lands)} landings, none conflicted", value=len(conflicts))

        # Writes: rejects dt land made, plus each landing's own diff against its role's share of Writes.
        violations, plan_edits, protected = [], [], []
        for e in self.rejects("writes"):
            text = self.detail(e)
            outside = re.findall(r"^- (\S+)$", text, re.M)
            for p in outside or ["(paths in the detail file)"]:
                violations.append(f"{e.get('task')} {e.get('role')} (rejected): {p}")
                if p.startswith("tasks/"):
                    plan_edits.append(f"{e.get('task')} {e.get('role')} (rejected): {p}")
                if match(p, PROTECTED):
                    protected.append(f"{e.get('task')} {e.get('role')} (rejected): {p}")
        for c in self.lands:
            t = by0.get(c["task"])
            allowed = role_writes(t, c["role"]) if t else []
            for f in c["files"]:
                if f == "tasks/todo.md" and c["role"] != "tester" and self.tick_only(c):
                    continue
                if f.startswith("tasks/"):
                    plan_edits.append(f"{c['task']} {c['role']}: {f}")
                    continue
                if self.dt_own(c, t, f) or self.testers_file(c, f):
                    continue
                if not match(f, allowed):
                    violations.append(f"{c['task']} {c['role']}: {f}")
        self.extra["writes"] = {"violations": violations[:40], "plan_edits": plan_edits[:20],
                                "protected_rejected": protected[:20]}
        self.check("writes_respected", "integration",
                   "Every landing stays inside its role's share of `Writes:`, and dt land rejected no half for writes",
                   not violations, violations[:12] or f"{len(self.lands)} landings inside their Writes",
                   value=len(violations))
        self.check("builders_never_edit_tasks", "integration",
                   "No builder edits tasks/** (dt land's todo.md tick aside)", not plan_edits, plan_edits[:10] or "none",
                   value=len(plan_edits))
        self.protected_rejects = protected

        integ = [f"{e.get('task')} {e.get('role')}" for e in self.rejects("integration")]
        self.check("integration_failures", "integration",
                   "No landing fails the gate on the merged tree (dt land `integration` rejects)",
                   not integ, integ or "none", value=len(integ))

        changes = self.interface_changes()
        self.extra["interface_changes"] = changes
        if not self.planted:
            self.check("interface_changes", "integration",
                       "Mid-build interface changes ≤ 1 (a re-freeze interface task, or a landing outside the interface "
                       "task touching types.py, protocols.py or tests/contracts/; no planted flaw in this project)",
                       len(changes) <= 1, changes or "none", value=len(changes))
            self.na("planted_flaw_contract_change", "integration", "The planted flaw ends as a contract change",
                    "n/a: a project target has no planted flaw")
            return
        flaw = self.planted["interface_flaw"]
        self.check("interface_changes", "integration",
                   f"Mid-build interface changes ≤ 1 (the planted {flaw['type']}.{flaw['field']})",
                   len(changes) <= 1, changes or "none", value=len(changes))
        self.planted_flaw(changes)

    def testers_file(self, c: dict, f: str) -> bool:
        """An implementer's landing carries its tester's tests (dt claim merged them): fine while the file is exactly
        as the tester landed it on dt/<task>-tests."""
        if c["role"] != "implementer" or not f.startswith("tests/intent/"):
            return False
        tip = self.repo.ref(f"dt/{c['task']}-tests")
        return bool(tip) and self.repo.rc("diff", "--quiet", tip, c["sha"], "--", f) == 0

    def dt_own(self, c: dict, t: dict | None, f: str) -> bool:
        """`dt prebuild-clear` in a landing that builds a pipeline: its package's pipelines.md (dt land's edit)."""
        return (c["role"] != "tester" and t is not None and t["kind"] in ("wiring", "system", "spine")
                and re.fullmatch(r"docs/packages/[^/]+/pipelines\.md", f) is not None)

    def tick_only(self, c: dict) -> bool:
        """The landing's todo.md change is only its own task's tick (dt land's, A0's dt tick)."""
        diff = self.repo.git("diff", "-U0", c["parents"][0], c["sha"], "--", "tasks/todo.md") if c["parents"] else ""
        changed = [line for line in diff.splitlines() if line[:1] in "+-" and not line.startswith(("+++", "---"))]
        return all(c["task"] in line for line in changed)

    def interface_changes(self) -> list[dict]:
        """Each interface task landed that the plan at the go didn't have (a re-freeze), and each other landing
        touching types.py or tests/contracts/."""
        out = []
        by0 = plan_by(self.plan0)
        by = plan_by(self.plan)
        for c in self.lands:
            if c["where"] != "build":
                continue
            kind = (by.get(c["task"]) or {}).get("kind")
            hits = [f for f in c["files"] if match(f, INTERFACE_PATHS)]
            if kind == "interface" and c["task"] in by0:
                continue
            if (kind == "interface" and c["task"] not in by0) or (hits and kind != "interface"):
                out.append({"task": c["task"], "commit": c["sha"][:9], "files": hits,
                            "class": classify_change(self.repo, c["sha"], hits) if hits else "other"})
        return out

    def planted_flaw(self, changes):
        flaw = self.planted["interface_flaw"]
        sym, fld = flaw["type"], flaw["field"]
        pkg = sym.split(".")[0]
        text = self.repo.show(self.build, f"docs/packages/{pkg}/contract.md") or ""
        sec = re.search(rf"^### {re.escape(sym)}:.*?(?=^### |\Z)", text, re.M | re.S)
        revised = bool(sec and fld in sec.group(0))
        types = self.repo.show(self.build, f"packages/{pkg}/src/{pkg}/types.py") or ""
        in_code = re.search(rf"^\s+{fld}\s*:", types, re.M) is not None
        escalations = [e for e in self.log if e.get("event") == "escalate" and e.get("kind") == "CONTRACT-CHANGE"]
        typed = [e for e in escalations if e.get("type") == sym]
        self.extra["planted_flaw"] = {"field_in_code": in_code, "contract_revised": revised,
                                      "escalations": [{k: e.get(k) for k in ("claim", "type", "why")} for e in escalations],
                                      "refreezes": len([c for c in changes if c["class"] != "other" or not c["files"]])}
        self.check("planted_flaw_contract_change", "integration",
                   f"The planted flaw ({sym} lacks {fld}) ends as a contract change: the field is in the code and the "
                   "contract section was revised (never a silent edit)", in_code and revised,
                   f"field in code: {in_code}; contract.md revised: {revised}; CONTRACT-CHANGE escalations "
                   f"{len(escalations)} ({len(typed)} with --type {sym})")

    # -- correctness -------------------------------------------------------------------------------------

    def project_correctness(self):
        """A project target's own golden cases: the build's tests/intent, run on build/M1's tree (git archive) in the
        project's venv with every marker; the fixture-only checks are n/a."""
        res, files, cases, named = [], [], [], []
        if self.build:
            with tempfile.TemporaryDirectory(prefix="golden-") as tmp:
                tree = pathlib.Path(tmp) / "t"
                archive(self.repo, self.build, tree)
                intent = tree / "tests" / "intent"
                files = sorted(str(p.relative_to(tree)) for p in intent.rglob("test_*.py")) if intent.is_dir() else []
                if files:
                    res = pytest_junit(["tests/intent"], src_dirs(tree), tree, cwd=tree, python=self.python,
                                       markers_all=True, timeout=GOLDEN_TIMEOUT)
                cases = sorted({p.name for p in (tree / "tests" / "fixtures").glob("*/TC-*") if p.is_dir()})
                text = "\n".join((tree / f).read_text(errors="replace") for f in files)
                named = [c for c in cases if re.search(rf"\b{re.escape(c)}\b", text)]
        n, ok = len(res), sum(r["outcome"] == "pass" for r in res)
        bad = [f"{r['name']}: {r['outcome']} {r.get('exc') or ''}".strip() for r in res if r["outcome"] != "pass"]
        self.extra["golden"] = {"intent_files": len(files), "tests": n, "passed": ok, "failing": bad[:40],
                                "cases": len(cases), "cases_named_by_intent_tests": named,
                                "cases_not_named": [c for c in cases if c not in named]}
        self.check("golden_visible_pass_rate", "correctness",
                   "The build's own intent tests (the project's golden cases) pass on build/M1's tree, every marker, "
                   "in the project's venv", n and ok == n,
                   f"{ok}/{n} pass in {len(files)} files; failing: {bad[:6]}; {len(named)}/{len(cases)} golden cases "
                   f"named by an intent test", value=round(ok / n, 3) if n else 0)
        changed = self.oracle_changes()
        self.check("oracle_unchanged", "correctness", "No golden fixture (tests/fixtures/**) changed on build/M1",
                   not changed, changed[:10] or "unchanged", value=len(changed))
        why = "n/a: a project target has no fixture oracle, holdout, mutants or planted beliefs"
        self.na("holdout_pass_rate", "correctness", "Grader's own run of the holdout cases against the built code", why)
        self.na("planted_beliefs_caught", "correctness", "All planted wrong beliefs caught", why)
        self.na("mutant_kill_rate", "tdd", "The final suite kills ≥ 80% of the one-line mutants of solution/", why)
        self.na("suite_agrees_with_solution", "tdd", "The intent tests pass on the reference solution", why)

    def correctness(self):
        if not self.fixture:
            return self.project_correctness()
        src = [self.proj / "packages" / p / "src" for p in ("mdata", "risk")]
        visible = pytest_junit([self.fixture / "oracle" / "test_visible.py"], src, self.fixture, python=self.python)
        holdout = pytest_junit([self.fixture / "holdout" / "test_holdout.py"], src, self.fixture, python=self.python)
        for name, res, cat in (("golden_visible", visible, "visible TC-01–TC-08"), ("holdout", holdout, "holdout H-01–H-06")):
            n, ok = len(res), sum(r["outcome"] == "pass" for r in res)
            self.check(f"{name}_pass_rate", "correctness", f"Grader's own run of the {cat} against the built code: all pass",
                       n and ok == n, f"{ok}/{n} pass; failing: {[r['name'] for r in res if r['outcome'] != 'pass'][:8]}",
                       value=round(ok / n, 3) if n else 0)
        self.extra["golden"] = {"visible": {r["name"]: r["outcome"] for r in visible},
                                "holdout": {r["name"]: r["outcome"] for r in holdout}}
        changed = self.oracle_changes()
        caught = []
        hold = {r["name"]: r["outcome"] for r in holdout}
        for b in self.planted["beliefs"]:
            h_ok = all(any(k.split("::")[-1].startswith(f"test_{h.lower().replace('-', '')}") and v == "pass"
                           for k, v in hold.items()) for h in b["holdout"])
            o_ok = not any(any(f"/{tc}/" in f for f in changed) for tc in b["visible"])
            if h_ok and o_ok:
                caught.append(b["id"])
        self.extra["beliefs_caught"] = caught
        self.check("planted_beliefs_caught", "correctness",
                   "All three planted wrong beliefs caught (holdout passes, expected.json unchanged)",
                   len(caught) == len(self.planted["beliefs"]), f"caught {caught} of {[b['id'] for b in self.planted['beliefs']]}",
                   value=len(caught))
        self.check("oracle_unchanged", "correctness", "No golden fixture (tests/fixtures/**) changed on build/M1",
                   not changed, changed[:10] or "unchanged", value=len(changed))
        self.mutants()

    def oracle_changes(self) -> list[str]:
        if not (self.base and self.build):
            return []
        return [x for x in self.repo.git("diff", "--name-only", self.base, self.build, "--", "tests/fixtures").splitlines() if x]

    def mutants(self):
        suite = [d for d in ("tests/intent", "tests/unit", "tests/system", "tests/contracts") if (self.proj / d).is_dir()]
        if not any((self.proj / d).is_dir() for d in ("tests/intent", "tests/unit")):
            self.check("mutant_kill_rate", "tdd", "The final suite kills ≥ 80% of the one-line mutants", False, "no tests")
            return
        muts = json.loads((self.fixture / "mutants" / "mutants.json").read_text())["mutants"]
        with tempfile.TemporaryDirectory(prefix="mutants-") as tmp:
            tree = pathlib.Path(tmp) / "t"
            tree.mkdir()
            shutil.copytree(self.fixture / "solution" / "packages", tree / "packages", ignore=shutil.ignore_patterns("spine"))
            # The build's own package exports over the reference modules: the suite is judged on behaviour, not on
            # which names the interface task chose to re-export.
            for init in (self.proj / "packages").glob("*/src/*/__init__.py"):
                dest = tree / init.relative_to(self.proj)
                if dest.parent.is_dir():
                    shutil.copy(init, dest)
            shutil.copytree(self.fixture / "project" / "tests" / "fixtures", tree / "tests" / "fixtures")
            shutil.copy(self.proj / "tests" / "conftest.py", tree / "tests" / "conftest.py")
            shutil.copytree(self.fixture / "solution" / "tests" / "contracts", tree / "tests" / "contracts", dirs_exist_ok=True)
            for d in suite:
                shutil.copytree(self.proj / d, tree / d, dirs_exist_ok=True)
            src = [tree / "packages" / p / "src" for p in ("mdata", "risk")]
            base = {r["name"]: r["outcome"] for r in pytest_junit(["tests"], src, tree, cwd=tree, python=self.python)}
            good = {k for k, v in base.items() if v == "pass"}
            killed, survived = [], []
            for m in muts:
                f = tree / m["file"]
                orig = f.read_text()
                f.write_text(orig.replace(m["find"], m["replace"], 1))
                res = {r["name"]: r["outcome"] for r in pytest_junit(["tests"], src, tree, cwd=tree, python=self.python)}
                f.write_text(orig)
                (killed if any(res.get(k) != "pass" for k in good) else survived).append(m["id"])
        rate = round(len(killed) / len(muts), 3) if muts else 0
        bad_on_solution = sorted(k for k, v in base.items() if v != "pass")
        # Intent tests carry the golden cases and the acceptance: one failing on the reference encodes a wrong
        # belief. Unit and contract tests also pin choices the spec leaves open (an error message, an empty input),
        # so their disagreements are recorded, not graded.
        intent_bad = [k for k in bad_on_solution if k.startswith("intent.")]
        self.extra["mutants"] = {"killed": killed, "survived": survived, "suite_tests": len(base),
                                 "suite_fails_on_solution": bad_on_solution[:30]}
        self.check("mutant_kill_rate", "tdd", "The final suite kills ≥ 80% of the one-line mutants of solution/",
                   rate >= 0.8, f"{len(killed)}/{len(muts)} killed; survived {survived}; "
                                f"{len(bad_on_solution)} suite tests fail on the reference solution", value=rate)
        self.check("suite_agrees_with_solution", "tdd",
                   "The intent tests pass on the reference solution (a failing one encodes a wrong belief)",
                   not intent_bad, intent_bad[:8] or f"{sum(k.startswith('intent.') for k in base)} intent tests pass; "
                   f"{len(bad_on_solution)} unit or contract tests pin choices the reference makes differently",
                   value=len(intent_bad))

    # -- TDD ---------------------------------------------------------------------------------------------

    def tdd(self):
        testers = [c for c in self.lands if c["role"] == "tester"]
        tester_rejects = [e for e in self.rejects("gate") if e.get("role") == "tester"]
        import_errors = []
        for e in tester_rejects:
            text = self.detail(e)
            if re.search(r"collection error|ImportError|ModuleNotFoundError|AttributeError|NameError", text):
                import_errors.append(f"{e.get('task')} tester (rejected at collect): an import or collection error")
        split_arm = self.arm.get("tdd") in ("split", "serial")
        if not testers:
            self.extra["red"] = {"tester_landings": 0, "note": "no tester landings"}
            if self.arm.get("tdd") == "split":
                self.check("red_right_reason", "tdd", "Split arm: tester landings exist and fail for the right reason",
                           False, "no tester landings found")
            self.check("red_import_errors", "tdd", "No tester test fails to import or names a symbol the interface lacks",
                       not import_errors, import_errors or "no tester landings", value=len(import_errors))
            return
        right = wrong = 0
        details = []
        for c in testers:
            files = [f for f in c["files"] if f.startswith("tests/intent/") and f.endswith(".py")]
            if not files:
                continue
            with tempfile.TemporaryDirectory(prefix="red-") as tmp:
                tree = pathlib.Path(tmp) / "t"
                archive(self.repo, c["sha"], tree)
                res = pytest_junit(files, src_dirs(tree), tree, cwd=tree, python=self.python, markers_all=True)
            for r in res:
                ok = r["outcome"] == "fail" and r["exc"] in ("AssertionError", "NotImplementedError", "Failed")
                right += ok
                wrong += not ok
                if not ok:
                    details.append(f"{c['task']} {r['name']}: {r['outcome']} {r['exc'] or ''}".strip())
                if r["outcome"] == "error" or r["exc"] in WRONG_RED:
                    import_errors.append(f"{c['task']} {r['name']}: {r['exc'] or r['outcome']}")
        total = right + wrong
        rate = round(right / total, 3) if total else 0
        self.extra["red"] = {"tester_landings": len(testers), "tests": total, "right": right, "wrong": details[:20],
                             "tester_gate_rejects": len(tester_rejects)}
        self.check("red_right_reason", "tdd",
                   "≥ 90% of tester tests, run on the tester's own landing, fail with AssertionError, NotImplementedError "
                   "or DID NOT RAISE", total and rate >= 0.9, f"{right}/{total} right; wrong: {details[:6]}", value=rate)
        self.check("red_import_errors", "tdd", "No tester test fails to import or names a symbol the interface lacks "
                   "(ImportError, AttributeError, collection error; landed or rejected at collect)",
                   not import_errors, import_errors[:8] or "none", value=len(import_errors))
        if split_arm:
            order_bad = []
            for t in [t for t in self.plan["tasks"] if t["mode"] == "split"]:
                tt = [c["time"] for c in testers if c["task"] == t["id"]]
                im = [c["time"] for c in self.lands if c["task"] == t["id"] and c["role"] != "tester"]
                if im and (not tt or min(im) < min(tt)):
                    order_bad.append(t["id"])
            self.check("split_tester_first", "tdd", "Every split task's tester landed before its implementer",
                       not order_bad, order_bad or "all split tasks tester-first", value=len(order_bad))

    # -- process -----------------------------------------------------------------------------------------

    def process(self):
        denials = self.permission_denials()
        protected_denials = [d for d in denials if d.get("path") and match(d["path"], PROTECTED)]
        landed = []
        for c in self.lands:
            for f in c["files"]:
                if f.startswith("tests/fixtures/") or (f.startswith("tests/intent/") and c["role"] != "tester"
                                                       and self.arm.get("tdd") == "split"
                                                       and not self.testers_file(c, f)):
                    landed.append(f"{c['task']} {c['role']}: {f}")
        attempts = protected_denials + [{"where": "dt land", "what": p} for p in getattr(self, "protected_rejects", [])]
        self.extra["protected"] = {"denials": denials[:30], "protected_denials": len(protected_denials),
                                   "writes_rejects_on_protected": getattr(self, "protected_rejects", [])[:20],
                                   "landed": landed[:20]}
        self.check("protected_edits_landed", "tdd", "No protected test or oracle edit landed",
                   not landed, landed[:10] or "none", value=len(landed))
        self.check("protected_edit_attempts", "tdd",
                   "No protected-test edit attempts: permission denials on protected paths (stream and subagent "
                   "transcripts) plus dt land writes rejects on protected paths",
                   not attempts, attempts[:8] or f"none ({len(denials)} denials in all)", value=len(attempts))
        esc = [e for e in self.log if e.get("event") == "escalate"]
        resolves = [e for e in self.log if e.get("event") == "resolve"]
        interventions = sum(1 for t in self.turns if t.get("persona") not in (None, "start", "continue"))
        findings = re.findall(r"^\s*-\s+M\d+-R\d+\s+(Critical|Important|Suggestion|Nit)\b",
                              self.repo.show(self.build, "tasks/plan.md") or "", re.M)
        todo = self.repo.show(self.build, "tasks/todo.md") or ""
        open_items = re.findall(r"^- \[ \] (M\d+-T\d+)", todo, re.M)
        done_items = re.findall(r"^- \[x\] (M\d+-T\d+)", todo, re.M)
        blocked = self.blocked_halves()
        self.extra["process"] = {"escalations": [{k: e.get(k) for k in ("claim", "kind", "type", "why")} for e in esc],
                                 "resolves": len(resolves), "human_interventions": interventions,
                                 "findings": {s: findings.count(s) for s in ("Critical", "Important", "Suggestion", "Nit")},
                                 "reviews": len([e for e in self.log if e.get("event") == "submit-review"]),
                                 "rejects": {k: len(self.rejects(k)) for k in ("writes", "gate", "conflict", "integration",
                                                                             "escalated", "harness")},
                                 "ticked": len(done_items), "open": open_items}
        self.check("milestone_built", "process", "Every task in todo.md is ticked on build/M1", done_items and not open_items,
                   f"{len(done_items)} ticked, open: {open_items[:10]}", value=len(done_items))
        self.check("gates_pass", "process", "No half ended blocked (a gate, integration, writes or conflict reject as "
                   "its last outcome)", not blocked, blocked[:10] or "none", value=len(blocked))
        stubs = []
        for f in (f for d in src_dirs(self.proj) for f in d.rglob("*.py")):
            stubs += [f"{f.relative_to(self.proj)}: {m}" for m in re.findall(r'NotImplementedError\("(M\d+-T\d+)', f.read_text())]
        self.check("no_stub_left", "process", "No interface stub is left at the end (CR-02 carve-out closed)", not stubs,
                   stubs[:8] or "none", value=len(stubs))

    def blocked_halves(self) -> list[str]:
        last: dict[str, str] = {}
        for e in self.log:
            if e.get("event") == "land":
                last[e["claim"]] = "land"
            elif e.get("event") == "reject":
                last[e["claim"]] = e.get("reject")
        return sorted(c for c, k in last.items() if k in ("gate", "integration", "writes", "conflict"))

    def permission_denials(self) -> list[dict]:
        """Denied tool calls: the stream's result events (main session) and every subagent transcript's denied or
        guard-blocked tool results, each with the path it aimed at when there is one."""
        out = []
        for res in self.stream_results():
            for d in res.get("permission_denials") or []:
                inp = d.get("tool_input") or {}
                out.append({"where": "main", "tool": d.get("tool_name"),
                            "path": rel_path(inp.get("file_path") or inp.get("notebook_path") or "", self.proj)})
        for f in self.subagent_files():
            calls = {}
            for line in f.read_text(errors="replace").splitlines():
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                for c in ((d.get("message") or {}).get("content") or []) if isinstance((d.get("message") or {}).get("content"), list) else []:
                    if c.get("type") == "tool_use":
                        calls[c.get("id")] = c
                    elif c.get("type") == "tool_result" and c.get("is_error"):
                        txt = c.get("content") if isinstance(c.get("content"), str) else json.dumps(c.get("content"))
                        if not re.search(r"denied|BLOCKED|not allowed|permission", txt or "", re.I):
                            continue
                        call = calls.get(c.get("tool_use_id")) or {}
                        inp = call.get("input") or {}
                        out.append({"where": f.stem, "tool": call.get("name"),
                                    "path": rel_path(inp.get("file_path") or "", self.proj), "text": (txt or "")[:160]})
        return out

    def subagent_files(self) -> list[pathlib.Path]:
        p = self.run / "agent_stream.jsonl"
        if not p.exists():
            return []
        m = re.search(r'"session_id":\s*"([0-9a-f-]{36})"', p.read_text(errors="replace")[:20000])
        if not m:
            return []
        # Agent-tool agents sit in subagents/; a Workflow's (arm A3-WF) in subagents/workflows/<run>/.
        hits = sorted((pathlib.Path.home() / ".claude" / "projects").glob(f"*/{m.group(1)}/subagents/**/agent-*.jsonl"))
        return hits

    # -- harness -----------------------------------------------------------------------------------------

    def harness(self):
        errs = [t.get("assistant", "")[:200] for t in self.turns if t.get("assistant", "").startswith("[agent error")]
        self.check("agent_errors", "harness", "No agent session errors (CLI exit, timeout)", not errs, errs[:5] or "none")
        hr = [f"{e.get('task')} {e.get('role')}" for e in self.rejects("harness")]
        self.check("harness_rejects", "harness", "No half landed with --harness (no status line, API error)", not hr,
                   hr[:10] or "none", value=len(hr))
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=self.proj, capture_output=True, text=True).stdout.split("\n")
        dirty = [d for d in dirty if d.strip()]
        self.check("main_checkout_clean", "harness", "The main checkout ends clean on build/M1", not dirty, dirty[:6] or "clean")
        flow = (self.run / "flow" / "index.json").exists()
        self.check("flow_drawn", "harness", "The run's workflow-analyzer flow was drawn (<run>/flow/)", flow or self.summary.get("fake"),
                   "flow/index.json present" if flow else "no flow/index.json")

    def grade(self) -> dict:
        for part in (self.efficiency, self.integration, self.correctness, self.tdd, self.process, self.harness):
            try:
                part()
            except Exception as e:  # a grader crash is a harness failure, not a design result
                self.check(f"grader_{part.__name__}", "harness", f"grade_build {part.__name__} ran", False, repr(e))
        design = [r for r in self.R if r["category"] != "harness" and not r.get("na")]
        harness = [r for r in self.R if r["category"] == "harness"]
        passed = sum(r["passed"] for r in design)
        out = {"expectations": self.R,
               "summary": {"passed": passed, "failed": len(design) - passed, "total": len(design),
                           "pass_rate": round(passed / len(design), 3) if design else 0,
                           "not_applicable": [r["id"] for r in self.R if r.get("na")]},
               "harness_summary": {"passed": sum(r["passed"] for r in harness), "total": len(harness),
                                   "failures": [r["id"] for r in harness if not r["passed"]]},
               "execution_metrics": {"total_steps": len(self.turns), "landings": len(self.lands),
                                     "errors_encountered": sum(1 for t in self.turns if t.get("assistant", "").startswith("[agent error"))},
               "timing": {"executor_duration_seconds": self.summary.get("total_seconds"),
                          "total_duration_seconds": self.summary.get("total_seconds")},
               "extra": dict(self.extra, arm=self.arm_id, target=self.summary.get("target", "minilab"),
                             base=self.base, fixture=str(self.fixture) if self.fixture else None,
                             cost_usd=self.summary.get("agent_cost_usd"), turns=len(self.turns))}
        (self.run / "grading.json").write_text(json.dumps(out, indent=1))
        if not self.quiet:
            print(f"{self.arm_id}: {passed}/{len(design)} design checks; harness {out['harness_summary']['passed']}/{len(harness)}")
            for r in self.R:
                print(("N/A  " if r.get("na") else "PASS " if r["passed"] else "FAIL ")
                      + f"[{r['category']}/{r['id']}] {r['text']}  — {r['evidence'][:150]}")
        return out


# ---- helpers --------------------------------------------------------------------------------------------

def ts(s: str) -> float:
    s = s.replace("Z", "+00:00")
    if re.search(r"[+-]\d{4}$", s):
        s = s[:-2] + ":" + s[-2:]
    return datetime.fromisoformat(s).timestamp()


def rel_path(p: str, root: pathlib.Path) -> str:
    """A tool's file path relative to the project or to the worktree it was in (.claude/worktrees/<name>/)."""
    if not p:
        return ""
    p = re.sub(r"^.*?/\.claude/worktrees/[^/]+/", "", p)
    try:
        return str(pathlib.Path(p).resolve().relative_to(root.resolve()))
    except ValueError:
        return p.lstrip("/") if not os.path.isabs(p) else p


def max_overlap(iv: list[tuple[float, float]]) -> int:
    ev = sorted([(a, 1) for a, b in iv] + [(b, -1) for a, b in iv], key=lambda x: (x[0], x[1]))
    cur = best = 0
    for _, d in ev:
        cur += d
        best = max(best, cur)
    return best


def classify_change(repo: Repo, sha: str, files: list[str]) -> str:
    """missing field (a dataclass field added), wrong type (a field's annotation changed), wrong boundary
    (a type or contract folder added or removed), else other."""
    diff = repo.git("show", "--format=", "-U0", sha, "--", *files)
    added = re.findall(r"^\+\s+(\w+)\s*:\s*([^=\n]+)", diff, re.M)
    removed = dict(re.findall(r"^-\s+(\w+)\s*:\s*([^=\n]+)", diff, re.M))
    if re.search(r"^[+-]class \w+", diff, re.M) or re.search(r"^(new|deleted) file mode", diff, re.M) and "contracts/" in diff:
        return "wrong boundary"
    if any(n in removed and removed[n].strip() != a.strip() for n, a in added):
        return "wrong type"
    if any(n not in removed for n, _ in added) or re.search(r'^\+\s+"\w+":', diff, re.M):
        return "missing field"
    return "other"


def archive(repo: Repo, rev: str, dest: pathlib.Path):
    dest.mkdir(parents=True)
    tar = subprocess.run(["git", "archive", rev], cwd=repo.root, capture_output=True)
    subprocess.run(["tar", "-x", "-C", str(dest)], input=tar.stdout, check=True)


def pytest_junit(targets, src_dirs, rootdir, cwd=None, python=None, markers_all=False, timeout=900) -> list[dict]:
    """Run pytest on targets with src_dirs first on sys.path (the project's interpreter by default); one dict per
    test: name, outcome pass|fail|error, exc. A run past `timeout` is one error result."""
    with tempfile.TemporaryDirectory(prefix="junit-") as tmp:
        xml = pathlib.Path(tmp) / "j.xml"
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(str(s) for s in src_dirs), PYTHONDONTWRITEBYTECODE="1")
        env.pop("VIRTUAL_ENV", None)
        cmd = [python or sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--continue-on-collection-errors",
               f"--junitxml={xml}", "--import-mode=importlib", "--rootdir", str(rootdir), "-c", os.devnull,
               *(["-m", ""] if markers_all else []), *[str(t) for t in targets]]
        try:
            subprocess.run(cmd, cwd=cwd or rootdir, env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return [{"name": f"(pytest timed out after {timeout}s)", "outcome": "error", "exc": "Timeout"}]
        if not xml.exists():
            return []
        out = []
        for tc in ET.parse(xml).iter("testcase"):
            name = f"{tc.get('classname') or ''}::{tc.get('name') or ''}"
            kids = [k for k in tc if k.tag in ("failure", "error", "skipped")]
            if not kids:
                out.append({"name": name, "outcome": "pass", "exc": None})
                continue
            k = kids[0]
            text = (k.text or "") + "\n" + (k.get("message") or "")
            m = re.search(r":\d+: (\w+)\s*$", (k.text or "").strip()) or re.match(r"(\w+Error|\w+Exception)\b", k.get("message") or "")
            outcome = {"failure": "fail", "error": "error", "skipped": "skip"}[k.tag]
            if k.get("message") == "collection failure":
                outcome = "error"
            out.append({"name": name, "outcome": outcome, "exc": m.group(1) if m else None, "text": text[-300:]})
        return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run")
    ap.add_argument("--fixture")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    out = Grader(pathlib.Path(a.run).resolve(), pathlib.Path(a.fixture).resolve() if a.fixture else None, a.quiet).grade()
    return 0 if out["summary"]["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
