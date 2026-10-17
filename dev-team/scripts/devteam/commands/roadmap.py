"""Rewrite the roadmap's derived Status* columns: milestones Idea → Specced → Designed → Planned → Building →
Done; stages the same, with Split once build-planning has written their milestone rows (older roadmaps wrote
`Cut`, which still reads as Split)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from .. import edit, md, model, specdocs
from ..repo import Doc, Repo

ORDER = ["Idea", "Specced", "Designed", "Planned", "Building", "Done"]
STAGE_ORDER = ["Idea", "Specced", "Designed", "Split", "Planned", "Building", "Done"]
# Stage status words an older dt wrote, and what they read as now.
LEGACY_STAGE_STATUS = {"Cut": "Split"}


def add_arguments(parser):
    parser.add_argument("--check", action="store_true", help="print the differences and exit 1 instead of writing")


# ---- deriving --------------------------------------------------------------------------------

def _plan_milestone(doc: Doc) -> str | None:
    m = model.milestone_of(doc)
    if m:
        return m
    found = re.match(r"(M\d+)\b", Path(doc.rel).name)
    return found.group(1) if found else None


def active_plan(repo: Repo) -> Doc | None:
    """tasks/plan.md when it is a dev-team plan for a milestone (not the between-milestones stub)."""
    plan = repo.plan
    if not plan or not model.is_dev_team_plan(plan):
        return None
    if (plan.status or "").lower().startswith("between") or not model.milestone_of(plan):
        return None
    return plan


def source_files(source: str) -> list[str]:
    """Idea files a roadmap row's Source cell cites, as repo paths (`docs/ideas/x.md`). `brief` → []."""
    out = []
    for f in re.findall(r"[\w./-]+\.md", source):
        f = re.sub(r"^(\.\./|\./|docs/)+", "", f)
        if f != "brief.md":
            out.append("docs/" + f)
    return list(dict.fromkeys(out))


def is_specced(repo: Repo, ms: model.Milestone | model.Stage) -> bool:
    files = source_files(ms.source)
    if files:
        return all((repo.doc(f) is not None and (repo.doc(f).status or "") == "Specced") for f in files)
    brief, spec = repo.doc("docs/brief.md"), repo.spec
    return bool(brief and brief.status == "Accepted" and spec and spec.status == "Approved")


def source_ids(repo: Repo, ms: model.Milestone | model.Stage) -> set[str]:
    """The IDs the row's Source adds: those of the spec Changelog rows that cite its idea files (or brief.md for
    a `brief` row), minus those marked removed. A row whose IDs cell reads `all` adds every live requirement."""
    files = {f.removeprefix("docs/") for f in source_files(ms.source)} or {"brief.md"}
    ids = set()
    for row in specdocs.changelog(repo.spec.text if repo.spec else None):
        cites_brief = not row.files and re.search(r"\bbrief\b", row.source, re.I)
        if row.files & files or ("brief.md" in files and cites_brief):
            ids |= {i for i, mark in row.ids.items() if mark != "removed"}
            if row.all_ids:
                ids |= live_requirement_ids(repo)
    return ids


def inferred_pipelines(repo: Repo, ms: model.Milestone | model.Stage) -> list[str]:
    """The milestone's pipelines worked out from its Source (`source_ids`): the live ones, package or system,
    whose Covers (else, with no Covers line, step Covers) include any of its IDs."""
    ids = source_ids(repo, ms)
    out = set()
    for p in model.all_pipelines(repo):
        # The pipeline's own Covers; its step Covers only when it has none (a step reused from an earlier
        # milestone's pipeline cites that milestone's IDs).
        covers = set(p.covers) or set().union(*(s.covers for s in p.steps))
        if covers & ids and not repo.is_retired(p.id):
            out.add(p.id)
    return sorted(out, key=lambda i: int(i.split("-")[1]))


def live_requirement_ids(repo: Repo) -> set[str]:
    """The spec's requirement IDs that aren't retired."""
    if not repo.spec:
        return set()
    defs = [d for d in repo.spec.definitions() if d.how == "requirement"]
    return {d.id for d in defs if not d.retired} - {d.id for d in defs if d.retired}


def ids_off_approved(repo: Repo, ms: model.Milestone | model.Stage) -> list[str]:
    """The live spec IDs the row's Source adds that no Approved pipeline carries on its Covers line or on a
    step's Covers: what pipeline-design still has to design before the stage is Designed."""
    on = set()
    for p in model.all_pipelines(repo):
        if p.doc.status == "Approved" and not repo.is_retired(p.id):
            on |= set(p.covers).union(*(s.covers for s in p.steps))
    left = (source_ids(repo, ms) & live_requirement_ids(repo)) - on
    return sorted(left, key=lambda i: (i.split("-")[0], int(i.split("-")[1])))


def milestone_pipelines(repo: Repo, ms: model.Milestone | model.Stage) -> tuple[list[str], bool]:
    """(the milestone's pipelines, inferred?): the row's Pipelines cell when it names any, else
    `inferred_pipelines` from its (or its stage's) Source. A stage always infers: build-planning divides its
    pipelines among the milestones it cuts."""
    if ms.pipelines:
        return ms.pipelines, False
    return inferred_pipelines(repo, ms), True


def pipelines_approved(repo: Repo, ms: model.Milestone | model.Stage) -> bool:
    """Every pipeline of the milestone (`milestone_pipelines`) is defined in an Approved pipelines.md or
    architecture."""
    live = [p for p in milestone_pipelines(repo, ms)[0] if not repo.is_retired(p)]
    if not live:
        return False
    for pid in live:
        d = repo.lookup(pid, archive=False)
        if not d or d.retired or d.doc.kind not in ("pipelines", "architecture") or d.doc.status != "Approved":
            return False
    return True


def milestone_status(repo: Repo, ms: model.Milestone) -> str:
    if md.strip_md(ms.fields.get("Outcome", "")).lower().startswith("done"):
        return "Done"
    if any(_plan_milestone(d) == ms.id for d in repo.docs("archived-plan", archive=True)):
        return "Done"
    plan = active_plan(repo)
    if plan and model.milestone_of(plan) == ms.id:
        return "Building" if any(model.todo_state(repo).values()) else "Planned"
    if any(_plan_milestone(d) == ms.id for d in repo.docs("queued-plan")):
        return "Planned"
    if pipelines_approved(repo, ms):
        return "Designed"
    return "Specced" if is_specced(repo, ms) else "Idea"


def stage_designed(repo: Repo, st: model.Stage) -> bool:
    """An uncut stage is ready to cut: its inferred pipelines are all Approved, and every live spec ID its
    Source adds is on an Approved pipeline (`ids_off_approved` is empty)."""
    return pipelines_approved(repo, st) and not ids_off_approved(repo, st)


def stage_status(repo: Repo, st: model.Stage) -> str:
    """Uncut: Idea → Specced → Designed (`stage_designed`: ready to cut). Split into milestone rows: Done when
    every milestone is; Building when any is Building or Done; Planned when any is; else Split."""
    mss = model.stage_milestones(repo.roadmap, st.id) if repo.roadmap else []
    if not mss:
        if stage_designed(repo, st):
            return "Designed"
        return "Specced" if is_specced(repo, st) else "Idea"
    got = [milestone_status(repo, m) for m in mss]
    if all(g == "Done" for g in got):
        return "Done"
    if any(g in ("Building", "Done") for g in got):
        return "Building"
    return "Planned" if "Planned" in got else "Split"


def stage_to_cut(repo: Repo) -> model.Stage | None:
    """The first stage with no milestone rows that is Designed, whatever earlier milestones are still waiting
    for their plans: build-planning cuts it now, rows only."""
    doc = repo.roadmap
    if not doc:
        return None
    for st in model.stages(doc):
        if not model.stage_milestones(doc, st.id) and stage_status(repo, st) == "Designed":
            return st
    return None


def next_unit(repo: Repo) -> model.Milestone | model.Stage | None:
    """What build-planning works on next: the first milestone below Planned, or the first stage with no
    milestone rows yet (to cut), in roadmap order (pre-stage milestones first, then stage by stage)."""
    doc = repo.roadmap
    if not doc:
        return None
    mss = model.milestones(doc)
    units: list = [m for m in mss if not m.stage]
    for st in model.stages(doc):
        cut = [m for m in mss if m.stage == st.id]
        units += cut or [st]
    for u in units:
        if isinstance(u, model.Stage):
            if stage_status(repo, u) in ("Idea", "Specced", "Designed"):
                return u
        elif milestone_status(repo, u) in ("Idea", "Specced", "Designed"):
            return u
    return None


def status_table(doc: Doc, first: str = "milestone") -> tuple[int, str] | None:
    """(status column index, column name) of the roadmap's milestone (or `first="stage"`: stage) table."""
    for _, head, _rows in doc.tables():
        if head and head[0].lower() == first:
            col = model.status_column(head)
            if col:
                return head.index(col), col
    return None


def has_status_table(doc: Doc) -> bool:
    return bool(status_table(doc) or status_table(doc, "stage"))


def differences(repo: Repo, legacy_ok: bool = False) -> list[tuple[model.Milestone | model.Stage, str, str]]:
    """(milestone or stage, current cell, derived status) for every row whose Status* cell is out of date.
    `legacy_ok`: an older word that reads the same (a stage's `Cut` for Split) is not out of date."""
    doc = repo.roadmap
    if not doc:
        return []
    out = []
    for first, rows, derive in (("stage", model.stages(doc), lambda x: stage_status(repo, x)),
                                ("milestone", model.milestones(doc), lambda x: milestone_status(repo, x))):
        table = status_table(doc, first)
        if not table:
            continue
        for item in rows:
            if item.row_line is None:
                continue
            current = md.strip_md(item.row.get(table[1], ""))
            derived = derive(item)
            if current != derived and not (legacy_ok and first == "stage"
                                           and LEGACY_STAGE_STATUS.get(current) == derived):
                out.append((item, current, derived))
    return out


# ---- writing ---------------------------------------------------------------------------------

def _rewrite(lines: list[str], idx: int, changes: dict[int, str]) -> list[str]:
    """`lines` (endings kept, as `edit.read_lines`) with cell `idx` of each changed row replaced."""
    lines = list(lines)
    for n, value in changes.items():
        body = lines[n].rstrip("\r\n")
        cells = md.table_cells(body) or []
        while len(cells) <= idx:
            cells.append("")
        cells[idx] = value
        indent = body[:len(body) - len(body.lstrip())]
        lines[n] = indent + "| " + " | ".join(cells) + " |" + lines[n][len(body):]
    return lines


def run(args, repo) -> int:
    doc = repo.roadmap
    if not doc:
        print("dt roadmap: no docs/roadmap.md", file=sys.stderr)
        return 1
    if not has_status_table(doc):
        print("dt roadmap: docs/roadmap.md has no stage or milestone table with a Status column",
              file=sys.stderr)
        return 1
    # --check accepts an older roadmap's `Cut`; a write brings it up to date (Split).
    diffs = differences(repo, legacy_ok=args.check)
    for ms, current, derived in diffs:
        print(f"{ms.id}: {current or '—'} → {derived}")
    if not diffs:
        print("roadmap: ok")
        return 0
    if args.check:
        print(f"roadmap: {len(diffs)} out of date (run dt roadmap)")
        return 1
    lines = edit.read_lines(doc.path)
    for first, kind in (("stage", model.Stage), ("milestone", model.Milestone)):
        changes = {x.row_line: d for x, _, d in diffs if isinstance(x, kind)}
        if changes:
            lines = _rewrite(lines, status_table(doc, first)[0], changes)
    edit.write_lines(doc.path, lines)
    repo.reload(doc.rel)
    print(f"roadmap: updated {len(diffs)}")
    return 0
