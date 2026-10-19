# Driver segment 18 · `/dev-team:pipeline-design From the previous session:
<<<
us:** `docs/architecture.md`, `docs/packages/research/architecture.md` and `docs/packages/research/contract.md` are back to Approved. AD-20 is now Accepted.
- **Your words:** I recorded your `best_estimator` confirmation as UR-53, linked to AD-20 and `research.Benchmark`. The test-planning request about the benchmark is marked done, and no requests are open.
- **Lint:** no errors. There are 5 warnings:
  - The three from before: the research contract is over the size ceiling, and the roadmap twice names a `dataviz` skill that isn't installed.
  - Two new ones, which go away when the next steps run. They're open questions that now look stale because their requests are done:
    - `docs/packages/learn/pipelines.md:194`: the `KeyError` note, already queued for `pipeline-design`.
    - `docs/packages/research/tests.md:119`: TC-34's question, sent to `test-planning` to remove.

**Commit:** the three docs, plus `docs/requests.md` (UR-52, UR-53) and `docs/routes.md` (the closed request and two new ones), aren't committed yet. Want me to commit them?

**Next:**
1. `pipeline-design`:
   - PL-17's `select_benchmark` ranks all ten candidates.
   - PL-21's forecast portfolios use `best_estimator`.
   - PL-24's benchmark book holds equal weight when `method == "equal"`.
   - Remove the stale `KeyError` note at `learn/pipelines.md:194`.
2. `test-planning`:
   - Remove TC-34's open question and, if you want one, add an equal-weight-winner case.
   - Then `learn`, which is still in New mode.
>>>

Approved. Yes, commit them.`

- **Steps:** D726–D743 · **definition:** `/Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/plugin/dev-team/skills/pipeline-design/SKILL.md`
- **Units spawned here:** none

## Steps

- `D726` **USER TYPED** `/dev-team:pipeline-design From the previous session:
<<<
us:** `docs/architecture.md`, `docs/packages/research/architecture.md` and `docs/packages/research/contract.md` are back to Approved. AD-20 is now Accepted.
- **Your words:** I recorded your `best_estimator` confirmation as UR-53, linked to AD-20 and `research.Benchmark`. The test-planning request about the benchmark is marked done, and no requests are open.
- **Lint:** no errors. There are 5 warnings:
  - The three from before: the research contract is over the size ceiling, and the roadmap twice names a `dataviz` skill that isn't installed.
  - Two new ones, which go away when the next steps run. They're open questions that now look stale because their requests are done:
    - `docs/packages/learn/pipelines.md:194`: the `KeyError` note, already queued for `pipeline-design`.
    - `docs/packages/research/tests.md:119`: TC-34's question, sent to `test-planning` to remove.

**Commit:** the three docs, plus `docs/requests.md` (UR-52, UR-53) and `docs/routes.md` (the closed request and two new ones), aren't committed yet. Want me to commit them?

**Next:**
1. `pipeline-design`:
   - PL-17's `select_benchmark` ranks all ten candidates.
   - PL-21's forecast portfolios use `best_estimator`.
   - PL-24's benchmark book holds equal weight when `method == "equal"`.
   - Remove the stale `KeyError` note at `learn/pipelines.md:194`.
2. `test-planning`:
   - Remove TC-34's open question and, if you want one, add an equal-weight-winner case.
   - Then `learn`, which is still in New mode.
>>>

Approved. Yes, commit them.`
- `D727` skill loaded from `/Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/plugin/dev-team/skills/pipeline-design`
- `D728` **Bash** git status --short && git log --oneline -3
      ↳ a08cbd6 turn 56 ⏎ 361ba5f turn 55 ⏎ 3a16136 turn 54
- `D729` **Bash** git show --stat HEAD | head -20 && python3 ../plugin/dev-team/scripts/dt.py status --skill pipeline-design
      ↳ …[956 chars] too (AD-20): select_benchmark ranks all ten candidates on mean realized variance after costs, writing estimator null for equal weight and best_estimator; fport_claim and fport_weights take the covariance from Benchmark.best_estimator, not estimator; BenchmarkStrategy builds equal weight with no covariance when method == "equal" (PL-17, PL-21, PL-24) (from architecture-design) ⏎ requests_open: none
- `D730` **Bash** cd /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/plugin/dev-team/skills/pipeline-design && cat references/revise.md && grep -n "routed\|route" ../../scripts/dt.py | head -5
      ↳ …[3338 chars] ⏎ - **The code changes** when it broke a rule: logic in the entry, a step owned by two components, a registry with no AD. Leave the doc, and list the fix for `build-planning` Replan. ⏎ Never rewrite the table to match code that breaks a readability rule. ⏎ 37:    "route": "route", ⏎ Shell cwd was reset to /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/project
- `D731` **Bash** cd /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill && cat plugin/dev-team/skills/pipeline-design/references/steps.md | sed -n '/Changing a step table/,/^## [^C]/p'; cd project; grep -n "PL-17\|PL-21\|PL-24\|select_benchmark\|best_estimator\|fport_claim\|fport_weights\|BenchmarkStrategy\|KeyError\|^Status\|^\*\*Status\|^## " docs/packages/*/pipelines.md
      ↳ …[7673 chars] ch and control runs ⏎ docs/packages/web/pipelines.md:31:## PL-16: Explore the dataset ⏎ docs/packages/web/pipelines.md:68:## PL-26: Results explorer ⏎ docs/packages/web/pipelines.md:98:## PL-27: Paper books ⏎ docs/packages/web/pipelines.md:125:## Planned layout (pre-build — removed by spine task) ⏎ docs/packages/web/pipelines.md:139:## Open questions ⏎ docs/packages/web/pipelines.md:142:## Retired
- `D732` _said:_ Let me read the contract's `Benchmark` and the affected sections.
- `D733` **Bash** grep -n -B2 -A14 "class Benchmark\|Benchmark\b.*dataclass\|^### .*Benchmark" docs/packages/research/contract.md | head -60; grep -n "AD-20" docs/architecture.md docs/packages/research/architecture.md | head; sed -n 1,4p docs/packages/research/pipelines.md docs/packages/learn/pipelines.md; sed -n 5,42p docs/packages/research/pipelines.md
      ↳ …[7333 chars] ⏎     loader = open_loader(as_of) ⏎     handle = register(compare_registration(loader, settings())) ⏎     covs = window_covariances(handle, remove_factors(handle)) ⏎     weights = target_weights(covs, Limits()) ⏎     results = hold_and_record(handle, weights) ⏎     verdict = decide(handle, results) ⏎     return select_benchmark(finish_comparison(handle, verdict, analyse_comparison(results))) ⏎ ```
- `D734` **Bash** sed -n 58,94p docs/packages/learn/pipelines.md; sed -n 147,174p docs/packages/learn/pipelines.md; grep -n -A4 "### research.estimate_covariances\|### research.build_portfolio" docs/packages/research/contract.md
      ↳ …[7162 chars] ts` ⏎ 165-- **Invariants:** `mean_var` needs `mu` (used by FPORT); risk contributions equal within 1% for `risk_parity` ⏎ 166-- **Errors:** `Infeasible` when the limits can't be met; the caller keeps the previous weights ⏎ 167-- **Boundary:** learn · **Fixtures:** tests/contracts/research.build_portfolio/ · **Cases:** a two-asset risk parity, a block-diagonal HRP, an infeasible 5% cap on 10 stocks
- `D735` **Bash** python3 - <<'EOF'
from pathlib import Path
r = Path("docs/packages/research/pipelines.md"); t = r.read_text()
old = "| lowest out-of-sample variance after costs; writes `benchmarks/S2.json` | PORT-06 |"
new = "| all ten candidates (9 estimator × method, plus equal weight) ranked on mean realised variance after costs, ties to the earlier registered; `estimator` null for equal weight; `best_estimator` from the lowest-variance candidate that has one (AD-20); writes `benchmarks/S2.json` | PORT-06 |" …[+1610 chars]
      ↳ …[861 chars] rch/tests.md:119: closed-open-question routed to architecture-design, whose routed changes are all done (docs/routes.md): drop the question or say what is still open ⏎ docs/roadmap.md:16: roadmap-skill S1 Skills names dataviz: not installed (.claude/skills or the plugin) ⏎ docs/roadmap.md:20: roadmap-skill S2 Skills names dataviz: not installed (.claude/skills or the plugin) ⏎ 0 errors, 6 warnings
- `D736` **Bash** python3 ../plugin/dev-team/scripts/dt.py explain --write 2>&1 | tail -3; python3 ../plugin/dev-team/scripts/dt.py lint 2>&1 | tail -1; ls tasks 2>/dev/null; git status --short
      ↳ docs/explained/server.md ⏎ docs/explained/system.md ⏎ docs/explained/web.md ⏎ 0 errors, 4 warnings ⏎  M docs/explained/learn.md ⏎  M docs/explained/research.md ⏎  M docs/packages/learn/pipelines.md ⏎  M docs/packages/research/pipelines.md
- `D737` _said:_ The files you asked me to commit (the three architecture docs, `docs/requests.md`, `docs/routes.md`) are already in git. They went into commit `a08cbd6` ("turn 56"), so there was nothing left to commit. ⏎ I then started the `pipeline-design` revision from AD-20. It's waiting for your approval. ⏎ ## What changed ⏎ - **PL-17 Classical risk comparison** (`python -m research compare`, 18 steps): step 18 `select_benchmark` now ranks all ten candidates on mean realised variance after costs. That's the 9 estimator × method combinations plus equal weight, with ties going to the earlier registered cand …[+2343 chars]
- `D738` HOOK SessionStart:resume said: milestone: none (no tasks/plan.md) ⏎ draft (waiting for approval): docs/packages/learn/pipelines.md, docs/packages/research/pipelines.md ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/plugin/dev-team/scripts/dt
- `D739` **USER:** Approved. Add an equal-weight-winner case to the research tests when you get there.
- `D740` **Bash** cd /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill && cat plugin/dev-team/skills/idea-refine/references/requests.md; tail -5 project/docs/requests.md
      ↳ …[6002 chars] mark ⏎ - **UR-53** architecture · "Confirming best_estimator: yes, keep it." [AD-20 assumption 1: Benchmark.best_estimator, always set, the estimator of the lowest-variance candidate that has one (FPORT-01's covariance)] · architecture-design 2026-10-18 → AD-20, research.Benchmark ⏎ Shell cwd was reset to /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/project
- `D741` **Bash** python3 ../plugin/dev-team/scripts/dt.py request add tests "Add an equal-weight-winner case to the research tests" --skill pipeline-design --about "TC-34 / research.Benchmark (AD-20): a golden case where equal weight has the lowest variance after costs and wins the benchmark" && sed -i '' 's/\*\*Status:\*\* Draft · \*\*Last updated:\*\* 2026-10-18/**Status:** Approved · **Last updated:** 2026-10-18/' docs/packages/research/pipelines.md docs/packages/learn/pipelines.md && python3 ../plugin/dev-te …[+305 chars]
      ↳ UR-54 tests: "Add an equal-weight-winner case to the research tests" ⏎ ticked: 1 change(s) routed to pipeline-design ⏎ mode: current ⏎ packages: learn=current, qdata=current, research=current, server=current, web=current ⏎ routed_changes: none ⏎ 0 errors, 4 warnings ⏎  M docs/packages/learn/pipelines.md ⏎  M docs/packages/research/pipelines.md ⏎  M docs/requests.md ⏎  M docs/routes.md
- `D742` _said:_ Both pipelines docs are Approved again: `docs/packages/research/pipelines.md` and `docs/packages/learn/pipelines.md`. ⏎ - **Routed change:** the AD-20 change sent from `architecture-design` is closed in `docs/routes.md`. Every package now shows as current. ⏎ - **Your words:** I recorded "Add an equal-weight-winner case to the research tests" as UR-54, for the research tests. It's open, and `test-planning` will see it at the start of its run. ⏎ - **Lint:** no errors. The 4 warnings are the same as before: the research contract is over its size ceiling, the roadmap twice names a `dataviz` skill  …[+517 chars]
- `D743` HOOK SessionStart:startup said: milestone: none (no tasks/plan.md) ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-all-at-once/with_skill/plugin/dev-team/scripts/dt
