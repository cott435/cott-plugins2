# Planning Stage — Design

**Status:** Ready to build · **Last updated:** 2026-10-15

Covers what happens after `architecture-design` is approved and before any code: pipelines, file layout, test plans, build plans, skill routing, and how all of it evolves across new, extend, grow, replan, rebuild and debug. Building itself is agent-skills' `/build`; this design only makes sure builders get small, correct inputs.

Inputs to this design: agent-skills `planning-and-task-breakdown`, `incremental-implementation`, `test-driven-development`, `context-engineering`, `constraint-driven-development`, `definition-of-done`; dev-team2's three skills; eval iteration 1.

---

## 1. Decisions at a glance

1. **Three new skills after architecture:** `pipeline-design` → `test-planning` (optional) → `build-planning`. Each stops at a review gate.
2. **One folder per package:** `docs/packages/<pkg>/` holds everything about a package, in single *and* multi-package repos. Grow then moves sections between folders; it never rewrites paths.
3. **Intent until code exists, then code is truth.** Planned layout and entry-function sketches are *pre-build sections*: the spine task replaces them with a pointer to `dt layout`. Contracts stay as docs but are checked against code.
4. **Build plans are per milestone, not per package.** `tasks/plan.md` is always the active milestone, so `/build` and `/build auto` work unchanged. Every task names its package.
5. **Repo-unique ID on every addressable unit.** Agents read by ID (`dt section PL-02 TC-06`), not by file. Each task lists the IDs it needs, and `dt context <task>` assembles them.
6. **New repo doc `docs/roadmap.md`** holds milestone order. Stages live there, not in brief goals. That fixes eval root cause #1, "the brief never re-aims".
7. **No review-plan file.** The standing bar is agent-skills' `CONSTRAINTS.md` plus a Definition of Done, written once. Checkpoints live in the plan.
8. **Depth:** design everything known, but write task-level plans only for the next milestone. Later milestones go into `tasks/queued/` only when the user asks. Either way, every milestone starts with a **kickoff check** that revalidates the docs against the code.
9. **Deterministic by default.** One shared CLI (`dt`) in the plugin's `scripts/` parses every doc. Status, IDs, coverage, context packets and lint come from it, not from an agent reading and counting. Plugin hooks run it at session start, guard oracle files, and lint doc edits (§10).
10. **Milestones are capabilities, not packages.** A package can span several milestones, and a milestone can touch several packages (§6).

---

## 2. Your proposed docs: verdicts

| Proposed | Verdict | Why |
|---|---|---|
| Contract | **Keep**, per package, written by `architecture-design` | Consumers of a package read only this, not its whole architecture. Moved out of the architecture doc's Interfaces section. |
| Planned file structure | **Keep, as a section of `pipelines.md`** | The layout follows from the pipelines (entry module plus step owners), so it's approved alongside them. It's a pre-build section: the spine task swaps it for `dt layout`. |
| Spine plan | **Drop as a file** | The spine is a *Spine version* column in the pipeline step table plus Phase 0 of the milestone plan. A separate file would restate both. |
| Review plan | **Drop as a file** | Review criteria are repo-wide and stable, so they go in `CONSTRAINTS.md` + DoD. Checkpoint blocks sit in the plan where builders hit them. |
| Test plan | **Keep**, optional, per package | `tests.md` is the index and strategy; fixtures live in `tests/fixtures/`. |
| Build plan | **Keep, per milestone** in `tasks/` | Milestones cross packages (the system spine always does). Per-package plans would split one milestone's ordering across files. A package-scoped agent filters tasks by `Package:`. |
| Pipeline plan | **Keep**, `pipelines.md` per package | System pipelines that cross packages stay general and live in the root architecture. |

---

## 3. Document map

```
AGENTS.md / CLAUDE.md          doc map + how to read sections + project skills (≤ 25 lines)
CONSTRAINTS.md                 standing quality bar, incl. pipeline readability rules (agent-skills /constraints)
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
tasks/
  plan.md                      active milestone (agent-skills /build format, extended)   build-planning
  todo.md                      active milestone checklist
  queued/M<n>-<slug>.md        later milestones planned in detail (optional)
  archive/M<n>-<slug>.md       finished milestones; not in the doc map
```

| Doc | Size budget | Lifecycle |
|---|---|---|
| `roadmap.md` | 1 table + 3-6 lines per milestone | Rows only; status is derived by script |
| `contract.md` | ≤ 1 page | Draft → Approved; Revise reopens it |
| `pipelines.md` | ≤ 2 pages (pre-build sections included) | Draft → Approved |
| `tests.md` | ≤ 2 pages; fixtures stay outside | Draft → Approved; expected outputs change only with approval |
| `tasks/plan.md` | ≤ ~400 lines | Draft → Approved → In progress → Done → archived |

**Single package** uses the same tree: root `architecture.md` is the full doc, and there's one `docs/packages/<pkg>/` without an `architecture.md`. Its `contract.md` has one section per component. When a component later becomes a package, its section moves with it.

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

**Rules**
- Every ID is a heading (`## PL-02: Covariance report`), or a bold line in the spec. `dt section <ID>…` prints only those sections, searching all docs. Because IDs are repo-unique, no path is needed.
- Each task's `Read:` field lists the IDs (and files) a builder needs. `dt context M2-T03` prints the task plus every section it lists. That output is the builder's whole context packet.
- New IDs come from `dt next-id <prefix>`, never from counting by hand.
- **Retire, don't keep in full.** A retired pipeline, case or decision collapses to one struck line with date and reason. Eval iteration 1 found superseded decisions kept in full drove 2-3× doc growth.
- **Docs carry no history.** Git is the history. Changelog rows are one line. Finished milestones move to `tasks/archive/`, which is outside the doc map.

---

## 5. Skills

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
tests/stats/
```

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
   - The raw example goes in `source/`, then is parsed to `input.json`, validated against the contract types.
   - The expected result is recorded as `expected.json` with tolerances.
   - A *parse test* checks raw → `input.json`; a *pipeline test* checks `input.json` → expected output. A parsing bug never looks like a logic bug, and the parse step proves the contract types before any pipeline code exists.
3. **No real pairs? Use synthetic known-answer cases.** Plant a signal and require it found; use pure noise and require nothing found; check a random matrix's eigenvalue edge against Marchenko–Pastur. This is where domain skills get routed (e.g. `null-hypothesis-testing` for any "feature X carries information" claim).
4. **Strategy per pipeline:**
   - A smoke test (the spine's done-check).
   - Step unit tests.
   - Golden cases.
   - For models: the evaluation protocol (metric, held-out split, baseline, seeds), citing the spec's model criteria by ID.
5. Review gate: the user approves the expected outputs, because they are the oracle.

**Rules**
- Fixtures are kilobytes. Large data is referenced by path plus hash, never committed.
- Tables go in CSV referenced from `input.json`. JSON holds structure and parameters.
- `expected.json` changes only through Revise mode with user approval, never by a builder to make a test pass. This goes in the `CONSTRAINTS.md` floor.

```
tests/fixtures/stats/TC-06/
  source/returns_5x250.csv      raw example as given
  input.json                    {"universe": [...], "returns": "source/returns_5x250.csv", "n_obs": 250}
  expected.json                 {"top_eigval": 2.31, "mp_edge": 1.62, "tol": 1e-6}
```

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
5. **Thicken:** one task per step upgrade, riskiest first. In ML that means data loading, leak checks and evaluation before any model.
6. **Route skills.** Read the descriptions of project skills (`.claude/skills/*/SKILL.md`) and installed plugin skills, then assign them per task. The plan header lists skills in use. A task needing a skill that doesn't exist is flagged, not silently built without it. Eval: the `null-hypothesis-testing` hand-off happened only by chance.
7. **Checkpoints** every 2-3 tasks, plus a milestone exit checkpoint.
8. **Parallel groups:** after the spine, tasks in different packages or steps with no dependency between them are marked as able to run in parallel.
9. Review gate. Stop.

**Task template** (extends agent-skills' template)

```markdown
### M2-T03: Ledoit-Wolf shrinkage behind `estimate_cov`
**Package:** stats · **Step:** PL-02.estimate_cov · **Covers:** STAT-02, QR-02 · **Size:** S
**Skills:** data-science
**Read:** PL-02, TC-06, STAT-02, contract.md#estimate_cov
**Acceptance:**
- [ ] TC-06 passes within tolerance; sample-cov baseline remains selectable for comparison
- [ ] PL-02 smoke test still passes
**Verify:** `pytest tests/stats -k cov` · `python -m quant.stats cov-report --smoke`
**Depends on:** M2-T01 · **Files likely:** src/quant/stats/cov.py, tests/stats/test_cov.py
```

**Checkpoint block**

```markdown
### Checkpoint after M2-T04
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] No new abstraction without a second implementation or an AD
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `dt layout` output reviewed; Definition of Done holds
```

**Modes**
| Mode | When | Does |
|---|---|---|
| New | No roadmap/plan | Roadmap, plus the M1 plan |
| Extend | A new idea is specced and designed | Adds the milestone. If a milestone is active, the new one is queued, never merged into the active plan unless the user asks |
| Replan | Something learned during the build, or a major bug | Reorders, splits or adds tasks. Never drops an unchecked task silently: drops are listed for approval. One-line replan note in the plan |
| Advance | All tasks and the exit checkpoint done | Archives the plan, writes a 1-2 line outcome on the roadmap, runs the **kickoff check**, and promotes or writes the next milestone's plan |

**Kickoff check** (part of Advance, and on every first entry into a milestone):
1. Re-run every status script.
2. Sync `pipelines.md` and `contract.md` against the code.
3. Review the queued plan (if any) against what the last milestone changed.
4. Confirm the plan with the user.

This is what makes up-front and sequential planning land in the same place.

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
- **Size:** about 5–15 tasks. Bigger means two milestones. A single task isn't a milestone; it belongs in an existing one.

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

**H. Advance:** milestone exit checkpoint → archive the plan → roadmap outcome line → kickoff check → next plan.

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

dev-team2 ships as a plugin with a root `scripts/` folder, the same way agent-skills ships `references/`. Nothing is copied into the project repo.

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
- **Existing bug:** today's skills call `skills/<name>/scripts/...` relative to the current folder. That only works when run from inside dev-team2, so these calls move to the plugin-relative form.

### `dt` commands

One parser means every skill, hook and agent sees the same IDs, statuses and sections.

| Command | Used by | Does |
|---|---|---|
| `dt status [--skill X] [--summary]` | every skill, SessionStart hook | Mode; upstream gates; coverage gaps (spec IDs on no component, pipeline or task, unless Deferred); pipelines with no spine task; stale or retired references; skills referenced but not installed; contract freshness (`contract.md` vs the git date of the contract module); Grow triggers. Replaces `idea-refine.sh`, `spec-status.sh` and `arch-status.py` over time |
| `dt next-id <prefix>` | every writing skill | Next free `AD`, `PL`, `TC`, `CODE` etc., counting retired IDs |
| `dt section <ID>…` | everyone | Prints those sections from any doc |
| `dt context <task>` | orchestrator → builder | Task section + every `Read:` section + file list; warns over 2,000 lines |
| `dt layout <pkg>` | spine task, reviewers, pipeline-design Sync | Real tree, each module annotated with its docstring's first line; flags entry functions whose calls don't match the step table |
| `dt lint [paths]` | PostToolUse hook, checkpoints | Duplicate IDs, references to missing or retired IDs, size budgets, an Approved doc edited without going back to Draft, a pre-build section still present after the spine is done |
| `dt roadmap` | build-planning, Advance | Rewrites the derived Status column |
| `dt guard <path>` | PreToolUse hook | Decides whether a write needs a human (below) |

### Hooks

| Event | Runs | Effect |
|---|---|---|
| SessionStart | `dt status --summary` | Injects active milestone, next task, blocked gates, resolved `dt` path |
| PreToolUse (Edit, Write) | `dt guard <path>` | `tests/fixtures/**/expected.json` → **ask**: the user must approve every oracle change. `tasks/archive/**` → **deny** |
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

**Open:** none.

## 12. Fixes to existing skills found in the eval

Iterations 2–3 (branch `claude/iter2-residual-fixes`, not merged) fixed the change markers, out-of-scope contradictions, vendor leakage, the `arch-status` name and the review-gate stops. Still open:
- Brief goals grow with each stage (7 goals RL, 6 quant). The roadmap is meant to fix this.
- Script paths are relative to the current folder, not the plugin (§10).
