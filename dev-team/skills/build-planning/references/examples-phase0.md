# Examples: contract-first Phase 0, routing, a foreign plan

`dt` means `python3 ../../scripts/dt.py`, run from the project root.

## Contract-first Phase 0 across packages (M3 after Grow)

After `architecture-design` Grow split quant into `data`, `stats`, `portfolio` and `features`, the root defines system pipeline PL-05 Research run (data → stats → features → portfolio, grown from PL-03). `pipeline-design` Grow kept PL-03 Min-variance backtest in `portfolio` as PL-05's portfolio segment (`**Part of:** PL-05`), and its Extend round added PL-06 Feature screening in `features`, also `Part of: PL-05`. M3 builds PL-06 and PL-05; PL-03 already exists.

`features.screen` is new and crosses a boundary: `portfolio` consumes it. Its contract section names the boundary:

```markdown
### features.screen: Screened feature panel
`def screen(panel: FeaturePanel, *, max_features: int = 50) -> FeaturePanel`
- **Invariants:** same index as the input; at most `max_features` columns; no column with NaN share > 5%
- **Errors:** `ValueError` if the panel is empty
- **Boundary:** portfolio · **Fixtures:** tests/contracts/features.screen/ · **Cases:** typical panel, one feature, all-NaN column dropped
- **Used by:** portfolio; PL-05, PL-06
```

Phase 0 freezes that boundary first, then builds both packages side by side, then integrates:

```markdown
## Phase 0: Spine

### M3-T01: Freeze the features.screen contract
**Package:** features · **Step:** contract · **Covers:** — · **Size:** S · **Mode:** solo
**Read:** features.screen
**Acceptance:**
- [ ] A pandera schema for the screened panel; each case's sample frame validates against it
- [ ] `portfolio`'s test support has a fake `screen` that returns the sample frames and nothing else
**Verify:** `pytest tests/contracts/features.screen` · `scripts/check.sh gate --pkg features`
**Depends on:** — · **Files likely:** packages/features/src/features/schemas.py, tests/contracts/features.screen/test_contract.py

### M3-T02: PL-06 spine with a univariate screen
**Package:** features · **Step:** PL-06 · **Covers:** FEAT-01 · **Size:** M · **Mode:** solo
**Read:** PL-06, features.screen, FEAT-01
**Acceptance:**
- [ ] `python -m features screen --smoke` runs end to end on synthetic features; its output validates against the M3-T01 schema
- [ ] PL-06 pre-build sections replaced by a `dt layout` pointer
**Verify:** `python -m features screen --smoke` · `scripts/check.sh gate --pkg features`
**Depends on:** M3-T01 · **Parallel:** G1 · **Files likely:** packages/features/src/features/__init__.py, packages/features/src/features/pipeline.py, packages/features/src/features/screen.py

### M3-T03: PL-03 on screened features, against the contract fake
**Package:** portfolio · **Step:** PL-03 · **Covers:** — · **Size:** S · **Mode:** solo
**Read:** PL-03, features.screen
**Acceptance:**
- [ ] `python -m portfolio backtest --smoke` runs end to end on every `features.screen` fixture through the fake
**Verify:** `python -m portfolio backtest --smoke` · `scripts/check.sh gate --pkg portfolio`
**Depends on:** M3-T01 · **Parallel:** G1 · **Files likely:** packages/portfolio/src/portfolio/pipeline.py, packages/portfolio/tests/support/fake_screen.py

### M3-T04: PL-05 system spine across packages
**Package:** data · **Step:** PL-05 · **Covers:** — · **Size:** S · **Mode:** solo
**Reason:** system spine
**Read:** PL-05, data.load_prices, stats.estimate_cov, features.screen
**Acceptance:**
- [ ] `python -m portfolio research --smoke` runs data → stats → features → portfolio on synthetic prices with the real `screen`, no fake
- [ ] The real `screen` output still validates against the M3-T01 schema; the smoke run is committed as PL-05's smoke test
**Verify:** `python -m portfolio research --smoke` · `scripts/check.sh gate --pkg data`
**Depends on:** M3-T02, M3-T03 · **Files likely:** packages/portfolio/src/portfolio/research.py
```

M3-T02 and M3-T03 share no file, and the only contract symbol both read is the one M3-T01 froze, which is read-only for the rest of the milestone, so both run in G1 (`dt lint`'s `parallel` check skips symbols a contract task froze). The fake in M3-T03 is allowed because it is built from the contract's schema and fixtures, and both sides test against them: M3-T02 asserts its output validates, M3-T03 consumes the fixtures. Neither spine mocks a step of its own package.

**Track:** the contract task and the system spine have no group, so they count in full (2); the chain through the rest is M3-T02 plus the longest thicken chain after it. With the old order (system spine first, then each package spine, all serial), Phase 0 alone would have counted 4.

The system spine's Package is `data`, the owner of PL-05's first step (system pipelines have no Entry). `--pkg data` scopes the gate to data and everything that depends on it, which here is every package. PL-05 is in the root, which has no pre-build sections; PL-06's spine (M3-T02) clears `features`' planned layout. Moving the code under `packages/` (the drift `pipeline-design` Grow listed) is its own solo task, omitted here.

Multi-package Verify lines scope the gate with `--pkg`. Phase 1 tasks for PL-06's null test name `null-hypothesis-testing` in `Skills:`. If it isn't installed, it's still named, `dt status` lists it under `skills_missing`, and the gate asks the user whether to install it or accept the gap.

---

## Routing milestone skills and references

A variant of M2, Structure + classical portfolios, where PL-03 runs a `remove_market` step before `estimate_cov`. `idea-refine` wrote stage S2's `**Skills:** data-analysis, null-hypothesis-testing`, and `reference-intake` assigned RF-01 (market decomposition) to S2. S2 was cut into the single milestone M2, which inherits both.

```
$ dt status --skill build-planning
mode: extend
…
milestone_skills: data-analysis, null-hypothesis-testing
milestone_references: RF-01
references_unindexed: none
references_changed: none
references_missing: none
```

Nothing is waiting for intake, so plan. `dt section RF-01` gives the entry. *Use for* names the market-removal step, *Key parts* lists `residualize`, and *Caveats* says the reference fits PCA on the whole sample. The file is over 300 lines, so the task reads one function through a selector:

```markdown
### M2-T04: Per-window market removal
**Package:** quant · **Step:** PL-03.remove_market · **Covers:** STRUCT-02 · **Size:** S · **Mode:** split
**Skills:** data-analysis
**Read:** PL-03, TC-09, stats.residualize, RF-01:residualize
**Acceptance:**
- [ ] TC-09 passes: the planted factor is removed within tolerance
- [ ] Given a walk-forward split, when `remove_market` runs, then each window's factors are fit only on returns inside that window
- [ ] PL-03 smoke test still passes
**Verify:** `pytest tests/intent/quant tests/unit/quant -k residualize` · `python -m quant.portfolio backtest --smoke` · `scripts/check.sh gate`
**Depends on:** M2-T01 · **Files likely:** src/quant/stats/residualize.py, tests/unit/quant/test_residualize.py
```

- The second bullet comes from TC-09 and the spec, not from the reference. Acceptance never says "reuse RF-01". Whether to reuse the residual arithmetic is the builder's call; `dt context M2-T04` prints the entry, the reference banner with its Caveats, and only `residualize`.
- `null-hypothesis-testing` goes on M2-T06, the claims task that tests whether the residual structure beats noise. The Scope reads `**Skills:** data-analysis (remove_market, estimate_cov), null-hypothesis-testing (claims)`.
- At the gate, `references_unrouted` and `skills_unrouted` are both `none`. Had a milestone item stayed off every task, it would need a reason under Open questions, such as `- RF-01 unrouted: the per-window fit is specified fully by TC-09; the reference adds nothing`. The user then decides at the gate.

---

## Foreign plan

```
mode: foreign
```

`tasks/plan.md` came from agent-skills' `/plan`: no `**Milestone:**` header, 5 of 9 tasks unchecked.

> `tasks/plan.md` is an agent-skills `/plan` plan with 5 unchecked tasks, which may be mid-build. I won't overwrite it. Options:
> 1. Finish it with `/build` first, then run me again. (default)
> 2. Move or discard it yourself, then run me again.
>
> Which one?

*(Turn ends. Nothing is written.)*
