# Changelog

One entry per tagged release. The versioning policy — what triggers patch/minor/major, and
how model and eval versioning relate to it — is in the `plugin-dev` plugin's `bump-version`
skill. This repo's own decisions are in `VERSIONING.md`.

## [0.3.0] - 2026-10-19

### Added
- Plan map reads schema `plan-map/2`: goal, feature and requirement levels with `serves` and `covers` edges, traced to the build.
- R6: an order row that serializes work is flagged "worth a look". R9: critical paths drawn as whole tasks, tied paths shown; shared-entry edges; file and integration edges before order; the mitigated tile counts data and call edges; testers wait on the interface.

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
