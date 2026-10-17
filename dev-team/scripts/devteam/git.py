"""Thin git helpers. Every function degrades to None/[] outside a git repo or when git is missing."""
from __future__ import annotations

import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def is_repo(root: Path) -> bool:
    return _git(root, "rev-parse", "--is-inside-work-tree") is not None


def last_commit_date(root: Path, *paths: str) -> str | None:
    """ISO date (YYYY-MM-DD) of the newest commit touching any of the paths."""
    out = _git(root, "log", "-1", "--format=%cs", "--", *paths)
    return out.strip() or None if out is not None else None


def show_head(root: Path, rel: str) -> str | None:
    """The file's text at HEAD, or None if it isn't tracked there. `rel` is relative to root (`./` makes git
    resolve it from root, so this also works when root is a subfolder of the git repo)."""
    return _git(root, "show", f"HEAD:./{rel}")


def changed_files(root: Path) -> list[str]:
    """Paths changed vs HEAD (staged, unstaged) plus untracked files, relative to root (and only under it)."""
    out = []
    for args in (("diff", "--name-only", "--relative", "HEAD"), ("ls-files", "--others", "--exclude-standard")):
        res = _git(root, *args)
        if res:
            out.extend(line for line in res.splitlines() if line)
    return sorted(set(out))


def head_sha(root: Path) -> str | None:
    out = _git(root, "rev-parse", "--short", "HEAD")
    return out.strip() if out else None


def last_commit_time(root: Path, *paths: str) -> int | None:
    """Unix time of the newest commit touching any of the paths (finer than `last_commit_date`)."""
    out = _git(root, "log", "-1", "--format=%ct", "--", *paths)
    return int(out.strip()) if out and out.strip().isdigit() else None
