"""PreToolUse guard: ask before an oracle file or a frozen boundary contract changes, deny writes to the plan
archive."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from .. import md, model
from ..repo import Repo

# Matched anywhere in the path: asking is the safe side.
ORACLE_RE = re.compile(r"(?:^|/)tests/fixtures/(?:[^/]+/)*expected\.json$")
# Matched anywhere in the path; what precedes it is the project root. Group 1: the path inside tests/contracts/.
CONTRACT_RE = re.compile(r"(?:^|/)tests/contracts/(.+)$")
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
    m = CONTRACT_RE.search(p.as_posix())
    if m and not _contract_open(Path(p.as_posix()[:m.start()] or "/"), m.group(1)):
        return _decision("ask", f"Frozen contract: {path}. No open contract task (`**Step:** contract`) freezes "
                                "it; a boundary contract changes only through architecture-design Revise (CR-09).")
    return None


def _contract_open(root: Path, inside: str) -> bool:
    """Whether an unticked contract task of root's plan freezes this path under tests/contracts/: its folder
    (`<pkg>.<symbol>`) is in the task's `Read:` or `Files likely`. A file directly in tests/contracts/ is
    shared support, open while any contract task is."""
    repo = Repo(root)
    if repo.plan is None:
        return False
    done = model.todo_state(repo)
    folder = inside.split("/", 1)[0] if "/" in inside else None
    for t in model.tasks(repo.plan):
        if not t.is_contract or done.get(t.id):
            continue
        names = {md.strip_md(i).split(" (")[0].strip() for i in t.read}
        files = [md.strip_md(f).rstrip("/") + "/" for f in t.files_likely]
        if folder is None or folder in names or any(f.startswith(f"tests/contracts/{folder}/") for f in files):
            return True
    return False


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
