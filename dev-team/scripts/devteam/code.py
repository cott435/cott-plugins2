"""Reading the project's source code: module docstrings and entry-function calls (via ast).

Owned by `dt layout`; `dt status` (pipeline-design Sync) and lint reuse `pipeline_drift`.
Code is parsed with `ast` only; project code is never imported or executed.
"""
from __future__ import annotations

import ast
import os
import posixpath
from dataclasses import dataclass, field
from pathlib import Path

from . import model
from .model import Pipeline
from .repo import IGNORE_DIRS, Repo

# ---- modules ---------------------------------------------------------------------------------


def parse(path: Path) -> ast.Module | None:
    """The module's syntax tree, or None if it can't be read or parsed."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
        return None


def module_docstring(path: Path) -> str | None:
    """First line of the module's docstring, or None (no docstring, or unparseable)."""
    tree = parse(path)
    doc = ast.get_docstring(tree) if tree else None
    return doc.strip().splitlines()[0].strip() if doc and doc.strip() else None


# ---- entry functions -------------------------------------------------------------------------


def find_function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """A module-level `def name` (sync or async)."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _import_aliases(*scopes: ast.AST) -> dict[str, str]:
    """`from x import load_prices as lp` → {"lp": "load_prices"}, from imports in the given scopes."""
    out = {}
    for scope in scopes:
        for node in ast.walk(scope):
            if isinstance(node, ast.ImportFrom):
                for a in node.names:
                    if a.asname:
                        out[a.asname] = a.name
    return out


def _outer_calls(node: ast.AST):
    """Calls in a statement that aren't nested inside another call, in source order.
    Nested function, class and lambda bodies are skipped."""
    if isinstance(node, ast.Call):
        yield node
        return
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
        return
    for child in ast.iter_child_nodes(node):
        yield from _outer_calls(child)


def call_name(call: ast.Call, aliases: dict[str, str]) -> str:
    """The called function's final name: `f(…)` → f, `data.load_prices(…)` → load_prices; `?` otherwise."""
    func = call.func
    if isinstance(func, ast.Name):
        return aliases.get(func.id, func.id)
    if isinstance(func, ast.Attribute):
        return func.attr
    return "?"


def entry_calls(tree: ast.Module, func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """The entry function's top-level call names, in order (calls used as arguments don't count)."""
    aliases = _import_aliases(tree, func)
    out = []
    for stmt in func.body:
        for call in _outer_calls(stmt):
            out.append(call_name(call, aliases))
    return out


@dataclass
class PipelineCheck:
    id: str
    entry_file: str
    function: str
    status: str                        # ok | drift | missing (entry file absent: pre-spine) | no-entry
    calls: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    detail: str = ""                   # one line, for drift

    def line(self) -> str:
        """`PL-02: ok`, `PL-02: drift — …`, `PL-02: not built (… missing)`."""
        if self.status == "drift":
            return f"{self.id}: drift — {self.detail}"
        if self.status == "missing":
            return f"{self.id}: not built ({self.entry_file} missing)"
        if self.status == "no-entry":
            return f"{self.id}: no Entry file::function to check"
        return f"{self.id}: ok"


def check_pipeline(repo: Repo, pipeline: Pipeline) -> PipelineCheck:
    """Compare the entry function's top-level calls with the step table's step names, in order."""
    steps = [s.name for s in pipeline.steps]
    pc = PipelineCheck(pipeline.id, pipeline.entry_file, pipeline.entry_function, "ok", steps=steps)
    if not pipeline.entry_file or not pipeline.entry_function:
        pc.status = "no-entry"
        return pc
    path = repo.root / pipeline.entry_file
    if not path.is_file():
        pc.status = "missing"
        return pc
    tree = parse(path)
    if tree is None:
        pc.status, pc.detail = "drift", f"cannot parse {pipeline.entry_file}"
        return pc
    func = find_function(tree, pipeline.entry_function)
    if func is None:
        pc.status, pc.detail = "drift", f"{pipeline.entry_function} not defined in {pipeline.entry_file}"
        return pc
    pc.calls = entry_calls(tree, func)
    if pc.calls != steps:
        pc.status = "drift"
        pc.detail = f"calls [{', '.join(pc.calls)}] vs steps [{', '.join(steps)}]"
    return pc


def pipeline_drift(repo: Repo, pipeline: Pipeline) -> str | None:
    """None if the entry file is missing (pre-spine) or its calls match the step table;
    otherwise a one-line description of the mismatch."""
    pc = check_pipeline(repo, pipeline)
    return pc.detail if pc.status == "drift" else None


# ---- package source folders ------------------------------------------------------------------


def package_pipelines(repo: Repo, pkg: str) -> list[Pipeline]:
    doc = repo.package_doc(pkg, "pipelines")
    return model.pipelines(doc) if doc else []


def source_folder(repo: Repo, pkg: str) -> str:
    """Repo-relative source folder of a package, from its pipelines' Entry paths, else `src/<pkg>`.

    Each entry's folder is cut after its last `<pkg>` component, so a single package with component
    subfolders (`src/quant/data/pipeline.py`) gives the package folder (`src/quant`). The folders'
    common prefix is the answer.
    """
    folders = []
    for p in package_pipelines(repo, pkg):
        if not p.entry_file:
            continue
        parts = list(posixpath.dirname(p.entry_file).split("/"))
        if pkg in parts:
            parts = parts[:len(parts) - parts[::-1].index(pkg)]
        folders.append("/".join(parts))
    common = posixpath.commonpath(folders) if folders else ""
    return common if common and common != "." else f"src/{pkg}"


def _skip(name: str) -> bool:
    return name.startswith(".") or name in IGNORE_DIRS or name.endswith((".pyc", ".egg-info"))


@dataclass
class TreeEntry:
    rel: str                           # path relative to the source folder; dirs end with "/"
    depth: int
    is_dir: bool
    doc: str | None = None             # module docstring's first line (.py files)


def source_tree(root: Path) -> list[TreeEntry]:
    """Files then subfolders at each level, alphabetically; hidden, cache and build folders skipped."""
    out: list[TreeEntry] = []

    def walk(d: Path, depth: int) -> None:
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name)
        except OSError:
            return
        files = [e for e in entries if not _skip(e.name) and e.is_file()]
        dirs = [e for e in entries if not _skip(e.name) and e.is_dir()]
        for e in files:
            path = Path(e.path)
            out.append(TreeEntry(path.relative_to(root).as_posix(), depth, False,
                                 module_docstring(path) if e.name.endswith(".py") else None))
        for e in dirs:
            path = Path(e.path)
            out.append(TreeEntry(path.relative_to(root).as_posix() + "/", depth, True))
            walk(path, depth + 1)

    walk(root, 0)
    return out
