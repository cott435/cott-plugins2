"""`dt status --skill build-planning`: the active milestone, its coverage and task rules, and the mode
(new · extend · replan · advance · foreign · current · blocked). The next unit to plan is a milestone, or a
stage with no milestone rows yet (`stage_to_cut`), whose pipelines are inferred from its Source
(`roadmap.milestone_pipelines`) and printed as `pipelines_inferred` for build-planning to divide."""
from __future__ import annotations

import re

from .. import git, md, model
from .. import probes as pb
from ..commands import roadmap as roadmap_cmd
from ..repo import Doc, Repo
from .common import (OWN_SKILLS, Report, add_common, add_graph, advance_ready, available_skills, blocked_reason,
                     live_spec_ids, milestone_row, next_task, plan_base)
from .packages import drift, grow_triggers, known_packages, stale_contracts


def expected_mode(task: model.Task) -> str:
    """The build-mode rule: solo for skeleton tasks (interface, spine, wiring, system; with no Kind, Phase 0),
    split for behaviour with a checkable outcome, else solo."""
    if task.kind in ("interface", "spine", "wiring", "system") or (not task.kind and task.is_spine):
        return "solo"
    return "split" if task.covers or any(i.startswith("TC-") for i in task.read) else "solo"


def mode_violations(tasks: list[model.Task]) -> list[str]:
    out = []
    for t in tasks:
        want = expected_mode(t)
        if t.mode in ("split", "solo") and t.mode != want and not md.strip_md(t.get("Reason")):
            skeleton = t.kind if t.kind and t.kind != "thicken" else "spine" if not t.kind and t.is_spine else ""
            why = skeleton or ("covers behaviour" if want == "split" else "no checkable outcome")
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


def boundaries_unfrozen(repo: Repo, pkgs: list[str], tasks: list[model.Task]) -> list[str]:
    """Boundaries the milestone crosses that no contract task freezes: a contract symbol whose `**Boundary:**`
    line names a consumer among the milestone's packages (in a single package, its components), and, in an
    interface-first plan, a contract type a milestone step's `In → Out` names (its signature needs it); each in no
    contract task's `Read:`, with no fixtures folder yet (an earlier milestone froze it). Items read
    `features.screen (portfolio)` and `profile.Report (PL-02.write_report)`."""
    frozen = {md.strip_md(i).split(" (")[0].strip() for t in tasks if t.is_contract for i in t.read}
    frozen |= model.frozen_symbols(tasks)
    arch = repo.architecture
    if pkgs and arch is not None and "single" in arch.header.get("Shape", "").lower():
        pkgs = list(pkgs) + [c.id for c in model.components(arch)]
    out, seen = [], set()
    for doc in repo.docs("contract"):
        for sym in model.symbols(doc):
            fields = md.bullet_fields(doc.lines, sym.start + 1, sym.end)
            consumers = [c for c in map(md.strip_md, md.split_list(fields.get("Boundary", ""))) if c in pkgs]
            folder = md.strip_md(fields.get("Fixtures", "")) or f"tests/contracts/{sym.id}/"
            if consumers and sym.id not in frozen and not (repo.root / folder).is_dir():
                out.append(f"{sym.id} ({', '.join(consumers)})")
                seen.add(sym.id)
    if not tasks or not model.is_interface_first(tasks[0].doc):
        return out
    types = model.contract_types(repo)
    by_id = {p.id: p for p in model.all_pipelines(repo)}
    for pid in _milestone_pipelines(repo, tasks):
        for s in by_id[pid].steps if pid in by_id else []:
            for name in s.in_types + s.out_types:
                ty = model.resolve_type(types, name)
                if ty is None or ty.id in frozen or ty.id in seen:
                    continue
                if not (repo.root / (ty.sample or f"tests/contracts/{ty.id}/")).exists():
                    out.append(f"{ty.id} ({pid}.{s.name})")
                    seen.add(ty.id)
    return out


def _milestone_pipelines(repo: Repo, tasks: list[model.Task]) -> list[str]:
    """The plan's milestone's live pipelines (its roadmap row), then any other a task's Step names."""
    row = milestone_row(repo, model.milestone_of(tasks[0].doc))
    ids = roadmap_cmd.milestone_pipelines(repo, row)[0] if row else []
    ids += [m.group(0) for t in tasks if (m := re.match(r"PL-\d{2,}", t.step))]
    return [p for p in dict.fromkeys(ids) if not repo.is_retired(p)]


def _sections(doc: Doc) -> dict[str, str]:
    return {s.id: "\n".join(line.rstrip() for line in s.text.splitlines() if not USED_BY.match(line))
            for s in model.symbols(doc)}


USED_BY = re.compile(r"^\s*(?:[-*]\s+)?\*\*Used by:?\*\*", re.IGNORECASE)


def interfaces_changed(repo: Repo, plan: Doc, tasks: list[model.Task], changed: list[str]) -> list[str]:
    """Interfaces the plan froze whose contract section changed since the plan was last committed, each with the
    tasks that build against it (its `Read:`, or a type their steps' `In → Out` cells name): `stats.Cov (M1-T04,
    M1-T05)`. Outside git, or with the plan uncommitted, every frozen symbol of a contract.md in `changed` counts.
    `**Used by:**` lines are ignored (pipeline-design appends to them)."""
    frozen = model.frozen_symbols(tasks)
    if not frozen:
        return []
    sha = git.last_commit(repo.root, plan.rel)
    moved: set[str] = set()
    for doc in repo.docs("contract"):
        now = _sections(doc)
        old_text = git.show_at(repo.root, sha, doc.rel) if sha else None
        if old_text is None:
            if doc.rel in changed:
                moved |= {i for i in now if i in frozen}
            continue
        before = _sections(Doc(repo.root, doc.rel, old_text))
        moved |= {i for i in now if i in frozen and i in before and before[i] != now[i]}
    if not moved:
        return []
    types = model.contract_types(repo)
    pipelines = {p.id: p for p in model.all_pipelines(repo)}
    out = []
    for sym in sorted(moved):
        readers = []
        for t in tasks:
            if t.is_contract:
                continue
            reads = {md.strip_md(i.split(" (")[0]).strip() for i in t.read}
            steps = [s for m in re.finditer(r"(PL-\d{2,})(?:\.(\w+))?", t.step) if m.group(1) in pipelines
                     for s in pipelines[m.group(1)].steps if m.group(2) in (None, s.name)]
            named = {ty.id for s in steps for n in s.in_types + s.out_types if (ty := model.resolve_type(types, n))}
            if sym in reads or sym in named:
                readers.append(t.id)
        out.append(f"{sym} ({', '.join(readers) or 'no task'})")
    return out


def probes_blocking(repo: Repo, ms: model.Milestone) -> list[str]:
    """Open or failed probes the milestone meets (design/probes.md §3.3): its packages, its pipelines' packages
    and step owners (a single package's components), and the types its steps pass."""
    pls = [p for p in roadmap_cmd.milestone_pipelines(repo, ms)[0] if not repo.is_retired(p)]
    names = set(milestone_packages(repo, ms, pls, []))
    types: set[str] = set()
    known = model.contract_types(repo)
    for p in model.all_pipelines(repo):
        if p.id in pls:
            for s in p.steps:
                names.add(s.owner)
                types |= {ty.id for n in s.in_types + s.out_types if (ty := model.resolve_type(known, n))}
    names.discard("")
    return pb.blocking(repo, ms.id, names, types)


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


def brief_stages_undesigned(repo: Repo) -> list[str]:
    """When every stage's Source is `brief` (an all-at-once project), the uncut stages still below Designed;
    else []."""
    sts = model.stages(repo.roadmap) if repo.roadmap else []
    if not sts or any(roadmap_cmd.source_files(st.source) or not re.search(r"\bbrief\b", st.source, re.I)
                      for st in sts):
        return []
    return [st.id for st in sts if roadmap_cmd.stage_status(repo, st) in ("Idea", "Specced")]


def stage_gaps(repo: Repo, stage_ids: list[str]) -> str:
    """What keeps each stage below Designed, stages with the same gap grouped: `S1, S2: QR-04 on no Approved
    pipeline`, `S3: PL-05, PL-06 not Approved`."""
    by_gap: dict[str, list[str]] = {}
    for st in (s for s in model.stages(repo.roadmap) if s.id in stage_ids):
        draft = [p for p in roadmap_cmd.milestone_pipelines(repo, st)[0] if not repo.is_retired(p)
                 and not ((d := repo.lookup(p, archive=False)) and d.doc.status == "Approved")]
        off = roadmap_cmd.ids_off_approved(repo, st)
        if draft:
            gap = f"{', '.join(draft[:8])}{f' and {len(draft) - 8} more' if len(draft) > 8 else ''} not Approved"
        elif off:
            gap = f"{', '.join(off[:8])}{f' and {len(off) - 8} more' if len(off) > 8 else ''} on no Approved pipeline"
        else:
            gap = "no pipeline inferred from its Source"
        by_gap.setdefault(gap, []).append(st.id)
    return "; ".join(f"{', '.join(sts)}: {gap}" for gap, sts in by_gap.items())


def unit_blocked_reason(repo: Repo, unit: model.Milestone | model.Stage) -> str:
    """Why the next unit can't be planned or cut yet: pipelines not all Approved, or (a stage) spec IDs its
    Source adds that no Approved pipeline carries."""
    pls, inferred = roadmap_cmd.milestone_pipelines(repo, unit)
    if not roadmap_cmd.pipelines_approved(repo, unit):
        listed = ", ".join(pls) or ("none inferred from its Source" if inferred else "none listed")
        return f"{unit.id} pipelines not all Approved ({listed}); run pipeline-design"
    off = roadmap_cmd.ids_off_approved(repo, unit)
    shown = ", ".join(off[:8]) + (f" and {len(off) - 8} more" if len(off) > 8 else "")
    return f"{unit.id} spec IDs on no Approved pipeline ({shown}); run pipeline-design"


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
    system = model.system_pipeline_ids(repo)
    spined = {pl for t in tasks for pl in model.spine_pipelines(t, system)}
    for doc in repo.docs("archived-plan", archive=True):
        spined |= {pl for t in model.tasks(doc) for pl in model.spine_pipelines(t, system)}
    drafts = draft_pipelines(repo, tasks, milestone_pls)
    pkgs = milestone_packages(repo, ms_row, milestone_pls, tasks) if active else []
    open_revise = revising(repo, pkgs, drafts) if active else []
    changed = changed_since_plan(repo, active, pkgs) if active else []
    moved = interfaces_changed(repo, active, tasks, changed) if active else []
    queued = sorted(f"{roadmap_cmd._plan_milestone(d) or '?'} ({d.rel})" for d in repo.docs("queued-plan"))
    available = available_skills(repo)

    # The next milestone that still needs a plan, or the next stage that still needs cutting into milestones;
    # and, on its own, the first designed stage with no milestone rows: it is cut now, whatever earlier
    # milestones still wait for their plans.
    target = roadmap_cmd.next_unit(repo)
    cut = roadmap_cmd.stage_to_cut(repo)
    never_planned = plan is None and not repo.docs("archived-plan", archive=True)
    blocked, focus = None, ms_row if active else None   # focus: the milestone this run plans or replans
    if plan is not None and not model.is_dev_team_plan(plan) and _has_unchecked(plan):
        mode = "foreign"
    elif active and advance_ready(repo, active):
        mode = "advance"
    elif active and open_revise:
        mode = "blocked"
        blocked = f"waiting for {', '.join(open_revise)} approval (Revise in progress)"
    elif not active and never_planned and (undesigned := brief_stages_undesigned(repo)):
        mode = "blocked"
        no_pl = [pkg for pkg in known_packages(repo) if repo.package_doc(pkg, "pipelines") is None]
        blocked = (f"{', '.join(undesigned)} below Designed: every stage comes from the brief, so all are "
                   f"designed before the first cut; {stage_gaps(repo, undesigned)}"
                   + (f"; no pipelines.md for {', '.join(no_pl)}" if no_pl else "") + "; run pipeline-design")
    elif cut is not None:
        if not active and not queued and never_planned:
            # New plans the first unit and cuts every designed stage; the first unit must be Designed too.
            focus = target or cut
            ready = (roadmap_cmd.pipelines_approved(repo, focus) if isinstance(focus, model.Milestone)
                     else roadmap_cmd.stage_designed(repo, focus))
            if not ready:
                mode, blocked = "blocked", unit_blocked_reason(repo, focus)
            else:
                mode = "new"
        else:
            mode, focus = "extend", cut
    elif active:
        if blocked_tasks or changed or moved:
            mode = "replan"
        elif isinstance(target, model.Milestone) and roadmap_cmd.pipelines_approved(repo, target):
            mode, focus = "extend", target
        else:
            mode = "current"
    elif queued:
        mode = "extend"
    elif target is not None:
        focus = target
        if isinstance(target, model.Milestone) and roadmap_cmd.pipelines_approved(repo, target):
            mode = "new" if never_planned else "extend"
        else:
            mode = "blocked"
            blocked = unit_blocked_reason(repo, target)
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
    # A milestone to plan (New, Extend) waits for the probes it meets; cutting a stage doesn't.
    blocking = probes_blocking(repo, focus) if isinstance(focus, model.Milestone) else []
    if blocking and mode in ("new", "extend") and focus is not ms_row:
        mode = "blocked"
        blocked = f"waiting for {', '.join(dict.fromkeys(b.split(' ')[0] for b in blocking))}"
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
    r.add("boundaries_unfrozen", boundaries_unfrozen(repo, pkgs, tasks) if active else [])
    r.add("draft_pipelines", drafts)
    r.add("changed_since_plan", changed)
    r.add("interfaces_changed", moved)
    r.add("probes_blocking", blocking)
    r.add("stage_to_cut", f"{cut.id} {cut.name}" if cut is not None else "none")
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
    add_graph(repo, r)
