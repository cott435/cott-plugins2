"""`dt status --skill build-planning`: the active milestone, its coverage and task rules, and the mode
(new · extend · replan · advance · foreign · current · blocked). The next unit to plan is a milestone, or a
stage with no milestone rows yet (`stage_to_cut`), whose pipelines are inferred from its Source
(`roadmap.milestone_pipelines`) and printed as `pipelines_inferred` for build-planning to divide."""
from __future__ import annotations

import re

from .. import md, model
from ..commands import roadmap as roadmap_cmd
from ..repo import Doc, Repo
from .common import (OWN_SKILLS, Report, add_common, advance_ready, available_skills, blocked_reason,
                     live_spec_ids, milestone_row, next_task, plan_base)
from .packages import drift, grow_triggers, stale_contracts


def expected_mode(task: model.Task) -> str:
    """The build-mode rule: solo for spine tasks, split for behaviour with a checkable outcome, else solo."""
    if task.is_spine:
        return "solo"
    return "split" if task.covers or any(i.startswith("TC-") for i in task.read) else "solo"


def mode_violations(tasks: list[model.Task]) -> list[str]:
    out = []
    for t in tasks:
        want = expected_mode(t)
        if t.mode in ("split", "solo") and t.mode != want and not md.strip_md(t.get("Reason")):
            why = "spine" if t.is_spine else "covers behaviour" if want == "split" else "no checkable outcome"
            out.append(f"{t.id}: {t.mode}, expected {want} ({why})")
    return out


def uncovered(repo: Repo, plan: Doc, tasks: list[model.Task], pipelines: list[str]) -> list[str]:
    """The milestone's spec IDs (Scope Covers plus its pipelines' Covers) on no task and not Deferred."""
    live, _ = live_spec_ids(repo)
    scope = md.fields_in(plan.lines, 0, len(plan.lines))
    wanted = set(md.expand_refs(scope.get("Covers", "")))
    for p in model.all_pipelines(repo):
        if p.id in pipelines:
            wanted |= set(p.covers)
            for s in p.steps:
                wanted |= set(s.covers)
    on_tasks = {c for t in tasks for c in t.covers}
    deferred = set(md.expand_refs(scope.get("Deferred", "")))
    left = wanted - on_tasks - deferred
    return sorted(left & live if live else left)


def skills_missing(plan: Doc | None, tasks: list[model.Task], available: list[str],
                   milestone_skills: list[str] = ()) -> list[str]:
    referenced = list(milestone_skills)
    if plan:
        scope_skills = md.fields_in(plan.lines, 0, len(plan.lines)).get("Skills", "")
        referenced += [md.strip_md(s).split(" (")[0].strip() for s in md.split_list(scope_skills)]
        for t in tasks:
            referenced += t.skills
    return sorted({s for s in referenced if s and s not in ("—", "-", "none")
                   and s not in available and s not in OWN_SKILLS})


def planned_milestones(repo: Repo) -> list[tuple[str, list[model.Task]]]:
    """(milestone, its tasks) for the active plan and each queued plan."""
    out = []
    active = roadmap_cmd.active_plan(repo)
    if active:
        out.append((model.milestone_of(active), model.tasks(active)))
    for d in sorted(repo.docs("queued-plan"), key=lambda d: d.rel):
        mid = roadmap_cmd._plan_milestone(d)
        if mid:
            out.append((mid, model.tasks(d)))
    return out


def unrouted(repo: Repo) -> tuple[list[str], list[str]]:
    """(references, skills) of each planned milestone that no task carries: an RF ID in no task's `Read:`
    (selector ignored), a roadmap `**Skills:**` skill on no task's `**Skills:**`. Items read `RF-01 (M2)`."""
    refs_out, skills_out = [], []
    for mid, tasks in planned_milestones(repo):
        read = {model.split_ref(md.strip_md(i.split(" (")[0]))[0] for t in tasks for i in t.read}
        on_tasks = {s for t in tasks for s in t.skills}
        refs_out += [f"{rid} ({mid})" for rid in model.milestone_references(repo, mid) if rid not in read]
        row = milestone_row(repo, mid)
        skills_out += [f"{s} ({mid})" for s in (row.skills if row else []) if s not in on_tasks]
    return refs_out, skills_out


def stage_unrouted(repo: Repo) -> list[str]:
    """For each cut stage: a stage skill on none of its milestones' Skills, or a reference assigned to the
    stage that none of its milestones serves. Items read `data-analysis (S1)`, `RF-02 (S1)`."""
    if not repo.roadmap:
        return []
    out = []
    for st in model.stages(repo.roadmap):
        mss = model.stage_milestones(repo.roadmap, st.id)
        if not mss:
            continue
        on = {s for m in mss for s in m.skills}
        served = {r for m in mss for r in model.milestone_references(repo, m.id)}
        out += [f"{s} ({st.id})" for s in st.skills if s not in on]
        out += [f"{r} ({st.id})" for r in model.milestone_references(repo, st.id) if r not in served]
    return out


def draft_pipelines(repo: Repo, tasks: list[model.Task], pipelines: list[str]) -> list[str]:
    """The milestone's and the tasks' pipelines whose doc is back to Draft."""
    ids = set(pipelines) | {m.group(0) for t in tasks if (m := re.match(r"PL-\d{2,}", t.step))}
    out = []
    for pid in sorted(ids):
        d = repo.lookup(pid, archive=False)
        if d and not d.retired and (d.doc.status or "") == "Draft":
            out.append(pid)
    return out


def _has_unchecked(doc: Doc) -> bool:
    return any(not cb.checked for cb in md.checkboxes(doc.lines, 0, len(doc.lines)))


def _date(value: str | None) -> str | None:
    m = re.search(r"\d{4}-\d{2}-\d{2}", value or "")
    return m.group(0) if m else None


def milestone_packages(repo: Repo, row: model.Milestone | None, pipelines: list[str],
                       tasks: list[model.Task]) -> list[str]:
    """The active milestone's packages: its roadmap row's Packages, its pipelines' packages and its tasks'."""
    pkgs = set(row.packages if row else [])
    by_id = {p.id: p for p in model.all_pipelines(repo)}
    pkgs |= {by_id[i].package for i in pipelines if i in by_id and by_id[i].package}
    pkgs |= {t.package for t in tasks if t.package and t.package not in ("—", "-")}
    return sorted(pkgs)


def revising(repo: Repo, pkgs: list[str], drafts: list[str]) -> list[str]:
    """Docs a Revise round has open: Draft pipelines.md/tests.md of the milestone's packages, plus any doc
    that defines a Draft milestone or task pipeline (a system pipeline's architecture.md)."""
    out = [d.rel for pkg in pkgs for n in ("pipelines", "tests")
           if (d := repo.package_doc(pkg, n)) and (d.status or "") == "Draft"]
    for pid in drafts:
        d = repo.lookup(pid, archive=False)
        if d and d.doc.rel not in out:
            out.append(d.doc.rel)
    return out


def changed_since_plan(repo: Repo, plan: Doc, pkgs: list[str]) -> list[str]:
    """The milestone packages' Approved pipelines.md, tests.md and contract.md whose `Last updated` date is
    later than the plan's (same-day changes aren't seen; empty when the plan has no date)."""
    since = _date(plan.last_updated)
    if not since:
        return []
    return [d.rel for pkg in pkgs for n in ("pipelines", "tests", "contract")
            if (d := repo.package_doc(pkg, n)) and (d.status or "").startswith("Approved")
            and (_date(d.last_updated) or "") > since]


def build_planning(repo: Repo, r: Report) -> None:
    plan = repo.plan
    active = roadmap_cmd.active_plan(repo)
    tasks = model.tasks(active) if active else []
    items = model.todo_items(repo.todo) if active and repo.todo else []
    mid = model.milestone_of(active) if active else None
    ms_row = milestone_row(repo, mid)
    milestone_pls = ([p for p in roadmap_cmd.milestone_pipelines(repo, ms_row)[0] if not repo.is_retired(p)]
                     if active and ms_row else [])

    blocked_tasks = [f"{t.id} ({blocked_reason(t)})" for t in tasks if blocked_reason(t)]
    by_id = {t.id: t for t in tasks}
    nxt = next_task(items, by_id)
    spined = {model.spine_pipeline(t) for t in tasks}
    for doc in repo.docs("archived-plan", archive=True):
        spined |= {model.spine_pipeline(t) for t in model.tasks(doc)}
    drafts = draft_pipelines(repo, tasks, milestone_pls)
    pkgs = milestone_packages(repo, ms_row, milestone_pls, tasks) if active else []
    open_revise = revising(repo, pkgs, drafts) if active else []
    changed = changed_since_plan(repo, active, pkgs) if active else []
    queued = sorted(f"{roadmap_cmd._plan_milestone(d) or '?'} ({d.rel})" for d in repo.docs("queued-plan"))
    available = available_skills(repo)

    # The next milestone that still needs a plan, or the next stage that still needs cutting into milestones.
    target = roadmap_cmd.next_unit(repo)
    blocked, focus = None, ms_row if active else None   # focus: the milestone this run plans or replans
    if plan is not None and not model.is_dev_team_plan(plan) and _has_unchecked(plan):
        mode = "foreign"
    elif active:
        if advance_ready(repo, active):
            mode = "advance"
        elif open_revise:
            mode = "blocked"
            blocked = f"waiting for {', '.join(open_revise)} approval (Revise in progress)"
        elif blocked_tasks or changed:
            mode = "replan"
        elif target and roadmap_cmd.pipelines_approved(repo, target):
            mode, focus = "extend", target
        else:
            mode = "current"
    elif queued:
        mode = "extend"
    elif target is not None:
        focus = target
        if roadmap_cmd.pipelines_approved(repo, target):
            never_planned = plan is None and not repo.docs("archived-plan", archive=True)
            mode = "new" if never_planned else "extend"
        else:
            mode = "blocked"
            pls, inferred = roadmap_cmd.milestone_pipelines(repo, target)
            listed = ", ".join(pls) or ("none inferred from its Source" if inferred else "none listed")
            blocked = f"{target.id} pipelines not all Approved ({listed}); run pipeline-design"
    elif repo.roadmap is None:
        if any(d.status == "Approved" for d in repo.docs("pipelines")):
            mode = "new"
        else:
            mode, blocked = "blocked", "no Approved pipelines.md (run pipeline-design)"
    else:
        mode = "current"
    inferred_pls: list[str] = []
    if focus is not None:
        pls, inferred = roadmap_cmd.milestone_pipelines(repo, focus)
        inferred_pls = pls if inferred else []
    focus_skills = focus.skills if focus is not None else []
    refs_unrouted, skills_unrouted = unrouted(repo)

    r.mode(mode, blocked)
    add_common(repo, r)
    r.add("milestone", f"{mid} {active.status or 'no status'}" if active else "none")
    r.add("progress", f"{sum(1 for i in items if i.checked)}/{len(items)}")
    r.add("next_task", f"{nxt.id} {by_id[nxt.id].title if nxt.id in by_id else nxt.text}" if nxt else "none")
    r.add("blocked_tasks", blocked_tasks)
    r.add("uncovered", uncovered(repo, active, tasks, milestone_pls) if active else [])
    r.add("no_spine", [p for p in milestone_pls if p not in spined])
    r.add("mode_violations", mode_violations(tasks))
    r.add("draft_pipelines", drafts)
    r.add("changed_since_plan", changed)
    r.add("stage_to_cut", f"{focus.id} {focus.name}" if isinstance(focus, model.Stage) else "none")
    r.add("pipelines_inferred", inferred_pls)
    r.add("milestone_references", model.milestone_references(repo, focus.id) if focus is not None else [])
    r.add("milestone_skills", focus_skills)
    r.add("references_unrouted", refs_unrouted)
    r.add("skills_unrouted", skills_unrouted)
    r.add("stage_unrouted", stage_unrouted(repo))
    r.add("skills_missing", skills_missing(active, tasks, available, focus_skills))
    r.add("skills_available", available)
    r.add("grow_triggers", grow_triggers(repo))
    pl_drift = drift(repo, [p for p in model.all_pipelines(repo) if p.id in milestone_pls])
    r.add("drift", "unknown" if pl_drift is None else pl_drift)
    r.add("stale_contracts", stale_contracts(repo))
    r.add("queued", queued)
    r.add("base", plan_base(active))
