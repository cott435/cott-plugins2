"""`dt status --skill idea-refine` (replaces idea-refine.sh): brief, ideas and roadmap stage rows."""
from __future__ import annotations

from .. import md, model
from ..commands import roadmap as roadmap_cmd
from ..repo import Repo
from .common import Report, add_common, doc_state, fmt


def idea_refine(repo: Repo, r: Report) -> None:
    brief = repo.doc("docs/brief.md")
    r.mode("extend" if brief else "new")
    add_common(repo, r)
    r.add("brief_words", len(brief.text.split()) if brief else 0)
    r.add("brief_goals", model.goal_count(brief) if brief else 0)
    r.add("ideas", {d.rel: doc_state(d) for d in sorted(repo.docs("idea"), key=lambda d: d.rel)})
    rows = []
    if repo.roadmap:
        # Stages are idea-refine's rows. A roadmap from before stages has only milestone rows, each its own stage.
        stages = model.stages(repo.roadmap)
        first = "stage" if stages else "milestone"
        col = roadmap_cmd.status_table(repo.roadmap, first)
        for x in stages or [m for m in model.milestones(repo.roadmap) if not m.stage]:
            rows.append({"id": x.id, "name": x.name, "source": md.strip_md(x.source),
                         "status": md.strip_md(x.row.get(col[1], "")) if col else ""})
    r.add("roadmap_rows", rows, fmt([f"{x['id']} {x['name']} [{x['source'] or '—'}]" for x in rows]))
    r.add("references_unassigned", [e.id for e in model.all_references(repo) if not e.milestones])

