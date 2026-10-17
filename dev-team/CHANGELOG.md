# Changelog

One entry per tagged release, newest first.

## [0.3.0] - 2026-10-17

### Added
- Interface-first milestones: an interface task freezes step-boundary types, signatures and sample payloads; one spine task per step, one wiring task per pipeline, a system task last (build-planning).
- Task fields `Kind:` and `Writes:` (an exclusive file claim) and a `## Dependency graph` table in `tasks/plan.md`, each edge with its kind and the interface that mitigates it.
- `dt ready` and `dt plan --json`; `dt status` reports the critical path, waves, width and parallelism; lints `writes`, `edges` and `step-io-types`.
- Types as contract sections (architecture-design); every step's `In → Out` names one (pipeline-design).
- Testers write against frozen interfaces; CR-02 allows a stub that names its open task (build-setup).
- Evals: graph and interface checks, `modecmp.py` for incremental vs all-at-once, a per-turn `plan.json` export for workflow-analyzer's plan map, and the build eval (minilab fixture, `build_driver.py`, `grade_build.py`, `dryrun_build.py`, `run_build.sh`).
- Design: `design/interface-first-design.md`, `design/plan-flow.html`.

### Changed
- Every skill is its role in `SKILL.md` plus one `references/<mode>.md` per mode.
- Parallel groups are derived from `Depends on`; `Parallel:` and `Files likely:` still parse, with a deprecation warning. The `parallel` lint is replaced by `writes` and `edges`.

## [0.2.0] - 2026-10-17

- Renamed from `dev-team2` and moved into the `cott-plugins2` marketplace, held to
  plugin-dev's checks.
