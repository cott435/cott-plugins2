#!/usr/bin/env python3
"""Module and function size checker (Ruff has no rule for either).

Usage:
    python scripts/check_size.py [PATH ...]      # default: src

Limits come from [tool.size_limits] in pyproject.toml:

    [tool.size_limits]
    max_module_lines = 500      # code lines per file
    min_module_lines = 3        # skip __init__.py; catches empty placeholder files
    max_function_lines = 60     # code lines per function/method (incl. docstring)

"Code lines" = non-blank lines that are not pure comments.
Output format mimics Ruff (path:line: CODE message). Exit 1 on any violation.

    SIZE001 module too long
    SIZE002 module too short
    SIZE003 function too long
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

DEFAULTS = {"max_module_lines": 500, "min_module_lines": 3, "max_function_lines": 60}
SKIP_DIRS = {".venv", "venv", "node_modules", "__pycache__", ".git", "build", "dist"}


def load_limits(pyproject: Path) -> dict[str, int]:
    limits = dict(DEFAULTS)
    if pyproject.is_file():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        limits.update(data.get("tool", {}).get("size_limits", {}))
    return limits


def iter_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*.py")) if not SKIP_DIRS & set(f.parts)]
        elif p.suffix == ".py" and p.is_file():
            files.append(p)
    return files


def is_code(line: str) -> bool:
    s = line.strip()
    return bool(s) and not s.startswith("#")


def check_file(path: Path, limits: dict[str, int]) -> list[str]:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    problems: list[str] = []

    n = sum(is_code(line) for line in lines)
    if n > limits["max_module_lines"]:
        problems.append(
            f"{path}:1: SIZE001 module has {n} code lines (max {limits['max_module_lines']})"
        )
    if path.name != "__init__.py" and n < limits["min_module_lines"]:
        problems.append(
            f"{path}:1: SIZE002 module has {n} code lines (min {limits['min_module_lines']})"
        )

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [*problems, f"{path}:{exc.lineno or 1}: SIZE000 cannot parse: {exc.msg}"]

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = min([node.lineno, *(d.lineno for d in node.decorator_list)])
            body = lines[start - 1 : node.end_lineno]
            size = sum(is_code(line) for line in body)
            if size > limits["max_function_lines"]:
                problems.append(
                    f"{path}:{node.lineno}: SIZE003 function `{node.name}` has {size} code lines "
                    f"(max {limits['max_function_lines']})"
                )
    return problems


def main(argv: list[str]) -> int:
    limits = load_limits(Path("pyproject.toml"))
    problems: list[str] = []
    for f in iter_files(argv or ["src"]):
        problems += check_file(f, limits)
    if problems:
        print("\n".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
