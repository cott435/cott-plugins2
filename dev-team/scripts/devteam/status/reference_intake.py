"""`dt status --skill reference-intake`: the reference files to read (new or changed), entries whose file is
gone, the next RF id, and the stages and milestones a file can be assigned to."""
from __future__ import annotations

from .. import md, model
from .. import references as refs
from ..repo import Repo
from .common import Report, add_common, doc_state, fmt


def reference_intake(repo: Repo, r: Report) -> None:
    state = refs.state(repo)
    if repo.references is None:
        r.mode("new" if state.unindexed else "current")
    else:
        r.mode("extend" if state.waiting else "current")
    add_common(repo, r)
    r.add("index", doc_state(repo.references))
    r.add("files_to_read", state.to_read)
    r.add("outline_first", [f for f in state.to_read
                            if f.endswith(".py") and refs.line_count(repo, f) > refs.INTAKE_OUTLINE_LINES])
    r.add("next_id", repo.next_id("RF"))
    rows = ([{"id": x.id, "name": x.name} for x in model.stages(repo.roadmap) + model.milestones(repo.roadmap)]
            if repo.roadmap else [])
    r.add("milestones", rows, fmt([f"{x['id']} {md.strip_md(x['name'])}" for x in rows]))
