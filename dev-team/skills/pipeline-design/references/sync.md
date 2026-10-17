# Sync

The code drifted from the step table. Ends at the Review Gate in `../SKILL.md`.

`dt layout <pkg>` printed `PL-02: drift — calls […] vs steps […]`. For each mismatch, show both sides and ask which changes:

- **The doc changes** when the code found a better order or a real extra step. Edit the table as `steps.md` (Changing a step table) says, Status to Draft.
- **The code changes** when it broke a rule: logic in the entry, a step owned by two components, a registry with no AD. Leave the doc, and list the fix for `build-planning` Replan.

Never rewrite the table to match code that breaks a readability rule (`steps.md`).
