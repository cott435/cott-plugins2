"""Route an upstream change to its owner's Revise (docs/routes.md), tick an owner's changes, or list the open ones."""
from __future__ import annotations

import json
import sys

from .. import routes


def add_arguments(parser):
    parser.add_argument("skill", nargs="?", choices=routes.OWNERS, help="the skill that owns the change")
    parser.add_argument("change", nargs="?", help="the change, e.g. 'stats.Cov needs a window field (PL-02.estimate)'")
    parser.add_argument("--from", dest="source", default="", help="the skill that found it")
    parser.add_argument("--done", metavar="SKILL", choices=routes.OWNERS,
                        help="tick every open change routed to SKILL (its Revise was approved)")
    parser.add_argument("--json", action="store_true", help="print the open changes as JSON")


def run(args, repo) -> int:
    if args.done:
        print(f"ticked: {routes.close(repo, args.done)} change(s) routed to {args.done}")
        return 0
    if args.skill:
        change = " ".join((args.change or "").split())
        if not change:
            print("dt route: say what the change is", file=sys.stderr)
            return 2
        routes.add(repo, args.skill, change, args.source)
        print(f"routed: {args.skill} · {change}")
        return 0
    open_ = [r for r in routes.routes(repo) if not r.done]
    if args.json:
        print(json.dumps([{"skill": r.skill, "change": r.change, "from": r.source, "date": r.date} for r in open_]))
    else:
        print("\n".join(f"{r.skill} · {r.change}" + (f" (from {r.source})" if r.source else "") for r in open_)
              or "routed: none")
    return 0
