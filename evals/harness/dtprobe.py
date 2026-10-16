#!/usr/bin/env python3
"""Facts the grader needs that `dt`'s CLI doesn't print as JSON, read through dt's own parser.

Runs against a given dt scripts/ folder (the plugin snapshot a trajectory used), so grading and the
run see the same parser. Prints one JSON object.

Usage: dtprobe.py <scripts-dir> <project-dir>
"""
import json, sys

sys.path.insert(0, sys.argv[1])
from devteam import md, model  # noqa: E402
from devteam.repo import Repo  # noqa: E402
from devteam.commands import roadmap as roadmap_cmd  # noqa: E402

try:  # dt's status internals move between versions; fall back to the §5.4 step 7 rule they implement.
    from devteam.status.build_planning import expected_mode  # noqa: E402
except ImportError:
    try:
        from devteam.commands.status import _expected_mode as expected_mode  # noqa: E402
    except ImportError:
        def expected_mode(t):
            if t.is_spine:
                return "solo"
            return "split" if t.covers or any(i.startswith("TC-") for i in t.read) else "solo"

repo = Repo(sys.argv[2])
live, removed = set(), set()
if repo.spec:
    for d in repo.spec.definitions():
        if d.how == "requirement":
            (removed if d.retired else live).add(d.id)
live -= removed


def plan_facts(doc):
    scope = md.fields_in(doc.lines, 0, len(doc.lines))
    return {
        "doc": doc.rel, "kind": doc.kind, "status": doc.status, "lines": len(doc.lines),
        "milestone": roadmap_cmd._plan_milestone(doc), "dev_team": model.is_dev_team_plan(doc),
        "covers": md.expand_refs(scope.get("Covers", "")), "deferred": md.expand_refs(scope.get("Deferred", "")),
        "tasks": [{"id": t.id, "title": t.title, "phase": t.phase, "is_spine": t.is_spine,
                   "spine_pipeline": model.spine_pipeline(t), "package": t.package, "step": t.step,
                   "size": t.size, "mode": t.mode, "expected_mode": expected_mode(t),
                   "reason": md.strip_md(t.get("Reason")), "read": t.read, "files_likely": t.files_likely,
                   "covers": t.covers, "blocked": t.blocked, "skills": getattr(t, "skills", [])}
                  for t in model.tasks(doc)],
    }


plans = [plan_facts(d) for d in sorted(repo.docs("plan", "queued-plan"), key=lambda d: d.rel)]
pipelines = [{"id": p.id, "doc": p.doc.rel, "doc_status": p.doc.status, "system": p.is_system,
              "package": p.package, "covers": p.covers,
              "steps": [{"name": s.name, "owner": s.owner, "covers": s.covers} for s in p.steps]}
             for p in model.all_pipelines(repo)]
rows = []
if repo.roadmap:
    for ms in model.milestones(repo.roadmap):
        rows.append({"id": ms.id, "name": ms.name, "source": md.strip_md(ms.source), "packages": ms.packages,
                     "pipelines": ms.pipelines, "derived": roadmap_cmd.milestone_status(repo, ms),
                     "skills": getattr(ms, "skills", []), "outline": md.strip_md(ms.fields.get("Outline", ""))})
# docs/references.md entries (dt versions before the references feature have none).
refs = [{"id": r.id, "title": r.title, "file": r.file, "hash": r.hash, "kind": r.kind, "milestones": r.milestones}
        for r in (model.all_references(repo) if hasattr(model, "all_references") else [])]
print(json.dumps({
    "live_spec": sorted(live), "removed_spec": sorted(removed),
    "pipelines": pipelines, "plans": plans, "roadmap": rows, "references": refs,
    "docs": {d.rel: d.status for d in sorted(repo.docs(), key=lambda d: d.rel)},
    "packages": repo.packages(),
}))
