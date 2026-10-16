#!/usr/bin/env python3
"""dt: dev-team2's doc tool. One parser for every planning doc; see scripts/README.md for the commands.

Run from the project root, or pass --root. Stdlib only.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from devteam.repo import Repo  # noqa: E402

# command name → module in devteam.commands. Each module defines add_arguments(parser) and run(args, repo) -> int.
COMMANDS = {
    "status": "status",
    "next-id": "next_id",
    "section": "section",
    "context": "context",
    "layout": "layout",
    "lint": "lint",
    "roadmap": "roadmap",
    "guard": "guard",
    "prebuild-clear": "prebuild_clear",
    "archive": "archive",
    "finding": "finding",
    "tick": "tick",
    "base": "base",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dt", description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    sub = parser.add_subparsers(dest="command", required=True)
    modules = {}
    for name, mod in COMMANDS.items():
        module = importlib.import_module(f"devteam.commands.{mod}")
        p = sub.add_parser(name, help=(module.__doc__ or "").strip().splitlines()[0] if module.__doc__ else None)
        module.add_arguments(p)
        modules[name] = module
    args = parser.parse_args(argv)
    if args.command == "guard":
        # Hooks must never fail closed on a parse error; guard reads hook JSON and decides itself.
        return modules["guard"].run(args, None)
    repo = Repo(args.root)
    return modules[args.command].run(args, repo)


if __name__ == "__main__":
    sys.exit(main())
