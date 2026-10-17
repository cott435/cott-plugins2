#!/usr/bin/env python3
"""SessionStart: print the protocol and the purpose of the plugin being worked on.

This is what a root CLAUDE.md used to carry. Printed from a hook, it reaches a session
opened in a plugin's own directory as well as one opened at the marketplace root, and
there is one copy of it: `protocol.md`, beside this plugin's manifest.

Inside a plugin (a `.claude-plugin/plugin.json` at or above the cwd): the protocol, then
that plugin's PURPOSE.md. At a marketplace root (a `.claude-plugin/marketplace.json` in the
cwd): the protocol, then every listed plugin's PURPOSE.md. Anywhere else it prints nothing.
A crash or an unreadable event exits 0 with the reason on stderr.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))


def purpose(root):
    path = root / "PURPOSE.md"
    if path.is_file():
        return f"## Purpose of `{root.name}` ({path})\n\n{path.read_text().strip()}"
    return (f"## `{root.name}` has no PURPOSE.md\n\nBefore changing it, agree its goal with "
            f"the user and write {path}.")


def main():
    import check
    cwd = Path(json.load(sys.stdin).get("cwd") or ".").resolve()
    root = check.plugin_root(cwd)
    market = cwd / ".claude-plugin" / "marketplace.json"
    if root:
        roots = [root]
    elif market.is_file():
        rows = json.loads(market.read_text()).get("plugins", [])
        roots = [r for r in (cwd / str(row.get("source", "")) for row in rows)
                 if (r / ".claude-plugin" / "plugin.json").is_file()]
    else:
        return 0
    limits = ", ".join(f"{kind} {n}" for kind, n in check.LIMITS.items())
    text = (HERE.parent / "protocol.md").read_text()
    print(text.replace("{limits}", limits).replace("{description}", str(check.DESCRIPTION_CHARS)))
    print(f"The check: python3 {HERE.parent / 'scripts' / 'check.py'} {{plugin dir}}\n")
    print("\n\n".join(purpose(r) for r in roots))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:      # a hook that crashes must not hold the session
        print(f"plugin-dev session start: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(0)
