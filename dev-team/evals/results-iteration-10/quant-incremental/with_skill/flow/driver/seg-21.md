# Driver segment 21 · `/dev-team:reference-intake From the previous session:
<<<
* [A new Python package with its own CLI that reads from `eqdata` and writes a report you can open in the existing app. The brief's Not Doing currently rules out research views in the app, so the alternative is a report file outside it.]

**Variations considered:**
- **Detoning only for HRP clustering:** keeps the full covariance for min-variance and risk parity.
- **A factor-model covariance (k PCs + diagonal residuals) as a fourth estimator:** a cheap, standard competitor to denoising.
- **Ledoit–Wolf with two shrinkage targets (identity vs constant correlation):** the target choice often matters more than shrinkage vs denoising.
- **Denoise, then shrink:** the two methods combine.
- **Estimator stability first:** compare estimators before any portfolio, using eigenvector stability and condition number across windows.
- **The simplest useful version:** min-variance only, three estimators, one window length. The allocators come after that.
- **Window sensitivity:** run 252, 504 and 1008 days, since q drives everything here.

**Brief fit check.** This serves the brief's goals only indirectly, so it needs no new goal; the stage is its roadmap row. But two lines of the brief go stale: Constraints says "Only the first stage (data) is decided", and Not Doing says "Signals, backtests or models: later stages". This stage is a variance-only backtest. I'd update Constraints to name S2, and narrow Not Doing to "return prediction, signals and ML models". **OK to make those two edits?**
>>>

RF-01 goes to S2 once it's added (yes). Approve the index. Q1: yes, trailing 504 days, monthly rebalance, walk-forward from 2000, over that day's members. Q2: MP edge, with fixed k=1 reported next to it. Q3: long-only, fully invested, turnover reported, no cost model. Q4: yes, the table with 1/N and sample-covariance min-variance as baselines, plus the chance test with multiple-comparison correction. Q5: new Python package with its own CLI reading from eqdata, writing a report file outside the app. Your pushback on keeping the full covariance for weights and using detoned correlation only for clustering is fine. Yes, make the two brief edits. Also add the factor-model estimator and Ledoit-Wolf with both targets as estimators, and run window sensitivity at 252, 504 and 1008.`

- **Steps:** D969–D974 · **definition:** `/Users/connorott/plugins/dev-team-workspace/iteration-10/quant-incremental/with_skill/plugin/dev-team/skills/reference-intake/SKILL.md`
- **Units spawned here:** none

## Steps

- `D969` **USER TYPED** `/dev-team:reference-intake From the previous session:
<<<
* [A new Python package with its own CLI that reads from `eqdata` and writes a report you can open in the existing app. The brief's Not Doing currently rules out research views in the app, so the alternative is a report file outside it.]

**Variations considered:**
- **Detoning only for HRP clustering:** keeps the full covariance for min-variance and risk parity.
- **A factor-model covariance (k PCs + diagonal residuals) as a fourth estimator:** a cheap, standard competitor to denoising.
- **Ledoit–Wolf with two shrinkage targets (identity vs constant correlation):** the target choice often matters more than shrinkage vs denoising.
- **Denoise, then shrink:** the two methods combine.
- **Estimator stability first:** compare estimators before any portfolio, using eigenvector stability and condition number across windows.
- **The simplest useful version:** min-variance only, three estimators, one window length. The allocators come after that.
- **Window sensitivity:** run 252, 504 and 1008 days, since q drives everything here.

**Brief fit check.** This serves the brief's goals only indirectly, so it needs no new goal; the stage is its roadmap row. But two lines of the brief go stale: Constraints says "Only the first stage (data) is decided", and Not Doing says "Signals, backtests or models: later stages". This stage is a variance-only backtest. I'd update Constraints to name S2, and narrow Not Doing to "return prediction, signals and ML models". **OK to make those two edits?**
>>>

RF-01 goes to S2 once it's added (yes). Approve the index. Q1: yes, trailing 504 days, monthly rebalance, walk-forward from 2000, over that day's members. Q2: MP edge, with fixed k=1 reported next to it. Q3: long-only, fully invested, turnover reported, no cost model. Q4: yes, the table with 1/N and sample-covariance min-variance as baselines, plus the chance test with multiple-comparison correction. Q5: new Python package with its own CLI reading from eqdata, writing a report file outside the app. Your pushback on keeping the full covariance for weights and using detoned correlation only for clustering is fine. Yes, make the two brief edits. Also add the factor-model estimator and Ledoit-Wolf with both targets as estimators, and run window sensitivity at 252, 504 and 1008.`
- `D970` skill loaded from `/Users/connorott/plugins/dev-team-workspace/iteration-10/quant-incremental/with_skill/plugin/dev-team/skills/reference-intake`
- `D971` **Bash** python3 ../plugin/dev-team/scripts/dt.py status --skill reference-intake; echo ---; cat docs/references.md; echo ---; grep -n "^## " docs/roadmap.md; ls docs docs/ideas 2>/dev/null  ❌ ERROR
      ↳ Exit code 1 ⏎ skill: reference-intake ⏎ mode: current ⏎ docs: brief Accepted · spec Approved · architecture Approved (Multi-package) · roadmap ok · plan M1 Approved · constraints Approved ⏎ next ids: AD-14 PL-12 TC-34 S2 M4 M1-T36 ⏎ references_unindexed: none ⏎ references_changed: none ⏎ references_missing: none ⏎ index: Draft ⏎ files_to_read: none ⏎ outline_first: none ⏎ next_id: RF-02 ⏎ milestones: S1 Trusted daily data, M1 Walking skeleton, M2 Validation and findings, M3 Live runs and EDA report ⏎ --- ⏎ # S&P 500 research data — References ⏎ **Status:** Draft · **Last updated:** 2026-10-18 ⏎ ### RF-01: PCA market-mode removal ⏎ **File:** `references/market_decomposition.py` · **Hash:** b3993e95 · **Kind:** code · **Milestones:** — ⏎ - **Purpose:** removes the top-k principal components  …[+1485 chars]
- `D972` **Bash** sed -i '' 's/^\*\*Status:\*\* Draft · \*\*Last updated:\*\* 2026-10-18/**Status:** Approved · **Last updated:** 2026-10-18/' docs/references.md && head -3 docs/references.md && python3 ../plugin/dev-team/scripts/dt.py lint docs/references.md; git status --short
      ↳ # S&P 500 research data — References ⏎ **Status:** Approved · **Last updated:** 2026-10-18 ⏎ 0 errors, 0 warnings ⏎  M docs/references.md
- `D973` _said:_ I approved the index. `docs/references.md` is now **Status: Approved** (2026-10-18), and `dt lint` reports 0 errors and 0 warnings. ⏎ **RF-01 milestone:** I've kept it as `—` for now. S2 doesn't have a roadmap row yet, and this skill can't point an entry at a stage that doesn't exist. When idea-refine adds S2, it will offer to set RF-01's milestone to S2, which matches your "yes". ⏎ **Commit:** only `docs/references.md` has changed (`references/market_decomposition.py` is already tracked). Do you want me to commit it? ⏎ **Next step: idea-refine.** The rest of your message answers idea-refine's …[+1296 chars]
- `D974` HOOK SessionStart:startup said: milestone: M1 Walking skeleton · plan Approved ⏎ progress: 0/35 · next: M1-T01 M1 interface ⏎ blocked: none ⏎ probes: 3 waiting → api-probe ⏎ requests: 5 not honoured → spec-writing, architecture-design ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-10/quant-incremental/with_skill/plugin/dev-team/scripts/dt
