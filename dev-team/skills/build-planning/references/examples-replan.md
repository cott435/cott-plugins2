# Example: Replan — MP cleaning needs shrinkage first

**State:** mid-M1 (the plan of `examples-phase0.md`). The build paused M1-T11:
```markdown
**Blocked:** TC-02 fails on sample covariance when T/N < 5; cleaning needs the shrinkage estimate as input
```
```
mode: replan
blocked_tasks: M1-T11
```

No step changed (PL-02 already runs `estimate_cov` before `clean_eigen`), so no `pipeline-design` Revise is needed; only the graph changes. Had a step changed, `pipeline-design` Revise would run first: while `pipelines.md` is Draft, `dt status` says `blocked` (`waiting for docs/packages/quant/pipelines.md approval`); once it's re-approved with a later `Last updated` than the plan, it says `replan` with `changed_since_plan: docs/packages/quant/pipelines.md`.

**Edits:**
- Move the M1-T12 section above M1-T11. IDs stay; plan position sets the order, and `dt lint` checks `Depends on` by position.
- M1-T11: `**Depends on:** M1-T05, M1-T12`; remove the `Blocked` line. Its `Writes:` and M1-T12's stay disjoint.
- The graph row that let them run side by side, `| M1-T11 MP cleaning | M1-T12 shrinkage | data | stats.Cov sample (M1-T01): … |`, becomes `| M1-T11 MP cleaning | M1-T12 shrinkage | order | none: TC-02 needs the shrinkage estimate as cleaning's input |`. The critical path grows from 4 to 5 (M1-T01 → M1-T04 → M1-T12 → M1-T11 → M1-T14).
- M1-T11 gains no new bullet: TC-02 already covers it.
- Reorder `todo.md` to match.
- `## Replan notes`: `- 2026-10-28: M1-T11 now waits on M1-T12 (MP cleaning needs the shrinkage estimate; TC-02 failed on sample cov); dropped none`
- Status → Draft.

**Gate message:** what moved and why, the new edge and the longer critical path, "dropped none". *(Turn ends.)*

**A drop looks like this.** It's listed for approval first ("Drop M1-T13? PCA is already checked by TC-03 in M1-T14's run. Default: keep"). Only after an unambiguous yes, remove the section, its graph rows and todo line, and add under Replan notes:
```markdown
- ~~M1-T13: Planted-factor PCA check~~ Retired 2026-10-28: TC-03 now runs in M1-T14
```
`dt next-id` counts the retired ID, so it's never reused, and `dt lint` flags any `Depends on` still pointing at it.
