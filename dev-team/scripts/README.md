# dt — dev-team doc tool

One stdlib-only CLI that parses every planning doc. Skills, hooks and agents get IDs, statuses, sections, coverage and lint from it instead of reading and counting by hand. Design: [design/planning-stage.md §10, §13](../design/planning-stage.md); the task graph, `dt ready` and `dt plan`: [design/interface-first-design.md §6, §8.3, §13](../design/interface-first-design.md); probes: [design/probes.md §3.4, §4, §5, §11](../design/probes.md).

```
python3 <plugin>/scripts/dt.py [--root DIR] <command> …
```

- **Skills** call it as `python3 ../../scripts/dt.py …` relative to the skill's own folder (resolve the skill folder first; the project root is the current directory).
- **Hooks** call `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dt.py" …`.
- Stdlib only, Python ≥ 3.9. Tests: `python3 -m unittest discover -s scripts/tests`.

## Layout

```
scripts/
  dt.py                    CLI entry; dispatches to devteam/commands/<command>.py
  devteam/
    md.py                  markdown primitives: fences, headings, header line, bold-key fields, tables, ID refs
    repo.py                Repo: doc map, doc kinds, ID definitions (incl. retired), lookup, next_id
    model.py               typed views: Task, Edge, Checkpoint, Finding, TodoItem, Pipeline, Step, TestCase,
                           Stage, Milestone, Reference, Symbol, Component; cross-doc helpers (spine_done,
                           smoke_command, milestone_references, contract_types, graph_edges…)
    graph.py               a plan's task graph from Depends on: waves, width, critical path, ready set; task halves
    buildstate.py          a build's state under <git-common-dir>/dt-build/, git plumbing, tree hash, Writes matching
    dispatch.py            what a build can dispatch: ready halves, due reviews, holds (barrier, Critical, blocked, risk)
    workflow.py            the Workflow script `dt build workflow` emits (the A3-WF eval arm)
    specdocs.py            spec/architecture Changelog matching and fence checks (ported from arch-status.py)
    code.py                project source via ast: module docstrings, entry-function calls, pipeline drift
    outline.py             one file's outline (ast defs/classes, markdown headings) and selections (symbol, heading)
    references.py          references/ vs docs/references.md: file hashes, files waiting for reference-intake
    probes.py              probes/PB-NN-*/ vs docs/probes.md: code hash, results.json shape, redaction scan,
                           the api-probe status lists and the build-planning gate
    git.py                 thin git helpers (commit dates, HEAD text, changed files); degrade outside git
    edit.py                byte-preserving, mode-keeping reads/writes; every file dt writes goes through it
    status/                `dt status` reports: common.py, packages.py, one module per skill
    commands/<name>.py     one module per command: add_arguments(parser), run(args, repo) -> int
  tests/
    fixtures/quant/        sample single-package project mid-M1 (the canonical worked example), with two
                           reference files (references/) and their index; its roadmap predates stages. M1 is
                           planned interface-first (design §5.3): 14 tasks, critical path 4
    fixtures/legacy-plan/  the same M1 as an old-style plan (Phase 0 spines, Parallel, Files likely), swapped in
                           by `dt_helpers` (`legacy=True`) so old plans stay tested
    fixtures/staged-roadmap.md  the same roadmap with stages (S1 cut into M1, S2 not yet cut)
    fixtures/probes/       laid over the quant copy by `dt_helpers.add_probes`: docs/probes.md (PB-01 Answered
                           pass, PB-02 Ready with the agent's C1 run, PB-03 retired) and probes/ (PB-02's sample
                           holds a planted email); the helper cites them from AD-03 and a new AD-04 (Proposed,
                           Scope portfolio) and writes PB-02's .env and PB-01's out/, which git never holds
    fixtures/buildmini/    the smallest project a live build runs on: one package, PL-01, TC-01, a 4-task M1
                           (interface, barrier, spine, split thicken, wiring, exit); make_live.py renders
                           build-setup's templates onto a copy (its README says how)
    dt_helpers.py          run dt in-process; throwaway fixture copies (optionally under git)
    build_helpers.py       a git repo of buildmini with a stub scripts/check.sh, for the build-command tests
    test_<area>.py         unittest, stdlib only
```

Commands never glob or open docs themselves; they ask `Repo` (doc map, IDs) and `model` (typed views). A parsing fix goes in `md`/`repo`/`model` so every command sees it.

## Doc format (what the parser reads)

- **Doc kinds** come from the path (`repo.KINDS`): brief, idea, roadmap, spec, architecture, package-architecture (`docs/packages/<pkg>/architecture.md`, legacy `docs/architecture/<pkg>.md`), contract, pipelines, tests, references (`docs/references.md`), probes (`docs/probes.md`), constraints, agents, plan, todo, queued-plan, archived-plan. `tasks/archive/**` is read only for `next-id` and as a `section` fallback.
- **Header:** first non-blank line after the H1, `**Key:** value` pairs joined by ` · `. Unknown keys are kept.
- **ID sections:** `## <ID>: <Title>` or `### <ID>: <Title>`, outside code fences. A section runs to the next heading of the same or higher level. ID forms: `PL-NN`, `TC-NN`, `AD-NN`, `CR-NN`, `S<n>`, `M<n>`, `M<n>-T<nn>`, `M<n>-R<nn>`, `<pkg>.<symbol>` (any `PREFIX-NN` works as a heading ID).
- **Spec requirements:** bold-led lines `- **CODE-NN** …` plus their indented sub-bullets. Struck (`~~`) on the line = removed.
- **CONSTRAINTS rules:** bold-led `- **CR-NN** …` lines and table rows whose first cell is `CR-NN`.
- **Retired:** `- ~~<ID>: <title>~~ Retired YYYY-MM-DD: <reason>`. A decision heading with a struck title (`### AD-02: ~~Old~~`) is superseded and counts as retired.
- **Tasks** (`### M<n>-T<nn>: <Title>` in a plan): bold fields `Package`, `Step`, `Kind`, `Covers`, `Size`, `Mode`, `Skills`, `Read`, `Verify`, `Depends on`, `Writes`, `Blocked`, `Reason`, and an `**Acceptance:**` checkbox list. `**Kind:**` is `interface | spine | wiring | thicken | system`. `**Writes:**` is the task's exclusive claim: exact paths, or one directory glob (`dir/**`, `dir/*`, `dir/`). A task from before these fields has no Kind and falls back to `**Files likely:**` for its writes; `**Parallel:** G<n>` still parses (both give a `deprecated` warning).
- **Interface-first plan:** one with a `## Dependency graph` section or a task with `Kind:`/`Writes:`. The section holds one table, `| From | To | Kind | Mitigated by |`: From depends on To (the direction of `Depends on`), each cell's first `M<n>-T<nn>` is the task. Kind is `data | call | file | code | contract-change | order`. Mitigated by names the interface that removes the wait (`stats.Cov sample (M1-T01)`: a contract symbol ID an interface task freezes), or `none: <reason>`. A mitigated edge is documentation and never orders; an unmitigated one is also in `Depends on`. A dependency on an interface task needs no row.
- **Contract types:** a contract section titled `type` (`### <component>.<Type>: type`), or one with a `**Kind:** type` field. Its sample is its `**Sample:**` path, else the `**Fixtures:**` folder on its `- **Boundary:** … · **Fixtures:** tests/contracts/<component>.<Type>/ · **Cases:** …` line. A step table's `In → Out` cell names types by CamelCase name or `pkg.Name`; single capitals (`T`) and all-caps words aren't types.
- **Findings:** list items `- M<n>-R<nn> <Severity> · <rule> · <text> → <disposition>` under a checkpoint's `**Findings:**`.
- **Ranges:** `STAT-01–STAT-04` and `STAT-01–04` expand to every ID in between.
- **Pre-build sections:** any heading containing `(pre-build`.
- **Reference entries** (`docs/references.md`, design/references.md §4): `### RF-NN: <Title>`, then `**File:** \`references/…\` · **Hash:** <8 hex> · **Kind:** code|doc · **Milestones:** S2, M4 | all | —` and bullet fields `- **Purpose:**`, `**Key parts:**`, `**In → Out:**`, `**Use for:**`, `**Caveats:**`. Retired entries are retired lines. "References for M<n>" are derived: entries whose `Milestones` names it (`all` serves every milestone; `—` none), plus the milestone section's `**References:**` line, or, with no such line, the entries assigned to its stage. There is no other list. A `Read:` item `RF-NN:<selector>` names the entry `RF-NN`.
- **Probe entries** (`docs/probes.md`, design/probes.md §4.2): `### PB-NN: <Title>`, then `**Folder:** \`probes/PB-NN-<slug>/\` · **Hash:** <8 hex> · **Status:** … · **Milestones:** S1 | M2 | all | — · **Last run:** —|<date>|<ISO time>` and bullet fields `- **Question:**`, `**Informs:**` (decisions, requirements with ranges, contract symbols), `**Spends:**`, `**Checks:**`, `**Verdict:**`, `**Caveats:**` (`**Docs read (<date>):**` is kept as text). Status is `Draft`, `Ready`, `Answered · pass|fail · <date>` or `Waived · <date> — <reason>`. The checks table under the entry is `| Check | What | How | Pass | Runner | Result |`; each row `C<n>` is the section `PB-NN.C<n>`; Runner starts with `agent` or `user` (`user (manual)`, `user (sandbox key)`). Retired probes are retired lines. The index's header needs no Status. A PB entry is routed like an RF entry (Milestones, `Read: PB-NN[:selector]`). A decision's `**Probe:** PB-NN — <question>` or `**Probe:** none — <why the docs settle it>` (bullet or plain line, architecture docs) cites it; `dt next-id PB` counts cited IDs too.
- **Probe folders** (`probes/PB-NN-<slug>/`): code files are every file except `evidence/`, `out/`, dot-files and dot-folders (`.env`, `.env.example`), caches and `*.md`. **Hash** = the first 8 hex of sha256 over, for each code file in sorted relative-path order, `path + NUL + bytes + NUL`; probe_kit writes the same value as results.json's `script_hash`. `evidence/results.json` (§4.3) needs `probe` (the entry's ID), `script_hash` (8 hex), `run_at` (ISO 8601), `runner` (agent|user) and `checks`: each key a `C<n>` of the entry's table, holding `pass` (true, false or null) and `observed`, and an optional string `note`; other keys are kept. Samples are `evidence/samples/*`.
- **Roadmap** (`docs/roadmap.md`): a stage table (first column `Stage`: `S<n>`, Name, Source, Status*) written by idea-refine, and a milestone table (first column `Milestone`: `M<n>`, Stage, Name, Packages, Pipelines, Depends, Status*) written by build-planning when it cuts a stage into milestones. `## S<n>: <Name>` sections carry `**Outline:**` and `**Skills:** a, b` (idea-refine); `## M<n>: <Name>` sections carry `**Outline:**`, `**Exit:**`, `**Plan:**`, `**Outcome:**` and optionally `**Skills:**` and `**References:**` (build-planning narrows a stage's skills and references per milestone). A milestone with no `**Skills:**` line takes its stage's; its Source is its stage's. A roadmap from before stages has only the milestone table, with a `Source` column and no `Stage` column: each such milestone stands for its own stage and is read as before.

## Commands

Exit codes everywhere: `0` ok, `1` problems found (lint errors, missing IDs, a gate not met), `2` usage error.
Text output is the default and is written for agents: short `key: value` lines, one item per line. `--json` (where listed) prints one JSON object for scripts and evals.

### `dt status [--skill NAME] [--summary] [--json]`

What a skill needs before it starts. Always printed:

```
skill: <name or —>
mode: <mode>                     # per skill, below; "blocked" when an upstream gate isn't met
blocked: <reason>                # only when mode is blocked
docs: brief Accepted · spec Approved · architecture Approved (Single package) · roadmap ok · plan M1 In progress · constraints Approved
next ids: AD-04 PL-05 TC-04 M3 M1-T07
```

- `docs`: each doc's Status, or `missing`. `roadmap` is `ok`, `stale (run dt roadmap)` or `missing`; `plan` is `M<n> <Status>`, `Between milestones`, `foreign` or `missing`.
- `next ids`: AD, PL, TC, S (once the roadmap has stages), M, plus `M<n>-T` while a plan is active. AD also counts every AD the architecture docs mention, so a broken fence can't hide one.

Every report (any `--skill`, or none) then prints the reference files waiting for `reference-intake`:
- `references_unindexed` — files under `references/` (hidden files and caches skipped) with no entry
- `references_changed` — `RF-NN (path)`: the file's hash differs from the entry's Hash, or the entry has none
- `references_missing` — `RF-NN (path)`: the entry's file is gone

Then skill-specific lines. Lists print as `key: a, b, c` or `key: none`; per-package maps as `pkg=mode, …`. Each key is printed even when empty, so a skill can rely on it. Exit 1 when mode is `blocked`, else 0.

With an active plan or not, the plain report (no `--skill`) and `build-planning` end with the plan's derived graph (`devteam/graph.py`; only `Depends on` inside the plan orders, mitigated graph rows never do):
- `critical_path` — the longest chain, `M1-T01 → M1-T05 → …`; ties go to the heavier chain (XS 1, S 2, M 4), then to plan order
- `waves` — topological levels: wave 0 has no dependencies, wave k's deepest dependency is in wave k−1
- `width` — the largest wave; `parallelism` — tasks ÷ critical path (2 decimals)
- `graph_warning` — when at least 3 waves exist and most have width 1; else `none`
- `critical_path_halves` — the longest chain of the halves the build dispatches (`M1-T01.solo → M1-T04.tester → M1-T04.implementer → …`; `graph.critical_path_halves`): a split task is a tester half then an implementer half, a tester half waits only on the interface tasks upstream, everything else on its `Depends on`
- `file_edges_on_path` — `file` graph rows between consecutive tasks of `critical_path` (`M1-T14 → M1-T09 (reason)`), each a planning choice; else `none`

`--json` prints one object with the same keys (`next_ids` for `next ids`); lists stay lists, maps stay objects, `blocked` is `null` when not blocked. `drift` is a list, or the string `"unknown"` until `dt layout`'s drift check is available; build-setup's generated-config checks are `"unknown"` when their input file is absent. `dependents` is `{pkg: [dependents]}`. Structured extras in JSON only: `ideas` and `packages` are objects, `roadmap_rows` is a list of `{id, name, source, status}`, `prefixes` is `{PREFIX: {highest, next}}`, and architecture-design adds arch-status.py's `spec` (`path`, `status`, `live_requirements`) and `architecture` (`path`, `exists`, `status`, `shape`, `last_updated`) objects.

| `--skill` | Modes | Extra keys |
|---|---|---|
| `idea-refine` | new · extend | `brief_words`, `brief_goals` (count), `ideas` (path=status), `roadmap_rows` (`S<n> name [source]`: the stages; on a roadmap from before stages, its milestone rows), `references_unassigned` (RF entries with `Milestones: —`) |
| `spec-writing` | blocked · new · extend | `ideas_ready` (Accepted ideas), `prefixes` (`highest→next` per prefix), `reserved_prefixes` (planning prefixes a requirement must not use: AD, CR, EX, PB, PL, RF, TC), `skills` |
| `architecture-design` | blocked · new · revise · extend · current | everything the old `arch-status.py` reported (`uncovered`, `changed_since`, `spec_rows_pending`, `stale`, `next_decision`, `package_docs`, `packages_found`, `skills`, `broken_fences`), plus `contracts_missing` (packages with no `contract.md`; `(no package id yet)` when no id can be found or inferred), `legacy_layout` (`docs/architecture/<pkg>.md` files to move), `grow_triggers`, `stale_contracts`, `probes_answered` (`PB-01 pass (AD-04)`, `PB-01 waived (AD-04)`: Answered or Waived probes whose decisions are still Proposed), `probes_failed` (`PB-01 (AD-04)`: Answered fail with a decision still Proposed; must be empty at its gate) |
| `pipeline-design` | blocked · new · grow · revise · extend · sync · current (per package) | `packages` (pkg=mode), `uncovered_ids` (spec IDs covered by a component in scope but on no pipeline step or Covers, system pipelines included), `components_unowned` (components that own no step), `drift` (entry calls ≠ step table, from `dt layout`), `retired_refs` (`path:line ID`), `misplaced` (pipelines whose Entry lies in another package's source folder) |
| `test-planning` | blocked · new · revise · extend · current (per package) | `packages` (pkg=mode), `pipelines_no_smoke`, `pipelines_no_golden`, `cases_no_source`, `cases_no_tolerance`, `fixtures_missing` (folder or `expected.json`), `fixtures_orphan` (`tests/fixtures/*/TC-NN/` no live case uses), `skills` |
| `build-planning` | blocked · new · extend · replan · advance · foreign · current | `milestone` (active M and status), `progress` (done/total), `next_task`, `blocked_tasks`, `uncovered` (milestone spec IDs on no task and not Deferred), `no_spine` (milestone pipelines with no task that builds them: a wiring task, a `Kind: system` task for a system pipeline, or with no Kind a Phase 0 task; archive included), `mode_violations`, `boundaries_unfrozen` (`pkg.symbol (consumers)`: a contract symbol whose `**Boundary:**` line names a milestone package (in a single-package architecture, also any of its components), with no `**Fixtures:**` folder yet and in no contract task's `Read:`; the contract task is the interface task, or with no Kind the Phase 0 `**Step:** contract` task), `draft_pipelines`, `changed_since_plan` (milestone docs Approved after the plan's Last updated), `probes_blocking` (`PB-01 → service, ledger.BankTxn (M1)`: probes the milestone to plan meets, below), `interfaces_changed` (`stats.Cov (M1-T04, M1-T05)`: a symbol the plan's interface task froze whose contract section, `**Used by:**` lines aside, differs from its text at the plan's last commit, with the tasks that read it or whose steps' `In → Out` cells name it; outside git, or with the plan uncommitted, every frozen symbol of a contract.md in `changed_since_plan`), `stage_to_cut` (`S<n> name`: the first stage with no milestone rows that is Designed, whatever earlier milestones still wait for their plans; or `none`), `pipelines_inferred` (that stage's pipelines, inferred from its Source, for build-planning to divide among the milestones it cuts; or a milestone's when its Pipelines cell is empty), `milestone_references` and `milestone_skills` (the references and skills serving that same stage or milestone; references include PB entries whose Milestones name it), `references_unrouted` (`RF-NN (M<n>)`, `PB-NN (M<n>)`: for the active and each queued plan, a milestone reference in no task's `Read:`, selector ignored), `skills_unrouted` (`skill (M<n>)`: a milestone skill on no task's `**Skills:**`), `stage_unrouted` (`skill (S<n>)`, `RF-NN (S<n>)`: for each cut stage, a stage skill or reference that none of its milestones carries), `skills_missing` (referenced by the plan, its tasks or the milestone's `**Skills:**`, not installed), `skills_available`, `grow_triggers`, `drift` (milestone pipelines), `stale_contracts`, `queued`, `base` |
| `api-probe` | new · revise · record · waiting · current | `index` (probes.md status, `ok` with none, or `missing`), `probes_unwritten` (`PB-01 (AD-04)`: cited by a `**Probe:**` line, no entry), `probes_open` (`PB-01 (user: C1, C3–C9)`: Ready, with the checks that have no Result and no record in results.json, by runner), `probes_results` (`PB-01 (<run_at>)`: a non-Draft entry whose results.json `run_at` is newer than its Last run, or `(results.json invalid: …)`), `probes_stale` (`PB-01 (results <hash>, code <hash>)`: results.json's `script_hash` isn't the code's hash), `evidence_leaks` (`dt probes --scan` hits, `path:line (pattern)`), `next_id` (next PB) |
| `reference-intake` | new · extend · current | `index` (references.md status or `missing`), `files_to_read` (unindexed and changed files), `outline_first` (`.py` files to read over 400 lines: give the subagent `dt outline` plus the first lines), `next_id` (next RF), `milestones` (`S<n> name` and `M<n> name`, to assign files to; assign to a stage unless a milestone is already cut for it) |
| `build-setup` | blocked · new · extend · ratchet · current | `constraints` (status), `config_mismatches`, `contract_mismatches`, `optional_layers_existing`, `deptry_missing`, `protected_gaps`, `ignores_without_exception`, `agents_missing`, `hooks_missing` (hook and check scripts, plus any `scripts/…` an agent file names), `not_executable`, `expired_exceptions`, `tools_missing` (uv, jq), `dependents` (`pkg<-a,b`), `base` |

`skills` and `skills_available` list installed skills by name: the project's `.claude/skills/*/SKILL.md` plus `$CLAUDE_PLUGIN_ROOT/skills/*` when that is set, minus dev-team's own planning skills (reference-intake and api-probe included).

`--summary` (SessionStart hook) prints at most 8 lines: active milestone and plan status, progress and next task, blocked tasks, queued plans, docs waiting for approval (Draft), a stale roadmap, `references: N waiting → reference-intake` when any reference file is unindexed, changed or missing, `probes: N waiting → api-probe` when results aren't recorded yet (`probes_results`) or a cited PB has no entry (`probes_unwritten`), and `dt: python3 <resolved path to dt.py>`. It prints nothing in a project with none of `docs/brief.md`, `docs/spec.md`, `docs/roadmap.md`, `tasks/plan.md`, never fails (an internal error prints one `dt status: error: …` line) and always exits 0.

Mode rules:
- **blocked** — idea-refine never; spec-writing: no brief; architecture-design: no spec (as arch-status.py; a Draft spec shows in `docs`); pipeline-design: architecture missing or not Approved; test-planning: no package has an Approved pipelines.md (a package whose pipelines.md isn't Approved is `pkg=blocked`); build-planning: the next milestone to plan has pipelines not all Approved, the next stage has spec IDs on no Approved pipeline, a Revise is open on the active milestone's docs, or (all-at-once) a brief stage is below Designed (below); build-setup: no active plan, or the plan is Draft.
- **architecture-design** — `new`: no architecture.md; `revise`: `probes_answered` is non-empty (a probe's results go into its decisions first); `extend`: `uncovered`, `changed_since`, `contracts_missing` or `legacy_layout` non-empty (the last two migrate projects designed before contract.md and `docs/packages/`); else `current`.
- **pipeline-design** (per package; the overall mode is the first of new, grow, revise, extend, sync present) — `new`: no pipelines.md; `grow`: `misplaced` lists one of its pipelines; `revise`: pipelines.md is Draft but Approved at git `HEAD`; `sync`: drift; `extend`: uncovered IDs or unowned components; else `current`.
- **test-planning** (per package) — `new`: no tests.md; `revise`: tests.md Draft but Approved at `HEAD`; `extend`: a pipeline with no smoke command or no golden case; else `current`. A pipeline with `**Part of:** PL-NN` (a package's part of a system pipeline) needs no smoke or golden case of its own.
- **build-planning** — first rule that holds: `foreign`: `tasks/plan.md` exists without a dev-team header (no `**Milestone:**`) and has unchecked tasks; never overwrite, ask. With an active plan: `advance` when every todo item is checked and the exit checkpoint is ticked (a finished milestone advances even while a Revise is open: that belongs to the next plan); `blocked` (`waiting for <doc> approval (Revise in progress)`) when a pipelines.md or tests.md of the milestone's packages is Draft, or a doc defining one of its pipelines (`draft_pipelines`) is; `extend` whenever `stage_to_cut` is set (the stage is cut first, rows only, even while the active milestone needs a replan or the next milestone waits for its plan); `replan` when a task is `Blocked`, `interfaces_changed` is non-empty, or `changed_since_plan` is: the packages' pipelines.md, tests.md or contract.md is Approved with a `Last updated` date later than the plan's (same-day changes aren't seen; a Replan bumps the plan's date); `extend` when the next milestone is Designed (one to queue); else `current`. A `new` or `extend` whose unit is a milestone becomes `blocked` (`waiting for PB-01`) while `probes_blocking` is non-empty; cutting a stage is unaffected. The milestone's packages are its roadmap Packages, its pipelines' packages and its tasks' Package. With no active plan (missing or between milestones): when no plan was ever written and every stage's Source is `brief` (all-at-once), `blocked` while any uncut stage is below Designed (`S2, S3 below Designed: … no pipelines.md for eval, ml; run pipeline-design`, naming the packages with no pipelines.md); `new` (no plan ever written, the first unit Designed) or `extend` when `stage_to_cut` is set; `extend` if a queued plan exists; otherwise for the next unit (`roadmap.next_unit`: in roadmap order, pre-stage milestones first, then each stage's milestones, or the stage itself while it has none; the first not yet Planned/Building/Done, or for a stage, not yet Split): `new` (no plan ever written) or `extend` for a Designed milestone, else `blocked` (`M2 pipelines not all Approved (…)`, or `S2 spec IDs on no Approved pipeline (PORT-03)`). No roadmap: `new` once any pipelines.md is Approved.
- **Milestone pipelines** (build-planning and `dt roadmap`) — the milestone row's Pipelines cell; a stage, or a milestone whose cell names none, has them inferred from its Source (a milestone's is its stage's): the spec Changelog rows citing its idea files (`brief` → rows citing brief.md) give the milestone's IDs (minus those marked removed), and its pipelines are the live package and system pipelines whose Covers include any of them (step Covers only for a pipeline with no Covers line, since a reused step cites an earlier milestone's IDs). `pipelines_inferred` prints the inferred set for the unit the mode acts on (the stage to cut, the milestone to queue or plan, else the active one), empty when a milestone's cell is filled; an explicit cell always wins.
- **Probes blocking a milestone** (design/probes.md §3.3) — a probe that is open (Draft, Ready), Answered fail with a decision still Proposed, or cited by a decision's `**Probe:**` line with no entry yet, meets the milestone when one of its decisions (its Informs' ADs and the decisions citing it) has a `**Scope:**` naming the milestone's packages, its pipelines' packages or their step Owners (`system` meets every milestone), or its Informs names a contract type of one of those, or a type the milestone's steps pass. Answered pass and Waived probes never block.
- **api-probe** — the first that holds: `new` (`probes_unwritten`), `revise` (`probes_stale`), `record` (`probes_results`), `waiting` (`probes_open`), else `current`. Never blocked.
- **build-planning task modes** (design/build-phase.md §3.2: keyed to the oracle, not the Kind) — expected `split` when the task's acceptance names a `TC-NN`, holds a Given/When/Then, or names a model criterion (a spec requirement a `model evaluation` test case cites, or one under a spec heading that says model), or its `Writes:` include a `tests/intent/` path; `solo` otherwise. Only `**Reason:** mode: <why>` overrides; a Reason about anything else doesn't. Items read `M1-T11: solo, expected split (acceptance names TC-02)`.
- **reference-intake** — `new`: no docs/references.md and files under `references/`; `extend`: the index exists and any of the three `references_*` lists is non-empty; else `current`.
- **build-setup** — `new`: no CONSTRAINTS.md; `ratchet`: the plan is advance-ready and CONSTRAINTS.md's header `**Ratcheted:** M<n>` isn't this milestone (build-setup Ratchet writes it); `extend`: the plan header's `Base` is pending (kickoff: `dt base` hasn't recorded the approved bar yet); else `current`.
- `base` — the plan header's `Base`; `pending` when missing or `—`.
- **build-setup generated-config checks** (each prints `unknown` when its input is absent: `pyproject.toml`, or for `protected_gaps` both `scripts/check.sh` and CONSTRAINTS.md's protected list):
  - `dependents` — per component (single package) or package (multi), everything that depends on it directly or not, from the root architecture's Components/Packages `Depends on`; `check.sh --pkg` scopes to the id plus these.
  - `contract_mismatches` — `[[tool.importlinter.contracts]]` (layers, with `|` independent siblings and `:` open siblings; forbidden; independence) vs the architecture: a node may import what it depends on, directly or not, and no other node. Lists each import a contract forbids but the architecture allows, and each the architecture forbids but no contract does. Modules compare by their last segment.
  - `optional_layers_existing` — `"(pkg.component)"` layers whose module now exists under `src/` or `packages/*/src/`.
  - `deptry_missing` — no `[tool.deptry]` in the root pyproject (single) or in `packages/<pkg>/pyproject.toml` (multi).
  - `protected_gaps` — `tests/intent/**` or `tests/fixtures/**` not covered by `PROTECTED=(…)` in `scripts/check.sh` or by CONSTRAINTS.md's `**Protected list**` line, and the two lists differing.
  - `ignores_without_exception` — Ruff `per-file-ignores` entries (standing `tests/**` and `__init__.py` exempt) and deptry `per_rule_ignores` names that no Exceptions row mentions.
- `expired_exceptions` — Exceptions rows (`EX-NN`) whose `Expires` date is past, or whose `M<n> exit` milestone has an archived plan or a Done roadmap status.
- `config_mismatches` — every CONSTRAINTS.md table row with a `CR-NN` ID and a backticked `tool.…` config key: the numbers in its Rule (or Today) cell vs the key's value in `pyproject.toml` (a table's numeric values must include them all). Also reports an unset key or a missing `pyproject.toml`.
- Contract freshness — `contract.md`'s last git commit vs the newest commit touching the package's contract module (each component's `__init__.py` in a single package, else `src/**/<pkg>/__init__.py`); reported as `stale_contracts` (`pkg (contract.md <date>, code <date>)`). Empty outside git.
- Grow triggers (measurable only): a package with > 3 pipelines, > 12 modules (non-`__init__` `.py` files) under its source folder (from its pipelines' Entry paths, else `src/<pkg>/`), or package docs over 2,000 lines (a single package counts the root architecture.md).
- Package ids come from `docs/packages/<pkg>/`, legacy `docs/architecture/<pkg>.md`, the roadmap's Packages column and, for a multi-package architecture, its package table. A single package none of those names yet gets an inferred id: the `src/<pkg>/` the architecture's Project layout names most, else `pyproject.toml`'s `[project] name`, else a lone `src/<pkg>/__init__.py`. It is used for `contracts_missing` and pipeline-design's `packages` (`<pkg>=new`).

Differences from the old scripts: paths are repo-relative (`docs/architecture.md:688`, `docs/ideas/x.md`); `package_docs` lists both layouts as paths; `broken_fences` also covers `contract.md`; `skills` also includes plugin skills when `CLAUDE_PLUGIN_ROOT` is set; spec requirements are bold-led lines only (outside code fences); architecture-design is `extend` (not `current`) while contracts or the `docs/packages/` move are outstanding; idea-refine no longer creates `docs/`.

### `dt next-id <prefix>…`

`PL`, `TC`, `AD`, `CR`, `RF`, any spec prefix, `S` (stages), `M`, `M2-T`, `M2-R`. Counts retired IDs and the archive. Prints one ID per prefix.

### `dt section <ID>…`

Prints each ID's defining section (heading section, requirement line with sub-bullets, table row or retired line), preceded by `<!-- path:line -->` (`--no-path` omits it). Missing IDs go to stderr and exit 1.

### `dt context <task> [--json]`

The builder's whole context packet, in this order (stable material first, active material last, per agent-skills `context-engineering`):
1. A two-line preamble: task ID, package, mode, and "read only what is below, plus CONSTRAINTS.md and the files you edit" (§9).
2. Every `Read:` entry, in order: ID → its section (as `dt section`, archive not searched); a repo path → `### <path>` then the file in a fence (a missing file is noted, not fatal). An entry is a path if it has a `/`, exists, or ends in a file extension.
   A reference `RF-NN[:<selector>]` → its index entry (once per packet), then the file under a fixed banner:
   ```
   ### Reference RF-01: references/market_decomposition.py
   > Reference, not part of the project. Reuse what fits the contract and step table as is, adapt it, or ignore it: your call.
   > Never import from references/. Anything you bring over meets the same bar as the rest of the code.
   > Caveats: <the entry's Caveats; line omitted when it has none>
   ```
   A probe `PB-NN[:<selector>]` → its index entry with the checks table (once per packet), then `### Reference PB-NN: <folder>/…` under the same banner with `probes/` in the import line, plus `> Probe code: written to answer PB-NN's checks, not to production standard. Its Verdict and Caveats follow.`, `> Verdict: …` and `> Caveats: …`. No selector: the folder's code files with line counts and its samples; `PB-NN:outline`: every code file's outline; `PB-NN:samples`: each `evidence/samples/*` file in a fence; `PB-NN:<file>`: that file (whole, or its outline past 300 lines); `PB-NN:<file>:<symbol or heading>`: one part. `out/` and `.env*` files are never shown (a problem, exit 1).
   An RF entry is followed by one of: the whole file (no selector, ≤ 300 lines); its outline (`RF-NN:outline`, or no selector on a file over 300 lines, with a note to name a part); one part (`RF-NN:<symbol>` — a module-level def, class or assignment, or `Class.method`, via `ast` — or `RF-NN:<heading>` in markdown, case-insensitive), preceded by `(<selector> · lines a–b of N)`. A selector that names nothing is a problem (exit 1); a missing reference file is noted, not fatal.
3. `## Layout (\`dt layout <pkg>\`)` — the task package's real tree, when its source folder exists (built pipelines point at `dt layout` instead of a planned layout, and the builder shouldn't have to run it).
4. `## Interfaces (frozen: …)` — the frozen interfaces the task's steps cross that `Read:` doesn't already show: the contract types their `In → Out` cells name (each followed by `Sample: <path> (exists|not written yet)`), and the contract symbols named after a step (its signature). A `PL-NN` Step (wiring, system) covers every step of the pipeline. Omitted when empty.
5. `## Writes (edit only these files; …)` — the task's `Writes:`, each `(exists)`, `(new)` or `(folder)`; the edit boundary. A task with no `Writes:` gets `## Files likely` instead, marked `(exists)` or `(new)`.
6. The task section itself, last.

The task is looked up in `tasks/plan.md` and `tasks/queued/`. Warns on stderr (exit stays 0) when the packet is over 2,000 lines. Exit 1, nothing on stdout, if the task or any `Read:` ID is missing or retired. `--json`: `task`, `package`, `mode`, `kind`, `lines`, `read` (each `ref`, `kind` id|file|reference; a reference adds `where`, `file`, `selector`, `shown` whole|part|outline|missing), `interfaces` (each `id`, `where`, `type`, `sample`), `writes` (each `path`, `exists`, `folder`; empty without a `Writes:` field), `files_likely`, `text` (the packet). The preamble adds `· kind <kind>` when the task has one.

### `dt ready [--json]`

Every task of the active plan that can start now, so an orchestrator fans out in one turn (design §6.4). A task is ready when it isn't ticked in `todo.md` and every `Depends on` inside the plan is (`graph.ready`). A split task whose own dependencies aren't all done but whose interface tasks upstream are (`graph.tester_ready`) is listed as its tester half: the tester writes against the frozen interface. Plan order. Text: `<id> [<kind>, tester half] <title> · writes: …`, or `ready: none`. `--json`: a list of `{"id", "title", "kind", "writes", "part"}`, `part` being `task` or `tester`. No active plan: message on stderr, exit 1.

### `dt ready --halves | --reserve [--cap N]`

The build's view (design/build-phase.md §6.1), one JSON object, needs git: `{"rows", "over_cap", "in_flight", "cap", "holds", "held", "all_landed"}`. `rows` are due reviews first, then ready task halves by `remaining_cp` (descending), then plan order, tester before implementer. A builder row is `{"id", "role" (tester|implementer|solo), "agent_type" (tester|implementer), "title", "kind", "pkg", "remaining_cp", "claim" (`<task>.<role>`), "prompt"}`; `prompt` is the one-line prompt, ``You are the <role> for <task>. Run `python3 <abs>/dt.py claim <task> --role <role>`, then read the packet it names.`` A review row is `{"id" (`<checkpoint>.<pkg>`), "role": "reviewer", "agent_type": "reviewer", "title", "kind" (interface|phase|exit), "pkg", "checkpoint" (`M1-T01` or `exit`), "tasks", "commits" (their `Dt-Landed:` commits, oldest first), "base" (the first one's parent), "end", "paths" (the tasks' Writes), "lead", "findings_file" (`dt-build/reviews/<checkpoint>.<pkg>.md`), "remaining_cp", "claim" (`<checkpoint>.<pkg>.reviewer`), "prompt"}`.
- A tester half is ready when the interface tasks upstream of its task are ticked and `dt/<task>-tests` doesn't exist; an implementer half when that branch exists and every `Depends on` is ticked; a solo half when every `Depends on` is. Reserved and claimed halves aren't listed.
- A review is due per package of a checkpoint's phase (the tasks between the previous checkpoint and it; the milestone exit: every task) once they are all ticked and no recorded review covers them; a second exit review covers only the tasks added since. One row per checkpoint is `lead`.
- `remaining_cp`: the size-weighted (XS 1, S 2, M 4) longest chain of halves from this one (`graph.remaining_weight`).
- `holds` (nothing is released): an unresolved Critical from a recorded review; an unresolved NEEDS-DEP or CONTRACT-CHANGE escalation. `held` (`{"id", "role", "why"}`): halves of a task after a `(barrier)` checkpoint whose reviews haven't all passed (`barrier: …`); blocked halves (rejected twice, three harness failures in a row, an unresolved TEST-WRONG escalation); a `**Risk:** external` task without `dt build resolve <task>`.
- `--cap N` (default 6) lists at most N minus `in_flight` (reservations plus unfinished claims); `over_cap` counts the rows left out. `--reserve` writes `dt-build/reserved/<claim>.json` for each listed row.

### `dt plan [--json]`

The plan as one `plan-map/2` snapshot body (design §8.3) for workflow-analyzer's plan map: `{"schema": "plan-map/2", "producer": "dt <version>", "levels": [...], "nodes": [...], "edges": [...], "builds": [...]}`, with no `turn`, `commit` or `skill` (the exporter adds those).
- **Nodes** `{id, level, parent, title, attrs, expects, hash}`, in level order: `goal` (`G<n>`, the brief's numbered Goals), `stage` (roadmap stages; attrs `status`, `source`), `feature` (a spec `### Name (`CODE`)` heading, id its code; parent its first stage; attrs `stages`, `stage_via`, `source`), `requirement` (each live spec requirement; parent its feature, else attrs `section`; expects `criteria`), `milestone` (parent its stage; `status`, `packages`, `pipelines`, `depends`), `task` (active and queued plans; parent its milestone; attrs `kind`, `size`, `mode`, `package`, `step`, `status` done|open|blocked; expects `acceptance`, `verify`, `reads`, `writes`, `tests` (TC IDs in Read), `covers`), `pipeline` (parent the first milestone listing it; `package`, `system`, `entry`, `trigger`; expects `covers`), `step` (`PL-NN.<name>`, parent its pipeline; `num`, `owner`, `in_out`, `spine`; expects `covers`, `in_types`, `out_types`), `test` (parent its pipeline; `pipeline`, `fixture`, `kind`), `type` and `symbol` (contract sections; `package`, and a type's `sample`). `hash` is 12 hex of the rest of the node, so any change to it shows.
- **Edges** `{from, to, kind}`: `serves` (feature → each goal on its Serves line), `covers` (pipeline, step, test case or task → each live requirement it covers), `depends` (task → each Depends on), `implements` (task → its Step: a step, or a pipeline), `verifies` (test case → its pipeline), and each dependency-graph row with its own kind plus `mitigated_by` and `reason`.
- **Builds**, one per planned milestone: `{milestone, state (active|queued), tasks, critical_path, waves, width, parallelism}`.

A feature's stages come from the first rule that finds any: its `**Stage:** S<n>` line (`Stage line`); else a spec heading starting with the stage ID that groups it (`spec heading`); else, when stages' Sources add different IDs, the stages whose Source added its requirements, earliest first (`stage source`); else the stages whose milestones list a pipeline covering them (`milestone pipelines`, a parent only when that is one stage).

Text output: node counts per level, how many requirements a pipeline, a test and a task cover, then each build with its waves.

### `dt outline <file|RF-NN>`

One file's outline, read without importing or running it. The first line is `<path> · <kind> · <n> lines`; then:
- `.py` (`python`): `<line>: <signature> — <docstring first line>` for each module-level def and class, methods indented under their class (via `ast`). A file that doesn't parse falls back to the first lines, noted `cannot parse`.
- `.md` (`markdown`): `<line>: ## <heading>` for every heading outside code fences.
- anything else (`text`): the first 40 lines, noted `first N lines`.

`RF-NN` outlines that entry's File. Exit 1 if the file can't be read as UTF-8.

### `dt references [RF-NN…] [--stamp]`

Without `--stamp`: one line per entry, `RF-NN: <file> · ok|changed (now <hash>)|unstamped|missing · <milestones>`, then `unindexed: …` (when no IDs are given). With `--stamp` (mechanical, below): writes each entry's Hash.

### `dt probes [PB-NN…] [--stamp | --scan]`

Without a flag: one line per entry, `PB-NN: <folder> · <Status> · hash ok|unstamped|hash changed (now <hash>)|folder missing · results <run_at> (current|for other code; n/m checks)|no results|results invalid: … · <milestones>`. `--stamp` (mechanical, below) writes each entry's Hash. `--scan` runs the redaction scan over every `probes/*/evidence/` (or the named probes'): token shapes (`access-production-…`, `public-sandbox-…`), `sk-…` keys, credentials in URLs (`?api_key=…`), emails, card-like (13–19 digits, spaces or dashes allowed) and other 8+ digit runs, phone numbers, hex runs of 24+, mixed-case base64 runs of 32+, and every secret-looking value (8+ characters, not a URL, with a digit or 16+ long) in the probe's `.env`/`.env.*` (not `.env.example`) and the project's `.env`. It prints `path:line (pattern)` per hit and never the matched text, then `scan: N hits` (exit 1) or `scan: clean`.

### `dt layout <pkg> [--json]`

```
package: quant
root: src/quant/
  __init__.py — Quant Lab.
  data/
    pipeline.py — PL-01 entry: load prices.
PL-01: ok
PL-02: not built (src/quant/stats/pipeline.py missing)
```

- **Source folder:** each of the package's pipelines' `Entry` folders, cut after its last `<pkg>` component (so a single package with component subfolders shows the whole package), then their common prefix; else `src/<pkg>/`. Unknown package (no `docs/packages/<pkg>/` and no folder) → exit 2.
- **Tree:** files then subfolders, alphabetically; hidden, cache and build folders skipped. Each `.py` shows its module docstring's first line, or `(no docstring)`.
- **Pipelines** (the package's `pipelines.md`): the entry function's top-level calls (outermost calls per statement, in order; calls used as arguments don't count), read with `ast` only — project code is never imported or run — compared with the step table's step names. A call is named by its final attribute (`data.load_prices(…)` → `load_prices`) and `from … import x as y` aliases are resolved. Lines: `PL-NN: ok`, `PL-NN: drift — calls […] vs steps […]` (also when the entry function is undefined or the file doesn't parse), `PL-NN: not built (<entry file> missing)`.
- Exit 1 on drift. `--json`: `package`, `root`, `exists`, `tree` (`path`, `dir`, `doc`), `pipelines` (`id`, `entry`, `status` ok|drift|missing|no-entry, `calls`, `steps`, `detail`).
- `devteam/code.py` exposes `pipeline_drift(repo, pipeline)` (the drift detail, or None) and `check_pipeline` for `dt status` and lint.

### `dt lint [paths…] [--changed] [--json] [--hook]`

No paths → the whole doc map (archive excluded). Paths (files or folders; a folder means every doc under it; relative to `--root`, else the current directory) → only problems located in those files; cross-doc checks still read the whole repo. `--changed` → docs changed vs `HEAD` plus untracked ones (outside git: exit 2). Output: `path:line: <code> <message>` sorted by path and line, then `N errors, M warnings`. `--json`: `problems` (`path`, `line`, `code`, `severity` E|W, `message`), `errors`, `warnings`. Exit 1 if any error; warnings don't fail. A malformed doc yields findings, never a traceback.

Checks (code: severity):
- `dup-id` E — an ID with two live definitions, or one with a retired line that is still defined elsewhere
- `missing-ref` E — an ID (`PB-NN` included) in a `Read:`, `Covers`, `Step`, `Pipeline`, `Used by`, `Part of` or `References` field, or a `Covers`, `Pipeline(s)`, `Used by` or `Read` table column, that isn't defined anywhere (archive counts as defined). `Read:` entries that look like paths (`/` or a file extension) are skipped; `PL-02.step` checks `PL-02`; `RF-01:pca_factors` checks `RF-01`, `PB-01:probe.py:get` checks `PB-01`. A decision's `**Probe:**` line isn't checked here (a cited PB with no entry is `probes_unwritten`). Ranges expand. Changelog sections are skipped. (`Depends on` is checked by `depends`.)
- `retired-ref` E — a literal mention of a retired ID (retired line, struck decision heading, struck requirement) anywhere outside code fences, except: retired lines and superseded/removed definitions themselves, the decision named in `Superseded by AD-NN`, and Changelog sections. An ID only reached through the inside of a range (`STAT-01–STAT-06`) isn't flagged
- `budget` W — size budgets (§3), in lines. Package docs are budgeted per unit: contract.md > 8 per live symbol (`### comp.symbol`) + 12; pipelines.md > 35 per live pipeline + 10, plus the lines of its `## … (pre-build …)` layout section; tests.md > 10 per live TC + 15. Fixed: plan.md and queued plans > 400, a probes.md entry > 10 non-blank lines plus its checks table (header, separator, one per check), a roadmap `## S<n>` or `## M<n>` section > 6 non-blank lines, AGENTS.md/CLAUDE.md `## Docs` + `## Project skills` > 25
- `grow-size` W — a package doc over a per-file ceiling (contract.md 200, pipelines.md 300, tests.md 300 lines), however well it keeps to its per-unit budget: the package holds too much for one set of docs, and architecture-design should consider a Grow
- `approved-edit` W — a doc whose `HEAD` version and working copy are both Approved but whose text (header line and trailing whitespace excluded) differs: it was edited without going back to Draft, or the approval isn't committed yet. Skipped outside git, for files not in `HEAD`, and for plan/queued/todo/roadmap (dt's mechanical edits). In contract.md, `**Used by:**` lines are ignored: pipeline-design appends PL IDs there without a Revise; in references.md and probes.md, Hash values are ignored (`dt references --stamp` and `dt probes --stamp` write them)
- `prebuild-left` E — a pre-build section inside a `PL-NN` section whose pipeline is built, or one outside any pipeline (Planned layout) when every pipeline in that doc is built. Built = `model.pipeline_built`, the same rule as `dt prebuild-clear`: the task that builds it (its wiring task; with no Kind, its Phase 0 spine task) checked in `todo.md`, or (no such task in the active plan) entry file exists
- `pipeline-fields` E — a package pipeline (`PL-NN` in pipelines.md) with no `Entry` or `Trigger`, or a step row whose Owner or Spine version cell is empty (`—` counts as empty). A system pipeline (`PL-NN` in the root architecture.md: package → package over named contracts) needs only a `Trigger` and steps (a table or a numbered `1. …` list); no Entry, Owner or Spine version
- `contract-heading` E — a contract.md `##`/`###` heading that starts with a `pkg.symbol` but isn't `<pkg>.<symbol>: <title>`: most often one naming several symbols (`train.train / train.train_seeds: …`, split on `/ , · & + and`), else a symbol with no `: <title>`. dt resolves a symbol only from its own heading, so `Read:` and `dt context` would fail on it later
- `spine-mock` W — a pipelines.md Spine version cell containing mock, stub, fake, TODO or placeholder: the spine must be a real baseline (system pipelines are skipped). `contract fake` / `boundary fake` is allowed: a fake of another package generated from an approved contract, not a mocked step
- `fixture-size` — per TC with a `Fixture:` folder: folder missing, or no `input.json` / `expected.json` → **E**; folder over 100 KB → W (also for a `tests/fixtures/<pkg>/TC-NN/` folder no TC names, reported at the folder). Optional TC fields such as `Parse:` and `Skills:` aren't checked
- Task checks run on `tasks/plan.md` and `tasks/queued/*.md` written by build-planning (a foreign plan is skipped):
  - `task-size` E — Size not XS/S/M, or the source files it writes outside the size's range (XS 1, S 1–2, M 3–5): `Writes:` (else `Files likely`) minus test files (`tests/**`, `test_*.py`). An interface task is sized by judgment
  - `task-acceptance` E — more than 3 top-level bullets under `**Acceptance:**` (indented sub-bullets don't count)
  - `task-title` E — the word "and" in a task title (any case)
  - `task-fields` E — missing Package, Step, Size, Mode, Read, Acceptance or Verify (in an interface-first plan also Kind and Writes); Mode not split/solo; Kind not one of the five
  - `task-step` W — Step `PL-NN.<name>` names a step that isn't in that pipeline's table
  - `depends` E — a `Depends on` task that isn't defined, comes at or after the task **in plan order** (position in the file, not ID number: Replan reorders without renumbering), or a cycle (reported once). A task from another plan or the archive resolves
  - `milestone-size` E — the plan's critical path (`graph.critical_path`: the longest `Depends on` chain; mitigated graph rows don't order; dependencies on other plans ignored) is over 15 tasks. The message names the chain. Parallel tracks don't add up, so the total task count isn't capped; the plan's line budget bounds it
  - `writes` — two tasks with no `Depends on` path between them (either way) whose writes overlap (same path, or one inside the other's folder glob), across the whole plan: E, or W when either side claims only through `Files likely`. And E: a task with a Kind other than interface, wiring or system writing a shared file (`__init__.py`, `types.py`, `__main__.py`, or a pipeline's Entry file)
  - `edges` E (interface-first plans) — a `Depends on` whose graph row is mitigated (mitigated edges don't order); a `Depends on` with no graph row (or no `## Dependency graph` section), except on an interface task; a row whose From or To names no task or an undefined one; a Kind outside the six; `none` with no reason; a mitigation that names no `pkg.Symbol`, or one no interface task freezes (in its `Read:`, or a `tests/contracts/<pkg.Symbol>/` path in its `Writes:`); an unmitigated `data` row across a type an interface task freezes (To's step Out ∩ From's step In), or `call` row across a frozen symbol (`<owner>.<step>` of From's steps that To reads or builds): mitigate it instead of waiting on code
  - `writes-unit` E (interface-first plans) — a task other than an interface task whose `Writes:` outside `tests/intent/` name no `tests/unit/` path: every implementer and solo half writes unit tests
  - `call-fake` E (interface-first plans) — a `call` graph row marked `none` whose callee (a `pkg.symbol` in its reason, or `<owner>.<step>` of From's steps that To reads or builds) is a contract symbol no interface task freezes: freeze its fake and mitigate the row, or give `none: integration: <what runs the real chain>`
  - `deprecated` W — a task's `**Parallel:**` (derived now) or `**Files likely:**` (use `**Writes:**`)
  - `verify-smoke` E — a task whose `Verify:` lacks its Step pipeline's smoke command (tests.md Strategy `Smoke` cell, else the pipeline's Trigger + ` --smoke`) when one is due: always for wiring and system tasks, and for any other task once its `Depends on` path reaches that pipeline's wiring task (with no Kind: every task outside Phase 0). Interface and spine tasks, and thicken tasks beside the wiring, land before the pipeline runs
  - `finding-disposition` E — a finding under a checkpoint with no `→ <disposition>`
  - `task-ref` E — a task ID in a task's Acceptance text, or in a graph row's Mitigated by cell (mitigation or `none:` reason), that names no task in any plan or the archive; a bare `T41` reads as the plan's own milestone's (`M1-T41`)
- `todo-mismatch` E — task IDs in todo.md ≠ plan.md (each side reported in its own file)
- `step-io-types` — in a package pipeline's step table, a type an `In → Out` cell names that no contract type section defines (bare name or `pkg.Name`), or a step whose Out names no contract type (entry arguments on the In side may stay plain). E once any contract has a type section, W before (projects from before typed contracts)
- `type-cases` — a contract type that crosses step owners (steps of two or more owners name it in `In → Out`, reused `PL-NN as built` steps aside, or its `**Boundary:**` line names a consumer) with no `**Cases:**` (or `—`): the interface task writes one sample per case. E once any contract type names a case, W before
- Reference checks (design/references.md):
  - `ref-file` E — an RF entry with no File, or whose file is missing
  - `ref-hash` W — an RF entry whose Hash isn't its file's current one (or has none)
  - `ref-large` W — a task reads an `RF-NN` whose file is over 300 lines with no selector (it would get only the outline)
  - `ref-prefix` E — a spec requirement uses the reserved `RF-` prefix
  - `roadmap-skill` W — a roadmap stage's or milestone's own `**Skills:**` names a skill that isn't installed (same list as `skills_available`)
  - `spec-stage` E — once the roadmap has stages, a spec feature with no `**Stage:**` line (nor a stage heading grouping it), or one naming no stage row
  - `roadmap-stage` E — once the roadmap has stages, a milestone row whose Stage cell names no stage row, isn't an `S<n>`, or is empty on a row with no Source of its own
- Probe checks (design/probes.md §4–§5):
  - `probe-fields` E — a PB entry with no Folder, Question or Informs, no checks table, a check with an empty Pass cell, a Status that isn't Draft, Ready, Answered · pass|fail or Waived, or (past Draft) a missing folder
  - `probe-informs` E — an Informs ID (decision, requirement, contract symbol) that isn't defined
  - `probe-cite` E — a decision's `**Probe:**` line naming a retired PB, `none` with no reason, or neither a PB nor `none`
  - `probe-runner` E — `public.py` (the agent's checks) touches the environment or a key (`os.environ`, `environ`, `getenv`, `.env`, `load_env`, `dotenv`; comments ignored), reported at its line; or a check whose Runner isn't agent or user
  - `probe-leak` E — a `dt probes --scan` hit, at the evidence file and line (the pattern, never the text)
  - `probe-sample` E — a doc names a probe sample (`PB-01 samples/sync_added.json#0`, `PB-01:samples/…`) that doesn't exist, or a PB with no entry
  - `probe-results` E — an `evidence/results.json` that isn't the shape above, or names a check the entry's table lacks (at the file and line)
  - `probe-stale` W — the entry's Hash isn't its code's (unstamped or changed), or results.json is for other code
  - `probe-large` W — a probe over 400 source lines (`.py .sh .js .ts .html`, the copied probe_kit.py aside)
- `foreign-plan` W — tasks/plan.md without a dev-team header (no `**Milestone:**`, not Between milestones); it gets no other checks
- `broken-fence` E — a fence that never closes, or one that holds a `## ` line (unless its info string is `markdown`/`md`)
- `header` E — a doc of a known kind with no header line, or no Status. Roadmap and probes.md need a header but no Status; todo, AGENTS.md/CLAUDE.md and a foreign plan are exempt
- `unreadable` E — a doc-map file that isn't valid UTF-8
- `internal` W — a check crashed (a `dt` bug); the other checks still run

**`--hook`** (plugin hooks): reads the Claude Code hook JSON on stdin (`hook_event_name`, `cwd`, `tool_input.file_path`), uses `cwd` as the root (ignores `--root`), always exits 0 and fails open (bad JSON or any exception → no output).
- `PostToolUse`: lints only the edited file, and only if it's under `docs/`, `tasks/` or `probes/` or is CONSTRAINTS.md/AGENTS.md/CLAUDE.md. Errors → `{"decision": "block", "reason": "<lines>"}` (feeds the problems back; the edit stays). Warnings only → `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "<lines>"}}`. Clean → nothing.
- `Stop`: like `--changed`; any problems → `{"systemMessage": "dt lint: <n> problem(s)\n<lines>"}`. Never blocks.

### `dt roadmap [--check]`

Rewrites the roadmap's derived `Status*` columns. Milestones: Idea → Specced → Designed → Planned → Building → Done. The first rule that holds, from the top:
- **Done** — an archived plan for it exists, or the roadmap section has an `**Outcome:** Done …` line
- **Building** — it's the active plan and at least one todo item is checked
- **Planned** — a plan for it exists (queued, or active with no checked task)
- **Designed** — every live pipeline of the milestone is defined in an Approved pipelines.md or architecture.md (system pipelines); retired IDs are skipped. The pipelines are its `Pipelines` cell, or, when that names none, the set inferred from its Source (see Milestone pipelines under `dt status`); none at all → not Designed
- **Specced** — every idea file its `Source` cites is Specced; for a `brief` row, the brief is Accepted and the spec Approved
- **Idea** — otherwise

Stages: while a stage has no milestone rows, Designed / Specced / Idea by the same rules on its inferred pipelines and Source, and Designed (ready to cut) also needs every live spec ID its Source adds (its spec Changelog rows, `all` meaning every live requirement; removed IDs aside) on an Approved pipeline's Covers line or a step's Covers. Once cut into milestone rows: **Done** when every milestone is, **Building** when any is Building or Done, **Planned** when any is Planned, else **Split**. An older roadmap's `Cut` reads as Split: `--check` accepts it, a write replaces it.

Prints one `S<n>:` or `M<n>: <old> → <new>` line per change, then `roadmap: ok` / `roadmap: updated N`. `--check` prints the differences and exits 1 instead of writing. Writes the file in place through `edit.py` (no Edit/Write, so hooks don't fire), touching only the Status cells and keeping line endings and the file mode. No roadmap, or neither table has a Status column: message on stderr, exit 1.

### `dt guard` (PreToolUse hook)

Reads the hook JSON on stdin (`tool_name`, `tool_input.file_path`, or `notebook_path`; `cwd`); the hook runs on Read as well as Edit, Write, MultiEdit and NotebookEdit. The path is taken relative to `cwd`. Prints the hook decision JSON:
- any tool, Read included, matched anywhere in the path (design/probes.md §5.2): a `.env` or `.env.*` file other than `.env.example`, or anything under `probes/*/out/` → `permissionDecision: "deny"`. A Read stops here: the rules below are for writes
- `probes/*/evidence/**` (matched anywhere) → `"deny"` (only a probe's scripts write evidence)
- `tests/fixtures/**/expected.json` (matched anywhere in the path, so a nested project's oracles are covered too) → `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "Oracle file: …"}}`
- `tasks/archive/**` under `cwd` → `permissionDecision: "deny"` (only `dt archive` writes there)
- `tests/contracts/**` (matched anywhere; the project root is the part before `tests/`) → `"ask"` ("Frozen contract: …", CR-09) unless an unticked contract task (`**Kind:** interface`, or with no Kind `**Step:** contract` in Phase 0) in that root's `tasks/plan.md` covers it: the folder `<pkg>.<symbol>` is in the task's `Read:`, or a `Writes:` (else `Files likely`) path starts with `tests/contracts/<pkg>.<symbol>/` or claims all of `tests/contracts/`; a file directly in `tests/contracts/` is covered by any open contract task
- anything else → no output, exit 0.

Always exits 0 and fails open: unreadable input or any error → no output. `dt guard --path P [--tool T]` decides for P (relative to `--root`) and tool T (default Write) without stdin. `dt.py` runs it without building a `Repo`; only a contract path loads one, from the path's own root.

### Mechanical edits

These write files directly (atomically, via a temp file), keep every untouched byte, line ending and the file's permission bits (a new file, such as the archive, gets 0644 less the umask), and never change a doc's Status. `devteam/edit.py` holds the shared read/write helpers; every dt write (these, `dt roadmap`) goes through it.

- **`dt prebuild-clear <PL-NN>`** — replaces that pipeline's `Entry sketch (pre-build …)` subsection with `Layout: \`dt layout <pkg>\`` (just removes it if the pipeline already has that line). When every pipeline in the doc is built, also removes `## Planned layout (pre-build …)`; otherwise says which aren't. Built = the task that builds it (its wiring task; with no Kind, its Phase 0 spine task) is checked in `todo.md`, or, for a pipeline with no such task in the active plan (built in an earlier milestone), its entry file exists. Idempotent: a second run prints `nothing to clear`. Exit 1 if the pipeline isn't found.
- **`dt archive [--date YYYY-MM-DD]`** — refuses (exit 1, nothing written) unless the plan is an active milestone plan, `todo.md` has task items and every one is checked, and the archive file doesn't exist yet. Copies `tasks/plan.md` byte for byte to `tasks/archive/M<n>-<slug>.md` (slug from the plan's H1 name) with the todo appended as a final `## Todo` section; adds `**Outcome:** Done <date>` to the roadmap's milestone section if it has no Outcome (adding the section if missing) and points its `**Plan:**` link at the archive; writes an empty todo (`# Todo`); then replaces `tasks/plan.md` in place with the stub (`# Between milestones` + `**Status:** Between milestones · **Last updated:** <date> · **Roadmap:** …` + a line naming the archive), so the plan is never missing. Prints the archive path.
- **`dt finding <checkpoint-task-id|exit> <severity> <text> [--disposition TEXT]`** — appends `- M<n>-R<nn> <Severity> · <text>[ → disposition]` after the findings already under that checkpoint's `**Findings:**` (the label is created after the checkpoint's last line if absent), with the next free `M<n>-R` ID (archive counted). `exit` = the checkpoint whose title contains "exit". Severities (case-insensitive): Critical, Important, Suggestion, Nit (agent-skills `code-review-and-quality`); anything else exits 2. Prints the new ID.
- **`dt finding --from FILE [--checkpoint ID|exit] [--pkg PKG]`** — records every finding line of a reviewer's file (`<Critical|Important|Suggestion|Nit> · <rule or axis> · <where> <what> → <fix>`, optionally a list item; other lines are ignored; backticks kept, which is why the lines come from a file) under that checkpoint, each with its own ID, then commits `tasks/plan.md` on the current branch (`<checkpoint> review, <pkg>: <n> findings[, <c> Critical]`) and writes `dt-build/reviews/<checkpoint>.<pkg>.json`. The checkpoint and package default to the file's name, `<checkpoint>.<pkg>.md`. Prints that JSON: `{"checkpoint", "pkg", "outcome" (passed|critical), "findings", "critical", "counts", "tasks", "file", "file_sha256", "commit", "time"}`; the same file again prints it with `"already_recorded": true` and records nothing. Releases the review's reservation. Errors print `{"error"}` (exit 1, or 2 for a missing checkpoint or package).
- **`dt tick <M#-T##> [--undo]`** — ticks (or unticks) that task's checkbox in `todo.md` and prints `ticked: <id>` / `unticked: <id>` (`(already)` if nothing changed). When ticking the task that builds a pipeline (a wiring task; with no Kind, a Phase 0 task) it also prints `next: dt prebuild-clear <PL-NN>` for that pipeline. Exit 1 if there's no todo.md or the task isn't in it; 2 for a malformed ID.
- **`dt references --stamp [RF-NN…]`** — sets each entry's (or only the named entries') `**Hash:**` to the first 8 hex digits of its file's sha256, inserting the field after `**File:**` when absent. Prints `RF-NN: <hash>` per change, then `references: stamped N` or `nothing to stamp`. An entry whose file is missing (or that has no File) is reported and not stamped (exit 1); the rest are still stamped. reference-intake runs it after writing entries; a stamp hides a change from `references_changed`, so stamp only after re-summarizing.
- **`dt probes --stamp [PB-NN…]`** — sets each entry's (or only the named entries') `**Hash:**` to its folder's code hash, inserting the field after `**Folder:**` when absent. Prints `PB-NN: <hash>` per change, then `probes: stamped N` or `nothing to stamp`. An entry with no Folder, or whose folder is missing, is reported and not stamped (exit 1). api-probe runs it after writing a probe's code.
- **`dt base [--sha SHA]`** — sets the active plan header's `**Base:**` to HEAD's short sha (inserted after Status if absent). `build-setup` runs it once its bar is approved and committed, so guard-the-bar diffs start from a commit that already holds the bar. Exit 1 without a plan header or outside git.

## The build (design/build-phase.md §6, §10)

A milestone build's state lives under `$(git rev-parse --git-common-dir)/dt-build/`, reachable from the main checkout and every linked worktree, never committed (`devteam/buildstate.py`). A half's claim id is `<task>.<role>` (`M1-T03.tester`); a review's reservation is `<checkpoint>.<pkg>.reviewer`.

| Path | Holds |
|---|---|
| `reserved/<id>.json` | `{"id", "task", "role", "time"}` (a review adds `"tasks"`): handed out by `dt ready --reserve`, not claimed yet |
| `claims/<id>.json` | `{"id", "task", "role", "agent_type", "pkg", "worktree", "branch", "base", "time", "finished"}`; `mark-finished` adds `"finished_time"`, `"stop_agent_type"` |
| `gates/<id>.json` | `{"claim", "mode" (collect|gate), "passed", "rc", "tree", "time"}`: the Stop gate's last verdict |
| `escalations/<id>.json` | `{"claim", "task", "role", "kind" (TEST-WRONG|CONTRACT-CHANGE|NEEDS-DEP), "why", "time"}` |
| `rejects/<id>.json` | `{"id", "count" (rejects other than harness and escalated), "harness" (in a row), "last": {"reject", "kind", "detail_file", "time"}}`; removed on a landing |
| `resolved/<id>.json` | `{"id", "kind" (finding|task), "note", "time"}`; a task adds `"escalations"`, `"reopened_tester"` |
| `reviews/<cp>.<pkg>.md`, `.json` | the reviewer's finding lines; the outcome `dt finding --from` recorded |
| `details/<id>-<n>.txt` | what one `dt land` saw: changed paths, gate output, the reject or the commit |
| `log.jsonl` | one JSON object a line, `{"time", "event", …}`: start, reserve, claim, verdict, escalate, finished, land, reject, flaky, review, resolve, release |
| `land.lock` | `dt land`'s `fcntl.flock` |

**Tree hash** — the git tree id of a worktree's whole content as `git add -A` would stage it (tracked files as on disk, untracked files that aren't ignored), written through a temporary index (`read-tree HEAD`, `add -A`, `write-tree`), so it is the same whether or not the agent committed, and the worktree's index is untouched.

**Landed** — an implementer or solo half: its task is ticked in `todo.md`, which `dt land` does in the landing commit, trailer `Dt-Landed: <task> <role>`; a tester half: `dt/<task>-tests` exists. `dt build status` and review rows read the trailers (`buildstate.landings`), never commit subjects.

### `dt claim <task> --role tester|implementer|solo`

Run by the agent in its own worktree (refused in the main checkout). Refuses (exit 1, stderr) without a reservation, when another worktree holds the claim, or on a stale base: HEAD's `todo.md` lacks a landing the half needs (a tester: the interface tasks upstream; otherwise every `Depends on`). An implementer's claim merges `dt/<task>-tests` into the worktree first. Then writes `.claude/.task_writes` (the role's share of `Writes:`, one a line: tester the `tests/intent/` entries, implementer the rest, solo all), `.claude/.check_pkg` (the Package), `.claude/.dt` (this `dt.py`'s absolute path, for the project's hook scripts), adds those and `.claude/packet.md` to the shared `info/exclude`, sets `refs/worktree/checks-base` to HEAD (after the merge), links the worktree links, records the claim (base = HEAD), drops the reservation and writes `.claude/packet.md`: a role header with the done condition, then the `dt context` packet with the Writes block narrowed to the role's share (a tester's leaves out source files named in `Read:` and the package layout). Prints `packet: <path> (<n> lines; read it in full)`, `task:`, `writes:`, `done:`, `links:` when any, and on a re-dispatch `previous rejection: <reject> (<kind>), details in <file>` with its first lines. Run again in the same worktree it rewrites the files and reprints.

**Worktree links:** CONSTRAINTS.md may hold one line `**Worktree links:** data/raw, models/cache` (comma-separated paths relative to the project root, backticks and a trailing `/` allowed, `—` for none): gitignored inputs that a fresh worktree lacks. Each that exists in the main checkout and not in the worktree becomes a symlink to the main checkout's copy; a `.env*` path is never linked.

### `dt land <task> --role R [--harness] [--lock-timeout S]`

Run by the driver in the main checkout (exit 2 in a worktree), under `dt-build/land.lock` (exit 3 after `--lock-timeout`, default 600 s or `$DT_LAND_LOCK_TIMEOUT`). Refuses a main checkout that isn't clean (exit 1). Prints one JSON object: `{"landed", "reject" (writes|gate|escalated|conflict|integration|harness|null), "kind" (the escalation kind or null), "detail_file", "task", "role"}`, plus `"commit"` and `"flaky"` when landed, `"rejects"` and `"harness_failures"` (the half's counts so far) when rejected; a precondition failure prints `{"landed": false, "reject": null, "kind": null, "detail_file": null, "error"}`. In order:
1. `harness` — `--harness`, no claim, the worktree gone, or an unfinished claim with no changes. `escalated` — an escalation record for the claim.
2. `writes` — a path changed since the claim's base (committed, uncommitted, untracked) outside the role's share of `Writes:` (re-derived from the plan), or matching `scripts/check.sh protected` (run in the worktree; `*` crosses `/`, case-insensitive) other than the tester's own intent paths.
3. `gate` — the Stop gate's verdict when its tree hash and mode match the worktree's, else `scripts/check.sh collect` (tester) or `gate --pkg <pkg>` (implementer, solo) in the worktree.
4. The worktree's state is committed in the worktree. A tester's changes become one commit on `dt/<task>-tests` on the build branch's head (`git merge-tree --write-tree --merge-base <base>`, `commit-tree`; `conflict` if they don't apply); the build branch isn't touched.
5. An implementer's or solo half's is `git merge --squash`ed into the current branch (`conflict` → `git reset --hard HEAD`). The main checkout's `refs/worktree/checks-base` is set to the pre-merge HEAD (an implementer's: a commit of it plus the task's tests branch, so the tests it merged don't count as its change), and `scripts/check.sh gate --pkg <pkg>` runs on the merged tree; on failure once more: a pass records an Important flaky finding under the next checkpoint, a second failure resets → `integration` (the detail names the dependents).
6. One commit: the merge, the `todo.md` tick, `dt prebuild-clear` for a task that builds a pipeline, any flaky finding; message `<task>: <title>` + `Dt-Landed: <task> <role>`. `refs/worktree/checks-base` moves to it.
7. Every outcome: a log event; the claim, reservation and gate verdict dropped; the worktree removed (`git worktree remove --force`); its branch deleted after a landing, kept after a reject. A reject increments `rejects/<id>.json` (`harness` separately; `escalated` neither).

The gate commands time out after `$DT_GATE_TIMEOUT` seconds (default 3600). `VIRTUAL_ENV` is dropped from their environment so each checkout uses its own venv.

### `dt escalate <TEST-WRONG|CONTRACT-CHANGE|NEEDS-DEP> "<why>"`

Run by an agent in its worktree (a subfolder works): writes `escalations/<claim>.json` for the claim holding the current directory and prints the status line to end with. Exit 1 with no claim; 2 for TEST-WRONG from a tester.

### `dt build start M<n> | status | resolve <id> [--note T] | release <task|cp.pkg> <role> | workflow M<n>`

- `start M<n>` — refuses a dirty tree or a milestone that isn't the active plan's, and an existing `build/M<n>`; creates and switches to `build/M<n>`, sets `**Build:** build/M<n> started <date>` in the plan header and commits it there, adds `/.claude/worktrees/` to `info/exclude`, and records the go with a fingerprint of the plan's task blocks (`go/go.json`). Prints `{"milestone", "branch", "build", "commit"}`.
- `go [--note TEXT]` — the user's new go after a Replan: re-records the fingerprint. While the task blocks differ from the last go's (a tick doesn't count), `dt ready` holds everything with a `go:` hold. Prints `{"go", "tasks"}`.
- `status` — `{"milestone", "branch", "go", "go_current" (false after a Replan; null with no recorded go), "progress", "landed" ([{task, role, commit}]), "tests_landed", "reserved", "claims" ([{id, task, role, worktree, finished, since}]), "ready" ([{id, role}], no cap), "holds", "blocked", "held", "escalations", "reviews" ([{review, outcome, critical, critical_open, tasks}]), "findings" ({severity: n}), "next_checkpoint" ({checkpoint, title, kind, waiting_on} or null), "all_landed"}`.
- `resolve <finding|task>` — a finding (`M1-R03`): recorded, so a Critical stops holding the build. A task (`M1-T05`): its escalations and reject counts are cleared, a `**Risk:** external` task is released, and after a TEST-WRONG its tests branch is deleted so a fresh tester half is ready, or, with `--test-stands`, kept and the implementer retried (its next `dt claim` prints the decision). Prints `{"resolved", "kind"}` (a task adds `"escalations_cleared"`, `"reopened_tester"`, `"test_stands"`).
- `submit-review <checkpoint>.<pkg> FILE` — run by the reviewer in its worktree: copies its findings file to `reviews/<checkpoint>.<pkg>.md`, since a worktree agent's Write tool can't reach the git common directory. Prints `{"submitted", "file", "lines"}`.
- `workflow M<n> [--cap N] [--out FILE]` — the A3-WF eval arm (design/build-phase.md §5): a Workflow script that runs `loop.md` with dt deciding, printed or written to FILE (relative to the project root). No task ID is written into it: a low-effort agent runs `dt ready --reserve --cap N --json` and returns the rows; each row runs as an agent of its type in a worktree (a builder with dt's one-line prompt, a reviewer with the row's); each finish gets a low-effort agent that runs `dt land` (`--harness` when the builder's last line isn't `DONE`/`STOPPED <task> <role>`) or `dt finding --from` (no findings file: `release`, and a second time it is left for the driver); every landing is followed by another dispatch. Agents that touch the main checkout run one at a time. When nothing is ready or running, a status agent runs `dt build status` and the script returns `{milestone, all_landed, exit_ready, progress, next_checkpoint, go_current, holds, blocked, held, escalations, critical_open, claims, review_failures, landings, reviews, notes}`. dt is called as `python3 <this dt.py> --root <project>`. With `--out`, prints `{"workflow", "milestone", "cap", "dt", "build_started"}`. Refuses another milestone than the active plan's, `--cap` below 1, or a linked worktree.
- `prune [--dry-run]` — in the main checkout: deletes every done task's tests branch, and the branch and worktree of every logged claim that is no longer live (a rejected half's). A live claim's branch is never touched. Prints `{"pruned"}` or `{"would_prune"}`, each `[{branch, worktree}]`.
- `release <task> <role>` — drops the reservation, claim and gate verdict (role `reviewer` with `<checkpoint>.<pkg>`). Prints `{"released", "dropped", "worktree"}`; the worktree is left for the driver.

Hook-facing (they never print, and never fail the hook):
- `verdict --mode collect|gate --rc N` — stop_gate.sh, in a worktree: records `gates/<claim>.json` with the tree hash. Exit 0; nothing without a claim.
- `escalated` — stop_gate.sh: exit 0 when the claim of the current directory has an escalation record, else 1.
- `mark-finished` — SubagentStop: reads the hook JSON on stdin and marks the claim whose worktree holds its `cwd` finished. Always exit 0.
