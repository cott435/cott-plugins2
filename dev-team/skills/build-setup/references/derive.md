# Deriving the bar's values

Read when generating or extending the bar: the templates, the values that matter most, and where every `{{placeholder}}` comes from.

## Templates

| Project file | Template |
|---|---|
| `CONSTRAINTS.md` | `CONSTRAINTS.md` (≤ 2 pages) |
| `pyproject.toml` | single: `pyproject.toml` · multi: `pyproject.workspace.toml` at the root plus `package.pyproject.toml` per package |
| `scripts/check.sh`, `check_size.py`, `floor_guard.sh`, `floor_guard.py`, `red_check.py`, `vulture_whitelist.py` | `scripts/` |
| `scripts/hooks/{path_guard,post_edit,stop_gate,project_root}.sh` | `scripts/hooks/` |
| `.claude/agents/{tester,implementer,reviewer}.md` | `.claude/agents/` |
| `.github/workflows/check.yml` | only when the user asks for CI |
| `.gitignore` | append `gitignore.additions` (skip lines already present) |

## Values

- **Protected list**: written once into `check.sh`'s `PROTECTED` (`path_guard.sh deny --protected` reads it from there) and copied into CONSTRAINTS.md: `tests/intent/**`, `tests/fixtures/**`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`, `CONSTRAINTS.md`, `scripts/**`, `.claude/agents/**`, `.claude/settings.json`, `references/**`, `probes/**`, `tests/contracts/**`. Multi-package adds `packages/*/pyproject.toml`. The two lists must match, and no test directory may be missing.
- **Frozen interfaces** (CR-09): `check.sh` narrows `tests/contracts/**` to the contract folders that exist at `refs/checks/base`, so the milestone's interface task (`**Kind:** interface`, run as the implementer) can write the new `tests/contracts/<id>.<symbol>/` it freezes, and from the next task's base nothing can change it. A frozen interface changes only through `architecture-design` Revise, then a new interface task re-freezes it in the main session (the implementer's guard blocks a folder frozen at the base); outside an open interface task naming the folder, the plugin's `dt guard` asks before any edit under `tests/contracts/`. The types and signatures it writes in `src/` are held by `Writes:`: no later task's list names them.
- **Interface stubs** (CR-02): `floor_guard.py` treats a body that is only `raise NotImplementedError("<task id>")` as the interface task's signature stub, never a `stub` finding; across the whole project it fails one naming a task not open in `tasks/todo.md` (`stub-task`, gate and full) and, under `--exit`, any (`stub-left`). Nothing to derive.
- **`Writes:` guard**: tester and implementer both run `path_guard.sh writes`, which reads `.claude/.task_writes` (written by the orchestrator per task, one path or folder glob a line) and blocks edits outside it; with no file it allows everything, so a serial `/build` works unchanged.
- **RED for the right reason**: `check.sh collect` runs `red_check.py` on the intent test files changed since the base. Each failure must be an `AssertionError`, a `NotImplementedError` from an interface stub, or `pytest.fail`; an ImportError, AttributeError, TypeError or fixture error fails collect, as does a set of tests none of which is red.
- **Import contracts**: generated from the architecture's dependency rules (`tools/import_linter.md`), never hand-written, so `dt` can check them. A module that doesn't exist yet is an optional layer: `"(pkg.component)"`.
- **`pkg_scope`** in `check.sh`: each package (single: component) and every package that depends on it, from the dependency graph. It must match `dt status`'s `dependents`.
- **Domain rule families and stubs** from the tech stack ADs (`DTZ`, `NPY` + numpy, `PD` + `pandas-stubs`); pandera only when a DataFrame crosses a contract.
- **Dependencies**: the milestone's, each with a `[tool.deptry.per_rule_ignores] DEP002` entry and an Exceptions row expiring `M<n> exit`. A dependency nobody planned blocks its task and comes back through Revise; the implementer never edits `[project.dependencies]`.
- **Thresholds**: measure and hold unless the user chose targets. Coverage `fail_under` is today's value (0 on an empty skeleton, recorded at the first Ratchet); vulture's whitelist holds today's findings. Never set a threshold the codebase fails today.
- **References and probes** (`design/references.md` §7, `design/probes.md` §4.6): nothing to derive. The templates exclude `references/` and `probes/` from Ruff, mypy, pytest, coverage, deptry, vulture and typos; both are protected (so reference files are committed before a task starts, and no builder edits probe evidence); CR-08 forbids importing either or putting it on `sys.path`, and `floor_guard` checks the diff. Copying from either is the builder's call: there is no copy check, and copied code meets the normal bar. `gitignore.additions` keeps `.env` files and each probe's `out/` out of git.
- **Exceptions**: every one is an `EX-NN` row with a rule, path, reason, owner and expiry (a date, or `M<n> exit`); a Ruff exception is also a `per-file-ignores` entry, and every config ignore has a row.
- **Numbers**: every CR rule with a number names its config key, and the two are identical. Every rule has a tool behind it, and at least one external check (pip-audit) runs in `full`.
- **Non-Python parts** (a frontend): their rules come from agent-skills `constraint-driven-development`; record them here with that part's path, and `check.sh` calls its check command.

## Placeholders: where each value comes from

Templates use `{{name}}`. After filling, `grep -rn '{{[a-z_]*}}'` over the written files must print nothing (`${{ github.… }}` in the CI file is GitHub's own syntax and has spaces, so it doesn't match). `../tests/project.py` fills them the same way for the tests.

| Placeholder | Where | Value | Derived from |
|---|---|---|---|
| `project_name` | pyproject | distribution name | existing `[project].name`, else the repo name |
| `python_version`, `python_target` | pyproject | `3.11`, `py311` | `.python-version`, else the language AD |
| `uv_build_requirement` | pyproject | `uv_build>=0.11,<0.12` | `uv --version` (major.minor, next minor) |
| `dependencies` | pyproject | `    "numpy",` lines | the milestone's dependencies (plan, tech stack ADs) |
| `stub_packages` | pyproject | `    "pandas-stubs",` | one per dependency without inline types (`tools/mypy.md`) |
| `domain_rules` | pyproject | `    "DTZ", "NPY", "PD",` | tech stack ADs (`tools/ruff_domain.md`); empty if none |
| `pkg` | pyproject | import name | the package id (multi: one file per package) |
| `pkg_dist`, `package_sources` | package pyproject | dist name; `[tool.uv.sources]` with `{ workspace = true }` for each sibling it depends on | package dependency rules |
| `workspace_members`, `workspace_sources`, `pkgs_quoted`, `src_dirs_quoted` | workspace pyproject | every package, as lists | the Packages table |
| `coverage_floor` | pyproject | `0` on an empty skeleton, else today's measured value (measure and hold), or the user's target | measure with `check.sh full` |
| `deptry_ignores` | pyproject | `[tool.deptry.per_rule_ignores]` + `DEP002 = [...]`, or empty | dependencies no code imports yet; one Exceptions row each |
| `import_contracts` | pyproject | `[[tool.importlinter.contracts]]` blocks | `Depends on` (single) or the package dependency rules (multi); missing modules in `(…)` |
| `typos_ignore_identifiers` | pyproject | `"^[A-Z]{1,5}$"` for tickers, else empty | domain |
| `protected_globs` | check.sh | `'tests/intent/**' 'tests/fixtures/**' …` (quoted) | the twelve globs of the Protected list above; multi adds `'packages/*/pyproject.toml'` |
| `src_dirs`, `packages_dir` | check.sh | `src` and empty · `packages/a/src packages/b/src` and `packages` | shape |
| `type_gate` | check.sh, CONSTRAINTS | `mypy` or `pyright` | the type-gate answer |
| `pkg_scope_cases` | check.sh | `    data) echo "data stats portfolio" ;;` per id | dependency graph: the id plus everything that depends on it, directly or not |
| `source_globs` | tester.md | `"src/**"` · `"packages/*/src/**"` | shape |
| `date`, `owner` | CONSTRAINTS | today, `@user` | — |
| `type_gate_key` | CONSTRAINTS | `tool.mypy.strict` · `tool.pyright.typeCheckingMode` | the type-gate answer |
| `coverage_today`, `vulture_today` | CONSTRAINTS | `— (no code)` / `71.2%`; whitelist entry count | measured |
| `readability_rules` | CONSTRAINTS | extra `- **CR-13** …` lines from pipeline-design, or empty | `pipelines.md` |
| `extra_enforced_rows` | CONSTRAINTS | e.g. CR-27 repro, a frontend row, or empty | spec QRs; non-Python parts |
| `boundary_rules` | CONSTRAINTS | one line, `` `pkg.data` imports nothing first-party · `pkg.stats` → data `` | same source as the contracts |
| `protected_globs_md` | CONSTRAINTS | the protected list in backticks | same list as `protected_globs` |
| `exception_rows` | CONSTRAINTS | `\| EX-01 \| … \|` rows, or empty | the `DEP002` and other exceptions |
| `default_branch` | check.yml | `main` | `git symbolic-ref refs/remotes/origin/HEAD`, else `main` |

**Multi-package `pyproject.toml`:** the root is `pyproject.workspace.toml` followed by these sections of `pyproject.toml`, unchanged: `[tool.ruff.lint]` (select, ignore), `.mccabe`, `.pylint`, `.per-file-ignores`, `[tool.ruff.format]`, `[tool.size_limits]`, `[tool.pytest.ini_options]`, `[tool.typos.files]`, `[tool.typos.default]`. deptry lives in each package's file, never the root.
