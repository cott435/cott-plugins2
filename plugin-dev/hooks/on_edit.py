#!/usr/bin/env python3
"""PostToolUse on Write and Edit: hold an edited definition to its size limit.

When the edited file is inside a plugin, records that plugin for `on_stop.py` and checks
the one file against its word limit. Over the limit exits 2, which hands the count and the
limit back to the model while the edit is still in front of it. Anywhere else exits 0 at
once; a crash or an unreadable event exits 0 with the reason on stderr.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def state_file(session_id):
    """Where one session's touched plugins and last reported failures are kept."""
    d = Path(tempfile.gettempdir()) / "plugin-dev"
    d.mkdir(exist_ok=True)
    return d / f"{session_id or 'session'}.json"


def main():
    import check
    event = json.load(sys.stdin)
    path = (event.get("tool_input") or {}).get("file_path")
    root = check.plugin_root(Path(path).parent) if path else None
    if root is None:
        return 0
    store = state_file(event.get("session_id"))
    state = json.loads(store.read_text()) if store.exists() else {}
    state["roots"] = sorted(set(state.get("roots", [])) | {str(root)})
    store.write_text(json.dumps(state))
    problems = check.size_problems(root, [Path(path)])
    if problems:
        print("plugin-dev: " + "\n".join(problems), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:      # a hook that crashes must not hold the session
        print(f"plugin-dev edit check: {type(e).__name__}: {e}; allowing", file=sys.stderr)
        sys.exit(0)
