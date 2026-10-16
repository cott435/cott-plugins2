"""PreToolUse guard: ask before an oracle file changes, deny writes to the plan archive."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Matched anywhere in the path: asking is the safe side.
ORACLE_RE = re.compile(r"(?:^|/)tests/fixtures/(?:[^/]+/)*expected\.json$")
# Matched only from the project root: denying is the strict side.
ARCHIVE_RE = re.compile(r"^tasks/archive/")


def add_arguments(parser):
    parser.add_argument("--path", help="decide for this path (relative to --root) instead of reading hook JSON")


def decide(file_path: str, cwd: str) -> dict | None:
    """The hook output for a write to file_path, or None to let it through."""
    root = Path(cwd).resolve()
    p = Path(file_path)
    p = (p if p.is_absolute() else root / p).resolve()
    rel = os.path.relpath(p, root).replace(os.sep, "/")
    inside = not (rel == ".." or rel.startswith("../"))
    path = rel if inside else p.as_posix()
    if inside and ARCHIVE_RE.match(rel):
        return _decision("deny", f"Archived plan: {rel} is written only by `dt archive`.")
    if ORACLE_RE.search(path):
        return _decision("ask", f"Oracle file: {path}. Expected outputs change only with the user's approval.")
    return None


def _decision(kind: str, reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": kind,
                                   "permissionDecisionReason": reason}}


def run(args, repo) -> int:
    # Fails open: a guard that crashes must not block every edit.
    try:
        if args.path:
            out = decide(args.path, args.root)
        else:
            event = json.loads(sys.stdin.read())
            tool_input = event.get("tool_input") or {}
            file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
            out = decide(file_path, event.get("cwd") or os.getcwd()) if file_path else None
    except Exception:
        return 0
    if out is not None:
        print(json.dumps(out))
    return 0
