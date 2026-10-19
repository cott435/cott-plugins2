"""What a build can dispatch now (build-phase.md §4, §6.1, §9): ready task halves and due reviews, and what holds
the rest. Read by `dt ready --halves/--reserve`, `dt build status`, `dt claim` and `dt finding --from`.

Landed: an implementer or solo half is landed when its task is ticked in `todo.md` (`dt land` ticks it in the
landing commit); a tester half when its tests branch `dt/<task>-tests` exists.

Holds, in the order they are reported:
- **critical** — a recorded review has a Critical finding not yet resolved: nothing is released.
- **escalation** — an unresolved NEEDS-DEP escalation, or a CONTRACT-CHANGE naming no type: nothing is released.
- **barrier** — a `(barrier)` checkpoint whose reviews haven't all passed: no implementer or solo half of a task after
  it in the plan. A checkpoint straight after an interface task is a barrier too, and where the plan puts another
  task straight after one, dt adds the barrier (`added_barriers`): no code builds on a frozen interface before its
  review. Tester halves run during it: they read only the frozen surface, so they are the fastest check of what it
  lacks, and their tests are red by design.
- **contract** — an unresolved CONTRACT-CHANGE naming a contract type (`dt escalate CONTRACT-CHANGE --type`): no
  half of a task that reads that type, nor of a task depending on the escalating one, directly or not.
- **blocked** — a half rejected twice, three harness failures in a row, or a TEST-WRONG escalation unresolved.
- **risk** — a task marked `**Risk:** external` with no `dt build resolve <task>`.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from . import buildstate as bs
from . import graph, md, model
from .commands.roadmap import active_plan

DEFAULT_CAP = 6


def holds_all(esc: dict) -> bool:
    """An escalation that holds every half: NEEDS-DEP, or a CONTRACT-CHANGE that names no type (an earlier stop on
    the same claim counts too)."""
    return any(e.get("kind") == "NEEDS-DEP" or (e.get("kind") == "CONTRACT-CHANGE" and not e.get("type"))
               for e in (esc, *esc.get("earlier", [])))


def half_id(task: str, role: str) -> str:
    return f"{task}.{role}"


def agent_type(role: str) -> str:
    return "tester" if role == "tester" else "implementer"


def builder_prompt(task: str, role: str) -> str:
    return (f"You are the {role} for {task}. Run `python3 {bs.DT_PY} claim {task} --role {role}`, "
            "then read the packet it names.")


def is_risky(task: model.Task) -> bool:
    return "external" in md.strip_md(task.get("Risk")).lower()


@dataclass
class Phase:
    """A checkpoint and the tasks it reviews: those between the previous checkpoint and it in the plan (the
    milestone exit: every task)."""
    checkpoint: model.Checkpoint
    key: str                    # the checkpoint's `after` task, or "exit"
    tasks: list[model.Task]
    after_interface: bool = False   # straight after an interface task in the plan

    @property
    def barrier(self) -> bool:
        return self.after_interface or "(barrier)" in self.checkpoint.title.lower()

    @property
    def kind(self) -> str:
        return "exit" if self.key == "exit" else "interface" if self.barrier else "phase"


def added_barriers(plan, tasks: list[model.Task]) -> list[model.Checkpoint]:
    """A barrier checkpoint, not in the plan's text, after each interface task the plan follows straight with a
    task that isn't one. It starts where the interface task's section ends; `dt finding` writes it into the plan
    with the review's first finding."""
    items = sorted([*tasks, *model.checkpoints(plan)], key=lambda x: x.start)
    return [model.Checkpoint(f"Checkpoint after {a.id} (barrier)", a.id, plan, a.end, a.end, [], [])
            for a, b in zip(items, items[1:])
            if isinstance(a, model.Task) and isinstance(b, model.Task) and a.kind == "interface" != b.kind]


def phases(plan) -> list[Phase]:
    tasks = model.tasks(plan)
    out, prev = [], -1
    for cp in sorted([*model.checkpoints(plan), *added_barriers(plan, tasks)], key=lambda c: c.start):
        if not cp.after and "exit" in cp.title.lower():
            out.append(Phase(cp, "exit", tasks))
            continue
        if not cp.after:
            continue
        mine = [t for t in tasks if prev < t.start < cp.start]
        out.append(Phase(cp, cp.after, mine, bool(mine) and mine[-1].kind == "interface"))
        prev = cp.start
    return out


def tasks_fingerprint(tasks: list[model.Task]) -> str:
    """A hash of the plan's task blocks, ticked boxes read as unticked, so a Replan changes it and a tick doesn't."""
    text = "".join(re.sub(r"\[[xX]\]", "[ ]", t.text) for t in tasks)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

class Build:
    """One snapshot of the plan, todo.md, git and dt-build/ for the checkout at `repo.root`."""

    def __init__(self, repo, state: bs.State | None = None):
        self.repo = repo
        self.plan = active_plan(repo)
        self.tasks = model.tasks(self.plan) if self.plan else []
        self.by_id = {t.id: t for t in self.tasks}
        self.done = {k for k, v in model.todo_state(repo).items() if v}
        self.state = state or bs.State(repo.root)
        self.reserved = {r["id"]: r for r in self.state.all("reserved")}
        self.claims = {c["id"]: c for c in self.state.all("claims")}
        self.escalations = {e["claim"]: e for e in self.state.all("escalations")}
        self.rejects = {r["id"]: r for r in self.state.all("rejects")}
        self.resolved = {r["id"]: r for r in self.state.all("resolved")}
        self.reviews = {f"{r['checkpoint']}.{r['pkg']}": r for r in self.state.all("reviews")}
        self.phases = phases(self.plan) if self.plan else []

    # ---- landed -------------------------------------------------------------------------------

    def tester_landed(self, task_id: str) -> bool:
        return bs.ref_exists(self.repo.root, f"refs/heads/{bs.tests_branch(task_id)}")

    def landed(self, task: model.Task, role: str) -> bool:
        if role == "tester":
            return task.id in self.done or self.tester_landed(task.id)
        return task.id in self.done

    # ---- holds --------------------------------------------------------------------------------

    def open_critical(self) -> list[str]:
        """Critical finding IDs recorded by a review and not resolved."""
        return [f for r in self.reviews.values() for f in r.get("critical", []) if f not in self.resolved]

    def go_current(self) -> bool | None:
        """Whether the recorded go still matches the plan's tasks; None when no go is recorded."""
        go = self.state.read("go", "go")
        return None if go is None else go.get("tasks") == tasks_fingerprint(self.tasks)

    def global_holds(self) -> list[str]:
        out = []
        if self.go_current() is False:
            out.append("go: the plan's tasks changed since the go (a Replan); the user's new go is recorded "
                       "with dt build go")
        crit = self.open_critical()
        if crit:
            out.append(f"critical: {', '.join(crit)} unresolved (dt build resolve <finding>)")
        for e in self.escalations.values():
            if holds_all(e):
                out.append(f"escalation: {e['claim']} {e['kind']}: {e.get('why', '')}")
        return out

    def contract_hold(self, task: model.Task) -> str:
        """Why a CONTRACT-CHANGE naming a type holds this task: it reads the type, or depends on the task that
        escalated. "" when none does."""
        for e in self.escalations.values():
            types = [t for x in (e, *e.get("earlier", [])) if x.get("kind") == "CONTRACT-CHANGE"
                     for t in ([x["type"]] if x.get("type") else [])]
            if not types or e.get("task") == task.id:
                continue
            reads = {md.strip_md(r) for r in task.read}
            for t in types:
                if t in reads:
                    return f"escalation: {e['claim']} CONTRACT-CHANGE on {t}, which {task.id} reads"
            if e.get("task") in graph.ancestors(self.tasks, task.id):
                return f"escalation: {e['claim']} CONTRACT-CHANGE on {', '.join(types)}; {task.id} depends on {e['task']}"
        return ""

    def review_passed(self, phase: Phase, pkg: str) -> bool:
        r = self.reviews.get(f"{phase.key}.{pkg}")
        if r is None:
            return False
        recorded = r.get("tasks")
        if recorded is not None and not {t.id for t in phase.tasks if t.package == pkg} <= set(recorded):
            return False
        return all(f in self.resolved for f in r.get("critical", []))

    def phase_passed(self, phase: Phase) -> bool:
        pkgs = sorted({t.package for t in phase.tasks})
        return bool(pkgs) and all(self.review_passed(phase, p) for p in pkgs)

    def barrier_for(self, task: model.Task) -> Phase | None:
        """The first unpassed barrier checkpoint before the task in the plan."""
        for ph in self.phases:
            if ph.barrier and ph.checkpoint.start < task.start and not self.phase_passed(ph):
                return ph
        return None

    def blocked_why(self, task: model.Task, role: str) -> str:
        hid = half_id(task.id, role)
        esc = self.escalations.get(hid)
        if esc and not holds_all(esc):
            return f"escalated {esc['kind']}: {esc.get('why', '')}"
        rej = self.rejects.get(hid) or {}
        if rej.get("count", 0) >= 2:
            return f"rejected {rej['count']} times (last: {rej.get('last', {}).get('reject')})"
        if rej.get("harness", 0) >= 3:
            return f"{rej['harness']} harness failures in a row"
        if is_risky(task) and task.id not in self.resolved:
            return "Risk: external (needs the user's yes: dt build resolve <task>)"
        return ""

    # ---- halves -------------------------------------------------------------------------------

    def waiting_halves(self) -> list[tuple[model.Task, str]]:
        """Halves whose dependencies have landed and that aren't landed, reserved or claimed (holds ignored)."""
        out = []
        kinds = {t.id: t.kind for t in self.tasks}
        for t in self.tasks:
            if t.id in self.done:
                continue
            deps_done = all(d in self.done for d in t.depends_on if d in self.by_id)
            for role in graph.roles(t):
                hid = half_id(t.id, role)
                if hid in self.reserved or hid in self.claims:
                    continue
                if role == "tester":
                    if self.tester_landed(t.id):
                        continue
                    ifaces = {a for a in graph.ancestors(self.tasks, t.id) if kinds[a] == "interface"}
                    ok = ifaces <= self.done
                elif role == "implementer":
                    ok = deps_done and self.tester_landed(t.id)
                else:
                    ok = deps_done
                if ok:
                    out.append((t, role))
        return out

    def held(self) -> tuple[list[str], list[dict], list[tuple[model.Task, str]]]:
        """(global holds, held halves with why, releasable halves)."""
        glob = self.global_holds()
        held, free = [], []
        for t, role in self.waiting_halves():
            why = ""
            if glob:
                why = glob[0]
            elif role != "tester" and (ph := self.barrier_for(t)) is not None:
                why = f"barrier: checkpoint after {ph.key} not passed"
            else:
                why = self.blocked_why(t, role) or self.contract_hold(t)
            if why:
                held.append({"id": t.id, "role": role, "why": why})
            else:
                free.append((t, role))
        return glob, held, free

    def half_row(self, t: model.Task, role: str, remaining: dict[str, int]) -> dict:
        return {"id": t.id, "role": role, "agent_type": agent_type(role), "title": t.title, "kind": t.kind,
                "pkg": t.package, "remaining_cp": remaining.get(half_id(t.id, role), 0),
                "claim": half_id(t.id, role), "prompt": builder_prompt(t.id, role)}

    # ---- reviews ------------------------------------------------------------------------------

    def due_reviews(self) -> list[dict]:
        """A review row per package of each checkpoint whose tasks have all landed and that has no recorded
        review covering them (a second exit review covers the tasks added since the first)."""
        rows = []
        lands = bs.landings(self.repo.root) if self.phases else {}
        for ph in self.phases:
            if not ph.tasks or not all(t.id in self.done for t in ph.tasks):
                continue
            due = []
            for pkg in sorted({t.package for t in ph.tasks}):
                rid = f"{ph.key}.{pkg}"
                mine = [t for t in ph.tasks if t.package == pkg]
                prev = self.reviews.get(rid)
                todo = [t for t in mine if prev is None or t.id not in prev.get("tasks", [])]
                if todo and f"{rid}.reviewer" not in self.reserved:
                    due.append((pkg, todo))
            for n, (pkg, todo) in enumerate(due):
                rows.append(self.review_row(ph, pkg, todo, lands, lead=n == 0))
        return rows

    def review_row(self, ph: Phase, pkg: str, tasks: list[model.Task], lands: dict, lead: bool) -> dict:
        root = self.repo.root
        shas = [lands[t.id]["sha"] for t in tasks if t.id in lands]
        order = bs.out(root, "rev-list", "--topo-order", "HEAD").splitlines() if shas else []
        pos = {s: i for i, s in enumerate(order)}
        shas = sorted(shas, key=lambda s: -pos.get(s, 0))          # oldest first
        end = shas[-1] if shas else bs.head(root)
        parent = bs.git(root, "rev-parse", f"{shas[0]}^", check=False).stdout.strip() if shas else ""
        base = parent or end
        paths = list(dict.fromkeys(w for t in tasks for w in t.writes))
        rid = f"{ph.key}.{pkg}"
        findings = self.state.path("reviews", f"{rid}.md")
        ids = [t.id for t in tasks]
        prompt = (f"You are the reviewer for the {ph.kind} review at checkpoint {ph.key}, package {pkg} "
                  f"(lead: {'yes' if lead else 'no'}). Tasks {', '.join(ids)}; base {base[:12]}, end {end[:12]}; "
                  f"commits {' '.join(s[:12] for s in shas) or 'none'}; paths {' '.join(paths) or 'none'}. "
                  + (f"What later tasks need from this surface: `python3 {bs.DT_PY} build needs {ph.key}`. "
                     if ph.kind == "interface" else "")
                  + f"Write your finding lines to .dt/review.md in your worktree, then run "
                  f"`python3 {bs.DT_PY} build submit-review {rid} .dt/review.md`, and end with one line: "
                  f"REVIEW {ph.key} {pkg}: <n> findings, <c> Critical. dt is `python3 {bs.DT_PY}`.")
        return {"id": rid, "role": "reviewer", "agent_type": "reviewer", "title": ph.checkpoint.title,
                "kind": ph.kind, "pkg": pkg, "checkpoint": ph.key, "tasks": ids, "commits": shas, "base": base,
                "end": end, "paths": paths, "lead": lead, "findings_file": str(findings),
                "remaining_cp": 0, "claim": f"{rid}.reviewer", "prompt": prompt}

    # ---- ready ------------------------------------------------------------------------------

    def ready(self, cap: int | None) -> dict:
        """What may start now under the cap: review rows first, then halves by remaining critical path."""
        glob, held, free = self.held()
        remaining = graph.remaining_weight(self.tasks)
        order = {t.id: n for n, t in enumerate(self.tasks)}
        free.sort(key=lambda h: (-remaining.get(half_id(h[0].id, h[1]), 0), order[h[0].id], h[1] != "tester"))
        reviews = [] if glob else self.due_reviews()
        for r in reviews:
            r["remaining_cp"] = max(remaining.values(), default=0)
        rows = reviews + [self.half_row(t, role, remaining) for t, role in free]
        in_flight = self.state.in_flight()
        shown = rows if cap is None else rows[:max(cap - len(in_flight), 0)]
        return {"rows": shown, "over_cap": len(rows) - len(shown), "in_flight": in_flight, "cap": cap,
                "holds": glob, "held": held,
                "all_landed": bool(self.tasks) and all(t.id in self.done for t in self.tasks)}

    def needs(self, key: str) -> list[dict]:
        """What each task after an interface checkpoint will ask of the frozen surface: its Read:, acceptance and
        the golden cases it reads or covers, in plan order. The interface reviewer checks each against the code."""
        ph = next((p for p in self.phases if p.key == key), None)
        if ph is None:
            raise ValueError(f"no checkpoint {key} in the plan")
        cases = {tc.id: tc for doc in self.repo.docs("tests") for tc in model.test_cases(doc)}
        out = []
        for t in self.tasks:
            if t.start < ph.checkpoint.start or t.kind == "interface":
                continue
            ids = [md.strip_md(r).split(" (")[0] for r in t.read] + t.covers
            tcs = [cases[i] for i in dict.fromkeys(ids) if i in cases]
            out.append({"id": t.id, "title": t.title, "kind": t.kind, "mode": t.mode,
                        "read": [md.strip_md(r) for r in t.read],
                        "acceptance": [c.text for c in t.acceptance],
                        "cases": [{"id": tc.id, "title": tc.title,
                                   "expected": md.strip_md(tc.fields.get("Expected", ""))} for tc in tcs]})
        return out

    def next_checkpoint(self) -> dict | None:
        for ph in self.phases:
            pkgs = sorted({t.package for t in ph.tasks})
            if pkgs and all(self.review_passed(ph, p) for p in pkgs):
                continue
            return {"checkpoint": ph.key, "title": ph.checkpoint.title, "kind": ph.kind,
                    "waiting_on": [t.id for t in ph.tasks if t.id not in self.done]}
        return None


def finding_counts(plan) -> dict[str, int]:
    counts: dict[str, int] = {}
    for cp in model.checkpoints(plan) if plan else []:
        for f in cp.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


def checkpoint_after(plan, task: model.Task) -> str | None:
    """The key (`M1-T05` or `exit`) of the first checkpoint below the task in the plan."""
    for cp in model.checkpoints(plan):
        if cp.start > task.start:
            return cp.after or ("exit" if "exit" in cp.title.lower() else None)
    return None


def task_of(repo, task_id: str) -> model.Task | None:
    plan = active_plan(repo)
    return next((t for t in model.tasks(plan) if t.id == task_id), None) if plan else None


TASK_RE = re.compile(md.TASK_ID)
