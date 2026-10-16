"""Print a file's outline: defs and classes with signatures and docstring first lines (`.py`, via ast; never
imported or run), headings (markdown), or the line count and first lines (anything else)."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from .. import model
from .. import outline as ol


def add_arguments(parser):
    parser.add_argument("file", help="a file path (relative to --root), or a reference ID such as RF-01")


def run(args, repo) -> int:
    target = args.file
    if re.fullmatch(model.REFERENCE_ID, target):
        entry = next((r for r in model.all_references(repo) if r.id == target), None)
        if entry is None or not entry.file:
            print(f"dt outline: {target} is not a reference entry with a File", file=sys.stderr)
            return 1
        target = entry.file
    path = Path(target)
    if not path.is_absolute():
        path = repo.root / target if (repo.root / target).exists() or not path.exists() else path.resolve()
    text = ol.read(path)
    if text is None:
        print(f"dt outline: cannot read {target} as UTF-8 text", file=sys.stderr)
        return 1
    try:
        rel = os.path.relpath(path.resolve(), repo.root).replace(os.sep, "/")
    except ValueError:
        rel = str(path)
    if rel.startswith("../"):
        rel = str(path)
    print(ol.render(rel, ol.outline(path, text)), end="")
    return 0
