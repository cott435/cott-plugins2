"""`dt status --skill pipeline-design`: per-package mode, coverage, owners, drift, retired references and
misplaced pipelines."""
from __future__ import annotations

from pathlib import Path

from .. import md, model, routes
from ..commands import roadmap as roadmap_cmd
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


def _owns(step: model.Step, home: str | None, pkg: str, comp: str) -> bool:
    """A step's Owner names the package's component: `comp` (or a dotted path through it) on a step of the
    package's own pipelines or a system pipeline; `pkg.comp` on another package's (lab's PL-01 runs
    `worlds.snake`)."""
    if home in (pkg, None) and _owner_matches(step.owner, comp):
        return True
    parts = step.owner.strip("`").split(".")
    return any(parts[i:i + 2] == [pkg, comp] for i in range(len(parts) - 1))


def citing_decisions(repo: Repo, id_: str, packages: list[str]) -> tuple[list[str], list[str]]:
    """(the live decisions that cite the ID, the known packages they are scoped to): the decision that meets a
    constraint names the step that applies it."""
    ads, pkgs = [], []
    for doc in repo.docs("architecture", "package-architecture"):
        for d in doc.definitions():
            if not d.id.startswith("AD-") or d.how != "heading" or d.retired or id_ not in md.expand_refs(d.text):
                continue
            ads.append(d.id)
            scope = md.fields_in(doc.lines, d.start + 1, d.end).get("Scope", "")
            if not is_multi(repo):
                pkgs += packages[:1]          # a single package's decisions are scoped to its components
                continue
            named = [doc.package] if doc.package else [md.strip_md(s) for s in md.split_list(scope)]
            pkgs += [s for s in named if s in packages]
    return sorted(set(ads), key=lambda i: int(i.split("-")[1])), sorted(set(pkgs))


def stage_ids_unplaced(repo: Repo, live: set[str], covered: set[str]) -> dict[str, list[str]]:
    """ID → the uncut, specced stages whose Source adds it while no pipeline (any status) carries it: a whole-run
    `QR-` constraint on no component lands here, and keeps the stage below Designed (`roadmap.ids_off_approved`)."""
    out: dict[str, list[str]] = {}
    doc = repo.roadmap
    for st in model.stages(doc) if doc else []:
        if model.stage_milestones(doc, st.id) or not roadmap_cmd.is_specced(repo, st):
            continue
        for i in (roadmap_cmd.source_ids(repo, st) & live) - covered:
            out.setdefault(i, []).append(st.id)
    return dict(sorted(out.items(), key=lambda kv: (kv[0].split("-")[0], int(kv[0].split("-")[1]))))


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
    root_rows = model.components(arch) if arch and is_multi(repo) else []
    modes: dict[str, str] = {}
    uncovered, unowned, drifts, moved, unknown = [], [], [], [], False
    packages = known_packages(repo)
    # Coverage and ownership are the whole design's: a package with no pipeline of its own (worlds) may have
    # every component run as a step of another package's pipeline.
    every = model.all_pipelines(repo)
    covered = set().union(*(set(p.covers).union(*(s.covers for s in p.steps)) for p in every))
    steps = [(p.package if not p.is_system else None, s) for p in every for s in p.steps]
    for pkg in packages:
        doc = repo.package_doc(pkg, "pipelines")
        if doc is None:
            modes[pkg] = "new"
            continue
        pls = model.pipelines(doc)
        comps = package_components(repo, pkg)
        wanted = set()
        for c in comps + [c for c in root_rows if c.id == pkg]:
            wanted |= set(c.covers)
        pkg_uncovered = sorted((wanted & live) - covered)
        pkg_unowned = [c.id for c in comps if not any(_owns(s, home, pkg, c.id) for home, s in steps)]
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
    unplaced = stage_ids_unplaced(repo, live, covered) if not blocked else {}
    placed = []
    for i, sts in unplaced.items():
        ads, homes = citing_decisions(repo, i, packages)
        for pkg in homes:
            if modes.get(pkg) == "current":
                modes[pkg] = "extend"
        meets = f"; {', '.join(ads)}" + (f" → {', '.join(homes)}" if homes else "") if ads else ""
        placed.append(f"{i} ({', '.join(sts)}{meets})")
    uncovered += list(unplaced)
    routed = routes.open_for(repo, "pipeline-design")
    if blocked:
        r.mode("blocked", blocked)
    else:
        present = set(modes.values()) | ({"revise"} if routed else set()) | ({"extend"} if unplaced else set())
        r.mode(next((m for m in ("new", "grow", "revise", "extend", "sync") if m in present),
                    "current" if modes else "new"))
    add_common(repo, r)
    r.add("packages", modes)
    r.add("uncovered_ids", sorted(set(uncovered)))
    r.add("stage_ids_unplaced", placed)
    r.add("components_unowned", unowned)
    r.add("drift", "unknown" if unknown and not drifts else drifts)
    r.add("retired_refs", retired_refs(repo, sorted(repo.docs("pipelines"), key=lambda d: d.rel)))
    r.add("misplaced", moved)
    r.add("routed_changes", routed)
