"""Build a tiny project from the build-setup templates, for the script tests.

`make_single(dest)` and `make_multi(dest)` render the templates the way build-setup New mode
would, add a few modules and tests, `uv sync`, and commit. Placeholders are `{{name}}`; a
leftover one fails the render, so a template and the skill's placeholder table can't drift.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")
SCRIPTS = [
    "scripts/check.sh",
    "scripts/check_size.py",
    "scripts/floor_guard.sh",
    "scripts/floor_guard.py",
    "scripts/vulture_whitelist.py",
    "scripts/hooks/path_guard.sh",
    "scripts/hooks/post_edit.sh",
    "scripts/hooks/stop_gate.sh",
    "scripts/hooks/project_root.sh",
]
PROTECTED = [
    "tests/intent/**", "tests/fixtures/**", "tests/conftest.py", "pyproject.toml", "uv.lock",
    "CONSTRAINTS.md", "scripts/**", ".claude/agents/**", ".claude/settings.json", "references/**",
    "tests/contracts/**",
]


def render(text: str, values: dict[str, str]) -> str:
    out = PLACEHOLDER.sub(lambda m: values[m[1]] if m[1] in values else m[0], text)
    left = PLACEHOLDER.findall(out)
    if left:
        raise KeyError(f"unfilled placeholders: {sorted(set(left))}")
    return out


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_template(root: Path, rel: str, values: dict[str, str], dest: str | None = None) -> None:
    write(root, dest or rel, render((TEMPLATES / rel).read_text(encoding="utf-8"), values))


def sh(root: Path, *cmd: str, check: bool = True, **kw) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "NO_COLOR": "1"}
    env.pop("VIRTUAL_ENV", None)
    return subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=check, env=env, **kw)


def uv_build_requirement() -> str:
    out = subprocess.run(["uv", "--version"], text=True, capture_output=True, check=True).stdout
    major, minor = out.split()[1].split(".")[:2]
    return f"uv_build>={major}.{minor},<{major}.{int(minor) + 1}"


def base_values() -> dict[str, str]:
    return {
        "project_name": "tinyq",
        "python_version": "3.11",
        "python_target": "py311",
        "uv_build_requirement": uv_build_requirement(),
        "stub_packages": "",
        "domain_rules": '    "DTZ",',
        "coverage_floor": "80",
        "deptry_ignores": "",
        "typos_ignore_identifiers": "",
        "protected_globs": " ".join(f"'{g}'" for g in PROTECTED),
        "type_gate": "mypy",
        "packages_dir": "",
        "src_dirs": "src",
        "date": "2026-10-16",
        "owner": "@tester",
        "readability_rules": "",
        "type_gate_key": "tool.mypy.strict",
        "extra_enforced_rows": "",
        "coverage_today": "80%",
        "vulture_today": "0",
        "boundary_rules": "- `tinyq.data` imports nothing first-party · `tinyq.stats` → data",
        "protected_globs_md": ", ".join(f"`{g}`" for g in PROTECTED),
        "exception_rows": "",
        "source_globs": '"src/**"',
        "default_branch": "main",
    }


def common(root: Path, values: dict[str, str]) -> None:
    for rel in SCRIPTS:
        copy_template(root, rel, values)
    for rel in [".claude/agents/tester.md", ".claude/agents/implementer.md",
                ".claude/agents/reviewer.md", "CONSTRAINTS.md", "tests/conftest.py"]:
        copy_template(root, rel, values)
    shutil.copy(TEMPLATES / "gitignore.additions", root / ".gitignore")
    write(root, ".python-version", "3.11\n")


DATA = '''"""Price loading."""


def load_prices(raw: list[float]) -> list[float]:
    """Return the prices, rejecting any that are not positive."""
    if any(p <= 0 for p in raw):
        raise ValueError("prices must be positive")
    return list(raw)
'''
STATS = '''"""Summary statistics."""

from {pkg}.prices import load_prices


def mean_price(raw: list[float]) -> float:
    """Mean of the validated prices."""
    prices = load_prices(raw)
    return sum(prices) / len(prices)
'''
UNIT = '''"""Unit tests for {mod}."""

import pytest

from {imp} import {fn}


def test_{fn}_accepts_positive() -> None:
    assert {fn}([1.0, 3.0]) == pytest.approx({want})


def test_{fn}_rejects_zero() -> None:
    with pytest.raises(ValueError, match="positive"):
        {fn}([1.0, 0.0])
'''
INTENT = '''"""Intent: the mean of known prices."""

import pytest

from {imp} import mean_price


@pytest.mark.intent
def test_mean_price_of_two() -> None:
    assert mean_price([2.0, 4.0]) == pytest.approx(3.0)
'''


def make_single(root: Path) -> dict[str, str]:
    values = base_values() | {
        "pkg": "tinyq",
        "dependencies": "",
        "pkg_scope_cases": '    data) echo "data stats" ;;\n    stats) echo "stats" ;;\n    report) echo "report" ;;',
        "import_contracts": (
            '[[tool.importlinter.contracts]]\nname = "Layers: report > stats > data"\n'
            'type = "layers"\nlayers = ["(tinyq.report)", "tinyq.stats", "tinyq.data"]'
        ),
    }
    common(root, values)
    copy_template(root, "pyproject.toml", values)
    write(root, "src/tinyq/__init__.py", '"""tinyq."""\n')
    write(root, "src/tinyq/data/__init__.py", '"""Data component."""\n')
    write(root, "src/tinyq/data/prices.py", DATA)
    write(root, "src/tinyq/stats/__init__.py", '"""Stats component."""\n')
    write(root, "src/tinyq/stats/moments.py", STATS.format(pkg="tinyq.data"))
    write(root, "tests/unit/data/test_prices.py",
          UNIT.format(mod="prices", imp="tinyq.data.prices", fn="load_prices", want="[1.0, 3.0]"))
    write(root, "tests/unit/stats/test_moments.py",
          UNIT.format(mod="moments", imp="tinyq.stats.moments", fn="mean_price", want="2.0"))
    write(root, "tests/intent/stats/test_mean.py", INTENT.format(imp="tinyq.stats.moments"))
    finish(root)
    return values


def make_multi(root: Path) -> dict[str, str]:
    pkgs = ["qcore", "qapp"]
    values = base_values() | {
        "packages_dir": "packages",
        "src_dirs": "packages/qcore/src packages/qapp/src",
        "src_dirs_quoted": '"packages/qcore/src", "packages/qapp/src"',
        "pkgs_quoted": '"qcore", "qapp"',
        "workspace_members": '    "qcore",\n    "qapp",',
        "workspace_sources": "qcore = { workspace = true }\nqapp = { workspace = true }",
        "pkg_scope_cases": '    qcore) echo "qcore qapp" ;;\n    qapp) echo "qapp" ;;',
        "import_contracts": (
            '[[tool.importlinter.contracts]]\nname = "Layers: qapp > qcore"\n'
            'type = "layers"\nlayers = ["qapp", "qcore"]'
        ),
        "source_globs": '"packages/*/src/**"',
        "protected_globs": " ".join(f"'{g}'" for g in [*PROTECTED, "packages/*/pyproject.toml"]),
    }
    common(root, values)
    single = render((TEMPLATES / "pyproject.toml").read_text(encoding="utf-8"),
                    values | {"pkg": "qcore", "dependencies": ""})
    workspace = render((TEMPLATES / "pyproject.workspace.toml").read_text(encoding="utf-8"), values)
    write(root, "pyproject.toml", workspace + "\n" + shared_sections(single))
    for pkg in pkgs:
        deps = '    "qcore",' if pkg == "qapp" else ""
        sources = "[tool.uv.sources]\nqcore = { workspace = true }" if pkg == "qapp" else ""
        copy_template(root, "package.pyproject.toml",
                      values | {"pkg": pkg, "pkg_dist": pkg, "dependencies": deps, "package_sources": sources},
                      dest=f"packages/{pkg}/pyproject.toml")
        write(root, f"packages/{pkg}/src/{pkg}/__init__.py", f'"""{pkg}."""\n')
    write(root, "packages/qcore/src/qcore/prices.py", DATA)
    write(root, "packages/qapp/src/qapp/moments.py", STATS.format(pkg="qcore"))
    write(root, "tests/unit/qcore/test_prices.py",
          UNIT.format(mod="prices", imp="qcore.prices", fn="load_prices", want="[1.0, 3.0]"))
    write(root, "tests/unit/qapp/test_moments.py",
          UNIT.format(mod="moments", imp="qapp.moments", fn="mean_price", want="2.0"))
    write(root, "tests/intent/qapp/test_mean.py", INTENT.format(imp="qapp.moments"))
    finish(root)
    return values


SHARED = ("[tool.ruff.lint]", "[tool.ruff.lint.mccabe]", "[tool.ruff.lint.pylint]",
          "[tool.ruff.lint.per-file-ignores]", "[tool.ruff.format]", "[tool.size_limits]",
          "[tool.pytest.ini_options]", "[tool.typos.files]", "[tool.typos.default]")


def shared_sections(single: str) -> str:
    """The sections the workspace root copies unchanged from the single-package template."""
    blocks = re.split(r"(?m)^(?=\[)", single)
    return "".join(b for b in blocks if b.startswith(SHARED) and not b.startswith("[tool.ruff.lint.isort]"))


def finish(root: Path) -> None:
    for rel in SCRIPTS:
        if rel.endswith(".sh"):
            (root / rel).chmod(0o755)
    sh(root, "git", "init", "-q", "-b", "main")
    sh(root, "git", "config", "user.email", "t@example.com")
    sh(root, "git", "config", "user.name", "t")
    sh(root, "uv", "lock", "--quiet")
    sh(root, "uv", "sync", "--frozen", "--quiet")
    sh(root, "uv", "run", "--frozen", "--quiet", "ruff", "format", "--quiet", ".")
    # New mode records today's vulture findings, so "must not grow" starts from here (CR-41).
    found = sh(root, "uv", "run", "--frozen", "--quiet", "vulture", "--make-whitelist", check=False).stdout
    header = (root / "scripts/vulture_whitelist.py").read_text(encoding="utf-8")
    write(root, "scripts/vulture_whitelist.py", header + found)
    commit(root, "skeleton")
    sh(root, "git", "update-ref", "refs/checks/skeleton", "HEAD")


def commit(root: Path, message: str) -> None:
    sh(root, "git", "add", "-A")
    sh(root, "git", "commit", "-q", "-m", message)
    sh(root, "git", "update-ref", "refs/checks/base", "HEAD")


def reset(root: Path) -> None:
    """Back to the committed skeleton; the venv and caches are ignored files and stay."""
    sh(root, "git", "reset", "-q", "--hard", "refs/checks/skeleton")
    sh(root, "git", "update-ref", "refs/checks/base", "HEAD")
    sh(root, "git", "clean", "-q", "-fd")
    for counter in (root / ".claude").glob(".stop_attempts_*"):
        counter.unlink()
    (root / ".claude" / ".check_pkg").unlink(missing_ok=True)
