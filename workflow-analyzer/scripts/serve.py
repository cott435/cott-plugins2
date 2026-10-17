#!/usr/bin/env python3
"""Serve built run pages on 127.0.0.1 and print the URL of one of them.

One server per root directory, reused across calls: its port and pid are kept in
`<root>/.server.json`, and a call whose recorded server still answers just prints the URL.
Otherwise a detached `python3 -m http.server` is started on a free port, bound to 127.0.0.1
only, serving only that root.

The root is $RUN_FLOW_HOME (`~/.claude/run-flow/`) when PAGE is under it, so pages that link
across sessions (views, comparisons) resolve; otherwise --root, or PAGE's own directory.

Usage: serve.py PAGE [--root DIR]      prints  http://127.0.0.1:<port>/<path>
       serve.py --stop [--root DIR]    stops the server for that root
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

RUNS = Path(os.environ.get("RUN_FLOW_HOME") or Path.home() / ".claude" / "run-flow")


def answers(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def ensure(root: Path) -> int:
    state = root / ".server.json"
    try:
        rec = json.loads(state.read_text())
        if answers(rec["port"]):
            return rec["port"]
    except (OSError, ValueError, KeyError):
        pass
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
                             "--directory", str(root)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(50):
        if answers(port):
            break
        time.sleep(0.1)
    state.write_text(json.dumps({"port": port, "pid": proc.pid, "root": str(root)}))
    return port


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", nargs="?")
    ap.add_argument("--root")
    ap.add_argument("--stop", action="store_true")
    a = ap.parse_args()
    if a.stop:
        root = Path(a.root or RUNS).expanduser().resolve()
        try:
            rec = json.loads((root / ".server.json").read_text())
            os.kill(rec["pid"], signal.SIGTERM)
            (root / ".server.json").unlink()
            print(f"stopped the server on port {rec['port']}")
        except (OSError, ValueError, KeyError):
            print("no server recorded for", root)
        return 0
    if not a.page:
        ap.error("give a page to serve")
    page = Path(a.page).expanduser().resolve()
    if not page.exists():
        sys.exit(f"no such page: {page}")
    runs = RUNS.expanduser().resolve()
    if a.root:
        root = Path(a.root).expanduser().resolve()
    elif page.is_relative_to(runs):
        root = runs
    else:
        root = page.parent if page.is_file() else page
    if not page.is_relative_to(root):
        sys.exit(f"{page} is not under {root}")
    root.mkdir(parents=True, exist_ok=True)
    port = ensure(root)
    print(f"http://127.0.0.1:{port}/{page.relative_to(root).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
