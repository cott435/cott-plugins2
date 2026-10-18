# dev-team

A Claude Code plugin that takes a project from a raw idea to an enforced build plan: brief, spec, architecture, pipelines, test plan, milestone plan and quality bar. Building itself is agent-skills' `/build`; dev-team makes sure builders get small, correct inputs. This README covers the documents the skills produce, how they change over time, and the `dt` tool that reads them.

**Install the whole plugin**, not single skills: the skills share `scripts/dt.py` and the hooks in `hooks/hooks.json`. Requires `python3` (stdlib only); `build-setup` also needs `uv` and `jq` in the project.

## The flow

```
Define                      Design                                   Plan                                   Bar            Build
idea-refine → spec-writing → architecture-design → pipeline-design → test-planning (optional) → build-planning → build-setup → /build
```

`/dev-team:plan <what you want>` drives the flow for you: `dt next` names the next skill run, and in the Claude desktop app each run starts as its own session in the project folder, so every context stays small. You answer and approve in that session; `/plan` only starts the next one. Without session tools it names the skill and runs it in the same session.

Every skill stops after writing a Draft and waits for your review. Nothing moves forward until you approve it in your own words, and "approved, go ahead" starts the next *planning* skill, never code. Planning skills never write or run project code. The one exception is `api-probe`: it writes small probe scripts under `probes/` to check an external API before a decision rests on it, runs only the checks that need no credentials, and leaves the rest for you to run.

## The documents

| Document | Answers | Written by | Size |
|---|---|---|---|
| `docs/brief.md` | **Why** the project exists: problem, users, ≤ 5 stage-neutral goals, constraints, not doing | `idea-refine` | ≤ 1 page |
| `docs/ideas/<idea>.md` | **Why** an addition is worth making | `idea-refine` | 300-700 words |
| `docs/requests.md` | **What you said**, verbatim (`UR-NN`): each fact, tool, choice and answer, traced to the requirement or decision that honours it, or to a change you approved | every planning skill, through `dt request` | One line per request |
| `docs/roadmap.md` | **In what order**: stages (`S<n>`: outcomes the user agreed, with an outline and the skills they route to) and the milestones each is cut into (`M<n>`: build-sized vertical slices) | `idea-refine` adds stages, `build-planning` cuts them into milestone rows, `dt roadmap` writes Status | 2 tables + ≤ 6 lines per stage or milestone |
| `references/` | Your reference code and notes: how something has been done before. Never imported, excluded from tooling | You | — |
| `docs/references.md` | What each reference is for (`RF-NN`), its caveats, and the stage it serves | `reference-intake` | ≤ 8 lines per file |
| `docs/probes.md` + `probes/PB-NN-*/` | What an external source **really returns** (`PB-NN`): the question, checks with pass criteria, what a run spends, the verdict; the probe script and its redacted evidence | `api-probe`; `evidence/` only by the probe's scripts | ≤ 8 lines + 1 per check |
| `docs/spec.md` | **What** is built: requirements (`CODE-NN`), acceptance criteria, scope | `spec-writing` | As long as needed |
| `docs/architecture.md` | **How**: components, dependencies, decisions (`AD-NN`); multi-package: system map and system pipelines | `architecture-design` | 1-3 pages (single); 2-4 (root) |
| `docs/packages/<pkg>/architecture.md` | A package's internals (multi-package only) | `architecture-design` | 1-3 pages |
| `docs/packages/<pkg>/contract.md` | The package's public API: one section per symbol and per type its steps pass (`### stats.Cov: type`), with invariants, errors and `**Boundary:**` lines | `architecture-design` | ≤ 1 page |
| `docs/packages/<pkg>/pipelines.md` | The workflows you run (`PL-NN`): one entry function each, a step table with `In → Out` in contract types, a real spine version per step, planned layout until the wiring lands | `pipeline-design` | ≤ 2 pages |
| `docs/packages/<pkg>/tests.md` | Test strategy per pipeline and golden cases (`TC-NN`), each with a source outside the agent and the step boundaries it exercises | `test-planning` | ≤ 2 pages |
| `tests/fixtures/<pkg>/TC-NN/` | `source/`, `input.json`, `expected.json` — the oracles | `test-planning` | Kilobytes |
| `tests/contracts/<id>.<symbol>/` | A frozen interface: a boundary type's schema and samples, or, for a call from another pipeline or package, a fixture-backed fake | Cases: `architecture-design` (contract `**Boundary:**` line); files: the milestone's interface task | Kilobytes |
| `tasks/plan.md`, `tasks/todo.md` | The active milestone: an interface task, one spine per step, wiring per pipeline, thicken and system tasks (`M<n>-T<nn>`), each with exclusive `Writes:`; the dependency graph; checkpoints | `build-planning` | ≤ ~400 lines |
| `tasks/queued/`, `tasks/archive/` | Later milestones planned in detail (only on request); finished milestones | `build-planning`, `dt archive` | — |
| `CONSTRAINTS.md` + `pyproject.toml`, `scripts/check.sh`, `.claude/agents/` | The quality bar (`CR-NN`), its enforcement, and the tester/implementer/reviewer roles | `build-setup` | ≤ 2 pages |
| `AGENTS.md` / `CLAUDE.md` | Doc map: how agents find their context | `build-planning` | ≤ 25 lines |

The **brief** is the stable foundation. **Idea files** carry each addition, so the brief doesn't grow; once specced, an idea is frozen. **Stages live in the roadmap**, not in the brief's goals, and they aren't sized: `build-planning` cuts each into milestones once its pipelines exist. The **spec** is the single source of truth for what gets built. The **architecture** gives every requirement a home and records each technical choice as a decision. **Pipelines** turn the design into call paths a reader can follow; **contracts** are all a consumer of a package reads. **Plans** are written for the next milestone only, because task lists are the most perishable doc; pipelines and contracts last.

**One folder per package**, in single- and multi-package repos alike. A single package has one `docs/packages/<pkg>/` with contract sections per component, so when a component later becomes a package (Grow), its sections move with it and nothing is rewritten.

**Intent until code exists, then code is truth.** Planned layout and entry sketches are *pre-build* sections; the pipeline's wiring task replaces them with a pointer to `dt layout`. Contracts stay as docs and are checked against the code.

## References and skills per stage

Drop reference files (code or markdown) into `references/` whenever you have them: a dataset builder, a transform, notes. `dt status` reports new or changed files at session start, and `reference-intake` summarizes each one (`RF-NN`) and asks which stage it serves. Each roadmap stage also lists the project skills it routes to; a stage cut into several milestones divides them among its milestones. The planning skills carry both down to tasks: a task's `Read:` names `RF-02:build_targets`, and `dt context` gives the builder that function under a "reference, your call what to reuse" banner. `build-planning` checks that every stage reference and skill reaches a milestone, and every milestone's reaches a task. Design: [design/references.md](design/references.md).

## Your words

The brief compresses, and each skill may run in a fresh session, so what you said must live in a doc. Every planning skill records each fact, tool, choice and answer you give in `docs/requests.md`, word for word (`UR-NN`). The skill whose doc owns a request honours it and traces it (`UR-02 → AD-04`), or proposes a change that you approve, recorded with your words. Once the spec or architecture is Approved, `dt lint` fails it for any request of its own left open, and `dt next` sends the run back. Design: [design/requests.md](design/requests.md).

## IDs and section reads

Every addressable unit has a repo-unique ID that is never renumbered or reused: requirements `CODE-NN`, decisions `AD-NN`, pipelines `PL-NN` (steps `PL-NN.<function>`), test cases `TC-NN`, stages `S<n>`, milestones `M<n>`, tasks `M<n>-T<nn>`, review findings `M<n>-R<nn>`, contract symbols `<component>.<symbol>`, constraint rules `CR-NN`, references `RF-NN`, probes `PB-NN` (checks `PB-NN.C<n>`). Agents read by ID, not by file:

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
| Probe | `Draft` → `Ready` → `Answered (pass\|fail)`, or `Waived` (your call, with your reason); a decision citing a probe stays `Proposed` until then, and no milestone the probe reaches can be planned |
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
→ build-planning (New): cut each designed stage into milestones, M1 plan (interface → step spines → wiring and thicken → system, dependency graph, checkpoints), AGENTS.md ─ approve
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

A **stage** is an outcome the user agreed in `idea-refine` ("See my spending"), unsized. Once its pipelines are approved, `build-planning` **cuts** it into **milestones** along dependency lines: vertical slices that each run end to end, the first a walking skeleton through every package the stage touches. Only one milestone is active at a time, so independent tracks stay inside one milestone, building side by side; a cut happens only where a later slice needs an earlier one's outputs, and the milestone row's `Depends` names them (`M1 (stats.Cov, PL-01 output)`). A milestone's size is its critical path, the longest `Depends on` chain, at most about 15.

### Interface first

A milestone is planned so many agents build it at once. Its unit is the pipeline step: one owner, one module, typed `In → Out`.
1. **Interface task** (solo, first): freezes every step boundary that crosses tasks, as code: each boundary type in its owner's `types.py` with a schema and one sample per case in `tests/contracts/<id>.<Type>/`, every step signature with the body `raise NotImplementedError("<task id>")` naming the task that replaces it, a fixture-backed fake for each call from another pipeline or package, and the exports.
2. **Step spines**, one per step, all at once, each writing only its owner module; **testers** of every split task start beside them, against the frozen signatures and samples.
3. **Wiring**, one per pipeline (entry, trigger, smoke test, on the fakes), beside the **thicken** tasks.
4. **System task** (last): swaps each fake for the real provider and runs every smoke and golden case on the real chain.

Every task declares `**Kind:**` and an exclusive `**Writes:**`: two tasks with no `Depends on` path between them never write the same file. The plan's `## Dependency graph` gives every edge between tasks a kind (`data`, `call`, `file`, `code`, `contract-change`, `order`) and either the interface that mitigates it, so the tasks run side by side, or the reason it can't (`none: …`), so `Depends on` orders them. Waves are derived from the graph, never typed.

Mocking a step is forbidden: every spine is a real baseline, and a step's consumer builds against the type's sample. The interface stubs are the floor's one stub carve-out: allowed while the task they name is open, failing the gate once it's done and the milestone exit if any is left.

Once the interface task is done, its contract folders are frozen (CR-09): `build-setup`'s protected list covers every `tests/contracts/` folder that exists at a task's base, no other task's `Writes:` names its types, and the plugin's `dt guard` asks before any edit no open interface task covers. A frozen interface changes only through `architecture-design` Revise and a new interface task. Builders never write `tasks/`: the orchestrator ticks tasks and records findings after each merge.

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
| Probes (`api-probe`) | What a chosen source **really returns**, checked before the build freezes types from it | "Sharadar's `close` is split-adjusted; raw prices are `closeunadj` only, with no raw open, high or low" |
| Pipelines (`pipeline-design`) | The **spine** version of each step: a real baseline, never a mock (only a call to another pipeline or package may be faked, across a frozen interface) | Sample covariance before shrinkage; equal weight before min-variance |
| Tests (`test-planning`) | **Known-answer** cases: planted signals, pure noise, closed forms, and the model evaluation protocol | Every cleaned eigenvalue ≤ the Marchenko–Pastur edge on pure noise |

A data source is named earlier only when it's a fixed constraint, such as your own database or a required benchmark. Thicken tasks put data loading, leak checks and evaluation before any model.

## Tooling: `dt` and hooks

`scripts/dt.py` parses every doc with one parser, so skills, hooks and agents see the same IDs, statuses and sections. Every skill starts with `dt status --skill <name>`; mechanical edits (`dt tick`, `dt prebuild-clear`, `dt archive`, `dt finding`, `dt roadmap`, `dt base`) go through `dt` so approved docs aren't reset to Draft. For the build, `dt status` reports the active plan's critical path, waves and width, `dt ready` lists every task that can start now with its `Writes:`, so an orchestrator dispatches a whole wave at once, and `dt plan --json` exports the plan for workflow-analyzer's plan map. Reference: [scripts/README.md](scripts/README.md).

The plugin's hooks run in every session, subagents included:

| Event | Runs | Effect |
|---|---|---|
| SessionStart | `dt status --summary` | Active milestone, next task, blocked tasks and docs awaiting approval (silent outside dev-team projects) |
| PreToolUse (Read, Edit, Write) | `dt guard` | Asks you before any `tests/fixtures/**/expected.json` change; denies writes to `tasks/archive/**` and `probes/*/evidence/**`; denies any access to `.env` files and `probes/*/out/**` |
| PostToolUse (Edit, Write) | `dt lint --hook` | Lint problems in docs and plans go straight back to the agent that made the edit |
| Stop | `dt lint --hook` | Reports problems in changed docs; never blocks |

Code tooling (`check.sh`, Ruff, mypy, import-linter, the agent role files and their hooks) is project-owned and written by `build-setup`, so CI and humans have it without the plugin.

## Skills

| Skill | Phase | Produces |
|---|---|---|
| [`idea-refine`](skills/idea-refine/SKILL.md) | Define | `docs/brief.md`, `docs/ideas/*.md`, roadmap stages and their Skills |
| [`reference-intake`](skills/reference-intake/SKILL.md) | Any time | `docs/references.md` (one read-only agent per new or changed file) |
| [`api-probe`](skills/api-probe/SKILL.md) | Design, or any time | `docs/probes.md`, `probes/PB-NN-*/` (a probe script per unknown, from the official docs; you run any check that needs your keys) |
| [`spec-writing`](skills/spec-writing/SKILL.md) | Define | `docs/spec.md` |
| [`architecture-design`](skills/architecture-design/SKILL.md) | Design | `docs/architecture.md`, `docs/packages/*/{architecture,contract}.md` |
| [`pipeline-design`](skills/pipeline-design/SKILL.md) | Design | `docs/packages/*/pipelines.md` |
| [`test-planning`](skills/test-planning/SKILL.md) | Plan (optional) | `docs/packages/*/tests.md`, `tests/fixtures/**` |
| [`build-planning`](skills/build-planning/SKILL.md) | Plan | Roadmap milestone rows (each stage cut into slices), `tasks/plan.md` (tasks with `Writes:`, the dependency graph), `tasks/todo.md`, AGENTS.md doc map |
| [`build-setup`](skills/build-setup/SKILL.md) | Bar | `CONSTRAINTS.md`, tool config, `scripts/`, `.claude/agents/` |

Design notes: [design/planning-stage.md](design/planning-stage.md), [design/build-setup.md](design/build-setup.md), [design/interface-first-design.md](design/interface-first-design.md), [design/probes.md](design/probes.md), [design/requests.md](design/requests.md).
