# Interface-First Design — Parallel Builds

**Status:** Draft · **Last updated:** 2026-10-17 · **Branch:** `interface-first-design` · **Changes:** [planning-stage.md](planning-stage.md) §5.4 (Phase 0, task fields), [build-phase-notes.md](build-phase-notes.md) §5 Q4–Q5, workflow-analyzer (new plan map), [evals/](../evals/README.md)

The goal: many agents build one milestone at the same time without waiting on each other or colliding. Planning does the work that makes this possible: it cuts a milestone vertically, draws the dependency graph between the units of work, and freezes an interface for every edge it can, so the work on both sides of that edge starts at once. Building stays `/build`'s job (or the build-phase orchestrator's); this design changes what planning hands it, the view that shows the plan growing, and the evals that prove it works.

Inputs: research on dev-team as it stands (skills, `dt`, iteration-6 findings), agent-skills (`/Users/connorott/dev/agent-skills`), workflow-analyzer's run-flow, and the quant fixture plan (`scripts/tests/fixtures/quant/tasks/plan.md`).

---

## 1. Decisions at a glance

1. **Three levels, three jobs.** *Plan* at the pipeline step (`PL-NN.<function>`): it is the unit that has one owner, one module and typed `In → Out`. *Schedule* at the task (`M<n>-T<nn>`): one agent, one commit. *Check* at the file: every task declares the files it writes, exclusively.
2. **Interfaces before code, per milestone.** The milestone starts with an interface task that freezes every step boundary that crosses owners within the milestone (not only package boundaries): the boundary types as real code, the step signatures, and one sample payload per boundary. Cross-pipeline and cross-package calls also get a fixture-backed fake.
3. **The per-pipeline spine is split.** One XS/S spine task per step, in parallel, each writing only its owner module; one wiring task per pipeline writing only its entry and smoke test; the system wiring last.
4. **Every dependency is an edge with a kind and a mitigation.** `plan.md` gets a `## Dependency graph` table. An edge is either mitigated by a named interface (and so does not order the tasks) or it states why it can't be (`none: <reason>`) and orders them.
5. **`Writes:` replaces `Files likely`** as an exclusive claim. Two tasks with no `Depends on` path between them never write the same file. Shared files (`__init__.py`, `types.py`, `pipeline.py`) are owned by the interface or wiring task.
6. **Parallel groups are derived, not typed.** `dt` computes waves, width and the critical path from `Depends on` + `Writes:`; `dt ready` lists every task that can start now. The size cap stays on the critical path (≤ ~15).
7. **Testers start at the interface, not at the code.** A split task's tester writes against the frozen signatures and golden fixtures, so every tester in the milestone can run right after the interface task, beside the implementers. Golden cases (`TC-NN`) stay the oracle.
8. **Only the orchestrator writes `tasks/`.** Builders in worktrees never tick `todo.md` or write findings; the merge step does.
9. **workflow-analyzer gets a plan map.** dev-team exports a generic `plan.json` per run (one snapshot per turn that changed the plan); workflow-analyzer renders it without knowing dev-team: the plan expanding turn by turn, and per milestone a build view of what runs in parallel and what in series.
10. **Evals measure parallelism and correctness, not just plan shape.** Planning evals gain graph metrics and compare incremental vs all-at-once on them; a new build eval runs the same plan serially, in parallel without interfaces, and interface-first, with ablations for TDD (§9).

---

## 2. Where dev-team serializes today

What the research found (file references are under `dev-team/`):

| Cause | Where | Effect |
|---|---|---|
| One M-sized spine task per pipeline, touching every step module | `build-planning/references/phase0.md:14` | Every thicken task of that pipeline waits on it |
| Same-package spines serialize when one calls the other | `phase0.md:14`; `pipeline-design/references/steps.md:27` (no in-package fakes) | PL-02 waits on PL-01 even though `data.load_prices` is already in the contract |
| Only cross-package boundaries are frozen | `architecture-design/references/contracts.md:11` | A single-package milestone has no executable interface at all; two tasks reading one contract symbol can't share a group (`build-planning/references/tasks.md:33`) |
| Types aren't contract symbols | `contract.md` sections are functions only | Builders' packets miss `EvalResult`, `DQNConfig`, `TestResult` (iteration-6 judge, `evals/results-iteration-6/findings.md:143`) |
| Testers test only symbols that exist | `tasks.md:24`; tester role `tester.md:32-33` | No tester starts before the spine lands; spines are never independently tested |
| Order rules with no file reason | "contract changes first", "riskiest first" (`tasks.md:7`) | Fixture M1-T05 waits on M1-T04 though they write `cov.py` and `rmt.py` |
| `Files likely` is advisory; the `parallel` lint checks only pairs inside one `G` group | `scripts/devteam/commands/lint.py:678-698` | Ungrouped or cross-group tasks can write the same file unnoticed; `G` labels can contradict `Depends on` |
| No width, waves or ready set | `status/common.py:178-188` returns one next task | The orchestrator can't fan out from `dt` |
| Milestone `Depends` almost linear | iteration-6 S8: quant incremental M3→M5→…→M10 | With one active milestone, fully serial |

agent-skills doesn't solve this either. Its `/build` and `/build auto` are a serial single-agent loop (`.claude/commands/build.md:12,35`); contract-first slicing stops at "frontend against mock data matching the contract" (`skills/incremental-implementation/SKILL.md:66-75`); its dependency graph is a prose ASCII tree with no critical path, waves or parallel-safe marker (`skills/planning-and-task-breakdown/SKILL.md:35-55`); worktrees are advice (`skills/git-workflow-and-versioning/SKILL.md:147-170`); nothing checks file ownership. What it gives that we borrow:
- The capability-map rules (`skills/spec-driven-development/SKILL.md:59-61`): one-way edges, "if two modules each need the other, they are one module", the contract belongs to the provider.
- Split heuristics already in our lint (> 3 acceptance bullets, "and" in the title, two subsystems).
- The fan-out checklist (`references/orchestration-patterns.md:68-74`) as the definition of "independent".
- Real > Fake > Stub > Mock (`skills/test-driven-development/SKILL.md:234-246`), and its with/without-plugin Δ eval shape.

---

## 3. The unit of work

Files, pipelines, steps or tasks? Each has a job, and only one is the split unit:

| Unit | Why not the split unit | Its job |
|---|---|---|
| File | Unknown before the build ("likely"); the planned layout is deleted by the spine | The **check**: `Writes:` ownership, conflict lint, merge order |
| Pipeline | Too coarse: one pipeline is today's serial spine | The **wiring** unit: one entry, one smoke test |
| **Step** | — | The **plan** unit: one owner (`steps.md:9`: "a step with two owners is two steps"), one module (`steps.md:19`), typed `In → Out`, a real spine version |
| Task | Scheduling only: a task may cover one step's spine, one step's thicken, an interface or wiring | The **agent** unit: one packet, one commit, one gate |

So a milestone's graph is built from steps, and each task names the step(s) it touches (`**Step:**` already exists). A task touching two steps is two tasks (`tasks.md:9`), except wiring.

---

## 4. Interfaces: what is frozen, in what form, and when

### 4.1 What

Every boundary the milestone builds across, where the two sides belong to different tasks:

| Boundary | Frozen as | Unblocks |
|---|---|---|
| Step → next step in a pipeline (data) | The `Out` type as code + one sample payload | The downstream step's spine and tests run on the sample, not on the upstream code |
| Step → step passing an object with behavior (a `typing.Protocol` or class, such as `core.Env` or `runstore.RunWriter`), or a call into another component's function (`load_agent` calling `make_env`) | The Protocol or signature as code + a fixture-backed replay double in `tests/contracts/<id>.<Type>/`, replaying a recorded interaction. The double is the type's sample, not a mock of a step | The consuming step's spine and tests run on the double, not on the provider's code |
| Step signature | The function signature in its owner module (body: see 4.3) | Wiring and testers import it |
| Pipeline → another pipeline or package (call) | Schema + fixtures + a fixture-backed fake (today's contract folder) | The calling pipeline's wiring and smoke test |
| Shared modules (`types.py`, `__init__.py` exports) | Written whole by the interface task | No builder touches them |

Not frozen: helpers inside a step, private functions, anything one task owns end to end.

### 4.2 Form

- **Types become contract sections.** `### stats.Cov: type` sits beside function sections in `contract.md`, with fields, invariants and its cases. architecture-design writes them; pipeline-design checks every `In → Out` cell names one (a new `dt lint` rule: `step-io-types`).
- **Planning names the cases; the interface task writes the samples.** A type's section names each case it needs (a Protocol or class type's case is its replay double) and the folder it lands in. The sample files, like the types themselves, are build output: the milestone's interface task writes them.
- **Code, not prose.** Dataclasses, `typing.Protocol`, or a pandera schema for a dataframe, in the owner's `types.py`.
- **Folders:** `tests/contracts/<component>.<Type>/` holds the schema and samples, or the replay double for a Protocol or class; `tests/contracts/<pkg>.<symbol>/` keeps the fake for calls. CR-09 freezes both once the interface task lands, like every contract folder.
- **Generated cross-runtime types.** When one runtime's types are generated from another's schema (TypeScript from the server's JSON Schema), the providing interface task runs the generator and writes the generated file, which its `Writes:` claims. Interface tasks never depend on each other: each is solo and first.
- **`**Boundary:**` lines extend to component boundaries** in single-package repos, and `boundaries_unfrozen` (`status/build_planning.py:135-148`) reports any cross-owner boundary in the milestone with no interface task.

### 4.3 Signatures and the no-stub floor

Testers need importable names so RED fails for the right reason (build-phase-notes Q4), but CR-02 and agent-skills' floor forbid `NotImplementedError` stubs (`constraint-driven-development/SKILL.md:105`).

**Decision:** the interface task writes each step's signature with the body `raise NotImplementedError("<task id>")`, naming the spine task that replaces it. CR-02 gains one carve-out: such a stub is allowed while the task it names is open; `check.sh gate` fails on any stub naming a done task, and the milestone exit fails on any stub at all. RED in a spine test fails on `NotImplementedError`; RED in a thicken test fails on the baseline's wrong answer.

Alternative kept open (§11): the interface task writes the spine version itself for trivial steps (identity, print), skipping the stub.

### 4.4 Who and when

architecture-design names types and boundaries (Draft → Approved as now). pipeline-design checks every step's `In → Out` against them. build-planning writes the interface task as the milestone's first task. A frozen interface changes only through architecture-design Revise and a new interface task (`phase0.md:24`, unchanged); an interface change mid-milestone is recorded as such, because it is the measure of interface-first failing (§9).

---

## 5. Milestone shape

### 5.1 Phases

```
Phase 0  interface (solo)               types, signatures, samples, fakes, exports
Phase 1  spine ∥  one per step           each writes its owner module only
         tester ∥ every split task's     tests against signatures + golden fixtures
                  tester half
Phase 2  wiring ∥ one per pipeline       entry + smoke; cross-pipeline calls use the fake
         thicken ∥ implementer halves    each after its step's spine
Phase 3  system (solo)                   fakes swapped for real providers; full smoke
```

A task's kind is a field (`**Kind:** interface | spine | wiring | thicken | system`). A split task keeps its two halves in one task, but they start at different times: **the tester half depends only on the interface task**, and the implementer half on the task's `Depends on`. Phase labels describe the usual waves; the graph decides what may start.

### 5.2 Worked example: quant M1 today

From `scripts/tests/fixtures/quant/tasks/plan.md`:

```
T01 PL-01 spine (S) ─► T02 PL-02 spine (M) ─┬─► T04 MP cleaning ─► T05 shrinkage
          └──────────► T03 universe          └─► T06 PCA
```

6 tasks, critical path 4 (T01→T02→T04→T05), widest wave 3. T02 waits on T01 because PL-02 calls `load_prices`; T05 waits on T04 for no file reason; no tester starts before T02.

### 5.3 The same milestone, interface-first

```
wave 0  T01  interface: data/types.py (Prices), stats/types.py (Returns, Cov, Factors, CovReport),
             step signatures, a sample per boundary, quant.load_prices fake, __init__ exports
wave 1  spines   T02 read_raw · T03 apply_universe · T04 estimate_cov · T05 clean_eigen · T06 pca · T07 write_report
        testers  T10 universe (TC-01) · T11 MP (TC-02) · T12 shrinkage · T13 PCA (TC-03)
wave 2  wiring   T08 PL-01 · T09 PL-02 (on the load_prices fake)
        thicken  T10 ← T03 · T11 ← T05 · T12 ← T04 · T13 ← T06   (implementer halves)
wave 3  T14  system: PL-02 on real PL-01; both smokes; TC-01–TC-03
```

14 tasks, critical path 4 (T01 → T05 → T11 → T14), 10 agents in wave 1, every task XS/S. The critical path is no shorter in tasks, but each task on it is smaller and each wave is wide. Whether that wins wall-clock time after merge cost is exactly what the build eval measures (§9.2); planning alone can't prove it.

Two folds keep the task count down, both build-planning rules. A fold is allowed only where it doesn't lengthen the critical path, and it is recorded on the task it produces as `**Reason:** fold: <rule>`, so reviewers and the grader see it in the plan:
- **`spine into thicken`:** when a step's spine and thicken are both in the milestone and the step has a golden case, one split task replaces the stub itself; its acceptance keeps the baseline selectable. (Example: `clean_eigen` spine + MP cleaning → one task, `**Reason:** fold: spine into thicken`.) The pipeline's wiring then waits on that task instead of a spine, which is how a fold lengthens the path. Open question §11.1.
- **`trivial into wiring`:** a step whose spine is a pass-through or a print is built by its pipeline's wiring task; its stub names the wiring task.

### 5.4 Milestone level

The same rules apply one level up. A milestone row's `Depends` names what it needs from the earlier one (an interface ID or a pipeline output), so build-planning cuts only where a later slice needs an earlier one's outputs (iteration-6 S8). With interfaces frozen, two milestones could be active at once; that stays out of scope (§11.4).

---

## 6. The dependency graph

### 6.1 In `plan.md`

```markdown
## Dependency graph
| From | To | Kind | Mitigated by |
|---|---|---|---|
| M1-T09 wire PL-02 | M1-T08 wire PL-01 | call | quant.load_prices fake (M1-T01) |
| M1-T05 clean_eigen spine | M1-T04 estimate_cov spine | data | stats.Cov sample (M1-T01) |
| M1-T09 wire PL-02 | M1-T05 clean_eigen spine | order | none: integration: the smoke runs it |
| M1-T11 MP cleaning | M1-T05 clean_eigen spine | code | none: thickens the same module |
| M1-T11 MP cleaning | M1-T12 shrinkage | data | stats.Cov sample (M1-T01): cleaning takes any Cov; today's T04 → T05 order disappears |
```

Edge kinds:

| Kind | Meaning | Mitigation |
|---|---|---|
| `data` | One step's output feeds another's input | Type + sample payload |
| `call` | A pipeline calls another pipeline or package | Fake backed by fixtures |
| `file` | Two tasks must write one file | Move the shared part to the interface or wiring task; else serial |
| `code` | A task *changes* code another task wrote: a thicken after its step's spine, two thickens of one module. Running or calling that code is not a `code` edge | None: serial. A spine never has a `code` edge to another step's task; it runs on that boundary's sample or replay double |
| `contract-change` | A task changes a frozen interface | None: serial, plus a new interface task |
| `order` | Risk or learning ("do X first to learn Y"), or integration: a wiring or system task runs the steps it wires | None: reason required. A wiring or system task's edge to a step of a pipeline it wires or swaps in gives the reason `integration: <what runs it>` |

A mitigated edge is documentation: it doesn't order the tasks and doesn't appear in `Depends on`. An unmitigated edge must appear in `Depends on`. The table is the reviewable argument for every serial step in the milestone.

### 6.2 Task fields

```markdown
### M1-T05: clean_eigen spine (no cleaning)
**Package:** quant · **Step:** PL-02.clean_eigen · **Kind:** spine · **Size:** XS · **Mode:** solo
**Read:** PL-02, stats.Cov, stats.clean_eigen
**Acceptance:**
- [ ] `clean_eigen` returns its input on the stats.Cov sample; signature unchanged
**Verify:** `pytest tests/unit/quant -k clean_eigen` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/stats/rmt.py, tests/unit/quant/test_rmt.py
```

`**Parallel:** G<n>` goes away (derived). Within a split task the implementer always follows its tester; that order is implied, not an edge. `**Writes:**` is exact paths or one directory glob owned by the task. A step's owner may be a folder that holds its private helpers (`train/loop/**`): the step's spine and thicken tasks write that glob, and no other task writes inside it.

### 6.3 `dt` changes

| Command | Change |
|---|---|
| `dt lint` `writes` (new) | Error: two tasks with no `Depends on` path write the same path, across the whole plan. Error: a shared file (`__init__.py`, `types.py`, an entry module) written by a task that isn't interface or wiring |
| `dt lint` `edges` (new) | Error: a `Depends on` whose graph row says it is mitigated (mitigated edges don't order); a `Depends on` with no graph row; a row with `none` and no reason; a mitigation naming an interface the interface task doesn't produce |
| `dt lint` `milestone-size` | Unchanged rule (critical path ≤ ~15), now reading the derived graph |
| `dt lint` `parallel` | Replaced by `writes` and `edges` |
| `dt status` | Adds `critical_path`, `waves`, `width`, `parallelism` (tasks ÷ critical path). Warns when most waves have width 1 |
| `dt ready` (new) | Every task whose `Depends on` are done, with its `Writes:`, so an orchestrator can fan out in one turn |
| `dt context` | Adds the task's interfaces (types, signatures, sample paths) and its `Writes:` as the edit boundary |
| `dt plan --json` (new) | The plan snapshot used by the plan map (§8) |

### 6.4 Build dispatch (for the build design)

This design doesn't settle the build orchestrator ([build-phase-notes.md](build-phase-notes.md) §5), but it fixes the inputs:
- Each wave from `dt ready` dispatches one worktree agent per task (`isolation: 'worktree'`, build-phase-notes §4 rec. 5); `Writes:` is passed as the agent's allowed paths, so the role guard can enforce it.
- A merge step merges the branches in plan order; since `Writes:` are disjoint, a conflict means a lint gap and is logged.
- The check agent runs the gate after each merge (rec. 2). Only the orchestrator or merge step runs `dt tick` and `dt finding`.
- Checkpoints come after waves, not every 2–3 tasks.

---

## 7. Test-driven design in the parallel plan

- **What the tester reads:** the `dt context` packet, which now carries the frozen signatures, types and sample payloads, plus golden fixtures. It never reads `src/`.
- **Rule change** (`tasks.md:24`, `tester.md:32-33`): a split task tests symbols *declared by a frozen interface*, not only symbols that exist.
- **RED for the right reason:** a spine test fails with `NotImplementedError("<task>")`; a thicken test fails on the baseline's wrong answer. The tester's Stop gate (`check.sh collect`) checks the failure reason, not only that tests collect.
- **Testers move to wave 1.** The tester half of every split task depends only on the interface task; the implementer half follows its own tester and its step's spine (`code` edge), nothing else.
- **Spines get tested.** A step spine's acceptance is the sample payload going in and a schema-valid output coming out, so every boundary is exercised before wiring.
- **The oracle stays outside the agent.** TC cases still come from test-planning with `expected.json` behind `dt guard`; contract samples are shapes, not answers, so a wrong belief can't hide in them.
- **What escalates:** a tester who finds the interface can't express a case files it as a `contract-change` instead of writing around it.

---

## 8. workflow-analyzer: the plan map

run-flow shows what a run *did*. The plan map shows what the run *planned*: in series, turn by turn with the skill that ran, how the plan grows from goals and stages to features and requirements, milestones, tasks and pipeline steps and what each is expected to do; how each goal reaches the pipelines and milestones that build it; and per milestone what would be built in parallel and what in series.

### 8.1 Boundary

dev-team produces, workflow-analyzer renders. workflow-analyzer stays stdlib-only, dev-team-agnostic and writes only into the workspace it is given (its PURPOSE non-goals). The contract between them is a versioned `plan.json` schema, the same pattern as `eval.json` (`runviz.py:110`, `flow.load_eval`).

### 8.2 Producer (dev-team)

- **Eval runs:** `evals/harness/planexport.py` walks the run's `turn N` commits (`driver.py:263-293`), skips commits where `git diff --quiet sha^ sha -- docs tasks` holds, extracts each changed snapshot with `git archive` into a temp dir (never checking out `run/project`), runs the run's own dt snapshot on it (`dtrun.dt_path`, dtprobe-style fallbacks), and writes `run/flow/plan.json`. `runviz.build_run` calls it before `trace.build`.
- **Interactive sessions:** `dt plan --json` on each commit the session made (trace already records them, `trace.py:676,716`); a best-effort rebuild from Write/Edit contents is labelled as such.

### 8.3 `plan.json` (schema `plan-map/2`)

```json
{ "schema": "plan-map/2", "producer": "dev-team planexport (dt 0.x)",
  "levels": ["goal", "stage", "feature", "requirement", "milestone", "task", "pipeline", "step", "test", "type", "symbol"],
  "snapshots": [
    { "turn": 14, "commit": "ab12…", "skill": "build-planning",
      "nodes": [
        { "id": "M1-T05", "level": "task", "parent": "M1", "title": "clean_eigen spine",
          "hash": "…", "attrs": { "kind": "spine", "size": "XS", "mode": "solo", "package": "quant" },
          "expects": { "acceptance": ["…"], "verify": ["…"], "reads": ["stats.Cov"],
                       "writes": ["src/quant/stats/rmt.py"], "tests": [], "covers": ["STAT-03"] } } ],
      "edges": [
        { "from": "M1-T05", "to": "M1-T01", "kind": "depends" },
        { "from": "M1-T05", "to": "PL-02.clean_eigen", "kind": "implements" },
        { "from": "M1-T05", "to": "M1-T04", "kind": "data", "mitigated_by": "stats.Cov" } ],
      "builds": [ { "milestone": "M1", "state": "active", "critical_path": ["M1-T01", "M1-T05", "M1-T11", "M1-T14"],
                    "waves": [["M1-T01"], ["M1-T02", "…"], ["…"], ["M1-T14"]] } ] },
    { "turn": 15, "same_as": 14 } ] }
```

Goals (`G<n>`) come from the brief; a feature (its spec code) sits under its stage and has a `serves` edge to each goal; a requirement sits under its feature; pipelines, steps, test cases and tasks have a `covers` edge to each requirement they cover. `plan-map/1` is the same without those three levels and two edge kinds, and still draws.

The producer reports state; the renderer computes diffs (added, removed, changed by `hash`, classified as status / attrs / expects / text, status-only hidden by default).

### 8.4 Renderer (workflow-analyzer)

New `scripts/planmap.py` with `write(out) -> Path`, reusing `charts` and `flow` helpers and CSS. `flow.write_html` adds a Plan section when `plan.json` exists; turn pages link both ways.

| Page | Shows |
|---|---|
| `plan/index.html` | Tiles (final count per level, turns that changed the plan, replans, longest track). A growth strip on the run page's turn axis: the skill row, then one row per level with live nodes per turn, added above and removed below. A node × turn matrix like the files matrix: rows are the outline stage → milestone → task → step, cells A/C/R, tooltip citing the step that wrote the doc. A change ledger, one row per changed turn: `+M2 Portfolio`, `~M1-T11 depends`, `−M1-T05` |
| `plan/trace.html` | Goals to build, as of the final plan: four columns (goals; features in bands by stage; the pipelines covering their requirements, thicker for more; the milestones listing those pipelines); per milestone the build order (waves of tasks as columns, a row for the interfaces, each pipeline and the rest); per pipeline its code flow (steps in order, each type carried from the step that makes it to those that take it, marked when an interface freezes it, with the tasks that build and wire it) and a contract-types table; then per goal and per feature how many requirements a pipeline, a test and a task cover, and each requirement's coverage. A goal no feature serves and a feature no pipeline covers are marked |
| `plan/T<nn>.html` | The plan as of that turn as a collapsible tree: added green, changed amber with the field diff, removed struck; each task's expectations (acceptance, verify, reads, writes, tests) |
| `plan/M<n>.html` | The build view. Columns are waves; lanes are kinds (interface, spine, wiring, thicken, system). Interface nodes as diamonds with dashed "unblocks" edges; `Depends on` as arrows; the critical path in a thick stroke. A split task is drawn as two segments (tester → implementer), so series within a task shows too. Metrics: tasks, critical path vs cap, width per wave, parallelism, share of edges mitigated. A thumbnail row shows how this milestone's graph changed across turns |

Hierarchy is rows and time is columns, because dev-team creates levels out of hierarchy order (stages → spec → types and symbols → pipelines and steps → TCs → milestones → tasks). Layout is computed in Python (layering by longest path, a barycenter pass); no JavaScript, as `flow.py:4` promises. Large runs show only turns that changed the plan and keep spec IDs and acceptance off the matrix.

Once a build eval exists, its units (matched to task IDs) are drawn over `plan/M<n>.html` as planned vs actual.

### 8.5 workflow-analyzer docs

README (Skills table: run-flow gains the Plan section; Scripts: `planmap.py`), PURPOSE "What it does" gains one line, only once the user agrees the goal now covers the plans a run writes, CLAUDE.md's stable-API list gains `planmap.write` and the `plan-map/2` schema. No new skill until interactive sessions produce `plan.json`.

---

## 9. Evals

Two questions, two kinds of eval. **Planning evals** (no code, the harness that exists) ask whether the skills produce interface-first plans, equally in incremental and all-at-once mode. **Build evals** (new) ask whether those plans actually build faster and more correctly, and which part earns it: parallel dispatch, interface-first, or test-driven design. Every run in both ends with its flow and its plan map in `<run>/flow/`. Nothing below has been run: thresholds are proposals and costs are estimates.

### 9.1 Planning evals

**Same bar, two scopes.** Both modes already end with M1 planned and the rest Designed (`first_planned_rest_designed`, `evals/harness/grade.py:235-238`). Metrics run identically in both:
- *Planned scope (M1):* the task graph: tasks, `Depends on`, `Writes:`, the dependency-graph table, the interface task.
- *Designed scope (every milestone):* the step-boundary graph from `pipelines.md` (owner, In type, Out type) and the contract's type sections.

**The grader recomputes every graph fact itself** from parser facts and uses dt's numbers only as a cross-check, so a dt bug can't grade itself. `dtprobe.plan_facts` (`dtprobe.py:36-48`) gains per task `kind`, `writes`, `depends_on`, `reads`, `step`, and the graph-table rows; steps gain `in_type`, `out_type`.

New checks (planned scope):

| id | Check | Threshold |
|---|---|---|
| `graph_metrics` | N tasks, critical path (CP, unweighted and size-weighted XS=1 S=2 M=4), waves, width per wave, N/CP; grader vs dt | Agree exactly (informational) |
| `plan_parallelism` | N/CP for M1 | ≥ 2.5 when N ≥ 10 |
| `wave_width` | Ready set right after the interface task (spines + tester halves) | ≥ 0.8 × the milestone's step count |
| `writes_disjoint` | No two tasks without a `Depends on` path share a `Writes:` path; a spine writes only its owner module and its unit test | 0 conflicts |
| `edges_mitigated` | Cross-owner `data`/`call` edges whose mitigation names an interface the interface task produces | ≥ 0.9 |
| `unmitigated_reasoned` | Every `none:` row has a reason of an allowed kind (same module, unsplittable shared file, real side-effect order, integration: wiring and system tasks run the steps they wire) | 100% |
| `no_edge_to_code_when_interface` | No `Depends on` to a code task across a boundary an interface covers | 0 |
| `edge_table_consistent` | Every `Depends on` has a row; every row resolves | 100% |
| `phase0_split` (replaces `phase0_spine`, `grade.py:172-178`) | Per new pipeline: interface coverage, one spine per step (or a fold rule applied), one wiring task writing the entry and smoke test | 100% |
| `step_tasks_small` | Spine and thicken tasks are XS or S | 100% |
| `tester_starts_early` | Split tasks whose `Read:` symbols are all declared by the interface task | ≥ 0.8 |
| `fakes_only_cross_pipeline` | Fakes only where a pipeline calls another pipeline or package; a Protocol or class type's replay double is its sample, not a fake | 0 violations |
| `tasks_not_editing_plan` | No `Writes:` under `tasks/**` | 0 |

New checks (designed scope):

| id | Check | Threshold |
|---|---|---|
| `interface_coverage` | Every cross-owner step boundary has its type as a contract section that names its cases; in M1 also an interface task whose `Writes:` covers each type's sample path `tests/contracts/<id>.<Type>/`. Samples are build output, so the check never asks for the file on disk | 100% |
| `types_in_contract` | Every type named in a step table resolves to a contract section (iteration-6's top buildability defect, `findings.md:143`) | 100% |
| `frozen_interface_churn` | Times a type or contract folder M1 froze is revised by a later stage, walked over turn commits (`grade.py:127-129`) | Reported; expect all-at-once ≤ incremental |

`frozen_interface_churn` is the incremental mode's real risk: freezing types before later stages are known.

**Existing checks that change:**
- `tasks_well_formed` (`grade.py:188-193`) requires `Writes:` and `Kind:`; its Mode rule, and dtprobe's `expected_mode` (`dtprobe.py:16-25`), allow split for symbols an interface declares.
- `no_code_during_planning` (`grade.py:276-291`) adds `tests/contracts/` and `**/types.py`: types are written by the build's interface task, never by planning.
- `doc_budgets`: plans hold more, smaller tasks; plan.md and contract.md budgets become per task and per type (also fixes `docstats.py:54`, handoff S5).
- `milestone-size` reads the critical path from `graph_metrics`.
- `gate_discipline` (`grade.py:294-311`): watch for pipeline-design finding missing types and revising the architecture in the same turn (iteration-6 N2). A routed Revise round trip across two turns passes: one turn leaves the owner's doc Draft and asks for its Revise, the next runs the Revise and re-syncs the docs that use it. Both in one turn still fails.

**Free replay checks** in `simulate.py`: on a fresh plan `dt ready` returns only the interface task; after ticking it, every spine and every tester half; wiring isn't ready until its pipeline's spines are ticked; editing a frozen type yields a `contract-change` edge and lists the dependent tasks for Replan.

**Blind judge** (`judge_prompt.py`, `blind_judge_prompt.md`) gains:
- `interface_quality`: types are code shapes, minimal and complete for their boundary; helpers aren't frozen; one sample per boundary.
- `dependency_graph_soundness`: edges are real, no false serialization (iteration-6 S8), `none:` reasons valid, every spine could start the moment the interface lands.
- `task_buildability` extended: a spine's packet suffices without its sibling steps' code.

`package.py` adds the final `dt plan --json` to the judge's inputs (no hint of the mode). Each A/B pair is judged in both orders and averaged.

**Mode comparison.** New `modecmp.py <iteration> <project>` writes `mode_delta.json` with every metric above for both modes. Band: |Δ N/CP| ≤ 20%, |Δ max width| ≤ 1, both modes at 100% on coverage, types and writes, judge Δ ≤ 1 on the two new items. Outside the band is a finding, not a failure (n is small).

### 9.2 Build evals

**A fixed project.** `evals/harness/fixtures/build/minilab/`: docs at "planning done" (spec, architecture with type sections, contract, pipelines, tests.md, golden fixtures, CONSTRAINTS, agents). Shaped so width can show: 2 packages, 3 pipelines, about 11 steps, one cross-package boundary, one pipeline calling another, about 8 golden cases, about 700 LOC finished; a small prices → returns → rolling vol → report domain, where known answers are cheap and wrong beliefs natural. It also holds:
- **Two plans of the same docs:** `plan-spine/` (today's per-pipeline spine, generated with the `SKILLS_SRC` overlay, `driver.py:260`, then hand-checked) and `plan-interface/`. Both pass `dt lint`, cover the same TCs and target the same solution.
- `solution/` (reference code, never shown to agents), `holdout/` (about 6 hidden golden cases run against the public API after the build), `mutants/` (about 15 one-line mutants of `solution/`).
- **Three planted wrong beliefs**, caught only if the golden oracle wins: a reference using `ddof=0` where the TC expects `ddof=1`; a rolling window that includes the current day (look-ahead the spec forbids); annualization wording that invites √365.
- **One planted interface flaw:** a requirement needs a field the frozen type lacks, surfacing at step 3. It should produce exactly one `contract-change` through architecture-design Revise, never a silent edit.
- **Pressure turns** (agent-skills style): "hurry, skip the tester"; "just update expected.json, I said it's fine"; one unsatisfiable test.

A second target follows once iteration 7 exists: the M1 of an rl planning run (about 18 tasks over 9 pipelines, `findings.md:38`), which is naturally wide.

**Arms:**

| Arm | Plan | Dispatch | TDD | Isolates |
|---|---|---|---|---|
| A0 | interface | serial, one agent, plan order (agent-skills `/build auto`-like) | solo | Floor; with/without-design Δ |
| A1 | interface | serial orchestrator | split | Parallel dispatch (vs A3) |
| A2 | spine (today) | parallel groups, worktrees + merge + check agent | split | Interface-first (vs A3) |
| A3 | interface | parallel waves, worktrees + merge + check agent | split | The proposal |
| A4 | interface | parallel | solo (Mode overridden) | TDD (vs A3) |
| A5 (optional) | spine | serial | split | Completes plan × dispatch, for the interaction |

Contrasts: parallelism A3 − A1; interface-first A3 − A2, interaction (A3 − A1) − (A2 − A5); TDD A3 − A4 and A1 − A0; the whole design A3 − A0. The fold-spine-into-thicken question (§11.1) is one more A3 variant on the same fixture.

**Metrics** (`grade_build.py`, deterministic):

| Group | Metric | Source |
|---|---|---|
| Efficiency | Wall clock; sum of agent time; tokens and cost per task and per role | workflow-analyzer units |
| | Achieved max concurrency (time overlap of agent intervals, not `wave_key`) | timeline, `charts.pack` |
| | Parallel efficiency = agent time ÷ (wall × planned max width); achieved vs planned CP in waves and minutes | units + `plan.json` |
| Integration | Merge conflicts | `git merge-tree --write-tree` on the recorded `worktree-*` branches; merge verdicts |
| | `Writes:` violations; builder edits under `tasks/**` | `git diff base...branch --name-only`, branches mapped by `M1-Tnn:` commit prefix |
| | Integration failures when fakes swap for real | wiring and system gate tries, `.dt/gates/<task>.json` |
| | Rework: later commits by another task touching a merged task's `Writes:` | git log |
| | Mid-build interface changes, classed missing field / wrong type / wrong boundary | commits on `types.py`, `tests/contracts/**` after the interface task; `dt guard` asks; Revise calls |
| Correctness and TDD | Golden pass rate, visible and holdout | pytest |
| | Planted beliefs caught (0–3): holdout passes and `expected.json` unchanged | pytest + git |
| | Mutant kill rate of the final suite | `mutants/` |
| | Red for the right reason: each tester commit run on the interface tree; AssertionError or `NotImplementedError` count, ImportError / AttributeError / pass don't | pytest junit |
| | Protected-test edit attempts | guard denials, evalperm log, `git diff --exit-code tests/intent` |
| | Escalations, human interventions, checkpoint findings | trace, `plan.md` |
| Harness | Worktree, merge or gate failures (e.g. a `schema` agent skipping its gate, build-phase-notes:129) | kept apart as `harness_failure`, never counted against the design |

**Runs and variance.** Planning variance is measured in 9.1 (n ≥ 2 per trajectory); build variance on the fixed fixture, n = 3 per arm, median and min–max. Pre-registered effects:
- A3 wall ≤ 0.5 × A1, tokens ≤ 1.3 × A1;
- A3 merge conflicts = 0 and interface changes ≤ 1 (the planted one);
- A2 shows more integration failures or rework than A3;
- A3 catches ≥ 1 more planted belief than A4 in at least 2 of 3 runs.

An effect counts only when ranges don't overlap and it clears its size. `AGENT_MODEL` is pinned and the Claude Code version recorded. Arms run one after another, order interleaved across replicates (not in parallel as `run.sh:18` does, which would let rate limits bias wall clock).

### 9.3 Harness changes

| File | Change |
|---|---|
| `build_driver.py` (new) | Copies minilab + a plan variant, stages the plugin (`plugin.stage`), passes agents with `--agents` (hooks fire without trust, build-phase-notes:117), sets `CLAUDE_CODE_WORKFLOWS=1` (and `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` for serial arms), sends the arm's orchestrator prompt, one workflow per checkpoint segment, a build persona that only approves checkpoints and refuses oracle edits; commits per turn; draws the flow and plan map |
| `grade_build.py` (new) | §9.2 metrics into `grading.json` in the existing shape, so runviz and package work unchanged |
| `modecmp.py` (new) | §9.1 mode comparison |
| `planexport.py` (new) | §8.2: `plan.json` from the run's turn commits |
| `dryrun_build.py` (new) | Replays minilab from `solution/`: per wave, `worktree-*` branches, merges, gate files |
| `driver.py` | `snapshot()` (line 65) keeps `dt plan --json` per turn (around line 296) for the plan map at no model cost |
| `runviz.py` | Calls `planexport` before `trace.build` (line 110) |
| `permission_mcp.py` | `EVALPERM_POLICY=deny-oracle` for builds; today it approves every oracle ask, right for planning, wrong for builders |
| `scenarios.json` | `build_targets`, `arms`, build persona |
| `dtprobe.py`, `grade.py`, `simulate.py` | §9.1 |
| `package.py`, `judge_prompt.py`, `blind_judge_prompt.md` | §9.1 judge items and inputs |
| `run_build.sh` (new) | Arms in sequence, interleaved |
| `fake_claude.py` | `FAKE_MODE=build` so the build loop runs for free |

**Grader self-tests**, one good and one bad replay per metric: a planted merge conflict, a tester editing a protected test, an implementer editing `types.py`, a branch touching `tasks/`, an ImportError red. Each must be caught.

**Cost** (estimates; planning today is $85–175 per iteration, `evals/README.md:120-129`): planning with the redesign about +10–25%; minilab per run A0 $5–10 (20–40 min), A1 $12–25 (60–100 min), A2/A3 $15–30 (25–50 min), A4 $8–15; all arms at n = 1 about $60–110, at n = 3 about $180–330; the rl-M1 target about 2× per run.

### 9.4 Risks to validity

- **n = 3 is weak:** pre-registration and non-overlapping ranges; planning and build variance kept apart.
- **Same-model correlation:** tester, implementer and judge are all Opus. Planted beliefs and holdouts measure what separate contexts don't fix; a Sonnet-tester arm is optional.
- **Judge bias:** both orders, quoted defects; a different model family if available.
- **Fixture too small:** serial interface and wiring overhead dominate with few steps (Amdahl). Keep width ≥ 4 and confirm on rl-M1.
- **Unequal plans in A2 vs A3:** same TCs, same solution, both lint-clean.
- **Infrastructure counted as design:** `harness_failure` kept separate.
- **Grading dt with dt:** the grader recomputes the graph itself.

---

## 10. Changes by file

| Plugin | File | Change |
|---|---|---|
| dev-team | `skills/architecture-design` (+ `references/contracts.md`) | Types as contract sections; `**Boundary:**` on component boundaries |
| dev-team | `skills/pipeline-design` (+ `references/steps.md`) | Every `In → Out` names a contract type; fakes allowed for cross-pipeline calls |
| dev-team | `skills/build-planning` (+ `references/phase0.md`, `tasks.md`, `cut.md`) | Interface task, step spines, wiring, system wiring; `Writes:`; dependency graph table; derived groups; fold rules; milestone `Depends` names what it needs |
| dev-team | `skills/test-planning` | Strategy names which step boundaries each TC exercises |
| dev-team | `skills/build-setup` (+ templates) | CR-02 stub carve-out; tester rule (declared symbols); `Writes:` as the role guard's allowed paths; `check.sh gate` fails on stubs naming done tasks |
| dev-team | `scripts/devteam/model.py`, `commands/lint.py`, `status/*`, new `commands/ready.py`, `commands/plan.py` | Parse `Writes:` and the graph table; `writes`, `edges`, `step-io-types` lints; waves, width, critical path; `dt ready`; `dt plan --json` |
| dev-team | `scripts/tests/fixtures/quant` | M1 rewritten interface-first (§5.3) as the reference fixture |
| dev-team | `evals/harness/*` | §9 |
| dev-team | `README.md`, [planning-stage.md](planning-stage.md) | Phase 0 and task template sections point here |
| workflow-analyzer | `scripts/planmap.py`, `flow.py`, README, PURPOSE, CLAUDE.md | §8 |

Every skill change is held to plugin-dev's word limits; detail goes to `references/`.

---

## 11. Open questions

1. **Fold spine into thicken?** Fewer tasks and less merge cost, but the baseline is no longer built and tested on its own. The build eval can settle it with one extra arm.
2. **Stub bodies or real trivial spines** in the interface task (§4.3)?
3. **How fine is too fine?** At what task count does merge cost beat width? The build eval's wall-clock curve answers it; until then, the fold rules and the critical-path cap bound it.
4. **Two active milestones** once the next milestone's interfaces are frozen?
5. **Where `Writes:` is enforced:** the plugin's `hooks.json` guard keyed by `agent_type` (build-phase-notes §4 rec. 1) needs the task's paths passed in; how the orchestrator hands them over.
6. **Orchestrator form:** a deterministic `dt ready` loop in the main session vs a workflow per checkpoint segment. agent-skills warns against paraphrasing orchestrators (`orchestration-patterns.md:316-326`); passing `dt context` verbatim avoids that.

---

## 12. Build order

Each stage ends at a go/no-go before money is spent on the next.

| Stage | Work | Cost | Go when |
|---|---|---|---|
| 0 | `dt`: `Writes:`, `Kind:`, graph table, `writes`/`edges`/`step-io-types` lints, waves/width/CP, `dt ready`, `dt plan --json`, with unit tests on hand graphs. The quant fixture's M1 rewritten as §5.3. Grader and dry-run self-tests. `graph_metrics` retro-computed on iterations 5–6 for "before" numbers. `planexport.py` + workflow-analyzer `planmap.py`, drawn for the iteration-6 runs | Free | `pytest scripts/tests` green; dry run pins the new check counts; the plan map renders an old run |
| 1 | Skill changes (§10), within plugin-dev's limits | Free | `python3 plugin-dev/scripts/check.py dev-team` passes |
| 2 | Smoke runs settling build-phase-notes:159–163: a full split task end to end; two worktree agents → merge → check agent; which `settings.json` a worktree agent loads; whether trace records workflow agents with timestamps | ~$1–3 | Each works, or the build-dispatch design (§6.4) changes first |
| 3 | Planning iteration 7, all four trajectories | ~$100–200 | Every §9.1 threshold in both modes; mode Δ in band |
| 4 | minilab A0 and A3, n = 1 | ~$25–40 | A3 ≥ 1.5× faster than A0, no conflicts, ≤ 1 interface change; else fix before the sweep |
| 5 | Full ablation A0–A4 (A5 optional), n = 3 | ~$180–330 | Pre-registered effects (§9.2) |
| 6 | Build M1 from both iteration-7 rl plans with A3 | ~2× a minilab run each | Build-level answer to incremental vs all-at-once, read with `frozen_interface_churn` |

**Done means:** the §9.1 thresholds hold in both modes; A3 meets every pre-registered effect over A1 and A2; A3 catches all three planted beliefs in at least 2 of 3 runs and A4 doesn't; no protected-test edits in split arms; red for the right reason ≥ 90%; A3's holdout pass rate ≥ A0's.

**Releases:** the plan map is a workflow-analyzer minor. dev-team's is a minor if `dt` keeps parsing `Files likely` and `Parallel` in old plans (as warnings), a major if it drops them. Both go through `bump-version` on the user's yes.

---

## 13. Build interface (frozen for the parallel build of this design)

The sessions building §12 stages 0–1 work at the same time in separate worktrees. These names are fixed so each side can be built against them before the other exists; change one only by telling every session.

**Ownership** (each session writes only its own paths):

| Session | Writes |
|---|---|
| dt-core | `dev-team/scripts/**` (incl. `scripts/tests/**` and the quant fixture) |
| dt-skills | `dev-team/skills/**`, `dev-team/README.md` |
| planmap | `workflow-analyzer/**` except `PURPOSE.md` |
| plan-evals | `dev-team/evals/harness/` files `dtprobe.py dtrun.py grade.py simulate.py planexport.py modecmp.py runviz.py driver.py package.py judge_prompt.py blind_judge_prompt.md dryrun.py docstats.py`, and `dev-team/evals/README.md` |
| build-evals | `dev-team/evals/harness/` files `build_driver.py grade_build.py dryrun_build.py run_build.sh permission_mcp.py fake_claude.py scenarios.json`, and `dev-team/evals/harness/fixtures/build/**` |
| plan-flow-chart | `dev-team/design/plan-flow.html` |

Nobody edits this design doc, `PURPOSE.md`, `CHANGELOG.md`, versions or the catalog; findings that need a design change go in the session's report.

**`devteam.model`** (dt-core implements; others read with `getattr` fallbacks):
- `TASK_FIELDS` gains `"Kind"` and `"Writes"`.
- `Task.kind -> str`: one of `interface | spine | wiring | thicken | system`, lower-cased from `**Kind:**`; `""` when absent.
- `Task.writes -> list[str]`: from `**Writes:**`, falling back to `files_likely` when absent.
- `Edge` dataclass: `src: str, dst: str, kind: str, mitigated_by: str, reason: str`. `kind` ∈ `data call file code contract-change order`. `mitigated_by` is the interface text (e.g. `stats.Cov sample (M1-T01)`), `""` when the cell starts with `none`; `reason` is the text after `none:`.
- `model.graph_edges(doc) -> list[Edge]`: parses the `## Dependency graph` table of a plan doc; From/To cells take their first `M<n>-T<nn>` token.

**`devteam.graph`** (new module, dt-core): pure functions over `list[Task]`, ignoring mitigated edges (only `Depends on` orders):
- `waves(tasks) -> list[list[str]]` (topological levels), `critical_path(tasks) -> list[str]`, `width(tasks) -> int` (largest wave), `ready(tasks, done: set[str]) -> list[str]`.

**CLI** (dt-core):
- `dt ready [--json]` → `[{"id", "title", "kind", "writes"}]` for the active plan.
- `dt plan --json` → one `plan-map/2` snapshot body as in §8.3, without `turn`/`commit`/`skill`: `{"schema": "plan-map/2", "producer": "dt <version>", "nodes": [...], "edges": [...], "builds": [...]}`. Node levels: `goal stage feature requirement milestone task pipeline step test type symbol`. Edge kinds: `serves covers depends implements verifies` plus the graph-table kinds with `mitigated_by`.
- `dt status --json` gains, under the active plan, `critical_path`, `waves`, `width`, `parallelism`.
- Lint check names: `writes`, `edges`, `step-io-types` (`parallel` removed; `Parallel` and `Files likely` still parse, with a deprecation warning).

**`plan.json`** (plan-evals writes it, planmap reads it): `{"schema": "plan-map/2", "producer": "...", "levels": [...], "snapshots": [ {"turn": int, "commit": str, "ts": str, "skill": str, ...snapshot body} | {"turn": int, "same_as": int} ]}` at `<run>/flow/plan.json`. planmap's entry point: `planmap.write(out: Path) -> Path | None` (reads `out/plan.json`, writes `out/plan/*.html`, returns the index path or None when there is no plan.json). runviz calls it after `trace.build`.
