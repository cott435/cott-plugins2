# Extend, Revise and Sync

Read when `dt status --skill pipeline-design` reports one of these modes. Each ends at the Review Gate in `../SKILL.md`. Formats are in `../examples.md`.

## Extend

New spec IDs or components arrived. Take `uncovered_ids` and `components_unowned` from `dt status`. For each ID: an existing step covers it (add it to Covers), an existing step changes its In → Out (edit that row; check the contract still matches, else route to `architecture-design` Revise), or a new workflow or step is needed. Confirm new workflows exactly as in New mode (Step 1): show the candidate list, the existing pipelines they sit beside, then one question. New pipelines get new IDs and their own entry sketch; existing IDs, rows and step names don't change. Append new PL IDs to the `Used by:` lines of the contract symbols they call.

**Layout in Extend.** A `## Planned layout (pre-build — removed by spine task)` section lives only while some pipeline in the doc is unbuilt; `dt lint` flags `prebuild-left` once every pipeline is built. So:
- **A new, unbuilt pipeline:** add its modules to the planned layout. If the spine already removed it, write a new one holding only the new modules, marked against the existing tree from `dt layout <pkg>`.
- **Only new steps on built pipelines:** write no planned layout. Name each new module at the gate (owner → `<owner>/<module>.py`); `build-planning` puts it in the task's `Files likely`.

Status back to Draft, then the Review Gate, highlighting only what changed.

## Revise

The build learned something: a step is replaced, split or reordered (a shrinkage step must come before cleaning). If a decision changed, `architecture-design` Revise goes first; cite its `AD-NN` on the row.

1. Edit the step table. Keep step names where the function survives; a split step gets new rows with new function names. Keep the pipeline's ID: a rebuilt package keeps its PL IDs where it can, so its golden cases still apply.
2. If the entry sketch is gone (the spine was built), don't recreate it. The step table is the contract the code must match; the code change becomes a task.
3. Keep `Used by:` lines true: add the PL ID to a symbol a new step calls, and remove it from one no step of that pipeline calls any more.
4. A pipeline dropped entirely collapses to one line under Retired: `- ~~PL-04: Raw eigen dump~~ Retired 2026-11-02: folded into PL-02 (AD-09)`. Delete its section, and its ID stays retired forever.
5. Set Status to Draft. At the gate, list the tasks whose `Step:` or `Read:` touches the changed rows and tell the user they pause: while this doc is Draft, `dt status --skill build-planning` reports `blocked` (waiting for approval). After approval, `build-planning` Replan follows (its `dt status` reports `replan` and lists this doc under `changed_since_plan`), plus `test-planning` Revise if an expected output changes. This skill never edits `tasks/`.

### Example: shrinkage before cleaning

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
