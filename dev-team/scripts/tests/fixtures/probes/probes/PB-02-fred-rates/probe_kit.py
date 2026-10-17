"""Shared probe helpers (a test stand-in for api-probe's templates/probe_kit.py): the code hash only."""
import hashlib
import os


def code_hash(folder):
    """First 8 hex of sha256 over the probe's code files (not evidence/, out/, dot-files or Markdown)."""
    files = []
    for d, subs, names in os.walk(folder):
        rel_d = os.path.relpath(d, folder).replace(os.sep, "/")
        subs[:] = sorted(s for s in subs if not s.startswith(".") and s != "__pycache__"
                         and not (rel_d == "." and s in ("evidence", "out")))
        for n in names:
            if n.startswith(".") or n.endswith((".pyc", ".md")):
                continue
            files.append(os.path.normpath(os.path.join(rel_d, n)).replace(os.sep, "/"))
    h = hashlib.sha256()
    for rel in sorted(files):
        with open(os.path.join(folder, rel), "rb") as f:
            h.update(rel.encode() + b"\0" + f.read() + b"\0")
    return h.hexdigest()[:8]
