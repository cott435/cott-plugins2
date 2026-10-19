"""Turn the buildmini fixture into a live repo for the build smoke tests: `python3 make_live.py DEST`.

Copies the fixture to DEST, renders build-setup's templates onto it the way build-setup New mode would (through
skills/build-setup/tests/project.py, so the placeholder values stay in step with the templates), then `git init`,
`uv lock`, `uv sync`, commits the skeleton, records the plan's Base with `dt base` and commits that.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[3]
DT = PLUGIN / "scripts" / "dt.py"
sys.path.insert(0, str(PLUGIN / "skills" / "build-setup" / "tests"))

import project as bp  # noqa: E402

SKIP = shutil.ignore_patterns("README.md", "make_live.py", "__pycache__")


def values() -> dict[str, str]:
    return bp.base_values() | {
        "project_name": "mini",
        "pkg": "mini",
        "dependencies": "",
        "pkg_scope_cases": '    mini) echo "mini" ;;',
        "import_contracts": ('[[tool.importlinter.contracts]]\nname = "Layers: pipeline > summary > types"\n'
                             'type = "layers"\nlayers = ["(mini.__main__)", "(mini.pipeline)", "(mini.summary)", '
                             '"(mini.types)"]'),
        "boundary_rules": "- `mini.types` imports nothing first-party · `mini.summary` → types · `mini.pipeline` → "
                          "summary, types",
        "coverage_floor": "0",
        "coverage_today": "0%",
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.splitlines()[0], file=sys.stderr)
        return 2
    dest = Path(argv[0]).resolve()
    if dest.exists() and any(dest.iterdir()):
        print(f"make_live: {dest} is not empty", file=sys.stderr)
        return 1
    shutil.copytree(HERE, dest, ignore=SKIP, dirs_exist_ok=True)
    v = values()
    bp.common(dest, v)
    bp.copy_template(dest, "pyproject.toml", v)
    constraints = dest / "CONSTRAINTS.md"         # the bar as the user approved it
    constraints.write_text(constraints.read_text(encoding="utf-8").replace("**Status:** Draft", "**Status:** Approved", 1),
                           encoding="utf-8")
    bp.finish(dest)                       # git init -b main, uv lock and sync, ruff format, commit "skeleton"
    subprocess.run([sys.executable, str(DT), "--root", str(dest), "base"], check=True)
    bp.sh(dest, "git", "commit", "-q", "-am", "M1: record the bar's base")
    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
