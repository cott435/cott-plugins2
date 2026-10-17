"""Every task of the active plan that can start now, with its Writes:, so an orchestrator fans out in one turn."""
from __future__ import annotations

import json
import sys

from .. import graph, model
from .roadmap import active_plan


def add_arguments(parser):
    parser.add_argument("--json", action="store_true", help="print a JSON list")


def ready_rows(repo) -> list[dict] | None:
    """`[{id, title, kind, writes, part}]` for the active plan, or None when there is none. `part` is `task` (every
    dependency is ticked) or `tester` (a split task whose interface tasks are ticked: its tester half may start)."""
    plan = active_plan(repo)
    if plan is None:
        return None
    tasks = model.tasks(plan)
    done = {k for k, v in model.todo_state(repo).items() if v}
    by_id = {t.id: t for t in tasks}
    rows = []
    for part, ids in (("task", graph.ready(tasks, done)), ("tester", graph.tester_ready(tasks, done))):
        for i in ids:
            t = by_id[i]
            rows.append({"id": t.id, "title": t.title, "kind": t.kind, "writes": t.writes, "part": part})
    order = {t.id: n for n, t in enumerate(tasks)}
    return sorted(rows, key=lambda r: order[r["id"]])


def run(args, repo) -> int:
    rows = ready_rows(repo)
    if rows is None:
        print("dt ready: no active plan (tasks/plan.md)", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        what = ", ".join(x for x in (r["kind"], "tester half" if r["part"] == "tester" else "") if x)
        print(f"{r['id']}{f' [{what}]' if what else ''} {r['title']} · writes: {', '.join(r['writes']) or 'none'}")
    if not rows:
        print("ready: none")
    return 0
