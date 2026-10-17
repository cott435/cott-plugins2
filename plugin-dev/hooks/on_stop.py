#!/usr/bin/env python3
"""Stop: run the whole check for every plugin this session edited.

`on_edit.py` records the plugins. A failure blocks the stop (exit 2) with the failing
lines, once per distinct set of failures: the same failures are not reported twice, so a
session can stop on something the user chose to leave. Exits 0 at once when the session
edited no plugin; a crash or an unreadable event exits 0 with the reason on stderr.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    import check
    from on_edit import state_file
    event = json.load(sys.stdin)
    store = state_file(event.get("session_id"))
    if event.get("stop_hook_active") or not store.exists():
        return 0
    state = json.loads(store.read_text())
    failures = []
    for root in map(Path, state.get("roots", [])):
        if (root / ".claude-plugin" / "plugin.json").is_file():
            ok, text = check.report(root, quiet=True)
            if not ok:
                failures.append(text)
    digest = hashlib.sha1("\n".join(failures).encode()).hexdigest() if failures else ""
    if digest == state.get("reported", ""):
        return 0
    state["reported"] = digest
    store.write_text(json.dumps(state))
    if not failures:
        return 0
    print("plugin-dev: the check fails for a plugin this session edited. Fix the files, or "
          "tell the user what you are leaving and why.\n" + "\n".join(failures), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:      # a gate that crashes must not hold the session
        print(f"plugin-dev stop check: {type(e).__name__}: {e}; allowing", file=sys.stderr)
        sys.exit(0)
