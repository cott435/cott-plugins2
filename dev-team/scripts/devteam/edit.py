"""Byte-preserving file edits for dt's mechanical commands (prebuild-clear, archive, finding, tick, roadmap,
base, references --stamp).

Lines keep their own endings, so everything an edit doesn't touch is written back exactly as read.
Line indices match `Doc.lines`, so a command can locate a section with the parser and splice here.
Writes go through a temp file and `os.replace`, so a file is never missing or half-written, and keep the
file's permission bits (a new file gets 0644 less the umask). Every dt write goes through `write_text`.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def read_lines(path: Path) -> list[str]:
    """The file's lines with their endings kept (no newline translation)."""
    with open(path, encoding="utf-8", newline="") as f:
        return f.read().splitlines(keepends=True)


def eol(lines: list[str]) -> str:
    """The file's line ending: `\\r\\n` if its first ended line uses it, else `\\n`."""
    for line in lines:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith(("\n", "\r")):
            return "\n"
    return "\n"


def ensure_eol(lines: list[str]) -> list[str]:
    """Give the last line an ending, so lines can be appended after it."""
    if lines and not lines[-1].endswith(("\n", "\r")):
        return lines[:-1] + [lines[-1] + eol(lines)]
    return lines


def _mode_for(path: Path) -> int:
    """The existing file's permission bits, else 0644 less the umask (`mkstemp` alone would leave 0600)."""
    try:
        return os.stat(path).st_mode & 0o7777
    except FileNotFoundError:
        umask = os.umask(0)
        os.umask(umask)
        return 0o644 & ~umask


def write_text(path: Path, text: str) -> None:
    """Write atomically: a temp file in the same folder, then `os.replace`. The file's mode is kept."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = _mode_for(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_lines(path: Path, lines: list[str]) -> None:
    write_text(path, "".join(lines))
