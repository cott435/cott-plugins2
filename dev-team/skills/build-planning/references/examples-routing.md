# Example: routing milestone skills and references

A variant of M2, Seasonality & baselines, where PL-03 runs a `remove_seasonality` step before `forecast_baseline`. `idea-refine` wrote stage S2's `**Skills:** profile-report, significance-check`, and `reference-intake` assigned RF-01 (`seasonal_profile.py`) to S2. S2 was cut into the single milestone M2, which inherits both.

```
$ dt status --skill build-planning
mode: extend
…
milestone_skills: profile-report, significance-check
milestone_references: RF-01
references_unindexed: none
references_changed: none
references_missing: none
```

Nothing is waiting for intake, so plan. `dt section RF-01` gives the entry. *Use for* names the seasonal-removal step, *Key parts* lists `deseasonalize`, and *Caveats* says the reference fits the seasonal profile on the whole sample. The file is over 300 lines, so the task, which thickens the `remove_seasonality` spine M2-T02, reads one function through a selector:

```markdown
### M2-T04: Per-window seasonal removal
**Package:** gridload · **Step:** PL-03.remove_seasonality · **Kind:** thicken · **Covers:** SEAS-02 · **Size:** XS · **Mode:** split
**Skills:** profile-report
**Read:** PL-03, TC-09, profile.deseasonalize, RF-01:deseasonalize
**Acceptance:**
- [ ] TC-09 passes: the planted daily sine is removed within tolerance
- [ ] Given a walk-forward split, when `remove_seasonality` runs, then each window's profile is fit only on load inside that window
**Verify:** `pytest tests/intent/gridload tests/unit/gridload -k deseasonalize` · `scripts/check.sh gate`
**Depends on:** M2-T02 · **Writes:** src/gridload/profile/deseasonalize.py, tests/intent/gridload/test_deseasonalize.py, tests/unit/gridload/test_deseasonalize.py
```

- The second bullet comes from TC-09 and the spec, not from the reference. Acceptance never says "reuse RF-01". Whether to reuse the removal arithmetic is the builder's call; `dt context M2-T04` prints the entry, the reference banner with its Caveats, and only `deseasonalize`.
- `significance-check` goes on M2-T05, the claims task that tests whether the residual structure beats noise. The Scope reads `**Skills:** profile-report (remove_seasonality, forecast_baseline), significance-check (claims)`.
- At the gate, `references_unrouted` and `skills_unrouted` are both `none`. Had a milestone item stayed off every task, it would need a reason under Open questions, such as `- RF-01 unrouted: the per-window fit is specified fully by TC-09; the reference adds nothing`. The user then decides at the gate.
