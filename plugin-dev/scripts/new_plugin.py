#!/usr/bin/env python3
"""Scaffold a new plugin beside the others in a marketplace repo and register it.

Creates <marketplace>/<name>/ from this plugin's templates/ with <name>, <description> and
<date> filled in, writes its .claude-plugin/plugin.json at 0.1.0, and adds its row to the
root .claude-plugin/marketplace.json. PURPOSE.md is written from --purpose, the file
holding the text the user approved. Refuses a name that is not kebab-case or already taken.

Usage:  python3 new_plugin.py <name> --description "<one line>" --purpose <file>
        [--marketplace <repo root>]      default: the nearest marketplace at or above the cwd
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def marketplace_root(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if (d / ".claude-plugin" / "marketplace.json").is_file():
            return d
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--description", required=True)
    ap.add_argument("--purpose", required=True, type=Path)
    ap.add_argument("--marketplace", type=Path)
    args = ap.parse_args()

    repo = (args.marketplace or marketplace_root(Path.cwd()) or Path()).resolve()
    catalog = repo / ".claude-plugin" / "marketplace.json"
    if not catalog.is_file():
        sys.exit("no .claude-plugin/marketplace.json at or above this directory; pass --marketplace")
    if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", args.name):
        sys.exit(f"{args.name!r} is not kebab-case")
    root = repo / args.name
    market = json.loads(catalog.read_text())
    if root.exists() or any(r.get("name") == args.name for r in market.get("plugins", [])):
        sys.exit(f"{args.name} already exists in {repo.name}")
    purpose = args.purpose.read_text()

    fill = {"<name>": args.name, "<description>": args.description,
            "<date>": datetime.date.today().isoformat()}
    (root / ".claude-plugin").mkdir(parents=True)
    (root / "skills").mkdir()
    for src in sorted(p for p in TEMPLATES.rglob("*") if p.is_file()):
        text = src.read_text()
        for k, v in fill.items():
            text = text.replace(k, v)
        dest = root / src.relative_to(TEMPLATES)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.with_name(dest.name.replace("gitignore", ".gitignore")).write_text(text)
    (root / "PURPOSE.md").write_text(purpose.rstrip() + "\n")
    manifest = {"name": args.name, "description": args.description, "version": "0.1.0",
                "author": market.get("owner", {})}
    (root / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n")
    market.setdefault("plugins", []).append({"name": args.name, "source": f"./{args.name}",
                                             "description": args.description, "version": "0.1.0"})
    catalog.write_text(json.dumps(market, indent=2) + "\n")
    print(f"created {root}\nregistered in {catalog}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
