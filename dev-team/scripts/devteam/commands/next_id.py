"""Print the next free ID for a prefix (PL, TC, AD, CR, S, M, M2-T, M2-R, or a spec prefix), retired IDs counted."""
from __future__ import annotations

import re


def add_arguments(parser):
    parser.add_argument("prefix", nargs="+", help="e.g. PL TC AD S M M2-T STAT")


def run(args, repo) -> int:
    for prefix in args.prefix:
        prefix = prefix.rstrip("-")
        if not re.fullmatch(r"[A-Z][A-Z0-9]*|M\d+-[TR]", prefix):
            print(f"dt next-id: bad prefix {prefix!r}")
            return 2
        print(repo.next_id(prefix))
    return 0
