"""`dt status --skill architecture-design`: arch-status.py's report on the new doc layout, plus the
contract.md migration (contracts_missing, legacy_layout), Grow triggers and contract freshness."""
from __future__ import annotations

import os
from pathlib import Path

from .. import probes as pb
from .. import requests as rq
from .. import routes
from .. import specdocs
from ..repo import Repo
from .common import Report, add_common, available_skills, doc_state, fmt, live_spec_ids, next_decision
from .packages import WALK_IGNORE, grow_triggers, known_packages, shape_kept, stale_contracts

MANIFESTS = {"pyproject.toml", "setup.py", "package.json", "Cargo.toml", "go.mod"}
KEYS = ("uncovered", "changed_since", "spec_rows_pending", "stale", "package_docs", "packages_found", "skills",
        "broken_fences", "contracts_missing", "legacy_layout", "grow_triggers", "grow_held", "stale_contracts", "probes_answered",
        "probes_failed", "routed_changes")


def packages_found(root: Path) -> list[str]:
    """Folders (≤ 4 deep) holding a package manifest, as arch-status.py found them."""
    found = []
    base = str(root)
    for d, subdirs, files in os.walk(base):
        subdirs[:] = [s for s in subdirs if s not in WALK_IGNORE and not s.startswith(".")]
        if d.count(os.sep) - base.count(os.sep) > 4:
            subdirs[:] = []
        if MANIFESTS & set(files):
            found.append(os.path.relpath(d, base))
    return sorted(found)


def architecture_design(repo: Repo, r: Report) -> None:
    spec, arch = repo.spec, repo.architecture
    if spec is None:
        r.mode("blocked", "no docs/spec.md (run spec-writing first)")
        add_common(repo, r)
        for k in KEYS:
            r.add(k, [])
        return

    pkg_docs = sorted(repo.docs("package-architecture"), key=lambda d: d.rel)
    arch_docs = ([arch] if arch else []) + pkg_docs
    live, removed = live_spec_ids(repo)
    referenced: set[str] = set()
    for d in arch_docs:
        referenced |= specdocs.refs(d.text)
    referenced = {i for i in referenced if not i.startswith("AD-")}
    updated = arch.last_updated if arch else None
    uncovered = sorted(live - referenced)
    pending = specdocs.pending_rows(specdocs.changelog(spec.text), specdocs.changelog(arch.text if arch else None),
                                   updated)
    changed = {i for row in pending for i, m in row.ids.items() if m == "changed"}
    changed_since = sorted(changed & live & referenced)
    prefixes = {i.split("-")[0] for i in live | removed}
    stale = sorted(i for i in referenced if i.split("-")[0] in prefixes and i not in live)
    if arch is None:
        contracts_missing = []
    else:
        contracts_missing = [p for p in known_packages(repo) if not repo.package_doc(p, "contract")] or \
            ([] if repo.docs("contract") else ["(no package id yet)"])
    legacy = sorted(d.rel for d in pkg_docs if d.rel.startswith("docs/architecture/"))

    probe_state = pb.state(repo)
    routed = routes.open_for(repo, "architecture-design")
    if arch is None:
        r.mode("new")
    elif probe_state.answered or routed or rq.due(repo, "architecture"):
        r.mode("revise")      # a probe's results, a change routed here or the user's words, before anything else
    else:
        r.mode("extend" if uncovered or changed_since or contracts_missing or legacy else "current")
    add_common(repo, r)
    r.add("spec", {"path": spec.rel, "status": spec.status, "live_requirements": len(live)},
          f"{doc_state(spec)}, {len(live)} live requirements")
    r.add("architecture", {"path": "docs/architecture.md", "exists": arch is not None,
                           "status": arch.status if arch else None,
                           "shape": arch.header.get("Shape") if arch else None, "last_updated": updated},
          doc_state(arch))
    r.add("next_decision", next_decision(repo))
    r.add("uncovered", uncovered)
    r.add("changed_since", changed_since)
    r.add("spec_rows_pending", [row.label() for row in pending], fmt([row.label() for row in pending]))
    r.add("stale", stale)
    r.add("package_docs", [d.rel for d in pkg_docs])
    r.add("packages_found", packages_found(repo.root))
    r.add("skills", available_skills(repo))
    fence_docs = arch_docs + sorted(repo.docs("contract"), key=lambda d: d.rel)
    r.add("broken_fences", [f"{d.rel}:{n}" for d in fence_docs for n in specdocs.broken_fences(d.lines)])
    r.add("contracts_missing", contracts_missing)
    r.add("legacy_layout", legacy)
    r.add("grow_triggers", grow_triggers(repo))
    r.add("grow_held", shape_kept(repo))
    r.add("stale_contracts", stale_contracts(repo))
    r.add("probes_answered", probe_state.answered)
    r.add("probes_failed", probe_state.failed)
    r.add("routed_changes", routed)
