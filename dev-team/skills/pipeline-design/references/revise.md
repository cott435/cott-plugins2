# Revise

The build learned something: a step is replaced, split or reordered (a ridge-penalty step must come before trimming). If a decision changed, `architecture-design` Revise goes first; cite its `AD-NN` on the row. Read `steps.md` first. Ends at the Review Gate in `../SKILL.md`.

1. Edit the step table as `steps.md` (Changing a step table) says.
2. A pipeline dropped entirely collapses to one line under Retired: `- ~~PL-04: Raw periodogram dump~~ Retired 2026-11-02: folded into PL-02 (AD-09)`. Delete its section, and its ID stays retired forever.
3. Set Status to Draft. At the gate, list the tasks whose `Step:` or `Read:` touches the changed rows and tell the user they pause: while this doc is Draft, `dt status --skill build-planning` reports `blocked` (waiting for approval). After approval, `build-planning` Replan follows (its `dt status` reports `replan` and lists this doc under `changed_since_plan`), plus `test-planning` Revise if an expected output changes. This skill never edits `tasks/`.

## Example: ridge penalty before trimming

**Context:** during M1 the build found trimming the terms of an unpenalized Fourier fit is unstable with under two years of hours. `architecture-design` Revise added AD-07: ridge-penalize the coefficients before trimming. PL-02's spine is built, so its entry sketch is already gone.

**Before:**
```markdown
| 2 | `fit_seasonality` | profile.fit | Demand → Profile | daily and weekly Fourier terms | PROF-02 |
| 3 | `trim_terms` | profile.terms | Profile, n_hours → Profile | keep every term (baseline) | PROF-03 |
```

**After** (`Status: Draft`):
```markdown
| 2 | `fit_seasonality` | profile.fit | Demand → Profile | daily and weekly Fourier terms | PROF-02 |
| 3 | `penalize` | profile.ridge | Profile, n_hours → Profile | no penalty (baseline; AD-07) | PROF-02 |
| 4 | `trim_terms` | profile.terms | Profile, n_hours → Profile | keep every term (baseline) | PROF-03 |
```

Rows below shift down a number; step names and the PL ID don't change. `penalize` isn't a contract symbol (it's internal to `profile`), so `contract.md` is untouched; had it been, its `Used by:` line would gain PL-02. The new step's spine is "no penalty": `penalize` returns its input until a task upgrades it, which is a real baseline, not a mock. No entry sketch is recreated: the code now calls five steps where the table has six, so `dt layout gridload` reports drift until the task lands.

**Gate message (excerpt):**

```
Revised PL-02: new step `penalize` (profile.ridge) between fit_seasonality and trim_terms, per AD-07.
Affected tasks: M1-T04 (Step: PL-02.trim_terms; Read: PL-02). They pause until this is approved:
while pipelines.md is Draft, build-planning's dt status says blocked (waiting for approval).
After approval: build-planning Replan (its dt status says replan, changed_since_plan lists
docs/packages/gridload/pipelines.md) adds the `penalize` task. TC-02's expected output is unchanged
(the planted daily sine is recovered either way), so no test-planning Revise.
```
