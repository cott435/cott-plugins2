"""Probe folders against docs/probes.md: list each probe's state, `--stamp` its Hash (mechanical), or `--scan` its
evidence for secrets and personal data."""
from __future__ import annotations

import sys

from .. import edit, md, model
from .. import probes as pb
from .references import _set_hash


def add_arguments(parser):
    parser.add_argument("ids", nargs="*", help="only these probes (PB-NN); default: every entry (or folder, --scan)")
    parser.add_argument("--stamp", action="store_true",
                        help="write each entry's Hash (first 8 hex of the code files' sha256); never changes Status")
    parser.add_argument("--scan", action="store_true",
                        help="scan evidence/ for secret and personal-data patterns; prints file:line and the "
                             "pattern, never the text; exit 1 on a hit")


def run(args, repo) -> int:
    entries = model.all_probes(repo)
    unknown = [i for i in args.ids if i not in {e.id for e in entries}]
    if unknown:
        print(f"dt probes: not an entry in docs/probes.md: {', '.join(unknown)}", file=sys.stderr)
        return 1
    chosen = [e for e in entries if e.id in args.ids] if args.ids else entries
    if args.scan:
        return _scan(repo, chosen if args.ids else None)
    if repo.probes is None:
        print("dt probes: no docs/probes.md", file=sys.stderr)
        return 1
    return _stamp(repo, repo.probes, chosen) if args.stamp else _list(repo, chosen)


def _list(repo, entries) -> int:
    for e in entries:
        folder = pb.folder_of(repo, e)
        current = pb.code_hash(folder) if folder is not None else None
        code = "no Folder" if folder is None else "folder missing" if current is None else \
            "hash ok" if current == e.hash.lower() else "unstamped" if not e.hash else f"hash changed (now {current})"
        res = pb.read_results(repo, e)
        if res is None:
            results = "no results"
        elif not res.ok:
            results = f"results invalid: {res.problems[0][1]}"
        else:
            fresh = "for other code" if current and res.script_hash != current else "current"
            results = f"results {res.run_at} ({fresh}; {len(res.checks)}/{len(e.checks)} checks)"
        status = md.strip_md(e.status) or "no Status"
        print(f"{e.id}: {e.folder or '—'} · {status} · {code} · {results} · {', '.join(e.milestones) or '—'}")
    return 0


def _stamp(repo, doc, entries) -> int:
    lines = edit.read_lines(doc.path)
    stamped, problems = [], []
    for e in entries:
        folder = pb.folder_of(repo, e)
        current = pb.code_hash(folder) if folder is not None else None
        if current is None:
            problems.append(f"{e.id}: {'no Folder field' if folder is None else e.folder + '/ missing'} (not stamped)")
            continue
        if current == e.hash.lower():
            continue
        i = md.field_line(doc.lines, e.start + 1, e.end, "Hash")
        i = md.field_line(doc.lines, e.start + 1, e.end, "Folder") if i is None else i
        raw = lines[i]
        body = raw.rstrip("\r\n")
        lines[i] = _set_hash(body, current, after="Folder") + raw[len(body):]
        stamped.append(f"{e.id}: {current}")
    if stamped:
        edit.write_lines(doc.path, lines)
    for s in stamped + problems:
        print(s)
    print(f"probes: stamped {len(stamped)}" if stamped else "probes: nothing to stamp")
    return 1 if problems else 0


def _scan(repo, only) -> int:
    hits = pb.scan(repo, only)
    for h in hits:
        print(h)
    print(f"scan: {len(hits)} hit{'s' if len(hits) != 1 else ''}" if hits else "scan: clean")
    return 1 if hits else 0
