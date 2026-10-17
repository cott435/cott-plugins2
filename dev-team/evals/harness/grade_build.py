#!/usr/bin/env python3
"""Grade one build-eval run (interface-first-design.md §9.2): writes <run>/grading.json in the planning
grader's shape (expectations, summary, execution_metrics, timing, extra), so runviz and package read it
unchanged.

Every graph fact is recomputed here from the plan text and git, never taken from `dt` (a dt bug can't grade
itself). Each expectation carries a `category`: efficiency, integration, correctness, tdd, process or
harness. `harness` checks (a worktree, merge or gate the infrastructure lost, an agent error, a flow that
didn't draw) are summarised apart in `harness_summary` and never count in `summary`.

Run layout (build_driver.py writes it; dryrun_build.py fakes it): <run>/project (git, one commit per turn
plus the agents' own commits and worktree-* branches), turns.json, summary.json, agent_stream.jsonl,
permission_prompts.jsonl, flow/index.json (workflow-analyzer units, optional).

Commit convention the orchestrator prompts ask for, and this grader reads:
  `M1-T05 tester: …` / `M1-T05 implementer: …` / `M1-T05 solo: …`   builder commits (one task each)
  `M1-T22 interface: …`                                             an interface or contract-change task
  `dt: tick M1-T05`, `merge M1-T05: worktree-…`, `turn N`           orchestrator, merge step, driver

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
ROLE = re.compile(r"^(M\d+-T\d+)\b[^:\n]*?\b(tester|implementer|solo|interface)\b", re.I)
SHARED = re.compile(r"(^|/)(__init__\.py|types\.py)$")
INTERFACE_PATHS = ["packages/*/src/*/types.py", "tests/contracts/*"]
HARNESS_PATHS = [".dt/*", ".claude/.check_*", ".claude/.stop_attempts_*"]


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
                                "exit": "exit" in title.lower()})
    graph = []
    gm = re.search(r"^## Dependency graph\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    for line in (gm.group(1).splitlines() if gm else []):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and TASK.search(cells[0]) and TASK.search(cells[1]):
            graph.append({"src": TASK.search(cells[0]).group(0), "dst": TASK.search(cells[1]).group(0),
                          "kind": cells[2], "mitigated_by": "" if cells[3].lower().startswith("none") else cells[3]})
    return {"tasks": tasks, "checkpoints": checkpoints, "graph": graph}


def derive_kind(t: dict) -> str:
    """A plan without `**Kind:**` (today's spine style): contract → interface, a system spine → system,
    a whole-pipeline step → spine, a step of a pipeline → thicken."""
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


def dispatch_rounds(plan: dict, arm: dict) -> list[list[str]]:
    """What the arm dispatches together: serial = one task per round in plan order; parallel with a
    `Kind`-less plan = today's `Parallel:` groups (consecutive tasks sharing a G label) and singletons;
    otherwise the dependency waves."""
    tasks = plan["tasks"]
    if arm.get("dispatch") == "serial":
        return [[t["id"]] for t in tasks]
    if any(t["parallel"] for t in tasks):
        rounds, cur, label = [], [], None
        for t in tasks:
            g = t["parallel"] or None
            if cur and (g is None or g != label):
                rounds.append(cur)
                cur = []
            cur.append(t["id"])
            label = g
        return rounds + ([cur] if cur else [])
    return waves(tasks)


def graph_facts(plan: dict, arm: dict | None = None) -> dict:
    tasks = plan["tasks"]
    w = waves(tasks)
    cp, n_cp = critical_path(tasks)
    cpw, n_cpw = critical_path(tasks, lambda t: SIZE_W.get(t["size"], 2))
    rounds = dispatch_rounds(plan, arm or {"dispatch": "parallel"})
    split = [t["id"] for t in tasks if t["mode"] == "split"]
    # Interface-first: a split task's tester half needs only the interface task, so wave 1 is the tasks
    # ready after it plus every split task's tester.
    iface = [t["id"] for t in tasks if t["kind"] == "interface"]
    ready_after_iface = [t["id"] for t in tasks if t["id"] not in iface and set(t["depends"]) <= set(iface)]
    testers_early = [i for i in split if i not in ready_after_iface] if iface else []
    return {"tasks": len(tasks), "critical_path": cp, "cp_tasks": n_cp, "cp_weighted": n_cpw, "cp_weighted_path": cpw,
            "waves": w, "width": max((len(x) for x in w), default=0), "parallelism": round(len(tasks) / max(n_cp, 1), 2),
            "dispatch_rounds": rounds, "dispatch_width": max((len(r) for r in rounds), default=0),
            "split_tasks": split, "ready_after_interface": ready_after_iface,
            "wave1_agents": len(ready_after_iface) + (len(testers_early) if iface else 0)}


def plan_by(plan: dict) -> dict:
    return {t["id"]: t for t in plan["tasks"]}


def match(path: str, globs: list[str]) -> bool:
    for g in globs:
        g = g.strip("/")
        if path == g or fnmatch.fnmatch(path, g) or (g.endswith("/**") and path.startswith(g[:-3] + "/")) \
                or (g.endswith("/") and path.startswith(g)):
            return True
    return False


# ---- git ------------------------------------------------------------------------------------------------

class Repo:
    def __init__(self, root: pathlib.Path):
        self.root = root

    def git(self, *a, check=False) -> str:
        r = subprocess.run(["git", *a], cwd=self.root, capture_output=True, text=True)
        if check and r.returncode:
            raise RuntimeError(f"git {' '.join(a)}: {r.stderr.strip()}")
        return r.stdout

    def rc(self, *a) -> int:
        return subprocess.run(["git", *a], cwd=self.root, capture_output=True, text=True).returncode

    def commits(self, rev_range: str = "--all") -> list[dict]:
        """Every commit (oldest first) with subject, parents, time and changed files (vs first parent)."""
        out = self.git("log", "--reverse", "--topo-order", "--format=%x1e%H%x1f%P%x1f%ct%x1f%s", "--name-only",
                       "-m", "--first-parent" if rev_range == "first-parent" else rev_range)
        seen, res = set(), []
        for rec in out.split("\x1e")[1:]:
            head, *files = rec.strip("\n").split("\n")
            sha, parents, ts, subject = head.split("\x1f")
            if sha in seen:
                continue
            seen.add(sha)
            res.append({"sha": sha, "parents": parents.split(), "time": int(ts), "subject": subject,
                        "files": [f for f in files if f.strip()]})
        return res

    def first_parent(self) -> list[str]:
        return self.git("rev-list", "--first-parent", "--reverse", "HEAD").split()

    def show(self, rev: str, path: str) -> str | None:
        r = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=self.root, capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None

    def branches(self, pattern="worktree-*") -> dict[str, str]:
        out = self.git("for-each-ref", "--format=%(refname:short) %(objectname)", f"refs/heads/{pattern}")
        return dict(line.split() for line in out.splitlines() if line.strip())

    def is_ancestor(self, a: str, b: str) -> bool:
        return self.rc("merge-base", "--is-ancestor", a, b) == 0


def builder_commits(repo: Repo, all_commits: list[dict]) -> list[dict]:
    """Non-merge commits whose subject starts with a task id and names a builder role (or no role)."""
    out = []
    for c in all_commits:
        if len(c["parents"]) > 1:
            continue
        s = c["subject"]
        if not re.match(r"^M\d+-T\d+\b", s) or re.search(r"\b(tick|merge)\b", s.split(":")[0], re.I):
            continue
        m = ROLE.match(s)
        role = m.group(2).lower() if m else ""
        if not role:
            role = "tester" if c["files"] and all(f.startswith("tests/intent/") for f in c["files"]) else "solo"
        out.append(dict(c, task=TASK.match(s).group(0), role=role))
    return out


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
        self.fixture = fixture or (HERE / tcfg["fixture"] if tcfg.get("fixture") else FIXTURES / "minilab")
        self.planted = json.loads((self.fixture / "planted.json").read_text())
        self.R, self.extra = [], {}
        self.base = self.repo.first_parent()[0] if self.repo.first_parent() else None
        self.plan0 = parse_plan(self.repo.show(self.base, "tasks/plan.md") or "") if self.base else {"tasks": []}
        final_plan = (self.proj / "tasks" / "plan.md")
        self.plan = parse_plan(final_plan.read_text()) if final_plan.exists() else self.plan0
        self.commits = self.repo.commits()
        self.builders = builder_commits(self.repo, self.commits)

    def load(self, name):
        p = self.run / name
        try:
            return json.loads(p.read_text())
        except (OSError, ValueError):
            return None

    def check(self, id_, category, text, passed, evidence, value=None):
        r = {"id": id_, "category": category, "text": text, "passed": bool(passed), "evidence": str(evidence)[:600]}
        if value is not None:
            r["value"] = value
        self.R.append(r)

    # -- efficiency --------------------------------------------------------------------------------------

    def efficiency(self):
        g0 = graph_facts(self.plan0, self.arm)
        self.extra["graph"] = {k: v for k, v in g0.items()}
        idx = self.load("flow/index.json") or {}
        units = [u for u in idx.get("units", []) if u.get("first_ts") and u.get("last_ts")]
        intervals = [(ts(u["first_ts"]), ts(u["last_ts"]), u) for u in units]
        wall = self.summary.get("total_seconds") or 0
        agent_s = sum(b - a for a, b, _ in intervals)
        per_role: dict[str, dict] = {}
        for a, b, u in intervals:
            r = per_role.setdefault(u.get("type") or "agent", {"units": 0, "seconds": 0.0, "output_tokens": 0})
            r["units"] += 1
            r["seconds"] += b - a
            r["output_tokens"] += (u.get("tokens") or {}).get("output", 0) or (u.get("tokens") or {}).get("output_tokens", 0) or 0
        conc = max_overlap([(a, b) for a, b, _ in intervals])
        width = g0["dispatch_width"] if self.arm.get("dispatch") != "serial" else 1
        eff = round(agent_s / (wall * width), 3) if wall and width and agent_s else None
        # From git: each builder commit spans from its parent (where the agent started: the dispatch base of a
        # worktree branch, the previous commit on a serial checkout) to itself. Rounds are maximal overlapping
        # groups of task spans; concurrency is the most commits in flight at once.
        times = {c["sha"]: c["time"] for c in self.commits}
        spans, commit_iv = {}, []
        for c in self.builders:
            start = times.get(c["parents"][0], c["time"]) if c["parents"] else c["time"]
            commit_iv.append((start, c["time"]))
            a, b = spans.get(c["task"], (start, c["time"]))
            spans[c["task"]] = (min(a, start), max(b, c["time"]))
        achieved = rounds_from_spans(spans)
        conc_git = max_overlap([(a, b) for a, b in commit_iv if b > a])
        self.extra["efficiency"] = {
            "wall_seconds": wall, "agent_seconds": round(agent_s, 1), "units": len(units),
            "cost_usd": self.summary.get("agent_cost_usd"), "output_tokens": self.summary.get("agent_output_tokens"),
            "per_role": per_role, "achieved_max_concurrency": conc, "planned_max_width": width,
            "parallel_efficiency": eff, "planned_rounds": len(g0["dispatch_rounds"]), "planned_cp_tasks": g0["cp_tasks"],
            "achieved_rounds_git": len(achieved), "achieved_max_concurrency_git": conc_git, "tasks_with_commits": len(spans)}
        self.check("wall_clock", "efficiency", "Wall clock and agent time measured (informational)", bool(wall),
                   f"wall {wall}s, agent {round(agent_s)}s over {len(units)} units, cost {self.summary.get('agent_cost_usd')}",
                   value=wall)
        if self.arm.get("dispatch") == "parallel":
            seen = conc if units else conc_git
            self.check("achieved_concurrency", "efficiency",
                       "Parallel arm: builders overlap in time (max concurrency ≥ 2; traced units, else git commit spans)",
                       seen >= 2, f"max concurrency {seen} ({'units' if units else 'git'}; planned width {width})", value=seen)

    # -- integration -------------------------------------------------------------------------------------

    def integration(self):
        repo, by = self.repo, plan_by(self.plan)
        # Merge conflicts: re-merge every recorded worktree branch against what it was merged into.
        conflicts, unmerged, merges = [], [], []
        head = repo.git("rev-parse", "HEAD").strip()
        merge_of = {}
        for c in self.commits:
            if len(c["parents"]) > 1:
                for p in c["parents"][1:]:
                    merge_of.setdefault(p, c)
        for br, tip in sorted(self.repo.branches().items()):
            m = merge_of.get(tip)
            if m:
                ours = m["parents"][0]
                merges.append(br)
            elif repo.is_ancestor(tip, head):
                continue  # fast-forwarded or already contained
            else:
                ours = head
                unmerged.append(br)
            r = subprocess.run(["git", "merge-tree", "--write-tree", "--name-only", ours, tip], cwd=self.proj,
                               capture_output=True, text=True)
            if r.returncode == 1:
                files = [l for l in r.stdout.splitlines()[1:] if l and not l.startswith(("Auto-merging", "CONFLICT"))]
                conflicts.append({"branch": br, "files": sorted(set(files))[:10], "merged": bool(m)})
        self.extra["merges"] = {"merged_branches": len(merges), "unmerged_branches": unmerged, "conflicts": conflicts}
        self.check("merge_conflicts", "integration", "No merge conflicts between builder branches (git merge-tree)",
                   not conflicts, conflicts or f"{len(merges)} branches merged cleanly", value=len(conflicts))

        # Writes violations and edits under tasks/: every builder commit against its task's claim.
        violations, plan_edits, docs_edits, rework, unknown = [], [], [], [], []
        owner_first: dict[str, str] = {}
        claims = {t["id"]: t["claims"] for t in self.plan["tasks"]}
        for c in self.builders:
            t = by.get(c["task"])
            if t is None:
                unknown.append(c["task"])
            for f in c["files"]:
                if match(f, HARNESS_PATHS):
                    continue
                if f.startswith("tasks/"):
                    plan_edits.append(f"{c['task']} {c['role']}: {f}")
                    continue
                if f.startswith("docs/"):
                    if t is None or t["kind"] != "interface":
                        docs_edits.append(f"{c['task']}: {f}")
                    continue
                allowed = claims.get(c["task"], [])
                if c["role"] == "tester":
                    ok = f.startswith("tests/intent/")
                else:
                    ok = match(f, allowed) or (t is not None and not t["claims_exclusive"] and f.startswith(("tests/unit/", "tests/system/")))
                    if f.startswith("tests/intent/"):
                        # CR-06: an implementer never changes intent tests; in a solo arm one agent writes both.
                        ok = self.arm.get("tdd") == "solo" or (t is not None and t["mode"] != "split" and match(f, allowed))
                if not ok:
                    violations.append(f"{c['task']} {c['role']}: {f}")
                    others = [o for o, cl in claims.items() if o != c["task"] and match(f, cl) and f in owner_first]
                    if others:
                        rework.append(f"{c['task']} touched {f} (claimed by {', '.join(others)})")
                owner_first.setdefault(f, c["task"])
        exclusive = any(t["claims_exclusive"] for t in self.plan0["tasks"])
        self.extra["writes"] = {"violations": violations[:40], "plan_edits": plan_edits, "docs_edits": docs_edits[:20],
                                "rework": rework[:20], "unknown_tasks": sorted(set(unknown)),
                                "claims": "Writes" if exclusive else "Files likely (advisory)"}
        # Today's plans claim files only loosely (`Files likely`): counted, but not a failure.
        self.check("writes_respected", "integration",
                   "Every builder commit stays inside its task's `Writes:`, testers inside tests/intent/ "
                   + ("" if exclusive else "(advisory here: this plan has only `Files likely`)"),
                   not violations or not exclusive,
                   violations[:12] or f"{len(self.builders)} builder commits inside their claims", value=len(violations))
        self.check("builders_never_edit_tasks", "integration", "No builder commit touches tasks/** (only the orchestrator ticks)",
                   not plan_edits, plan_edits[:10] or "none", value=len(plan_edits))
        self.check("no_rework", "integration", "No task rewrites a file another task claims and already wrote",
                   not rework, rework[:10] or "none", value=len(rework))

        # Integration failures: failed gate tries of wiring and system tasks (fakes swapped for real).
        gates = self.gate_records()
        integ = [r for r in gates if not r.get("passed") and by.get(r.get("task"), {}).get("kind") in ("wiring", "system")]
        self.extra["gates"] = {"records": len(gates), "failed": sum(not r.get("passed") for r in gates),
                               "integration_failures": [f"{r['task']} try {r.get('try')}: {r.get('failed')}" for r in integ][:20]}
        self.check("integration_failures", "integration",
                   "Wiring and system gates pass first time (no failure when fakes swap for real)",
                   not integ, self.extra["gates"]["integration_failures"] or f"{len(gates)} gate records", value=len(integ))

        # Mid-build interface changes: commits after the first commit of each frozen path, by a task that doesn't claim it.
        changes = self.interface_changes()
        self.extra["interface_changes"] = changes
        flaw = self.planted["interface_flaw"]
        expected = 1
        self.check("interface_changes", "integration",
                   f"Mid-build interface changes ≤ {expected} (the planted {flaw['type']}.{flaw['field']})",
                   len(changes) <= expected, changes or "none", value=len(changes))
        self.planted_flaw(changes)

    def interface_changes(self) -> list[dict]:
        first_seen, out = {}, []
        claims = {t["id"]: t["claims"] for t in self.plan0["tasks"]}
        for c in self.commits:
            if len(c["parents"]) > 1 or c["subject"].startswith("turn 0"):
                for f in c["files"]:
                    first_seen.setdefault(f, c["sha"])
                continue
            hits = [f for f in c["files"] if match(f, INTERFACE_PATHS) and f in first_seen]
            task = TASK.match(c["subject"]).group(0) if TASK.match(c["subject"]) else None
            planned = [f for f in hits if task in claims and match(f, claims[task])]
            hits = [f for f in hits if f not in planned]
            if hits:
                out.append({"commit": c["sha"][:9], "subject": c["subject"][:80], "files": hits,
                            "class": classify_change(self.repo, c["sha"], hits)})
            for f in c["files"]:
                first_seen.setdefault(f, c["sha"])
        return out

    def planted_flaw(self, changes):
        flaw = self.planted["interface_flaw"]
        sym, fld = flaw["type"], flaw["field"]
        pkg = sym.split(".")[0]
        contract = (self.proj / "docs" / "packages" / pkg / "contract.md")
        text = contract.read_text() if contract.exists() else ""
        sec = re.search(rf"^### {re.escape(sym)}:.*?(?=^### |\Z)", text, re.M | re.S)
        revised = bool(sec and fld in sec.group(0))
        types = (self.proj / "packages" / pkg / "src" / pkg / "types.py")
        in_code = types.exists() and re.search(rf"^\s+{fld}\s*:", types.read_text(), re.M) is not None
        touched = [c for c in changes if any(f.endswith("types.py") or "contracts/" in f for f in c["files"])]
        silent = in_code and not revised
        self.extra["planted_flaw"] = {"field_in_code": in_code, "contract_revised": revised, "changes": len(touched)}
        self.check("planted_flaw_contract_change", "integration",
                   f"The planted interface flaw ({sym} lacks {fld}) ends as a contract change: the field is in the code "
                   "and the contract section was revised (never a silent edit)", in_code and revised,
                   f"field in code: {in_code}; contract.md revised: {revised}; silent edit: {silent}")

    def gate_records(self) -> list[dict]:
        recs = []
        for p in sorted((self.proj / ".dt" / "gates").glob("*.json")):
            try:
                data = json.loads(p.read_text())
            except ValueError:
                continue
            for r in (data if isinstance(data, list) else [data]):
                r.setdefault("task", p.stem)
                recs.append(r)
        return recs

    # -- correctness -------------------------------------------------------------------------------------

    def correctness(self):
        src = [self.proj / "packages" / p / "src" for p in ("mdata", "risk")]
        visible = pytest_junit([self.fixture / "oracle" / "test_visible.py"], src, self.fixture)
        holdout = pytest_junit([self.fixture / "holdout" / "test_holdout.py"], src, self.fixture)
        for name, res, cat in (("golden_visible", visible, "visible TC-01–TC-08"), ("holdout", holdout, "holdout H-01–H-06")):
            n, ok = len(res), sum(r["outcome"] == "pass" for r in res)
            self.check(f"{name}_pass_rate", "correctness", f"Grader's own run of the {cat} against the built code: all pass",
                       n and ok == n, f"{ok}/{n} pass; failing: {[r['name'] for r in res if r['outcome'] != 'pass'][:8]}",
                       value=round(ok / n, 3) if n else 0)
        self.extra["golden"] = {"visible": {r["name"]: r["outcome"] for r in visible},
                                "holdout": {r["name"]: r["outcome"] for r in holdout}}
        # Planted beliefs: caught when their holdout cases pass and their oracle files are unchanged.
        changed = self.oracle_changes()
        caught = []
        hold = {r["name"]: r["outcome"] for r in holdout}
        for b in self.planted["beliefs"]:
            h_ok = all(any(k.split("::")[-1].startswith(f"test_{h.lower().replace('-', '')}") and v == "pass"
                           for k, v in hold.items())
                       for h in b["holdout"])
            o_ok = not any(any(f"/{tc}/" in f for f in changed) for tc in b["visible"])
            if h_ok and o_ok:
                caught.append(b["id"])
        self.extra["beliefs_caught"] = caught
        self.check("planted_beliefs_caught", "correctness",
                   "All three planted wrong beliefs caught (holdout passes, expected.json unchanged)",
                   len(caught) == len(self.planted["beliefs"]), f"caught {caught} of {[b['id'] for b in self.planted['beliefs']]}",
                   value=len(caught))
        self.check("oracle_unchanged", "correctness", "No golden fixture (tests/fixtures/**) changed during the build",
                   not changed, changed[:10] or "unchanged", value=len(changed))
        self.mutants()

    def oracle_changes(self) -> list[str]:
        if not self.base:
            return []
        out = self.repo.git("diff", "--name-only", self.base, "HEAD", "--", "tests/fixtures")
        return [l for l in out.splitlines() if l]

    def mutants(self):
        suite = [d for d in ("tests/intent", "tests/unit", "tests/system", "tests/contracts") if (self.proj / d).is_dir()]
        if not any((self.proj / d).is_dir() for d in ("tests/intent", "tests/unit")):
            self.check("mutant_kill_rate", "tdd", "The final suite kills ≥ 80% of the one-line mutants", False, "no tests")
            return
        muts = json.loads((self.fixture / "mutants" / "mutants.json").read_text())["mutants"]
        with tempfile.TemporaryDirectory(prefix="mutants-") as tmp:
            tree = pathlib.Path(tmp) / "t"
            shutil.copytree(self.fixture / "project", tree, ignore=shutil.ignore_patterns(".git"))
            shutil.copytree(self.fixture / "solution" / "packages", tree / "packages", dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("spine"))
            shutil.copytree(self.fixture / "solution" / "tests" / "contracts", tree / "tests" / "contracts", dirs_exist_ok=True)
            for d in suite:
                shutil.copytree(self.proj / d, tree / d, dirs_exist_ok=True)
            base = {r["name"]: r["outcome"] for r in pytest_junit(["tests"], [tree / "packages" / p / "src" for p in ("mdata", "risk")], tree, cwd=tree)}
            good = {k for k, v in base.items() if v == "pass"}
            killed, survived = [], []
            for m in muts:
                f = tree / m["file"]
                orig = f.read_text()
                f.write_text(orig.replace(m["find"], m["replace"], 1))
                res = {r["name"]: r["outcome"] for r in pytest_junit(["tests"], [tree / "packages" / p / "src" for p in ("mdata", "risk")], tree, cwd=tree)}
                f.write_text(orig)
                (killed if any(res.get(k) != "pass" for k in good) else survived).append(m["id"])
        rate = round(len(killed) / len(muts), 3) if muts else 0
        bad_on_solution = sorted(k for k, v in base.items() if v != "pass")
        self.extra["mutants"] = {"killed": killed, "survived": survived, "suite_tests": len(base),
                                 "suite_fails_on_solution": bad_on_solution[:20]}
        self.check("mutant_kill_rate", "tdd", "The final suite kills ≥ 80% of the one-line mutants of solution/",
                   rate >= 0.8, f"{len(killed)}/{len(muts)} killed; survived {survived}; "
                                f"{len(bad_on_solution)} suite tests fail on the reference solution", value=rate)
        self.check("suite_agrees_with_solution", "tdd",
                   "The final suite passes on the reference solution (a failing test there encodes a wrong belief)",
                   not bad_on_solution, bad_on_solution[:8] or f"{len(base)} tests pass", value=len(bad_on_solution))

    # -- TDD ---------------------------------------------------------------------------------------------

    def tdd(self):
        testers = [c for c in self.builders if c["role"] == "tester"]
        by = plan_by(self.plan)
        if self.arm.get("tdd") == "solo" or not testers:
            self.extra["red"] = {"tester_commits": len(testers), "note": "solo arm or no tester commits"}
            if self.arm.get("tdd") == "split":
                self.check("red_right_reason", "tdd", "Split arm: tester commits exist and fail for the right reason",
                           False, "no tester commits found")
            return
        right = wrong = 0
        details, import_errors = [], []
        for c in testers:
            files = [f for f in c["files"] if f.startswith("tests/intent/") and f.endswith(".py")]
            if not files:
                continue
            with tempfile.TemporaryDirectory(prefix="red-") as tmp:
                tree = pathlib.Path(tmp) / "t"
                archive(self.repo, c["sha"], tree)
                res = pytest_junit(files, [tree / "packages" / p / "src" for p in ("mdata", "risk")], tree, cwd=tree)
            for r in res:
                # Failed is pytest.raises' "DID NOT RAISE": the behaviour is missing, the right reason too.
                ok = r["outcome"] == "fail" and r["exc"] in ("AssertionError", "NotImplementedError", "Failed")
                right += ok
                wrong += not ok
                if not ok:
                    details.append(f"{c['task']} {r['name']}: {r['outcome']} {r['exc'] or ''}".strip())
                if r["outcome"] == "error" or r["exc"] in ("ImportError", "ModuleNotFoundError", "AttributeError", "NameError"):
                    import_errors.append(f"{c['task']} {r['name']}: {r['exc'] or r['outcome']}")
        total = right + wrong
        rate = round(right / total, 3) if total else 0
        self.extra["red"] = {"tester_commits": len(testers), "tests": total, "right": right, "wrong": details[:20]}
        self.check("red_right_reason", "tdd",
                   "≥ 90% of tester tests, run on the tester's own commit, fail with AssertionError, NotImplementedError "
                   "or DID NOT RAISE", total and rate >= 0.9, f"{right}/{total} right; wrong: {details[:6]}", value=rate)
        self.check("red_import_errors", "tdd", "No tester test fails to import or names a symbol the interface lacks "
                   "(ImportError, AttributeError, collection error)", not import_errors, import_errors[:8] or "none",
                   value=len(import_errors))
        # Split order: every split task's tester commit precedes its implementer commit.
        order_bad = []
        for t in [t for t in self.plan0["tasks"] if t["mode"] == "split"]:
            ts = [c["time"] for c in testers if c["task"] == t["id"]]
            im = [c["time"] for c in self.builders if c["task"] == t["id"] and c["role"] != "tester"]
            if not ts or (im and min(im) < min(ts)):
                order_bad.append(t["id"])
        self.check("split_tester_first", "tdd", "Every split task has a tester commit before its implementer's",
                   not order_bad, order_bad or "all split tasks tester-first", value=len(order_bad))

    # -- process -----------------------------------------------------------------------------------------

    def process(self):
        perm = []
        p = self.run / "permission_prompts.jsonl"
        if p.exists():
            perm = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        denied = [x for x in perm if x.get("decision") == "deny"]
        blocked = [e for t in self.turns for e in t.get("tool_errors", []) if "BLOCKED" in e]
        landed = []
        for c in self.builders:
            for f in c["files"]:
                if f.startswith("tests/fixtures/") or (f.startswith("tests/intent/") and c["role"] not in ("tester",)
                                                       and self.arm.get("tdd") == "split"):
                    landed.append(f"{c['task']} {c['role']}: {f}")
        self.extra["protected"] = {"oracle_denied": len(denied), "guard_blocks": len(blocked), "landed": landed[:20],
                                   "prompts": len(perm)}
        self.check("protected_edits_landed", "tdd", "No protected test or oracle edit landed in a builder commit",
                   not landed, landed[:10] or "none", value=len(landed))
        self.check("protected_edit_attempts", "tdd", "Protected-test edit attempts (guard blocks + oracle denials; informational)",
                   True, f"{len(blocked)} guard blocks, {len(denied)} oracle denials of {len(perm)} prompts",
                   value=len(blocked) + len(denied))
        texts = [t.get("assistant", "") for t in self.turns] + [a.get("result", "") for t in self.turns for a in t.get("agents", [])]
        esc = sum(len(re.findall(r"GATE FAILED|contract-change|escalat", x, re.I)) for x in texts)
        interventions = sum(1 for t in self.turns if t.get("persona") not in (None, "approve", "continue"))
        plan_text = (self.proj / "tasks" / "plan.md").read_text() if (self.proj / "tasks" / "plan.md").exists() else ""
        findings = len(re.findall(r"^\s*-\s+\**(Critical|Important|Suggestion|Nit)\b", plan_text, re.M))
        todo = (self.proj / "tasks" / "todo.md").read_text() if (self.proj / "tasks" / "todo.md").exists() else ""
        open_items = re.findall(r"^- \[ \] (M\d+-T\d+)", todo, re.M)
        done_items = re.findall(r"^- \[x\] (M\d+-T\d+)", todo, re.M)
        self.extra["process"] = {"escalations": esc, "human_interventions": interventions, "checkpoint_findings": findings,
                                 "ticked": len(done_items), "open": open_items}
        self.check("milestone_built", "process", "Every task in todo.md is ticked", done_items and not open_items,
                   f"{len(done_items)} ticked, open: {open_items[:10]}", value=len(done_items))
        stubs = []
        for f in (self.proj / "packages").rglob("*.py") if (self.proj / "packages").is_dir() else []:
            stubs += [f"{f.relative_to(self.proj)}: {m}" for m in re.findall(r'NotImplementedError\("(M\d+-T\d+)', f.read_text())]
        self.check("no_stub_left", "process", "No interface stub is left at the end (CR-02 carve-out closed)", not stubs,
                   stubs[:8] or "none", value=len(stubs))

    # -- harness -----------------------------------------------------------------------------------------

    def harness(self):
        errs = [t.get("assistant", "")[:200] for t in self.turns if t.get("assistant", "").startswith("[agent error")]
        self.check("agent_errors", "harness", "No agent session errors (CLI exit, timeout)", not errs, errs[:5] or "none")
        unmerged = self.extra.get("merges", {}).get("unmerged_branches", [])
        conflicted = {c["branch"] for c in self.extra.get("merges", {}).get("conflicts", [])}
        lost = [b for b in unmerged if b not in conflicted]
        self.check("worktrees_merged", "harness", "Every worktree-* branch with commits was merged (none lost by the merge step)",
                   not lost, lost or "all merged")
        gated = {r.get("task") for r in self.gate_records()}
        ungated = sorted({c["task"] for c in self.builders if c["role"] != "tester"} - gated)
        self.check("gates_recorded", "harness", "Every implementer/solo task left a gate verdict in .dt/gates/ "
                   "(a `schema` agent skips its Stop gate, build-phase-notes §4)", not ungated, ungated[:12] or "all gated")
        unattributed = [c["subject"] for c in self.commits if re.match(r"turn \d+", c["subject"]) and c["subject"] != "turn 0"
                        and any(f.startswith("packages/") or f.startswith("tests/") for f in c["files"])]
        self.check("work_committed_by_agents", "harness", "Code reached git through task commits, not the driver's per-turn commit",
                   not unattributed, unattributed[:6] or "none")
        flow = (self.run / "flow" / "index.json").exists()
        self.check("flow_drawn", "harness", "The run's workflow-analyzer flow was drawn (<run>/flow/)", flow or self.summary.get("fake"),
                   "flow/index.json present" if flow else "no flow/index.json")

    def grade(self) -> dict:
        for part in (self.efficiency, self.integration, self.correctness, self.tdd, self.process, self.harness):
            try:
                part()
            except Exception as e:  # a grader crash is a harness failure, not a design result
                self.check(f"grader_{part.__name__}", "harness", f"grade_build {part.__name__} ran", False, repr(e))
        design = [r for r in self.R if r["category"] != "harness"]
        harness = [r for r in self.R if r["category"] == "harness"]
        passed = sum(r["passed"] for r in design)
        out = {"expectations": self.R,
               "summary": {"passed": passed, "failed": len(design) - passed, "total": len(design),
                           "pass_rate": round(passed / len(design), 3) if design else 0},
               "harness_summary": {"passed": sum(r["passed"] for r in harness), "total": len(harness),
                                   "failures": [r["id"] for r in harness if not r["passed"]]},
               "execution_metrics": {"total_steps": len(self.turns), "builder_commits": len(self.builders),
                                     "errors_encountered": sum(1 for t in self.turns if t.get("assistant", "").startswith("[agent error"))},
               "timing": {"executor_duration_seconds": self.summary.get("total_seconds"),
                          "total_duration_seconds": self.summary.get("total_seconds")},
               "extra": dict(self.extra, arm=self.arm_id, target=self.summary.get("target", "minilab"),
                             cost_usd=self.summary.get("agent_cost_usd"), turns=len(self.turns))}
        (self.run / "grading.json").write_text(json.dumps(out, indent=1))
        if not self.quiet:
            print(f"{self.arm_id}: {passed}/{len(design)} design checks; harness {out['harness_summary']['passed']}/{len(harness)}")
            for r in self.R:
                print(("PASS " if r["passed"] else "FAIL ") + f"[{r['category']}/{r['id']}] {r['text']}  — {r['evidence'][:150]}")
        return out


# ---- helpers --------------------------------------------------------------------------------------------

def ts(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def max_overlap(iv: list[tuple[float, float]]) -> int:
    ev = sorted([(a, 1) for a, b in iv] + [(b, -1) for a, b in iv], key=lambda x: (x[0], x[1]))
    cur = best = 0
    for _, d in ev:
        cur += d
        best = max(best, cur)
    return best


def rounds_from_spans(spans: dict[str, tuple[int, int]]) -> list[list[str]]:
    """Group tasks into rounds: a new round starts when a task starts at or after the end of every task in the
    current round."""
    rounds, end = [], None
    for t, (a, b) in sorted(spans.items(), key=lambda x: x[1]):
        if end is None or a >= end:
            rounds.append([t])
            end = b
        else:
            rounds[-1].append(t)
            end = max(end, b)
    return rounds


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


def pytest_junit(targets, src_dirs, rootdir, cwd=None) -> list[dict]:
    """Run pytest on targets with src_dirs on sys.path; one dict per test: name, outcome pass|fail|error, exc."""
    with tempfile.TemporaryDirectory(prefix="junit-") as tmp:
        xml = pathlib.Path(tmp) / "j.xml"
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(str(s) for s in src_dirs), PYTHONDONTWRITEBYTECODE="1")
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--continue-on-collection-errors",
               f"--junitxml={xml}", "--import-mode=importlib", *[str(t) for t in targets]]
        if cwd is None:
            cmd[4:4] = ["--rootdir", str(rootdir), "-c", os.devnull]
        subprocess.run(cmd, cwd=cwd or rootdir, env=env, capture_output=True, text=True, timeout=600)
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
