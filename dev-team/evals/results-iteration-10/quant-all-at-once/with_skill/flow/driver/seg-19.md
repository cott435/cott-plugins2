# Driver segment 19 · `/dev-team:test-planning From the previous session:
<<<
Both pipelines docs are Approved again: `docs/packages/research/pipelines.md` and `docs/packages/learn/pipelines.md`.

- **Routed change:** the AD-20 change sent from `architecture-design` is closed in `docs/routes.md`. Every package now shows as current.
- **Your words:** I recorded "Add an equal-weight-winner case to the research tests" as UR-54, for the research tests. It's open, and `test-planning` will see it at the start of its run.
- **Lint:** no errors. The 4 warnings are the same as before: the research contract is over its size ceiling, the roadmap twice names a `dataviz` skill that isn't installed, and TC-34 still has its stale question.

**Commit:** the two pipelines docs, `docs/requests.md` (UR-54) and `docs/routes.md` aren't committed yet. Want me to commit them?

**Next:** `test-planning` revises the research tests:
1. Remove TC-34's open question.
2. Add the equal-weight-winner case from UR-54: equal weight has the lowest variance after costs, so the benchmark gets a null `estimator` and keeps a `best_estimator`.

After that, `learn`'s tests are still to plan from scratch.
>>>

Approved. Yes, commit them.`

- **Steps:** D744–D773 · **definition:** `/Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/plugin/dev-team/skills/test-planning/SKILL.md`
- **Units spawned here:** none

## Steps

- `D744` **USER TYPED** `/dev-team:test-planning From the previous session:
<<<
Both pipelines docs are Approved again: `docs/packages/research/pipelines.md` and `docs/packages/learn/pipelines.md`.

- **Routed change:** the AD-20 change sent from `architecture-design` is closed in `docs/routes.md`. Every package now shows as current.
- **Your words:** I recorded "Add an equal-weight-winner case to the research tests" as UR-54, for the research tests. It's open, and `test-planning` will see it at the start of its run.
- **Lint:** no errors. The 4 warnings are the same as before: the research contract is over its size ceiling, the roadmap twice names a `dataviz` skill that isn't installed, and TC-34 still has its stale question.

**Commit:** the two pipelines docs, `docs/requests.md` (UR-54) and `docs/routes.md` aren't committed yet. Want me to commit them?

**Next:** `test-planning` revises the research tests:
1. Remove TC-34's open question.
2. Add the equal-weight-winner case from UR-54: equal weight has the lowest variance after costs, so the benchmark gets a null `estimator` and keeps a `best_estimator`.

After that, `learn`'s tests are still to plan from scratch.
>>>

Approved. Yes, commit them.`
- `D745` skill loaded from `/Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/plugin/dev-team/skills/test-planning`
- `D746` **Bash** git status --short && git branch --show-current
      ↳ master
- `D747` **Bash** git log --stat -3 | head -40; grep -n "UR-54" docs/requests.md
      ↳ …[999 chars]      | 2 +- ⏎  docs/requests.md                       | 1 + ⏎  docs/routes.md                         | 2 +- ⏎  5 files changed, 6 insertions(+), 5 deletions(-) ⏎ 60:- **UR-54** tests · "Add an equal-weight-winner case to the research tests" [TC-34 / research.Benchmark (AD-20): a golden case where equal weight has the lowest variance after costs and wins the benchmark] · pipeline-design 2026-10-18
- `D748` _said:_ Those four files are already committed (in `a8c3466`), so there's nothing left to commit. On to test planning.
- `D749` **Bash** python3 ../plugin/dev-team/scripts/dt.py status --skill test-planning
      ↳ …[651 chars] ): remove it; an equal-weight winner now gives Benchmark(method="equal", estimator=None, best_estimator=<lowest-variance estimator>), which a case can check (PL-17) (from architecture-design) ⏎ requests_open: UR-54 "Add an equal-weight-winner case to the research tests" [TC-34 / research.Benchmark (AD-20): a golden case where equal weight has the lowest variance after costs and wins the benchmark]
- `D750` **Bash** cd /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/plugin/dev-team/skills/test-planning && cat references/revise.md && cat examples.md && cat ../idea-refine/references/requests.md
      ↳ …[9737 chars] 05 one predator → two (yes?); open: none. ⏎ Quote the words and the traced text side by side, so the user sees whether one does the other. ⏎ Once the spec or architecture is Approved, `dt lint` fails it for every open request it owns, and `dt next` sends the run back to its skill. ⏎ Shell cwd was reset to /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/project
- `D751` **Bash** wc -l docs/packages/research/tests.md && cat docs/packages/research/tests.md && ls -R tests/fixtures/research | head -80
      ↳ …[21898 chars] earch/TC-27: ⏎ expected.json ⏎ input.json ⏎ tests/fixtures/research/TC-28: ⏎ expected.json ⏎ input.json ⏎ tests/fixtures/research/TC-29: ⏎ expected.json ⏎ input.json ⏎ tests/fixtures/research/TC-30: ⏎ expected.json ⏎ input.json ⏎ tests/fixtures/research/TC-31: ⏎ expected.json ⏎ input.json ⏎ tests/fixtures/research/TC-32: ⏎ expected.json ⏎ input.json ⏎ tests/fixtures/research/TC-33: ⏎ expected.json
- `D752` **Bash** cat tests/fixtures/research/TC-34/*.json; echo; grep -n -i -B2 -A25 "class Benchmark\|### .*Benchmark\|select_benchmark\|load_benchmark" docs/packages/research/contract.md | head -120
      ↳ …[4016 chars] iod: int64, resid_ret: float64` ⏎ 213-- **Invariants:** `resid_ret` is the next hold period's residual return, from the previous window's loadings; a stock delisting in the hold keeps its return to the last close ⏎ 214-- **Boundary:** ftest · **Fixtures:** tests/contracts/research.ResidualTargets/ · **Cases:** two periods of the planted panel with one delisting ⏎ 215-- **Used by:** research; PL-18
- `D753` **Bash** grep -n "select_benchmark\|best_estimator\|registration order\|registered order" docs/packages/research/pipelines.md | head; python3 ../plugin/dev-team/scripts/dt.py section PORT-06; python3 ../plugin/dev-team/scripts/dt.py section COV-02; python3 ../plugin/dev-team/scripts/dt.py section AD-20 2>/dev/null | head -30
      ↳ …[2886 chars] ready beats. Use equal weight's estimator as a sentinel string: a value that names no estimator, which every consumer would have to special-case. ⏎ - **Consequences:** `benchmarks/S2.json` stores `method`, `estimator` (null for equal weight) and `best_estimator`. PL-21's forecast portfolios and PL-24's benchmark book read the new fields. ⏎ - **Probe:** none — an internal type, no external service.
- `D754` **Bash** python3 ../plugin/dev-team/scripts/dt.py next-id TC
      ↳ TC-40
- `D755` _thought:_ The four files from last session were already committed in `a8c3466`, so there's nothing new to commit. Now revising the research tests: adding `best_estimator` to TC-34, dropping its stale question, and adding TC-40 for the equal-weight-winner case.
- `D756` **Write** /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/project/tests/fixtures/research/TC-34/expected.json (9 lines)
- `D757` **Bash** mkdir -p tests/fixtures/research/TC-40 && cat > tests/fixtures/research/TC-40/input.json <<'EOF'
{
  "span": "RunRecord -> select_benchmark -> Benchmark",
  "periods": 3,
  "realized_var_x1e4": {
    "sample/min_var": 1.2,
    "sample/risk_parity": 1.3,
    "sample/hrp": 1.0,
    "shrinkage/min_var": 1.0,
    "shrinkage/risk_parity": 1.25,
    "shrinkage/hrp": 0.75,
    "denoised/min_var": 0.9,
    "denoised/risk_parity": 1.1,
    "denoised/hrp": 0.8,
    "equal": 0.7
  }
}
EOF
cat tests/fixture …[+72 chars]
      ↳ ok
- `D758` **Write** /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/project/tests/fixtures/research/TC-40/expected.json (9 lines)
- `D759` **Read** /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/project/docs/packages/research/tests.md limit=3
      ↳ 3 lines
- `D760` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/project/docs/packages/research/tests.md | old: '**Status:** Approved ·' | new: '**Status:** Draft ·'
- `D761` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/project/docs/packages/research/tests.md | old: 'TC-34 (RunRecord → select_benchmark → Benchmark), TC-35' | new: 'TC-34 (RunRecord → select_benchmark → Benchmark), TC-40 (RunRecord → select_benc'
- `D762` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/project/docs/packages/research/tests.md | old: '**Expected:** `Benchmark.method == "hrp"`, `estimator == "denoised"`, `realized_' | new: '**Expected:** `Benchmark.method == "hrp"`, `estimator == "denoised"`, `best_esti'
- `D763` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/project/docs/packages/research/tests.md | old: '- TC-34: `Benchmark.estimator` is `Literal["sample", "shrinkage", "denoised"]`, ' | new: ''
- `D764` **Bash** sed -i '' 's/DENO-04 and HARN-07.s finished-run recording beyond TC-33\./DENO-04, HARN-07'"'"'s finished-run recording beyond TC-33, and `select_benchmark`'"'"'s tie to the earlier registered candidate (AD-20)./' docs/packages/research/tests.md && grep -n "Uncovered" docs/packages/research/tests.md && python3 ../plugin/dev-team/scripts/dt.py request trace UR-54 TC-40 && python3 ../plugin/dev-team/scripts/dt.py lint docs/packages/research/tests.md; python3 ../plugin/dev-team/scripts/dt.py status  …[+80 chars]
      ↳ …[596 chars] lines_no_golden: none ⏎ cases_no_source: none ⏎ cases_no_tolerance: none ⏎ fixtures_missing: none ⏎ fixtures_orphan: none ⏎ routed_changes: TC-34's open question is answered (UR-52, AD-20): remove it; an equal-weight winner now gives Benchmark(method="equal", estimator=None, best_estimator=<lowest-variance estimator>), which a case can check (PL-17) (from architecture-design) ⏎ requests_open: none
- `D765` _said:_ I've revised the research tests and set them back to Draft. Lint is clean: 0 errors, 0 warnings, and the stale TC-34 warning is gone. Every gap key in `dt status` is empty. ⏎ ## Revise TC-34 (PL-17 · PORT-06, COV-02) ⏎ | | `expected.json` | ⏎ |---|---| ⏎ | old | `{"method": "hrp", "estimator": "denoised", "realized_var": 0.8e-4, "writes": "benchmarks/S2.json", "estimator_rank_per_method": ["denoised","shrinkage","sample"], "tol": 1e-15}` | ⏎ | new | the same, plus `"best_estimator": "denoised"` | ⏎ - **Source of the new field:** AD-20 and the `research.Benchmark` invariant: `best_estimator` eq …[+2771 chars]
- `D766` HOOK SessionStart:resume said: milestone: none (no tasks/plan.md) ⏎ draft (waiting for approval): docs/packages/research/tests.md ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/plugin/dev-team/scripts/dt
- `D767` **USER:** Approved. TC-34's new best_estimator and TC-40's expected outputs are fine.
- `D768` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/project/docs/packages/research/tests.md | old: '**Status:** Draft ·' | new: '**Status:** Approved ·'
- `D769` **Bash** python3 ../plugin/dev-team/scripts/dt.py route --done test-planning && python3 ../plugin/dev-team/scripts/dt.py lint docs/packages/research/tests.md && python3 ../plugin/dev-team/scripts/dt.py status --skill test-planning | grep -E "packages|routed|requests_open" && git status --short
      ↳ ticked: 1 change(s) routed to test-planning ⏎ 0 errors, 0 warnings ⏎ packages: learn=new, qdata=current, research=current, server=current, web=current ⏎ routed_changes: none ⏎ requests_open: none ⏎  M docs/packages/research/tests.md ⏎  M docs/routes.md
- `D770` **Bash** git status --short --ignored tests/fixtures/research | head; git check-ignore -v tests/fixtures/research/TC-40/expected.json  ❌ ERROR
      ↳ Exit code 1
- `D771` **Bash** ls tests/fixtures/research/TC-40; cat tests/fixtures/research/TC-34/expected.json; git log --oneline -2 -- tests/fixtures/research/TC-40
      ↳ expected.json ⏎ input.json ⏎ { ⏎   "method": "hrp", ⏎   "estimator": "denoised", ⏎   "best_estimator": "denoised", ⏎   "realized_var": 0.8e-4, ⏎   "writes": "benchmarks/S2.json", ⏎   "estimator_rank_per_method": ["denoised", "shrinkage", "sample"], ⏎   "tol": 1e-15 ⏎ } ⏎ 2eddf57 turn 59
- `D772` _said:_ The research tests are **Approved** again, dated 2026-10-18. ⏎ - **Routed change:** the AD-20 change from `architecture-design`, which TC-34 depended on, is closed in `docs/routes.md`. Every package except `learn` now shows as current. ⏎ - **Your words:** UR-54 now traces to TC-40, and no requests are open. ⏎ - **Lint:** 0 errors, 0 warnings. ⏎ **Commit:** the TC-34 and TC-40 fixtures were already committed in `2eddf57` ("turn 59"). Two files are still uncommitted: `docs/packages/research/tests.md` (now Approved) and `docs/routes.md`. Want me to commit them? ⏎ **Next:** `learn` has no `tests.m …[+91 chars]
- `D773` HOOK SessionStart:startup said: milestone: none (no tasks/plan.md) ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/plugin/dev-team/scripts/dt
