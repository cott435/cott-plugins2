"""Record why this worktree's agent can't finish its half (TEST-WRONG, CONTRACT-CHANGE, NEEDS-DEP).

build-phase.md §6.4, §9. Run inside the worktree: TEST-WRONG (implementer: an intent test is wrong),
CONTRACT-CHANGE (the interface can't express what the task needs), NEEDS-DEP (a dependency isn't declared). The Stop gate then lets the agent stop; `dt land` rejects the
half as `escalated`, and it stays blocked until `dt build resolve <task>`."""
from __future__ import annotations

import sys

from .. import buildstate as bs


def add_arguments(parser):
    parser.add_argument("kind", type=str.upper, choices=bs.ESCALATIONS)
    parser.add_argument("why", help="one line: what is wrong and what would fix it")


def run(args, repo) -> int:
    try:
        state = bs.State(repo.root)
    except bs.GitError as e:
        print(f"dt escalate: needs git: {e}", file=sys.stderr)
        return 1
    claim = state.claim_for(repo.root)
    if claim is None:
        print("dt escalate: no claim for this worktree (run dt claim first)", file=sys.stderr)
        return 1
    if args.kind == "TEST-WRONG" and claim["role"] == "tester":
        print("dt escalate: TEST-WRONG is the implementer's: a tester rewrites its own tests", file=sys.stderr)
        return 2
    why = " ".join(args.why.split())
    state.write("escalations", claim["id"], {"claim": claim["id"], "task": claim["task"], "role": claim["role"],
                                             "kind": args.kind, "why": why, "time": bs.now()})
    state.log("escalate", claim=claim["id"], task=claim["task"], role=claim["role"], kind=args.kind, why=why)
    print(f"escalated: {claim['id']} {args.kind}. End now with one line: "
          f"STOPPED {claim['task']} {claim['role']}: see dt escalate")
    return 0
