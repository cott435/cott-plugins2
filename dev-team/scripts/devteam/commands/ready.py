"""Every task of the active plan that can start now; with --halves or --reserve, the build's task halves.

Without flags: each task with its Writes:, so an orchestrator fans out in one turn. With --halves, --reserve or
--cap: the build's ready task halves and due reviews, as one JSON object (build-phase.md §6.1)."""
from __future__ import annotations

import json
import sys

from .. import buildstate as bs
from .. import dispatch, graph, model
from .roadmap import active_plan


def add_arguments(parser):
    parser.add_argument("--json", action="store_true", help="print a JSON list")
    parser.add_argument("--halves", action="store_true",
                        help="list ready task halves and due reviews as one JSON object (the build's view)")
    parser.add_argument("--reserve", action="store_true",
                        help="like --halves, and reserve each listed row so it is never listed twice")
    parser.add_argument("--cap", type=int, default=None,
                        help=f"at most N agents in flight, reservations and live claims counted "
                             f"(default {dispatch.DEFAULT_CAP}; implies --halves)")


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


def run_halves(args, repo) -> int:
    if active_plan(repo) is None:
        print("dt ready: no active plan (tasks/plan.md)", file=sys.stderr)
        return 1
    try:
        build = dispatch.Build(repo)
    except bs.GitError as e:
        print(f"dt ready: the build needs git: {e}", file=sys.stderr)
        return 1
    cap = dispatch.DEFAULT_CAP if args.cap is None else args.cap
    result = build.ready(cap)
    if args.reserve:
        for row in result["rows"]:
            build.state.write("reserved", row["claim"], {"id": row["claim"], "task": row["id"], "role": row["role"],
                                                         "time": bs.now(), **({"tasks": row["tasks"]}
                                                                              if row["role"] == "reviewer" else {})})
            build.state.log("reserve", claim=row["claim"], task=row["id"], role=row["role"])
        result["in_flight"] = build.state.in_flight()
    print(json.dumps(result, indent=2))
    return 0


def run(args, repo) -> int:
    if args.halves or args.reserve or args.cap is not None:
        return run_halves(args, repo)
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
