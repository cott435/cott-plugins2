"""What a task's builder packet shows of the contract: the symbols its `Read:` names, the frozen interfaces its
steps cross, and every contract section their signatures name, followed until nothing new is named. `dt context`
prints it; `dt lint` (`packet-type-closure`) reports the names no section defines."""
from __future__ import annotations

import builtins
import collections
import collections.abc
import dataclasses
import datetime
import decimal
import enum
import fractions
import pathlib
import re
import typing
import uuid
from dataclasses import dataclass

from . import md, model
from .repo import Repo

CODE_SPAN = re.compile(r"`([^`]+)`")
STRING = re.compile(r"\"[^\"\n]*\"|'[^'\n]*'")
BULLET = re.compile(r"^\s*[-*]\s")
# A name a piece of contract code defines: `class X`, `X = …`, `NewType("X", …)`, or a constructor-style
# signature `X(field: type, …)`.
DEFINES = re.compile(r"\bclass\s+([A-Z]\w*)|(?:^|[;,]\s*)([A-Z]\w*)\s*(?::\s*TypeAlias\s*)?=(?!=)"
                     r"|NewType\(\s*[\"']([A-Z]\w*)|\b([A-Z]\w*)\(\s*\w+\s*:")
# Library names a signature may use bare: Python's own, and the common third-party ones. A qualified name whose
# first part isn't a contract component (`pd.DataFrame`, `np.random.Generator`) is a library name too.
STDLIB_MODULES = (builtins, typing, collections, collections.abc, dataclasses, datetime, decimal, enum, fractions,
                  pathlib, uuid)
THIRD_PARTY = {"DataFrame", "Series", "Index", "DatetimeIndex", "Timestamp", "Timedelta", "BaseModel", "Field",
               "FastAPI", "APIRouter", "Request", "Response", "HTTPException", "Tensor", "Module", "Figure", "Axes",
               "Generator", "DuckDBPyConnection", "ArrayLike", "NDArray", "Console",
               "Record", "Promise", "Partial", "Readonly"}        # TypeScript's, for a front-end package
LIBRARY = {n for m in STDLIB_MODULES for n in dir(m) if n[:1].isupper()} | THIRD_PARTY


@dataclass
class Shown:
    symbol: model.Symbol
    why: str            # "read", "step" (an In → Out type or the step's own symbol), or "named by <symbol ID>"


def _code(doc, start: int, end: int, bullets: bool) -> list[str]:
    """The code in lines [start, end): fenced lines, and inline code on lines that aren't bullets (all bullets
    when `bullets`, else only an `**Errors:**` bullet); `#` comments dropped."""
    out = []
    for i in range(start, end):
        line = doc.lines[i]
        if doc.mask[i]:
            if not md.FENCE_RE.match(line):
                out.append(line.split("#", 1)[0])
        elif bullets or not BULLET.match(line) or "**Errors:**" in line:
            out += [span.split("#", 1)[0] for span in CODE_SPAN.findall(line)]
    return out


def signature(sym: model.Symbol) -> str:
    """A contract section's signature and fields: its fenced code, the inline code on lines that aren't bullets,
    and the inline code of its `**Errors:**` bullet; string literals dropped (`Literal["S2"]` names no type)."""
    return STRING.sub('""', "\n".join(_code(sym.doc, sym.start + 1, sym.end, bullets=False)))


def defined_names(code: list[str]) -> set[str]:
    """The names a piece of contract code defines (library names aside: `x: int | None = None` defines nothing)."""
    out = set()
    for piece in code:
        for line in piece.splitlines():
            for m in DEFINES.finditer(line.strip()):
                out.add(next(g for g in m.groups() if g))
    return out - LIBRARY


class Types:
    """The contract sections a name in a signature resolves to: a type or CamelCase class section of that name
    (its own component first, then its package, then any), else the section whose code defines it inline
    (`ActionSpace = Discrete(n: int) | Box(…)` defines `Discrete`)."""

    def __init__(self, repo: Repo):
        self.repo = repo
        self.symbols = model.all_symbols(repo)
        self.by_id = model.contract_types(repo)
        self.by_name: dict[str, list[model.Symbol]] = {}
        for s in sorted(self.symbols, key=lambda s: not s.is_type):
            if s.is_type or s.name[:1].isupper():
                self.by_name.setdefault(s.name, []).append(s)
        self.inline: dict[str, list[model.Symbol]] = {}
        for s in self.symbols:
            for name in defined_names(_code(s.doc, s.start + 1, s.end, bullets=True)) - {s.name}:
                self.inline.setdefault(name, []).append(s)
        self.components = {s.id.split(".")[0] for s in self.symbols} | set(repo.packages())

    @staticmethod
    def _nearest(hits: list[model.Symbol], near: model.Symbol | None) -> model.Symbol | None:
        if near is not None:
            comp = near.id.split(".")[0]
            for pick in ([h for h in hits if h.id.split(".")[0] == comp], [h for h in hits if h.package == near.package]):
                if pick:
                    return pick[0]
        return hits[0] if hits else None

    def resolve(self, name: str, near: model.Symbol | None = None) -> model.Symbol | None:
        if "." in name:
            return model.resolve_type(self.by_id, name) or next(
                (s for s in self.symbols if name.endswith(s.id) and s.name[:1].isupper()), None)
        return self._nearest(self.by_name.get(name, []), near) or self._nearest(self.inline.get(name, []), near)

    def is_library(self, name: str) -> bool:
        head = name.split(".")[0]
        return name in LIBRARY if "." not in name else head not in self.components

    def named_by(self, sym: model.Symbol) -> list[model.Symbol]:
        """The contract sections a symbol's signature names, itself aside, in order."""
        out: dict[str, model.Symbol] = {}
        for name in model.type_names(signature(sym)):
            hit = self.resolve(name, sym)
            if hit is not None and hit.id != sym.id:
                out.setdefault(hit.id, hit)
        return list(out.values())

    def unresolved(self, sym: model.Symbol) -> list[str]:
        """Names a symbol's signature uses that no contract section defines and that aren't library names."""
        own = defined_names(_code(sym.doc, sym.start + 1, sym.end, bullets=True)) | {sym.name}
        return [n for n in model.type_names(signature(sym))
                if n not in own and not self.is_library(n) and self.resolve(n, sym) is None]


def outside_sections(doc) -> dict[str, int]:
    """Names a contract doc's code defines outside any symbol section (a preamble alias), by line index."""
    inside = set()
    for s in model.symbols(doc):
        inside.update(range(s.start, s.end))
    out: dict[str, int] = {}
    for i in range(len(doc.lines)):
        if i not in inside:
            for name in defined_names(_code(doc, i, i + 1, bullets=True)):
                out.setdefault(name, i)
    return out


def task_steps(repo: Repo, task: model.Task) -> list[model.Step]:
    """The steps a task touches: `PL-02.pca` → that step; `PL-02` (wiring, system) → every step of PL-02."""
    pipelines = {p.id: p for p in model.all_pipelines(repo)}
    out = []
    for m in re.finditer(r"(PL-\d{2,})(?:\.(\w+))?", task.step):
        p = pipelines.get(m.group(1))
        if p is not None:
            out += [s for s in p.steps if m.group(2) in (None, s.name)]
    return out


def contract(repo: Repo, task: model.Task, read_ids: list[str], types: Types | None = None) -> list[Shown]:
    """Every contract symbol the task's packet shows, in packet order: those `read_ids` names, then the frozen
    interfaces its steps cross (the types their `In → Out` cells name, and the contract symbols with a step's
    name), then each section a shown symbol's signature names that isn't shown yet, until closed."""
    types = types or Types(repo)
    syms = {s.id: s for s in types.symbols}
    out: dict[str, Shown] = {}
    for i in read_ids:
        if i in syms:
            out.setdefault(i, Shown(syms[i], "read"))
    steps = task_steps(repo, task)
    for s in steps:
        for name in s.in_types + s.out_types:
            ty = model.resolve_type(types.by_id, name)
            if ty is not None:
                out.setdefault(ty.id, Shown(ty, "step"))
    names = {s.name for s in steps}
    for sym in syms.values():
        if not sym.is_type and sym.name in names:
            out.setdefault(sym.id, Shown(sym, "step"))
    queue = list(out.values())
    while queue:
        shown = queue.pop(0)
        for hit in types.named_by(shown.symbol):
            if hit.id not in out:
                out[hit.id] = Shown(hit, f"named by {shown.symbol.id}")
                queue.append(out[hit.id])
    return list(out.values())
