# Extend

Read when `dt status --skill build-setup` reports `extend`: kickoff, after the next plan is approved. Apply only the deltas, with values per `derive.md`, and end at the Review Gate in `../SKILL.md`.

## Deltas

- **Dependencies:** add the milestone's, each with its `DEP002` entry and Exceptions row expiring `M<n> exit`.
- **New packages or components:** contracts, `pkg_scope`, deptry config, `known-first-party`, test dirs in the protected list.
- **Frozen contracts**, on a bar written before them (`protected_gaps` names `tests/contracts/**` once the project is multi-package or has `tests/contracts/`): copy the template's `frozen_contracts` and `protected_globs` functions into `check.sh` and its `protected` and `gate` lines, `tests/contracts/**` in both protected lists, CR-09 and the role-table row. A tightening.
- **Interface-first plans**, on a bar written before them (the plan has `**Kind:**` fields and the bar has no `scripts/red_check.py`): copy `red_check.py`, `floor_guard.py`'s interface-stub rules, `check.sh`'s `collect` and `--exit` lines, `path_guard.sh`'s `writes` mode, the agents' `writes` hooks, the role-table rows and CR-02's carve-out. The carve-out loosens CR-02, so list it under Loosenings; the rest tightens.
- **Review and duplicates**, on a bar written before them (CONSTRAINTS.md has no CR-42): `pylint` in the dev group (`uv lock`), `[tool.pylint.similarities]`, `check.sh`'s pylint line in `full`, the template's `floor_guard.py`, CR-42, and the Review section, reviewer and implementer files. A tightening.
- **New stack:** stubs and rule families.
- **Grow:** rewrite component contracts as package contracts; the rules don't change.
- Remove parentheses from optional layers whose module now exists.
- **References and probes**, on a bar written before them: the `references/` and `probes/` excludes, `references/**` and `probes/**` in both protected lists, the template's `floor_guard.py`, CR-08, Review item 7 and the `.gitignore` lines. A tightening; the floor guard doesn't count those excludes as loosening.

After approval and the commit, `dt base` runs as the Review Gate says.

## Example: M2 kickoff

```
Bar changes for M2:
- reserve exists now: "(gridload.reserve)" → "gridload.reserve" in the layers contract
- New dependency scipy (M2-T03): added, with EX-02 CR-25 DEP002 `scipy`, expires M2 exit
- EX-01 dropped: numpy and pandas are imported (that is a tightening)
Loosenings: EX-02 is a new exception. Approve it?
```
