# Example: routing milestone skills and references

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

Nothing is waiting for intake, so plan. `dt section RF-01` gives the entry. *Use for* names the market-removal step, *Key parts* lists `residualize`, and *Caveats* says the reference fits PCA on the whole sample. The file is over 300 lines, so the task, which thickens the `remove_market` spine M2-T03, reads one function through a selector:

```markdown
### M2-T09: Per-window market removal
**Package:** quant · **Step:** PL-03.remove_market · **Kind:** thicken · **Covers:** STRUCT-02 · **Size:** XS · **Mode:** split
**Skills:** data-analysis
**Read:** PL-03, TC-09, stats.residualize, RF-01:residualize
**Acceptance:**
- [ ] TC-09 passes: the planted factor is removed within tolerance
- [ ] Given a walk-forward split, when `remove_market` runs, then each window's factors are fit only on returns inside that window
**Verify:** `pytest tests/intent/quant tests/unit/quant -k residualize` · `scripts/check.sh gate`
**Depends on:** M2-T03 · **Writes:** src/quant/stats/residualize.py, tests/intent/quant/test_residualize.py, tests/unit/quant/test_residualize.py
```

- The second bullet comes from TC-09 and the spec, not from the reference. Acceptance never says "reuse RF-01". Whether to reuse the residual arithmetic is the builder's call; `dt context M2-T09` prints the entry, the reference banner with its Caveats, and only `residualize`.
- `null-hypothesis-testing` goes on M2-T10, the claims task that tests whether the residual structure beats noise. The Scope reads `**Skills:** data-analysis (remove_market, estimate_cov), null-hypothesis-testing (claims)`.
- At the gate, `references_unrouted` and `skills_unrouted` are both `none`. Had a milestone item stayed off every task, it would need a reason under Open questions, such as `- RF-01 unrouted: the per-window fit is specified fully by TC-09; the reference adds nothing`. The user then decides at the gate.
