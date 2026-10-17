# Deriving the bar's values

Read when generating or extending the bar. Every `{{placeholder}}` and how its value is derived is in `../examples.md`; these are the values that matter most.

## Templates

| Project file | Template |
|---|---|
| `CONSTRAINTS.md` | `CONSTRAINTS.md` (≤ 2 pages) |
| `pyproject.toml` | single: `pyproject.toml` · multi: `pyproject.workspace.toml` at the root plus `package.pyproject.toml` per package |
| `scripts/check.sh`, `check_size.py`, `floor_guard.sh`, `floor_guard.py`, `vulture_whitelist.py` | `scripts/` |
| `scripts/hooks/{path_guard,post_edit,stop_gate,project_root}.sh` | `scripts/hooks/` |
| `.claude/agents/{tester,implementer,reviewer}.md` | `.claude/agents/` |
| `.github/workflows/check.yml` | only when the user asks for CI |
| `.gitignore` | append `gitignore.additions` (skip lines already present) |

## Values

- **Protected list**: written once into `check.sh`'s `PROTECTED` (`path_guard.sh deny --protected` reads it from there) and copied into CONSTRAINTS.md: `tests/intent/**`, `tests/fixtures/**`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`, `CONSTRAINTS.md`, `scripts/**`, `.claude/agents/**`, `.claude/settings.json`, `references/**`, `tests/contracts/**`. Multi-package adds `packages/*/pyproject.toml`. The two lists must match, and no test directory may be missing.
- **Frozen contracts** (CR-09): `check.sh` narrows `tests/contracts/**` to the contract folders that exist at `refs/checks/base`, so the Phase 0 contract task (`**Step:** contract`, run as the implementer) can write the new `tests/contracts/<pkg>.<symbol>/` it freezes, and from the next task's base nothing can change it. A frozen contract changes only through `architecture-design` Revise, then a new contract task re-freezes it in the main session (the implementer's guard blocks a folder frozen at the base); outside an open contract task naming the folder, the plugin's `dt guard` asks before any edit under `tests/contracts/`.
- **Import contracts**: generated from the architecture's dependency rules (`tools/import_linter.md`), never hand-written, so `dt` can check them. A module that doesn't exist yet is an optional layer: `"(pkg.component)"`.
- **`pkg_scope`** in `check.sh`: each package (single: component) and every package that depends on it, from the dependency graph. It must match `dt status`'s `dependents`.
- **Domain rule families and stubs** from the tech stack ADs (`DTZ`, `NPY` + numpy, `PD` + `pandas-stubs`); pandera only when a DataFrame crosses a contract.
- **Dependencies**: the milestone's, each with a `[tool.deptry.per_rule_ignores] DEP002` entry and an Exceptions row expiring `M<n> exit`. A dependency nobody planned blocks its task and comes back through Revise; the implementer never edits `[project.dependencies]`.
- **Thresholds**: measure and hold unless the user chose targets. Coverage `fail_under` is today's value (0 on an empty skeleton, recorded at the first Ratchet); vulture's whitelist holds today's findings. Never set a threshold the codebase fails today.
- **References** (`design/references.md` §7): nothing to derive. The templates exclude `references/` from Ruff, mypy, pytest, coverage, deptry, vulture and typos; it is protected (so reference files are committed before a task starts); CR-08 forbids importing it or putting it on `sys.path`, and `floor_guard` checks the diff. Copying from a reference is the builder's call: there is no copy check, and copied code meets the normal bar.
- **Exceptions**: every one is an `EX-NN` row with a rule, path, reason, owner and expiry (a date, or `M<n> exit`); a Ruff exception is also a `per-file-ignores` entry, and every config ignore has a row.
- **Numbers**: every CR rule with a number names its config key, and the two are identical. Every rule has a tool behind it, and at least one external check (pip-audit) runs in `full`.
- **Non-Python parts** (a frontend): their rules come from agent-skills `constraint-driven-development`; record them here with that part's path, and `check.sh` calls its check command.
