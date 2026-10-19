#!/usr/bin/env python3
"""Diff-scoped floor checks for CONSTRAINTS.md (CR-01 to CR-04, CR-07, CR-08).

Called by scripts/floor_guard.sh, which writes the diff, the untracked-file list and the
base commit's pyproject.toml. Prints one line per finding and exits 1 if there are any:

    path:line: [rule] message

Rules (CONSTRAINTS.md ID in brackets):
    suppression [CR-01]            a new `type: ignore`, `pyright:`, `noqa`, `pragma: no cover`...
    stub [CR-02]                   a function whose body is only pass, ... or NotImplementedError
    stub-task [CR-02]              an interface stub, `raise NotImplementedError("M1-T05")`, naming
                                   a task that is not open in tasks/todo.md (whole repo, not the diff)
    stub-left [CR-02]              any interface stub, with --exit (the milestone exit)
    stub-pinned [CR-02]            a test naming NotImplementedError: it would pin a stub that a
                                   later task replaces, so no implementer could pass it
    swallowed-exception [CR-02]    `except:` / `except Exception:` with only pass
    test-skipped [CR-03]           a new skip, skipif, xfail or importorskip
    test-deleted [CR-03]           a test file removed
    assertion-removed [CR-03]      a test file lost more assertion lines than it gained
    test-without-assertion [CR-03] a changed test function that asserts nothing
    secret [CR-04]                 a credential pattern (the value is never printed)
    references-import [CR-08]      an import from the references folder
    references-path [CR-08]        the references folder put on an import path (sys.path,
                                   an environment variable, pytest or type-checker config)
    probes-import, probes-path     the same for the probes folder [CR-08]
    bar-loosened [CR-07]           pyproject.toml tool config weakened, or a new config file
    rule-removed [CR-07]           a CR rule gone from CONSTRAINTS.md
    new-exception [CR-07]          a new row in CONSTRAINTS.md's Exceptions table

An interface stub is the one placeholder body CR-02 allows: the milestone's interface task writes
each step signature that way, naming the task that replaces it, and testers import it before the
code exists. It is never a `stub` finding; `stub-task` and `stub-left` judge it instead.

A CR-01 to CR-03 or CR-08 finding is allowed when an unexpired row in CONSTRAINTS.md's
Exceptions table names that rule and a path glob matching the file. Secrets and CR-07 never are.
Files under scripts/ are skipped for code checks: they are the bar, protected separately.
Files under references/ and probes/ are inputs, not project code: only the secret check reads them.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import re
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, NamedTuple

SUPPRESSION = re.compile(
    r"#\s*(type:\s*ignore|pyright:\s*\w|mypy:\s*ignore|noqa|ruff:\s*noqa"
    r"|pragma:\s*no\s*(cover|branch)|nosec|pylint:\s*(disable|skip-file))"
    r"|@(typing\.)?no_type_check\b",
    re.IGNORECASE,
)
SKIP = re.compile(
    r"pytest\.mark\.(skip|skipif|xfail)\b|pytest\.(skip|importorskip)\(|unittest\.skip"
)
ASSERTION = re.compile(r"\bassert\b|pytest\.(raises|warns)\(|\bassert\w*\(")
SECRETS = {
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private-key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "github-token": re.compile(r"\bgh[opsur]_[A-Za-z0-9]{36,}\b"),
    "slack-token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "stripe-live-key": re.compile(r"\b[rs]k_live_[A-Za-z0-9]{16,}"),
    "api-key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
}
# CR-08. Folders that are inputs, not project code, each as a path or module word:
# "references", "../references/x", "references.x".
OUTSIDE = {f: re.compile(rf"(?<![\w.-]){f}(?![\w-])") for f in ("references", "probes")}
# Settings that put a folder on the import path, outside Python code (shell, TOML, CI, .env).
IMPORT_PATH_SETTING = re.compile(r"\b(PYTHONPATH|mypy_path|extraPaths)\b", re.IGNORECASE)
DOC_SUFFIXES = (".md", ".rst", ".txt")
SYS_PATH_CALLS = {"insert", "append", "extend"}
RULE_IDS = {
    "suppression": "CR-01",
    "stub": "CR-02",
    "stub-task": "CR-02",
    "stub-left": "CR-02",
    "stub-pinned": "CR-02",
    "swallowed-exception": "CR-02",
    "test-skipped": "CR-03",
    "test-deleted": "CR-03",
    "assertion-removed": "CR-03",
    "test-without-assertion": "CR-03",
    "references-import": "CR-08",
    "references-path": "CR-08",
    "probes-import": "CR-08",
    "probes-path": "CR-08",
}
CONFIG_FILES = {
    "ruff.toml", ".ruff.toml", "mypy.ini", ".mypy.ini", "pytest.ini", "setup.cfg", "tox.ini",
    "pyrightconfig.json", ".coveragerc", ".importlinter", "typos.toml", "_typos.toml",
    ".typos.toml", ".deptry.toml", "pylintrc", ".pylintrc", "pylintrc.toml",
}  # fmt: skip
LOCKFILES = {"uv.lock", "poetry.lock", "pdm.lock", "Pipfile.lock"}
TASK_ID = re.compile(r"M\d+-T\d{2,}")
OPEN_TASK = re.compile(r"^\s*- \[ \] (M\d+-T\d{2,})\b", re.MULTILINE)
EXEMPT_DECORATORS = {"abstractmethod", "abstractproperty", "overload"}
TRIVIAL_EXCEPT = {None, "Exception", "BaseException"}


class Finding(NamedTuple):
    rule: str
    path: str
    line: int  # 0 when the finding has no single line
    message: str

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}: [{self.rule}] {self.message}"


@dataclass
class Diff:
    added: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    removed: dict[str, list[str]] = field(default_factory=dict)
    deleted: set[str] = field(default_factory=set)

    def added_lines(self, path: str) -> set[int]:
        return {n for n, _ in self.added.get(path, [])}


# ----------------------------------------------------------------------------- the diff
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _diff_path(raw: str) -> str:
    raw = raw.rstrip("\t")
    return raw[2:] if raw[:2] in {"a/", "b/"} else raw


def parse_diff(text: str) -> Diff:
    """Added lines (with new line numbers), removed lines and deleted files, per file."""
    diff = Diff()
    old = new = ""
    line_no = 0
    in_header = False
    for line in text.splitlines():
        if line.startswith("diff --git "):
            old, new, in_header = "", "", True
        elif in_header and line.startswith("--- "):
            old = _diff_path(line[4:])
        elif in_header and line.startswith("+++ "):
            new = _diff_path(line[4:])
            if new == "/dev/null":
                diff.deleted.add(old)
        elif match := HUNK.match(line):
            in_header, line_no = False, int(match[1])
        elif in_header:
            continue
        elif line.startswith("+"):
            diff.added.setdefault(new, []).append((line_no, line[1:]))
            line_no += 1
        elif line.startswith("-"):
            diff.removed.setdefault(old, []).append(line[1:])
    return diff


def add_untracked(diff: Diff, paths: list[str]) -> None:
    """An untracked file is all added lines."""
    for name in paths:
        path = Path(name)
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        diff.added[name] = list(enumerate(text.splitlines(), start=1))


# --------------------------------------------------------------------------- line checks
def is_outside(path: str) -> bool:
    return path.startswith(tuple(f"{folder}/" for folder in OUTSIDE))


def is_python(path: str) -> bool:
    if path.startswith("scripts/") or is_outside(path):
        return False
    return path.endswith((".py", ".pyi"))


def is_test_file(path: str) -> bool:
    parts = Path(path).parts
    name = parts[-1] if parts else ""
    return (
        "tests" in parts
        and (name.startswith("test_") or name.endswith("_test.py"))
        and not is_outside(path)
    )


def line_findings(diff: Diff) -> list[Finding]:
    found: list[Finding] = []
    for path, lines in diff.added.items():
        python, test = is_python(path), is_test_file(path)
        path_settings = not is_outside(path) and not path.endswith(DOC_SUFFIXES)
        for n, text in lines:
            if python and SUPPRESSION.search(text):
                found.append(Finding("suppression", path, n, "new suppression comment"))
            if path_settings and IMPORT_PATH_SETTING.search(text):
                found += [
                    Finding(f"{folder}-path", path, n, f"{folder}/ on an import path")
                    for folder, word in OUTSIDE.items()
                    if word.search(text)
                ]
            if test and SKIP.search(text):
                found.append(Finding("test-skipped", path, n, "test skipped or marked xfail"))
            if Path(path).name not in LOCKFILES:
                found += [
                    Finding("secret", path, n, f"looks like a {kind} (value not shown)")
                    for kind, pattern in SECRETS.items()
                    if pattern.search(text)
                ]
    return found


def test_file_findings(diff: Diff) -> list[Finding]:
    found = [
        Finding("test-deleted", p, 0, "test file deleted") for p in diff.deleted if is_test_file(p)
    ]
    for path, lines in diff.removed.items():
        if not is_test_file(path) or path in diff.deleted:
            continue
        lost = sum(bool(ASSERTION.search(t)) for t in lines)
        gained = sum(bool(ASSERTION.search(t)) for _, t in diff.added.get(path, []))
        if lost > gained:
            found.append(
                Finding("assertion-removed", path, 0, f"{lost - gained} assertion line(s) removed")
            )
    return found


# ---------------------------------------------------------------------------- AST checks
def _touches(node: ast.AST, lines: set[int]) -> bool:
    start = getattr(node, "lineno", 0)
    end = getattr(node, "end_lineno", start) or start
    return any(start <= n <= end for n in lines)


def _is_trivial(body: list[ast.stmt]) -> bool:
    """Only pass, `...` or `raise NotImplementedError`, after an optional docstring."""
    stmts = body[1:] if body and _is_docstring(body[0]) else body
    return all(_is_placeholder(s) for s in stmts)


def _task_stub(body: list[ast.stmt]) -> str | None:
    """The task an interface stub names: a body that is only `raise NotImplementedError("M1-T05")`."""
    stmts = body[1:] if body and _is_docstring(body[0]) else body
    if len(stmts) != 1 or not isinstance(stmts[0], ast.Raise):
        return None
    exc = stmts[0].exc
    if not (isinstance(exc, ast.Call) and _name(exc.func) == "NotImplementedError"):
        return None
    arg = exc.args[0] if len(exc.args) == 1 and not exc.keywords else None
    if (
        isinstance(arg, ast.Constant)
        and isinstance(arg.value, str)
        and TASK_ID.fullmatch(arg.value)
    ):
        return arg.value
    return None


def _is_docstring(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def _is_placeholder(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        return stmt.value.value is Ellipsis
    if isinstance(stmt, ast.Raise) and stmt.exc is not None:
        exc = stmt.exc.func if isinstance(stmt.exc, ast.Call) else stmt.exc
        return _name(exc) == "NotImplementedError"
    return False


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _name(node.func)
    return None


def _exempt_functions(tree: ast.Module) -> set[ast.AST]:
    """Abstract methods, overloads and Protocol members may have placeholder bodies."""
    exempt: set[ast.AST] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if {_name(d) for d in node.decorator_list} & EXEMPT_DECORATORS:
                exempt.add(node)
        elif isinstance(node, ast.ClassDef) and "Protocol" in {_name(b) for b in node.bases}:
            exempt.update(
                n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
    return exempt


def _in_folder(name: str | None, folder: str) -> bool:
    return name is not None and (name == folder or name.startswith(f"{folder}."))


def _mentions(node: ast.AST, word: re.Pattern[str]) -> bool:
    return any(
        isinstance(n, ast.Constant) and isinstance(n.value, str) and word.search(n.value)
        for n in ast.walk(node)
    )


def _is_sys_path(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "path"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def _imported_modules(node: ast.AST) -> list[str | None]:
    """Absolute module names an import statement or an import_module call brings in."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return [node.module] if node.level == 0 else []
    if isinstance(node, ast.Call) and _name(node.func) in {"import_module", "__import__"}:
        first = node.args[0] if node.args else None
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return [first.value]
    return []


def _changes_sys_path(node: ast.AST) -> bool:
    """sys.path.insert/append/extend, site.addsitedir, or an assignment to sys.path."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        func = node.func
        return func.attr == "addsitedir" or (
            func.attr in SYS_PATH_CALLS and _is_sys_path(func.value)
        )
    if isinstance(node, ast.Assign):
        return any(_is_sys_path(target) for target in node.targets)
    if isinstance(node, ast.AugAssign):
        return _is_sys_path(node.target)
    return False


def _outside_finding(path: str, node: ast.AST) -> Finding | None:
    """CR-08: an import from references/ or probes/, or either folder added to sys.path."""
    line = getattr(node, "lineno", 0)
    for folder, word in OUTSIDE.items():
        if any(_in_folder(name, folder) for name in _imported_modules(node)):
            return Finding(f"{folder}-import", path, line, f"import from {folder}/")
        if _changes_sys_path(node) and _mentions(node, word):
            return Finding(f"{folder}-path", path, line, f"{folder}/ added to sys.path")
    return None


def _asserts(func: ast.AST) -> bool:
    for node in ast.walk(func):
        if isinstance(node, ast.Assert):
            return True
        name = _name(node) if isinstance(node, ast.Call) else None
        if name and (
            name.startswith("assert") or name in {"raises", "warns", "deprecated_call", "fail"}
        ):
            return True
    return False


def _stub_pinned(path: str, node: ast.AST, test: bool) -> list[Finding]:
    """A test naming NotImplementedError: it passes only while a stub stands (CR-02)."""
    if not test or isinstance(node, ast.Call) or _name(node) != "NotImplementedError":
        return []
    message = "a test expects NotImplementedError: check the signature, not the stub body"
    return [Finding("stub-pinned", path, getattr(node, "lineno", 0), message)]


def ast_findings(path: str, lines: set[int]) -> list[Finding]:
    try:
        tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []  # ruff reports syntax errors; a deleted file has nothing to check
    exempt, test = _exempt_functions(tree), is_test_file(path)
    found: list[Finding] = []
    for node in ast.walk(tree):
        if not _touches(node, lines):
            continue
        if outside := _outside_finding(path, node):
            found.append(outside)
        found += _stub_pinned(path, node, test)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                node not in exempt
                and not path.endswith(".pyi")
                and _is_trivial(node.body)
                and not _task_stub(node.body)
            ):
                found.append(
                    Finding("stub", path, node.lineno, f"`{node.name}` has a placeholder body")
                )
            if test and node.name.startswith("test") and not _asserts(node):
                found.append(
                    Finding(
                        "test-without-assertion",
                        path,
                        node.lineno,
                        f"`{node.name}` asserts nothing",
                    )
                )
        elif isinstance(node, ast.ExceptHandler) and _is_trivial(node.body):
            if (None if node.type is None else _name(node.type)) in TRIVIAL_EXCEPT:
                found.append(
                    Finding("swallowed-exception", path, node.lineno, "exception swallowed")
                )
    return found


def open_tasks() -> set[str]:
    """Task IDs with an unchecked line in tasks/todo.md (none when there is no todo)."""
    path = Path("tasks/todo.md")
    return set(OPEN_TASK.findall(path.read_text(encoding="utf-8"))) if path.is_file() else set()


def task_stub_findings(paths: list[str], at_exit: bool) -> list[Finding]:
    """Interface stubs anywhere in the project's code: each must name an open task, and at the
    milestone exit none may be left. Not diff-scoped: the stub was written by an earlier task."""
    open_ids, found = open_tasks(), []
    for path in paths:
        if not is_python(path) or is_test_file(path) or not Path(path).is_file():
            continue
        try:
            tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not (task := _task_stub(node.body)):
                continue
            if at_exit:
                found.append(
                    Finding(
                        "stub-left",
                        path,
                        node.lineno,
                        f"`{node.name}` is still the stub for {task}",
                    )
                )
            elif task not in open_ids:
                found.append(
                    Finding(
                        "stub-task",
                        path,
                        node.lineno,
                        f"`{node.name}` is a stub naming {task}, which is not open in tasks/todo.md",
                    )
                )
    return found


# ---------------------------------------------------------------- the bar: tool config
MAX_KEYS = (
    "tool.ruff.lint.mccabe.max-complexity",
    "tool.size_limits.max_module_lines",
    "tool.size_limits.max_function_lines",
    "tool.vulture.min_confidence",
    "tool.pylint.similarities.min-similarity-lines",
)
MIN_KEYS = ("tool.coverage.report.fail_under", "tool.size_limits.min_module_lines")
TRUE_KEYS = ("tool.mypy.strict", "tool.pytest.ini_options.xfail_strict")
OFF_KEYS = ("tool.pylint.main.exit-zero",)  # turning one on silences a check
NO_SHRINK = ("tool.ruff.lint.select", "tool.ruff.lint.extend-select")
NO_GROW = (
    "tool.ruff.lint.ignore", "tool.ruff.lint.extend-ignore", "tool.ruff.exclude",
    "tool.ruff.extend-exclude", "tool.ruff.lint.exclude", "tool.deptry.exclude",
    "tool.deptry.extend_exclude", "tool.deptry.ignore", "tool.vulture.ignore_names",
    "tool.vulture.exclude", "tool.mypy.exclude", "tool.pylint.main.ignore-paths",
    "tool.pylint.main.ignore", "tool.pylint.main.ignore-patterns",
)  # fmt: skip
# Excluding the references or probes folder is not a loosening: neither is project code (CR-08).
OUTSIDE_EXCLUDE = re.compile(r"\^?(references|probes)/?\*{0,2}")
NO_GROW_TABLES = ("tool.ruff.lint.per-file-ignores", "tool.deptry.per_rule_ignores")
MUST_MATCH = ("tool.importlinter", "tool.mypy.overrides", "tool.pyright")
STRICT_FLAGS = ("--strict-markers", "--strict-config")


def _get(data: dict[str, Any], dotted: str) -> Any:
    for key in dotted.split("."):
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    return data


def _as_set(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    return {str(v) for v in value} if isinstance(value, list) else set()


def _limit_findings(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    pylint = _get(old, "tool.ruff.lint.pylint") or {}
    maxes = [*MAX_KEYS, *(f"tool.ruff.lint.pylint.{k}" for k in pylint)]
    out = [
        f"{k}: {_get(old, k)} -> {_get(new, k)}"
        for k in maxes
        if _loosened(_get(old, k), _get(new, k), +1)
    ]
    out += [
        f"{k}: {_get(old, k)} -> {_get(new, k)}"
        for k in MIN_KEYS
        if _loosened(_get(old, k), _get(new, k), -1)
    ]
    out += [
        f"{k} turned off" for k in TRUE_KEYS if _get(old, k) is True and _get(new, k) is not True
    ]
    out += [f"{k} turned on" for k in OFF_KEYS if _get(new, k) is True and _get(old, k) is not True]
    return out


def _loosened(was: Any, now: Any, direction: int) -> bool:
    if not isinstance(was, (int, float)):
        return False
    if not isinstance(now, (int, float)):
        return True  # a limit that disappeared
    return (now - was) * direction > 0


def _list_findings(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    out = [f"{k} lost {sorted(_as_set(_get(old, k)) - _as_set(_get(new, k)))}" for k in NO_SHRINK]
    for k in NO_GROW:
        gained = _as_set(_get(new, k)) - _as_set(_get(old, k))
        out.append(f"{k} gained {sorted(g for g in gained if not OUTSIDE_EXCLUDE.fullmatch(g))}")
    for table in NO_GROW_TABLES:
        was, now = _get(old, table) or {}, _get(new, table) or {}
        out += [
            f"{table}.{key} gained {sorted(_as_set(codes) - _as_set(was.get(key)))}"
            for key, codes in now.items()
            if _as_set(codes) - _as_set(was.get(key))
        ]
    flags = _as_set((_get(new, "tool.pytest.ini_options.addopts") or "").split())
    out += [
        f"pytest addopts dropped {f}"
        for f in STRICT_FLAGS
        if f in str(_get(old, "tool.pytest.ini_options.addopts")) and f not in flags
    ]
    out += [
        f"{k} changed (boundaries and type config change only through build-setup)"
        for k in MUST_MATCH
        if _get(old, k) != _get(new, k)
    ]
    return [o for o in out if not o.endswith("[]")]


def config_findings(old_pyproject: Path, diff: Diff) -> list[Finding]:
    found = [
        Finding("bar-loosened", p, 0, "new tool config file overrides pyproject.toml")
        for p in diff.added
        if Path(p).name in CONFIG_FILES and not p.startswith("scripts/")
    ]
    old_text = old_pyproject.read_text(encoding="utf-8") if old_pyproject.is_file() else ""
    if not old_text or not Path("pyproject.toml").is_file():
        return found
    try:
        old, new = (
            tomllib.loads(old_text),
            tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8")),
        )
    except tomllib.TOMLDecodeError as exc:
        return [*found, Finding("bar-loosened", "pyproject.toml", 0, f"cannot parse: {exc}")]
    changes = _limit_findings(old, new) + _list_findings(old, new)
    return found + [Finding("bar-loosened", "pyproject.toml", 0, c) for c in changes]


# ---------------------------------------------------------------------- CONSTRAINTS.md
RULE_REF = re.compile(r"^\s*(?:-\s*\*\*(CR-\d+)\*\*|\|\s*(CR-\d+)\s*\|)")


def _section(lines: list[str], title: str) -> tuple[int, int]:
    """1-based line range of a `## title` section, or (0, -1)."""
    start = next((i for i, t in enumerate(lines, 1) if t.strip().lower() == f"## {title}"), 0)
    if not start:
        return 0, -1
    end = next(
        (i - 1 for i, t in enumerate(lines, 1) if i > start and t.startswith("## ")), len(lines)
    )
    return start, end


def _table_rows(lines: list[str], start: int, end: int) -> list[tuple[int, list[str]]]:
    rows = []
    for n in range(start + 1, end + 1):
        text = lines[n - 1].strip()
        if not text.startswith("|"):
            continue
        cells = [c.strip() for c in text.strip("|").split("|")]
        if cells and cells[0] not in {"", "ID"} and not set(cells[0]) <= set("-: "):
            rows.append((n, cells))
    return rows


def constraints_findings(diff: Diff) -> list[Finding]:
    path = "CONSTRAINTS.md"
    if path not in diff.added and path not in diff.removed:
        return []
    still = {
        m.group(1) or m.group(2) for _, t in diff.added.get(path, []) if (m := RULE_REF.match(t))
    }
    gone = {
        m.group(1) or m.group(2) for t in diff.removed.get(path, []) if (m := RULE_REF.match(t))
    }
    found = [Finding("rule-removed", path, 0, f"{rule} removed") for rule in sorted(gone - still)]
    lines = Path(path).read_text(encoding="utf-8").splitlines() if Path(path).is_file() else []
    start, end = _section(lines, "exceptions")
    new_rows = diff.added_lines(path)
    found += [
        Finding("new-exception", path, n, f"new exception {cells[0]} needs the user's yes")
        for n, cells in _table_rows(lines, start, end)
        if n in new_rows
    ]
    return found


def load_exceptions(today: date) -> list[tuple[str, str]]:
    """(rule cell, path glob) for each unexpired row in CONSTRAINTS.md's Exceptions table."""
    path = Path("CONSTRAINTS.md")
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    allowed = []
    for _, cells in _table_rows(lines, *_section(lines, "exceptions")):
        if len(cells) < 6:
            continue
        expires = re.match(r"\d{4}-\d{2}-\d{2}", cells[5])
        if expires and date.fromisoformat(expires[0]) < today:
            continue
        allowed.append((cells[1], cells[2].strip("`")))
    return allowed


def is_excepted(finding: Finding, allowed: list[tuple[str, str]]) -> bool:
    rule_id = RULE_IDS.get(finding.rule)
    return bool(rule_id) and any(
        rule_id in rule and fnmatch.fnmatch(finding.path, glob) for rule, glob in allowed
    )


# ---------------------------------------------------------------------------------- main
def run(
    diff: Diff, old_pyproject: Path, python_files: list[str] | None = None, at_exit: bool = False
) -> list[Finding]:
    found = line_findings(diff) + test_file_findings(diff)
    found += task_stub_findings(python_files or [], at_exit)
    for path in diff.added:
        if is_python(path):
            found += ast_findings(path, diff.added_lines(path))
    found += config_findings(old_pyproject, diff) + constraints_findings(diff)
    allowed = load_exceptions(datetime.now(tz=UTC).date())
    return [f for f in found if not is_excepted(f, allowed)]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--diff", type=Path, required=True)
    parser.add_argument("--untracked", type=Path, required=True)
    parser.add_argument("--old-pyproject", type=Path, required=True)
    parser.add_argument(
        "--python", type=Path, help="every Python file in the project, one per line"
    )
    parser.add_argument(
        "--exit", action="store_true", help="the milestone exit: no stub may be left"
    )
    args = parser.parse_args(argv)
    diff = parse_diff(args.diff.read_text(encoding="utf-8", errors="replace"))
    add_untracked(diff, args.untracked.read_text(encoding="utf-8").splitlines())
    python_files = args.python.read_text(encoding="utf-8").splitlines() if args.python else []
    findings = run(diff, args.old_pyproject, python_files, args.exit)
    if not findings:
        print("floor_guard: clean", file=sys.stderr)
        return 0
    print("\n".join(str(f) for f in sorted(findings)))
    print(
        f"floor_guard: {len(findings)} floor violation(s). Fix the code; a real exception goes "
        "through build-setup (Revise) and the Exceptions table in CONSTRAINTS.md.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
