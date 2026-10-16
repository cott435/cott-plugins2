"""Record the milestone's base commit: set the active plan header's `**Base:**` to HEAD's short sha."""
from __future__ import annotations

import re

from .. import edit, git


def add_arguments(parser):
    parser.add_argument("--sha", help="record this commit instead of HEAD")


def run(args, repo) -> int:
    plan = repo.plan
    if plan is None or plan.header_line is None:
        print("dt base: no tasks/plan.md with a header line")
        return 1
    sha = args.sha or git.head_sha(repo.root)
    if not sha:
        print("dt base: not a git repo, or no commits yet")
        return 1
    lines = edit.read_lines(plan.path)
    raw = lines[plan.header_line]
    line = raw.rstrip("\r\n")
    if "**Base:**" in line:
        new = re.sub(r"\*\*Base:\*\*\s*[^·]*?(\s*·|\s*$)", lambda m: f"**Base:** {sha}{m.group(1)}", line, count=1)
    else:
        new = re.sub(r"(\*\*Status:\*\*[^·]*)", rf"\1· **Base:** {sha} ", line, count=1)
        if new == line:
            new = f"{line} · **Base:** {sha}"
    lines[plan.header_line] = new + raw[len(line):]
    edit.write_lines(plan.path, lines)
    print(f"Base: {sha}")
    return 0
