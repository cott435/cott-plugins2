"""`dt status --skill api-probe` (design/probes.md §3.4): probes cited with no entry, results waiting to be
recorded, results for other code, checks still to run, and evidence the redaction scan rejects."""
from __future__ import annotations

from .. import probes as pb
from ..repo import Repo
from .common import Report, add_common


def api_probe(repo: Repo, r: Report) -> None:
    s = pb.state(repo)
    if s.unwritten:
        mode = "new"
    elif s.stale:
        mode = "revise"
    elif s.results:
        mode = "record"
    elif s.open:
        mode = "waiting"
    else:
        mode = "current"
    r.mode(mode)
    add_common(repo, r)
    r.add("index", "missing" if repo.probes is None else repo.probes.status or "ok")
    r.add("probes_unwritten", s.unwritten)
    r.add("probes_open", s.open)
    r.add("probes_results", s.results)
    r.add("probes_stale", s.stale)
    r.add("evidence_leaks", s.leaks)
    r.add("next_id", repo.next_id("PB"))
