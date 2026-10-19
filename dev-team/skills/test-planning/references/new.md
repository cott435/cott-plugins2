# New: the first test plan for a package

No `tests.md` yet. Read `cases.md` before writing a case or a Strategy row. Worked rounds, with the interview and the gate message, are in `examples-new.md`; the template and fixture shapes are in `../examples.md`.

```
STATUS ─→ ASK ─→ CASES ─→ STRATEGY ─→ WRITE ─→ [gate: user approves oracles; stop]
```

**1. Ask**, in one message, the two things only the user knows: **which workflows matter most** (cases go where a wrong answer hurts) and **input/output pairs they already trust** (files, notebook outputs, paper tables).

**2. Cases** for those workflows and pairs, as `cases.md` says.

**3. Strategy:** one row per pipeline, as `cases.md` says.

**4. Write** `tests.md` from the template, and the fixtures. Then the Review Gate.
