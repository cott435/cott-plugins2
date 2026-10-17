"""Record a review finding under a checkpoint in tasks/plan.md, with the next free M<n>-R ID."""
from __future__ import annotations

import re

from .. import edit, md, model

SEVERITIES = ("Critical", "Important", "Suggestion", "Nit")   # agent-skills code-review-and-quality


def add_arguments(parser):
    parser.add_argument("checkpoint", help="task ID the checkpoint follows (M1-T04), or `exit` for the milestone exit")
    parser.add_argument("severity", help="Critical, Important, Suggestion or Nit")
    parser.add_argument("text", help="the finding, e.g. 'CR-21 · `rmt.py::clean_eigen` complexity 14'")
    parser.add_argument("--disposition", default="", help="fix task or reason, appended as `→ <disposition>`")


def _checkpoint(plan, which: str) -> model.Checkpoint | None:
    for cp in model.checkpoints(plan):
        if (which == "exit" and "exit" in cp.title.lower()) or (which != "exit" and cp.after == which):
            return cp
    return None


def run(args, repo) -> int:
    severity = next((s for s in SEVERITIES if s.lower() == args.severity.lower()), None)
    if severity is None:
        print(f"dt finding: severity must be one of {', '.join(SEVERITIES)}")
        return 2
    which = args.checkpoint if args.checkpoint == "exit" else args.checkpoint.upper()
    if which != "exit" and not re.fullmatch(md.TASK_ID, which):
        print(f"dt finding: checkpoint must be a task ID (M1-T04) or `exit`, not {args.checkpoint!r}")
        return 2
    text, disposition = " ".join(args.text.split()), " ".join(args.disposition.split())
    if not text:
        print("dt finding: empty finding text")
        return 2

    plan = repo.plan
    milestone = model.milestone_of(plan) if plan else None
    if not plan or not milestone:
        print("dt finding: tasks/plan.md has no active milestone")
        return 1
    cp = _checkpoint(plan, which)
    if cp is None:
        label = "milestone exit checkpoint" if which == "exit" else f"checkpoint after {which}"
        print(f"dt finding: tasks/plan.md has no {label}")
        return 1

    fid = repo.next_id(f"{milestone}-R")
    lines = edit.read_lines(plan.path)
    nl = edit.eol(lines)
    item = f"- {fid} {severity} · {text}" + (f" → {disposition}" if disposition else "") + nl

    f_line = md.field_line(plan.lines, cp.start + 1, cp.end, "Findings")
    if f_line is not None:
        at = f_line + 1           # after the label and any findings already listed under it
        while at < cp.end and re.match(r"^\s*[-*]\s+", plan.lines[at]):
            at += 1
        new = [item]
    else:
        at = cp.end               # after the checkpoint's last non-blank line
        while at > cp.start + 1 and not plan.lines[at - 1].strip():
            at -= 1
        new = ["**Findings:**" + nl, item]
    lines = edit.ensure_eol(lines) if at >= len(lines) else lines
    lines[at:at] = new
    edit.write_lines(plan.path, lines)
    repo.reload(plan.rel)
    print(fid)
    return 0
