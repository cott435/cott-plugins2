# Build Setup — Placeholders and Examples

## Placeholders: where each value comes from

Templates use `{{name}}`. After filling, `grep -rn '{{[a-z_]*}}'` over the written files must print nothing (`${{ github.… }}` in the CI file is GitHub's own syntax and has spaces, so it doesn't match). `skills/build-setup/tests/project.py` fills them the same way for the tests.

| Placeholder | Where | Value | Derived from |
|---|---|---|---|
| `project_name` | pyproject | distribution name | existing `[project].name`, else the repo name |
| `python_version`, `python_target` | pyproject | `3.11`, `py311` | `.python-version`, else the language AD |
| `uv_build_requirement` | pyproject | `uv_build>=0.11,<0.12` | `uv --version` (major.minor, next minor) |
| `dependencies` | pyproject | `    "numpy",` lines | the milestone's dependencies (plan, tech stack ADs) |
| `stub_packages` | pyproject | `    "pandas-stubs",` | one per dependency without inline types (`references/tools/mypy.md`) |
| `domain_rules` | pyproject | `    "DTZ", "NPY", "PD",` | tech stack ADs (`references/tools/ruff_domain.md`); empty if none |
| `pkg` | pyproject | import name | the package id (multi: one file per package) |
| `pkg_dist`, `package_sources` | package pyproject | dist name; `[tool.uv.sources]` with `{ workspace = true }` for each sibling it depends on | package dependency rules |
| `workspace_members`, `workspace_sources`, `pkgs_quoted`, `src_dirs_quoted` | workspace pyproject | every package, as lists | the Packages table |
| `coverage_floor` | pyproject | `0` on an empty skeleton, else today's measured value (question 3), or the user's target | measure with `check.sh full` |
| `deptry_ignores` | pyproject | `[tool.deptry.per_rule_ignores]` + `DEP002 = [...]`, or empty | dependencies no code imports yet; one Exceptions row each |
| `import_contracts` | pyproject | `[[tool.importlinter.contracts]]` blocks | `Depends on` (single) or the package dependency rules (multi); missing modules in `(…)` |
| `typos_ignore_identifiers` | pyproject | `"^[A-Z]{1,5}$"` for tickers, else empty | domain |
| `protected_globs` | check.sh | `'tests/intent/**' 'tests/fixtures/**' …` (quoted) | the fixed eleven globs below (SKILL.md Step 4); multi adds `'packages/*/pyproject.toml'` |
| `src_dirs`, `packages_dir` | check.sh | `src` and empty · `packages/a/src packages/b/src` and `packages` | shape |
| `type_gate` | check.sh, CONSTRAINTS | `mypy` or `pyright` | question 2 |
| `pkg_scope_cases` | check.sh | `    data) echo "data stats portfolio" ;;` per id | dependency graph: the id plus everything that depends on it, directly or not |
| `source_globs` | tester.md | `"src/**"` · `"packages/*/src/**"` | shape |
| `date`, `owner` | CONSTRAINTS | today, `@user` | — |
| `type_gate_key` | CONSTRAINTS | `tool.mypy.strict` · `tool.pyright.typeCheckingMode` | question 2 |
| `coverage_today`, `vulture_today` | CONSTRAINTS | `— (no code)` / `71.2%`; whitelist entry count | measured |
| `readability_rules` | CONSTRAINTS | extra `- **CR-13** …` lines from pipeline-design, or empty | `pipelines.md` |
| `extra_enforced_rows` | CONSTRAINTS | e.g. CR-27 repro, a frontend row, or empty | spec QRs; non-Python parts |
| `boundary_rules` | CONSTRAINTS | one line, `` `pkg.data` imports nothing first-party · `pkg.stats` → data `` | same source as the contracts |
| `protected_globs_md` | CONSTRAINTS | the protected list in backticks | same list as `protected_globs` |
| `exception_rows` | CONSTRAINTS | `\| EX-01 \| … \|` rows, or empty | the `DEP002` and other exceptions |
| `default_branch` | check.yml | `main` | `git symbolic-ref refs/remotes/origin/HEAD`, else `main` |

**Multi-package `pyproject.toml`:** the root is `pyproject.workspace.toml` followed by these sections of `pyproject.toml`, unchanged: `[tool.ruff.lint]` (select, ignore), `.mccabe`, `.pylint`, `.per-file-ignores`, `[tool.ruff.format]`, `[tool.size_limits]`, `[tool.pytest.ini_options]`, `[tool.typos.files]`, `[tool.typos.default]`. deptry lives in each package's file, never the root.

## Example: quant, single package, New mode

Architecture: `quant` with components `data` (depends on nothing), `stats` (→ data), `portfolio` (→ stats, data); pandas and NumPy (AD-02); `portfolio` arrives in M2. Plan M1 declares `numpy` and `pandas`.

**Values**
```bash
PROTECTED=('tests/intent/**' 'tests/fixtures/**' 'tests/conftest.py' 'pyproject.toml' 'uv.lock' 'CONSTRAINTS.md' 'scripts/**' '.claude/agents/**' '.claude/settings.json' 'references/**' 'tests/contracts/**')
pkg_scope() {
  case "$1" in
    data) echo "data stats portfolio" ;;
    stats) echo "stats portfolio" ;;
    portfolio) echo "portfolio" ;;
    *) return 1 ;;
  esac
}
```
```toml
[[tool.importlinter.contracts]]
name = "Layers: portfolio > stats > data"
type = "layers"
layers = ["(quant.portfolio)", "quant.stats", "quant.data"]

[tool.deptry.per_rule_ignores]
DEP002 = ["numpy", "pandas"]
```
```markdown
## Boundaries (generated from architecture — do not edit)
- `quant.data` imports nothing first-party · `quant.stats` → data · `quant.portfolio` → stats, data

## Exceptions
| ID | Rule | Path | Reason | Owner | Expires |
|---|---|---|---|---|---|
| EX-01 | CR-25 DEP002 | `numpy`, `pandas` | M1 dependencies, declared before the code imports them | @connor | M1 exit |
```

**Question, as asked**
```
Q2: Which type checker gates the implementer, mypy or pyright?
GUESS: mypy strict. The architecture pins pandas, and mypy with pandas-stubs is the verified setup.
DEFAULT if unsure: mypy strict as the gate; pyright runs in check.sh full.
```

**Review gate**
```
Wrote: CONSTRAINTS.md (Draft), pyproject.toml tool config, scripts/check.sh, check_size.py,
floor_guard.sh/.py, red_check.py, vulture_whitelist.py, scripts/hooks/*.sh, .claude/agents/{tester,implementer,
reviewer}.md, tests/conftest.py (didn't exist), .gitignore (+8 lines). No CI (not requested).
Proof run, after the skeleton commit: ruff --show-settings ok; check.sh gate passed in 14 s
(fresh venv; budget 90 s).

ASSUMPTIONS:
- Single package `quant`; components data < stats < portfolio; portfolio is an optional layer until M2
- Protected list: the eleven globs above
- Rule families DTZ, NPY, PD; stubs: pandas-stubs
- numpy, pandas declared now with a DEP002 exception expiring at M1 exit
- Coverage floor 0 (no code yet); Ratchet sets it at M1 exit. vulture whitelist: 0 entries
- Answers: block (default), mypy (default), measure and hold (default), 90 s (default)

Loosenings: none (first bar).
Open questions: none.

Approve the bar? Once approved I'll offer to commit it and record the plan's Base.
```

## Example: Extend at M2 kickoff

```
Bar changes for M2:
- portfolio exists now: "(quant.portfolio)" → "quant.portfolio" in the layers contract
- New dependency scipy (M2-T03): added, with EX-02 CR-25 DEP002 `scipy`, expires M2 exit
- EX-01 dropped: numpy and pandas are imported (that is a tightening)
Loosenings: EX-02 is a new exception. Approve it?
```

## Example: Ratchet at M1 exit

```
M1 measured (check.sh full): coverage 71.2%, vulture whitelist 0 entries (unchanged).
Tightenings: [tool.coverage.report] fail_under 0 → 71; EX-01 dropped (numpy and pandas are imported).
Loosenings: none. Header: **Ratcheted:** M1.
Approve? After the commit, next is build-planning Advance (dt archive). No dt base: M2 isn't planned yet.
```

## Example: Revise with a loosening

```
You asked to allow complexity 12 in stats/rmt.py.
Loosening: CR-21 ≤ 10 per function → unchanged; new exception
  EX-03 · CR-21 C901 · `src/quant/stats/rmt.py` · eigen-cleaning follows the paper's 12-branch case split · @connor · 2026-12-31
  pyproject: [tool.ruff.lint.per-file-ignores] "src/quant/stats/rmt.py" = ["C901"]
This needs your explicit yes.
```
A raised global limit (`max-complexity = 12`) would be the bigger loosening; offer the file-scoped exception first.
