"""What a skill needs before it starts: mode, upstream gates, gaps and next IDs. `--summary` for SessionStart.

The reports live in `devteam/status/`; this module is the CLI.
"""
from __future__ import annotations

import json

from ..status import SKILLS, report
from ..status.common import summary


def add_arguments(parser):
    parser.add_argument("--skill", choices=SKILLS, help="report what this skill needs")
    parser.add_argument("--summary", action="store_true", help="short session-start summary (always exits 0)")
    parser.add_argument("--json", action="store_true", help="print one JSON object")


def run(args, repo) -> int:
    if args.summary:
        try:
            lines = summary(repo)
        except Exception as e:   # SessionStart must never fail
            lines = [f"dt status: error: {type(e).__name__}: {e}"]
        if args.json:
            print(json.dumps({"summary": lines}))
        elif lines:
            print("\n".join(lines))
        return 0
    r = report(repo, args.skill)
    if args.json:
        print(json.dumps(r.values, indent=2))
    else:
        print(r.render())
    return 1 if r.values.get("mode") == "blocked" else 0
