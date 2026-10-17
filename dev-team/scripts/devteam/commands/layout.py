"""Print a package's real source tree with module docstrings, and flag entry functions that drift from their step tables."""
from __future__ import annotations

import json

from .. import code


def add_arguments(parser):
    parser.add_argument("pkg", help="package id (docs/packages/<pkg>/)")
    parser.add_argument("--json", action="store_true", help="print one JSON object")


def run(args, repo) -> int:
    pkg = args.pkg
    folder = code.source_folder(repo, pkg)
    root = repo.root / folder
    if pkg not in repo.packages() and not root.is_dir():
        print(f"dt layout: unknown package {pkg!r} (no docs/packages/{pkg}/ and no {folder}/)")
        return 2
    tree = code.source_tree(root) if root.is_dir() else []
    checks = [code.check_pipeline(repo, p) for p in code.package_pipelines(repo, pkg)]
    drift = any(c.status == "drift" for c in checks)

    if args.json:
        print(json.dumps({
            "package": pkg,
            "root": folder + "/",
            "exists": root.is_dir(),
            "tree": [{"path": e.rel, "dir": e.is_dir, "doc": e.doc} for e in tree],
            "pipelines": [{"id": c.id, "entry": f"{c.entry_file}::{c.function}", "status": c.status,
                           "calls": c.calls, "steps": c.steps, "detail": c.detail} for c in checks],
        }, indent=2))
        return 1 if drift else 0

    print(f"package: {pkg}")
    print(f"root: {folder}/{'' if root.is_dir() else ' (missing)'}")
    print("".join(tree_lines(tree)), end="")
    for c in checks:
        print(c.line())
    return 1 if drift else 0


def tree_lines(tree: list[code.TreeEntry]) -> list[str]:
    """Indented tree lines, each `.py` with its docstring's first line."""
    out = []
    for e in tree:
        name = e.rel.rstrip("/").rsplit("/", 1)[-1] + ("/" if e.is_dir else "")
        note = f" — {e.doc}" if e.doc else (" — (no docstring)" if name.endswith(".py") else "")
        out.append(f"{'  ' * (e.depth + 1)}{name}{note}\n")
    return out
