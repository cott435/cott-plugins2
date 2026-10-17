"""Tick (or untick) a task's checkbox in tasks/todo.md."""
from __future__ import annotations

import re
import sys

from .. import edit, md, model


def add_arguments(parser):
    parser.add_argument("task", help="task ID, e.g. M1-T03")
    parser.add_argument("--undo", action="store_true", help="untick instead")


def run(args, repo) -> int:
    if not re.fullmatch(md.TASK_ID, args.task):
        print(f"dt tick: {args.task!r} is not a task ID (M<n>-T<nn>)", file=sys.stderr)
        return 2
    todo = repo.todo
    if todo is None:
        print("dt tick: no tasks/todo.md", file=sys.stderr)
        return 1
    item = next((i for i in model.todo_items(todo) if i.id == args.task), None)
    if item is None:
        print(f"dt tick: {args.task} is not in tasks/todo.md", file=sys.stderr)
        return 1
    want = not args.undo
    verb = "ticked" if want else "unticked"
    if item.checked == want:
        print(f"{verb}: {args.task} (already)")
    else:
        _set_checkbox(todo.path, item.line, want)
        print(f"{verb}: {args.task}")
    if want:
        task = next((t for t in model.tasks(repo.plan) if t.id == args.task), None) if repo.plan else None
        pl = model.spine_pipeline(task, model.system_pipeline_ids(repo)) if task else None
        if pl:
            print(f"next: dt prebuild-clear {pl}")
    return 0


def _set_checkbox(path, line: int, checked: bool) -> None:
    """Rewrite one line's `[ ]`/`[x]`, keeping every other byte (and the line endings) as it was."""
    lines = edit.read_lines(path)
    lines[line] = re.sub(r"\[[ xX]\]", "[x]" if checked else "[ ]", lines[line], count=1)
    edit.write_lines(path, lines)
