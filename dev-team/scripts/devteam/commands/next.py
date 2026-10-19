"""Name the next skill run and its mode, and why: a Draft waiting for approval, references or probes waiting, a
change routed to its owner, a user request its Approved doc doesn't honour, else the first planning skill with work
to do.

It reads the `dt status --skill` reports; their mode logic lives there. `/dev-team:plan` and the eval driver
start each run from this answer.
"""
from __future__ import annotations

import json
import re

from .. import model
from .. import probes as pb
from .. import references as refs
from .. import requests as rq
from .. import routes
from ..status import report
from ..status.common import milestone_row
from . import roadmap as roadmap_cmd

ORDER = ["idea-refine", "spec-writing", "architecture-design", "pipeline-design", "test-planning", "build-planning",
         "build-setup"]
# The skill whose gate a Draft doc waits at, by doc kind.
OWNER = {"brief": "idea-refine", "idea": "idea-refine", "spec": "spec-writing", "architecture": "architecture-design",
         "package-architecture": "architecture-design", "contract": "architecture-design",
         "pipelines": "pipeline-design", "tests": "test-planning", "references": "reference-intake",
         "probes": "api-probe", "constraints": "build-setup", "plan": "build-planning",
         "queued-plan": "build-planning"}
DRAFT = ("Draft", "Proposed")
IDLE = ("blocked", "current")


def add_arguments(parser):
    parser.add_argument("--skip", action="append", default=[], choices=["test-planning"],
                        help="leave out an optional skill the user declined")
    parser.add_argument("--json", action="store_true",
                        help="print {skill, mode, reason, waiting_on_user} (plus packages, for a per-package skill)")


def decide(repo, skip=()) -> dict:
    drafts = sorted((d for d in repo.docs() if (d.status or "") in DRAFT and d.kind in OWNER),
                    key=lambda d: (_rank(OWNER[d.kind]), d.rel))
    if drafts:
        owner = OWNER[drafts[0].kind]
        rels = [d.rel for d in drafts if OWNER[d.kind] == owner]
        return _out(owner, "gate", f"{', '.join(rels)} {'is' if len(rels) == 1 else 'are'} "
                    f"{drafts[0].status}: answer its questions or approve it", True)
    if repo.roadmap and refs.state(repo).waiting:     # intake assigns each file to a stage, so stages come first
        return _from_report(repo, "reference-intake", "reference files waiting in references/")
    if pb.state(repo).waiting:
        return _from_report(repo, "api-probe", "probes cited with no entry, or results waiting to be recorded")
    for owner in routes.OWNERS:
        changed = routes.open_for(repo, owner)
        if changed:
            return _from_report(repo, owner, f"routed to its owner: {'; '.join(changed)}")
    for owner, skill in rq.OWNERS.items():
        due = rq.due(repo, owner)
        if due:
            return _from_report(repo, skill, f"the user's words, not yet honoured: {'; '.join(map(rq.label, due))}")
    for skill in ORDER:
        if skill in skip:
            continue
        r = report(repo, skill).values
        mode = r["mode"]
        if skill == "idea-refine":
            if mode == "new" or r["docs"]["roadmap"] == "missing":
                return _out(skill, mode, "no brief yet" if mode == "new" else "the brief has no roadmap stages")
        elif skill == "spec-writing":
            if mode == "new" or (mode != "blocked" and r["ideas_ready"]):
                why = "no spec yet" if mode == "new" else f"accepted ideas to spec: {', '.join(r['ideas_ready'])}"
                return _out(skill, mode, why)
        elif skill == "test-planning":
            # Optional: a project that reached a build plan with no tests.md anywhere skipped it.
            skipped = not repo.docs("tests") and (repo.plan or repo.docs("queued-plan", "archived-plan", archive=True))
            units, scope = _test_scope(repo)
            pkgs = {p: m for p, m in r["packages"].items() if m == "revise" or scope is None or p in scope}
            home = {p.id: p.package for p in model.all_pipelines(repo)}
            untested = sorted(i for i in set(r["pipelines_no_smoke"]) & set(r["pipelines_no_golden"])
                              if scope is None or home.get(i) in scope)
            mode = next((m for m in ("new", "revise", "extend") if m in pkgs.values()), "current")
            if not skipped and (mode in ("new", "revise") or (mode == "extend" and untested)):
                what = "golden cases and test strategy" + (f" for {', '.join(units)}" if scope is not None else "")
                return _per_package(skill, {**r, "mode": mode, "packages": pkgs}, what + " (optional)"
                                    + (f"; pipelines with no tests: {', '.join(untested)}" if untested else ""))
        elif skill == "build-planning" and mode == "blocked":
            if r["probes_blocking"]:
                return _out("api-probe", "waiting", f"build-planning waits for probes: {', '.join(r['probes_blocking'])}"
                            ": run their checks, then say so", True)
            if "run pipeline-design" in (r["blocked"] or ""):
                pd = report(repo, "pipeline-design").values
                return _out("pipeline-design", pd["mode"] if pd["mode"] not in IDLE else "extend",
                            f"build-planning is blocked: {r['blocked']}",
                            packages=[p for p, m in pd["packages"].items() if m != "current"])
            return _out(skill, "blocked", r["blocked"], True)
        elif skill == "build-planning" and mode == "extend" and r["milestone"] != "none" and r["stage_to_cut"] == "none":
            continue    # mid-milestone, the next milestone's plan is queued only when the user asks for it
        elif skill == "pipeline-design":
            # A component on no step is a gap the gate lets stand with a reason; a spec ID on no pipeline is work.
            if mode not in IDLE and (mode != "extend" or r["uncovered_ids"]):
                # A stage's ID on no component is shown with its stages and the decisions that meet it.
                staged = {s.split(" ")[0]: s for s in r["stage_ids_unplaced"]}
                ids = [staged.get(i, i) for i in r["uncovered_ids"]]
                why = f"spec IDs on no pipeline: {', '.join(ids)}" if ids else ""
                return _per_package(skill, r, why or "pipelines to design")
        elif mode not in IDLE:
            return _out(skill, mode, _why(skill, r))
    return _out(None, "done", "every planning skill is current: build the active milestone (/build), "
                "or bring a new idea to idea-refine", True)


def _test_scope(repo) -> tuple[list[str], set[str] | None]:
    """(units, packages) that optional test-planning covers: the active milestone's and the next unit
    build-planning plans (a milestone, or a stage to cut); a later milestone's packages wait until it comes next.
    Packages are a unit's Packages cell, its pipelines' packages (a brief stage's are those of its features,
    `roadmap.staged_pipelines`) and those of package pipelines Part of its system pipelines. (_, None), every
    package, when the project has no roadmap unit to scope by."""
    active = roadmap_cmd.active_plan(repo)
    units = [u for u in (milestone_row(repo, model.milestone_of(active)) if active else None,
                         roadmap_cmd.next_unit(repo)) if u is not None]
    by_id = {p.id: p for p in model.all_pipelines(repo)}
    pkgs: set[str] = set()
    for u in units:
        staged = roadmap_cmd.staged_pipelines(repo, u) if isinstance(u, model.Stage) else None
        pls = set(roadmap_cmd.milestone_pipelines(repo, u)[0] if staged is None else staged)
        pkgs |= set(getattr(u, "packages", []))
        pkgs |= {p.package for p in by_id.values() if p.package and (p.id in pls or set(
            re.findall(r"PL-\d{2,}", p.fields.get("Part of", ""))) & pls)}
    names = list(dict.fromkeys(u.id for u in units))
    return (names, pkgs) if pkgs else (names, None)


def _rank(skill: str) -> int:
    return ORDER.index(skill) if skill in ORDER else -1     # reference-intake and api-probe come first


def _out(skill, mode, reason, waiting=False, packages=None) -> dict:
    out = {"skill": skill, "mode": mode, "reason": reason, "waiting_on_user": waiting}
    if packages:
        out["packages"] = packages
    return out


def _from_report(repo, skill: str, reason: str) -> dict:
    r = report(repo, skill).values
    return _out(skill, r["mode"], reason, r["mode"] == "blocked")


def _per_package(skill: str, r: dict, what: str) -> dict:
    pkgs = {p: m for p, m in r["packages"].items() if m not in IDLE}
    shown = ", ".join(f"{p} ({m})" for p, m in pkgs.items())
    return _out(skill, r["mode"], f"{what}: {shown}" if shown else what, packages=list(pkgs))


# The report keys that say why a skill has work, by skill.
WHY = {"architecture-design": ("uncovered", "changed_since", "contracts_missing", "legacy_layout", "probes_answered"),
       "build-planning": ("stage_to_cut", "blocked_tasks", "changed_since_plan", "interfaces_changed", "queued"),
       "build-setup": ("config_mismatches", "agents_missing", "hooks_missing")}


def _why(skill: str, r: dict) -> str:
    parts = [f"{k} {', '.join(map(str, v)) if isinstance(v, list) else v}" for k in WHY.get(skill, ())
             if (v := r.get(k)) and v != "none"]
    return f"{skill} reports {r['mode']}" + (f": {'; '.join(parts)}" if parts else "")


def run(args, repo) -> int:
    out = decide(repo, args.skip)
    if args.json:
        print(json.dumps(out))
        return 0
    print(f"next: {out['skill'] or 'none'} ({out['mode']})")
    if out.get("packages"):
        print(f"packages: {', '.join(out['packages'])}")
    print(f"reason: {out['reason']}")
    print(f"waiting on user: {'yes' if out['waiting_on_user'] else 'no'}")
    if out["skill"]:
        print(f"run: /dev-team:{out['skill']}")
    return 0
