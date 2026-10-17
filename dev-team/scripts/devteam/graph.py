"""A plan's task graph (interface-first-design.md §6): waves, critical path, width and the ready set.

Pure functions over `list[model.Task]`. Only `Depends on` orders tasks: a mitigated `## Dependency graph` edge is
documentation and never appears here. Dependencies on tasks outside the list (another plan, the archive) are
ignored, and so is a dependency that would close a cycle (`dt lint` reports cycles).
"""
from __future__ import annotations

from .model import Task

# Size weights for breaking ties between equally long paths: the heavier path is the critical one.
SIZE_WEIGHT = {"XS": 1, "S": 2, "M": 4}


def _deps(tasks: list[Task]) -> dict[str, list[str]]:
    ids = {t.id for t in tasks}
    return {t.id: [d for d in dict.fromkeys(t.depends_on) if d in ids and d != t.id] for t in tasks}


def _levels(tasks: list[Task]) -> dict[str, int]:
    """Task → its wave: 0 for no dependencies, else one past its deepest dependency."""
    deps = _deps(tasks)
    level: dict[str, int] = {}

    def visit(node: str, path: frozenset) -> int:
        if node not in level:
            level[node] = 1 + max((visit(d, path | {node}) for d in deps[node] if d not in path), default=-1)
        return level[node]

    for t in tasks:
        visit(t.id, frozenset())
    return level


def waves(tasks: list[Task]) -> list[list[str]]:
    """Topological levels: wave 0 holds the tasks with no dependencies, wave k those whose deepest dependency is
    in wave k−1. Plan order within a wave."""
    level = _levels(tasks)
    out: list[list[str]] = [[] for _ in range(max(level.values(), default=-1) + 1)]
    for t in tasks:
        out[level[t.id]].append(t.id)
    return out


def width(tasks: list[Task]) -> int:
    """The largest wave: how many agents the plan can use at once."""
    return max((len(w) for w in waves(tasks)), default=0)


def critical_path(tasks: list[Task]) -> list[str]:
    """The longest Depends-on chain, first to last. Ties go to the heavier chain (XS 1, S 2, M 4), then to the
    one whose tasks come first in plan order."""
    deps = _deps(tasks)
    order = {t.id: n for n, t in enumerate(tasks)}
    weight = {t.id: SIZE_WEIGHT.get(t.size, 2) for t in tasks}
    best: dict[str, tuple[int, int, list[str]]] = {}

    def key(c: tuple[int, int, list[str]]):
        return (c[0], c[1], [-order[i] for i in c[2]])

    def chain(node: str, path: frozenset) -> tuple[int, int, list[str]]:
        if node not in best:
            prev = [chain(d, path | {node}) for d in deps[node] if d not in path]
            n, w, ids = max(prev, key=key, default=(0, 0, []))
            best[node] = (n + 1, w + weight[node], ids + [node])
        return best[node]

    return max((chain(t.id, frozenset()) for t in tasks), key=key, default=(0, 0, []))[2]


def parallelism(tasks: list[Task]) -> float:
    """Tasks ÷ critical path (0 for an empty plan), two decimals."""
    cp = len(critical_path(tasks))
    return round(len(tasks) / cp, 2) if cp else 0.0


def ready(tasks: list[Task], done: set[str]) -> list[str]:
    """Tasks not done whose dependencies (inside the plan) are all done, in plan order."""
    deps = _deps(tasks)
    return [t.id for t in tasks if t.id not in done and all(d in done for d in deps[t.id])]


def ancestors(tasks: list[Task], task_id: str) -> set[str]:
    """Every task `task_id` depends on, directly or not."""
    deps = _deps(tasks)
    seen: set[str] = set()
    stack = list(deps.get(task_id, []))
    while stack:
        node = stack.pop()
        if node not in seen:
            seen.add(node)
            stack.extend(deps[node])
    return seen


def tester_ready(tasks: list[Task], done: set[str]) -> list[str]:
    """Split tasks not in `ready` whose tester half may start: the tester writes against the frozen interface,
    so it waits only for the interface tasks among the task's dependencies (§5.1, §7). A task with no interface
    task upstream isn't listed."""
    now = set(ready(tasks, done))
    kinds = {t.id: t.kind for t in tasks}
    out = []
    for t in tasks:
        if t.id in done or t.id in now or t.mode != "split":
            continue
        interfaces = {a for a in ancestors(tasks, t.id) if kinds[a] == "interface"}
        if interfaces and interfaces <= done:
            out.append(t.id)
    return out


def path_between(tasks: list[Task], a: str, b: str) -> bool:
    """A Depends-on path joins the two tasks, either way (one must finish before the other starts)."""
    return a in ancestors(tasks, b) or b in ancestors(tasks, a)


def metrics(tasks: list[Task]) -> dict:
    """What `dt status` and `dt plan --json` report for one plan."""
    ws = waves(tasks)
    cp = critical_path(tasks)
    return {"critical_path": cp, "waves": ws, "width": max((len(w) for w in ws), default=0),
            "parallelism": round(len(tasks) / len(cp), 2) if cp else 0.0}


def serial_warning(tasks: list[Task]) -> str:
    """A warning when most waves have width 1 (the plan barely runs in parallel), else ""."""
    ws = waves(tasks)
    single = sum(1 for w in ws if len(w) == 1)
    if len(ws) >= 3 and single * 2 > len(ws):
        return f"{single} of {len(ws)} waves have width 1: freeze interfaces so more tasks can start at once"
    return ""
