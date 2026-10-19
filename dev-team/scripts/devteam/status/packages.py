"""Packages as `dt status` sees them: ids, components, source folders, Grow triggers, contract freshness
and pipeline drift."""
from __future__ import annotations

import datetime
import os
import re
from collections import Counter
from pathlib import Path

from .. import git, md, model
from .. import requests as rq
from ..repo import Doc, Repo

GROW_PIPELINES, GROW_MODULES, GROW_DOC_LINES = 3, 12, 2000
# A request keeping one package: "one package", "a single package", "no split" (not "one package per component").
KEEP_ONE = re.compile(r"\b(?:one|single)\s+package\b(?!\s+(?:per|for|each)\b)|\b(?:no|not|don'?t|never)\s+split\b",
                      re.IGNORECASE)
# A decision declining the split: "keeps one package", "no split" (a decision only naming the shape doesn't).
SPLIT_DECLINED = re.compile(r"\b(?:no|not|don'?t|never|without)\s+(?:a\s+)?split\b|\b(?:keeps?|kept|keeping|stays?|"
                            r"remains?)\s+(?:as\s+)?(?:one|a single|single)\s+package\b", re.IGNORECASE)
WALK_IGNORE = {"node_modules", ".venv", "venv", ".git", "dist", "build", "__pycache__", ".tox"}


def is_multi(repo: Repo) -> bool:
    arch = repo.architecture
    return bool(arch and "multi" in arch.header.get("Shape", "").lower())


def known_packages(repo: Repo) -> list[str]:
    """Package ids from docs/packages/, legacy docs/architecture/<pkg>.md, the roadmap's Packages column and a
    multi-package architecture's package table. A single package none of those names yet gets the id
    `inferred_package` finds."""
    names = set(repo.packages())
    names |= {d.package for d in repo.docs("package-architecture") if d.package}
    if repo.roadmap:
        for ms in model.milestones(repo.roadmap):
            names |= set(ms.packages)
    if is_multi(repo):
        names |= {c.id for c in model.components(repo.architecture)}
    elif not names:
        inferred = inferred_package(repo)
        names = {inferred} if inferred else set()
    return sorted(n for n in names if n)


def inferred_package(repo: Repo) -> str | None:
    """A single package's likely id: the `src/<pkg>/` the architecture's Project layout names most, else
    pyproject.toml's `[project] name`, else the only `src/<pkg>/__init__.py`."""
    arch = repo.architecture
    # Raw text, not the heading index: a broken fence earlier in the doc can hide the heading from the parser.
    layout = re.search(r"^##\s+Project layout[^\n]*\n(.*?)(?=^## |\Z)", arch.text, re.M | re.S) if arch else None
    if layout:
        found = Counter(re.findall(r"\bsrc/([A-Za-z_][\w-]*)/", layout.group(1)))
        if found:
            return found.most_common(1)[0][0]
    pyproject = repo.root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^\[project\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S)
        name = re.search(r"""^name\s*=\s*["']([^"']+)["']""", m.group(1), re.M) if m else None
        if name:
            return name.group(1).strip()
    src = repo.root / "src"
    if src.is_dir():
        pkgs = sorted(p.name for p in src.iterdir() if (p / "__init__.py").is_file())
        if len(pkgs) == 1:
            return pkgs[0]
    return None


def package_arch(repo: Repo, pkg: str) -> Doc | None:
    return repo.doc(f"docs/packages/{pkg}/architecture.md") or repo.doc(f"docs/architecture/{pkg}.md")


def package_pipelines(repo: Repo, pkg: str) -> list[model.Pipeline]:
    doc = repo.package_doc(pkg, "pipelines")
    return model.pipelines(doc) if doc else []


def package_components(repo: Repo, pkg: str) -> list[model.Component]:
    """A package's components: its own architecture doc's table, else (single package) the root's."""
    doc = package_arch(repo, pkg)
    if doc:
        return model.components(doc)
    if repo.architecture and not is_multi(repo):
        return model.components(repo.architecture)
    return []


def source_dir(repo: Repo, pkg: str) -> Path:
    """The package's source folder: from its pipelines' Entry paths (up to the folder named after the
    package), else src/<pkg>/."""
    for p in package_pipelines(repo, pkg):
        parts = Path(p.entry_file).parts
        if pkg in parts[:-1]:
            return repo.root.joinpath(*parts[:parts.index(pkg) + 1])
    return repo.root / "src" / pkg


def py_files(base: Path) -> list[Path]:
    if not base.is_dir():
        return []
    out = []
    for d, subdirs, files in os.walk(base):
        subdirs[:] = [s for s in subdirs if s not in WALK_IGNORE]
        out.extend(Path(d) / f for f in files if f.endswith(".py"))
    return out


def shape_kept(repo: Repo) -> list[str]:
    """What records the user's choice of one package, while the architecture is single-package: a request in force
    whose words keep it (`UR-34 "Keep it as one package, no split."`), or an Accepted decision whose text declines
    the split (`AD-15 "Grow declined: rllab stays one package"`). The Grow triggers are held while any does."""
    arch = repo.architecture
    if arch is None or is_multi(repo):
        return []
    out = [f'{r.id} "{r.words}"' for r in rq.all_requests(repo)
           if r.state not in ("changed", "superseded") and KEEP_ONE.search(r.words)]
    for d in arch.definitions():
        status = md.strip_md(md.fields_in(arch.lines, d.start + 1, d.end).get("Status", ""))
        if (d.id.startswith("AD-") and d.how == "heading" and not d.retired and status.startswith("Accepted")
                and SPLIT_DECLINED.search(d.text)):
            out.append(f'{d.id} "{md.strip_md(d.title)}"')
    return out


def grow_triggers(repo: Repo) -> list[str]:
    """The measurable Grow triggers per package; none while `shape_kept` holds the user's one package."""
    out = []
    if shape_kept(repo):
        return out
    for pkg in known_packages(repo):
        n_pl = len(package_pipelines(repo, pkg))
        if n_pl > GROW_PIPELINES:
            out.append(f"{pkg}: {n_pl} pipelines > {GROW_PIPELINES}")
        n_mod = len([f for f in py_files(source_dir(repo, pkg)) if f.name != "__init__.py"])
        if n_mod > GROW_MODULES:
            out.append(f"{pkg}: {n_mod} modules > {GROW_MODULES}")
        docs = [d for d in repo.docs() if d.package == pkg]
        if not is_multi(repo) and repo.architecture:
            docs.append(repo.architecture)     # a single package's architecture is the root doc
        n_lines = sum(len(d.lines) for d in docs)
        if n_lines > GROW_DOC_LINES:
            out.append(f"{pkg}: docs {n_lines} lines > {GROW_DOC_LINES}")
    return out


def contract_modules(repo: Repo, pkg: str) -> list[str]:
    """The files that make up a package's contract: each component's `__init__.py` (single package), else
    `src/**/<pkg>/__init__.py`. Repo-relative."""
    inits = [f for f in py_files(repo.root / "src") if f.name == "__init__.py"]
    names = [c.id for c in package_components(repo, pkg)] if not is_multi(repo) else []
    out = [f for f in inits if f.parent.name in names and pkg in f.parts]
    if not out:
        out = [f for f in inits if f.parent.name == pkg]
    return sorted(str(f.relative_to(repo.root)) for f in out)


def stale_contracts(repo: Repo) -> list[str]:
    """Packages whose contract code was committed after their contract.md."""
    if not git.is_repo(repo.root):
        return []
    out = []
    for pkg in known_packages(repo):
        doc = repo.package_doc(pkg, "contract")
        modules = contract_modules(repo, pkg)
        if not doc or not modules:
            continue
        doc_t = git.last_commit_time(repo.root, doc.rel)
        code_t = git.last_commit_time(repo.root, *modules)
        if doc_t and code_t and code_t > doc_t:
            day = datetime.date.fromtimestamp
            out.append(f"{pkg} (contract.md {day(doc_t)}, code {day(code_t)})")
    return out


def drift(repo: Repo, pipelines: list[model.Pipeline]) -> list[str] | None:
    """`dt layout`'s drift line per drifting pipeline, or None when drift can't be computed yet."""
    from .. import code
    out = []
    for p in pipelines:
        try:
            res = code.pipeline_drift(repo, p)
        except NotImplementedError:
            return None
        except Exception as e:   # a parse failure in project code must not break status
            out.append(f"{p.id}: unknown ({type(e).__name__})")
            continue
        if res:
            out.append(res if res.startswith(p.id) else f"{p.id}: {res}")
    return out


# ---- dependency graph --------------------------------------------------------------------------

def dependency_graph(repo: Repo) -> dict[str, list[str]]:
    """Component (single package) or package (multi) → what it depends on, from the root architecture's
    Components / Packages table, in table order. Unknown names in `Depends on` are dropped."""
    arch = repo.architecture
    rows = model.components(arch) if arch else []
    ids = [c.id for c in rows]
    return {c.id: [d.split()[0] for d in c.depends_on if d.split() and d.split()[0] in ids and d.split()[0] != c.id]
            for c in rows}


def closure(graph: dict[str, list[str]], node: str) -> set[str]:
    """Everything `node` depends on, directly or not."""
    seen: set[str] = set()
    todo = list(graph.get(node, []))
    while todo:
        n = todo.pop()
        if n not in seen and n != node:
            seen.add(n)
            todo.extend(graph.get(n, []))
    return seen


def dependents(graph: dict[str, list[str]]) -> dict[str, list[str]]:
    """Node → the nodes that depend on it, directly or not (what `check.sh --pkg` must also test)."""
    return {n: [m for m in graph if n in closure(graph, m)] for n in graph}
