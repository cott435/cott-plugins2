# Changelog

One entry per tagged release, newest first.

## [0.4.0] - 2026-10-17

### Added
- `api-probe` skill: probes an external API before a decision rests on it (PB-NN entries in `docs/probes.md`, evidence kept, keys never read by the agent); architecture-design, idea-refine, test-planning, build-planning and build-setup wired to probes.
- dt probes: `dt probes --stamp/--scan`, `dt status --skill api-probe`, `dt context` for PB-NN, `dt guard` on Read (`.env*`, probe output), and probe lints.
- `dt plan --json` schema plan-map/2: goal, feature and requirement levels, with `serves` and `covers` edges.
- Spec features carry a `**Stage:** S<n>` line (spec-writing); `dt plan` places each feature by it.
- Lints `spec-stage`, `type-cases` and `task-ref` (errors). A spec whose roadmap has stages now fails `dt lint` until every feature names its stage.
- Evals: probe scenarios with fake vendors, stage-based readiness, blind judge copies, structural graders with self-tests, `planexport.py --dt`.

### Changed
- build-planning cuts each Designed stage on its own; an uncut stage is Designed only when every spec ID its Source adds is on an Approved pipeline; New waits while a brief stage is below Designed. The derived stage status Cut is Split.
- Iteration-7 fixes across build-planning, pipeline-design, architecture-design and test-planning: replay doubles, one module per separately thickened step, Boundary lines for types crossing step owners, `fold:` reasons, an upstream-change gate row.
- spec-writing: cost, licence and budget limits are QR- items.
- Skill examples use the GridLoad and LeafLab domains, kept apart from the eval projects.

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
