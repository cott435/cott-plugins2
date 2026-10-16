"""Print the sections that define the given IDs, searching every doc (the archive last)."""
from __future__ import annotations


def add_arguments(parser):
    parser.add_argument("ids", nargs="+", help="IDs such as PL-02 TC-06 STAT-02 AD-07 M2-T03 stats.estimate_cov")
    parser.add_argument("--no-path", action="store_true", help="omit the `<!-- path:line -->` marker before each")


def run(args, repo) -> int:
    missing = []
    out = []
    for id_ in args.ids:
        d = repo.lookup(id_)
        if d is None:
            missing.append(id_)
            continue
        marker = "" if args.no_path else f"<!-- {d.where}{' (retired)' if d.retired else ''} -->\n"
        out.append(marker + d.text)
    print("\n".join(out), end="")
    for id_ in missing:
        print(f"dt section: {id_} not found", file=__import__("sys").stderr)
    return 1 if missing else 0
