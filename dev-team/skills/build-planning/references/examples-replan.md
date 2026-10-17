# Example: Replan — the spectrum needs the Fourier fit first

**State:** mid-M1 (the plan of `examples-phase0.md`). The build paused M1-T11:
```markdown
**Blocked:** TC-02 fails on the hour-of-week means profile when T < 5 weeks; the spectrum needs the Fourier profile as input
```
```
mode: replan
blocked_tasks: M1-T11
```

No step changed (PL-02 already runs `fit_seasonality` before `spectrum`), so no `pipeline-design` Revise is needed; only the graph changes. Had a step changed, `pipeline-design` Revise would run first: while `pipelines.md` is Draft, `dt status` says `blocked` (`waiting for docs/packages/gridload/pipelines.md approval`); once it's re-approved with a later `Last updated` than the plan, it says `replan` with `changed_since_plan: docs/packages/gridload/pipelines.md`.

**Edits:**
- Move the M1-T12 section above M1-T11. IDs stay; plan position sets the order, and `dt lint` checks `Depends on` by position.
- M1-T11: `**Depends on:** M1-T05, M1-T12`; remove the `Blocked` line. Its `Writes:` and M1-T12's stay disjoint.
- The graph row that let them run side by side, `| M1-T11 LS amplitudes | M1-T12 Fourier seasonality | data | profile.Profile sample (M1-T01): … |`, becomes `| M1-T11 LS amplitudes | M1-T12 Fourier seasonality | order | none: TC-02 needs the Fourier profile as the spectrum's input |`. The critical path grows from 4 to 5 (M1-T01 → M1-T04 → M1-T12 → M1-T11 → M1-T14).
- M1-T11 gains no new bullet: TC-02 already covers it.
- Reorder `todo.md` to match.
- `## Replan notes`: `- 2026-10-28: M1-T11 now waits on M1-T12 (the spectrum needs the Fourier profile; TC-02 failed on hour-of-week means); dropped none`
- Status → Draft.

**Gate message:** what moved and why, the new edge and the longer critical path, "dropped none". *(Turn ends.)*

**A drop looks like this.** It's listed for approval first ("Drop M1-T13? Seasonal removal is already checked by TC-02 and TC-03 in M1-T14's run. Default: keep"). Only after an unambiguous yes, remove the section, its graph rows and todo line, and add under Replan notes:
```markdown
- ~~M1-T13: Seasonal removal check~~ Retired 2026-10-28: TC-02 and TC-03 now run in M1-T14
```
`dt next-id` counts the retired ID, so it's never reused, and `dt lint` flags any `Depends on` still pointing at it.
