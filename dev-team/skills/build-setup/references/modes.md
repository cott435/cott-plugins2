# Extend, Ratchet, Revise and Audit

Read when `dt status --skill build-setup` reports one of these modes, or the user asks for one. Each ends at the Review Gate in `../SKILL.md`, showing the diff of the bar. A loosening (a higher limit, a removed rule, a new exception, a weaker type mode) is shown as a before → after line and needs the user's explicit yes; a tightening is routine.

## Extend

At kickoff, after the next plan is approved. Apply only the deltas (values per `derive.md`):
- **Dependencies:** add the milestone's, each with its `DEP002` entry and Exceptions row expiring `M<n> exit`.
- **New packages or components:** contracts, `pkg_scope`, deptry config, `known-first-party`, test dirs in the protected list.
- **Frozen contracts**, on a bar written before them (`protected_gaps` names `tests/contracts/**` once the project is multi-package or has `tests/contracts/`): copy the template's `frozen_contracts` and `protected_globs` functions into `check.sh` and its `protected` and `gate` lines, `tests/contracts/**` in both protected lists, CR-09 and the role-table row. A tightening.
- **Interface-first plans**, on a bar written before them (the plan has `**Kind:**` fields and the bar has no `scripts/red_check.py`): copy `red_check.py`, `floor_guard.py`'s interface-stub rules, `check.sh`'s `collect` and `--exit` lines, `path_guard.sh`'s `writes` mode, the agents' `writes` hooks, the role-table rows and CR-02's carve-out. The carve-out loosens CR-02, so list it under Loosenings; the rest tightens.
- **New stack:** stubs and rule families.
- **Grow:** rewrite component contracts as package contracts; the rules don't change.
- Remove parentheses from optional layers whose module now exists.
- **References**, on a bar written before them: the `references/` excludes, `references/**` in both protected lists, CR-08 and Review item 7. A tightening; the floor guard doesn't count the `references` excludes as loosening.

After approval and the commit, `dt base` runs as in New.

## Ratchet

At Advance, after the exit checkpoint. Run `check.sh full`; record measured values in "Measured, not yet enforced". A metric that improved tightens (`fail_under` up, a shorter vulture whitelist). Drop expired `DEP002` entries the code now imports. Offer once to promote a measured metric to enforced. Set `**Ratcheted:** M<n>` in the header. After approval and the commit offer, hand back to `build-planning` Advance, whose next step is `dt archive`. Never run `dt base` and never say `/build` is next: the next milestone isn't planned yet.

## Revise

The user asks for a change. Edit `CONSTRAINTS.md` and its config key together. A request to raise a limit "just this once" to unblock a task is a loosening like any other: an expiring exception with the user's yes, or the code gets fixed.

## Audit

Changes nothing. Run `bash scripts/floor_guard.sh --base <plan Base>` (it reports a loosened `pyproject.toml`, new config files, removed rules and new exceptions) and `dt status`. Report each loosening since the milestone's Base and whether a build-setup commit recorded the user's yes, plus expired exceptions and config mismatches. Offer Revise for anything to fix.
