# New

Read when `dt status --skill build-setup` reports `new` (no `CONSTRAINTS.md`). Values come from `derive.md`; the run ends at the Review Gate in `../SKILL.md`.

```
PRECHECK → DETECT → 4 QUESTIONS → GENERATE → [commit yes] → PROVE → REVIEW GATE
   → (next turn) [approved] → [commit yes] → dt base
```

## Steps

**1. Precheck.** `command -v uv jq`; if either is missing, stop and ask the user to install it (check.sh and the hooks need both). A `tasks/plan.md` without a dev-team header (agent-skills `/plan`) means stop and ask.

**2. Detect, don't ask.** Read, and report in two lines: shape, ids, dependency rules and stack ADs (`docs/architecture.md`); module layout (`pipelines.md`); tests and fixtures; the milestone's dependencies (`tasks/plan.md`); Python version; existing config, CI and `.claude/`.

**3. Four questions**, one at a time, with these defaults: **block or warn mid-task?** (block on the floor and gate; `full` findings become review findings; "warn" adds `--warn` to the Stop hooks); **type gate?** (mypy strict gates, pyright in `full`); **targets or measure-and-hold?** (measure and hold); **slowest gate tolerated?** (90 s; no limit for `full`). Mention CI once; write it only if asked.

**4. Generate.** Derive every value per `derive.md` and fill the templates; `grep -rn '{{[a-z_]*}}'` over the written files must print nothing. `chmod +x scripts/*.sh scripts/hooks/*.sh`; append the `.gitignore` lines. `uv lock && uv sync`, then write the vulture whitelist: the template header plus `uv run --frozen vulture --make-whitelist`, and count `duplicates_today` with `check.sh`'s pylint line (`tools/pylint.md`). Never edit `check.sh` steps or hook commands by hand.

**5. Prove.** Ask to commit the bar skeleton (default yes): the protected-path diff needs a commit. On a yes, commit and `git update-ref refs/worktree/checks-base HEAD`. Run `uv run --frozen ruff check --show-settings >/dev/null` and `time bash scripts/check.sh gate`; fix the config, never the check, until it passes within budget. Headless: don't commit; run the gate, report the protected-path step as expected to fail, leave Draft.

## Example: GridLoad, single package

Architecture: `gridload` with components `data` (depends on nothing), `profile` (→ data), `reserve` (→ profile, data); pandas and NumPy (AD-02); `reserve` arrives in M2. Plan M1 declares `numpy` and `pandas`.

**Values**
```bash
PROTECTED=('tests/intent/**' 'tests/fixtures/**' 'tests/conftest.py' 'pyproject.toml' 'uv.lock' 'CONSTRAINTS.md' 'scripts/**' '.claude/agents/**' '.claude/settings.json' 'references/**' 'probes/**' 'tests/contracts/**')
pkg_scope() {
  case "$1" in
    data) echo "data profile reserve" ;;
    profile) echo "profile reserve" ;;
    reserve) echo "reserve" ;;
    *) return 1 ;;
  esac
}
```
```toml
[[tool.importlinter.contracts]]
name = "Layers: reserve > profile > data"
type = "layers"
layers = ["(gridload.reserve)", "gridload.profile", "gridload.data"]

[tool.deptry.per_rule_ignores]
DEP002 = ["numpy", "pandas"]
```
```markdown
## Boundaries (generated from architecture — do not edit)
- `gridload.data` imports nothing first-party · `gridload.profile` → data · `gridload.reserve` → profile, data

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
reviewer}.md, .claude/settings.json, tests/conftest.py (didn't exist), .gitignore (+12 lines). No CI (not requested).
Proof run, after the skeleton commit: ruff --show-settings ok; check.sh gate passed in 14 s
(fresh venv; budget 90 s).

ASSUMPTIONS:
- Single package `gridload`; components data < profile < reserve; reserve is an optional layer until M2
- Protected list: the twelve globs above
- Rule families DTZ, NPY, PD; stubs: pandas-stubs
- numpy, pandas declared now with a DEP002 exception expiring at M1 exit
- Coverage floor 0 (no code yet); Ratchet sets it at M1 exit. vulture whitelist: 0 entries
- Answers: block (default), mypy (default), measure and hold (default), 90 s (default)

Loosenings: none (first bar).
Open questions: none.

Approve the bar? Once approved I'll offer to commit it and record the plan's Base.
```
