"""`dt status --skill spec-writing` (replaces spec-status.sh): ideas ready to spec, ID prefixes, skills."""
from __future__ import annotations

from ..repo import Repo
from .common import Report, add_common, available_skills, fmt


def spec_writing(repo: Repo, r: Report) -> None:
    brief, spec = repo.doc("docs/brief.md"), repo.spec
    if not brief:
        r.mode("blocked", "no docs/brief.md (run idea-refine first)")
    else:
        r.mode("extend" if spec else "new")
    add_common(repo, r)
    r.add("ideas_ready", sorted(d.rel for d in repo.docs("idea") if d.status == "Accepted"))
    prefixes: dict[str, dict[str, str]] = {}
    if spec:
        found = {d.id.split("-")[0] for d in spec.definitions() if d.how == "requirement"}
        for p in sorted(found):
            ids = repo.ids_with_prefix(p)
            prefixes[p] = {"highest": ids[-1] if ids else "", "next": repo.next_id(p)}
    r.add("prefixes", prefixes, fmt([f"{v['highest']}→{v['next']}" for v in prefixes.values()]))
    r.add("skills", available_skills(repo))
