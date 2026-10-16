# Planning Stage — Design

**Status:** Ready to build · **Last updated:** 2026-10-16 · **Start here:** §13 Implementation handoff

Covers what happens after `architecture-design` is approved and before any code: pipelines, file layout, test plans, build plans, skill routing, and how all of it evolves across new, extend, grow, replan, rebuild and debug. Building itself is agent-skills' `/build`; this design only makes sure builders get small, correct inputs.

Inputs to this design: agent-skills `planning-and-task-breakdown`, `incremental-implementation`, `test-driven-development`, `context-engineering`, `constraint-driven-development`, `definition-of-done`; dev-team2's three skills; eval iteration 1.

---

## 1. Decisions at a glance

1. **Three new skills after architecture:** `pipeline-design` → `test-planning` (optional) → `build-planning`. Each stops at a review gate.
2. **One folder per package:** `docs/packages/<pkg>/` holds everything about a package, in single *and* multi-package repos. Grow then moves sections between folders; it never rewrites paths.
3. **Intent until code exists, then code is truth.** Planned layout and entry-function sketches are *pre-build sections*: the spine task replaces them with a pointer to `dt layout`. Contracts stay as docs but are checked against code.
4. **Build plans are per milestone, not per package.** `tasks/plan.md` is always the active milestone, in agent-skills' `/build` format (plan.md plus todo.md). Every task names its package. Solo tasks can run under `/build` as-is; split tasks need the build-phase orchestrator (`build-phase-notes.md`).
5. **Repo-unique ID on every addressable unit.** Agents read by ID (`dt section PL-02 TC-06`), not by file. Each task lists the IDs it needs, and `dt context <task>` assembles them.
6. **New repo doc `docs/roadmap.md`** holds milestone order. Stages live there, not in brief goals. That fixes eval root cause #1, "the brief never re-aims".
7. **No review-plan file.** The standing bar is agent-skills' `CONSTRAINTS.md` plus a Definition of Done, written once. Checkpoints live in the plan.
8. **Depth:** design everything known, but write task-level plans only for the next milestone. Later milestones go into `tasks/queued/` only when the user asks. Either way, every milestone starts with a **kickoff check** that revalidates the docs against the code.
9. **Deterministic by default.** One shared CLI (`dt`) in the plugin's `scripts/` parses every doc. Status, IDs, coverage, context packets and lint come from it, not from an agent reading and counting. Plugin hooks run it at session start, guard oracle files, and lint doc edits (§10).
10. **Milestones are capabilities, not packages.** A package can span several milestones, and a milestone can touch several packages (§6).
11. **Planning never writes or runs code.** Each skill and build role writes only the paths in its row of the write matrix (§10). Mechanical edits to approved docs go through `dt`.

---

## 2. Your proposed docs: verdicts

| Proposed | Verdict | Why |
|---|---|---|
| Contract | **Keep**, per package, written by `architecture-design` | Consumers of a package read only this, not its whole architecture. Moved out of the architecture doc's Interfaces section. |
| Planned file structure | **Keep, as a section of `pipelines.md`** | The layout follows from the pipelines (entry module plus step owners), so it's approved alongside them. It's a pre-build section: the spine task swaps it for `dt layout`. |
| Spine plan | **Drop as a file** | The spine is a *Spine version* column in the pipeline step table plus Phase 0 of the milestone plan. A separate file would restate both. |
| Review plan | **Drop as a file** | Review criteria are repo-wide and stable, so they go in the Review section of `CONSTRAINTS.md` (see [build-setup.md](build-setup.md)). Checkpoint blocks sit in the plan where builders hit them. |
| Test plan | **Keep**, optional, per package | `tests.md` is the index and strategy; fixtures live in `tests/fixtures/`. |
| Build plan | **Keep, per milestone** in `tasks/` | Milestones cross packages (the system spine always does). Per-package plans would split one milestone's ordering across files. A package-scoped agent filters tasks by `Package:`. |
| Pipeline plan | **Keep**, `pipelines.md` per package | System pipelines that cross packages stay general and live in the root architecture. |

---

## 3. Document map

```
AGENTS.md / CLAUDE.md          doc map + how to read sections + project skills (≤ 25 lines)
CONSTRAINTS.md                 standing quality bar, incl. pipeline readability rules + Done   build-setup
docs/
  brief.md                     why                                  idea-refine
  ideas/<idea>.md              why, per addition                    idea-refine
  roadmap.md                   NEW  milestone order and outlines     idea-refine adds rows, build-planning fills
  spec.md                      what                                 spec-writing
  architecture.md              how: single = full doc               architecture-design
                                    multi  = system map, system pipelines, all ADs
  packages/<pkg>/
    architecture.md            multi only (moved from docs/architecture/<pkg>.md)
    contract.md                public API, invariants, errors        architecture-design
    pipelines.md               NEW  pipelines + pre-build layout      pipeline-design
    tests.md                   NEW  test strategy + case index        test-planning (optional)
tests/fixtures/<pkg>/TC-NN/    source/, input.json, expected.json    test-planning
tests/intent/<pkg>/            intent tests from TC cases + acceptance  tester (build)
tests/unit/<pkg>/              unit tests                            implementer (build)
scripts/check.sh, scripts/hooks/, .claude/agents/                    build-setup (see build-setup.md)
tasks/
  plan.md                      active milestone (agent-skills /build format, extended)   build-planning
  todo.md                      active milestone checklist
  queued/M<n>-<slug>.md        later milestones planned in detail (optional)
  archive/M<n>-<slug>.md       finished milestones; not in the doc map
```

| Doc | Size budget | Lifecycle |
|---|---|---|
| `roadmap.md` | 1 table + 3-6 lines per milestone | Rows only; status is derived by script |
| `contract.md` | ≤ ~8 lines per symbol + 12 | Draft → Approved; Revise reopens it |
| `pipelines.md` | ≤ ~35 lines per pipeline (step table and entry sketch included) + 10, plus the pre-build layout section | Draft → Approved |
| `tests.md` | ≤ ~10 lines per test case + 15; fixtures stay outside | Draft → Approved; expected outputs change only with approval |
| `tasks/plan.md` | ≤ ~400 lines | Draft → Approved → In progress → Done → archived |

Package docs are budgeted per unit because the cost per unit is steady (eval iteration 5: 4–6 lines per symbol, 21–32 per pipeline, 5–8 per test case) while the number of units grows with the package. A separate per-file ceiling (contract.md 200, pipelines.md 300, tests.md 300 lines) is a warning that the package holds too much: `architecture-design` considers a Grow.

**Single package** uses the same tree: root `architecture.md` is the full doc, and there's one `docs/packages/<pkg>/` without an `architecture.md`. Its `contract.md` has one `### <component>.<symbol>` section per public symbol, grouped under one `## <component>` per component. When a component later becomes a package, its group moves with it.

---

## 4. IDs and section reads

| Unit | ID | Defined in | Notes |
|---|---|---|---|
| Goal | Goal N | brief | Project-level outcomes. Stages go in the roadmap, not here. |
| Requirement | `CODE-NN`, `DATA-NN`, `QR-NN` | spec | Existing |
| Decision | `AD-NN` | root architecture | Existing |
| Package / component | kebab id | architecture | A component id becomes the package id on Grow |
| Pipeline | `PL-NN` | `pipelines.md` or root architecture | **Repo-unique**, never renumbered; keeps its ID when moved between packages |
| Step | `PL-NN.<function>` | pipelines step table | The step name *is* the function the entry calls |
| Test case | `TC-NN` | `tests.md` | Repo-unique; also the fixture folder name |
| Milestone / task | `M<n>`, `M<n>-T<nn>` | roadmap / plan | |
| Review finding | `M<n>-R<nn>` | plan, under its checkpoint | Needs a disposition (fix task or reason) |
| Contract symbol | `<pkg>.<symbol>` | `contract.md` heading (`### stats.estimate_cov: Covariance estimate`) | Lets `Read:` point at one function's contract |
| Constraint rule | `CR-NN` | CONSTRAINTS.md | See [build-setup.md](build-setup.md) |

**Rules**
- Every ID is a heading (`## PL-02: Covariance report`), or a bold line in the spec. `dt section <ID>…` prints only those sections, searching all docs. Because IDs are repo-unique, no path is needed.
- Each task's `Read:` field lists the IDs (and files) a builder needs. `dt context M2-T03` prints the task plus every section it lists. That output is the builder's whole context packet.
- New IDs come from `dt next-id <prefix>`, never from counting by hand.
- **Retire, don't keep in full.** A retired pipeline, case or decision collapses to one struck line with date and reason. Eval iteration 1 found superseded decisions kept in full drove 2-3× doc growth.
- **Docs carry no history.** Git is the history. Changelog rows are one line. Finished milestones move to `tasks/archive/`, which is outside the doc map.

---

## 5. Skills

### 5.0 Shared rules for every planning skill

- **Read-only toward code.** A planning skill writes only its row of the write matrix (§10). It never creates or runs anything under `src/`, `tests/intent/` or `tests/unit/`. Fixtures are data, so `test-planning` may write them. "Approved, go ahead" means *start the next planning skill*, never *start coding*.
- **Start with `dt status --skill <name>`.** Take the mode, gaps and next IDs from its output.
- **Interview one question at a time**, each with a guess and a default (agent-skills `interview-me`). Ask only about what the user must decide: workflows, oracles, scope cuts. Infer everything else and list it as an assumption.
- **Every review gate lists:**
  - what was written
  - **ASSUMPTIONS:** names, triggers, types, order and sizes the skill chose
  - open questions
  - anything left uncovered

  Then the turn stops.
- **Approval is an unambiguous yes** in the user's own words. A hedge ("looks fine I guess") on an oracle, a loosening or a dropped task is not approval; ask again. Approval sets `Status: Approved`.
- **Commits:** on approval, offer to commit the approved docs and fixtures; commit only on a yes. At milestone kickoff the plan header records `**Base:** <sha>`. `build-setup`'s guard-the-bar diff and protected-path check compare against it.
- **No live user** (a headless run): don't invent confirmations. Write the doc, put the needed confirmations under Open questions, and leave it at Draft.

### 5.1 `architecture-design`: small changes

- Writes `docs/packages/<pkg>/contract.md`; the Interfaces section becomes a link to it.
- Multi-package: package docs move to `docs/packages/<pkg>/architecture.md`.
- Multi-package: a **System pipelines** section with `PL-NN` entries. Each is ordered package → package steps over named contracts, with no functions and no files.
- Project layout: package-level folders only. The file level belongs to `pipelines.md`.
- **Explicit Grow triggers.** No eval run ever entered Grow, so the skill must check these on Extend:
  - The new milestone brings a dependency stack the rest shouldn't carry (torch, gym).
  - A one-way dependency is worth enforcing (data must never import models, to prevent leakage).
  - A package exceeds ~3 pipelines or ~12 modules, or its docs no longer fit a 2k-line agent context.
  - A part runs or deploys on its own (a paper-trading service).
- After approval: stop, then point to `pipeline-design`. Eval: "Approved, go ahead" led straight to an improvised plan and code.

**`contract.md` template.** There is one `###` section per public symbol. A single package groups symbols under `## <component>`.
````markdown
# stats — Contract
**Package:** stats · **Status:** Approved · **Last updated:** 2026-10-15 · **Architecture:** [../../architecture.md](../../architecture.md)

### stats.estimate_cov: Covariance estimate
`def estimate_cov(returns: Returns, *, method: CovMethod = "sample") -> Cov`
- **Invariants:** N×N for T×N input; symmetric; positive semi-definite; no NaN out when none in
- **Errors:** `ValueError` if T < 2 or the input contains NaN
- **Used by:** PL-02, PL-03
````

### 5.2 `pipeline-design`

**Input:** approved architecture. **Output:** `pipelines.md` for each package in scope (the next milestone's packages, or all of them in up-front mode).

**Process**
1. Run `dt status --skill pipeline-design`: mode, packages in scope, spec IDs and components not yet on any pipeline.
2. **Ask which workflows the user will actually run.** Confirm them; don't invent them. Each workflow becomes a pipeline with one entry function.
3. For each pipeline: entry (file and function), trigger (CLI or call), step table, entry sketch.
4. Derive the planned layout from the pipelines: one entry module per package; one module per step owner. In a single package, each component gets its own subfolder and exports its contract from `__init__`, with cross-component imports only through it. That makes Grow a folder move.
5. Check the readability rules (below).
6. Review gate: summarize the pipelines, the layout, and anything uncovered. Stop.

**Readability rules** (these also go in `CONSTRAINTS.md` so builders and reviewers enforce them):
- One entry function per pipeline. It reads top to bottom as calls to its named steps.
- Each step is owned by one component, and its function lives there.
- No registries, plugin dispatch or config-driven wiring unless an `AD-NN` says so.
- A new abstraction needs a second real implementation or a seam the architecture named.
- Every step's spine version is real and minimal, often the baseline (sample covariance, equal weight, TWAP). Never a mock. It stays in the code as the thing upgrades must beat.

**Template**

````markdown
# stats — Pipelines
**Package:** stats · **Status:** Draft · **Last updated:** 2026-10-15 · **Contract:** [contract.md](contract.md)

## PL-02: Covariance report
**Entry:** `src/quant/stats/pipeline.py::run_cov_report` · **Trigger:** `python -m quant.stats cov-report`
**Covers:** STAT-01–STAT-04, QR-02

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `load_returns` | data | universe, dates → Returns (T×N) | synthetic GBM returns | DATA-01 |
| 2 | `estimate_cov` | stats.cov | Returns → Cov | sample covariance | STAT-02 |
| 3 | `clean_eigen` | stats.rmt | Cov, T → Cov | no cleaning (baseline) | STAT-03 |
| 4 | `pca` | stats.pca | Cov → Factors | full eigendecomposition | STAT-01 |
| 5 | `write_report` | stats.report | Factors → CovReport | print table | STAT-04 |

### Entry sketch (pre-build — removed by spine task)
```python
def run_cov_report(cfg: CovConfig) -> CovReport:
    returns = load_returns(cfg.universe, cfg.start, cfg.end)
    cov = estimate_cov(returns)
    cov = clean_eigen(cov, n_obs=len(returns))
    factors = pca(cov)
    return write_report(factors, cfg.out)
```

## Planned layout (pre-build — removed by spine task)
```
src/quant/stats/
  __init__.py   contract exports only
  pipeline.py   PL-02, PL-03 entry functions
  cov.py  rmt.py  pca.py  report.py
tests/intent/stats/  tests/unit/stats/
```

## Open questions
- Should `clean_eigen` take T from Returns instead of a parameter? (assumed: parameter)

## Retired
- ~~PL-01: Raw eigen dump~~ Retired 2026-11-02: folded into PL-02 (AD-09)
````

**Modes**
| Mode | When | Does |
|---|---|---|
| New | Package has no `pipelines.md` | Full process |
| Extend | New spec IDs or components land in the package | Adds pipelines or steps; existing IDs untouched |
| Revise | The build caught something: a step is replaced, split or reordered | Edits the step table; status back to Draft; affected tasks pause until re-approved |
| Grow | Architecture Grow split the package | Moves each `PL-NN` section to its new package by owner. A pipeline that now crosses packages becomes a system pipeline in the root, with a package-local pipeline on each side |
| Sync | Code drifted (entry calls ≠ step table) | Lists mismatches; user picks which side changes |

### 5.3 `test-planning` (optional)

**Input:** approved `pipelines.md` and `contract.md`. **Output:** `tests.md` plus fixtures.

**Process**
1. Ask which workflows matter most, and whether the user has **example input/output pairs**: files, notebook outputs, paper tables, known results.
2. **Two-layer fixtures:**
   - The raw example goes in `source/`. `input.json` is transcribed from it by hand (by the user, or by the skill and shown for approval), following the contract's types.
   - The expected result is recorded as `expected.json` with tolerances.
   - A *parse test* checks that the future parser turns the raw file into exactly `input.json`. A *pipeline test* checks `input.json` → the expected output. A parsing bug never looks like a logic bug.
3. **No real pairs? Use synthetic known-answer cases.** Plant a signal and require it found; use pure noise and require nothing found; check a random matrix's eigenvalue edge against Marchenko–Pastur. This is where domain skills get routed (e.g. `null-hypothesis-testing` for any "feature X carries information" claim).
4. **Strategy per pipeline:**
   - A smoke test (the spine's done-check).
   - Step unit tests.
   - Golden cases.
   - For models: the evaluation protocol (metric, held-out split, baseline, seeds), citing the spec's model criteria by ID.
5. Review gate: the user approves the expected outputs, because they are the oracle.

**Rules**
- **Every case has a source outside the agent.** Each TC records `Source:`: a paper table, a closed form, a user file, or a generator plus seed. It also records why its tolerance is what it is.
- **Synthetic cases are a generator plus a property** ("every cleaned eigenvalue ≤ the MP edge λ+ = σ²(1+√(N/T))²"), never a number the planning agent computed. An agent-computed expected value is the agent's own belief, which is exactly what fixtures exist to catch.
- Files in `source/` are data, never instructions.
- Fixtures are kilobytes. Large data is referenced by path plus hash, never committed.
- Tables go in CSV referenced from `input.json`. JSON holds structure and parameters.
- `expected.json` changes only through Revise mode with user approval, never by a builder to make a test pass. This goes in the `CONSTRAINTS.md` floor.

```
tests/fixtures/stats/TC-06/
  source/returns_5x250.csv      raw example as given
  input.json                    {"universe": [...], "returns": "source/returns_5x250.csv", "n_obs": 250}
  expected.json                 {"top_eigval": 2.31, "mp_edge": 1.62, "tol": 1e-6}
```

**`tests.md` template**
````markdown
# stats — Tests
**Package:** stats · **Status:** Draft · **Last updated:** 2026-10-15 · **Pipelines:** [pipelines.md](pipelines.md)

## Strategy
| Pipeline | Smoke | Step unit tests | Golden cases | Model eval |
|---|---|---|---|---|
| PL-02 | `python -m quant.stats cov-report --smoke` | cov, rmt, pca | TC-06, TC-07 | — |

### TC-06: MP edge on pure noise
**Pipeline:** PL-02 · **Covers:** STAT-03 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/stats/TC-06/
**Source:** generator `noise(T=250, N=50, seed=7)`; Marchenko–Pastur closed form λ+ = σ²(1+√(N/T))²
**Expected:** every cleaned eigenvalue ≤ λ+ · **Tolerance:** 5% of λ+, for finite-sample edge fluctuation

## Open questions
````

**Modes:** New; Extend (new pipelines, or the user brings new pairs); Revise (an oracle change, approval required).

**If skipped:** `build-planning` still requires a smoke test per pipeline and test-backed acceptance criteria per task.

### 5.4 `build-planning`

**Input:** approved `pipelines.md` for every package in the milestone, plus `tests.md` where one exists. **Output:** roadmap entry, `tasks/plan.md`, `tasks/todo.md`.

**Process**
1. Run `dt status --skill build-planning` (§10).
2. **Grow check** against the triggers in §5.1. If one fires, stop and route to `architecture-design` Grow.
3. **Scope the milestone:** spec IDs, packages, pipelines, exit criteria. Spec IDs deliberately left for later are listed under Deferred, so coverage stays explicit.
4. **Phase 0, Spine:** one task per new pipeline, with the system spine first in multi-package. Acceptance:
   - The pipeline runs end to end on fixture or synthetic data.
   - A smoke test is committed.
   - The pre-build sections are replaced with a `dt layout` pointer.
5. **Thicken:** one task per step upgrade, riskiest first. In ML that means data loading, leak checks and evaluation before any model. **Split a task** when:
   - it needs more than one session
   - it has more than 3 acceptance bullets
   - it touches two packages or two steps
   - its title contains "and"

   (agent-skills `planning-and-task-breakdown`.)
6. **Route skills.** Read the descriptions of project skills (`.claude/skills/*/SKILL.md`) and installed plugin skills, then assign them per task. The plan header lists skills in use. A task needing a skill that doesn't exist is flagged, not silently built without it. Eval: the `null-hypothesis-testing` hand-off happened only by chance.
7. **Set each task's build mode** by rule:
   - `split` (tester, then implementer) when the task adds or changes behavior with a checkable outcome: anything a TC case, Given/When/Then criterion or model criterion covers.
   - `solo` (one agent plus the gate hooks) for spine, refactor, glue and doc-sync tasks.
   - `dt status` flags a task whose mode breaks the rule. Overriding it needs a one-line reason on the task.
8. **Checkpoints** every 2-3 tasks, plus a milestone exit checkpoint. Each one is reviewed by a separate read-only reviewer agent.
9. **Dependencies and parallel groups:**
   - `Depends on` must resolve, be acyclic and point only backward.
   - After the spine, independent tasks get `**Parallel:** G<n>`. Tasks that share a file in `Files likely` or a contract symbol can't share a group.
   - A split task may only test symbols that already exist (from the spine or an earlier solo task), so the tester never writes against a guess.
   - Contract changes come first, then the tasks that depend on them.
10. Review gate. Stop.

**Sizing** (lint-enforced; agent-skills caps tasks at about 5 files):
| Size | `Files likely` | Other limits |
|---|---|---|
| XS | 1 | |
| S | 1–2 | |
| M | 3–5 | |

Every task also has at most 3 acceptance bullets, one Package and one Step (or a reason on the task), and no "and" in its title. After Phase 0, every `Verify:` includes its pipeline's smoke command, so each task leaves the system working.

**Task template** (extends agent-skills' template). `**Blocked:** <reason>` is added when Revise pauses a task. `dt status --summary` shows blocked tasks.

```markdown
### M2-T03: Ledoit-Wolf shrinkage behind `estimate_cov`
**Package:** stats · **Step:** PL-02.estimate_cov · **Covers:** STAT-02, QR-02 · **Size:** S · **Mode:** split
**Skills:** data-science
**Read:** PL-02, TC-06, STAT-02, stats.estimate_cov
**Acceptance:**
- [ ] TC-06 passes within tolerance; sample-cov baseline remains selectable for comparison
- [ ] PL-02 smoke test still passes
**Verify:** `pytest tests/intent/stats tests/unit/stats -k cov` · `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate --pkg stats`
**Depends on:** M2-T01 · **Parallel:** G1 · **Files likely:** src/quant/stats/cov.py, tests/unit/stats/test_cov.py
```

**`plan.md` skeleton.** Tasks and checkpoints use the blocks above and below. Tasks stay in markdown, not an external tracker, because `dt` parses them.
````markdown
# M2: Classical portfolios — Plan
**Milestone:** M2 · **Status:** Approved · **Base:** 3f2c1ab · **Last updated:** 2026-11-03 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** min-var, risk parity and HRP backtests beat equal weight on Sharpe out of sample; PL-03 golden cases pass.
**Covers:** PORT-01–PORT-06, QR-04 · **Deferred:** PORT-07 (to M4: needs forecasts)
**Skills:** data-science (stats steps)

## Phase 0: Spine
### M2-T01: …
## Phase 1: Thicken
### M2-T02: …
### Checkpoint after M2-T03
## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| HRP clustering unstable on short windows | wrong weights | TC-12 pins a known dendrogram |

## Open questions
## Replan notes
- 2026-11-05: split M2-T04 (too large); dropped none
````

**`todo.md`** holds task state: one line per task, `- [ ] M2-T03 Ledoit-Wolf shrinkage (stats, S, split)`. Status reads come from here. `dt lint` checks that its task IDs match `plan.md`'s.

**Checkpoint block** (run by the reviewer agent against CONSTRAINTS.md's Review section; findings are recorded under the block, see [build-setup.md §7](build-setup.md))

```markdown
### Checkpoint after M2-T04
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] No new abstraction without a second implementation or an AD
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `dt layout` output reviewed; Definition of Done holds
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition
```

**Modes**
| Mode | When | Does |
|---|---|---|
| New | No roadmap or plan | Roadmap, plus the M1 plan. **If `tasks/plan.md` exists with no dev-team2 header** (from agent-skills' `/plan`, say) and has unchecked tasks: stop and ask. Never overwrite it |
| Extend | A new idea is specced and designed | Adds the milestone. If a milestone is active, the new one is queued, never merged into the active plan unless the user asks |
| Replan | Something learned during the build, or a major bug | Reorders, splits or adds tasks. Never drops an unchecked task silently: drops are listed for approval. One-line replan note in the plan |
| Advance | All tasks and the exit checkpoint done | Runs the sequence below. `tasks/plan.md` is never left missing: until the next plan is approved, it holds a stub with `Status: Between milestones`, so agent-skills' `/build auto` can't start its own planner |

**Advance and kickoff sequence.** Each [gate] ends a turn.
1. Exit checkpoint: the reviewer's findings are all dispositioned, then you approve the milestone [gate].
2. `build-setup` Ratchet: record measured values, offer tightenings [gate].
3. `dt archive`: move the plan to `tasks/archive/`, write the stub, add the roadmap outcome line.
4. **Kickoff check:** `dt status`; Sync `pipelines.md` and `contract.md` against the code [gate if mismatches]; review the queued plan, if any, against what changed.
5. Write the next milestone's plan (Extend), recording `Base` [gate].
6. `build-setup` Extend for new packages, dependencies or Grow [gate].
7. Build.

This is what makes up-front and sequential planning land in the same place.

### 5.5 Anatomy seeds

Content for each skill's agent-skills anatomy sections. The description says *when* to use the skill, never the workflow.

| Skill | Use when / Not for | Rationalizations → reality | Red flags | Verification |
|---|---|---|---|---|
| pipeline-design | Architecture approved and a package has no or stale `pipelines.md`. Not for choosing technologies (architecture) or ordering work (build-planning) | "I can infer the workflows" → ask · "A registry keeps it extensible" → needs an AD · "The spine step can be a mock" → it must be a real baseline | A step with two owners · logic in the entry sketch · a layout module on no step | `dt status` shows no uncovered IDs · every PL has entry, trigger and spine column · workflows confirmed by the user · assumptions listed |
| test-planning | Pipelines approved and you want golden cases. Not for writing test code | "A quick script gives the expected value" → circular · "No real data, so no golden cases" → use known-answer cases | An expected value with no source · no parse layer · an oracle approved by a hedge | Smoke test plus ≥ 1 golden case per PL · a source and tolerance reason per TC |
| build-planning | Pipelines approved and the next milestone needs tasks. Not for agent-skills `/plan` output | "The old plan is stale, I'll overwrite it" → stop and ask · "I'll detail every milestone" → perishable · "No skill fits, I'll build without one" → flag it | A split task testing a missing symbol · parallel tasks sharing files · a task over M | §13 assertions plus agent-skills' planning verification list |
| build-setup | Plan approved, before the first build of a milestone. Not for changing rules mid-task | Reuse agent-skills `constraint-driven-development` rationalizations | Same | Same, plus `check.sh gate` passed once on the committed skeleton |

---

## 6. Roadmap

```markdown
# Quant Lab — Roadmap
**Last updated:** 2026-10-15

| Milestone | Name | Source | Packages | Pipelines | Depends | Status* |
|---|---|---|---|---|---|---|
| M1 | Data + stats | brief | quant | PL-01, PL-02 | — | Building |
| M2 | Classical portfolios | ideas/classical-portfolios.md | quant | PL-03 | M1 | Designed |
| M3 | Features + info gain | ideas/features-ml.md | features, stats | PL-04 | M2 | Idea |

*Written by `dt roadmap` from doc statuses and todo checkboxes; never hand-edited.

## M1: Data + stats
**Exit:** PCA and MP cleaning on 10y of daily returns, survivorship-free; PL-01/PL-02 golden cases pass.
**Outcome:** Done 2026-11-02 — switched to Ledoit-Wolf before MP cleaning (AD-07).
```

- **Derived status:** Idea → Specced → Designed → Planned → Building → Done. `dt roadmap` reads it from the idea, spec, pipelines and plan statuses and rewrites the column.
- **Ownership:** `idea-refine` adds a row when a stage is accepted. `build-planning` fills in packages, pipelines, exit criteria, outcome and the plan link.

### What a milestone is

A milestone delivers one working capability end to end: a pipeline you can run, plus the spec IDs it satisfies. Packages are where its code lands. Neither contains the other.

- **One package, several milestones.** In a quant repo, `data` might carry M1 prices, M2 financials, and later M5 point-in-time store.
- **One milestone, several packages.** A stats milestone that needs survivorship-free sampling adds tasks to `data`, each tagged `Package: data`. If `data`'s contract changes, that's an architecture Revise during the milestone's planning, and `data/pipelines.md` gets an Extend.
- **Slice by pipeline, not by layer.** "Prices → financials → cleaning → storage" mixes the two. Prices and financials are pipelines, so they can be milestones. Cleaning and storage are *steps* inside those pipelines: M1's spine ships prices with naive cleaning and plain files, and later tasks thicken those steps. A storage overhaul becomes its own milestone only when it's large and delivers something testable on its own (e.g. "point-in-time queries pass the leak cases").
- **Size, per track:** the Phase 0 spine plus the longest `Depends on` chain after it, at most about 15 tasks (`dt lint` `milestone-size`). Parallel groups that don't depend on each other don't add up, so independent tracks stay in one milestone however many tasks the plan holds; the plan's ~400-line budget bounds the total. Only one milestone is active at a time, so splitting independent tracks would serialize them. Split only where a later part needs an earlier part's outputs. A single task isn't a milestone; it belongs in an existing one.

---

## 7. Up-front vs sequential

| Stage | Up-front (all six stages known) | Sequential (one stage at a time) |
|---|---|---|
| idea-refine | Brief with project-level goals; one roadmap row per stage | Brief, then an idea file and roadmap row per stage |
| spec / architecture | All stages specced and designed | Extend per stage |
| pipeline-design | All packages (later ones may change at kickoff) | Packages for the next milestone |
| test-planning | Optional, per package | Optional, per package |
| build-planning | Roadmap for all; **task plan for M1 only** by default, `queued/` for the rest if asked | Plan per milestone as it comes |
| Every milestone start | Kickoff check | Kickoff check |

**Why task plans default to the next milestone only:** task lists are the most perishable doc. Eval iteration 1 found designs written ahead of the build went stale (quant: a stale `Guard` interface, a stage-1 budget carried forward). Pipelines and contracts survive much better than task lists.

---

## 8. Flows (quant example)

**A. From scratch, single package (M1 data + stats)**
```
idea-refine (New) → brief + roadmap M1 ─ accept
→ spec-writing (New) ─ approve
→ architecture-design (New): Shape single, components data/stats, contract.md ─ approve
→ pipeline-design (New): PL-01 load/clean data, PL-02 cov report, planned layout ─ approve
→ test-planning (New, optional): TC-01..TC-08, fixtures ─ approve expected outputs
→ build-planning (New): Phase 0 spine for PL-01, PL-02 → thicken → checkpoints ─ approve
→ build-setup (New): CONSTRAINTS.md, tool config, check scripts, agent roles ─ approve
→ /build
```

**B. Extend, no Grow (M2 classical portfolios)**
```
idea-refine (Extend) → ideas/classical-portfolios.md + roadmap M2 ─ accept
→ spec-writing (Extend) → architecture-design (Extend): component portfolio; Grow check passes
→ pipeline-design (Extend): PL-03 backtest; layout adds src/quant/portfolio/
→ test-planning (Extend) → build-planning (Extend: queued if M1 active; Advance promotes it)
```

**C. Extend with Grow (M3 features + ML brings sklearn/torch)**
```
architecture-design (Extend → Grow trigger: new dependency stack, leak-proof direction)
  → Grow: packages data, stats, portfolio, features; AD "why now"; package docs moved
→ pipeline-design (Grow): PL-NN sections move by owner; PL-05 crosses packages → system pipeline in root
→ pipeline-design (Extend): PL-06 feature screening in features
→ test-planning: TC-20 planted-signal, TC-21 pure-noise (null-hypothesis-testing routed)
→ build-planning (Extend): M3 Phase 0 = system spine across packages first, then package spines
```

**D. Up-front, all six stages**
```
All define/design skills cover all stages → pipeline-design for all packages
→ build-planning: roadmap M1–M6, plan for M1, (optional) queued/M2…M6
→ each Advance runs the kickoff check before promoting the next plan
```

**E. Replan (learned during build).** For example, MP cleaning needs shrinkage first.
```
Step change → pipeline-design (Revise) ─ approve → build-planning (Replan) ─ approve
Decision change → architecture-design (Revise) first. Oracle change → test-planning (Revise).
```

**F. Debug**
- **Small, local bug:** agent-skills `debugging-and-error-recovery` only. If the bug was in a golden path, add a `TC-NN` case.
- **Major bug** (a contract, step or design is wrong): debug to root cause, then run E. The new regression case is a task acceptance criterion.

**G. Rebuild a package**
```
architecture-design (Revise: new AD supersedes) → pipeline-design (Revise; same PL IDs where possible)
→ build-planning (Extend: "Rebuild <pkg>" milestone, spine first)
Old implementation keeps running until the new spine passes the existing golden cases; then it's removed.
```
The golden cases are what make a rebuild safe.

**H. Advance:** exit checkpoint [gate] → build-setup Ratchet [gate] → `dt archive` (stub plan + roadmap outcome) → kickoff check → next plan [gate] → build-setup Extend [gate] → build.

**State × skill matrix**

| State | architecture | pipeline-design | test-planning | build-planning |
|---|---|---|---|---|
| From scratch | New | New | New | New |
| New milestone | Extend | Extend | Extend | Extend |
| Outgrows a package | Grow | Grow | fixtures move with the package | Extend / Replan |
| Learned during build | Revise if a decision changes | Revise if steps change | Revise if the oracle changes | Replan |
| Rebuild | Revise | Revise | reuse cases | Extend |
| Major bug | maybe Revise | maybe Revise | add case | Replan |
| Small bug | — | — | add case if golden | — |
| Milestone done | Sync | Sync | — | Advance |

---

## 9. Agent context

| Role | Gets its context from | Never reads |
|---|---|---|
| Builder (one task) | `dt context <task>` output, plus CONSTRAINTS.md and the files it edits | brief, ideas, other packages' docs, archive |
| Checkpoint reviewer | the checkpoint block, `pipelines.md` of touched packages, `dt layout`, `dt lint`, the diff | brief, ideas |
| pipeline-design | `dt status`, architecture (root + package), `contract.md`, spec sections in Covers, `dt layout` | other packages' pipelines (except contracts) |
| test-planning | `dt status`, `pipelines.md`, `contract.md`, spec DATA/QR/model criteria | plan |
| build-planning | `dt status`, roadmap, milestone packages' `pipelines.md` + `tests.md`, skill list | archive |

Target: a builder's context is under 2,000 lines (agent-skills `context-engineering`). `dt context` warns when a packet goes over.

**How context gets in, deterministically:**
- **Main session:** the SessionStart hook injects `dt status --summary`: active milestone, next task, blocked gates, and the resolved `dt` path.
- **Builder subagents:** the orchestrating session runs `dt context M2-T03` and passes the output as the subagent's prompt. The subagent never hunts for docs. (SessionStart doesn't fire for subagents; tool hooks do.)

**AGENTS.md doc map** (written by `build-planning` New, kept current by Grow and Advance). It holds no script paths; the hook supplies them.
```markdown
## Docs
- Plan with dev-team2's `build-planning`, not agent-skills' `/plan`.
- Your task's context: `dt context <M#-T##>`. Read only what it prints.
- Any section by ID: `dt section <ID>...` (e.g. PL-02 TC-06 STAT-02 AD-07)
- Package docs: `docs/packages/<pkg>/{architecture,contract,pipelines,tests}.md`
- Real layout: `dt layout <pkg>` (planned layouts are gone once the spine lands)
- Quality bar: CONSTRAINTS.md. Oracle files (tests/fixtures/*/expected.json) need user approval to change.
## Project skills
- data-science — stats steps · null-hypothesis-testing — any feature/information claim
```

---

## 10. Scripts and hooks

### Where they live

dev-team2 ships as a plugin with a root `scripts/` folder, the same way agent-skills ships `references/`. Doc tooling is never copied into the project repo. Code tooling (`check.sh`, agent files) is project-owned; see [build-setup.md](build-setup.md).

```
dev-team2/
  .claude-plugin/plugin.json
  hooks/hooks.json            calls ${CLAUDE_PLUGIN_ROOT}/scripts/dt.py
  scripts/
    dt.py                     single CLI entry
    devteam/                  stdlib-only package: one doc parser shared by every command
  skills/<skill>/SKILL.md     calls ../../scripts/dt.py (relative to the skill's own folder)
```

- **Skills** reference `../../scripts/dt.py` relative to their own folder, as agent-skills does with `../../references/`.
- **Hooks** use `${CLAUDE_PLUGIN_ROOT}/scripts/dt.py`.
- **Stdlib only**, so it runs in any project without installing anything.
- **Caveat:** installing a single skill copies only `skills/<name>/`. agent-skills has the same gap with `references/` (their issue #361). dev-team2 must be installed as a whole plugin.
- **Existing bug (fixed 2026-10-16):** the skills called `skills/<name>/scripts/...` relative to the current folder. That only works when run from inside dev-team2, so these calls move to the plugin-relative form.

### Write matrix

Who may write what. `build-setup` turns the build-role rows into path guards. Planning skills follow theirs as a rule, and `dt lint` reports violations.

| Skill / role | May write | Never |
|---|---|---|
| idea-refine | `docs/brief.md`, `docs/ideas/**`, roadmap rows | everything else |
| spec-writing | `docs/spec.md`, idea Status lines | |
| architecture-design | `docs/architecture.md`, `docs/packages/*/architecture.md`, `docs/packages/*/contract.md` | |
| pipeline-design | `docs/packages/*/pipelines.md` | `src/**`, tests code |
| test-planning | `docs/packages/*/tests.md`, `tests/fixtures/**` | `src/**`, tests code |
| build-planning | `tasks/plan.md`, `tasks/todo.md`, `tasks/queued/**`, roadmap fill-ins, AGENTS.md doc map | `src/**`, tests code |
| build-setup | CONSTRAINTS.md, tool config in `pyproject.toml`, `scripts/**`, `.claude/agents/**`, CI | `src/**` |
| tester (build) | `tests/intent/**` | everything else |
| implementer / solo (build) | `src/**`, `tests/unit/**` | protected paths (build-setup §4) |
| reviewer (build) | nothing; the orchestrator records findings with `dt finding` | everything |
| `dt` (mechanical) | `dt prebuild-clear` (removes pre-build sections when a spine task is checked), `dt archive`, `dt finding`, `dt roadmap`, `todo.md` checkboxes | — |

`dt` writes files itself rather than through Edit or Write, so the Edit/Write guards don't fire, and its mechanical edits don't reset an Approved doc to Draft.

### `dt` commands

One parser means every skill, hook and agent sees the same IDs, statuses and sections.

| Command | Used by | Does |
|---|---|---|
| `dt status [--skill X] [--summary]` | every skill, SessionStart hook | Mode; upstream gates; coverage gaps (spec IDs on no component, pipeline or task, unless Deferred); pipelines with no spine task; stale or retired references; skills referenced but not installed; contract freshness (`contract.md` vs the git date of the contract module); Grow triggers. Replaced `idea-refine.sh`, `spec-status.sh` and `arch-status.py` (removed 2026-10-16 once `dt` matched their output) |
| `dt next-id <prefix>` | every writing skill | Next free `AD`, `PL`, `TC`, `CODE` etc., counting retired IDs |
| `dt section <ID>…` | everyone | Prints those sections from any doc |
| `dt context <task>` | orchestrator → builder | Every `Read:` section, then the file list, then the task section last (active material goes last, per agent-skills `context-engineering`); warns over 2,000 lines |
| `dt layout <pkg>` | spine task, reviewers, pipeline-design Sync | Real tree, each module annotated with its docstring's first line; flags entry functions whose calls don't match the step table |
| `dt lint [paths]` | PostToolUse hook, checkpoints | Duplicate IDs; references to missing or retired IDs; size budgets; an Approved doc edited without going back to Draft; a leftover pre-build section; task sizing, `Depends on` and parallel-group rules; `Verify:` missing the smoke command; `todo.md`/`plan.md` ID mismatch; findings without a disposition; a foreign `tasks/plan.md` |
| `dt roadmap` | build-planning, Advance | Rewrites the derived Status column |
| `dt guard <path>` | PreToolUse hook | Decides whether a write needs a human (below) |
| `dt prebuild-clear <PL>` · `dt archive` · `dt finding <checkpoint> <severity> <text>` | spine task, Advance, orchestrator | The mechanical edits in the write matrix |

### Hooks

| Event | Runs | Effect |
|---|---|---|
| SessionStart | `dt status --summary` | Injects active milestone, next task, blocked tasks and gates, resolved `dt` path. It doesn't reach subagents; those get `dt context` in their prompt, or `SubagentStart` if needed |
| PreToolUse (Edit, Write) | `dt guard <path>` | `tests/fixtures/**/expected.json` → **ask**: the user must approve every oracle change. `tasks/archive/**` → **deny** (only `dt archive` writes there). Plugin hooks also fire on subagent tool calls, so this covers tester and implementer too |
| PostToolUse (Edit, Write on `docs/**`, `tasks/**`) | `dt lint <path>` | Feeds problems straight back to the agent that made the edit |
| Stop (optional) | `dt lint --changed` | Reports, never blocks, so a turn can't loop |

Statuses like Approved stay a human decision. Hooks check the *format* and protect oracles; they don't approve anything.

---

## 11. Decisions and open questions

**Decided (2026-10-15)**
- Keep both a package `architecture.md` (internals) and `contract.md` (promise to consumers) in multi-package repos.
- Package docs move to `docs/packages/<pkg>/architecture.md`.
- Fixtures: JSON for structure and parameters, CSV for tables, path+hash for large data.
- Scripts ship in the plugin's `scripts/` folder, not copied into projects.
- Records are structured and script-checked wherever possible (§10).
- Task lists are written for the next milestone only. Later milestones stay as 3–6 line roadmap outlines. `tasks/queued/` is used only when the user asks.
- `idea-refine` adds a roadmap row (milestone id, name, source) when a stage is accepted. `build-planning` fills in packages, pipelines, exit criteria, outcome and the plan link. `dt roadmap` writes the Status column.

- Build model: hybrid (§5.4 step 7; build-setup.md).
- Gap review against agent-skills (`planning-gap-review.md`) folded in 2026-10-16.

**Open:** none for planning. `build-setup` has two open items (dependency arrival, CI) in [build-setup.md §11](build-setup.md).

## 12. Fixes to existing skills found in the eval

Iterations 2–4 (merged into `master` 2026-10-16) fixed the change markers, out-of-scope contradictions, vendor leakage, the `arch-status` name and the review-gate stops. Still open:
- Brief goals grow with each stage (7 goals RL, 6 quant). The roadmap is meant to fix this.
- Script paths are relative to the current folder, not the plugin (§10).

---

## 13. Implementation handoff

For the chat that implements these skills. The build-phase skills (task orchestration, `/build` wrapping) are **out of scope**; see `build-phase-notes.md`.

### Before starting
1. **Eval-fix branches: merged into `master` on 2026-10-16** (`cc9cd2c`, `4cf56f9`). Start from `master`.
2. **Read:**
   - this doc and [build-setup.md](build-setup.md)
   - `README.md`
   - the three existing skills, as the format reference
   - agent-skills `docs/skill-anatomy.md`
3. **Background, already folded in:**
   - `design/planning-gap-review.md`: gaps against agent-skills' planning phase, now in this doc
   - `design/tooling-verification.md`: verified tool config; its fixed scripts in `evals/tooling-check/` are the `build-setup` templates

### Scope
**In scope:**
- the `dt` CLI and plugin hooks
- plugin packaging
- the `architecture-design` changes (§5.1)
- the `idea-refine` roadmap row
- the `pipeline-design`, `test-planning`, `build-planning` and `build-setup` skills
- README lifecycle and doc tables
- eval harness extension

**Out of scope:** how tasks get built.

### Build order
Each step ends green on its own tests, or on an eval run.

1. **Plugin skeleton and parser:**
   - `.claude-plugin/plugin.json`
   - `scripts/dt.py`
   - `scripts/devteam/`: stdlib-only parser for the doc format below, with unit tests on sample docs
2. **First commands:** `dt status`, `next-id`, `section` and `lint` on today's docs (brief, ideas, spec, architecture). Point the existing skills at `../../scripts/dt.py`. Keep the old scripts until `dt` matches their output. (Done: matched and removed 2026-10-16.)
3. **Existing skills:** the `architecture-design` changes (contract.md, `docs/packages/`, system pipelines, Grow triggers, stop after approval) and the `idea-refine` roadmap row.
4. **`pipeline-design`**, plus `dt layout`.
5. **`test-planning`.**
6. **`build-planning`**, plus `dt context` and `dt roadmap`.
7. **`build-setup`**, after the tooling verification.
8. **Hooks:** `hooks/hooks.json` with SessionStart, guard and lint.
9. **README:** lifecycle diagrams, document table, statuses.
10. **Evals:** below.

### Doc format contract (what `dt` parses)
- **Header:** the first non-blank line after the H1 holds `**Key:** value` pairs joined by ` · `. Existing docs put it on line 3, new templates on line 2; both parse.
  - Known keys: Status, Last updated, Last reviewed, Shape, Package, Spec, Contract, Architecture, Pipelines, Milestone, Base, Roadmap. Unknown keys are kept, not rejected.
  - Status values per doc are as in §3.
- **ID sections:** a heading `## <ID>: <Title>` or `### <ID>: <Title>`. A section runs to the next heading of the same or higher level.
  - ID forms: `PL-\d{2,}`, `TC-\d{2,}`, `AD-\d{2,}`, `CR-\d{2,}`, `M\d+`, `M\d+-T\d{2,}`, `M\d+-R\d{2,}`, `<pkg>.<symbol>`.
- **Spec requirements:** bold-led lines, `**CODE-NN**` (existing convention). Ranges in Covers fields use an en dash (`STAT-01–STAT-04`) and expand to every ID in between.
- **Retired:** `- ~~<ID>: <title>~~ Retired YYYY-MM-DD: <reason>`. Retired IDs count for `next-id` and fail on reference.
- **Task fields:** bold-key lines (`**Package:** … · **Mode:** split`).
  - `**Read:**` is a comma-separated list of IDs or repo paths.
  - `Mode` is `split` or `solo`.
  - `Size` is XS–M, matched against the `Files likely` count (§5.4 sizing). L or larger fails lint.
  - Optional fields: `Parallel` (`G<n>`), `Blocked` (reason).
- **Pre-build sections:** a heading containing `(pre-build`. `dt lint` flags one that's still present after that pipeline's spine task is checked.

### Skill format
Match the existing dev-team2 skills and agent-skills' anatomy:
- frontmatter `name` and `description` ("Use when…")
- Overview, When to Use, Modes table, Process, Review Gate, Common Rationalizations, Red Flags, Verification checklist
- SKILL.md at about 250 lines or fewer; templates and long examples in `examples.md`
- every skill starts by running `dt status --skill <name>` and stops its turn at the review gate

### Validation
- **Scenarios:**
  - the existing `rl` and `quant` scenarios
  - the user's upcoming test projects
  - all of them extended past architecture through pipeline-design, test-planning, build-planning and build-setup, in both all-at-once and incremental modes
- **Programmatic assertions** (mostly via `dt`):
  - `dt lint` is clean
  - every live spec ID sits on a pipeline step, or is Deferred
  - every new pipeline has a Phase 0 spine task
  - every task has resolvable `Read:` IDs, size M or smaller, and a `Mode` that follows the rule
  - `dt context` packets are under 2,000 lines
  - doc size budgets hold
  - there's one roadmap row per stage, with derived status
  - brief goals stay at 5 or fewer and stage-neutral
  - quant triggers Grow at the features milestone
  - no source code is written during planning
  - every skill stops at its gate
- **Replan and Advance:** simulate with a scripted state change (edit a step, tick all tasks) and assert the right modes run.
- **Blind judge:** pipelines read as clear call paths; layouts are sensible; each task could be built from its `dt context` packet alone.

### Done means
- All planning skills and `dt` commands exist, with passing tests.
- The eval assertions pass on rl, quant and at least one user project, in both modes.
- The README describes the full Define → Design → Plan → Build-setup flow.

