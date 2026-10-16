"""Archive a finished milestone: plan + todo to tasks/archive/, a between-milestones stub plan, the roadmap outcome."""
from __future__ import annotations

import datetime
import re

from .. import edit, model


def add_arguments(parser):
    parser.add_argument("--date", default=None, help="date to record (YYYY-MM-DD; default today)")


def _name(title: str) -> str:
    """`M1: Data + stats — Plan` → `Data + stats`."""
    t = re.sub(r"^M\d+\s*:\s*", "", title or "")
    return re.sub(r"\s*[—–-]+\s*plan\s*$", "", t, flags=re.I).strip()


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "plan"


def _todo_body(lines: list[str]) -> list[str]:
    """The todo's lines after its H1, leading blank lines dropped."""
    i = next((n + 1 for n, line in enumerate(lines) if line.startswith("# ")), 0)
    while i < len(lines) and not lines[i].strip():
        i += 1
    return lines[i:]


def _roadmap_lines(roadmap, milestone: str, name: str, date: str, archive_rel: str) -> list[str] | None:
    """The roadmap with `**Outcome:** Done <date>` added to the milestone's section (and its Plan link pointed
    at the archive). None if there is nothing to change."""
    lines = edit.read_lines(roadmap.path)
    nl = edit.eol(lines)
    outcome = f"**Outcome:** Done {date}{nl}"
    m = next((m for m in model.milestones(roadmap) if m.id == milestone), None)
    if m is None or m.section is None:          # no section yet: add one at the end
        title = name or (m.name if m else "") or milestone
        return edit.ensure_eol(lines) + [nl, f"## {milestone}: {title}{nl}", outcome]
    h = m.section
    changed = False
    for i in range(h.line + 1, h.end):
        if "**Plan:**" in lines[i] and "tasks/plan.md" in lines[i]:
            lines[i] = lines[i].replace("tasks/plan.md", archive_rel)
            changed = True
    if "Outcome" not in m.fields:
        at = h.line + 1               # after the section's first block of lines
        while at < h.end and roadmap.lines[at].strip():
            at += 1
        if at >= len(lines):
            lines = edit.ensure_eol(lines)
        lines[at:at] = [outcome]
        changed = True
    return lines if changed else None


def run(args, repo) -> int:
    date = args.date or datetime.date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        print(f"dt archive: bad --date {date!r} (YYYY-MM-DD)")
        return 2
    plan, todo = repo.plan, repo.todo
    milestone = model.milestone_of(plan) if plan else None
    if not plan or not milestone or (plan.status or "").lower().startswith("between"):
        print("dt archive: no active milestone plan in tasks/plan.md; nothing to archive")
        return 1
    items = model.todo_items(todo) if todo else []
    if not items:
        print("dt archive: tasks/todo.md has no task items; refusing to archive")
        return 1
    open_items = [i.id for i in items if not i.checked]
    if open_items:
        print(f"dt archive: refused, unchecked in tasks/todo.md: {', '.join(open_items)}")
        return 1

    name = _name(plan.title)
    archive_rel = f"tasks/archive/{milestone}-{_slug(name)}.md"
    archive_path = repo.root / archive_rel
    if archive_path.exists():
        print(f"dt archive: {archive_rel} already exists; refusing to overwrite")
        return 1

    # 1. Archive copy: the plan byte for byte, then the todo as a final `## Todo` section.
    plan_lines = edit.ensure_eol(edit.read_lines(plan.path))
    nl = edit.eol(plan_lines)
    todo_lines = edit.ensure_eol(_todo_body(edit.read_lines(todo.path)))
    edit.write_lines(archive_path, plan_lines + [nl, f"## Todo{nl}", nl] + todo_lines)

    # 2. Roadmap outcome line.
    roadmap = repo.roadmap
    if roadmap:
        new = _roadmap_lines(roadmap, milestone, name, date, archive_rel)
        if new is not None:
            edit.write_lines(roadmap.path, new)

    # 3. Empty todo, then the stub plan (replaced in place, so tasks/plan.md is never missing).
    edit.write_text(todo.path, f"# Todo{nl}")
    link = plan.header.get("Roadmap") or "[../docs/roadmap.md](../docs/roadmap.md)"
    archived = archive_rel.split("tasks/", 1)[1]
    edit.write_text(plan.path, f"# Between milestones{nl}{nl}"
                               f"**Status:** Between milestones · **Last updated:** {date} · **Roadmap:** {link}{nl}{nl}"
                               f"{milestone} is archived at [{archived}]({archived}). "
                               f"`build-planning` writes the next plan.{nl}")
    for rel in (archive_rel, plan.rel, todo.rel) + ((roadmap.rel,) if roadmap else ()):
        repo.reload(rel)
    print(archive_rel)
    return 0
