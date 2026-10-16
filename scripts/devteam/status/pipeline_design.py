"""`dt status --skill pipeline-design`: per-package mode, coverage, owners, drift, retired references and
misplaced pipelines."""
from __future__ import annotations

from pathlib import Path

from .. import md, model
from ..repo import Doc, Repo
from .common import Report, add_common, doc_state, in_revise, live_spec_ids
from .packages import drift, is_multi, known_packages, package_components, source_dir


def _under(path: Path, folder: Path) -> bool:
    try:
        path.relative_to(folder)
        return True
    except ValueError:
        return False


def misplaced(repo: Repo, pkg: str, pipelines: list[model.Pipeline], packages: list[str]) -> list[str]:
    """Pipelines whose Entry lies in another package's source folder (a Grow signal)."""
    own = source_dir(repo, pkg)
    out = []
    for p in pipelines:
        if not p.entry_file:
            continue
        entry = repo.root / p.entry_file
        if _under(entry, own):
            continue
        for other in packages:
            if other != pkg and _under(entry, source_dir(repo, other)):
                out.append(f"{p.id} ({pkg} → {other}: {p.entry_file})")
                break
    return out


def _owner_matches(owner: str, comp: str) -> bool:
    owner = owner.strip("`")
    return owner == comp or comp in owner.split(".")


def retired_refs(repo: Repo, docs: list[Doc]) -> list[str]:
    """`path:line ID` for every reference to a retired ID outside retired lines and code fences."""
    out = []
    for doc in docs:
        own = {x.line for x in md.retired_lines(doc.lines, doc.mask)}
        for i, line in enumerate(doc.lines):
            if doc.mask[i] or i in own:
                continue
            for rid in md.expand_refs(line):
                if repo.is_retired(rid):
                    out.append(f"{doc.rel}:{i + 1} {rid}")
    return out


def pipeline_design(repo: Repo, r: Report) -> None:
    arch = repo.architecture
    blocked = None
    if arch is None:
        blocked = "no docs/architecture.md (run architecture-design)"
    elif arch.status != "Approved":
        blocked = f"architecture is {doc_state(arch)}, not Approved"
    live, _ = live_spec_ids(repo)
    system = model.pipelines(arch) if arch else []
    root_rows = model.components(arch) if arch and is_multi(repo) else []
    modes: dict[str, str] = {}
    uncovered, unowned, drifts, moved, unknown = [], [], [], [], False
    packages = known_packages(repo)
    for pkg in packages:
        doc = repo.package_doc(pkg, "pipelines")
        if doc is None:
            modes[pkg] = "new"
            continue
        pls = model.pipelines(doc)
        covered = set()
        for p in pls + system:
            covered |= set(p.covers)
            for s in p.steps:
                covered |= set(s.covers)
        comps = package_components(repo, pkg)
        wanted = set()
        for c in comps + [c for c in root_rows if c.id == pkg]:
            wanted |= set(c.covers)
        pkg_uncovered = sorted((wanted & live) - covered)
        owners = [s.owner for p in pls + system for s in p.steps]
        pkg_unowned = [c.id for c in comps if not any(_owner_matches(o, c.id) for o in owners)]
        pkg_drift = drift(repo, pls)
        if pkg_drift is None:
            unknown, pkg_drift = True, []
        pkg_moved = misplaced(repo, pkg, pls, packages)
        uncovered += pkg_uncovered
        unowned += [f"{pkg}.{c}" if is_multi(repo) else c for c in pkg_unowned]
        drifts += pkg_drift
        moved += pkg_moved
        if pkg_moved:
            modes[pkg] = "grow"
        elif in_revise(repo, doc):
            modes[pkg] = "revise"
        elif pkg_drift:
            modes[pkg] = "sync"
        else:
            modes[pkg] = "extend" if pkg_uncovered or pkg_unowned else "current"
    if blocked:
        r.mode("blocked", blocked)
    else:
        present = set(modes.values())
        r.mode(next((m for m in ("new", "grow", "revise", "extend", "sync") if m in present),
                    "current" if modes else "new"))
    add_common(repo, r)
    r.add("packages", modes)
    r.add("uncovered_ids", sorted(set(uncovered)))
    r.add("components_unowned", unowned)
    r.add("drift", "unknown" if unknown and not drifts else drifts)
    r.add("retired_refs", retired_refs(repo, sorted(repo.docs("pipelines"), key=lambda d: d.rel)))
    r.add("misplaced", moved)
