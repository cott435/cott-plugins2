# Extend: add cases

A new pipeline, new user pairs, or a bug found in a golden path. Read `cases.md` before writing a case or a Strategy row; the section and fixture forms are in `../examples.md`.

- New pipelines get a Strategy row and cases.
- New user pairs become new cases.
- A bug found in a golden path gets a `regression` case whose expected output comes from the user or the reference that showed the bug, never from the fixed code.

Existing cases stay untouched. **Rebuild** reuses existing cases unchanged: they're what proves the new implementation matches the old.

Then the Review Gate, showing the cases this round added.
