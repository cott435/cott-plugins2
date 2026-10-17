"""Reference files against docs/references.md: list each entry's state, or `--stamp` its Hash (mechanical)."""
from __future__ import annotations

import re
import sys

from .. import edit, md, model
from .. import references as refs


def add_arguments(parser):
    parser.add_argument("ids", nargs="*", help="only these entries (RF-NN); default: every entry")
    parser.add_argument("--stamp", action="store_true",
                        help="write each entry's Hash (first 8 hex of the file's sha256); never changes Status")


def _set_hash(line: str, value: str) -> str:
    """Set `**Hash:** <value>` on a field line, inserting it after the File field when absent."""
    if "**Hash:**" in line:
        return re.sub(r"(\*\*Hash:\*\*\s*)[^·]*?(\s*·|\s*$)", lambda m: f"{m.group(1)}{value}{m.group(2)}", line,
                      count=1)
    new = re.sub(r"(\*\*File:\*\*[^·]*?)(\s*·|\s*$)", lambda m: f"{m.group(1)} · **Hash:** {value}{m.group(2)}",
                 line, count=1)
    return new if new != line else f"{line} · **Hash:** {value}"


def run(args, repo) -> int:
    doc = repo.references
    if doc is None:
        print("dt references: no docs/references.md", file=sys.stderr)
        return 1
    entries = model.all_references(repo)
    unknown = [i for i in args.ids if i not in {e.id for e in entries}]
    if unknown:
        print(f"dt references: not an entry in docs/references.md: {', '.join(unknown)}", file=sys.stderr)
        return 1
    if args.ids:
        entries = [e for e in entries if e.id in args.ids]
    return _stamp(repo, doc, entries) if args.stamp else _list(repo, entries, bool(args.ids))


def _list(repo, entries, filtered: bool) -> int:
    for e in entries:
        current = refs.file_hash(repo.root / e.file) if e.file else None
        state = "no File" if not e.file else "missing" if current is None else \
            "ok" if current == e.hash.lower() else "unstamped" if not e.hash else f"changed (now {current})"
        print(f"{e.id}: {e.file or '—'} · {state} · {', '.join(e.milestones) or '—'}")
    if not filtered:
        print(f"unindexed: {', '.join(refs.state(repo).unindexed) or 'none'}")
    return 0


def _stamp(repo, doc, entries) -> int:
    lines = edit.read_lines(doc.path)
    stamped, problems = [], []
    for e in entries:
        current = refs.file_hash(repo.root / e.file) if e.file else None
        if current is None:
            problems.append(f"{e.id}: {'no File field' if not e.file else e.file + ' missing'} (not stamped)")
            continue
        if current == e.hash.lower():
            continue
        i = md.field_line(doc.lines, e.start + 1, e.end, "Hash")
        i = md.field_line(doc.lines, e.start + 1, e.end, "File") if i is None else i
        raw = lines[i]
        body = raw.rstrip("\r\n")
        lines[i] = _set_hash(body, current) + raw[len(body):]
        stamped.append(f"{e.id}: {current}")
    if stamped:
        edit.write_lines(doc.path, lines)
    for s in stamped + problems:
        print(s)
    print(f"references: stamped {len(stamped)}" if stamped else "references: nothing to stamp")
    return 1 if problems else 0
