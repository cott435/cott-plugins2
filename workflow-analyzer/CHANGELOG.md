# Changelog

One entry per tagged release. The versioning policy — what triggers patch/minor/major, and
how model and eval versioning relate to it — is in the `plugin-dev` plugin's `bump-version`
skill. This repo's own decisions are in `VERSIONING.md`.

## [0.2.0] - 2026-10-17

### Added
- Plan map: `scripts/planmap.py` renders a run's `plan.json` (schema `plan-map/1`) as `plan/index.html` (growth strip, node × turn matrix, change ledger), a page per turn and a build view per milestone (waves, lanes by task kind, critical path, interface edges).
- `flow.html` links a Plan section when `plan.json` is present; turn pages link to their plan page and back.

## [0.1.1] - 2026-10-17

### Added
- `trace.py view --flat` builds each session into `ROOT/<id8>/` instead of `ROOT/<project>/<id8>/`, the layout plugin-dev's audit workspaces use (69509e2).

### Changed
- Issue marks fall back to `<plugin>/audits/issues/` (plugin-dev's ledger) when `runs/audits/issues/` does not exist (69509e2).
- plugin-dev now runs these scripts through a link; `CLAUDE.md` lists what it relies on (69509e2).

## [0.1.0] - 2026-10-17

- Initial release.
