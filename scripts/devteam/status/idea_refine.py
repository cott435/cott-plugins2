"""`dt status --skill idea-refine` (replaces idea-refine.sh): brief, ideas and roadmap rows."""
from __future__ import annotations

import re

from .. import md, model
from ..commands import roadmap as roadmap_cmd
from ..repo import Repo
from .common import Report, add_common, doc_state, fmt


def idea_refine(repo: Repo, r: Report) -> None:
    brief = repo.doc("docs/brief.md")
    r.mode("extend" if brief else "new")
    add_common(repo, r)
    r.add("brief_words", len(brief.text.split()) if brief else 0)
    r.add("brief_goals", _goal_count(brief.lines, brief.headings) if brief else 0)
    r.add("ideas", {d.rel: doc_state(d) for d in sorted(repo.docs("idea"), key=lambda d: d.rel)})
    rows = []
    if repo.roadmap:
        col = roadmap_cmd.status_table(repo.roadmap)
        for ms in model.milestones(repo.roadmap):
            rows.append({"id": ms.id, "name": ms.name, "source": md.strip_md(ms.source),
                         "status": md.strip_md(ms.row.get(col[1], "")) if col else ""})
    r.add("roadmap_rows", rows, fmt([f"{x['id']} {x['name']} [{x['source'] or '—'}]" for x in rows]))


def _goal_count(lines: list[str], headings: list[md.Heading]) -> int:
    """Numbered items under `## Goals` (bullets if none are numbered)."""
    h = next((h for h in headings if h.level == 2 and h.text.lower().startswith("goal")), None)
    if not h:
        return 0
    body = lines[h.line + 1:h.end]
    return len([x for x in body if re.match(r"^\d+[.)]\s", x)]) or len([x for x in body if re.match(r"^[-*]\s", x)])
