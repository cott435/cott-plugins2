"""Check the planning docs: IDs, references, size budgets, task rules, fences and headers.

One small function per check code (see scripts/README.md for the list). Each takes a `Context` and yields
`Problem`s; `lint()` runs them all, turns a crashing check into an `internal` warning, and keeps only the
problems located in the files asked for. Cross-doc checks always read the whole repo.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from .. import git, md, model
from .. import references as refs
from ..repo import Repo
from ..status.common import available_skills

# code → severity (E fails the run, W doesn't)
SEVERITY = {
    "dup-id": "E", "missing-ref": "E", "retired-ref": "E", "budget": "W", "approved-edit": "W",
    "prebuild-left": "E", "task-size": "E", "task-acceptance": "E", "task-title": "E", "task-fields": "E",
    "task-step": "W", "depends": "E", "parallel": "E", "verify-smoke": "E", "todo-mismatch": "E",
    "finding-disposition": "E", "foreign-plan": "W", "broken-fence": "E", "header": "E",
    "unreadable": "E", "internal": "W", "pipeline-fields": "E", "spine-mock": "W",
    "fixture-size": "W",                # missing fixture files are reported as E
    "ref-file": "E", "ref-hash": "W", "ref-large": "W", "ref-prefix": "E", "roadmap-skill": "W",
}

# Size budgets (planning-stage.md §3), in lines.
BUDGETS = {"contract": 60, "pipelines": 120, "tests": 120, "plan": 400, "queued-plan": 400}
ROADMAP_SECTION_MAX = 6
AGENTS_DOC_MAP_MAX = 25

FIXTURE_MAX_BYTES = 100 * 1024
SPINE_MOCK = re.compile(r"\b(mock|stub|fake|todo|placeholder)", re.IGNORECASE)

SIZE_FILES = {"XS": (1, 1), "S": (1, 2), "M": (3, 5)}
REQUIRED_TASK_FIELDS = ("Package", "Step", "Size", "Mode", "Read", "Acceptance", "Verify")

# Fields and table columns whose IDs must resolve. `Depends on` is checked by `depends`.
REF_FIELDS = {"Read", "Covers", "Step", "Pipeline", "Used by", "Part of", "References"}
REF_COLUMNS = {"covers", "pipeline", "pipelines", "used by", "read"}
PATH_LIKE = re.compile(r"\.(md|py|toml|json|ya?ml|txt|csv|cfg|ini|sh|ipynb|lock|j2|html|parquet)$")
NONE_VALUES = ("", "—", "-", "none")

LINTED_ROOT_FILES = ("CONSTRAINTS.md", "AGENTS.md", "CLAUDE.md")


@dataclass
class Problem:
    path: str
    line: int          # 1-based; 0 when the problem isn't tied to a line
    code: str
    message: str
    sev: str = ""      # overrides the code's usual severity

    @property
    def severity(self) -> str:
        return self.sev or SEVERITY.get(self.code, "E")

    def as_dict(self) -> dict:
        return {"path": self.path, "line": self.line, "code": self.code, "severity": self.severity,
                "message": self.message}

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.code} {self.message}"


class Context:
    """The repo plus what the checks share: which files are in scope, and the parsed plans."""

    def __init__(self, repo: Repo, scope: set[str] | None = None):
        self.repo = repo
        self.scope = scope            # repo-relative paths (or folder prefixes ending in "/"); None = all

    def in_scope(self, rel: str) -> bool:
        if self.scope is None:
            return True
        return rel in self.scope or any(s.endswith("/") and rel.startswith(s) for s in self.scope)

    @cached_property
    def docs(self):
        return self.repo.docs()

    @cached_property
    def scoped_docs(self):
        return [d for d in self.docs if self.in_scope(d.rel)]

    @cached_property
    def plan_docs(self):
        """The active plan and queued plans written by build-planning (a foreign plan is left alone)."""
        return [d for d in self.repo.docs("plan", "queued-plan") if model.is_dev_team_plan(d)]

    @cached_property
    def tasks(self) -> list[model.Task]:
        return [t for d in self.plan_docs for t in model.tasks(d)]

    @cached_property
    def pipelines(self) -> dict[str, model.Pipeline]:
        return {p.id: p for p in model.all_pipelines(self.repo)}

    def resolves(self, id_: str) -> bool:
        return self.repo.lookup(id_) is not None


def _p(doc, line_index: int, code: str, message: str) -> Problem:
    return Problem(doc.rel, line_index + 1, code, message)


def _changelog_ranges(doc) -> list[tuple[int, int]]:
    return [(h.line, h.end) for h in doc.headings if h.text.lower().startswith("changelog")]


def _inside(i: int, ranges) -> bool:
    return any(a <= i < b for a, b in ranges)


def _read_ids(value: str) -> list[str]:
    """IDs in a `Read:` value; repo paths and free text are skipped. `PL-02.step` → `PL-02`,
    `RF-01:pca_factors` → `RF-01`."""
    out = []
    for item in md.split_list(value):
        item = model.split_ref(md.strip_md(item.split(" (")[0]))[0]
        if item.lower() in NONE_VALUES or "/" in item or PATH_LIKE.search(item):
            continue
        m = re.fullmatch(rf"({md.REQ_ID})\.\w+", item)
        if m:
            out.append(m.group(1))
        elif re.fullmatch(md.HEADING_ID, item):
            out.append(item)
    return out


def _contract_symbols(ids: list[str]) -> set[str]:
    return {i for i in ids if re.fullmatch(md.SYMBOL_ID, i)}


def _ref_values(doc):
    """(line index, field or column name, value) for every reference field and column outside changelogs."""
    skip = _changelog_ranges(doc)
    for i, line in enumerate(doc.lines):
        if doc.mask[i] or "**" not in line or _inside(i, skip):
            continue
        for key, value in md.split_fields(line).items():
            if key in REF_FIELDS:
                yield i, key, value
    for _, head, rows in doc.tables():
        cols = [(k, h) for k, h in enumerate(head) if md.strip_md(h).rstrip("*").strip().lower() in REF_COLUMNS]
        for n, cells in rows:
            if _inside(n, skip):
                continue
            for k, h in cols:
                if k < len(cells):
                    yield n, md.strip_md(h), cells[k]


# ---- ID checks ------------------------------------------------------------------------------------

def check_dup_id(ctx: Context):
    """An ID with two live definitions, or one that is both retired and still defined."""
    for id_, defs in ctx.repo.index.items():
        live = [d for d in defs if not d.retired]
        for d in live[1:]:
            yield _p(d.doc, d.start, "dup-id", f"{id_} is already defined at {live[0].where}")
        if live:
            for d in defs:
                if d.retired and d.how == "retired":
                    yield _p(live[0].doc, live[0].start, "dup-id", f"{id_} is retired at {d.where} but still defined here")


def check_missing_ref(ctx: Context):
    for doc in ctx.docs:
        for i, key, value in _ref_values(doc):
            ids = _read_ids(value) if key == "Read" else md.expand_refs(value)
            for id_ in ids:
                if not ctx.resolves(id_):
                    yield _p(doc, i, "missing-ref", f"{key}: {id_} is not defined")


def _retired_exemptions(repo: Repo) -> dict[str, list[tuple[str, int, int]]]:
    """Retired ID → (doc, start, end) regions where mentioning it is fine: the superseding decision."""
    out: dict[str, list[tuple[str, int, int]]] = {}
    for d in repo.all_definitions:
        if d.retired and d.how == "heading":
            m = re.search(r"Superseded by\s+(AD-\d{2,})", d.retired_note)
            if m:
                by = repo.lookup(m.group(1))
                if by is not None:
                    out.setdefault(d.id, []).append((by.doc.rel, by.start, by.end))
    return out


def check_retired_ref(ctx: Context):
    """A literal mention of a retired ID, outside retired lines/sections, its superseder and Changelogs."""
    retired = sorted(i for i in ctx.repo.index if ctx.repo.is_retired(i))
    if not retired:
        return
    pat = re.compile(r"(?<![\w.])(" + "|".join(re.escape(i) for i in retired) + r")(?![\w-])")
    exempt_by_id = _retired_exemptions(ctx.repo)
    history: dict[str, list[tuple[int, int]]] = {}
    for d in ctx.repo.all_definitions:
        if d.retired:
            history.setdefault(d.doc.rel, []).append((d.start, d.end))
    for doc in ctx.docs:
        skip = history.get(doc.rel, []) + _changelog_ranges(doc)
        for i, line in enumerate(doc.lines):
            if doc.mask[i] or _inside(i, skip):
                continue
            for m in pat.finditer(line):
                id_ = m.group(1)
                if any(rel == doc.rel and a <= i < b for rel, a, b in exempt_by_id.get(id_, [])):
                    continue
                note = ctx.repo.lookup(id_).retired_note if ctx.repo.lookup(id_) else ""
                yield _p(doc, i, "retired-ref", f"{id_} is retired ({note})" if note else f"{id_} is retired")


# ---- per-doc checks -------------------------------------------------------------------------------

def check_budget(ctx: Context):
    for doc in ctx.scoped_docs:
        limit = BUDGETS.get(doc.kind)
        if limit and len(doc.lines) > limit:
            yield _p(doc, 0, "budget", f"{len(doc.lines)} lines, budget {limit} ({doc.kind})")
        if doc.kind == "roadmap":
            for h in doc.headings:
                if h.id and re.fullmatch(md.MILESTONE_ID, h.id):
                    n = sum(1 for line in doc.lines[h.line + 1:h.end] if line.strip())
                    if n > ROADMAP_SECTION_MAX:
                        yield _p(doc, h.line, "budget", f"{h.id} section is {n} lines, budget {ROADMAP_SECTION_MAX}")
        if doc.kind == "agents":
            docs_h = doc.heading("Docs")
            if docs_h:
                skills_h = doc.heading("Project skills")
                end = skills_h.end if skills_h and skills_h.line >= docs_h.end else docs_h.end
                n = end - docs_h.line
                if n > AGENTS_DOC_MAP_MAX:
                    yield _p(doc, docs_h.line, "budget", f"doc map is {n} lines, budget {AGENTS_DOC_MAP_MAX}")


def _body_without_header(lines: list[str]) -> list[str]:
    _, header_line, _, _ = md.header(lines)
    body = [line.rstrip() for n, line in enumerate(lines) if n != header_line]
    while body and not body[-1]:
        body.pop()
    return body


USED_BY_LINE = re.compile(r"^\s*(?:[-*]\s+)?\*\*Used by:?\*\*", re.IGNORECASE)
HASH_VALUE = re.compile(r"(\*\*Hash:\*\*)[^·]*")


def _approved_body(doc_kind: str, lines: list[str]) -> list[str]:
    """The text approved-edit compares: no header line, no trailing blank lines, and for contract.md no
    `**Used by:**` lines (pipeline-design appends PL IDs there without a Revise), and for references.md no
    Hash values (`dt references --stamp` writes them)."""
    body = _body_without_header(lines)
    if doc_kind == "contract":
        body = [line for line in body if not USED_BY_LINE.match(line)]
    if doc_kind == "references":
        body = [HASH_VALUE.sub(r"\1 ", line) for line in body]
    return body


def check_approved_edit(ctx: Context):
    candidates = [d for d in ctx.scoped_docs if d.kind not in ("plan", "todo", "roadmap", "queued-plan")
                  and (d.status or "").startswith("Approved")]
    if not candidates or not git.is_repo(ctx.repo.root):
        return
    for doc in candidates:
        head = git.show_head(ctx.repo.root, doc.rel)
        if head is None:
            continue
        head_lines = head.splitlines()
        fields, *_ = md.header(head_lines)
        if not fields.get("Status", "").startswith("Approved"):
            continue
        if _approved_body(doc.kind, head_lines) != _approved_body(doc.kind, doc.lines):
            line = doc.header_line if doc.header_line is not None else 0
            yield _p(doc, line, "approved-edit",
                     "Approved doc changed since HEAD without going back to Draft (or the approval isn't committed)")


def check_prebuild_left(ctx: Context):
    """A pre-build section left after its pipeline is built (same rule as `dt prebuild-clear`)."""
    spine = model.spine_done(ctx.repo)
    for doc in ctx.repo.docs("pipelines", "architecture"):
        pls = model.pipelines(doc)
        built = {p.id: model.pipeline_built(ctx.repo, p, spine) for p in pls}
        for h in doc.prebuild_sections():
            parent = next((p for p in pls if p.start < h.line < p.end), None)
            if parent is not None:
                if built[parent.id]:
                    yield _p(doc, h.line, "prebuild-left", f"{parent.id} is built; run `dt prebuild-clear {parent.id}`")
            elif pls and all(built.values()):
                yield _p(doc, h.line, "prebuild-left",
                         "every pipeline here is built; run `dt prebuild-clear` for the last one")


# ---- pipeline and test-case checks ----------------------------------------------------------------

def _empty(cell: str) -> bool:
    return md.strip_md(cell).lower() in NONE_VALUES


def _has_steps(doc, p: model.Pipeline) -> bool:
    """A step table (any table) or numbered steps (`1. <pkg> → <pkg>: <contract>`) directly in the section."""
    if p.steps:
        return True
    body_end = next((h.line for h in doc.headings if p.start < h.line < p.end), p.end)
    if any(True for _ in doc.tables(p.start + 1, body_end)):
        return True
    return any(re.match(r"\s*\d+[.)]\s+\S", doc.lines[i]) and not doc.mask[i] for i in range(p.start + 1, body_end))


def check_pipeline_fields(ctx: Context):
    """Package pipelines need Entry, Trigger and filled Owner/Spine version cells. System pipelines (root
    architecture.md) are package → package over named contracts: Trigger and steps only."""
    for doc in ctx.repo.docs("pipelines", "architecture"):
        for p in model.pipelines(doc):
            required = ("Trigger",) if p.is_system else ("Entry", "Trigger")
            missing = [k for k in required if _empty(p.fields.get(k, ""))]
            if p.is_system and not _has_steps(doc, p):
                missing.append("step table")
            if missing:
                yield _p(doc, p.start, "pipeline-fields", f"{p.id} has no {' or '.join(missing)}")
            if p.is_system:
                continue
            for s in p.steps:
                empty = [k for k, v in (("Owner", s.owner), ("Spine version", s.spine)) if _empty(v)]
                if empty:
                    yield _p(doc, s.line, "pipeline-fields", f"{p.id} step `{s.name}` has an empty {' and '.join(empty)} cell")


def check_spine_mock(ctx: Context):
    for doc in ctx.repo.docs("pipelines"):      # system pipelines (architecture.md) have no spine versions
        for p in model.pipelines(doc):
            for s in p.steps:
                m = SPINE_MOCK.search(s.spine)
                if m:
                    yield _p(doc, s.line, "spine-mock",
                             f"{p.id} step `{s.name}` spine version says {m.group(1)!r}: the spine must be a real baseline")


def _folder_bytes(folder: Path) -> int:
    total = 0
    for d, _, files in os.walk(folder):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(d, f))
            except OSError:
                pass
    return total


def check_fixture_size(ctx: Context):
    """Each TC's Fixture folder exists with input.json and expected.json (E) and stays under 100 KB (W)."""
    root = ctx.repo.root
    seen: set[str] = set()
    for doc in ctx.repo.docs("tests"):
        for tc in model.test_cases(doc):
            rel = tc.fixture.strip().rstrip("/")
            if _empty(rel):
                continue
            seen.add(rel)
            folder = root / rel
            if not folder.is_dir():
                yield Problem(doc.rel, tc.start + 1, "fixture-size", f"{tc.id} Fixture folder {rel}/ doesn't exist", "E")
                continue
            for name in ("input.json", "expected.json"):
                if not (folder / name).is_file():
                    yield Problem(doc.rel, tc.start + 1, "fixture-size", f"{tc.id} Fixture {rel}/ has no {name}", "E")
            size = _folder_bytes(folder)
            if size > FIXTURE_MAX_BYTES:
                yield _p(doc, tc.start, "fixture-size",
                         f"{tc.id} Fixture {rel}/ is {size // 1024} KB (budget 100 KB; store large data as path + hash)")
    for folder in sorted((root / "tests" / "fixtures").glob("*/TC-*")):
        rel = folder.relative_to(root).as_posix()
        if folder.is_dir() and rel not in seen:
            size = _folder_bytes(folder)
            if size > FIXTURE_MAX_BYTES:
                yield Problem(rel + "/", 0, "fixture-size", f"{size // 1024} KB (budget 100 KB)")


# ---- reference checks -----------------------------------------------------------------------------

def check_ref_file(ctx: Context):
    """An RF entry with no File, or whose file is gone (reference-intake retires it)."""
    for e in model.all_references(ctx.repo):
        if not e.file:
            yield _p(e.doc, e.start, "ref-file", f"{e.id} has no **File:**")
        elif not (ctx.repo.root / e.file).is_file():
            yield _p(e.doc, e.start, "ref-file", f"{e.id} file {e.file} is missing (run reference-intake)")


def check_ref_hash(ctx: Context):
    """An RF entry whose Hash isn't the file's current one (or is unstamped)."""
    for e in model.all_references(ctx.repo):
        current = refs.file_hash(ctx.repo.root / e.file) if e.file else None
        if current is not None and current != e.hash.lower():
            what = f"Hash {e.hash} is stale (file now {current})" if e.hash else "has no Hash"
            yield _p(e.doc, e.start, "ref-hash", f"{e.id} {what}: run reference-intake, then `dt references --stamp`")


def check_ref_large(ctx: Context):
    """A task reads a reference over 300 lines with no selector (it would get only the outline)."""
    entries = {e.id: e for e in model.all_references(ctx.repo)}
    sizes: dict[str, int] = {}
    for t in ctx.tasks:
        line = md.field_line(t.doc.lines, t.start, t.end, "Read")
        for item in t.read:
            rid, selector = model.split_ref(md.strip_md(item.split(" (")[0]))
            e = entries.get(rid)
            if e is None or selector or not e.file:
                continue
            if e.file not in sizes:
                sizes[e.file] = refs.line_count(ctx.repo, e.file)
            if sizes[e.file] > refs.LARGE_LINES:
                yield _p(t.doc, t.start if line is None else line, "ref-large",
                         f"{t.id} reads {rid} ({e.file}, {sizes[e.file]} lines) whole: name a part, "
                         f"{rid}:<symbol>, {rid}:<heading> or {rid}:outline")


def check_ref_prefix(ctx: Context):
    """`RF` is reserved for reference entries: a spec requirement must not use it."""
    spec = ctx.repo.spec
    if spec is None:
        return
    for b in md.bold_leads(spec.lines, spec.mask):
        if b.id.startswith("RF-"):
            yield _p(spec, b.line, "ref-prefix", f"{b.id}: the RF prefix is reserved for docs/references.md")


def check_roadmap_skill(ctx: Context):
    """A roadmap milestone's `**Skills:**` names a skill that isn't installed."""
    roadmap = ctx.repo.roadmap
    if roadmap is None:
        return
    available = set(available_skills(ctx.repo))
    for ms in model.milestones(roadmap):
        if ms.section is None:
            continue
        missing = [s for s in ms.skills if s not in available]
        if missing:
            line = md.field_line(roadmap.lines, ms.section.line + 1, ms.section.end, "Skills")
            yield _p(roadmap, ms.section.line if line is None else line, "roadmap-skill",
                     f"{ms.id} Skills names {', '.join(missing)}: not installed (.claude/skills or the plugin)")


# ---- task checks ----------------------------------------------------------------------------------

def _acceptance_count(t: model.Task) -> int:
    lines = t.doc.lines
    i = md.field_line(lines, t.start + 1, t.end, "Acceptance")
    if i is None:
        return 0
    n = 0
    for line in lines[i + 1:t.end]:
        if not line.strip() or line.startswith((" ", "\t")):
            continue                  # blank, or a sub-bullet / continuation
        if re.match(r"^[-*]\s", line):
            n += 1
            continue
        break
    return n


def _files(t: model.Task) -> list[str]:
    return [f.removeprefix("./") for f in t.files_likely if f.lower() not in NONE_VALUES]


def check_task_size(ctx: Context):
    for t in ctx.tasks:
        if not t.size:
            continue                  # task-fields reports it
        if t.size not in SIZE_FILES:
            yield _p(t.doc, t.start, "task-size", f"{t.id} Size {t.size}: must be XS, S or M (split it)")
            continue
        lo, hi = SIZE_FILES[t.size]
        n = len(_files(t))
        if not lo <= n <= hi:
            want = f"{lo}" if lo == hi else f"{lo}–{hi}"
            yield _p(t.doc, t.start, "task-size", f"{t.id} Size {t.size} wants {want} Files likely, has {n}")


def check_task_acceptance(ctx: Context):
    for t in ctx.tasks:
        n = _acceptance_count(t)
        if n > 3:
            yield _p(t.doc, t.start, "task-acceptance", f"{t.id} has {n} acceptance bullets (max 3; split it)")


def check_task_title(ctx: Context):
    for t in ctx.tasks:
        if re.search(r"\band\b", md.strip_md(t.title), re.IGNORECASE):
            yield _p(t.doc, t.start, "task-title", f"{t.id} title has \"and\" (split it)")


def check_task_fields(ctx: Context):
    for t in ctx.tasks:
        missing = [k for k in REQUIRED_TASK_FIELDS
                   if k not in t.fields or (k != "Acceptance" and not t.get(k))]
        if missing:
            yield _p(t.doc, t.start, "task-fields", f"{t.id} missing {', '.join(missing)}")
        if t.get("Mode") and t.mode not in ("split", "solo"):
            yield _p(t.doc, t.start, "task-fields", f"{t.id} Mode {t.get('Mode')!r}: must be split or solo")


def check_task_step(ctx: Context):
    for t in ctx.tasks:
        for pl, step in re.findall(r"(PL-\d{2,})\.(\w+)", t.step):
            p = ctx.pipelines.get(pl)
            if p is not None and step not in [s.name for s in p.steps]:
                yield _p(t.doc, t.start, "task-step", f"{t.id} Step {pl}.{step}: no step `{step}` in {pl}'s table")


def check_depends(ctx: Context):
    for doc in ctx.plan_docs:
        tasks = model.tasks(doc)
        order = {t.id: n for n, t in enumerate(tasks)}
        graph = {t.id: t.depends_on for t in tasks}
        for t in tasks:
            line = md.field_line(doc.lines, t.start, t.end, "Depends on")
            line = t.start if line is None else line
            for dep in t.depends_on:
                if dep in order:
                    if order[dep] >= order[t.id]:
                        yield _p(doc, line, "depends", f"{t.id} depends on {dep}, which comes later (or is itself)")
                elif not ctx.resolves(dep):
                    yield _p(doc, line, "depends", f"{t.id} depends on {dep}, which isn't defined")
        for cycle in _cycles(graph):
            yield _p(doc, tasks[order[cycle[0]]].start, "depends", "cycle: " + " → ".join(cycle + [cycle[0]]))


def _cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """Each dependency cycle once, as the list of its nodes."""
    seen_cycles, out = set(), []
    state: dict[str, int] = {}          # 1 = on the stack, 2 = done
    stack: list[str] = []

    def visit(node):
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, []):
            if nxt not in graph:
                continue
            if state.get(nxt) == 1:
                cycle = stack[stack.index(nxt):]
                key = frozenset(cycle)
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    out.append(list(cycle))
            elif state.get(nxt) is None:
                visit(nxt)
        stack.pop()
        state[node] = 2

    for node in graph:
        if node not in state:
            visit(node)
    return out


def check_parallel(ctx: Context):
    for doc in ctx.plan_docs:
        groups: dict[str, list[model.Task]] = {}
        for t in model.tasks(doc):
            if t.parallel.lower() not in NONE_VALUES:
                groups.setdefault(t.parallel, []).append(t)
        for group, members in groups.items():
            for n, b in enumerate(members):
                for a in members[:n]:
                    files = sorted(set(_files(a)) & set(_files(b)))
                    syms = sorted(_contract_symbols(_read_ids(a.get("Read"))) & _contract_symbols(_read_ids(b.get("Read"))))
                    shared = files + syms
                    if shared:
                        yield _p(doc, b.start, "parallel",
                                 f"{b.id} and {a.id} are both in {group} but share {', '.join(shared)}")


def check_verify_smoke(ctx: Context):
    smoke: dict[str, str | None] = {}
    for t in ctx.tasks:
        if t.is_spine:
            continue
        verify = " ".join(t.get("Verify").split())
        for pl in dict.fromkeys(re.findall(r"PL-\d{2,}", t.step)):
            if pl not in smoke:
                smoke[pl] = model.smoke_command(ctx.repo, pl)
            cmd = smoke[pl]
            if cmd and " ".join(cmd.split()) not in verify:
                yield _p(t.doc, t.start, "verify-smoke", f"{t.id} Verify lacks {pl}'s smoke command `{cmd}`")


def check_todo_mismatch(ctx: Context):
    plan, todo = ctx.repo.plan, ctx.repo.todo
    if plan is None or todo is None or not model.is_dev_team_plan(plan):
        return
    planned = {t.id: t for t in model.tasks(plan)}
    listed = {i.id: i for i in model.todo_items(todo)}
    for id_, t in planned.items():
        if id_ not in listed:
            yield _p(plan, t.start, "todo-mismatch", f"{id_} is in plan.md but not in todo.md")
    for id_, item in listed.items():
        if id_ not in planned:
            yield _p(todo, item.line, "todo-mismatch", f"{id_} is in todo.md but not in plan.md")


def check_finding_disposition(ctx: Context):
    for doc in ctx.plan_docs:
        for cp in model.checkpoints(doc):
            for f in cp.findings:
                if not f.disposition:
                    yield _p(doc, f.line, "finding-disposition", f"{f.id} has no `→ <disposition>` (fix task or reason)")


def check_foreign_plan(ctx: Context):
    plan = ctx.repo.plan
    if plan is not None and not model.is_dev_team_plan(plan):
        yield _p(plan, 0, "foreign-plan", "tasks/plan.md has no dev-team2 header (**Milestone:**); not checked further")


# ---- format checks --------------------------------------------------------------------------------

def check_broken_fence(ctx: Context):
    for doc in ctx.scoped_docs:
        lines = doc.lines
        for f in md.fences(lines):
            closed = f.end > f.start and md.FENCE_RE.match(lines[f.end]) and not md.FENCE_RE.match(lines[f.end]).group(2).strip()
            if not closed:
                yield _p(doc, f.start, "broken-fence", "code fence never closes")
                continue
            if f.info.lower() in ("markdown", "md"):
                continue
            for i in range(f.start + 1, f.end):
                if re.match(r"^##\s", lines[i]):
                    yield _p(doc, f.start, "broken-fence",
                             f"code fence holds a `##` heading at line {i + 1} (a fence closed too early or too late?)")
                    break


def check_header(ctx: Context):
    for doc in ctx.scoped_docs:
        if doc.kind in ("agents", "todo") or (doc.kind == "plan" and not model.is_dev_team_plan(doc)):
            continue
        if doc.header_line is None:
            line = doc.title_line if doc.title_line is not None else 0
            yield _p(doc, line, "header", "no header line (`**Status:** … · **Last updated:** …` after the H1)")
        elif doc.kind != "roadmap" and not doc.status:
            yield _p(doc, doc.header_line, "header", "no **Status:** in the header line")


def check_unreadable(ctx: Context):
    for rel in getattr(ctx.repo, "unreadable", []):
        if ctx.in_scope(rel):
            yield Problem(rel, 0, "unreadable", "file could not be read as UTF-8 text")


CHECKS = [
    check_unreadable, check_header, check_broken_fence,
    check_pipeline_fields, check_spine_mock, check_fixture_size,
    check_dup_id, check_missing_ref, check_retired_ref,
    check_budget, check_approved_edit, check_prebuild_left,
    check_task_fields, check_task_size, check_task_acceptance, check_task_title, check_task_step,
    check_depends, check_parallel, check_verify_smoke,
    check_todo_mismatch, check_finding_disposition, check_foreign_plan,
    check_ref_file, check_ref_hash, check_ref_large, check_ref_prefix, check_roadmap_skill,
]


def lint(repo: Repo, scope: set[str] | None = None) -> list[Problem]:
    """Every problem in scope (None = the whole doc map), sorted by path and line."""
    ctx = Context(repo, scope)
    out: list[Problem] = []
    for check in CHECKS:
        try:
            out.extend(p for p in check(ctx) if ctx.in_scope(p.path))
        except Exception as e:  # a lint bug must never hide the other checks
            out.append(Problem("dt", 0, "internal", f"{check.__name__} crashed: {type(e).__name__}: {e}"))
    seen, unique = set(), []
    for p in sorted(out, key=lambda p: (p.path, p.line, p.code, p.message)):
        if (p.path, p.line, p.code, p.message) not in seen:
            seen.add((p.path, p.line, p.code, p.message))
            unique.append(p)
    return unique


# ---- CLI ------------------------------------------------------------------------------------------

def add_arguments(parser):
    parser.add_argument("paths", nargs="*", help="files or folders to report on (default: the whole doc map)")
    parser.add_argument("--changed", action="store_true", help="report on files changed vs HEAD (plus untracked)")
    parser.add_argument("--json", action="store_true", help="print one JSON object")
    parser.add_argument("--hook", action="store_true",
                        help="read Claude Code hook JSON on stdin (PostToolUse or Stop); always exits 0")


def _rel(root: Path, arg: str, base: Path) -> str | None:
    """A path argument → repo-relative (folders end in "/"), or None if it's outside the repo."""
    p = Path(arg)
    if not p.is_absolute():
        p = root / arg if (root / arg).exists() or not (base / arg).exists() else base / arg
    try:
        rel = os.path.relpath(p.resolve(), root)
    except ValueError:
        return None
    rel = rel.replace(os.sep, "/")
    if rel == "." or rel.startswith("../"):
        return None
    return rel + "/" if p.is_dir() else rel


def _summary(problems: list[Problem]) -> str:
    e = sum(1 for p in problems if p.severity == "E")
    w = len(problems) - e
    return f"{e} error{'s' if e != 1 else ''}, {w} warning{'s' if w != 1 else ''}"


def scope_for(repo: Repo, paths: list[str], changed: bool, base: Path | None = None) -> set[str] | None:
    if not paths and not changed:
        return None
    scope: set[str] = set()
    for arg in paths:
        rel = _rel(repo.root, arg, base or Path.cwd())
        if rel:
            scope.add(rel)
    if changed:
        scope.update(git.changed_files(repo.root))
    return scope


def run(args, repo) -> int:
    if args.hook:
        return run_hook(sys.stdin.read())
    if args.changed and not git.is_repo(repo.root):
        print("dt lint: --changed needs a git repo", file=sys.stderr)
        return 2
    problems = lint(repo, scope_for(repo, args.paths, args.changed))
    errors = sum(1 for p in problems if p.severity == "E")
    if args.json:
        print(json.dumps({"problems": [p.as_dict() for p in problems],
                          "errors": errors, "warnings": len(problems) - errors}, indent=2))
    else:
        for p in problems:
            print(p)
        print(_summary(problems))
    return 1 if errors else 0


# ---- hook mode ------------------------------------------------------------------------------------

def _is_doc_path(rel: str) -> bool:
    return rel.startswith(("docs/", "tasks/")) or rel in LINTED_ROOT_FILES


def run_hook(stdin_text: str) -> int:
    """PostToolUse: lint the edited doc, block (feed back) on errors. Stop: lint changed docs, report only.
    Fails open: any bad input or crash prints nothing. Always exits 0."""
    try:
        out = _hook_output(json.loads(stdin_text))
    except Exception:
        return 0
    if out is not None:
        print(json.dumps(out))
    return 0


def _hook_output(event: dict) -> dict | None:
    name = event.get("hook_event_name", "")
    root = Path(event.get("cwd") or ".").resolve()
    if name == "PostToolUse":
        file_path = (event.get("tool_input") or {}).get("file_path")
        if not file_path:
            return None
        rel = _rel(root, file_path, root)
        if not rel or not _is_doc_path(rel):
            return None
        problems = lint(Repo(root), {rel})
        if not problems:
            return None
        text = "\n".join(map(str, problems)) + "\n" + _summary(problems)
        if any(p.severity == "E" for p in problems):
            return {"decision": "block", "reason": f"dt lint found problems in {rel}:\n{text}"}
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": f"dt lint:\n{text}"}}
    if name == "Stop":
        if not git.is_repo(root):
            return None
        repo = Repo(root)
        scope = scope_for(repo, [], True)
        if not scope:
            return None
        problems = lint(repo, scope)
        if not problems:
            return None
        n = len(problems)
        lines = "\n".join(map(str, problems))
        return {"systemMessage": f"dt lint: {n} problem{'s' if n != 1 else ''}\n{lines}"}
    return None
