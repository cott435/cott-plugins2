#!/usr/bin/env python3
"""Turn minilab into a live repo at "planning done" with build-setup's real bar:
`python3 make_live.py DEST [--plan interface|spine|interface-solo|interface-pertask]`.

Copies project/ and the plan variant's tasks/ to DEST, renders build-setup's templates onto it the way build-setup
New mode would for a uv workspace of `mdata` and `risk` (through skills/build-setup/tests/project.py, as
scripts/tests/fixtures/buildmini/make_live.py does): scripts/check.sh and the hook scripts, the tester,
implementer and reviewer agents, CONSTRAINTS.md (Approved), the `.claude/settings.json` allow rules, `.gitignore`,
the workspace and package pyproject.toml files. The fixture's own tests/conftest.py (Hypothesis profiles plus the
golden-case helpers) replaces the template's. Then `git init`, `uv lock`, `uv sync`, `ruff format`, a commit, and
`dt base`, committed.

`make(dest, plan, plugin)` does the same from another copy of the plugin (build_driver.py passes the staged one, so
the plugin under test supplies the bar). `render_solution(dest)` copies solution/ over a rendered tree, to check the
bar passes on it (dryrun_build.py).
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE.parent
PLUGIN = FIX.parents[4]
PKGS = ("mdata", "risk")
PLANS = ("interface", "spine", "interface-solo", "interface-pertask")
# Each package's skeleton. risk declares mdata (the architecture's dependency rule) before any risk code exists, so
# its skeleton imports it, or deptry fails every gate until a risk task lands (DEP002); the first task writing
# risk/__init__.py replaces it.
SKELETON = {"mdata": '"""mdata."""\n',
            "risk": '"""risk: returns, volatility and the report, over mdata\'s prices."""\n\nimport mdata\n'}


def load_bp(plugin: Path):
    """build-setup's template renderer (skills/build-setup/tests/project.py) from that copy of the plugin."""
    path = plugin / "skills" / "build-setup" / "tests" / "project.py"
    spec = importlib.util.spec_from_file_location(f"bp_{abs(hash(str(path)))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bp = load_bp(PLUGIN)


def values(bp=bp) -> dict[str, str]:
    return bp.base_values() | {
        "project_name": "minilab",
        "packages_dir": "packages",
        "src_dirs": "packages/mdata/src packages/risk/src",
        "src_dirs_quoted": '"packages/mdata/src", "packages/risk/src"',
        "pkgs_quoted": '"mdata", "risk"',
        "workspace_members": '    "mdata",\n    "risk",',
        "workspace_sources": "mdata = { workspace = true }\nrisk = { workspace = true }",
        "pkg_scope_cases": '    mdata) echo "mdata risk" ;;\n    risk) echo "risk" ;;',
        "import_contracts": ('[[tool.importlinter.contracts]]\nname = "Layers: risk > mdata"\n'
                             'type = "layers"\nlayers = ["risk", "mdata"]'),
        "boundary_rules": "- `mdata` imports nothing first-party · `risk` → `mdata.types`, `mdata.load_prices`",
        "source_globs": '"packages/*/src/**"',
        "protected_globs": " ".join(f"'{g}'" for g in [*bp.PROTECTED, "packages/*/pyproject.toml"]),
        "protected_globs_md": ", ".join(f"`{g}`" for g in [*bp.PROTECTED, "packages/*/pyproject.toml"]),
        "coverage_floor": "0",
        "coverage_today": "0%",
        "date": "2026-10-17",
        "owner": "@connor",
        "worktree_links": "—",
    }


def render(dest: Path, plan: str = "interface", bp=bp) -> dict[str, str]:
    """Copy the fixture and render the bar onto it; no git, no uv."""
    shutil.copytree(FIX / "project", dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    shutil.copytree(FIX / f"plan-{plan}" / "tasks", dest / "tasks", dirs_exist_ok=True)
    conftest = (dest / "tests" / "conftest.py").read_text(encoding="utf-8")
    v = values(bp)
    bp.common(dest, v)
    (dest / "tests" / "conftest.py").write_text(conftest, encoding="utf-8")
    single = bp.render((bp.TEMPLATES / "pyproject.toml").read_text(encoding="utf-8"),
                       v | {"pkg": "mdata", "dependencies": ""})
    workspace = bp.render((bp.TEMPLATES / "pyproject.workspace.toml").read_text(encoding="utf-8"), v)
    bp.write(dest, "pyproject.toml", workspace + "\n" + bp.shared_sections(single))
    for pkg in PKGS:
        deps = '    "mdata",' if pkg == "risk" else ""
        sources = "[tool.uv.sources]\nmdata = { workspace = true }" if pkg == "risk" else ""
        bp.copy_template(dest, "package.pyproject.toml",
                         v | {"pkg": pkg, "pkg_dist": pkg, "dependencies": deps, "package_sources": sources},
                         dest=f"packages/{pkg}/pyproject.toml")
        init = dest / "packages" / pkg / "src" / pkg / "__init__.py"
        if not init.exists():
            bp.write(dest, f"packages/{pkg}/src/{pkg}/__init__.py", SKELETON[pkg])
    constraints = dest / "CONSTRAINTS.md"         # the bar as the user approved it
    constraints.write_text(constraints.read_text(encoding="utf-8").replace("**Status:** Draft", "**Status:** Approved", 1),
                           encoding="utf-8")
    return v


def render_solution(dest: Path, spine: bool = False) -> None:
    """solution/ (or solution/spine/ over it) copied onto a rendered tree."""
    sol = FIX / "solution"
    shutil.copytree(sol / "packages", dest / "packages", dirs_exist_ok=True)
    shutil.copytree(sol / "tests", dest / "tests", dirs_exist_ok=True)
    if spine:
        shutil.copytree(sol / "spine" / "packages", dest / "packages", dirs_exist_ok=True)


def make(dest: Path, plan: str = "interface", plugin: Path = PLUGIN) -> Path:
    """A live repo at DEST (which must not exist or be empty) from that plugin's templates; returns its dt.py."""
    plugin_bp = bp if plugin == PLUGIN else load_bp(plugin)
    dest.mkdir(parents=True, exist_ok=True)
    render(dest, plan, plugin_bp)
    plugin_bp.finish(dest)                # git init -b main, uv lock and sync, ruff format, commit "skeleton"
    dt = plugin / "scripts" / "dt.py"
    subprocess.run([sys.executable, str(dt), "--root", str(dest), "base"], check=True, capture_output=True)
    plugin_bp.sh(dest, "git", "commit", "-q", "-am", "M1: record the bar's base")
    return dt


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dest")
    ap.add_argument("--plan", default="interface", choices=PLANS)
    a = ap.parse_args(argv)
    dest = Path(a.dest).resolve()
    if dest.exists() and any(dest.iterdir()):
        print(f"make_live: {dest} is not empty", file=sys.stderr)
        return 1
    make(dest, a.plan)
    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
