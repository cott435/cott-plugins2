"""Record the user's words in docs/requests.md and trace them: add a request, trace it to the IDs that honour it,
record a change the user approved, or list them."""
from __future__ import annotations

import dataclasses
import json
import re
import sys

from .. import requests as rq

USAGE = ('dt request add <owner> "<words>" --skill S [--about TEXT] [--replaces UR-NN] · '
         "dt request trace UR-NN ID… · "
         'dt request change UR-NN "<what instead>" --approved "<words>" --skill S · '
         "dt request [list] [--open] [--owner O] [--json]")


def add_arguments(parser):
    parser.add_argument("action", nargs="?", default="list", choices=["add", "trace", "change", "list"])
    parser.add_argument("args", nargs="*", help="add: owner and words; trace: UR-NN and IDs; change: UR-NN and what")
    parser.add_argument("--skill", help="the skill that heard the words (add) or the approval (change)")
    parser.add_argument("--about", default="", help="add: what the words answer, when they don't say it themselves")
    parser.add_argument("--replaces", metavar="UR-NN", help="add: an earlier request these words replace")
    parser.add_argument("--approved", help="change: the user's words approving the change")
    parser.add_argument("--owner", choices=list(rq.OWNERS), help="list: only this owner's requests")
    parser.add_argument("--open", action="store_true", help="list: only requests nothing honours yet")
    parser.add_argument("--json", action="store_true", help="list: print JSON")


def _fail(msg: str) -> int:
    print(f"dt request: {msg}\nusage: {USAGE}", file=sys.stderr)
    return 2


def _one_line(text: str) -> str:
    text = " ".join(text.split())
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    return text


def _find(repo, id_: str):
    return next((r for r in rq.all_requests(repo) if r.id == id_), None)


def run(args, repo) -> int:
    return {"add": _add, "trace": _trace, "change": _change, "list": _list}[args.action](args, repo)


def _add(args, repo) -> int:
    if len(args.args) < 2 or args.args[0] not in rq.OWNERS:
        return _fail(f"add needs an owner ({', '.join(rq.OWNERS)}) and the user's words")
    if not args.skill or not re.fullmatch(r"[a-z-]+", args.skill):
        return _fail("add needs --skill (the skill that heard the words, e.g. idea-refine)")
    words = _one_line(" ".join(args.args[1:]))
    if not words:
        return _fail("add needs the user's words")
    old = _find(repo, args.replaces) if args.replaces else None
    if args.replaces and old is None:
        return _fail(f"{args.replaces} is not in {rq.PATH}")
    r = rq.add(repo, args.args[0], words, args.skill, _one_line(args.about).replace("[", "(").replace("]", ")"))
    if old is not None:
        rq.set_trace(repo, _find(repo, old.id), f"superseded by {r.id}")
    print(f"{r.id} {r.owner}: \"{r.words}\"" + (f" (replaces {old.id})" if old else ""))
    return 0


def _trace(args, repo) -> int:
    if len(args.args) < 2:
        return _fail("trace needs a UR-NN and the IDs that honour it")
    r = _find(repo, args.args[0])
    if r is None:
        return _fail(f"{args.args[0]} is not in {rq.PATH}")
    if r.state in ("changed", "superseded"):
        return _fail(f"{r.id} is {r.state} ({r.trace}); its record stays")
    new = [i.strip(",") for i in args.args[1:]]
    unknown = [i for i in new if repo.lookup(i, archive=False) is None]
    if unknown:
        return _fail(f"not defined: {', '.join(unknown)}")
    # IDs traced earlier that no longer resolve or are retired drop out; the rest stay.
    kept = [i for i in r.honoured_by if (d := repo.lookup(i, archive=False)) is not None and not d.retired]
    ids = list(dict.fromkeys(kept + new))
    if not rq.honouring(repo, dataclasses.replace(r, honoured_by=ids)):
        kinds = ", ".join(rq.HONOUR_KINDS[r.owner])
        return _fail(f"{r.id} ({r.owner}) needs a live ID defined in {kinds}")
    rq.set_trace(repo, r, ", ".join(ids))
    print(f"{r.id} → {r.trace}")
    return 0


def _change(args, repo) -> int:
    if len(args.args) < 2 or not args.approved or not re.fullmatch(r"[a-z-]+", args.skill or ""):
        return _fail('change needs a UR-NN, what was done instead, --approved "<the user\'s words>" and --skill')
    r = _find(repo, args.args[0])
    if r is None:
        return _fail(f"{args.args[0]} is not in {rq.PATH}")
    if r.state == "superseded":
        return _fail(f"{r.id} is {r.trace}: change that one")
    what = _one_line(" ".join(args.args[1:]))
    rq.set_trace(repo, r, rq.changed_trace(what, _one_line(args.approved), args.skill))
    print(f"{r.id} → {_find(repo, r.id).trace}")
    return 0


def _list(args, repo) -> int:
    if args.args:
        return _fail("list takes no arguments")
    items = [r for r in rq.all_requests(repo) if args.owner is None or r.owner == args.owner]
    state = {r.id: ("open" if rq.is_open(repo, r) else r.state) for r in items}
    if args.open:
        items = [r for r in items if state[r.id] == "open"]
    if args.json:
        print(json.dumps([{"id": r.id, "owner": r.owner, "words": r.words, "about": r.about, "skill": r.skill,
                           "date": r.date, "state": state[r.id], "trace": r.trace} for r in items]))
        return 0
    print("\n".join(f"{rq.label(r)} · {r.owner}" + (" · open" if state[r.id] == "open" else "")
                    + (f" → {r.trace}" if r.trace else "") for r in items) or "requests: none")
    return 0
