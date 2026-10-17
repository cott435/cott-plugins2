# Revise: an oracle changes

An expected output or tolerance must change: the user corrected an example, a paper has an erratum, a contract changed the output type, or a tolerance proved wrong *for a stated reason*. "The build can't make it pass" is not a reason; that's a bug until the source says the oracle was wrong. A looser tolerance is an oracle change too.

1. Show the old and new expected value (or tolerance) side by side, with the source of the new one.
2. Edit `expected.json` (the `dt guard` hook asks the user) and the case section. Status to Draft.
3. At the gate, name the tasks that cite the case. They pause: while `tests.md` is Draft, `build-planning`'s `dt status` says `blocked`. After approval, `build-planning` Replan follows (`changed_since_plan` lists `tests.md`).

A case that no longer applies collapses to one line under Retired (form in `../examples.md`) and its fixture folder is deleted. Its ID is never reused.

## Example: an oracle changes

**Context:** TC-05 pinned the top eigenvalue from the user's notebook. Two weeks later the user found their notebook used unadjusted closes and re-ran it.

```
Revise TC-05 (PL-02 · STAT-01):
  old expected.json  {"top_eigval": 2.31, "tol": 1e-6}
  new expected.json  {"top_eigval": 2.27, "tol": 1e-6}
  Source: your notebook `cov_check.ipynb`, re-run 2026-11-04 on adjusted closes (cell 14 output attached in source/).
  Tolerance unchanged: same data, same float64 arithmetic.
Tasks citing TC-05: M1-T04. After approval, build-planning Replan if its acceptance changes.
Do you approve the new expected output?
```

Writing `expected.json` brings up the `dt guard` permission prompt; that's the second check, not a substitute for the user's yes in chat. `tests.md` goes to Draft until they answer.

**Not a Revise:** the build gets 2.29 and the test fails. Nothing says the oracle was wrong, so that's a bug for the build to find. Changing the expected value or widening the tolerance here would delete the evidence.
