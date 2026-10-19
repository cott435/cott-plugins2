"""Check the planning docs: IDs, references, size budgets, task rules, fences and headers.

One small function per check code (see scripts/README.md for the list). Each takes a `Context` and yields
`Problem`s; `lint()` runs them all, turns a crashing check into an `internal` warning, and keeps only the
problems located in the files asked for. Cross-doc checks always read the whole repo.
"""
from __future__ import annotations

import ast
import fnmatch
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from .. import git, graph, md, model, packet
from .. import probes as pb
from .. import references as refs
from .. import requests as rq
from .. import routes as rt
from ..repo import Doc, Repo
from ..status.common import available_skills
from ..status.build_planning import steps_unplanned
from ..status.packages import shape_kept
from . import roadmap as roadmap_cmd
from ..status.tomlread import load_toml

# code → severity (E fails the run, W doesn't)
SEVERITY = {
    "dup-id": "E", "missing-ref": "E", "retired-ref": "E", "budget": "W", "grow-size": "W", "approved-edit": "W",
    "prebuild-left": "E", "task-size": "E", "task-acceptance": "E", "task-title": "E", "task-fields": "E",
    "task-step": "W", "depends": "E", "milestone-size": "E", "writes": "E", "edges": "E", "deprecated": "W",
    "step-io-types": "E", "verify-smoke": "E", "todo-mismatch": "E", "writes-unit": "E", "call-fake": "E",
    "finding-disposition": "E", "foreign-plan": "W", "broken-fence": "E", "header": "E",
    "unreadable": "E", "internal": "W", "pipeline-fields": "E", "spine-mock": "W", "contract-heading": "E",
    "fixture-size": "W",                # missing fixture files are reported as E
    "ref-file": "E", "ref-hash": "W", "ref-large": "W", "ref-prefix": "E", "roadmap-skill": "W",
    "roadmap-stage": "E", "spec-stage": "E", "type-cases": "E", "task-ref": "E", "contract-args": "E",
    "contract-depends": "E",
    "probe-fields": "E", "probe-informs": "E", "probe-cite": "E", "probe-runner": "E", "probe-leak": "E",
    "probe-sample": "E", "probe-results": "E", "probe-stale": "W", "probe-large": "W",
    "boundaries": "E", "probe-open": "E", "milestone-depends": "E",
    "request-format": "E", "request-trace": "E", "request-open": "E", "request-edit": "E", "request-ref": "E",
    "request-number": "W", "request-cite": "W", "request-source": "W",
    "packet-type-closure": "W", "parallel-step": "W", "milestone-lines": "E", "milestone-order": "E",
    "exit-cases-in-scope": "E", "kind-title": "E", "covers-vs-deferred": "E", "closed-open-question": "W",
    "process-narration": "E", "explain-stale": "W", "spine-claim": "W", "step-unplanned": "W",
    "interface-barrier": "W", "stale-row": "E",
    "milestone-lopsided": "W", "read-unwritten": "E",
    "task-order": "E",
}

# Size budgets (planning-stage.md §3), in lines. Package docs are budgeted per unit (lines per unit × units +
# an allowance for the header, groups and Retired lines); pipelines.md's pre-build layout section is extra.
BUDGETS = {"plan": 400, "queued-plan": 400}
UNIT_BUDGETS = {"contract": (8, 12, "symbol"), "pipelines": (35, 10, "pipeline"), "tests": (10, 15, "test case")}
# A pipeline with many step rows (library classes and called contract functions are steps) gets 20 + 1.5 a row.
PIPELINE_BASE, PER_STEP_ROW = 20, 1.5
# Past these a package holds too much for one set of docs: consider a Grow.
GROW_CEILINGS = {"contract": 200, "pipelines": 300, "tests": 300}
ROADMAP_SECTION_MAX = 6
BRIEF_WORDS, BRIEF_GOALS = 500, 5        # about one page; a new stage is not a new goal
PROBE_ENTRY_MAX = 10          # a PB entry: ~8 lines, plus the checks table (header, separator, one line per check)
AGENTS_DOC_MAP_MAX = 25

FIXTURE_MAX_BYTES = 100 * 1024
SPINE_MOCK = re.compile(r"\b(mock|stub|fake|todo|placeholder)", re.IGNORECASE)
# A fake of another package generated from an approved contract is allowed; a mocked step is not.
BOUNDARY_FAKE = re.compile(r"\b(contract|boundary)\s+fakes?\b", re.IGNORECASE)

SIZE_FILES = {"XS": (1, 1), "S": (1, 2), "M": (3, 5)}     # source files a task writes (tests don't count)
TRACK_MAX = 15        # the plan's critical path, in tasks
REQUIRED_TASK_FIELDS = ("Package", "Step", "Size", "Mode", "Read", "Acceptance", "Verify")
INTERFACE_FIRST_FIELDS = ("Kind", "Writes")    # also required once a plan is interface-first
# Shared modules the interface task writes whole (interface-first-design.md §4.1), with any `pipeline.py` that isn't
# one pipeline's own entry module (it re-exports the entries). A pipeline's entry module is its wiring task's (the
# interface task writes its stub, a system task may swap a fake in it).
INTERFACE_FILES = ("__init__.py", "types.py", "__main__.py")
ENTRY_WRITERS = ("interface", "wiring", "system")

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


def _p(doc, line_index: int, code: str, message: str, sev: str = "") -> Problem:
    return Problem(doc.rel, line_index + 1, code, message, sev)


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

def _units(doc) -> int:
    if doc.kind == "contract":
        return len(model.symbols(doc))
    if doc.kind == "pipelines":
        return len(model.pipelines(doc))
    return len(model.test_cases(doc))


def _unit_budget(doc) -> tuple[int, str]:
    """(budget in lines, how it was worked out) for a contract, pipelines or tests doc. A pipeline gets the larger
    of its per-unit lines and `PIPELINE_BASE` + `PER_STEP_ROW` a step row."""
    per, allowance, unit = UNIT_BUDGETS[doc.kind]
    n = _units(doc)
    layout = sum(h.end - h.line for h in doc.prebuild_sections() if h.level == 2) if doc.kind == "pipelines" else 0
    rows = [len(p.steps) for p in model.pipelines(doc)] if doc.kind == "pipelines" else []
    long = [r for r in rows if PIPELINE_BASE + math.ceil(PER_STEP_ROW * r) > per]
    units = per * (n - len(long)) + sum(PIPELINE_BASE + math.ceil(PER_STEP_ROW * r) for r in long)
    how = f"{per} per {unit} × {n - len(long)}" + (f" + ({PIPELINE_BASE} + {PER_STEP_ROW:g} per step row) × "
                                                   f"{len(long)} ({sum(long)} rows)" if long else "")
    how += f" + {allowance}" + (f" + {layout} layout" if layout else "")
    return units + allowance + layout, how


def check_budget(ctx: Context):
    kept = shape_kept(ctx.repo)       # the user kept one package: no Grow nudge
    for doc in ctx.scoped_docs:
        limit = BUDGETS.get(doc.kind)
        if limit and len(doc.lines) > limit:
            yield _p(doc, 0, "budget", f"{len(doc.lines)} lines, budget {limit} ({doc.kind})")
        if doc.kind in UNIT_BUDGETS:
            limit, how = _unit_budget(doc)
            if len(doc.lines) > limit:
                yield _p(doc, 0, "budget", f"{len(doc.lines)} lines, budget {limit} ({how})")
            ceiling = GROW_CEILINGS[doc.kind]
            if len(doc.lines) > ceiling and not kept:
                yield _p(doc, 0, "grow-size", f"{len(doc.lines)} lines, over the {ceiling}-line ceiling for one "
                         f"package's {doc.kind} doc: size alone never splits a package; trim the doc, or split a "
                         "module")
        if doc.kind == "brief":
            words, goals = len(doc.text.split()), model.goal_count(doc)
            if words > BRIEF_WORDS:
                yield _p(doc, 0, "budget", f"{words} words, budget {BRIEF_WORDS} (about one page)")
            if goals > BRIEF_GOALS:
                h = next(h for h in doc.headings if h.level == 2 and h.text.lower().startswith("goal"))
                yield _p(doc, h.line, "budget", f"{goals} goals, at most {BRIEF_GOALS}: a new stage is not a new "
                         "goal; ask the user which to merge")
        if doc.kind == "roadmap":
            for h in doc.headings:
                if h.id and re.fullmatch(rf"{md.MILESTONE_ID}|{md.STAGE_ID}", h.id):
                    n = sum(1 for line in doc.lines[h.line + 1:h.end] if line.strip())
                    if n > ROADMAP_SECTION_MAX:
                        yield _p(doc, h.line, "budget", f"{h.id} section is {n} lines, budget {ROADMAP_SECTION_MAX}")
        if doc.kind == "probes":
            for e in model.probes(doc):
                n = sum(1 for line in doc.lines[e.start:e.end] if line.strip())
                limit = PROBE_ENTRY_MAX + (len(e.checks) + 2 if e.checks else 0)
                if n > limit:
                    yield _p(doc, e.start, "budget", f"{e.id} is {n} lines, budget {limit} "
                             f"({PROBE_ENTRY_MAX} + the checks table)")
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
    if doc_kind in ("references", "probes"):
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


SYMBOL_LEAD = re.compile(rf"^{md.SYMBOL_ID}")
NAME_SEP = re.compile(r"\s*(?:/|,|·|&|\+|\band\b)\s*")


def check_contract_heading(ctx: Context):
    """A contract heading that starts with a symbol but isn't `<pkg>.<symbol>: <title>`, most often one that
    names several (`### train.train / train.train_seeds: …`). dt resolves a symbol only from its own heading."""
    for doc in ctx.scoped_docs:
        if doc.kind != "contract":
            continue
        for h in doc.headings:
            if h.id or h.level not in (2, 3) or not SYMBOL_LEAD.match(h.text):
                continue
            names = [n for n in NAME_SEP.split(h.text.split(":", 1)[0]) if n]
            if len(names) > 1:
                yield _p(doc, h.line, "contract-heading",
                         f"heading names {len(names)} symbols ({', '.join(names)}): give each its own "
                         "`### <pkg>.<symbol>: <title>` section")
            else:
                yield _p(doc, h.line, "contract-heading", "heading isn't `### <pkg>.<symbol>: <title>`, so dt can't resolve it")


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
                m = SPINE_MOCK.search(BOUNDARY_FAKE.sub("", s.spine))
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
    """`RF` and `UR` are reserved for reference and request entries: a spec requirement must not use them."""
    spec = ctx.repo.spec
    if spec is None:
        return
    for b in md.bold_leads(spec.lines, spec.mask):
        for prefix, doc in (("RF", "docs/references.md"), ("UR", rq.PATH)):
            if b.id.startswith(prefix + "-"):
                yield _p(spec, b.line, "ref-prefix", f"{b.id}: the {prefix} prefix is reserved for {doc}")


def check_roadmap_skill(ctx: Context):
    """A roadmap stage's or milestone's own `**Skills:**` line names a skill that isn't installed."""
    roadmap = ctx.repo.roadmap
    if roadmap is None:
        return
    available = set(available_skills(ctx.repo))
    for x in model.stages(roadmap) + model.milestones(roadmap):
        if x.section is None:
            continue
        missing = [s for s in model.skill_names(x.fields.get("Skills", "")) if s not in available]
        if missing:
            line = md.field_line(roadmap.lines, x.section.line + 1, x.section.end, "Skills")
            yield _p(roadmap, x.section.line if line is None else line, "roadmap-skill",
                     f"{x.id} Skills names {', '.join(missing)}: not installed (.claude/skills or the plugin)")


def check_roadmap_stage(ctx: Context):
    """Once the roadmap has stages, every milestone row names one that exists in its Stage cell (a row from
    before stages keeps its own Source instead)."""
    roadmap = ctx.repo.roadmap
    if roadmap is None or not ctx.in_scope(roadmap.rel):
        return
    stage_ids = {s.id for s in model.stages(roadmap)}
    if not stage_ids:
        return
    for ms in model.milestones(roadmap):
        if ms.row_line is None:
            continue
        cell = md.strip_md(ms.row.get("Stage", ""))
        if ms.stage and ms.stage not in stage_ids:
            yield _p(roadmap, ms.row_line, "roadmap-stage", f"{ms.id} Stage {ms.stage}: no such stage row")
        elif not ms.stage and cell not in NONE_VALUES:
            yield _p(roadmap, ms.row_line, "roadmap-stage", f"{ms.id} Stage {cell!r}: not a stage ID (S<n>)")
        elif not ms.stage and md.strip_md(ms.row.get("Source", "")) in NONE_VALUES:
            yield _p(roadmap, ms.row_line, "roadmap-stage", f"{ms.id} names no stage: fill its Stage cell")



def check_milestone_depends(ctx: Context):
    """A cycle in the roadmap's milestone Depends (IDs outside parentheses), reported once at its first row."""
    roadmap = ctx.repo.roadmap
    if roadmap is None:
        return
    rows = {m.id: m.row_line for m in model.milestones(roadmap)}
    for cycle in roadmap_cmd.depends_cycles(roadmap):
        line = rows.get(cycle[0])
        yield _p(roadmap, 0 if line is None else line, "milestone-depends",
                 f"{roadmap_cmd.cycle_text(cycle)}: Depends lists only the milestones whose outputs are needed; "
                 "a build order goes in the milestone's section")


EXIT_DUE = ("Designed", "Planned", "Building")


def check_milestone_lines(ctx: Context):
    """A Designed, Planned or Building milestone has an `**Exit:**` line; in a stage cut into more than one
    milestone, each milestone section has `**Skills:**` and `**References:**` lines (build-planning cut.md)."""
    roadmap = ctx.repo.roadmap
    if roadmap is None or not ctx.in_scope(roadmap.rel):
        return
    ms = model.milestones(roadmap)
    per_stage: dict[str, int] = {}
    for m in ms:
        if m.stage:
            per_stage[m.stage] = per_stage.get(m.stage, 0) + 1
    for m in ms:
        at = m.section.line if m.section else (m.row_line or 0)
        status = roadmap_cmd.milestone_status(ctx.repo, m)
        if m.section is None and (status in EXIT_DUE or per_stage.get(m.stage, 0) > 1):
            yield _p(roadmap, at, "milestone-lines", f"{m.id} ({status}) has no `## {m.id}: <name>` section")
            continue
        missing = []
        if status in EXIT_DUE and "Exit" not in m.fields:
            missing.append(f"**Exit:** line ({status})")
        lines = [f"**{k}:**" for k in ("Skills", "References") if k not in m.fields]
        if per_stage.get(m.stage, 0) > 1 and lines:
            missing.append(f"{' or '.join(lines)} line ({m.stage} is cut into {per_stage[m.stage]} milestones)")
        if missing:
            yield _p(roadmap, at, "milestone-lines", f"{m.id} has no {'; no '.join(missing)}")


def check_milestone_order(ctx: Context):
    """Roadmap milestone IDs increase down the table (the build order), and each Depends names only lower IDs."""
    roadmap = ctx.repo.roadmap
    if roadmap is None or not ctx.in_scope(roadmap.rel):
        return
    rows = sorted((m for m in model.milestones(roadmap) if m.row_line is not None), key=lambda m: m.row_line)
    high = None
    for m in rows:
        n = int(m.id[1:])
        if high is not None and n < int(high.id[1:]):
            yield _p(roadmap, m.row_line, "milestone-order",
                     f"{m.id} comes after {high.id} in the table: rows run in build order, so renumber the "
                     "milestones that have no plan yet")
        elif high is None or n > int(high.id[1:]):
            high = m
        later = [d for d in m.depends if int(d[1:]) >= n]
        if later:
            yield _p(roadmap, m.row_line, "milestone-order",
                     f"{m.id} depends on {', '.join(later)}, not an earlier milestone: renumber so a milestone "
                     "comes after those it needs")


LOPSIDED_MIN_PIPELINES = 4


def check_milestone_lopsided(ctx: Context):
    """A stage held whole in one milestone that carries more pipelines than every milestone of a stage cut into
    several, at least twice the smallest of them and at least `LOPSIDED_MIN_PIPELINES`: one lump beside slices
    (rl: M3 holds all of S2, 7 pipelines, beside S1's M1 at 3 and M2 at 5). A warning: cut the stage into slices."""
    roadmap = ctx.repo.roadmap
    if roadmap is None or not ctx.in_scope(roadmap.rel):
        return
    by_stage: dict[str, list[model.Milestone]] = {}
    for m in model.milestones(roadmap):
        if m.stage and m.row_line is not None:
            by_stage.setdefault(m.stage, []).append(m)
    sliced = [m for ms in by_stage.values() if len(ms) > 1 for m in ms]
    if not sliced:
        return
    sizes = {m.id: len([p for p in m.pipelines if p.startswith("PL-")]) for ms in by_stage.values() for m in ms}
    small, large = min(sizes[m.id] for m in sliced), max(sizes[m.id] for m in sliced)
    for stage, ms in by_stage.items():
        m = ms[0]
        n = sizes[m.id]
        if len(ms) == 1 and n > large and n >= max(2 * small, LOPSIDED_MIN_PIPELINES):
            beside = ", ".join(f"{x.id} {sizes[x.id]}" for x in sliced)
            yield _p(roadmap, m.row_line, "milestone-lopsided",
                     f"{m.id} holds all of {stage} in one milestone ({n} pipelines), beside sliced milestones "
                     f"({beside}): cut {stage} into slices, the first one end to end")


def _milestone_plans(ctx: Context) -> dict[str, Doc]:
    out = {}
    for doc in ctx.plan_docs:
        mid = model.milestone_of(doc)
        if mid:
            out.setdefault(mid, doc)
    return out


def check_exit_cases_in_scope(ctx: Context):
    """Each TC a milestone's Exit or Outline names (in the roadmap section, or its plan's Scope Exit) is defined and
    belongs to a pipeline in that milestone's Pipelines: a range with a gap, or a case of another milestone's
    pipeline, promises an Exit the milestone can't show."""
    roadmap = ctx.repo.roadmap
    if roadmap is None:
        return
    cases = {tc.id: tc for d in ctx.repo.docs("tests") for tc in model.test_cases(d)}
    plans = _milestone_plans(ctx)
    for m in model.milestones(roadmap):
        pls = set(m.pipelines or roadmap_cmd.milestone_pipelines(ctx.repo, m)[0])
        places = []
        if m.section is not None:
            for key in ("Exit", "Outline"):
                line = md.field_line(roadmap.lines, m.section.line + 1, m.section.end, key)
                if line is not None:
                    places.append((roadmap, line, md.split_fields(roadmap.lines[line]).get(key, "")))
        plan = plans.get(m.id)
        if plan is not None:
            line = md.field_line(plan.lines, 0, len(plan.lines), "Exit")
            if line is not None:
                places.append((plan, line, md.split_fields(plan.lines[line]).get("Exit", "")))
        for doc, line, text in places:
            ids = [i for i in md.expand_refs(text) if i.startswith("TC-")]
            gaps = [i for i in ids if i not in cases and not ctx.repo.is_retired(i)]
            if gaps:
                yield _p(doc, line, "exit-cases-in-scope",
                         f"{m.id}'s Exit names {', '.join(gaps)}, which no tests.md defines (a gap in a range?)")
            outside: dict[str, list[str]] = {}
            for i in ids:
                tc = cases.get(i)
                if tc is not None and pls and tc.pipeline and tc.pipeline not in pls:
                    outside.setdefault(tc.pipeline, []).append(i)
            for pl, tcs in outside.items():
                yield _p(doc, line, "exit-cases-in-scope",
                         f"{m.id}'s Exit names {', '.join(tcs)} of {pl}, which isn't in {m.id}'s Pipelines")


def check_spec_stage(ctx: Context):
    """Once the roadmap has stages, every spec feature names one that exists on its `**Stage:**` line (a feature
    grouped under a stage heading counts)."""
    spec, roadmap = ctx.repo.spec, ctx.repo.roadmap
    if spec is None or roadmap is None or not ctx.in_scope(spec.rel):
        return
    stage_ids = {s.id for s in model.stages(roadmap)}
    if not stage_ids:
        return
    for f in model.spec_features(spec)[0]:
        h = next(h for h in spec.headings if h.line == f.line)
        line = md.field_line(spec.lines, f.line + 1, h.end, "Stage")
        at = f.line if line is None else line
        if f.stage and f.stage not in stage_ids:
            yield _p(spec, at, "spec-stage", f"{f.code} Stage {f.stage}: no such stage row")
        elif not f.stage and line is not None:
            cell = md.strip_md(md.split_fields(spec.lines[line]).get("Stage", ""))
            yield _p(spec, at, "spec-stage", f"{f.code} Stage {cell!r}: not a stage ID (S<n>)")
        elif not f.stage:
            yield _p(spec, at, "spec-stage", f"{f.code} names no stage: add a **Stage:** line")


ROUTED_TO = re.compile(r"\brouted\s+to\s+`?([a-z]+(?:-[a-z]+)+)`?", re.IGNORECASE)


def _open_question_bullets(doc):
    """(line index, text) of each top-level bullet under a heading that mentions open questions."""
    for h in doc.headings:
        if "open question" not in h.text.lower():
            continue
        for i in range(h.line + 1, h.end):
            if not doc.mask[i] and re.match(r"^[-*]\s", doc.lines[i]):
                yield i, doc.lines[i]


def check_closed_open_question(ctx: Context):
    """An Open questions bullet that waits on a change routed to a skill (`routed to architecture-design`) when
    docs/routes.md has no open change for that skill and a done one: the Revise landed, so the question is stale."""
    items = rt.routes(ctx.repo)
    closed = {r.skill for r in items if r.done} - {r.skill for r in items if not r.done}
    if not closed:
        return
    for doc in ctx.scoped_docs:
        for i, text in _open_question_bullets(doc):
            skills = [s for s in ROUTED_TO.findall(text) if s in closed]
            if skills:
                yield _p(doc, i, "closed-open-question",
                         f"routed to {', '.join(dict.fromkeys(skills))}, whose routed changes are all done "
                         f"({rt.PATH}): drop the question or say what is still open")


# Narration that only ever tells the story of the planning (an error), and wording that usually does (a warning:
# "previously", "as of <date>" and a TC that "doesn't change" also state facts).
NARRATION = re.compile(
    r"\brevised\s+\d{4}-\d{2}-\d{2}|\b(?:adopted|added|changed)\s+before\s+M\d+|\bbefore\s+M\d+\s+is\s+built\b"
    r"|\b(?:confirmed|approved|agreed|decided|chosen)\s+by\s+the\s+user,?\s*(?:on\s+)?\d{4}-\d{2}-\d{2}"
    r"|\bnothing\s+(?:is|has\s+been)\s+built\b|\bno\s+code\s+exists\s+yet\b"
    r"|\b\d+\s+of\s+\d+\s+tasks\s+(?:(?:are|is)\s+)?(?:done|built|finished|complete)\b|\bM\d+\s+is\s+at\s+\d+\s+of\s+\d+\s+tasks\b"
    r"|\bdocs?\s+to\s+rework\b|\bthe\s+build\s+waits\s+for\b|\bwith\s+the\s+[\w-]+(?:\s+[\w-]+)?\s+as\s+it\s+stood\b",
    re.IGNORECASE)
# "The user chose X" with no request cited tells the conversation; with its UR-NN it is the trace, and passes.
USER_CHOSE = re.compile(r"\bthe\s+user\s+(?:chose|picked|opted)\b", re.IGNORECASE)
NARRATION_SOFT = re.compile(
    r"(?:TC-\d{2,}|golden|expected\s+values?)[^.;]{0,60}?\b(?:(?:don't|do\s+not|doesn't|does\s+not)\s+change"
    r"|(?:are|stay|remain)\s+unchanged)\b|\bpreviously\b|\bas\s+of\s+\d{4}-\d{2}", re.IGNORECASE)
# Docs where dates and the user's words are the content (an idea file is the record of why, as it was that day).
NARRATION_EXEMPT = ("requests", "routes", "todo", "idea")


def check_process_narration(ctx: Context):
    """History in a doc that states what holds, an error: "revised 2026-10-18", "confirmed by the user, 2026-10-17",
    "adopted before M1", "Nothing is built yet", "M1 has 0 of 22 tasks done", "Docs to rework", "the build waits
    for", "With the table as it stood", "The user chose", or a `## Replan notes` section outside a plan. A warning
    for "previously", "as of 2026-10" and "TC-01–TC-49 don't change", which can also state a fact.
    Changelog sections, code, `**Source:**` lines (a test case's provenance) and the plan's Replan notes (its
    changelog, replan.md) are left alone: the changelog holds the history."""
    for doc in ctx.scoped_docs:
        if doc.kind in NARRATION_EXEMPT:
            continue
        skip = _changelog_ranges(doc)
        if doc.kind in ("plan", "queued-plan"):
            skip += [(h.line, h.end) for h in doc.headings if h.text.lower().startswith("replan notes")]
        else:
            for h in doc.headings:
                if h.text.lower().startswith("replan notes"):
                    yield _p(doc, h.line, "process-narration",
                             "a `## Replan notes` section outside a plan: the doc states what holds, the Changelog "
                             "what changed")
        for i, line in enumerate(doc.lines):
            if doc.mask[i] or _inside(i, skip) or "**Source:**" in line:
                continue
            text = re.sub(r"`[^`]*`", "", line)
            m, sev, fix = NARRATION.search(text), "", "state what holds now"
            if not m and not re.search(r"\bUR-\d{2,}", text):
                m, fix = USER_CHOSE.search(text), "state the choice and cite the user's request (UR-NN)"
            if not m:
                m, sev = NARRATION_SOFT.search(text), "W"
            if m:
                yield _p(doc, i, "process-narration",
                         f"{m.group(0)!r} narrates history: {fix} (the Changelog holds what changed, docs/routes.md "
                         f"what goes back)", sev)


ROW_SKILL = re.compile(r"[`*]+([a-z0-9][a-z0-9-]*)[`*]+\s+skill\b")


def _live_decisions(repo: Repo) -> dict[str, str]:
    """Each live decision's ID → its section text (superseded ones are retired, and `retired-ref` covers them)."""
    return {d.id: "\n".join(d.doc.lines[d.start:d.end]) for d in repo.all_definitions
            if d.how == "heading" and not d.retired and re.fullmatch(r"AD-\d{2,}", d.id)
            and d.doc.kind in ("architecture", "package-architecture")}


def check_stale_row(ctx: Context):
    """A pipeline step row that defers to a skill under an older decision while a newer decision naming that skill
    goes uncited: the row restates what the newer one replaced (rl: "the `dataviz` skill specifies (AD-14)" after
    AD-21 set the chart). A row deferring to a skill that isn't installed is a warning. A row citing a superseded
    decision is `retired-ref`."""
    decisions = _live_decisions(ctx.repo)
    available = set(available_skills(ctx.repo))
    num = lambda ad: int(ad[3:])
    for p in ctx.pipelines.values():
        if not ctx.in_scope(p.doc.rel):
            continue
        for s in p.steps:
            cited = set(re.findall(r"AD-\d{2,}", s.spine))
            for skill in dict.fromkeys(ROW_SKILL.findall(s.spine)):
                naming = sorted((a for a, text in decisions.items() if re.search(rf"[`*]{re.escape(skill)}[`*]", text)),
                                key=num)
                old = [a for a in naming if a in cited]
                newer = [a for a in naming if a not in cited and old and num(a) > num(old[-1])]
                line = s.line
                if newer:
                    yield _p(p.doc, line, "stale-row",
                             f"{p.id}.{s.name} defers to the `{skill}` skill ({', '.join(old)}), but {', '.join(newer)} "
                             f"also decide{'s' if len(newer) == 1 else ''} it: restate the row from the newer "
                             f"decision and cite it")
                elif skill not in available:
                    yield _p(p.doc, line, "stale-row",
                             f"{p.id}.{s.name} defers to the `{skill}` skill, which isn't installed (.claude/skills or "
                             f"the plugin): state what the row does, from the decision that sets it", "W")


# ---- request checks (design/requests.md) ----------------------------------------------------------

def check_request_format(ctx: Context):
    """A `- **UR-NN**` line that isn't `<owner> · "<words>" [<context>] · <skill> <date> → <trace>`."""
    doc = ctx.repo.requests
    for b in rq.parse(doc)[1] if doc else []:
        yield _p(doc, b.line, "request-format", f"{b.id}: {b.message}")


def check_request_trace(ctx: Context):
    """A trace naming an undefined ID or request, or IDs (none retired) that no doc of the request's owner defines."""
    doc = ctx.repo.requests
    reqs = rq.parse(doc)[0] if doc else []
    ids = {r.id for r in reqs}
    for r in reqs:
        if r.superseded_by and (r.superseded_by not in ids or r.superseded_by == r.id):
            yield _p(doc, r.line, "request-trace", f"{r.id} is superseded by {r.superseded_by}: no such later request")
        defs = {i: ctx.repo.lookup(i) for i in r.honoured_by if not rq.is_section(i)}
        for i, d in defs.items():
            if d is None:
                yield _p(doc, r.line, "request-trace", f"{r.id} → {i}: {i} is not defined")
        for i in r.honoured_by:
            if rq.is_section(i) and not rq.section_docs(ctx.repo, r.owner, i):
                yield _p(doc, r.line, "request-trace",
                         f"{r.id} → {i}: no such heading in {', '.join(rq.HONOUR_KINDS[r.owner])}")
        for i in r.into:
            if (d := ctx.repo.lookup(i)) is None or d.retired:
                yield _p(doc, r.line, "request-trace", f"{r.id} was changed in {i}: {i} is not defined")
        if (defs and len(defs) == len(r.honoured_by) and all(d is not None and not d.retired for d in defs.values())
                and not rq.honouring(ctx.repo, r)):
            yield _p(doc, r.line, "request-trace",
                     f"{r.id} ({r.owner}) is traced to no ID defined in {', '.join(rq.HONOUR_KINDS[r.owner])}")


def check_request_open(ctx: Context):
    """An Approved spec or architecture with a request of its own that nothing honours and the user didn't change."""
    for owner, rel in rq.DUE_WHEN_APPROVED.items():
        doc = ctx.repo.doc(rel)
        for r in rq.due(ctx.repo, owner):
            yield _p(doc, doc.header_line or 0, "request-open",
                     f"{rq.label(r)} is neither honoured nor changed with the user's approval: "
                     f"`dt request trace {r.id} <ID>`, or `dt request change {r.id}` once the user approves")


def check_request_edit(ctx: Context):
    """A request whose words, context, skill or date changed since HEAD, or that was deleted: only traces change."""
    doc = ctx.repo.requests
    if doc is None or not git.is_repo(ctx.repo.root):
        return
    head = git.show_head(ctx.repo.root, doc.rel)
    if head is None:
        return
    now = {r.id: r for r in rq.parse(doc)[0]}
    for old in rq.parse(Doc(ctx.repo.root, doc.rel, head))[0]:
        new = now.get(old.id)
        if new is None:
            yield _p(doc, doc.header_line or 0, "request-edit",
                     f"{old.id} is gone since HEAD: requests are never deleted (`dt request change` or `--replaces`)")
        elif new.fixed != old.fixed:
            yield _p(doc, new.line, "request-edit",
                     f"{old.id} changed since HEAD: the user's words stay as heard; record new words with "
                     f"`dt request add … --replaces {old.id}`")


def check_request_ref(ctx: Context):
    """A `UR-NN` named in any doc that docs/requests.md doesn't define."""
    for doc in ctx.docs:
        for i, line in enumerate(doc.lines):
            if doc.mask[i] or "UR-" not in line:
                continue
            for id_ in dict.fromkeys(re.findall(rf"(?<![\w-])({rq.ID})(?![\w-])", line)):
                if id_ not in ctx.repo.index:
                    yield _p(doc, i, "request-ref", f"{id_} is not in {rq.PATH}")


def check_request_number(ctx: Context):
    """A traced or changed request whose number none of the IDs it names states: "under ~1 hour" traced to a
    requirement that says 90 minutes."""
    doc = ctx.repo.requests
    for r in rq.parse(doc)[0] if doc else []:
        ids = [i for i in (r.into if r.state == "changed" else r.honoured_by) if not rq.is_section(i)]
        texts = [rq.definition_text(ctx.repo, i) for i in ids]
        if not ids or not all(texts):
            continue
        for shown in rq.unstated(rq.strip_labels(r.changed or r.words, r.about), texts):
            yield _p(doc, r.line, "request-number",
                     f"{r.id} says {shown!r}, which {', '.join(ids)} doesn't state: honour the number, or change it "
                     "with the user's yes")


def check_request_cite(ctx: Context):
    """A doc citing a request that was replaced, or that the user changed when the citing ID isn't one the change
    was written into: the citing text may still follow the old words."""
    reqs = {r.id: r for r in rq.all_requests(ctx.repo)}
    for doc in ctx.docs:
        if doc.kind == "requests" or not ctx.in_scope(doc.rel):
            continue
        defs = doc.definitions()
        for i, line in enumerate(doc.lines):
            if doc.mask[i] or "UR-" not in line:
                continue
            for id_ in dict.fromkeys(re.findall(rf"(?<![\w-])({rq.ID})(?![\w-])", line)):
                r = reqs.get(id_)
                if r is None:
                    continue
                if r.superseded_by:
                    yield _p(doc, i, "request-cite", f"{id_} is superseded by {r.superseded_by}: follow and cite "
                                                     f"{r.superseded_by}")
                elif r.state == "changed" and r.into:
                    at = min((d for d in defs if d.start <= i < d.end), key=lambda d: d.end - d.start, default=None)
                    if at is not None and at.id not in r.into:
                        yield _p(doc, i, "request-cite",
                                 f"{id_} was changed ({r.changed}) in {', '.join(r.into)}, not {at.id}: bring "
                                 f"{at.id} in line, then `dt request change {id_} --into {at.id}`")


def check_request_source(ctx: Context):
    """A golden case whose Source is only the user's words, with an Expected number those words don't state: a value
    worked out from the user's fact isn't theirs, so its Source must say how it was derived."""
    reqs = {r.id: r for r in rq.all_requests(ctx.repo)}
    if not reqs:
        return
    for doc in ctx.docs:
        if doc.kind != "tests" or not ctx.in_scope(doc.rel):
            continue
        for case in model.test_cases(doc):
            source = case.fields.get("Source", "")
            cited = [i for i in dict.fromkeys(re.findall(rf"(?<![\w-])({rq.ID})(?![\w-])", source)) if i in reqs]
            rest = re.sub(rf'{rq.ID}|"[^"]*"|“[^”]*”|\d{{4}}-\d{{2}}-\d{{2}}|\b(the|user|user\'s|words|and|as|given|'
                          r'said|by|from)\b|[^\w]', " ", source, flags=re.I)
            if not cited or rest.strip():
                continue
            for shown in rq.unstated(case.fields.get("Expected", ""), [rq.stated(ctx.repo, reqs[i]) for i in cited]):
                yield _p(doc, case.start, "request-source",
                         f"{case.id}: Expected states {shown!r}, which {', '.join(cited)} doesn't: cite how it "
                         "was derived, or route it to the user")


def check_explain_stale(ctx: Context):
    """A page under docs/explained/ that no longer matches what `dt explain --write` would write now."""
    from . import explain
    folder = ctx.repo.root / explain.DIR
    if not folder.is_dir():
        return
    want = explain.pages(ctx.repo)
    for path in sorted(folder.glob("*.md")):
        rel = path.relative_to(ctx.repo.root).as_posix()
        if want.get(rel) != path.read_text(encoding="utf-8"):
            yield Problem(rel, 1, "explain-stale", "out of date with the pipelines docs: `dt explain --write`"
                          + ("" if rel in want else " (no pipelines left for it: delete it)"))


# ---- probe checks (design/probes.md §4, §5) --------------------------------------------------------

PROBE_FIELDS = ("Folder", "Question", "Informs")
# What `public.py` (the agent's checks) must never touch: a credential of any kind (§5.1).
ENV_ACCESS = re.compile(r"\bos\.environ\b|\benviron\b|\bgetenv\b|\.env\b|\bload_env\b|\bdotenv\b")
SAMPLE_REF = re.compile(rf"\b({model.PROBE_ID})[ :]+(?:evidence/)?(samples/[\w.-]+(?:/[\w.-]+)*?)(?=#|[\s),;`]|$)")


def check_probe_fields(ctx: Context):
    """A PB entry with no Folder, Question or Informs, no checks table, a check with no Pass, or a Status that
    isn't Draft, Ready, Answered or Waived; past Draft, its folder must exist."""
    for e in model.all_probes(ctx.repo):
        missing = [k for k in PROBE_FIELDS if not e._get(k)]
        if missing:
            yield _p(e.doc, e.start, "probe-fields", f"{e.id} has no {', '.join(f'**{k}:**' for k in missing)}")
        if e.state not in model.PROBE_STATES:
            yield _p(e.doc, e.start, "probe-fields",
                     f"{e.id} Status {e.status or '(none)'!r}: not Draft, Ready, Answered · pass|fail, or Waived")
        elif e.state == "Answered" and not e.verdict:
            yield _p(e.doc, e.start, "probe-fields", f"{e.id} is Answered with no pass or fail")
        if not e.checks:
            yield _p(e.doc, e.start, "probe-fields",
                     f"{e.id} has no checks table (`| Check | What | How | Pass | Runner | Result |`)")
        for c in e.checks:
            if not c.passes:
                yield _p(e.doc, c.line, "probe-fields", f"{e.id}.{c.id} has no Pass criterion")
        if e.folder and e.state != "Draft" and not (ctx.repo.root / e.folder).is_dir():
            yield _p(e.doc, e.start, "probe-fields", f"{e.id} folder {e.folder}/ is missing")


def check_probe_informs(ctx: Context):
    """An Informs ID (decision, requirement or contract symbol) that isn't defined anywhere."""
    for e in model.all_probes(ctx.repo):
        line = md.field_line(e.doc.lines, e.start + 1, e.end, "Informs")
        for id_ in e.informs:
            if not ctx.resolves(id_):
                yield _p(e.doc, e.start if line is None else line, "probe-informs",
                         f"{e.id} Informs {id_}: not defined")


def check_probe_cite(ctx: Context):
    """A decision's `**Probe:**` line naming a retired PB, `none` with no reason, or neither."""
    for c in model.probe_citations(ctx.repo):
        where = c.decision or "a decision"
        if c.is_none:
            if not c.reason:
                yield _p(c.doc, c.line, "probe-cite", f"{where} Probe: none needs the reason the docs settle it")
        elif not c.probe:
            yield _p(c.doc, c.line, "probe-cite", f"{where} Probe: {c.value!r} names neither PB-NN nor none")
        elif ctx.repo.is_retired(c.probe):
            note = ctx.repo.lookup(c.probe).retired_note
            yield _p(c.doc, c.line, "probe-cite", f"{where} Probe: {c.probe} is retired ({note})")


def check_probe_open(ctx: Context):
    """A decision Accepted while its `**Probe:**` names an entry that isn't Answered or Waived: it stays Proposed
    until the probe answers (architecture-design)."""
    entries = {e.id: e for e in model.all_probes(ctx.repo)}
    for c in model.probe_citations(ctx.repo):
        e = entries.get(c.probe)
        if not c.decision or e is None or not e.is_open:
            continue
        status = md.strip_md((model.decision_fields(ctx.repo, c.decision) or {}).get("Status", ""))
        if status.lower().startswith("accepted"):
            yield _p(c.doc, c.line, "probe-open", f"{c.decision} is Accepted while its probe {e.id} is "
                     f"{e.state or 'unread'}: keep it Proposed until {e.id} is Answered or Waived")


def check_probe_runner(ctx: Context):
    """`public.py` (the agent's checks) reads the environment or a `.env`; or a check's Runner isn't agent or
    user."""
    for folder in pb.folders(ctx.repo):
        path = folder / "public.py"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(ctx.repo.root).as_posix()
        for i, line in enumerate(lines):
            code = line.split("#", 1)[0]
            if ENV_ACCESS.search(code):
                yield Problem(rel, i + 1, "probe-runner", "public.py runs as the agent and reads no environment, "
                              "`.env` or key: move this check to probe.py (runner user)")
    for e in model.all_probes(ctx.repo):
        for c in e.checks:
            if c.runner not in pb.RUNNERS:
                yield _p(e.doc, c.line, "probe-runner",
                         f"{e.id}.{c.id} Runner {c.runner or '(empty)'!r}: agent, user or user (manual)")


def check_probe_leak(ctx: Context):
    """Evidence holding a secret or personal-data pattern (`dt probes --scan`). Names the pattern, never the text."""
    for h in pb.scan(ctx.repo):
        yield Problem(h.path, h.line, "probe-leak", f"{h.pattern} in committed evidence: fix the probe's allow-list, "
                      "re-run it, and keep this file out of git")


def check_probe_sample(ctx: Context):
    """A doc names a probe sample (`PB-01 samples/sync_added.json#0`) that doesn't exist."""
    entries = {e.id: e for e in model.all_probes(ctx.repo)}
    for doc in ctx.docs:
        skip = _changelog_ranges(doc)
        for i, line in enumerate(doc.lines):
            if doc.mask[i] or "samples/" not in line or _inside(i, skip):
                continue
            for m in SAMPLE_REF.finditer(line):
                pid, sample = m.group(1), m.group(2)
                e = entries.get(pid)
                if e is None:
                    if not ctx.repo.is_retired(pid):
                        yield _p(doc, i, "probe-sample", f"{pid} {sample}: {pid} has no entry in docs/probes.md")
                elif not e.folder or not (ctx.repo.root / e.folder / "evidence" / sample).is_file():
                    yield _p(doc, i, "probe-sample",
                             f"{pid} {sample}: no {e.folder or '(no Folder)'}/evidence/{sample} (has the probe run?)")


def check_probe_results(ctx: Context):
    """An `evidence/results.json` that isn't the shape in design/probes.md §4.3, or names a check its entry's
    table doesn't have."""
    for e in model.all_probes(ctx.repo):
        res = pb.read_results(ctx.repo, e)
        if res is not None:
            for line, message in res.problems:
                yield Problem(res.path, line, "probe-results", message)


def check_probe_stale(ctx: Context):
    """The entry's Hash isn't its code's (unstamped or changed), or results.json is for other code."""
    for e in model.all_probes(ctx.repo):
        folder = pb.folder_of(ctx.repo, e)
        current = pb.code_hash(folder) if folder is not None else None
        if current is None:
            continue
        if current != e.hash.lower():
            what = f"Hash {e.hash} is stale (code now {current})" if e.hash else "has no Hash"
            yield _p(e.doc, e.start, "probe-stale", f"{e.id} {what}: run `dt probes --stamp {e.id}`")
        res = pb.read_results(ctx.repo, e)
        if res is not None and res.script_hash and res.script_hash != current:
            yield _p(e.doc, e.start, "probe-stale",
                     f"{e.id} results.json is for code {res.script_hash}, not {current}: re-run before recording")


def check_probe_large(ctx: Context):
    """A probe over 400 code lines (probe_kit.py aside): a probe answers its checks and nothing else."""
    for e in model.all_probes(ctx.repo):
        folder = pb.folder_of(ctx.repo, e)
        if folder is None or not folder.is_dir():
            continue
        n = pb.code_lines(folder)
        if n > pb.LARGE_LINES:
            yield _p(e.doc, e.start, "probe-large", f"{e.id} is {n} code lines (budget {pb.LARGE_LINES}, "
                     f"{pb.KIT} aside): keep to what the checks need")


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


def _is_test(path: str) -> bool:
    return path.startswith("tests/") or "/tests/" in path or path.rsplit("/", 1)[-1].startswith("test_")


def check_task_size(ctx: Context):
    """Size vs the source files the task writes (`Writes:`, else `Files likely`; test files don't count). An
    interface task writes many small shapes and is sized by judgment."""
    for t in ctx.tasks:
        if not t.size:
            continue                  # task-fields reports it
        if t.size not in SIZE_FILES:
            yield _p(t.doc, t.start, "task-size", f"{t.id} Size {t.size}: must be XS, S or M (split it)")
            continue
        if t.kind == "interface":
            continue
        lo, hi = SIZE_FILES[t.size]
        n = len([f for f in t.writes if not _is_test(f)])
        if not lo <= n <= hi:
            want = f"{lo}" if lo == hi else f"{lo}–{hi}"
            field = "Writes" if "Writes" in t.fields else "Files likely"
            yield _p(t.doc, t.start, "task-size", f"{t.id} Size {t.size} wants {want} source files in {field}, has {n}")


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
    for doc in ctx.plan_docs:
        required = REQUIRED_TASK_FIELDS + (INTERFACE_FIRST_FIELDS if model.is_interface_first(doc) else ())
        for t in model.tasks(doc):
            missing = [k for k in required if k not in t.fields or (k != "Acceptance" and not t.get(k))]
            if missing:
                yield _p(t.doc, t.start, "task-fields", f"{t.id} missing {', '.join(missing)}")
            if t.get("Mode") and t.mode not in ("split", "solo"):
                yield _p(t.doc, t.start, "task-fields", f"{t.id} Mode {t.get('Mode')!r}: must be split or solo")
            if t.get("Kind") and t.kind not in model.KINDS:
                yield _p(t.doc, t.start, "task-fields",
                         f"{t.id} Kind {t.get('Kind')!r}: must be one of {', '.join(model.KINDS)}")


def check_deprecated(ctx: Context):
    """`Parallel` and `Files likely` still parse, but an interface-first plan derives groups from the graph and
    claims files with `Writes:`."""
    for t in ctx.tasks:
        for key, why in model.DEPRECATED_FIELDS.items():
            if key in t.fields:
                line = md.field_line(t.doc.lines, t.start, t.end, key)
                yield _p(t.doc, t.start if line is None else line, "deprecated", f"{t.id} **{key}:** is deprecated: {why}")


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


def check_task_order(ctx: Context):
    """A plan's task IDs run up the file (rl: M1-T20–M1-T24 sat before M1-T14). Checked only while no task of the
    plan is ticked in todo.md: then nothing built names an ID yet, so the plan renumbers; once the build starts, a
    replan keeps its IDs (replan.md)."""
    done = model.todo_state(ctx.repo)
    for doc in ctx.plan_docs:
        tasks = model.tasks(doc)
        if any(done.get(t.id) for t in tasks):
            continue
        for prev, t in zip(tasks, tasks[1:]):
            if _task_number(t.id) < _task_number(prev.id):
                yield _p(doc, t.start, "task-order",
                         f"{t.id} comes after {prev.id}: task IDs run in plan order, so renumber the plan's tasks "
                         "top to bottom (Depends on, the graph rows, todo.md and any doc naming them) while none "
                         "is done")


def _task_number(task_id: str) -> int:
    return int(task_id.rsplit("-T", 1)[1])


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


def check_milestone_size(ctx: Context):
    """The plan's critical path (the longest `Depends on` chain; mitigated edges don't order) is capped. Parallel
    tracks don't add up, so the total task count isn't capped (the plan's line budget bounds it)."""
    for doc in ctx.plan_docs:
        chain = graph.critical_path(model.tasks(doc))
        if len(chain) > TRACK_MAX:
            line = doc.header_line if doc.header_line is not None else 0
            yield _p(doc, line, "milestone-size",
                     f"critical path is {len(chain)} tasks, cap {TRACK_MAX}: {' → '.join(chain)}. Freeze an "
                     "interface for an edge on it so both sides start at once, or cut the stage into another "
                     "milestone where a later part needs an earlier part's outputs; never split independent tracks")


def _interface_file(path: str, entries: dict[str, list[str]]) -> bool:
    """`__init__.py`, `types.py`, `__main__.py`, or a `pipeline.py` that isn't exactly one pipeline's Entry file."""
    p, folder = model.norm_write(path)
    name = p.rsplit("/", 1)[-1]
    return not folder and (name in INTERFACE_FILES or name == "pipeline.py" and len(entries.get(p, [])) != 1)


def check_writes(ctx: Context):
    """`Writes:` is an exclusive claim. Two tasks with no `Depends on` path between them (in either direction)
    must not write the same path, across the whole plan, and two wiring tasks never write one file, path or not;
    the shared modules (`__init__.py`, `types.py`, `__main__.py`, a re-exporting `pipeline.py`) belong to the
    interface task, and a pipeline's entry module to an interface, wiring or system task. A conflict only `Files
    likely` claims is a warning."""
    entries: dict[str, list[str]] = {}
    for p in ctx.pipelines.values():
        if p.entry_file:
            entries.setdefault(p.entry_file, []).append(p.id)
    for doc in ctx.plan_docs:
        tasks = model.tasks(doc)
        up = {t.id: graph.ancestors(tasks, t.id) for t in tasks}
        for n, b in enumerate(tasks):
            for a in tasks[:n]:
                wiring = a.kind == b.kind == "wiring"
                if not wiring and (a.id in up[b.id] or b.id in up[a.id]):
                    continue
                shared = [w for w in b.writes if any(model.writes_overlap(w, v) for v in a.writes)]
                if not shared:
                    continue
                sev = "" if "Writes" in a.fields and "Writes" in b.fields else "W"
                if wiring:
                    yield Problem(doc.rel, b.start + 1, "writes",
                                  f"{b.id} and {a.id} are wiring tasks that both write {', '.join(shared)}: each "
                                  "writes only its own pipeline's entry module and smoke test, and the interface "
                                  "task writes `__main__.py` and any re-exporting `pipeline.py`", sev)
                else:
                    yield Problem(doc.rel, b.start + 1, "writes",
                                  f"{b.id} and {a.id} both write {', '.join(shared)} with no Depends on path "
                                  "between them: move the shared part to the interface or wiring task, or "
                                  "order them (and give the edge a graph row)", sev)
            if not b.kind or b.kind == "interface":
                continue
            line = md.field_line(doc.lines, b.start, b.end, "Writes")
            line = b.start if line is None else line
            owned = [w for w in b.writes if _interface_file(w, entries)]
            if owned:
                why = "".join(f" ({p} is the entry of {', '.join(entries[p])}: give each pipeline its own entry "
                              "module)" for p in owned if len(entries.get(p, [])) > 1)
                yield _p(doc, line, "writes", f"{b.id} ({b.kind}) writes the shared file {', '.join(owned)}: only "
                         f"the interface task may{why}")
            entry = [w for w in b.writes if w in entries and w not in owned]
            if entry and b.kind not in ENTRY_WRITERS:
                yield _p(doc, line, "writes", f"{b.id} ({b.kind}) writes the shared file {', '.join(entry)}: only "
                         "an interface, wiring or system task may")


KIND_WORDS = ("spine", "thicken")


def check_kind_title(ctx: Context):
    """A task title saying "spine" or "thicken" names its own Kind."""
    for t in ctx.tasks:
        words = set(re.findall(r"[a-z]+", md.strip_md(t.title).lower()))
        for word in KIND_WORDS:
            if word in words and t.kind and t.kind != word:
                yield _p(t.doc, t.start, "kind-title", f"{t.id} title says {word!r} but its Kind is {t.kind}: retitle "
                         "it or fix the Kind")


def check_covers_vs_deferred(ctx: Context):
    """A task or the plan's Scope covers an ID the Scope also defers (E), or a task covers an ID that another step's
    Covers cell lists and its own step's doesn't (W): it claims a requirement another step delivers. `uncovered`
    (dt status) checks that Covers and Deferred account for every ID."""
    owners: dict[str, set[str]] = {}
    for p in ctx.pipelines.values():
        for st in p.steps:
            for c in st.covers:
                owners.setdefault(c, set()).add(f"{p.id}.{st.name}")
    for doc in ctx.plan_docs:
        scope = md.fields_in(doc.lines, 0, len(doc.lines))
        deferred = set(md.expand_refs(scope.get("Deferred", "")))
        line = md.field_line(doc.lines, 0, len(doc.lines), "Deferred")
        both = [i for i in md.expand_refs(scope.get("Covers", "")) if i in deferred]
        if both:
            yield _p(doc, 0 if line is None else line, "covers-vs-deferred",
                     f"Scope Covers and Deferred both list {', '.join(both)}: pick one")
        for t in model.tasks(doc):
            at = md.field_line(doc.lines, t.start, t.end, "Covers")
            at = t.start if at is None else at
            late = [i for i in t.covers if i in deferred]
            if late:
                yield _p(doc, at, "covers-vs-deferred", f"{t.id} covers {', '.join(late)}, which the plan's Scope "
                         "defers: drop it from the task, or from Deferred")
            if not re.fullmatch(r"PL-\d{2,}\.\w+", t.step) or not _step_of(ctx, t):
                continue            # a step-less or unknown Step is `task-step`'s
            stray = [i for i in t.covers if i not in late and owners.get(i) and t.step not in owners[i]]
            if stray:
                steps = sorted({s for i in stray for s in owners[i]})
                named = ", ".join(steps[:3]) + (f" and {len(steps) - 3} more" if len(steps) > 3 else "")
                yield Problem(doc.rel, at + 1, "covers-vs-deferred",
                              f"{t.id} covers {', '.join(stray)}, which the Covers cells of {named} list, not "
                              f"{t.step}'s: cover what the step delivers, or route the step table to pipeline-design",
                              "W")


def check_step_unplanned(ctx: Context):
    """A step of the milestone's pipelines that no task builds and the Scope doesn't defer by name
    (`build_planning.steps_unplanned`): spec IDs can all be covered while a step is left out."""
    for doc in ctx.plan_docs:
        at = md.field_line(doc.lines, 0, len(doc.lines), "Deferred")
        if at is None:
            at = md.field_line(doc.lines, 0, len(doc.lines), "Covers")
        for pid, names in steps_unplanned(ctx.repo, doc).items():
            shown = ", ".join(names[:6]) + (f" and {len(names) - 6} more" if len(names) > 6 else "")
            yield _p(doc, at or 0, "step-unplanned",
                     f"{pid} steps on no task and not Deferred by name: {shown}: give each a task, or defer it "
                     f"(`{pid}.{names[0]} (to M<n>: why)`)")


def check_interface_barrier(ctx: Context):
    """An interface task followed straight, in plan order, by a non-interface task with no checkpoint between them
    (`### Checkpoint after M1-T01 (barrier)`): the build adds the review anyway; the block's items guide it."""
    for doc in ctx.plan_docs:
        tasks = sorted(model.tasks(doc), key=lambda t: t.start)
        marks = [c.start for c in model.checkpoints(doc)]
        for a, b in zip(tasks, tasks[1:]):
            if a.kind == "interface" and b.kind != "interface" and not any(a.start < m < b.start for m in marks):
                yield _p(doc, a.start, "interface-barrier",
                         f"{a.id} (interface) is followed by {b.id} with no checkpoint between: add "
                         f"`### Checkpoint after {a.id} (barrier)` so the interface is reviewed before it is built on")


def check_parallel_step(ctx: Context):
    """Two thicken tasks on one step (`PL-NN.<name>`) with no `Depends on` path between them: the step is one
    function, so each needs the file the other changes even when their Writes don't overlap."""
    for doc in ctx.plan_docs:
        tasks = model.tasks(doc)
        up = {t.id: graph.ancestors(tasks, t.id) for t in tasks}
        thicken = [t for t in tasks if t.kind == "thicken" and re.fullmatch(r"PL-\d{2,}\.\w+", t.step)]
        for n, b in enumerate(thicken):
            for a in thicken[:n]:
                if a.step == b.step and a.id not in up[b.id] and b.id not in up[a.id]:
                    yield _p(doc, b.start, "parallel-step",
                             f"{b.id} and {a.id} both thicken {b.step} with no Depends on path between them: the "
                             "step's code is one function, so order them (a `code` graph row) or fold one into the other")


def _step_of(ctx: Context, t: model.Task) -> list[model.Step]:
    """The pipeline steps a task touches: `PL-02.pca` → that step; `PL-02` → every step of PL-02."""
    out = []
    for m in re.finditer(r"(PL-\d{2,})(?:\.(\w+))?", t.step):
        p = ctx.pipelines.get(m.group(1))
        if p is not None:
            out += [s for s in p.steps if m.group(2) in (None, s.name)]
    return out


def _under_owner(path: str, owner: str) -> bool:
    """A Writes item sits in a step owner's folder or module: owner `train.loop` → `…/train/loop/…`, `…/train/loop.py`."""
    p, _ = model.norm_write(path)
    return bool(re.search(rf"(^|/){re.escape(owner.replace('.', '/'))}(/|\.\w+$)", p))


def check_spine_claim(ctx: Context):
    """A spine task whose Reason claims a contract function or class (backticked, `make_learner` or
    `methods.make_learner`) that no pipeline step or entry is, outside its step's owner, while it writes a source file
    outside that owner's folder: the symbol needs its own step, or its home in the step's folder owner
    (interface-F9 of iteration 9). One beside the step's own module is fine."""
    symbols = [s for s in model.all_symbols(ctx.repo) if not s.is_type]
    stepped = {s.name for p in ctx.pipelines.values() for s in p.steps} | \
        {p.entry_function for p in ctx.pipelines.values()}
    for doc in ctx.plan_docs:
        for t in model.tasks(doc):
            reason = t.get("Reason")
            owners = [s.owner for s in _step_of(ctx, t) if s.owner]
            if t.kind != "spine" or not owners or not md.strip_md(reason):
                continue
            names = set(re.findall(r"`([\w.]+)`", reason))
            claimed = [sym.id for sym in symbols if (sym.id in names or sym.name in names) and sym.name not in stepped
                       and not any(sym.id.startswith(o + ".") for o in owners)]
            stray = [w for w in t.writes if not _is_test(w) and not any(_under_owner(w, o) for o in owners)]
            if claimed and stray:
                line = md.field_line(doc.lines, t.start, t.end, "Reason")
                yield _p(doc, t.start if line is None else line, "spine-claim",
                         f"{t.id} (spine on {', '.join(dict.fromkeys(owners))}) claims {', '.join(claimed)} in its "
                         f"Reason, which no pipeline step owns, and writes {', '.join(stray)} outside its step's "
                         "owner: give each its own step, or put it in the step's folder owner")


def _types_between(ctx: Context, types, src: model.Task, dst: model.Task) -> set[str]:
    """Contract types `dst`'s steps produce that `src`'s steps take in (a `data` edge's boundary)."""
    outs = {ty.id for s in _step_of(ctx, dst) for n in s.out_types if (ty := model.resolve_type(types, n))}
    ins = {ty.id for s in _step_of(ctx, src) for n in s.in_types if (ty := model.resolve_type(types, n))}
    return outs & ins


def _callees(ctx: Context, src: model.Task, dst: model.Task) -> set[str]:
    """Contract symbols a `call` edge crosses: those `src`'s steps call (`<owner>.<step>`) that `dst` reads or
    builds."""
    called = {f"{s.owner}.{s.name}" for s in _step_of(ctx, src)}
    provided = _contract_symbols(_read_ids(dst.get("Read"))) | {f"{s.owner}.{s.name}" for s in _step_of(ctx, dst)}
    return called & provided


def check_edges(ctx: Context):
    """Every `Depends on` is an unmitigated `## Dependency graph` row (a dependency on an interface task is
    implied); a mitigated row never orders, so it must not be in `Depends on`; a `none` row gives its reason; a
    mitigation names a symbol an interface task freezes; and a `data` or `call` edge an interface already
    covers is mitigated, not waited for."""
    types = model.contract_types(ctx.repo)
    for doc in ctx.plan_docs:
        if not model.is_interface_first(doc):
            continue
        tasks = model.tasks(doc)
        by_id = {t.id: t for t in tasks}
        edges = model.graph_edges(doc)
        produced = model.frozen_symbols(tasks)
        section = model.graph_section(doc)
        rows: dict[tuple[str, str], model.Edge] = {}
        for e in edges:
            where = e.line
            if not e.src or not e.dst:
                yield _p(doc, where, "edges", f"graph row {' | '.join(e.cells[:2])}: From and To must each name a task")
                continue
            for end in (e.src, e.dst):
                if end not in by_id and not ctx.resolves(end):
                    yield _p(doc, where, "edges", f"graph row {e.src} → {e.dst}: {end} isn't defined")
            if e.kind not in model.EDGE_KINDS:
                yield _p(doc, where, "edges",
                         f"graph row {e.src} → {e.dst}: Kind {e.kind!r} must be one of {', '.join(model.EDGE_KINDS)}")
            if not e.mitigated and not e.reason:
                yield _p(doc, where, "edges", f"graph row {e.src} → {e.dst} is `none` with no reason (`none: <why>`)")
            if e.mitigated:
                syms = re.findall(rf"(?<![\w.]){md.SYMBOL_ID}", md.strip_md(e.mitigated_by))
                if not syms:
                    yield _p(doc, where, "edges",
                             f"graph row {e.src} → {e.dst}: mitigation names no interface (`pkg.Symbol sample|fake`)")
                for sym in syms:
                    if sym not in produced:
                        yield _p(doc, where, "edges",
                                 f"graph row {e.src} → {e.dst}: {sym} isn't frozen by an interface task "
                                 "(not in its Read: or a tests/contracts/ folder it Writes)")
            elif e.kind in ("data", "call") and e.src in by_id and e.dst in by_id:
                src, dst = by_id[e.src], by_id[e.dst]
                covered = (_types_between(ctx, types, src, dst) if e.kind == "data"
                           else _callees(ctx, src, dst)) & produced
                if covered:
                    yield _p(doc, where, "edges",
                             f"{e.src} waits on code task {e.dst} across {', '.join(sorted(covered))}, which an "
                             "interface task freezes: mitigate the edge and drop the dependency")
            rows.setdefault((e.src, e.dst), e)
        for t in tasks:
            line = md.field_line(doc.lines, t.start, t.end, "Depends on")
            line = t.start if line is None else line
            for dep in t.depends_on:
                e = rows.get((t.id, dep))
                if e is not None and e.mitigated:
                    yield _p(doc, line, "edges", f"{t.id} depends on {dep}, but its graph row is mitigated by "
                             f"{e.mitigated_by}: a mitigated edge doesn't order, drop the dependency")
                elif e is None and not (dep in by_id and by_id[dep].kind == "interface"):
                    where = "no ## Dependency graph section" if section is None else "no graph row"
                    yield _p(doc, line, "edges", f"{t.id} depends on {dep} with {where} saying why (kind, `none: <reason>`)")


def check_packet_type_closure(ctx: Context):
    """A name contract signatures use (their code, and the `**Errors:**` bullet) that no contract section defines
    and that isn't a library name, once per contract doc at its first use. `dt context` pulls every section a
    packet's symbols name (`packet.contract`), so a name with no section is one no builder sees; a name defined
    outside every section (a preamble alias) too, since no packet shows the preamble."""
    types = packet.Types(ctx.repo)
    outside = {}
    for doc in ctx.repo.docs("contract"):
        for name, line in packet.outside_sections(doc).items():
            outside.setdefault(name, f"{doc.rel}:{line + 1}")
    users: dict[tuple[str, str], list[model.Symbol]] = {}
    for sym in types.symbols:
        for name in types.unresolved(sym):
            users.setdefault((sym.doc.rel, name), []).append(sym)
    for (_, name), syms in users.items():
        first, bare = syms[0], name.rsplit(".", 1)[-1]
        by = ", ".join(s.id for s in syms[:3]) + (f" and {len(syms) - 3} more" if len(syms) > 3 else "")
        section = f"`### {first.id.split('.')[0]}.{bare}: type`"
        if name in outside:
            why = f"is defined outside any section ({outside[name]}), so no packet shows it: give it a {section} section"
        else:
            why = (f"has no contract section, so no packet shows it: add a {section} section (or a `class {bare}(…)` "
                   "line in one), or qualify a library type (`pd.DataFrame`)")
        yield Problem(first.doc.rel, first.start + 1, "packet-type-closure", f"{name} (named by {by}) {why}")


def check_writes_unit(ctx: Context):
    """Every implementer and solo half writes unit tests (implementer.md), so a task's `Writes:` outside
    `tests/intent/` name a `tests/unit/` path. An interface task is exempt."""
    for doc in ctx.plan_docs:
        if not model.is_interface_first(doc):
            continue
        for t in model.tasks(doc):
            if t.kind == "interface" or "Writes" not in t.fields:
                continue
            share = [w for w in t.writes if not w.startswith("tests/intent/")]
            if not any(w.startswith("tests/unit/") for w in share):
                line = md.field_line(doc.lines, t.start, t.end, "Writes")
                half = "implementer" if t.mode == "split" else "solo"
                yield _p(doc, t.start if line is None else line, "writes-unit",
                         f"{t.id} Writes name no tests/unit/ path: its {half} half writes unit tests "
                         f"(tests/unit/{t.package or '<pkg>'}/)")


def check_call_fake(ctx: Context):
    """A `call` edge marked `none` whose callee is a contract symbol no interface task freezes: freeze its fake in
    the interface task and mitigate the edge, so both sides start at once, or give the reason
    `none: integration: <what runs the real chain>`. (A callee the interface already freezes is `edges`'.)"""
    symbols = {s.id for s in model.all_symbols(ctx.repo)}
    for doc in ctx.plan_docs:
        if not model.is_interface_first(doc):
            continue
        tasks = model.tasks(doc)
        by_id = {t.id: t for t in tasks}
        produced = model.frozen_symbols(tasks)
        for e in model.graph_edges(doc):
            if e.kind != "call" or e.mitigated or not e.src or not e.dst:
                continue
            if re.match(r"integration\s*:", e.reason, re.IGNORECASE):
                continue
            callees = set(re.findall(rf"(?<![\w.]){md.SYMBOL_ID}", md.strip_md(e.reason)))
            if e.src in by_id and e.dst in by_id:
                callees |= _callees(ctx, by_id[e.src], by_id[e.dst])
            hit = sorted((callees & symbols) - produced)
            if hit:
                yield _p(doc, e.line, "call-fake",
                         f"{e.src} waits on {e.dst} to call {', '.join(hit)}, a contract symbol with no fake: have the "
                         "interface task freeze its fake and mitigate the edge, or give `none: integration: <what "
                         "runs the real chain>`")


def check_step_io_types(ctx: Context):
    """Every type a package step's `In → Out` cell names is a contract type section, and every step's Out names
    one: the boundaries an interface task freezes (entry arguments on the In side may stay plain). A project with
    no type sections yet gets warnings, not errors, and so does a type an open route (docs/routes.md) names: the
    addition waits for its owner's Revise."""
    types = model.contract_types(ctx.repo)
    sev = "" if types else "W"
    routed = " ".join(r.change for r in rt.routes(ctx.repo) if not r.done)
    for doc in ctx.repo.docs("pipelines"):
        for p in model.pipelines(doc):
            for s in p.steps:
                for name in s.in_types + s.out_types:
                    if model.resolve_type(types, name) is None:
                        short = name.rsplit(".", 1)[-1]
                        waiting = bool(re.search(rf"(?<![\w.]){re.escape(short)}\b|\b{re.escape(name)}\b", routed))
                        yield Problem(doc.rel, s.line + 1, "step-io-types",
                                      f"{p.id} step `{s.name}` names {name}, which no contract.md type section "
                                      f"defines (`### <component>.{short}: type`)"
                                      + ("; routed, waiting for its owner's Revise" if waiting else ""),
                                      "W" if waiting else sev)
                if not s.out_types:
                    yield Problem(doc.rel, s.line + 1, "step-io-types",
                                  f"{p.id} step `{s.name}`: its Out names no contract type", sev)


def _has_cases(sym: model.Symbol) -> bool:
    bullets = md.bullet_fields(sym.doc.lines, sym.start + 1, sym.end)
    value = md.strip_md(sym.fields.get("Cases", "") or bullets.get("Cases", ""))
    return value.lower() not in NONE_VALUES


def check_type_cases(ctx: Context):
    """A contract type that crosses step owners has at least one case: pipeline steps of two or more owners name
    it in their `In → Out` cells, or its `**Boundary:**` line names a consumer, and it has no `**Cases:**`. The
    interface task writes one sample per case. E once any contract type names a case, W before."""
    types = model.contract_types(ctx.repo)
    owners: dict[str, set[str]] = {}
    for p in ctx.pipelines.values():
        for s in p.steps:
            for n in s.in_types + s.out_types:
                ty = model.resolve_type(types, n)
                # A reused step (`PL-01 as built`) is owned where that pipeline defines it.
                if ty is not None and s.owner and not re.match(r"PL-\d", s.owner):
                    owners.setdefault(ty.id, set()).add(s.owner)
    syms = [s for s in model.all_symbols(ctx.repo) if s.is_type]
    sev = "" if any(_has_cases(s) for s in syms) else "W"
    for sym in syms:
        if _has_cases(sym):
            continue
        bullets = md.bullet_fields(sym.doc.lines, sym.start + 1, sym.end)
        consumers = [c for c in map(md.strip_md, md.split_list(bullets.get("Boundary", "")))
                     if c.lower() not in NONE_VALUES]
        crossing = sorted(owners.get(sym.id, set()))
        if len(crossing) < 2 and not consumers:
            continue
        why = (f"steps of {', '.join(crossing)} pass it" if len(crossing) >= 2
               else f"its Boundary names {', '.join(consumers)}")
        yield Problem(sym.doc.rel, sym.start + 1, "type-cases",
                      f"{sym.id} crosses step owners ({why}) but names no case: add `**Cases:** <the payloads a "
                      f"sample must show>` to its `- **Boundary:** … · **Fixtures:** tests/contracts/{sym.id}/` "
                      "line", sev)


REUSED_STEP = re.compile(r"\bPL-\d{2,}\s+as\s+built\b", re.IGNORECASE)


def _owners(repo: Repo) -> set[str]:
    """Every package and component the docs define: what a `Used by` names besides PL IDs."""
    out = set(repo.packages()) | {d.package for d in repo.docs() if d.package}
    for doc in repo.docs("architecture", "package-architecture"):
        out |= {c.id.strip("`") for c in model.components(doc)}
    return out


def _other_pipelines(ctx: Context, sym: model.Symbol, used: list[str]) -> list[str]:
    """The pipelines in a contract function's `Used by` that aren't its own. Its own are those whose entry it is
    and those with a step of its name its component owns. Another is any other, once it has one; with none, a
    pipeline that calls it through a reused step (`PL-01 as built`, or an Owner cell naming a PL)."""
    component = sym.id.split(".")[0]
    home, callers = set(), set()
    for p in ctx.pipelines.values():
        if p.entry_function == sym.name and (p.is_system or p.package == sym.package):
            home.add(p.id)
        for s in p.steps:
            if s.name != sym.name:
                continue
            if REUSED_STEP.search(md.strip_md(s.spine)) or re.match(r"PL-\d", s.owner):
                callers.add(p.id)
            elif s.owner == component:
                home.add(p.id)
    return [i for i in used if i not in home and (home or i in callers)]


def _used_by(value: str, own: set[str], owners: set[str]) -> tuple[list[str], list[str]]:
    """(the packages and components a `Used by` value names other than `own`, the PL IDs it names)."""
    names = [n for n in (md.strip_md(x).strip("`") for x in re.split(r"[;,·]", value)) if n in owners and n not in own]
    return list(dict.fromkeys(names)), [i for i in md.expand_refs(value) if re.fullmatch(r"PL-\d{2,}", i)]


def check_boundaries(ctx: Context):
    """A contract function, or a pipeline, whose `Used by` names another package or component, or a pipeline it
    is neither a step nor the entry of, has a `**Boundary:**` line, so the interface task freezes a fake for it
    and the caller's wiring never waits on its code (interface-first-design.md §4.1). Types are `type-cases'."""
    owners = _owners(ctx.repo)
    for sym in model.all_symbols(ctx.repo):
        if sym.is_type:
            continue
        bullets = md.bullet_fields(sym.doc.lines, sym.start + 1, sym.end)
        if "Boundary" in sym.fields or "Boundary" in bullets:
            continue
        names, pls = _used_by(sym.fields.get("Used by") or bullets.get("Used by", ""),
                              {sym.id.split(".")[0], sym.package}, owners)
        outside = names + _other_pipelines(ctx, sym, pls)
        if outside:
            line = md.field_line(sym.doc.lines, sym.start + 1, sym.end, "Used by")
            yield Problem(sym.doc.rel, (sym.start if line is None else line) + 1, "boundaries",
                          f"{sym.id} is used by {', '.join(outside)} but has no **Boundary:** line: add `- "
                          f"**Boundary:** <consumers> · **Fixtures:** tests/contracts/{sym.id}/ · **Cases:** …` "
                          "so the interface task freezes its fake")
    for p in ctx.pipelines.values():
        if "Boundary" in p.fields:
            continue
        names, pls = _used_by(p.fields.get("Used by", ""), {p.package}, owners)
        outside = names + [i for i in pls if i != p.id]
        if outside:
            line = md.field_line(p.doc.lines, p.start + 1, p.end, "Used by")
            yield Problem(p.doc.rel, (p.start if line is None else line) + 1, "boundaries",
                          f"{p.id}'s entry is used by {', '.join(outside)} but has no **Boundary:** line: add "
                          "`**Boundary:** <consumers> · **Fixtures:** tests/contracts/<pkg.entry>/` so the "
                          "interface task freezes its fake")


# The bar's argument limits when pyproject.toml doesn't set them: build-setup's template values.
ARG_LIMITS = {"max-args": 5, "max-positional-args": 4}
DEF_START = re.compile(r"\bdef\s+\w+\s*\(")
NAME = re.compile(r"\b[A-Za-z_][\w.]*")


def _signature_code(sym: model.Symbol) -> str:
    """A contract section's code before its first bullet: its inline code spans and fenced lines, comments cut."""
    out = []
    for i in range(sym.start + 1, sym.end):
        line = sym.doc.lines[i]
        if not sym.doc.mask[i] and line.lstrip().startswith("- **"):
            break
        if sym.doc.mask[i]:
            out.append("" if line.lstrip().startswith(("```", "~~~")) else line)
        else:
            out += re.findall(r"`([^`]+)`", line)
    return " ".join(re.sub(r"#.*", "", c) for c in out)


def _defs(code: str) -> list[ast.FunctionDef]:
    """Each `def name(…) -> …` in the code, parsed alone (one-line class bodies aren't valid Python)."""
    out = []
    for m in DEF_START.finditer(code):
        depth, i = 1, m.end()
        while i < len(code) and depth:
            depth += {"(": 1, ")": -1}.get(code[i], 0)
            i += 1
        ret = re.match(r"\s*->\s*(.+?)(?=\s*(?:;|$|\bdef\b|\bclass\b))", code[i:])
        try:
            node = ast.parse(code[m.start():i] + (f" -> {ret.group(1)}" if ret else "") + ": ...").body[0]
        except SyntaxError:
            continue
        if isinstance(node, ast.FunctionDef):
            out.append(node)
    return out


def _arg_counts(fn: ast.FunctionDef) -> tuple[int, int]:
    """(arguments, positional ones) as Ruff's PLR0913 and PLR0917 count them: `self`/`cls`, `*args` and
    `**kwargs` left out."""
    pos = fn.args.posonlyargs + fn.args.args
    if pos and pos[0].arg in ("self", "cls"):
        pos = pos[1:]
    return len(pos) + len(fn.args.kwonlyargs), len(pos)


def _arg_limits(repo: Repo) -> dict[str, int]:
    path = repo.root / "pyproject.toml"
    try:
        tool = load_toml(path).get("tool", {}) if path.is_file() else {}
    except Exception:
        tool = {}
    ruff = tool.get("ruff", {})
    pylint = {**ruff.get("pylint", {}), **ruff.get("lint", {}).get("pylint", {})}
    return {k: int(pylint.get(k, v)) for k, v in ARG_LIMITS.items()}


def check_contract_args(ctx: Context):
    """A contract signature with more arguments, or more positional ones, than the bar allows (Ruff's PLR0913 and
    PLR0917, limits from pyproject.toml else build-setup's 5 and 4). The interface task can't freeze it."""
    limits = _arg_limits(ctx.repo)
    for sym in model.all_symbols(ctx.repo):
        for fn in _defs(_signature_code(sym)):
            n, pos = _arg_counts(fn)
            over = [f"{n} arguments (max-args {limits['max-args']})"] if n > limits["max-args"] else []
            if pos > limits["max-positional-args"]:
                over.append(f"{pos} positional (max-positional-args {limits['max-positional-args']})")
            if over:
                yield Problem(sym.doc.rel, sym.start + 1, "contract-args",
                              f"{sym.id}: `{fn.name}` takes {' and '.join(over)}, past the bar's limit: group "
                              "arguments into a type or make them keyword-only")


def _reachable(deps: dict[str, list[str]], start: str) -> set[str]:
    seen, todo = set(), list(deps.get(start, []))
    while todo:
        c = todo.pop()
        if c not in seen:
            seen.add(c)
            todo += deps.get(c, [])
    return seen


def check_contract_depends(ctx: Context):
    """A contract symbol whose signature or fields name another component's (or package's) type when its own
    doesn't depend on that one, directly or not, in the architecture's Components or Packages table. The bar's
    import layers come from that table, so the interface task couldn't import the type."""
    deps: dict[str, list[str]] = {}
    for doc in ctx.repo.docs("architecture", "package-architecture"):
        for c in model.components(doc):
            deps.setdefault(c.id, c.depends_on)
    if not deps:
        return
    syms = model.all_symbols(ctx.repo)
    types = model.contract_types(ctx.repo)
    own_names = {(s.id.split(".")[0], s.name) for s in syms if s.is_type}
    for sym in syms:
        owner = sym.id.split(".")[0]
        if owner not in deps:
            continue
        named = set()
        for name in NAME.findall(_signature_code(sym)):
            if (owner, name.rsplit(".", 1)[-1]) in own_names and "." not in name:
                continue
            ty = model.resolve_type(types, name)
            other = ty.id.split(".")[0] if ty else owner
            if other != owner and other in deps and other not in _reachable(deps, owner):
                named.add(ty.id)
        for tid in sorted(named):
            yield Problem(sym.doc.rel, sym.start + 1, "contract-depends",
                          f"{sym.id} names {tid}, but {owner} doesn't depend on {tid.split('.')[0]}: move the "
                          "type down, or add the dependency to the components table")


BARE_TASK = re.compile(r"(?<![\w-])T\d{2,}\b")


def _task_ids_in(text: str, milestone: str | None) -> list[str]:
    """Task IDs a piece of text names: `M1-T05`, and a bare `T05` read as the plan's own milestone's."""
    plain = md.strip_md(text)
    out = re.findall(rf"\b{md.TASK_ID}\b", plain)
    if milestone:
        out += [f"{milestone}-{t}" for t in BARE_TASK.findall(plain)]
    return list(dict.fromkeys(out))


def check_task_ref(ctx: Context):
    """A task ID in a task's Acceptance text or in a `## Dependency graph` row's Mitigated by cell (its mitigation
    or its `none:` reason) that names no task: in this plan, another plan or the archive. A bare `T41` is read as
    the plan's own milestone's."""
    known = {t.id for t in ctx.tasks}
    for doc in ctx.plan_docs:
        mid = model.milestone_of(doc)

        def stale(text: str) -> list[str]:
            return [i for i in _task_ids_in(text, mid) if i not in known and not ctx.resolves(i)]

        for t in model.tasks(doc):
            acc = md.field_line(doc.lines, t.start + 1, t.end, "Acceptance")
            items = ([(acc, md.split_fields(doc.lines[acc]).get("Acceptance", ""))] if acc is not None else [])
            items += [(cb.line, cb.text) for cb in t.acceptance]
            for line, text in items:
                for i in stale(text):
                    yield _p(doc, line, "task-ref", f"{t.id} Acceptance names {i}, which isn't a task")
        for e in model.graph_edges(doc):
            if len(e.cells) < 4:
                continue
            for i in stale(e.cells[3]):
                yield _p(doc, e.line, "task-ref", f"graph row {e.src} → {e.dst} names {i}, which isn't a task")


def check_read_unwritten(ctx: Context):
    """A repo path in a task's `Read:` (one not checked in todo.md) that isn't in the repo and that no task writes before it starts
    (a task it waits on, or an earlier milestone's): its `dt context` packet says "missing: not in the repo yet"
    where the seam it builds against should be."""
    done = model.todo_state(ctx.repo)
    for doc in ctx.plan_docs:
        for t in model.tasks(doc):
            if done.get(t.id):
                continue
            for ref in packet.unwritten_reads(ctx.repo, t):
                line = md.field_line(doc.lines, t.start + 1, t.end, "Read")
                yield _p(doc, t.start if line is None else line, "read-unwritten",
                         f"{t.id} Read: {ref} isn't in the repo and no task it waits on writes it, so its packet "
                         f"shows \"missing: not in the repo yet\": put the seam in a task it depends on (the "
                         f"interface stubs it), or drop the path")


def _smoke_due(t: model.Task, pl: str, wired_before: dict[str, set[str]]) -> bool:
    """Whether the task's Verify must run pipeline `pl`'s smoke command. Wiring and system tasks do, and so does
    any other task whose `Depends on` reaches `pl`'s wiring task; interface and spine tasks, and thicken tasks
    beside the wiring, land before the pipeline runs. A task with no Kind: every task outside Phase 0."""
    if not t.kind:
        return not t.is_spine
    return t.kind in ("wiring", "system") or pl in wired_before.get(t.id, set())


def check_verify_smoke(ctx: Context):
    smoke: dict[str, str | None] = {}
    wired_before: dict[str, set[str]] = {}
    for doc in ctx.plan_docs:
        tasks = model.tasks(doc)
        wiring = {t.id: model.spine_pipeline(t) for t in tasks if t.kind == "wiring"}
        for t in tasks:
            wired_before[t.id] = {wiring[a] for a in graph.ancestors(tasks, t.id) if a in wiring}
    for t in ctx.tasks:
        verify = " ".join(t.get("Verify").split())
        for pl in dict.fromkeys(re.findall(r"PL-\d{2,}", t.step)):
            if not _smoke_due(t, pl, wired_before):
                continue
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
        yield _p(plan, 0, "foreign-plan", "tasks/plan.md has no dev-team header (**Milestone:**); not checked further")


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
        if doc.kind in ("agents", "todo", "routes") or (doc.kind == "plan" and not model.is_dev_team_plan(doc)):
            continue
        if doc.header_line is None:
            line = doc.title_line if doc.title_line is not None else 0
            yield _p(doc, line, "header", "no header line (`**Status:** … · **Last updated:** …` after the H1)")
        elif doc.kind not in ("roadmap", "probes", "requests") and not doc.status:
            yield _p(doc, doc.header_line, "header", "no **Status:** in the header line")


def check_unreadable(ctx: Context):
    for rel in getattr(ctx.repo, "unreadable", []):
        if ctx.in_scope(rel):
            yield Problem(rel, 0, "unreadable", "file could not be read as UTF-8 text")


CHECKS = [
    check_unreadable, check_header, check_broken_fence, check_contract_heading,
    check_pipeline_fields, check_spine_mock, check_fixture_size,
    check_dup_id, check_missing_ref, check_retired_ref,
    check_budget, check_approved_edit, check_prebuild_left,
    check_task_fields, check_task_size, check_task_acceptance, check_task_title, check_task_step,
    check_depends, check_task_order, check_milestone_size, check_writes, check_parallel_step, check_spine_claim, check_edges,
    check_writes_unit, check_call_fake, check_deprecated, check_verify_smoke,
    check_step_io_types, check_packet_type_closure, check_type_cases, check_contract_args, check_contract_depends,
    check_task_ref, check_read_unwritten,
    check_todo_mismatch, check_finding_disposition, check_foreign_plan,
    check_ref_file, check_ref_hash, check_ref_large, check_ref_prefix, check_roadmap_skill, check_roadmap_stage,
    check_spec_stage, check_milestone_lines, check_milestone_order, check_milestone_lopsided, check_exit_cases_in_scope,
    check_kind_title, check_covers_vs_deferred, check_step_unplanned, check_interface_barrier, check_closed_open_question, check_process_narration,
    check_stale_row,
    check_probe_fields, check_probe_informs, check_probe_cite, check_probe_runner, check_probe_leak,
    check_probe_sample, check_probe_results, check_probe_stale, check_probe_large,
    check_boundaries, check_probe_open, check_milestone_depends,
    check_request_format, check_request_trace, check_request_open, check_request_edit, check_request_ref,
    check_request_number, check_request_cite, check_request_source, check_explain_stale,
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
    return rel.startswith(("docs/", "tasks/", "probes/")) or rel in LINTED_ROOT_FILES


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
