"""Upstream changes a skill found and left to their owner's Revise: `docs/routes.md`, one checkbox per change,
written and ticked only by `dt route`. `dt status` reports a skill's open changes as `routed_changes`, and
`dt next` sends the next run to that owner."""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass

from . import edit, md
from .repo import Repo

PATH = "docs/routes.md"
# The skills a change can be routed to: each has a mode that edits its Approved docs (spec-writing's is Extend).
OWNERS = ("spec-writing", "architecture-design", "pipeline-design", "test-planning")
HEADER = ("# Routed changes\n\n"
          "Changes a skill found that another skill owns, waiting for the owner's Revise. Written by `dt route`; "
          "the owner ticks its items (`dt route --done <skill>`) when the user approves that Revise.\n\n")
ITEM = re.compile(r"^(?P<skill>[a-z-]+) · (?P<change>.*?)(?: \(from (?P<source>[a-z-]+), (?P<date>[\d-]+)\))?$")


@dataclass
class Route:
    line: int
    done: bool
    skill: str
    change: str
    source: str
    date: str


def routes(repo: Repo) -> list[Route]:
    doc = repo.doc(PATH)
    if doc is None:
        return []
    out = []
    for cb in md.checkboxes(doc.lines, 0, len(doc.lines)):
        m = ITEM.match(cb.text)
        if m:
            out.append(Route(cb.line, cb.checked, m["skill"], m["change"], m["source"] or "", m["date"] or ""))
    return out


def open_for(repo: Repo, skill: str) -> list[str]:
    """The skill's open changes, `<change> (from <skill>)`."""
    return [r.change + (f" (from {r.source})" if r.source else "") for r in routes(repo)
            if r.skill == skill and not r.done]


def add(repo: Repo, skill: str, change: str, source: str = "", date: str | None = None) -> None:
    path = repo.root / PATH
    date = date or datetime.date.today().isoformat()
    item = f"- [ ] {skill} · {change}" + (f" (from {source}, {date})" if source else "")
    if path.is_file():
        lines = edit.ensure_eol(edit.read_lines(path))
        lines.append(item + edit.eol(lines))
        edit.write_lines(path, lines)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        edit.write_text(path, HEADER + item + "\n")
    repo.reload(PATH)


def close(repo: Repo, skill: str) -> int:
    """Tick every open change routed to `skill`; returns how many."""
    todo = [r for r in routes(repo) if r.skill == skill and not r.done]
    if todo:
        path = repo.root / PATH
        lines = edit.read_lines(path)
        for r in todo:
            lines[r.line] = re.sub(r"\[ \]", "[x]", lines[r.line], count=1)
        edit.write_lines(path, lines)
        repo.reload(PATH)
    return len(todo)
