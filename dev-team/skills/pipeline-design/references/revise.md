# Revise

The build learned something: a step is replaced, split or reordered (a shrinkage step must come before cleaning). If a decision changed, `architecture-design` Revise goes first; cite its `AD-NN` on the row. Read `steps.md` first. Ends at the Review Gate in `../SKILL.md`.

1. Edit the step table as `steps.md` (Changing a step table) says.
2. A pipeline dropped entirely collapses to one line under Retired: `- ~~PL-04: Raw eigen dump~~ Retired 2026-11-02: folded into PL-02 (AD-09)`. Delete its section, and its ID stays retired forever.
3. Set Status to Draft. At the gate, list the tasks whose `Step:` or `Read:` touches the changed rows and tell the user they pause: while this doc is Draft, `dt status --skill build-planning` reports `blocked` (waiting for approval). After approval, `build-planning` Replan follows (its `dt status` reports `replan` and lists this doc under `changed_since_plan`), plus `test-planning` Revise if an expected output changes. This skill never edits `tasks/`.

## Example: shrinkage before cleaning

**Context:** during M1 the build found MP cleaning of a raw sample covariance is unstable at T/N ≈ 2. `architecture-design` Revise added AD-07: shrink to a Ledoit–Wolf target before cleaning. PL-02's spine is built, so its entry sketch is already gone.

**Before:**
```markdown
| 2 | `estimate_cov` | stats.cov | Returns → Cov | sample covariance | STAT-02 |
| 3 | `clean_eigen` | stats.rmt | Cov, T → Cov | no cleaning (baseline) | STAT-03 |
```

**After** (`Status: Draft`):
```markdown
| 2 | `estimate_cov` | stats.cov | Returns → Cov | sample covariance | STAT-02 |
| 3 | `shrink` | stats.shrink | Cov, T → Cov | no shrinkage (baseline; AD-07) | STAT-02 |
| 4 | `clean_eigen` | stats.rmt | Cov, T → Cov | no cleaning (baseline) | STAT-03 |
```

Rows below shift down a number; step names and the PL ID don't change. `shrink` isn't a contract symbol (it's internal to `stats`), so `contract.md` is untouched; had it been, its `Used by:` line would gain PL-02. The new step's spine is "no shrinkage": `shrink` returns its input until a task upgrades it, which is a real baseline, not a mock. No entry sketch is recreated: the code now calls four steps where the table has five, so `dt layout quant` reports drift until the task lands.

**Gate message (excerpt):**

```
Revised PL-02: new step `shrink` (stats.shrink) between estimate_cov and clean_eigen, per AD-07.
Affected tasks: M1-T04 (Step: PL-02.clean_eigen; Read: PL-02). They pause until this is approved:
while pipelines.md is Draft, build-planning's dt status says blocked (waiting for approval).
After approval: build-planning Replan (its dt status says replan, changed_since_plan lists
docs/packages/quant/pipelines.md) adds the `shrink` task. TC-02's expected output is unchanged
(the MP-edge property holds either way), so no test-planning Revise.
```

## Sync

`dt layout <pkg>` printed `PL-02: drift — calls […] vs steps […]`. For each mismatch, show both sides and ask which changes:

- **The doc changes** when the code found a better order or a real extra step. Edit the table (as Revise), Status to Draft.
- **The code changes** when it broke a rule: logic in the entry, a step owned by two components, a registry with no AD. Leave the doc, and list the fix for `build-planning` Replan.

Never rewrite the table to match code that breaks a readability rule.
