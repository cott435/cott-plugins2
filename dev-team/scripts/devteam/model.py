"""Typed views over the planning docs: tasks, checkpoints, todo items, pipelines, test cases, milestones,
contract symbols and components. Each is read from a `Doc` by the shared markdown helpers in `md`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import md
from .repo import Doc, Repo

# ---- plan ------------------------------------------------------------------------------------

TASK_FIELDS = ("Package", "Step", "Kind", "Covers", "Size", "Mode", "Skills", "Read", "Verify",
               "Depends on", "Writes", "Parallel", "Files likely", "Blocked", "Reason")
# A task's kind (`**Kind:**`), in the order a milestone usually runs them (interface-first-design.md §5.1).
KINDS = ("interface", "spine", "wiring", "thicken", "system")
# The fields an interface-first plan replaces: groups are derived from the graph, Writes is the exclusive claim.
DEPRECATED_FIELDS = {"Parallel": "groups are derived from Depends on (`dt ready`, `dt status` waves)",
                     "Files likely": "use **Writes:**, the task's exclusive claim"}


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
    def kind(self) -> str:
        """`interface | spine | wiring | thicken | system`, lower-cased; "" when the task has no Kind."""
        v = md.strip_md(self.get("Kind")).split()
        return v[0].lower() if v else ""

    @property
    def writes(self) -> list[str]:
        """The paths the task writes, exclusively (`**Writes:**`, exact paths or one directory glob); a task
        from before Writes falls back to its `Files likely`."""
        raw = self.get("Writes") if "Writes" in self.fields else self.get("Files likely")
        return [w.strip("`").strip().removeprefix("./") for w in md.split_list(raw)
                if w.strip("`").strip().lower() not in ("", "—", "-", "none")]

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
        """Builds a skeleton rather than behaviour: an interface or spine task, or (a task with no Kind) any
        Phase 0 task, the contract task included."""
        if self.kind:
            return self.kind in ("interface", "spine")
        return "spine" in self.phase.lower() or self.phase.lower().startswith("phase 0")

    @property
    def is_contract(self) -> bool:
        """The task that freezes the milestone's boundaries: `**Kind:** interface`, or the Phase 0 contract task
        (`**Step:** contract`) of a plan from before Kind."""
        if self.kind:
            return self.kind == "interface"
        return self.is_spine and self.step.lower() == "contract"

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


GRAPH_HEADING = "dependency graph"
EDGE_KINDS = ("data", "call", "file", "code", "contract-change", "order")


@dataclass
class Edge:
    """A `## Dependency graph` row: `src` depends on `dst` (From → To, as `Depends on`). `mitigated_by` is the
    interface text (`stats.Cov sample (M1-T01)`), "" when the cell starts with `none`; `reason` is the text
    after `none:`. A mitigated edge doesn't order the tasks."""
    src: str
    dst: str
    kind: str
    mitigated_by: str
    reason: str
    line: int = -1                     # 0-based row line in the plan doc
    cells: tuple = ()                  # the raw From, To, Kind, Mitigated by cells

    @property
    def mitigated(self) -> bool:
        return bool(self.mitigated_by)


def graph_section(doc: Doc) -> md.Heading | None:
    return next((h for h in doc.headings if not h.id and h.text.strip().lower() == GRAPH_HEADING), None)


def graph_edges(doc: Doc) -> list[Edge]:
    """The rows of a plan's `## Dependency graph` table (From | To | Kind | Mitigated by)."""
    h = graph_section(doc)
    if h is None:
        return []
    out = []
    for _, head, rows in doc.tables(h.line + 1, h.end):
        if not head or md.strip_md(head[0]).lower() != "from":
            continue
        for n, row in md.table_dicts(head, rows):
            src, dst = (md.task_refs(_col(row, c)) for c in ("From", "To"))
            kind = md.strip_md(_col(row, "Kind")).lower()
            cell = _col(row, "Mitigat").strip()
            plain = md.strip_md(cell)
            if re.match(r"none\b", plain, re.IGNORECASE) or plain in ("", "—", "-"):
                reason = re.sub(r"^none\s*:?\s*", "", plain, flags=re.IGNORECASE).strip()
                mitigated, reason = "", "" if reason in ("—", "-") else reason
            else:
                mitigated, reason = cell, ""
            out.append(Edge(src[0] if src else "", dst[0] if dst else "", kind, mitigated, reason, n,
                            (_col(row, "From"), _col(row, "To"), _col(row, "Kind"), cell)))
    return out


def is_interface_first(doc: Doc) -> bool:
    """A plan written to interface-first-design: a `## Dependency graph` section, or a task with Kind/Writes."""
    return graph_section(doc) is not None or any("Kind" in t.fields or "Writes" in t.fields for t in tasks(doc))


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

    def _side(self, n: int) -> str:
        parts = re.split(r"→|->", self.io, maxsplit=1)
        return parts[n] if len(parts) == 2 else (self.io if n == 1 else "")

    @property
    def in_types(self) -> list[str]:
        """Type names on the In side of the `In → Out` cell (CamelCase or `pkg.Name`)."""
        return type_names(self._side(0))

    @property
    def out_types(self) -> list[str]:
        return type_names(self._side(1))


TYPE_NAME = re.compile(r"(?<![\w.])(?:[a-z][a-z0-9_]*\.)*[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)*\b")


def type_names(text: str) -> list[str]:
    """CamelCase names in an `In → Out` cell, qualified ones kept whole: `Cov, T → stats.Cov` → [Cov, stats.Cov].
    Single capitals (`T`, `N`) and all-caps words (`CSV`) aren't types."""
    return list(dict.fromkeys(TYPE_NAME.findall(md.strip_md(text))))


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
#
# Two tables. Stages (`S<n>`, written by idea-refine) are outcomes the user agreed: Name, Source, Status*,
# and a `## S<n>` section with Outline and Skills. Milestones (`M<n>`, written by build-planning once the
# stage's pipelines are approved) are build-sized vertical slices of one stage: Stage, Name, Packages,
# Pipelines, Depends, Status*, and a `## M<n>` section. A roadmap from before stages has only the milestone
# table, with a Source column and no Stage column: each of its milestones stands for its own stage.

@dataclass
class Stage:
    id: str
    row: dict[str, str]                # stage table row ({} if only a section exists)
    row_line: int | None
    section: md.Heading | None
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.row.get("Name") or (self.section.title if self.section else "")

    @property
    def source(self) -> str:
        return self.row.get("Source", "")

    @property
    def skills(self) -> list[str]:
        """The section's `**Skills:**` line (idea-refine writes it): skills routed to this stage."""
        return skill_names(self.fields.get("Skills", ""))

    @property
    def pipelines(self) -> list[str]:
        """A stage lists no pipelines: `dt` infers them from its Source until build-planning cuts it."""
        return []

    @property
    def packages(self) -> list[str]:
        return []


@dataclass
class Milestone:
    id: str
    row: dict[str, str]                # roadmap table row ({} if only a section exists)
    row_line: int | None
    section: md.Heading | None
    fields: dict[str, str] = field(default_factory=dict)
    stage_of: Stage | None = None      # the stage its Stage cell names (None on a pre-stage roadmap)

    @property
    def name(self) -> str:
        return self.row.get("Name") or (self.section.title if self.section else "")

    @property
    def stage(self) -> str:
        """The `S<n>` its Stage cell names, or ""."""
        m = re.search(rf"\b{md.STAGE_ID}\b", self.row.get("Stage", ""))
        return m.group(0) if m else ""

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
        """Its own Source cell (pre-stage roadmaps), else its stage's."""
        own = self.row.get("Source", "")
        if md.strip_md(own) not in ("", "—", "-"):
            return own
        return self.stage_of.source if self.stage_of else own

    @property
    def skills(self) -> list[str]:
        """The section's `**Skills:**` line; with none, its stage's (build-planning narrows a stage's skills
        per milestone when it cuts the stage into several)."""
        if "Skills" in self.fields or self.stage_of is None:
            return skill_names(self.fields.get("Skills", ""))
        return self.stage_of.skills

    @property
    def references(self) -> list[str] | None:
        """The section's `**References:**` RF IDs, or None when it has no such line."""
        if "References" not in self.fields:
            return None
        return re.findall(rf"\b{REFERENCE_ID}\b", self.fields["References"])


def skill_names(value: str) -> list[str]:
    """`data-analysis, null-hypothesis-testing (claims)` → names; `—`/none → []."""
    out = [md.strip_md(s).split(" (")[0].strip() for s in md.split_list(value)]
    return [s for s in out if s and s.lower() not in ("—", "-", "none")]


def _id_rows(doc: Doc, first_col: str, id_pat: str) -> list[tuple[str, dict[str, str], int]]:
    out = []
    for _, head, rows in doc.tables():
        if not head or head[0].lower() != first_col:
            continue
        for n, row in md.table_dicts(head, rows):
            rid = md.strip_md(row.get(head[0], ""))
            if re.fullmatch(id_pat, rid):
                out.append((rid, row, n))
    return out


def stages(doc: Doc) -> list[Stage]:
    out: dict[str, Stage] = {rid: Stage(rid, row, n, None) for rid, row, n in _id_rows(doc, "stage", md.STAGE_ID)}
    for h in doc.headings:
        if h.id and re.fullmatch(md.STAGE_ID, h.id):
            s = out.setdefault(h.id, Stage(h.id, {}, None, None))
            s.section = h
            s.fields = md.fields_in(doc.lines, h.line + 1, h.end)
    return sorted(out.values(), key=lambda s: int(s.id[1:]))


def milestones(doc: Doc) -> list[Milestone]:
    out: dict[str, Milestone] = {rid: Milestone(rid, row, n, None)
                                 for rid, row, n in _id_rows(doc, "milestone", md.MILESTONE_ID)}
    for h in doc.headings:
        if h.id and re.fullmatch(md.MILESTONE_ID, h.id):
            m = out.setdefault(h.id, Milestone(h.id, {}, None, None))
            m.section = h
            m.fields = md.fields_in(doc.lines, h.line + 1, h.end)
    by_id = {s.id: s for s in stages(doc)}
    for m in out.values():
        m.stage_of = by_id.get(m.stage)
    return sorted(out.values(), key=lambda m: int(m.id[1:]))


def stage_milestones(doc: Doc, stage: str) -> list[Milestone]:
    return [m for m in milestones(doc) if m.stage == stage]


def status_column(head: list[str]) -> str | None:
    for h in head:
        if h.lower().startswith("status"):
            return h
    return None


# ---- references -----------------------------------------------------------------------------

REFERENCE_ID = r"RF-\d{2,}"


@dataclass
class Reference:
    """An `RF-NN` section of docs/references.md: `**File:** … · **Hash:** … · **Kind:** … · **Milestones:** …`
    plus bullet fields (Purpose, Key parts, In → Out, Use for, Caveats)."""
    id: str
    title: str
    doc: Doc
    start: int
    end: int
    fields: dict[str, str]

    def _get(self, key: str) -> str:
        v = md.strip_md(self.fields.get(key, ""))
        return "" if v.lower() in ("—", "-", "none") else v

    @property
    def file(self) -> str:
        return self._get("File")

    @property
    def hash(self) -> str:
        return self._get("Hash")

    @property
    def kind(self) -> str:
        return self._get("Kind").lower()

    @property
    def milestones(self) -> list[str]:
        """`S<n>` (stage) and `M<n>` IDs, `["all"]`, or [] (`—`: not assigned yet)."""
        value = self._get("Milestones")
        if value.lower() == "all":
            return ["all"]
        return list(dict.fromkeys(re.findall(r"\b[SM]\d+\b", value)))

    def serves(self, milestone: str) -> bool:
        return "all" in self.milestones or milestone in self.milestones

    @property
    def caveats(self) -> str:
        return self.fields.get("Caveats", "").strip()

    @property
    def text(self) -> str:
        return "\n".join(self.doc.lines[self.start:self.end]).rstrip() + "\n"


def references(doc: Doc) -> list[Reference]:
    """Live RF sections (retired entries are one struck line, not sections)."""
    out = []
    for h in doc.headings:
        if h.id and re.fullmatch(REFERENCE_ID, h.id) and "~~" not in h.title:
            fields = dict(md.bullet_fields(doc.lines, h.line + 1, h.end))
            fields.update(md.fields_in(doc.lines, h.line + 1, h.end))
            out.append(Reference(h.id, h.title, doc, h.line, h.end, fields))
    return out


def all_references(repo: Repo) -> list[Reference]:
    return references(repo.references) if repo.references else []


def milestone_references(repo: Repo, milestone: str) -> list[str]:
    """The RF IDs that serve a milestone or stage, derived and never listed twice: those whose `Milestones`
    field names it (or `all`); for a milestone, also its section's `**References:**` line, or with no such
    line, the references assigned to its stage."""
    refs = all_references(repo)
    out = [r.id for r in refs if r.serves(milestone)]
    ms = next((m for m in milestones(repo.roadmap) if m.id == milestone), None) if repo.roadmap else None
    if ms is not None:
        if ms.references is not None:
            extra = ms.references
        else:
            extra = [r.id for r in refs if ms.stage and ms.stage in r.milestones]
        out += [i for i in extra if i not in out]
    return out


def split_ref(item: str) -> tuple[str, str]:
    """A `Read:` item `RF-01:pca_factors` → ("RF-01", "pca_factors"); anything else → (item, "")."""
    m = re.fullmatch(rf"({REFERENCE_ID}):(.+)", item.strip())
    return (m.group(1), m.group(2).strip()) if m else (item.strip(), "")


# ---- contract and architecture ---------------------------------------------------------------

@dataclass
class Symbol:
    id: str                            # pkg.symbol
    title: str
    doc: Doc
    start: int
    end: int
    fields: dict[str, str]


    @property
    def is_type(self) -> bool:
        """A boundary type (`**Kind:** type`, or a heading titled `type`), not a function."""
        kind = md.strip_md(self.fields.get("Kind", "")).lower()
        return kind.startswith("type") or md.strip_md(self.title).lower() == "type"

    @property
    def name(self) -> str:
        return self.id.rsplit(".", 1)[1]

    @property
    def package(self) -> str | None:
        return self.doc.package

    @property
    def sample(self) -> str:
        """The `**Sample:**` path of a type section, or ""."""
        v = md.strip_md(self.fields.get("Sample", ""))
        return "" if v.lower() in ("", "—", "-", "none") else v

    @property
    def text(self) -> str:
        return "\n".join(self.doc.lines[self.start:self.end]).rstrip() + "\n"


def symbols(doc: Doc) -> list[Symbol]:
    return [Symbol(h.id, h.title, doc, h.line, h.end, md.fields_in(doc.lines, h.line + 1, h.end))
            for h in doc.headings if h.id and re.fullmatch(md.SYMBOL_ID, h.id)]


def all_symbols(repo: Repo) -> list[Symbol]:
    return [s for d in repo.docs("contract") for s in symbols(d)]


def contract_types(repo: Repo) -> dict[str, Symbol]:
    """Every contract type section by its ID (`stats.Cov`) and by its bare name (`Cov`; first one wins)."""
    out: dict[str, Symbol] = {}
    for s in all_symbols(repo):
        if s.is_type:
            out.setdefault(s.id, s)
            out.setdefault(s.name, s)
    return out


def resolve_type(types: dict[str, Symbol], name: str) -> Symbol | None:
    """A type name from a step table (`Cov`, `stats.Cov`, or `quant.stats.Cov`) → its contract section."""
    parts = name.split(".")
    for k in range(len(parts)):
        hit = types.get(".".join(parts[k:]))
        if hit is not None:
            return hit
    return None


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
    """The pipeline a task makes run end to end, from its Step field (`PL-01` or `PL-01.step`): its wiring task,
    or in a plan from before Kind, its Phase 0 spine task."""
    if task.kind:
        if task.kind != "wiring":
            return None
    elif not task.is_spine:
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
