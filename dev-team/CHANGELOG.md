# Changelog

One entry per tagged release, newest first.

## [0.5.0] - 2026-10-18

### Added
- `/dev-team:plan`: drives planning with one child session per skill run. `dt next` names the next skill run, its mode and why; `dt route` records a change for an upstream skill.
- `docs/requests.md`: every planning skill records the user's words verbatim (`UR-NN`, `dt request add`) and traces each to the IDs that honour it, or to a change the user approved (`dt request change … --into`, naming every ID the change was written into). Lints `request-format`, `request-trace`, `request-open`, `request-edit`, `request-ref` (errors) and `request-number`, `request-cite`, `request-source` (warnings). Each gate's **Your words** line quotes the words beside the traced text.
- `dt explain [--write]`: the pipelines in plain words (`docs/explained/<pkg>.md`): what each is for, how it runs, each step's job and the requirements it serves. Pipelines carry a one-sentence `**Purpose:**`. `explain-stale` warns when a written page drifts.
- `dt context` closes a packet over nested contract types and marks a Writes path an earlier task wrote `(from M1-Txx)`.
- Plan lints: `milestone-lines`, `milestone-order`, `exit-cases-in-scope`, `kind-title`, `covers-vs-deferred` (errors); `packet-type-closure`, `parallel-step`, `closed-open-question`, `process-narration` (warnings).
- build-setup: a pylint tool reference; reviewer and implementer agent templates revised for the build phase.
- Design: `design/build-phase.md` (dev-team owns the build), `design/requests.md`, `design/plan-sequence.html`.

### Changed
- pipeline-design: one entry module per pipeline, library classes as steps, helper folders, probe stand-ins. build-planning: wiring on spines and folds only, folds are split thickens, `__main__.py` in the interface task, every In → Out type declared by the interface task.
- architecture-design: a Boundary line and a fake for cross-pipeline functions, field types defined, no contract split for size or direction.
- test-planning: trusts the user's facts and cites their request as Source; looks up at most three, only when a case rests on one.
- idea-refine Extend: a new stage never adds a goal. api-probe: every probe run writes evidence.
- A project that passed `dt lint` under 0.4.0 can now fail it: the new milestone, plan and request lints are errors.

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
