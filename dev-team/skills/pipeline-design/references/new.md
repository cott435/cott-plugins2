# New

A package in scope has no `pipelines.md`. Read `steps.md` (rules) and `template.md` (the file format) here; `examples-new.md` has two worked New rounds. Ends at the Review Gate in `../SKILL.md`.

```
STATUS ─→ WORKFLOWS (ask) ─→ STEPS ─→ LAYOUT ─→ WRITE ─→ [gate: stop]
```

**1. Workflows.** Confirm them with the user as `../SKILL.md` (Asking about workflows) says.

**2. Steps.** Per pipeline, following `steps.md`: an ID from `dt next-id PL` (write the section before the next; never count by hand), Entry, Trigger, Covers, a step table with one owner, `In → Out` in contract types and a real spine version per step, and a pre-build entry sketch of step calls only.

**3. Layout.** One entry module per pipeline, one module (or helper folder) per step owner, each under `build-setup`'s size bar (`steps.md`, Layout).

**4. Write** `docs/packages/<pkg>/pipelines.md` from `template.md`, each pipeline about 35 lines (`dt lint` `budget`). Append the calling PL IDs to each called contract symbol's `Used by:` line (`- **Used by:** forecast; PL-02, PL-03`); that leaves an Approved contract Approved. A step needing a different signature, type or error is a contract change: list it and route to `architecture-design` Revise. Fix every error and `budget` warning `dt lint` reports on every file touched.
