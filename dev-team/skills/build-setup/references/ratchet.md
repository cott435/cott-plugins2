# Ratchet

Read when `dt status --skill build-setup` reports `ratchet`: at Advance, after the exit checkpoint. Thresholds and exceptions follow `derive.md`; the run ends at the Review Gate in `../SKILL.md`.

## Steps

1. Run `check.sh full`; record measured values in "Measured, not yet enforced".
2. A metric that improved tightens (`fail_under` up, a shorter vulture whitelist, fewer pylint `ignore-paths`).
3. Drop expired `DEP002` entries the code now imports.
4. Offer once to promote a measured metric to enforced.
5. Set `**Ratcheted:** M<n>` in the header.
6. At the Review Gate, `expired_exceptions` must be empty too.
7. After approval and the commit offer, hand back to `build-planning` Advance, whose next step is `dt archive`. Never run `dt base` and never say the `build` skill is next: the next milestone isn't planned yet.

## Example: M1 exit

```
M1 measured (check.sh full): coverage 71.2%, vulture whitelist 0 entries (unchanged).
Tightenings: [tool.coverage.report] fail_under 0 → 71; EX-01 dropped (numpy and pandas are imported).
Loosenings: none. Header: **Ratcheted:** M1.
Approve? After the commit, next is build-planning Advance (dt archive). No dt base: M2 isn't planned yet.
```
