"""Typed views over the planning docs: tasks, checkpoints, todo items, pipelines, test cases, milestones,
contract symbols and components. Each is read from a `Doc` by the shared markdown helpers in `md`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import md
from .repo import Doc, Repo

# ---- plan ------------------------------------------------------------------------------------

TASK_FIELDS = ("Package", "Step", "Covers", "Size", "Mode", "Skills", "Read", "Verify",
               "Depends on", "Parallel", "Files likely", "Blocked", "Reason")


@dataclass
class Task:
    id: str
    title: str
    doc: Doc
    start: int
    end: int
    phase: str                         # heading text of the enclosing `## Phase …`, or ""
    fields: dict[str, str]
    acceptance: list[md.Checkbox]

    def get(self, key: str) -> str:
        return self.fields.get(key, "").strip()

    @property
    def package(self) -> str:
        return md.strip_md(self.get("Package"))

    @property
    def step(self) -> str:
        return md.strip_md(self.get("Step"))

    @property
    def size(self) -> str:
        return md.strip_md(self.get("Size"))

    @property
    def mode(self) -> str:
        return md.strip_md(self.get("Mode")).split()[0].lower() if self.get("Mode") else ""

    @property
    def read(self) -> list[str]:
        return md.split_list(self.get("Read"))

    @property
    def files_likely(self) -> list[str]:
        return md.split_list(self.get("Files likely"))

    @property
    def depends_on(self) -> list[str]:
        return md.task_refs(self.get("Depends on"))

    @property
    def parallel(self) -> str:
        return md.strip_md(self.get("Parallel"))

    @property
    def covers(self) -> list[str]:
        return md.expand_refs(self.get("Covers"))

    @property
    def skills(self) -> list[str]:
        return [md.strip_md(s).split(" (")[0] for s in md.split_list(self.get("Skills"))
                if md.strip_md(s) and md.strip_md(s) not in ("—", "-", "none")]

    @property
    def verify(self) -> list[str]:
        return re.findall(r"`([^`]+)`", self.get("Verify"))

    @property
    def blocked(self) -> str:
        return self.get("Blocked")

    @property
    def is_spine(self) -> bool:
        return "spine" in self.phase.lower() or self.phase.lower().startswith("phase 0")

    @property
    def text(self) -> str:
        return "\n".join(self.doc.lines[self.start:self.end]).rstrip() + "\n"


@dataclass
class Finding:
    id: str
    line: int
    text: str
    severity: str
    disposition: str                   # text after the last "→", or ""


@dataclass
class Checkpoint:
    title: str
    after: str                         # task ID the checkpoint follows, or "" (e.g. milestone exit)
    doc: Doc
    start: int
    end: int
    items: list[md.Checkbox]
    findings: list[Finding]


def _phase_of(doc: Doc, line: int) -> str:
    phase = ""
    for h in doc.headings:
        if h.line > line:
            break
        if h.level == 2:
            phase = h.text if h.text.lower().startswith("phase") else ""
    return phase


def tasks(doc: Doc) -> list[Task]:
    out = []
    for h in doc.headings:
        if not (h.id and re.fullmatch(md.TASK_ID, h.id)):
            continue
        acc_line = md.field_line(doc.lines, h.line + 1, h.end, "Acceptance")
        acceptance = []
        if acc_line is not None:
            j = acc_line + 1
            while j < h.end and (doc.lines[j].strip().startswith(("- [", "* [")) or not doc.lines[j].strip()):
                j += 1
            acceptance = md.checkboxes(doc.lines, acc_line + 1, j)
        out.append(Task(h.id, h.title, doc, h.line, h.end, _phase_of(doc, h.line),
                        md.fields_in(doc.lines, h.line + 1, h.end), acceptance))
    return out


def checkpoints(doc: Doc) -> list[Checkpoint]:
    out = []
    for h in doc.headings:
        if not h.text.lower().startswith("checkpoint"):
            continue
        m = re.search(md.TASK_ID, h.text)
        f_line = md.field_line(doc.lines, h.line + 1, h.end, "Findings")
        items = md.checkboxes(doc.lines, h.line + 1, f_line if f_line is not None else h.end)
        findings = []
        for i in range(h.line + 1, h.end):
            fm = re.match(rf"^\s*[-*]\s+({md.FINDING_ID})\s+(.*)$", doc.lines[i])
            if fm:
                body = fm.group(2)
                sev = body.split("·")[0].strip().split()[0] if body.strip() else ""
                disp = body.rsplit("→", 1)[1].strip() if "→" in body else ""
                findings.append(Finding(fm.group(1), i, body, sev, disp))
        out.append(Checkpoint(h.text, m.group(0) if m else "", doc, h.line, h.end, items, findings))
    return out


@dataclass
class TodoItem:
    id: str
    checked: bool
    line: int
    text: str


def todo_items(doc: Doc) -> list[TodoItem]:
    out = []
    for cb in md.checkboxes(doc.lines, 0, len(doc.lines)):
        m = re.match(rf"({md.TASK_ID})\b\s*(.*)$", cb.text)
        if m:
            out.append(TodoItem(m.group(1), cb.checked, cb.line, m.group(2)))
    return out


def milestone_of(doc: Doc) -> str | None:
    """`**Milestone:** M2` from a plan's header, else the H1's leading M<n>."""
    m = re.match(r"M\d+", md.strip_md(doc.header.get("Milestone", "")))
    if m:
        return m.group(0)
    m = re.match(r"(M\d+)\b", doc.title or "")
    return m.group(1) if m else None


def is_dev_team_plan(doc: Doc) -> bool:
    """A plan written by build-planning has a `**Milestone:**` or a between-milestones Status in its header."""
    return "Milestone" in doc.header or (doc.status or "").lower().startswith("between")


# ---- pipelines -------------------------------------------------------------------------------

@dataclass
class Step:
    num: str
    name: str                          # function name, backticks stripped
    owner: str
    io: str
    spine: str
    covers: list[str]
    line: int


@dataclass
class Pipeline:
    id: str
    title: str
    doc: Doc
    start: int
    end: int
    fields: dict[str, str]
    steps: list[Step]

    @property
    def entry(self) -> str:
        return md.strip_md(self.fields.get("Entry", ""))

    @property
    def entry_file(self) -> str:
        return self.entry.split("::")[0]

    @property
    def entry_function(self) -> str:
        return self.entry.split("::")[1] if "::" in self.entry else ""

    @property
    def trigger(self) -> str:
        return md.strip_md(self.fields.get("Trigger", ""))

    @property
    def covers(self) -> list[str]:
        return md.expand_refs(self.fields.get("Covers", ""))

    @property
    def package(self) -> str | None:
        return self.doc.package

    @property
    def is_system(self) -> bool:
        return self.doc.kind == "architecture"

    def step_ids(self) -> list[str]:
        return [f"{self.id}.{s.name}" for s in self.steps]


def _col(row: dict[str, str], *names: str) -> str:
    for n in names:
        for k, v in row.items():
            if k.lower().startswith(n.lower()):
                return v
    return ""


def pipelines(doc: Doc) -> list[Pipeline]:
    out = []
    for h in doc.headings:
        if not (h.id and re.fullmatch(r"PL-\d{2,}", h.id)) or "~~" in h.title:
            continue
        # The step table sits directly in the section, before any sub-heading.
        sub = [x for x in doc.headings_under(h)]
        body_end = sub[0].line if sub else h.end
        steps = []
        for _, head, rows in doc.tables(h.line + 1, body_end):
            if not any(c.lower() == "step" for c in head):
                continue
            for n, row in md.table_dicts(head, rows):
                steps.append(Step(_col(row, "#"), md.strip_md(_col(row, "Step")).split("(")[0].strip(),
                                  md.strip_md(_col(row, "Owner")), _col(row, "In"), _col(row, "Spine"),
                                  md.expand_refs(_col(row, "Covers")), n))
        out.append(Pipeline(h.id, h.title, doc, h.line, h.end, md.fields_in(doc.lines, h.line + 1, body_end), steps))
    return out


def all_pipelines(repo: Repo) -> list[Pipeline]:
    out = []
    for d in repo.docs("pipelines", "architecture"):
        out.extend(pipelines(d))
    return out


# ---- tests -----------------------------------------------------------------------------------

@dataclass
class TestCase:
    id: str
    title: str
    doc: Doc
    start: int
    end: int
    fields: dict[str, str]

    @property
    def pipeline(self) -> str:
        m = re.search(r"PL-\d{2,}", self.fields.get("Pipeline", ""))
        return m.group(0) if m else ""

    @property
    def fixture(self) -> str:
        return md.strip_md(self.fields.get("Fixture", ""))

    @property
    def covers(self) -> list[str]:
        return md.expand_refs(self.fields.get("Covers", ""))


def test_cases(doc: Doc) -> list[TestCase]:
    return [TestCase(h.id, h.title, doc, h.line, h.end, md.fields_in(doc.lines, h.line + 1, h.end))
            for h in doc.headings if h.id and re.fullmatch(r"TC-\d{2,}", h.id) and "~~" not in h.title]


def strategy_rows(doc: Doc) -> list[dict[str, str]]:
    """Rows of the tests.md Strategy table (Pipeline | Smoke | …)."""
    h = doc.heading("Strategy")
    if not h:
        return []
    out = []
    for _, head, rows in doc.tables(h.line + 1, h.end):
        if head and head[0].lower() == "pipeline":
            out.extend(r for _, r in md.table_dicts(head, rows))
    return out


# ---- roadmap ---------------------------------------------------------------------------------

@dataclass
class Milestone:
    id: str
    row: dict[str, str]                # roadmap table row ({} if only a section exists)
    row_line: int | None
    section: md.Heading | None
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.row.get("Name") or (self.section.title if self.section else "")

    @property
    def packages(self) -> list[str]:
        return [md.strip_md(p) for p in md.split_list(self.row.get("Packages", "")) if md.strip_md(p) not in ("—", "")]

    @property
    def pipelines(self) -> list[str]:
        return md.expand_refs(self.row.get("Pipelines", ""))

    @property
    def depends(self) -> list[str]:
        return re.findall(r"\bM\d+\b", self.row.get("Depends", ""))

    @property
    def source(self) -> str:
        return self.row.get("Source", "")


def milestones(doc: Doc) -> list[Milestone]:
    out: dict[str, Milestone] = {}
    for _, head, rows in doc.tables():
        if not head or head[0].lower() != "milestone":
            continue
        for n, row in md.table_dicts(head, rows):
            mid = md.strip_md(row.get(head[0], ""))
            if re.fullmatch(md.MILESTONE_ID, mid):
                out[mid] = Milestone(mid, row, n, None)
    for h in doc.headings:
        if h.id and re.fullmatch(md.MILESTONE_ID, h.id):
            m = out.setdefault(h.id, Milestone(h.id, {}, None, None))
            m.section = h
            m.fields = md.fields_in(doc.lines, h.line + 1, h.end)
    return sorted(out.values(), key=lambda m: int(m.id[1:]))


def status_column(head: list[str]) -> str | None:
    for h in head:
        if h.lower().startswith("status"):
            return h
    return None


# ---- contract and architecture ---------------------------------------------------------------

@dataclass
class Symbol:
    id: str                            # pkg.symbol
    title: str
    doc: Doc
    start: int
    end: int
    fields: dict[str, str]


def symbols(doc: Doc) -> list[Symbol]:
    return [Symbol(h.id, h.title, doc, h.line, h.end, md.fields_in(doc.lines, h.line + 1, h.end))
            for h in doc.headings if h.id and re.fullmatch(md.SYMBOL_ID, h.id)]


@dataclass
class Component:
    id: str
    row: dict[str, str]
    doc: Doc
    line: int

    @property
    def covers(self) -> list[str]:
        return md.expand_refs(self.row.get("Covers", ""))

    @property
    def depends_on(self) -> list[str]:
        raw = self.row.get("Depends on") or self.row.get("Depends") or ""
        return [md.strip_md(x) for x in md.split_list(raw) if md.strip_md(x) not in ("—", "-", "", "nothing")]


def components(doc: Doc) -> list[Component]:
    """Rows of a Components or Packages table (first column is the id, in backticks or plain)."""
    out = []
    for _, head, rows in doc.tables():
        if not head or head[0].lower() not in ("component", "package", "package id", "module"):
            continue
        for n, row in md.table_dicts(head, rows):
            cid = md.strip_md(row.get(head[0], "")).split()[0] if row.get(head[0]) else ""
            if cid:
                out.append(Component(cid, row, doc, n))
    return out


# ---- cross-doc helpers -----------------------------------------------------------------------

def todo_state(repo: Repo) -> dict[str, bool]:
    """Task ID → checked, from tasks/todo.md."""
    return {i.id: i.checked for i in todo_items(repo.todo)} if repo.todo else {}


def spine_pipeline(task: Task) -> str | None:
    """The pipeline a Phase 0 (spine) task builds, from its Step field (`PL-01` or `PL-01.step`)."""
    if not task.is_spine:
        return None
    m = re.match(r"PL-\d{2,}", task.step)
    return m.group(0) if m else None


def spine_done(repo: Repo) -> dict[str, bool]:
    """Pipeline ID → whether its spine task is checked in todo.md (active plan only)."""
    if not repo.plan:
        return {}
    state = todo_state(repo)
    out: dict[str, bool] = {}
    for t in tasks(repo.plan):
        pl = spine_pipeline(t)
        if pl:
            out[pl] = out.get(pl, False) or state.get(t.id, False)
    return out


def pipeline_built(repo: Repo, pipeline: Pipeline, spine: dict[str, bool] | None = None) -> bool:
    """Its spine task is checked in todo.md; for a pipeline the active plan has no spine task for (built in
    an earlier milestone), its entry file exists. Pass `spine_done(repo)` when checking several."""
    spine = spine_done(repo) if spine is None else spine
    if pipeline.id in spine:
        return spine[pipeline.id]
    return bool(pipeline.entry_file) and (repo.root / pipeline.entry_file).is_file()


def smoke_command(repo: Repo, pipeline_id: str) -> str | None:
    """The pipeline's smoke command: tests.md Strategy's Smoke cell, else its Trigger + ` --smoke`."""
    for doc in repo.docs("tests"):
        for row in strategy_rows(doc):
            if re.search(rf"\b{re.escape(pipeline_id)}\b", row.get("Pipeline", "")):
                cmds = re.findall(r"`([^`]+)`", row.get("Smoke", ""))
                if cmds:
                    return cmds[0]
    for p in all_pipelines(repo):
        if p.id == pipeline_id and p.trigger:
            return p.trigger + " --smoke"
    return None
