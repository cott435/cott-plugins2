"""Reference files (`references/`) against their index (`docs/references.md`): hashes, and which files are
waiting for reference-intake. Used by `dt status`, `dt references`, `dt context` and lint."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from . import model
from .repo import IGNORE_DIRS, Repo

FOLDER = "references"
LARGE_LINES = 300          # a reference over this many lines needs a selector in `Read:`
INTAKE_OUTLINE_LINES = 400  # intake gives a subagent `dt outline` + the first lines above this


def file_hash(path) -> str | None:
    """First 8 hex digits of the file's sha256, or None if it can't be read."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:8]
    except OSError:
        return None


def files(repo: Repo) -> list[str]:
    """Repo-relative paths of every file under references/ (hidden and cache files skipped), sorted."""
    base = repo.root / FOLDER
    if not base.is_dir():
        return []
    out = []
    for d, subdirs, names in os.walk(base):
        subdirs[:] = sorted(s for s in subdirs if s not in IGNORE_DIRS and not s.startswith("."))
        for name in sorted(names):
            if not name.startswith(".") and not name.endswith(".pyc"):
                out.append(os.path.relpath(os.path.join(d, name), repo.root).replace(os.sep, "/"))
    return sorted(out)


def line_count(repo: Repo, rel: str) -> int:
    try:
        with open(repo.root / rel, encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


@dataclass
class State:
    unindexed: list[str] = field(default_factory=list)   # files with no entry
    changed: list[str] = field(default_factory=list)     # `RF-NN (path)`: hash differs, or none stamped
    missing: list[str] = field(default_factory=list)     # `RF-NN (path)`: the entry's file is gone
    to_read: list[str] = field(default_factory=list)     # unindexed + changed files, for intake

    @property
    def waiting(self) -> int:
        return len(self.unindexed) + len(self.changed) + len(self.missing)


def state(repo: Repo) -> State:
    entries = model.all_references(repo)
    s = State()
    indexed = {e.file for e in entries if e.file}
    s.unindexed = [f for f in files(repo) if f not in indexed]
    for e in entries:
        if not e.file:
            continue
        current = file_hash(repo.root / e.file)
        if current is None:
            s.missing.append(f"{e.id} ({e.file})")
        elif current != e.hash.lower():
            s.changed.append(f"{e.id} ({e.file})")
            s.to_read.append(e.file)
    s.to_read = sorted(set(s.to_read) | set(s.unindexed))
    return s
