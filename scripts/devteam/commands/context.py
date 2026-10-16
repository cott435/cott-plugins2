"""Print a task's whole builder context packet: its Read: sections and files, the package layout, the Files likely
list, then the task."""
from __future__ import annotations

import json
import re
import sys

from .. import code, model
from .layout import tree_lines

BUDGET = 2000          # lines; agent-skills context-engineering target for one builder
PLAN_KINDS = ("plan", "queued-plan")
LANGS = {".py": "python", ".md": "markdown", ".json": "json", ".toml": "toml", ".yaml": "yaml", ".yml": "yaml",
         ".sh": "bash", ".csv": "csv", ".sql": "sql", ".js": "javascript", ".ts": "typescript", ".txt": "text"}


def add_arguments(parser):
    parser.add_argument("task", help="task ID, e.g. M2-T03")
    parser.add_argument("--json", action="store_true", help="print one JSON object (the packet is under `text`)")


def _find_task(repo, task_id: str):
    for doc in repo.docs(*PLAN_KINDS):
        for t in model.tasks(doc):
            if t.id == task_id:
                return t
    return None


def _ref(raw: str) -> str:
    """A `Read:` item without backticks or a trailing `(reason)`."""
    return re.sub(r"\s*\(.*\)\s*$", "", raw).strip().strip("`").strip()


def _looks_like_path(repo, ref: str) -> bool:
    """A repo path rather than an ID: has a folder, exists, or ends in a file extension."""
    suffix = ("." + ref.rsplit(".", 1)[1].lower()) if "." in ref else ""
    return "/" in ref or (repo.root / ref).exists() or suffix in LANGS or suffix in (".cfg", ".ini", ".lock")


def _fence(text: str) -> str:
    longest = max((len(m) for m in re.findall(r"`{3,}", text)), default=0)
    return "`" * max(3, longest + 1)


def _file_block(repo, rel: str) -> tuple[str, bool]:
    """`### <path>` and the file in a fence; a one-line note if it can't be read."""
    path = repo.root / rel
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return f"### {rel}\n(missing: not in the repo yet)\n", False
    fence = _fence(text)
    lang = LANGS.get(path.suffix.lower(), "")
    body = text if text.endswith("\n") or not text else text + "\n"
    return f"### {rel}\n{fence}{lang}\n{body}{fence}\n", True


def _layout_block(repo, pkg: str) -> str:
    """The package's real tree (as `dt layout`), since built pipelines point there instead of a planned layout."""
    if not pkg:
        return ""
    folder = code.source_folder(repo, pkg)
    root = repo.root / folder
    if not root.is_dir():
        return ""
    return f"## Layout (`dt layout {pkg}`)\n{folder}/\n" + "".join(tree_lines(code.source_tree(root)))


def run(args, repo) -> int:
    task = _find_task(repo, args.task)
    if task is None:
        print(f"dt context: task {args.task} not found in tasks/plan.md or tasks/queued/", file=sys.stderr)
        return 1

    blocks: list[str] = []
    reads: list[dict] = []
    problems: list[str] = []
    for raw in task.read:
        ref = _ref(raw)
        d = repo.lookup(ref, archive=False)
        if d is not None:
            if d.retired:
                problems.append(f"Read: {ref} is retired ({d.retired_note}) at {d.where}")
            reads.append({"ref": ref, "kind": "id", "where": d.where, "retired": d.retired})
            blocks.append(f"<!-- {d.where} -->\n{d.text}")
        elif _looks_like_path(repo, ref):
            block, exists = _file_block(repo, ref)
            reads.append({"ref": ref, "kind": "file", "exists": exists})
            blocks.append(block)
        else:
            problems.append(f"Read: {ref} is not defined in any doc")
    if problems:
        for p in problems:
            print(f"dt context: {task.id}: {p}", file=sys.stderr)
        return 1

    layout = _layout_block(repo, task.package)
    if layout:
        blocks.append(layout)
    files = [{"path": f, "exists": (repo.root / f).exists()} for f in task.files_likely]
    if files:
        blocks.append("## Files likely\n" + "".join(
            f"- {f['path']} ({'exists' if f['exists'] else 'new'})\n" for f in files))
    blocks.append(f"<!-- {task.doc.rel}:{task.start + 1} -->\n{task.text}")

    preamble = (f"# Context for {task.id}: package {task.package or '—'} · mode {task.mode or '—'}\n"
                "Read only what is below, plus CONSTRAINTS.md and the files you edit. "
                "Your task is the last section.\n")
    text = "\n".join([preamble] + blocks)
    lines = text.count("\n")
    if lines > BUDGET:
        print(f"dt context: {task.id} packet is {lines} lines (budget {BUDGET}); split the task or trim its Read:",
              file=sys.stderr)

    if args.json:
        print(json.dumps({"task": task.id, "package": task.package, "mode": task.mode, "lines": lines,
                          "read": reads, "files_likely": files, "text": text}, indent=2))
    else:
        print(text, end="")
    return 0
