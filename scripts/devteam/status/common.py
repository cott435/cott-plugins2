"""Shared by every `dt status` report: the Report printer, the docs line, next IDs, skill lists, plan helpers
and the SessionStart summary."""
from __future__ import annotations

import os
import re
from pathlib import Path

from .. import git, md, model, specdocs
from .. import references as refs
from ..commands import roadmap as roadmap_cmd
from ..repo import Doc, Repo

# dev-team2's own skills: never reported as project skills to route steps to.
OWN_SKILLS = {"idea-refine", "spec-writing", "architecture-design", "pipeline-design", "test-planning",
              "build-planning", "build-setup", "reference-intake"}
SUMMARY_DOCS = ("docs/brief.md", "docs/spec.md", "docs/roadmap.md", "tasks/plan.md")


# ---- report ----------------------------------------------------------------------------------

class Report:
    """Ordered keys with JSON values; `text` overrides how a key prints when its value isn't a plain list."""

    def __init__(self):
        self.values: dict[str, object] = {}
        self.text: dict[str, str] = {}

    def add(self, key: str, value, text: str | None = None) -> None:
        self.values[key] = value
        if text is not None:
            self.text[key] = text

    def mode(self, mode: str, blocked: str | None = None) -> None:
        self.add("mode", mode)
        self.add("blocked", blocked)

    def render(self) -> str:
        out = []
        for key, value in self.values.items():
            if key == "blocked" and not value:
                continue
            label = "next ids" if key == "next_ids" else key
            out.append(f"{label}: {self.text.get(key, fmt(value))}")
        return "\n".join(out)


def fmt(value) -> str:
    if value is None:
        return "none"
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items()) or "none"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) or "none"
    return str(value)


def add_common(repo: Repo, r: Report) -> None:
    """The `docs` and `next ids` lines every report prints after its mode, then the reference files waiting
    for reference-intake."""
    docs = docs_summary(repo)
    r.add("docs", docs, " · ".join(f"{k} {v}" for k, v in docs.items()))
    ids = next_ids(repo)
    r.add("next_ids", ids, " ".join(ids))
    state = refs.state(repo)
    r.add("references_unindexed", state.unindexed)
    r.add("references_changed", state.changed)
    r.add("references_missing", state.missing)


# ---- docs line and next IDs ------------------------------------------------------------------

def doc_state(doc: Doc | None) -> str:
    if doc is None:
        return "missing"
    return doc.status or "no status"


def plan_state(repo: Repo) -> str:
    plan = repo.plan
    if plan is None:
        return "missing"
    if not model.is_dev_team_plan(plan):
        return "foreign"
    if (plan.status or "").lower().startswith("between"):
        return "Between milestones"
    return f"{model.milestone_of(plan) or '?'} {plan.status or 'no status'}"


def roadmap_state(repo: Repo) -> str:
    if repo.roadmap is None:
        return "missing"
    if not roadmap_cmd.has_status_table(repo.roadmap):
        return "no status column"
    return "stale (run dt roadmap)" if roadmap_cmd.differences(repo) else "ok"


def docs_summary(repo: Repo) -> dict[str, str]:
    arch = repo.architecture
    arch_state = doc_state(arch)
    if arch is not None and arch.header.get("Shape"):
        arch_state += f" ({arch.header['Shape']})"
    return {"brief": doc_state(repo.doc("docs/brief.md")), "spec": doc_state(repo.spec),
            "architecture": arch_state, "roadmap": roadmap_state(repo), "plan": plan_state(repo),
            "constraints": doc_state(repo.constraints)}


def next_decision(repo: Repo) -> str:
    """Next free AD: past every defined decision and every AD the architecture docs mention (a broken fence
    can hide decision headings from the parser, never from this)."""
    n = int(repo.next_id("AD").split("-")[1])
    for d in repo.docs("architecture", "package-architecture"):
        n = max([n] + [int(i.split("-")[1]) + 1 for i in specdocs.refs(d.text) if i.startswith("AD-")])
    return f"AD-{n:02d}"


def next_ids(repo: Repo) -> list[str]:
    stages = bool(repo.roadmap and model.stages(repo.roadmap))     # roadmaps from before stages have none
    out = [next_decision(repo)] + [repo.next_id(p) for p in ("PL", "TC") + (("S",) if stages else ()) + ("M",)]
    plan = roadmap_cmd.active_plan(repo)
    if plan:
        out.append(repo.next_id(f"{model.milestone_of(plan)}-T"))
    return out


# ---- skills, spec, git -----------------------------------------------------------------------

def _skill_names(base: Path) -> list[str]:
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if (p / "SKILL.md").is_file())


def available_skills(repo: Repo) -> list[str]:
    """Project skills (.claude/skills) plus the plugin's (`$CLAUDE_PLUGIN_ROOT/skills`), minus dev-team2's own."""
    names = set(_skill_names(repo.root / ".claude" / "skills"))
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin:
        names |= set(_skill_names(Path(plugin) / "skills"))
    return sorted(names - OWN_SKILLS)


def live_spec_ids(repo: Repo) -> tuple[set[str], set[str]]:
    """(live, removed) requirement IDs in the spec."""
    live, removed = set(), set()
    if repo.spec:
        for d in repo.spec.definitions():
            if d.how == "requirement":
                (removed if d.retired else live).add(d.id)
    return live - removed, removed


def head_status(repo: Repo, doc: Doc) -> str | None:
    """The doc's Status at git HEAD, or None (not in git, or not committed)."""
    text = git.show_head(repo.root, doc.rel)
    return md.header(text.splitlines())[0].get("Status") if text else None


def in_revise(repo: Repo, doc: Doc | None) -> bool:
    """Draft in the working copy but Approved at HEAD: a Revise round is open."""
    return bool(doc and doc.status == "Draft" and head_status(repo, doc) == "Approved")


# ---- plan --------------------------------------------------------------------------------------

def milestone_row(repo: Repo, mid: str | None) -> model.Milestone | None:
    if not repo.roadmap or not mid:
        return None
    return next((m for m in model.milestones(repo.roadmap) if m.id == mid), None)


def blocked_reason(task: model.Task) -> str:
    """The task's `Blocked:` reason, or "" when it isn't blocked."""
    v = md.strip_md(task.blocked)
    return "" if v.lower() in ("", "—", "-", "none", "no") else v


def next_task(items: list[model.TodoItem], tasks: dict[str, model.Task]) -> model.TodoItem | None:
    """First unchecked todo item that isn't blocked and whose dependencies are all checked."""
    state = {i.id: i.checked for i in items}
    for it in items:
        t = tasks.get(it.id)
        if it.checked or (t and blocked_reason(t)):
            continue
        if t and not all(state.get(d, False) for d in t.depends_on):
            continue
        return it
    return None


def plan_base(plan: Doc | None) -> str:
    """The plan header's Base commit, or "pending" when it is missing or `—`."""
    value = md.strip_md(plan.header.get("Base", "")) if plan else ""
    return "pending" if value in ("", "—", "-") else value


def exit_ticked(plan: Doc) -> bool:
    exits = [c for c in model.checkpoints(plan) if not c.after and "exit" in c.title.lower()]
    return all(c.items and all(i.checked for i in c.items) for c in exits)


def advance_ready(repo: Repo, plan: Doc | None) -> bool:
    """Every todo item is checked and the plan's exit checkpoint is ticked."""
    items = model.todo_items(repo.todo) if plan and repo.todo else []
    return bool(items) and all(i.checked for i in items) and exit_ticked(plan)


# ---- SessionStart summary ----------------------------------------------------------------------

def summary(repo: Repo) -> list[str]:
    """At most 8 lines for the SessionStart hook; [] when the project has no dev-team2 docs."""
    if not any(repo.doc(p) for p in SUMMARY_DOCS):
        return []
    out = []
    plan, active = repo.plan, roadmap_cmd.active_plan(repo)
    queued = [roadmap_cmd._plan_milestone(d) or d.rel for d in repo.docs("queued-plan")]
    if active:
        mid = model.milestone_of(active)
        row = milestone_row(repo, mid)
        name = row.name if row else re.sub(r"^M\d+:\s*|\s*—\s*Plan$", "", active.title or "")
        out.append(f"milestone: {mid} {name} · plan {active.status or 'no status'}")
        items = model.todo_items(repo.todo) if repo.todo else []
        tasks = {t.id: t for t in model.tasks(active)}
        nxt = next_task(items, tasks)
        nxt_text = f"{nxt.id} {tasks[nxt.id].title if nxt.id in tasks else nxt.text}" if nxt else "none"
        out.append(f"progress: {sum(i.checked for i in items)}/{len(items)} · next: {nxt_text}")
        blocked = [f"{t.id} ({blocked_reason(t)})" for t in tasks.values() if blocked_reason(t)]
        out.append(f"blocked: {fmt(blocked)}")
    elif plan is not None and not model.is_dev_team_plan(plan):
        out.append("plan: tasks/plan.md is not a dev-team2 plan (build-planning will ask before touching it)")
    elif plan is not None:
        out.append("milestone: none (between milestones)")
    else:
        out.append("milestone: none (no tasks/plan.md)")
    if queued:
        out.append(f"queued: {fmt(queued)}")
    drafts = sorted(d.rel for d in repo.docs() if (d.status or "") == "Draft")
    if drafts:
        shown = drafts[:5] + ([f"+{len(drafts) - 5} more"] if len(drafts) > 5 else [])
        out.append(f"draft (waiting for approval): {fmt(shown)}")
    if repo.roadmap and roadmap_cmd.has_status_table(repo.roadmap) and roadmap_cmd.differences(repo):
        out.append("roadmap: Status* column stale (run dt roadmap)")
    waiting = refs.state(repo).waiting
    if waiting:
        out.append(f"references: {waiting} waiting → reference-intake")
    dt = Path(__file__).resolve().parents[2] / "dt.py"
    out = out[:7]
    out.append(f"dt: python3 {dt}")
    return out
