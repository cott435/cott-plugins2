# dev-team2

A Claude Code plugin that takes a project from a raw idea to an enforced build plan: brief, spec, architecture, pipelines, test plan, milestone plan and quality bar. Building itself is agent-skills' `/build`; dev-team2 makes sure builders get small, correct inputs. This README covers the documents the skills produce, how they change over time, and the `dt` tool that reads them.

**Install the whole plugin**, not single skills: the skills share `scripts/dt.py` and the hooks in `hooks/hooks.json`. Requires `python3` (stdlib only); `build-setup` also needs `uv` and `jq` in the project.

## The flow

```
Define                      Design                                   Plan                                   Bar            Build
idea-refine → spec-writing → architecture-design → pipeline-design → test-planning (optional) → build-planning → build-setup → /build
```

Every skill stops after writing a Draft and waits for your review. Nothing moves forward until you approve it in your own words, and "approved, go ahead" starts the next *planning* skill, never code. Planning skills never write or run code.

## The documents

| Document | Answers | Written by | Size |
|---|---|---|---|
| `docs/brief.md` | **Why** the project exists: problem, users, ≤ 5 stage-neutral goals, constraints, not doing | `idea-refine` | ≤ 1 page |
| `docs/ideas/<idea>.md` | **Why** an addition is worth making | `idea-refine` | 300-700 words |
| `docs/roadmap.md` | **In what order**: stages (`S<n>`: outcomes the user agreed, with an outline and the skills they route to) and the milestones each is cut into (`M<n>`: build-sized vertical slices) | `idea-refine` adds stages, `build-planning` cuts them into milestone rows, `dt roadmap` writes Status | 2 tables + ≤ 6 lines per stage or milestone |
| `references/` | Your reference code and notes: how something has been done before. Never imported, excluded from tooling | You | — |
| `docs/references.md` | What each reference is for (`RF-NN`), its caveats, and the stage it serves | `reference-intake` | ≤ 8 lines per file |
| `docs/spec.md` | **What** is built: requirements (`CODE-NN`), acceptance criteria, scope | `spec-writing` | As long as needed |
| `docs/architecture.md` | **How**: components, dependencies, decisions (`AD-NN`); multi-package: system map and system pipelines | `architecture-design` | 1-3 pages (single); 2-4 (root) |
| `docs/packages/<pkg>/architecture.md` | A package's internals (multi-package only) | `architecture-design` | 1-3 pages |
| `docs/packages/<pkg>/contract.md` | The package's public API: one section per symbol, with invariants and errors | `architecture-design` | ≤ 1 page |
| `docs/packages/<pkg>/pipelines.md` | The workflows you run (`PL-NN`): one entry function each, a step table, a real spine version per step, planned layout until the spine lands | `pipeline-design` | ≤ 2 pages |
| `docs/packages/<pkg>/tests.md` | Test strategy per pipeline and golden cases (`TC-NN`), each with a source outside the agent | `test-planning` | ≤ 2 pages |
| `tests/fixtures/<pkg>/TC-NN/` | `source/`, `input.json`, `expected.json` — the oracles | `test-planning` | Kilobytes |
| `tests/contracts/<pkg>.<symbol>/` | A cross-package boundary frozen as a schema, fixture payloads and a fixture-backed fake | Cases: `architecture-design` (contract `**Boundary:**` line); files: the Phase 0 contract task | Kilobytes |
| `tasks/plan.md`, `tasks/todo.md` | The active milestone: Phase 0 (contract, spines, integration), thicken tasks (`M<n>-T<nn>`), checkpoints | `build-planning` | ≤ ~400 lines |
| `tasks/queued/`, `tasks/archive/` | Later milestones planned in detail (only on request); finished milestones | `build-planning`, `dt archive` | — |
| `CONSTRAINTS.md` + `pyproject.toml`, `scripts/check.sh`, `.claude/agents/` | The quality bar (`CR-NN`), its enforcement, and the tester/implementer/reviewer roles | `build-setup` | ≤ 2 pages |
| `AGENTS.md` / `CLAUDE.md` | Doc map: how agents find their context | `build-planning` | ≤ 25 lines |

The **brief** is the stable foundation. **Idea files** carry each addition, so the brief doesn't grow; once specced, an idea is frozen. **Stages live in the roadmap**, not in the brief's goals, and they aren't sized: `build-planning` cuts each into milestones once its pipelines exist. The **spec** is the single source of truth for what gets built. The **architecture** gives every requirement a home and records each technical choice as a decision. **Pipelines** turn the design into call paths a reader can follow; **contracts** are all a consumer of a package reads. **Plans** are written for the next milestone only, because task lists are the most perishable doc; pipelines and contracts last.

**One folder per package**, in single- and multi-package repos alike. A single package has one `docs/packages/<pkg>/` with contract sections per component, so when a component later becomes a package (Grow), its sections move with it and nothing is rewritten.

**Intent until code exists, then code is truth.** Planned layout and entry sketches are *pre-build* sections; the spine task replaces them with a pointer to `dt layout`. Contracts stay as docs and are checked against the code.

## References and skills per stage

Drop reference files (code or markdown) into `references/` whenever you have them: a dataset builder, a transform, notes. `dt status` reports new or changed files at session start, and `reference-intake` summarizes each one (`RF-NN`) and asks which stage it serves. Each roadmap stage also lists the project skills it routes to; a stage cut into several milestones divides them among its milestones. The planning skills carry both down to tasks: a task's `Read:` names `RF-02:build_targets`, and `dt context` gives the builder that function under a "reference, your call what to reuse" banner. `build-planning` checks that every stage reference and skill reaches a milestone, and every milestone's reaches a task. Design: [design/references.md](design/references.md).

## IDs and section reads

Every addressable unit has a repo-unique ID that is never renumbered or reused: requirements `CODE-NN`, decisions `AD-NN`, pipelines `PL-NN` (steps `PL-NN.<function>`), test cases `TC-NN`, stages `S<n>`, milestones `M<n>`, tasks `M<n>-T<nn>`, review findings `M<n>-R<nn>`, contract symbols `<component>.<symbol>`, constraint rules `CR-NN`, references `RF-NN`. Agents read by ID, not by file:

```bash
python3 <plugin>/scripts/dt.py section PL-02 TC-06 STAT-02
```

Each task lists the IDs a builder needs in its `Read:` field; `dt context M2-T03` prints exactly those sections plus the task, and that packet is the builder's whole context. Removed items collapse to one struck line with a date and reason; docs carry no history beyond one-line changelog rows, since git is the history.

## Statuses

| Document | Lifecycle |
|---|---|
| Brief | `Draft` → `Accepted` |
| Idea | `Draft` → `Accepted` → `Specced` (frozen), or `Parked` |
| Spec, architecture, contract, pipelines, tests, CONSTRAINTS | `Draft` → `Approved`; editing an Approved doc sets it back to `Draft` (except mechanical `dt` edits and pipeline-design appending pipeline IDs to a contract's `Used by`) |
| Decision | `Proposed` → `Accepted` → `Superseded by AD-NN` |
| Plan | `Draft` → `Approved` → `In progress` → `Done` → archived; a stub with `Between milestones` until the next plan is approved |
| Stage (roadmap, derived by `dt roadmap`) | `Idea` → `Specced` → `Designed` → `Cut` (milestone rows written) → `Planned` → `Building` → `Done` |
| Milestone (roadmap, derived by `dt roadmap`) | `Idea` → `Specced` → `Designed` → `Planned` → `Building` → `Done` |

## Lifecycles

### New project

```
idea-refine (New) → brief + roadmap stages S1… ─ accept
→ spec-writing (New) ─ approve
→ architecture-design (New): shape, components, contract.md ─ approve
→ pipeline-design (New): pipelines + planned layout ─ approve
→ test-planning (New, optional): golden cases + fixtures ─ approve the expected outputs
→ build-planning (New): cut each designed stage into milestones, M1 plan (Phase 0 contract → spines → system spine, thicken, checkpoints), AGENTS.md ─ approve
→ build-setup (New): CONSTRAINTS.md, tool config, check scripts, agent roles ─ approve
→ /build
```

### A new stage

```
idea-refine (Extend) → idea file + roadmap stage ─ accept
→ spec-writing (Extend) → architecture-design (Extend; Grow check) → pipeline-design (Extend)
→ test-planning (Extend) → build-planning (Extend: cut the stage into milestones; plan the next, queued if a milestone is active)
```

Up front (all stages known) or one stage at a time land in the same place: design everything known, cut each designed stage into milestones, write task plans only for the next milestone, and start every milestone with a kickoff check against the code.

### Stages and milestones

A **stage** is an outcome the user agreed in `idea-refine` ("See my spending"), unsized. Once its pipelines are approved, `build-planning` **cuts** it into **milestones** along dependency lines: vertical slices that each run end to end, the first a walking skeleton through every package the stage touches. Only one milestone is active at a time, so independent tracks stay inside one milestone as parallel groups; a cut happens only where a later slice needs an earlier one's outputs. A milestone's size is counted per track: the serial Phase 0 tasks plus the longest `Depends on` chain through the rest, at most about 15.

### Phase 0: contract first

In a multi-package milestone, Phase 0 doesn't queue every package behind one system-spine task:
1. **Contract task** (solo, first): freezes each cross-package boundary the milestone uses as executable artifacts in `tests/contracts/<pkg>.<symbol>/`: a schema (JSON Schema, a typed model, or a pandera schema for a dataframe), golden fixture payloads, and a fixture-backed fake of the provider.
2. **Package spines** in parallel groups: consumers run against the contract fake, providers assert their output validates against the schema.
3. **System spine** (last): integration, swapping the fake for the real provider.

A boundary fake generated from an approved contract is allowed, because both sides are tested against the same fixtures. Mocking a step inside a package is still forbidden: every spine step is a real baseline.

### Finishing a milestone (Advance)

```
exit checkpoint (reviewer findings dispositioned) ─ you approve the milestone
→ build-setup Ratchet ─ approve tightenings
→ dt archive (plan to tasks/archive/, stub plan, roadmap outcome)
→ kickoff check: dt status; Sync pipelines.md and contract.md against the code ─ approve if mismatched
→ build-planning: next milestone's plan (cutting the next stage first if it has no milestones) ─ approve
→ build-setup Extend (new packages, dependencies, Grow) ─ approve; dt base records the start commit
→ /build
```

### Changing something that already exists

| Change | Go to | Result |
|---|---|---|
| Small, clear tweak to existing behavior | `spec-writing` | Requirement edited in place (same ID), one changelog row |
| Rethinking how a feature works | `idea-refine` | New idea file, then `spec-writing` updates the spec |
| Project direction (goals, users, constraints) | `idea-refine` | Brief back to Draft; once re-accepted, the spec follows |
| Technical change with no spec change | `architecture-design` (Revise) | New decision; the old one superseded or revised |
| Project outgrows one package | `architecture-design` (Grow) → `pipeline-design` (Grow) | Package docs and pipelines move by owner; a pipeline crossing packages becomes a system pipeline |
| A step is replaced, split or reordered during the build | `pipeline-design` (Revise) → `build-planning` (Replan) | Affected tasks pause until re-approved |
| An expected output was wrong | `test-planning` (Revise) | Oracle changed only with your approval |
| Something learned during the build, or a major bug | `build-planning` (Replan) | Tasks reordered, split or added; drops listed for approval; a regression case added |
| Rebuild a package | `architecture-design` (Revise) → `pipeline-design` (Revise) → `build-planning` (Extend) | Old code runs until the new spine passes the existing golden cases |
| Code has drifted from the design | `pipeline-design` / `architecture-design` (Sync) | Mismatches listed; you decide which side changes |

## Data and ML projects

Data decisions are spread across the stages on purpose:

| Stage | Decides | Example |
|---|---|---|
| Brief / idea (`idea-refine`) | Whether usable data **exists** and is affordable and legal. The non-ML baseline. | "Need daily US prices including delisted companies, under $100/month" |
| Spec (`spec-writing`) | What the data must **contain and guarantee** (`DATA-` requirements). Model targets against a baseline. | "No value published after date D is visible to a backtest on D" |
| Architecture (`architecture-design`) | **Which** API, vendor, or dataset, and which model type, each recorded as a decision | Candidates are checked against the `DATA-` requirements and the brief's budget |
| Pipelines (`pipeline-design`) | The **spine** version of each step: a real baseline, never a mock (only another package across a frozen contract may be faked) | Sample covariance before shrinkage; equal weight before min-variance |
| Tests (`test-planning`) | **Known-answer** cases: planted signals, pure noise, closed forms, and the model evaluation protocol | Every cleaned eigenvalue ≤ the Marchenko–Pastur edge on pure noise |

A data source is named earlier only when it's a fixed constraint, such as your own database or a required benchmark. Thicken tasks put data loading, leak checks and evaluation before any model.

## Tooling: `dt` and hooks

`scripts/dt.py` parses every doc with one parser, so skills, hooks and agents see the same IDs, statuses and sections. Every skill starts with `dt status --skill <name>`; mechanical edits (`dt tick`, `dt prebuild-clear`, `dt archive`, `dt finding`, `dt roadmap`, `dt base`) go through `dt` so approved docs aren't reset to Draft. Reference: [scripts/README.md](scripts/README.md).

The plugin's hooks run in every session, subagents included:

| Event | Runs | Effect |
|---|---|---|
| SessionStart | `dt status --summary` | Active milestone, next task, blocked tasks and docs awaiting approval (silent outside dev-team2 projects) |
| PreToolUse (Edit, Write) | `dt guard` | Asks you before any `tests/fixtures/**/expected.json` change; denies writes to `tasks/archive/**` |
| PostToolUse (Edit, Write) | `dt lint --hook` | Lint problems in docs and plans go straight back to the agent that made the edit |
| Stop | `dt lint --hook` | Reports problems in changed docs; never blocks |

Code tooling (`check.sh`, Ruff, mypy, import-linter, the agent role files and their hooks) is project-owned and written by `build-setup`, so CI and humans have it without the plugin.

## Skills

| Skill | Phase | Produces |
|---|---|---|
| [`idea-refine`](skills/idea-refine/SKILL.md) | Define | `docs/brief.md`, `docs/ideas/*.md`, roadmap stages and their Skills |
| [`reference-intake`](skills/reference-intake/SKILL.md) | Any time | `docs/references.md` (one read-only agent per new or changed file) |
| [`spec-writing`](skills/spec-writing/SKILL.md) | Define | `docs/spec.md` |
| [`architecture-design`](skills/architecture-design/SKILL.md) | Design | `docs/architecture.md`, `docs/packages/*/{architecture,contract}.md` |
| [`pipeline-design`](skills/pipeline-design/SKILL.md) | Design | `docs/packages/*/pipelines.md` |
| [`test-planning`](skills/test-planning/SKILL.md) | Plan (optional) | `docs/packages/*/tests.md`, `tests/fixtures/**` |
| [`build-planning`](skills/build-planning/SKILL.md) | Plan | Roadmap milestone rows (each stage cut into slices), `tasks/plan.md`, `tasks/todo.md`, AGENTS.md doc map |
| [`build-setup`](skills/build-setup/SKILL.md) | Bar | `CONSTRAINTS.md`, tool config, `scripts/`, `.claude/agents/` |

Design notes: [design/planning-stage.md](design/planning-stage.md), [design/build-setup.md](design/build-setup.md).
