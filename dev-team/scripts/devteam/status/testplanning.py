"""`dt status --skill test-planning`: per-package mode, smoke and golden coverage, case fields and fixtures.

(Not named test_planning.py so test runners never collect it.)
"""
from __future__ import annotations

import os
import re

from .. import md, model, routes
from ..repo import Repo
from .common import Report, add_common, available_skills, in_revise
from .packages import known_packages


def _norm_path(p: str) -> str:
    return md.strip_md(p).strip().rstrip("/").lstrip("./")


def fixtures_orphan(repo: Repo, referenced: set[str]) -> list[str]:
    """`tests/fixtures/<pkg>/TC-NN/` folders no live case points at."""
    out = []
    base = repo.root / "tests" / "fixtures"
    if base.is_dir():
        for pkg_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            for case in sorted(p for p in pkg_dir.iterdir() if p.is_dir() and re.fullmatch(r"TC-\d{2,}", p.name)):
                rel = str(case.relative_to(repo.root)).replace(os.sep, "/")
                if rel not in referenced:
                    out.append(rel + "/")
    return out


def test_planning(repo: Repo, r: Report) -> None:
    modes: dict[str, str] = {}
    no_smoke, no_golden, no_source, no_tol, fx_missing = [], [], [], [], []
    referenced_fixtures: set[str] = set()
    for pkg in known_packages(repo):
        pdoc = repo.package_doc(pkg, "pipelines")
        if pdoc is None or pdoc.status != "Approved":
            modes[pkg] = "blocked"
            continue
        tdoc = repo.package_doc(pkg, "tests")
        cases = model.test_cases(tdoc) if tdoc else []
        rows = model.strategy_rows(tdoc) if tdoc else []
        gaps = False
        for p in model.pipelines(pdoc):
            if re.search(r"PL-\d{2,}", p.fields.get("Part of", "")):
                continue      # a package part of a system pipeline: tested through the system pipeline
            row = next((x for x in rows if re.search(rf"\b{re.escape(p.id)}\b", x.get("Pipeline", ""))), {})
            if not re.search(r"`[^`]+`", row.get("Smoke", "")):
                no_smoke.append(p.id)
                gaps = True
            golden = [t for t in cases if t.pipeline == p.id] or \
                [i for i in md.expand_refs(row.get("Golden cases", "")) if i.startswith("TC-")]
            if not golden:
                no_golden.append(p.id)
                gaps = True
        for t in cases:
            if not md.strip_md(t.fields.get("Source", "")):
                no_source.append(t.id)
            if not md.strip_md(t.fields.get("Tolerance", "")):
                no_tol.append(t.id)
            fixture = _norm_path(t.fixture) or f"tests/fixtures/{pkg}/{t.id}"
            referenced_fixtures.add(fixture)
            folder = repo.root / fixture
            if not folder.is_dir():
                fx_missing.append(f"{t.id} ({fixture}/)")
            elif not (folder / "expected.json").is_file():
                fx_missing.append(f"{t.id} (no expected.json)")
        modes[pkg] = "new" if tdoc is None else "revise" if in_revise(repo, tdoc) else \
            "extend" if gaps else "current"
    routed = routes.open_for(repo, "test-planning")
    if not modes or all(m == "blocked" for m in modes.values()):
        r.mode("blocked", "no Approved pipelines.md (run pipeline-design)")
    else:
        present = set(modes.values()) | ({"revise"} if routed else set())
        r.mode(next(m for m in ("new", "revise", "extend", "current") if m in present))
    add_common(repo, r)
    r.add("packages", modes)
    r.add("pipelines_no_smoke", no_smoke)
    r.add("pipelines_no_golden", no_golden)
    r.add("cases_no_source", no_source)
    r.add("cases_no_tolerance", no_tol)
    r.add("fixtures_missing", fx_missing)
    r.add("fixtures_orphan", fixtures_orphan(repo, referenced_fixtures))
    r.add("skills", available_skills(repo))
    r.add("routed_changes", routed)
