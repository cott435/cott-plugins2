"""Record why this worktree's agent can't finish its half (TEST-WRONG, CONTRACT-CHANGE, NEEDS-DEP).

build-phase.md §6.4, §9. Run inside the worktree: TEST-WRONG (implementer: an intent test is wrong),
CONTRACT-CHANGE (the interface can't express what the task needs; `--type` names the contract symbol that falls
short), NEEDS-DEP (a dependency isn't declared). The Stop gate then lets the agent stop; `dt land` rejects the
half as `escalated`, and it stays blocked until `dt build resolve <task>`. Until then `dt ready` holds every half
for a NEEDS-DEP, and for a CONTRACT-CHANGE the halves of tasks reading `--type` and of the task's dependents (every
half when no type is given)."""
from __future__ import annotations

import sys

from .. import buildstate as bs
from .. import model


def add_arguments(parser):
    parser.add_argument("kind", type=str.upper, choices=bs.ESCALATIONS)
    parser.add_argument("why", help="one line: what is wrong and what would fix it")
    parser.add_argument("--type", dest="symbol", metavar="SYMBOL",
                        help="CONTRACT-CHANGE: the contract symbol that can't express what the task needs (risk.Drawdown)")


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
    symbol = None
    if args.symbol:
        if args.kind != "CONTRACT-CHANGE":
            print("dt escalate: --type names the contract symbol of a CONTRACT-CHANGE", file=sys.stderr)
            return 2
        known = {s.id for s in model.all_symbols(repo)}
        symbol = args.symbol.strip().strip("`")
        if symbol not in known:
            near = sorted(k for k in known if k.split(".")[-1].lower() == symbol.split(".")[-1].lower())
            print(f"dt escalate: {symbol} is not a contract symbol"
                  + (f" (did you mean {', '.join(near)}?)" if near else " (see docs/packages/*/contract.md)"),
                  file=sys.stderr)
            return 2
    why = " ".join(args.why.split())
    record = {"claim": claim["id"], "task": claim["task"], "role": claim["role"], "kind": args.kind, "why": why,
              "time": bs.now(), **({"type": symbol} if symbol else {})}
    state.write("escalations", claim["id"], record)
    state.log("escalate", claim=claim["id"], task=claim["task"], role=claim["role"], kind=args.kind, why=why,
              **({"type": symbol} if symbol else {}))
    print(f"escalated: {claim['id']} {args.kind}. End now with one line: "
          f"STOPPED {claim['task']} {claim['role']}: see dt escalate")
    return 0
