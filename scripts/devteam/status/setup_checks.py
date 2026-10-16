"""build-setup.md §9 checks that compare the generated config with the architecture and CONSTRAINTS.md:
import-linter contracts, optional layers, deptry config, the protected list, per-file ignores and
exceptions. Each returns a list of problems, or None when its input file is absent (printed `unknown`)."""
from __future__ import annotations

import datetime
import re
from fnmatch import fnmatch
from pathlib import Path

from .. import md, model
from ..commands import roadmap as roadmap_cmd
from ..repo import Repo
from .packages import closure, is_multi, known_packages
from .tomlread import load_toml

REQUIRED_PROTECTED = ("tests/intent/**", "tests/fixtures/**")
STANDING_IGNORES = {"tests/**", "__init__.py"}


def read_pyproject(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return load_toml(path)
    except Exception:
        return None


def _tool(data: dict | None, *keys: str):
    node = (data or {}).get("tool", {})
    for k in keys:
        node = node.get(k) if isinstance(node, dict) else None
    return node


# ---- import-linter -----------------------------------------------------------------------------

def _layer_names(entry: str) -> tuple[list[str], bool, bool]:
    """A layers entry → (module names, optional, independent siblings). `"(quant.portfolio)"`,
    `"quant.a | quant.b"` (independent), `"quant.a : quant.b"` (siblings that may import each other)."""
    optional = entry.strip().startswith("(")
    names = [n.strip().strip("()").strip() for n in re.split(r"[|:]", entry) if n.strip().strip("()").strip()]
    return names, optional, "|" in entry


def _short(module: str) -> str:
    return module.strip().split(".")[-1]


def forbidden_imports(contracts: list[dict]) -> set[tuple[str, str]]:
    """(importer, imported) pairs the contracts forbid, by last module segment."""
    out: set[tuple[str, str]] = set()
    for c in contracts:
        kind = c.get("type", "")
        if kind == "layers":
            layers = [_layer_names(str(e)) for e in c.get("layers", [])]
            for i, (upper, _, independent) in enumerate(layers):
                if independent:
                    out |= {(_short(a), _short(b)) for a in upper for b in upper if a != b}
                for lower, _, _ in layers[i + 1:]:
                    out |= {(_short(b), _short(a)) for a in upper for b in lower}
        elif kind == "forbidden":
            out |= {(_short(a), _short(b)) for a in c.get("source_modules", []) for b in c.get("forbidden_modules", [])}
        elif kind == "independence":
            mods = c.get("modules", [])
            out |= {(_short(a), _short(b)) for a in mods for b in mods if a != b}
    return out


def contract_mismatches(data: dict | None, graph: dict[str, list[str]]) -> list[str] | None:
    """Import-linter contracts vs the architecture's dependency rules (each node may import what it depends
    on, directly or not, and nothing else first-party)."""
    if data is None:
        return None
    if len(graph) < 2:
        return []
    contracts = _tool(data, "importlinter", "contracts") or []
    if not contracts:
        return ["no [[tool.importlinter.contracts]] in pyproject.toml"]
    forbidden = forbidden_imports(contracts)
    out = []
    for a in graph:
        allowed = closure(graph, a)
        for b in graph:
            if b == a:
                continue
            if b in allowed and (a, b) in forbidden:
                out.append(f"{a} → {b}: forbidden by a contract, allowed by the architecture")
            elif b not in allowed and (a, b) not in forbidden:
                out.append(f"{a} → {b}: allowed by the contracts, not by the architecture")
    return out


def optional_layers_existing(repo: Repo, data: dict | None) -> list[str] | None:
    """`"(pkg.component)"` layers whose module now exists: the parentheses should come off."""
    if data is None:
        return None
    roots = [repo.root / "src"] + sorted((repo.root / "packages").glob("*/src"))
    out = []
    for c in _tool(data, "importlinter", "contracts") or []:
        for entry in c.get("layers", []) if c.get("type") == "layers" else []:
            names, optional, _ = _layer_names(str(entry))
            if not optional:
                continue
            for name in names:
                rel = Path(*name.split("."))
                if any((r / rel).is_dir() or (r / rel).with_suffix(".py").is_file() for r in roots):
                    out.append(name)
    return list(dict.fromkeys(out))


# ---- deptry, protected list, ignores -----------------------------------------------------------

def deptry_missing(repo: Repo, data: dict | None) -> list[str] | None:
    """Packages with no `[tool.deptry]`: the root pyproject (single) or `packages/<pkg>/pyproject.toml` (multi)."""
    if data is None:
        return None
    pkgs = known_packages(repo)
    if not is_multi(repo):
        return [] if _tool(data, "deptry") is not None else (pkgs or ["(root pyproject.toml)"])
    return [p for p in pkgs if _tool(read_pyproject(repo.root / "packages" / p / "pyproject.toml"), "deptry") is None]


def protected_lists(repo: Repo) -> dict[str, list[str]]:
    """The protected globs as `scripts/check.sh` (`PROTECTED=(…)`) and CONSTRAINTS.md (**Protected list**) state them."""
    out = {}
    check = repo.root / "scripts" / "check.sh"
    if check.is_file():
        m = re.search(r"^PROTECTED=\((.*?)\)", check.read_text(encoding="utf-8", errors="replace"), re.M | re.S)
        if m:
            out["check.sh"] = [a or b for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", m.group(1))]
    if repo.constraints:
        line = next((x for x in repo.constraints.lines if "**Protected list**" in x), None)
        if line:
            out["CONSTRAINTS.md"] = [g for g in re.findall(r"`([^`]+)`", line.split(":", 1)[-1]) if "/" in g or "." in g]
    return out


def protected_gaps(repo: Repo) -> list[str] | None:
    """Required test paths a protected list doesn't cover, and the two lists disagreeing."""
    lists = protected_lists(repo)
    if not lists:
        return None
    out = []
    for source, globs in lists.items():
        for req in REQUIRED_PROTECTED:
            sample = req.replace("**", "pkg/test_x.py")
            if not any(g == req or fnmatch(sample, g) for g in globs):
                out.append(f"{req} not in {source}")
    if len(lists) == 2:
        a, b = (set(v) for v in lists.values())
        if a != b:
            out.append(f"check.sh and CONSTRAINTS.md differ: {', '.join(sorted(a ^ b))}")
    return out


def exception_rows(repo: Repo) -> list[dict[str, str]]:
    """Rows of CONSTRAINTS.md's Exceptions table."""
    doc = repo.constraints
    h = doc.heading("Exceptions") if doc else None
    if not h:
        return []
    rows = []
    for _, head, trows in doc.tables(h.line + 1, h.end):
        rows += [row for _n, row in md.table_dicts(head, trows) if any(v.strip() for v in row.values())]
    return rows


def ignores_without_exception(repo: Repo, data: dict | None) -> list[str] | None:
    """Ruff per-file-ignores (standing `tests/**` and `__init__.py` exempt) and deptry per_rule_ignores
    entries that no Exceptions row names."""
    if data is None:
        return None
    rows_text = [md.strip_md(" ".join(r.values())) for r in exception_rows(repo)]

    def named(token: str) -> bool:
        return any(token in t for t in rows_text)
    out = []
    for path, codes in (_tool(data, "ruff", "lint", "per-file-ignores") or {}).items():
        if path not in STANDING_IGNORES and not named(path):
            out.append(f"{path} ({', '.join(map(str, codes)) if isinstance(codes, list) else codes})")
    configs = [data] + [read_pyproject(p) for p in sorted((repo.root / "packages").glob("*/pyproject.toml"))]
    for cfg in configs:
        for rule, names in (_tool(cfg, "deptry", "per_rule_ignores") or {}).items():
            for name in names if isinstance(names, list) else [names]:
                if not named(str(name)):
                    out.append(f"deptry {rule} {name}")
    return list(dict.fromkeys(out))


def _milestone_done(repo: Repo, mid: str) -> bool:
    if any(roadmap_cmd._plan_milestone(d) == mid for d in repo.docs("archived-plan", archive=True)):
        return True
    ms = next((m for m in model.milestones(repo.roadmap) if m.id == mid), None) if repo.roadmap else None
    return bool(ms and roadmap_cmd.milestone_status(repo, ms) == "Done")


def expired_exceptions(repo: Repo, today: str | None = None) -> list[str]:
    """Exceptions whose `Expires` date is past, or whose `M<n> exit` milestone is archived or Done."""
    today = today or datetime.date.today().isoformat()
    out = []
    for row in exception_rows(repo):
        head = list(row)
        expires = row.get(next((k for k in head if k.lower().startswith("expires")), ""), "")
        date = re.search(r"\d{4}-\d{2}-\d{2}", expires)
        mid = re.search(r"\b(M\d+)\s+exit\b", expires, re.I)
        if date and date.group(0) < today:
            when = date.group(0)
        elif mid and _milestone_done(repo, mid.group(1)):
            when = f"{mid.group(1)} exit"
        else:
            continue
        label = " ".join(md.strip_md(row[k]) for k in head[:3] if md.strip_md(row[k]))
        out.append(f"{label} (expired {when})")
    return out
