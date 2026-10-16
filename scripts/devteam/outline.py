"""Outlines and selections of a single file, for `dt outline` and reference rendering in `dt context`.

- `.py`: each def and class (methods indented under their class) with its signature and the first line of
  its docstring, read with `ast` only: the file is never imported or run.
- markdown: its headings.
- anything else: the line count and the first lines.

`select` cuts one part of a file: a def, class or assignment by name (`.py`, `Class.method` allowed), or a
heading's section (markdown).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from . import md

MARKDOWN = (".md", ".markdown")
DOC_SUFFIXES = MARKDOWN + (".txt", ".rst")
HEAD_LINES = 40            # lines shown for a file with no outline form


def is_doc(path: str | Path) -> bool:
    """Markdown or plain text: a `doc` reference. Everything else is `code`."""
    return Path(path).suffix.lower() in DOC_SUFFIXES


def read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


# ---- python -----------------------------------------------------------------------------------

def _doc_line(node: ast.AST) -> str:
    doc = ast.get_docstring(node) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else None
    return doc.strip().splitlines()[0].strip() if doc and doc.strip() else ""


def signature(node: ast.AST) -> str:
    """`def name(args) -> ret`, `async def …`, `class Name(bases)`."""
    if isinstance(node, ast.ClassDef):
        bases = [ast.unparse(b) for b in node.bases] + [ast.unparse(k) for k in node.keywords]
        return f"class {node.name}" + (f"({', '.join(bases)})" if bases else "")
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    ret = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix} {node.name}({ast.unparse(node.args)}){ret}"


def _defs(body: list[ast.stmt]):
    return [n for n in body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]


def py_outline(text: str) -> list[str] | None:
    """`<line>: <signature> — <docstring first line>` per def and class; None if the file doesn't parse."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    out = []

    def add(node, depth):
        doc = _doc_line(node)
        out.append(f"{node.lineno}: {'  ' * depth}{signature(node)}" + (f" — {doc}" if doc else ""))
        if isinstance(node, ast.ClassDef):
            for child in _defs(node.body):
                add(child, depth + 1)

    for node in _defs(tree.body):
        add(node, 0)
    return out


def _start(node: ast.AST) -> int:
    decorators = getattr(node, "decorator_list", [])
    return min([node.lineno] + [d.lineno for d in decorators])


def _named(body: list[ast.stmt], name: str) -> ast.AST | None:
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            return node
        targets = node.targets if isinstance(node, ast.Assign) else \
            [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return node
    return None


def py_symbol(text: str, name: str) -> tuple[int, int] | None:
    """1-based (first, last) lines of a module-level def, class or assignment called `name`, decorators
    included; `Class.method` names a method; a bare method name is found in the first class that has it."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    parts = name.split(".")
    node = _named(tree.body, parts[0])
    for part in parts[1:]:
        node = _named(node.body, part) if isinstance(node, ast.ClassDef) else None
    if node is None and len(parts) == 1:
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
            node = _named(cls.body, name)
            if node is not None:
                break
    if node is None:
        return None
    return _start(node), getattr(node, "end_lineno", None) or node.lineno


# ---- markdown ---------------------------------------------------------------------------------

def md_outline(text: str) -> list[str]:
    """`<line>: ## Heading` for every heading outside code fences."""
    lines = text.splitlines()
    return [f"{h.line + 1}: {'#' * h.level} {h.text}" for h in md.headings(lines)]


def md_section(text: str, heading: str) -> tuple[int, int] | None:
    """1-based (first, last) lines of the section under the heading whose text matches (case-insensitive)."""
    lines = text.splitlines()
    want = heading.strip().lstrip("#").strip().lower()
    for h in md.headings(lines):
        if h.text.lower() == want:
            end = h.end
            while end > h.line + 1 and not lines[end - 1].strip():
                end -= 1
            return h.line + 1, end
    return None


# ---- any file ---------------------------------------------------------------------------------

@dataclass
class Outline:
    kind: str              # python | markdown | text
    lines: int             # the file's line count
    items: list[str]       # outline lines (python, markdown) or the first lines (text)
    note: str = ""         # e.g. "cannot parse; first 40 lines"


def outline(path: Path, text: str) -> Outline:
    n = len(text.splitlines())
    suffix = path.suffix.lower()
    if suffix == ".py":
        items = py_outline(text)
        if items is not None:
            return Outline("python", n, items)
        return Outline("text", n, text.splitlines()[:HEAD_LINES], f"cannot parse; first {HEAD_LINES} lines")
    if suffix in MARKDOWN:
        return Outline("markdown", n, md_outline(text))
    return Outline("text", n, text.splitlines()[:HEAD_LINES], f"first {min(n, HEAD_LINES)} lines")


def render(rel: str, o: Outline) -> str:
    """The `dt outline` text: a `<path> · <kind> · <n> lines` line, then the outline."""
    head = f"{rel} · {o.kind} · {o.lines} lines" + (f" · {o.note}" if o.note else "")
    return "\n".join([head] + (o.items or ["(no defs or headings)"])) + "\n"


def select(path: Path, text: str, selector: str) -> tuple[int, int] | None:
    """1-based (first, last) lines the selector names: a symbol (`.py`) or a heading (markdown)."""
    suffix = path.suffix.lower()
    if suffix == ".py":
        return py_symbol(text, selector)
    if suffix in MARKDOWN:
        return md_section(text, selector)
    return None
