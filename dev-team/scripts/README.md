# dt — dev-team doc tool

One stdlib-only CLI that parses every planning doc. Skills, hooks and agents get IDs, statuses, sections, coverage and lint from it instead of reading and counting by hand. Design: [design/planning-stage.md §10, §13](../design/planning-stage.md); the task graph, `dt ready` and `dt plan`: [design/interface-first-design.md §6, §8.3, §13](../design/interface-first-design.md); probes: [design/probes.md §3.4, §4, §5, §11](../design/probes.md).

```
<plugin>/scripts/dt [--root DIR] <command> …
python3 <plugin>/scripts/dt.py [--root DIR] <command> …
```

- **`scripts/dt`** is an executable shim (`#!/usr/bin/env python3`) that runs dt.py: one word, so a shell variable holding its path works in zsh, which doesn't word-split `$DT="python3 …"`.
- **Skills** call it as `../../scripts/dt …` or `python3 ../../scripts/dt.py …` relative to the skill's own folder (resolve the skill folder first; the project root is the current directory).
- **Hooks** call `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dt.py" …`.
- Stdlib only, Python ≥ 3.9. Tests: `python3 -m unittest discover -s scripts/tests`.

## Layout

```
scripts/
  dt.py                    CLI entry; dispatches to devteam/commands/<command>.py
  dt                       executable shim: runs dt.py's main without `python3`
  devteam/
    md.py                  markdown primitives: fences, headings, header line, bold-key fields, tables, ID refs
    repo.py                Repo: doc map, doc kinds, ID definitions (incl. retired), lookup, next_id
    model.py               typed views: Task, Edge, Checkpoint, Finding, TodoItem, Pipeline, Step, TestCase,
                           Stage, Milestone, Reference, Symbol, Component; cross-doc helpers (spine_done,
                           smoke_command, milestone_references, contract_types, graph_edges…)
    graph.py               a plan's task graph from Depends on: waves, width, critical path, ready set
    specdocs.py            spec/architecture Changelog matching and fence checks (ported from arch-status.py)
    code.py                project source via ast: module docstrings, entry-function calls, pipeline drift
    outline.py             one file's outline (ast defs/classes, markdown headings) and selections (symbol, heading)
    references.py          references/ vs docs/references.md: file hashes, files waiting for reference-intake
    probes.py              probes/PB-NN-*/ vs docs/probes.md: code hash, results.json shape, redaction scan,
                           the api-probe status lists and the build-planning gate
    routes.py              docs/routes.md: upstream changes routed to their owner's Revise (`dt route`)
    requests.py            docs/requests.md: the user's words as UR lines, their traces, which are open or due
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
    fixtures/gridload/     a GridLoad project (design/example-domains.md) with an interface-first M1 laid out as
                           design §4.1 has it: one entry module per pipeline, the interface task writing
                           `__init__.py`, `__main__.py`, the re-exporting `pipeline.py` and the types; PL-02 calls
                           PL-01 through `ingest.load_readings`'s Boundary; AD-02 Proposed on the Draft PB-01
    fixtures/probes/       laid over the quant copy by `dt_helpers.add_probes`: docs/probes.md (PB-01 Answered
                           pass, PB-02 Ready with the agent's C1 run, PB-03 retired) and probes/ (PB-02's sample
                           holds a planted email); the helper cites them from AD-03 and a new AD-04 (Proposed,
                           Scope portfolio) and writes PB-02's .env and PB-01's out/, which git never holds
    dt_helpers.py          run dt in-process; throwaway fixture copies (optionally under git)
    test_<area>.py         unittest, stdlib only
```

Commands never glob or open docs themselves; they ask `Repo` (doc map, IDs) and `model` (typed views). A parsing fix goes in `md`/`repo`/`model` so every command sees it.

## Doc format (what the parser reads)

- **Doc kinds** come from the path (`repo.KINDS`): brief, idea, roadmap, spec, architecture, package-architecture (`docs/packages/<pkg>/architecture.md`, legacy `docs/architecture/<pkg>.md`), contract, pipelines, tests, references (`docs/references.md`), probes (`docs/probes.md`), routes (`docs/routes.md`), requests (`docs/requests.md`), constraints, agents, plan, todo, queued-plan, archived-plan. `tasks/archive/**` is read only for `next-id` and as a `section` fallback.
- **Header:** first non-blank line after the H1, `**Key:** value` pairs joined by ` · `. Unknown keys are kept.
- **ID sections:** `## <ID>: <Title>` or `### <ID>: <Title>`, outside code fences. A section runs to the next heading of the same or higher level. ID forms: `PL-NN`, `TC-NN`, `AD-NN`, `CR-NN`, `S<n>`, `M<n>`, `M<n>-T<nn>`, `M<n>-R<nn>`, `<pkg>.<symbol>` (any `PREFIX-NN` works as a heading ID).
- **Spec requirements:** bold-led lines `- **CODE-NN** …` plus their indented sub-bullets. Struck (`~~`) on the line = removed.
- **CONSTRAINTS rules:** bold-led `- **CR-NN** …` lines and table rows whose first cell is `CR-NN`.
- **Retired:** `- ~~<ID>: <title>~~ Retired YYYY-MM-DD: <reason>`. A decision heading with a struck title (`### AD-02: ~~Old~~`) is superseded and counts as retired.
- **Tasks** (`### M<n>-T<nn>: <Title>` in a plan): bold fields `Package`, `Step`, `Kind`, `Covers`, `Size`, `Mode`, `Skills`, `Read`, `Verify`, `Depends on`, `Writes`, `Blocked`, `Reason`, and an `**Acceptance:**` checkbox list. `**Kind:**` is `interface | spine | wiring | thicken | system`. `**Writes:**` is the task's exclusive claim: exact paths, or one directory glob (`dir/**`, `dir/*`, `dir/`). A task from before these fields has no Kind and falls back to `**Files likely:**` for its writes; `**Parallel:** G<n>` still parses (both give a `deprecated` warning).
- **Interface-first plan:** one with a `## Dependency graph` section or a task with `Kind:`/`Writes:`. The section holds one table, `| From | To | Kind | Mitigated by |`: From depends on To (the direction of `Depends on`), each cell's first `M<n>-T<nn>` is the task. Kind is `data | call | file | code | contract-change | order`. Mitigated by names the interface that removes the wait (`stats.Cov sample (M1-T01)`: a contract symbol ID an interface task freezes), or `none: <reason>`. A mitigated edge is documentation and never orders; an unmitigated one is also in `Depends on`. A dependency on an interface task needs no row.
- **Contract types:** a contract section titled `type` (`### <component>.<Type>: type`), or one with a `**Kind:** type` field. Its sample is its `**Sample:**` path, else the `**Fixtures:**` folder on its `- **Boundary:** … · **Fixtures:** tests/contracts/<component>.<Type>/ · **Cases:** …` line. A step table's `In → Out` cell names types by CamelCase name or `pkg.Name`; single capitals (`T`) and all-caps words aren't types.
- **Findings:** list items `- M<n>-R<nn> <Severity> · <rule> · <text> → <disposition>` under a checkpoint's `**Findings:**`.
- **Routes** (`docs/routes.md`, written only by `dt route`): checkbox items `- [ ] <owner skill> · <change> (from <skill>, YYYY-MM-DD)`; ticked when the owner's Revise is approved.
- **Requests** (`docs/requests.md`, design/requests.md §3, written by `dt request`): `- **UR-NN** <owner> · "<the user's words>" [<context>] · <skill> YYYY-MM-DD → <trace>`. Owner is `brief`, `spec`, `architecture`, `pipelines`, `tests`, `plan` or `constraints`; `[<context>]` and `→ <trace>` are optional. The trace is the IDs or sections that honour it (`TANK-02, §Out of scope`: a section is `§` plus a heading's text, case ignored), `changed: <what instead> (approved "<the user's words>", <skill> YYYY-MM-DD)` or `superseded by UR-NN`. A request is **open** unless it is changed, superseded, or its trace names a live ID defined in, or a heading of, its owner's docs (brief: brief.md and ideas; spec: spec.md; architecture: architecture docs and contracts; pipelines, tests, plan, constraints: theirs). Each line defines its UR ID; the header needs no Status.
- **Ranges:** `STAT-01–STAT-04` and `STAT-01–04` expand to every ID in between.
- **Pre-build sections:** any heading containing `(pre-build`.
- **Reference entries** (`docs/references.md`, design/references.md §4): `### RF-NN: <Title>`, then `**File:** \`references/…\` · **Hash:** <8 hex> · **Kind:** code|doc · **Milestones:** S2, M4 | all | —` and bullet fields `- **Purpose:**`, `**Key parts:**`, `**In → Out:**`, `**Use for:**`, `**Caveats:**`. Retired entries are retired lines. "References for M<n>" are derived: entries whose `Milestones` names it (`all` serves every milestone; `—` none), plus the milestone section's `**References:**` line, or, with no such line, the entries assigned to its stage. There is no other list. A `Read:` item `RF-NN:<selector>` names the entry `RF-NN`.
- **Probe entries** (`docs/probes.md`, design/probes.md §4.2): `### PB-NN: <Title>`, then `**Folder:** \`probes/PB-NN-<slug>/\` · **Hash:** <8 hex> · **Status:** … · **Milestones:** S1 | M2 | all | — · **Last run:** —|<date>|<ISO time>` and bullet fields `- **Question:**`, `**Informs:**` (decisions, requirements with ranges, contract symbols), `**Spends:**`, `**Checks:**`, `**Verdict:**`, `**Caveats:**` (`**Docs read (<date>):**` is kept as text). Status is `Draft`, `Ready`, `Answered · pass|fail · <date>` or `Waived · <date> — <reason>`. The checks table under the entry is `| Check | What | How | Pass | Runner | Result |`; each row `C<n>` is the section `PB-NN.C<n>`; Runner starts with `agent` or `user` (`user (manual)`, `user (sandbox key)`). Retired probes are retired lines. The index's header needs no Status. A PB entry is routed like an RF entry (Milestones, `Read: PB-NN[:selector]`). A decision's `**Probe:** PB-NN — <question>` or `**Probe:** none — <why the docs settle it>` (bullet or plain line, architecture docs) cites it; `dt next-id PB` counts cited IDs too.
- **Probe folders** (`probes/PB-NN-<slug>/`): code files are every file except `evidence/`, `out/`, dot-files and dot-folders (`.env`, `.env.example`), caches and `*.md`. **Hash** = the first 8 hex of sha256 over, for each code file in sorted relative-path order, `path + NUL + bytes + NUL`; probe_kit writes the same value as results.json's `script_hash`. `evidence/results.json` (§4.3) needs `probe` (the entry's ID), `script_hash` (8 hex), `run_at` (ISO 8601), `runner` (agent|user) and `checks`: each key a `C<n>` of the entry's table, holding `pass` (true, false or null) and `observed`, and an optional string `note`; other keys are kept. Samples are `evidence/samples/*`.
- **Roadmap** (`docs/roadmap.md`): a stage table (first column `Stage`: `S<n>`, Name, Source, Status*) written by idea-refine, and a milestone table (first column `Milestone`: `M<n>`, Stage, Name, Packages, Pipelines, Depends, Status*) written by build-planning when it cuts a stage into milestones. A Depends cell's milestones are the `M<n>` outside parentheses: `M4 (after M4, before M5)` depends on M4 only. `## S<n>: <Name>` sections carry `**Outline:**` and `**Skills:** a, b` (idea-refine); `## M<n>: <Name>` sections carry `**Outline:**`, `**Exit:**`, `**Plan:**`, `**Outcome:**` and optionally `**Skills:**` and `**References:**` (build-planning narrows a stage's skills and references per milestone). A milestone with no `**Skills:**` line takes its stage's; its Source is its stage's. A roadmap from before stages has only the milestone table, with a `Source` column and no `Stage` column: each such milestone stands for its own stage and is read as before.

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

`--json` prints one object with the same keys (`next_ids` for `next ids`); lists stay lists, maps stay objects, `blocked` is `null` when not blocked. `drift` is a list, or the string `"unknown"` until `dt layout`'s drift check is available; build-setup's generated-config checks are `"unknown"` when their input file is absent. `dependents` is `{pkg: [dependents]}`. Structured extras in JSON only: `ideas` and `packages` are objects, `roadmap_rows` is a list of `{id, name, source, status}`, `prefixes` is `{PREFIX: {highest, next}}`, and architecture-design adds arch-status.py's `spec` (`path`, `status`, `live_requirements`) and `architecture` (`path`, `exists`, `status`, `shape`, `last_updated`) objects.

| `--skill` | Modes | Extra keys |
|---|---|---|
| `idea-refine` | new · extend | `brief_words`, `brief_goals` (count), `ideas` (path=status), `roadmap_rows` (`S<n> name [source]`: the stages; on a roadmap from before stages, its milestone rows), `references_unassigned` (RF entries with `Milestones: —`) |
| `spec-writing` | blocked · new · extend | `ideas_ready` (Accepted ideas), `prefixes` (`highest→next` per prefix), `reserved_prefixes` (planning prefixes a requirement must not use: AD, CR, EX, PB, PL, RF, TC, UR), `skills` |
| `architecture-design` | blocked · new · revise · extend · current | everything the old `arch-status.py` reported (`uncovered`, `changed_since`, `spec_rows_pending`, `stale`, `next_decision`, `package_docs`, `packages_found`, `skills`, `broken_fences`), plus `contracts_missing` (packages with no `contract.md`; `(no package id yet)` when no id can be found or inferred), `legacy_layout` (`docs/architecture/<pkg>.md` files to move), `grow_triggers` (a package over 3 pipelines, 12 modules or 2,000 doc lines; none while `grow_held` is set), `grow_held` (in a single-package architecture, what records the user's one package: a request in force whose words keep it, `UR-34 "Keep it as one package, no split."`, or an Accepted decision whose text declines the split, `stays one package`, `no split`; a decision only naming the shape doesn't count), `stale_contracts`, `probes_answered` (`PB-01 pass (AD-04)`, `PB-01 waived (AD-04)`: Answered or Waived probes whose decisions are still Proposed), `probes_failed` (`PB-01 (AD-04)`: Answered fail with a decision still Proposed; must be empty at its gate) |
| `pipeline-design` | blocked · new · grow · revise · extend · sync · current (per package) | `packages` (pkg=mode), `uncovered_ids` (spec IDs on no pipeline step or Covers, any package's or system: those a component in scope covers, and those an uncut, specced stage's Source adds), `stage_ids_unplaced` (`QR-04 (S1, S2; AD-03, AD-04 → qdata)`: the second kind, with the stages they keep below Designed and the live decisions citing them, whose packages go to `extend`: the ID goes on the Covers of the step that applies the decision), `components_unowned` (components that own no step: an Owner naming it on its own package's or a system pipeline, or `pkg.comp` on another package's), `drift` (entry calls ≠ step table, from `dt layout`), `retired_refs` (`path:line ID`), `misplaced` (pipelines whose Entry lies in another package's source folder) |
| `test-planning` | blocked · new · revise · extend · current (per package) | `packages` (pkg=mode), `pipelines_no_smoke`, `pipelines_no_golden`, `cases_no_source`, `cases_no_tolerance`, `fixtures_missing` (folder or `expected.json`), `fixtures_orphan` (`tests/fixtures/*/TC-NN/` no live case uses), `skills` |
| `build-planning` | blocked · new · extend · replan · advance · foreign · current | `milestone` (active M and status), `progress` (done/total), `next_task`, `blocked_tasks`, `uncovered` (milestone spec IDs on no task and not Deferred), `no_spine` (milestone pipelines with no task that builds them: a wiring task, a `Kind: system` task for each system pipeline its Step, Read or Reason names, or with no Kind a Phase 0 task; archive included), `steps_unplanned` (`PL-07.daily_bars`: a step of the milestone's pipelines that no task's Step names and the Scope's Deferred doesn't name; a spine task on the whole pipeline builds every step, and a step needs none when its Spine version reuses one, `as PL-05` or `PL-01 as built`, or a task of any plan, archive included, names its name on another pipeline), `mode_violations`, `boundaries_unfrozen` (`pkg.symbol (consumers)`: a contract symbol whose `**Boundary:**` line names a milestone package (in a single-package architecture, also any of its components), with no `**Fixtures:**` folder yet and in no contract task's `Read:`; the contract task is the interface task, or with no Kind the Phase 0 `**Step:** contract` task; and in an interface-first plan `pkg.Type (PL-NN.step)`: a contract type a step of the milestone's pipelines (its roadmap row's, and every task's Step pipeline) names in `In → Out`, in no contract task's `Read:` or `tests/contracts/<pkg.Type>/` Writes, with no fixtures folder yet), `draft_pipelines`, `changed_since_plan` (milestone docs Approved after the plan's Last updated), `probes_blocking` (`PB-01 → service, ledger.BankTxn (M1)`: probes the milestone to plan meets, below), `interfaces_changed` (`stats.Cov (M1-T04, M1-T05)`: a symbol the plan's interface task froze whose contract section, `**Used by:**` lines aside, differs from its text at the plan's last commit, with the tasks that read it or whose steps' `In → Out` cells name it; outside git, or with the plan uncommitted, every frozen symbol of a contract.md in `changed_since_plan`), `stage_to_cut` (`S<n> name`: the first stage with no milestone rows that is Designed, whatever earlier milestones still wait for their plans; or `none`), `pipelines_inferred` (that stage's pipelines, inferred from its Source, for build-planning to divide among the milestones it cuts; or a milestone's when its Pipelines cell is empty), `milestone_references` and `milestone_skills` (the references and skills serving that same stage or milestone; references include PB entries whose Milestones name it), `references_unrouted` (`RF-NN (M<n>)`, `PB-NN (M<n>)`: for the active and each queued plan, a milestone reference in no task's `Read:`, selector ignored), `skills_unrouted` (`skill (M<n>)`: a milestone skill on no task's `**Skills:**`), `stage_unrouted` (`skill (S<n>)`, `RF-NN (S<n>)`: for each cut stage, a stage skill or reference that none of its milestones carries), `skills_missing` (referenced by the plan, its tasks or the milestone's `**Skills:**`, not installed), `skills_available`, `grow_triggers` and `grow_held` (as architecture-design's), `drift` (milestone pipelines), `stale_contracts`, `queued`, `base` |
| `api-probe` | new · revise · record · waiting · current | `index` (probes.md status, `ok` with none, or `missing`), `probes_unwritten` (`PB-01 (AD-04)`: cited by a `**Probe:**` line, no entry), `probes_open` (`PB-01 (user: C1, C3–C9)`: Ready, with the checks that have no Result and no record in results.json, by runner), `probes_results` (`PB-01 (<run_at>)`: a non-Draft entry whose results.json `run_at` is newer than its Last run, or `(results.json invalid: …)`), `probes_stale` (`PB-01 (results <hash>, code <hash>)`: results.json's `script_hash` isn't the code's hash), `evidence_leaks` (`dt probes --scan` hits, `path:line (pattern)`), `next_id` (next PB) |
| `reference-intake` | new · extend · current | `index` (references.md status or `missing`), `files_to_read` (unindexed and changed files), `outline_first` (`.py` files to read over 400 lines: give the subagent `dt outline` plus the first lines), `next_id` (next RF), `milestones` (`S<n> name` and `M<n> name`, to assign files to; assign to a stage unless a milestone is already cut for it) |
| `build-setup` | blocked · new · extend · ratchet · current | `constraints` (status), `config_mismatches`, `contract_mismatches`, `optional_layers_existing`, `deptry_missing`, `protected_gaps`, `ignores_without_exception`, `agents_missing`, `hooks_missing` (hook and check scripts, plus any `scripts/…` an agent file names), `not_executable`, `expired_exceptions`, `tools_missing` (uv, jq), `dependents` (`pkg<-a,b`), `base` |

`routed_changes` (spec-writing, architecture-design, pipeline-design, test-planning): the skill's open items in `docs/routes.md`, `<change> (from <skill>)`.

`requests_open` (idea-refine, spec-writing, architecture-design, pipeline-design, test-planning, build-planning, build-setup): the open requests the skill's doc owns, `UR-NN "<words>" [<context>]`.

`skills` and `skills_available` list installed skills by name: the project's `.claude/skills/*/SKILL.md` plus `$CLAUDE_PLUGIN_ROOT/skills/*` when that is set, minus dev-team's own planning skills (reference-intake and api-probe included).

`--summary` (SessionStart hook) prints at most 8 lines: active milestone and plan status, progress and next task, blocked tasks, queued plans, docs waiting for approval (Draft), a stale roadmap, `references: N waiting → reference-intake` when any reference file is unindexed, changed or missing, `probes: N waiting → api-probe` when results aren't recorded yet (`probes_results`) or a cited PB has no entry (`probes_unwritten`), `requests: N not honoured → <skills>` when an Approved spec or architecture has open requests, and `dt: <resolved path to scripts/dt>` (`dt: python3 <…/dt.py>` when the shim isn't executable). It prints nothing in a project with none of `docs/brief.md`, `docs/spec.md`, `docs/roadmap.md`, `tasks/plan.md`, never fails (an internal error prints one `dt status: error: …` line) and always exits 0.

Mode rules:
- **blocked** — idea-refine never; spec-writing: no brief; architecture-design: no spec (as arch-status.py; a Draft spec shows in `docs`); pipeline-design: architecture missing or not Approved; test-planning: no package has an Approved pipelines.md (a package whose pipelines.md isn't Approved is `pkg=blocked`); build-planning: the next milestone to plan has pipelines not all Approved, the next stage has spec IDs on no Approved pipeline, a Revise is open on the active milestone's docs, or (all-at-once) a brief stage is below Designed (below); build-setup: no active plan, or the plan is Draft.
- **architecture-design** — `new`: no architecture.md; `revise`: `probes_answered` or `routed_changes` is non-empty, or the Approved architecture has open requests (a probe's results, a change routed here or the user's words go in first); `extend`: `uncovered`, `changed_since`, `contracts_missing` or `legacy_layout` non-empty (the last two migrate projects designed before contract.md and `docs/packages/`); else `current`.
- **pipeline-design** (per package; the overall mode is the first of new, grow, revise, extend, sync present) — `new`: no pipelines.md; `grow`: `misplaced` lists one of its pipelines; `revise`: pipelines.md is Draft but Approved at git `HEAD` (or, overall, `routed_changes` is non-empty); `sync`: drift; `extend`: uncovered IDs or unowned components (overall, also any `stage_ids_unplaced`); else `current`.
- **test-planning** (per package) — `new`: no tests.md; `revise`: tests.md Draft but Approved at `HEAD` (or, overall, `routed_changes` is non-empty); `extend`: a pipeline with no smoke command or no golden case; else `current`. A pipeline with `**Part of:** PL-NN` (a package's part of a system pipeline) needs no smoke or golden case of its own.
- **build-planning** — first rule that holds: `foreign`: `tasks/plan.md` exists without a dev-team header (no `**Milestone:**`) and has unchecked tasks; never overwrite, ask. With an active plan: `advance` when every todo item is checked and the exit checkpoint is ticked (a finished milestone advances even while a Revise is open: that belongs to the next plan); `blocked` (`waiting for <doc> approval (Revise in progress)`) when a pipelines.md or tests.md of the milestone's packages is Draft, or a doc defining one of its pipelines (`draft_pipelines`) is; `replan` when no todo item is checked and `interfaces_changed` or `changed_since_plan` is non-empty (an unbuilt plan the docs moved under is replanned before any cut); `extend` whenever `stage_to_cut` is set (the stage is cut first, rows only, even while a task is `Blocked`, a building milestone needs a replan or the next milestone waits for its plan); `replan` when a task is `Blocked`, `interfaces_changed` is non-empty, or `changed_since_plan` is: the packages' pipelines.md, tests.md or contract.md is Approved with a `Last updated` date later than the plan's (same-day changes aren't seen; a Replan bumps the plan's date); `extend` when the next milestone is Designed (one to queue); else `current`. A `new` or `extend` whose unit is a milestone becomes `blocked` (`waiting for PB-01`) while `probes_blocking` is non-empty; cutting a stage is unaffected. The milestone's packages are its roadmap Packages, its pipelines' packages and its tasks' Package. With no active plan (missing or between milestones): when no plan was ever written and every stage's Source is `brief` (all-at-once), `blocked` while any uncut stage is below Designed (`S2, S3 below Designed: …; S2, S3: QR-04 on no Approved pipeline; no pipelines.md for eval, ml; run pipeline-design`, naming each stage's gap (pipelines not Approved, else the IDs on no Approved pipeline) and the packages with no pipelines.md); `new` (no plan ever written, the first unit Designed) or `extend` when `stage_to_cut` is set; `extend` if a queued plan exists; otherwise for the next unit (`roadmap.next_unit`: in roadmap order, pre-stage milestones first, then each stage's milestones, or the stage itself while it has none; the first not yet Planned/Building/Done, or for a stage, not yet Split): `new` (no plan ever written) or `extend` for a Designed milestone, else `blocked` (`M2 pipelines not all Approved (…)`, or `S2 spec IDs on no Approved pipeline (PORT-03)`). No roadmap: `new` once any pipelines.md is Approved.
- **Milestone pipelines** (build-planning and `dt roadmap`) — the milestone row's Pipelines cell; a stage, or a milestone whose cell names none, has them inferred from its Source (a milestone's is its stage's): the spec Changelog rows citing its idea files (`brief` → rows citing brief.md) give the milestone's IDs (minus those marked removed), and its pipelines are the live package and system pipelines whose Covers include any of them (step Covers only for a pipeline with no Covers line, since a reused step cites an earlier milestone's IDs). `pipelines_inferred` prints the inferred set for the unit the mode acts on (the stage to cut, the milestone to queue or plan, else the active one), empty when a milestone's cell is filled; an explicit cell always wins.
- **Probes blocking a milestone** (design/probes.md §3.3) — a probe that is open (Draft, Ready), Answered fail with a decision still Proposed, or cited by a decision's `**Probe:**` line with no entry yet, meets the milestone when one of its decisions (its Informs' ADs and the decisions citing it) has a `**Scope:**` naming the milestone's packages, its pipelines' packages or their step Owners (`system` meets every milestone), or its Informs names a contract type of one of those, or a type the milestone's steps pass. Answered pass and Waived probes never block.
- **api-probe** — the first that holds: `new` (`probes_unwritten`), `revise` (`probes_stale`), `record` (`probes_results`), `waiting` (`probes_open`), else `current`. Never blocked.
- **build-planning task modes** — expected `solo` for interface, spine, wiring and system tasks (a task with no Kind: Phase 0 tasks); `split` for any other task with Covers or a `TC-NN` in Read; `solo` otherwise. A `**Reason:**` line on the task overrides.
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

### `dt next [--skip test-planning] [--json]`

The next skill run, its mode and why, for `/dev-team:plan` and the eval driver. It reads the `dt status --skill` reports and takes the first that holds:

1. **A Draft waits at its owner's gate** — any doc with Status `Draft` or `Proposed`; the owner by doc kind (brief and ideas: idea-refine, … constraints: build-setup, plan and queued plans: build-planning), earliest in planning order. Mode `gate`; the user answers or approves.
2. **References waiting** (once the roadmap exists) → reference-intake; **probes waiting** (`probes_unwritten`, `probes_results`) → api-probe.
3. **A routed change** (`dt route`) → its owner, owners in planning order; the owner's report gives the mode (`revise`, spec-writing's `extend`).
4. **A user request an Approved spec or architecture doesn't honour** (open, `request-open`) → spec-writing (`extend`), then architecture-design (`revise`).
5. **The first planning skill with work**, in order idea-refine, spec-writing, architecture-design, pipeline-design, test-planning, build-planning, build-setup. A skill reporting `blocked` or `current` has none, and also: idea-refine unless `new` or the roadmap is missing; spec-writing unless `new` or `ideas_ready`; pipeline-design's `extend` without `uncovered_ids` (an unowned component is a gap its gate may accept); test-planning beyond its scope, the packages of the active milestone and of the next unit build-planning plans (`roadmap.next_unit`): the unit's Packages, its pipelines' packages (a stage from the brief: the pipelines covering a requirement of a feature whose `**Stage:**` line names it, `roadmap.staged_pipelines`, since every brief stage infers every pipeline) and those of package pipelines Part of its system pipelines, plus any package in `revise` (with no unit to scope by, every package; the reason names the units, `for M1, M2`); test-planning's `extend` unless an in-scope pipeline has neither smoke nor golden case, and test-planning at all once a plan exists with no tests.md anywhere (the user skipped it) or with `--skip`; build-planning's `extend` with an active milestone and no `stage_to_cut` (a queued plan is the user's request). A blocked build-planning sends the run to api-probe (`probes_blocking`: mode `waiting`, the user runs the checks) or to pipeline-design when its reason says `run pipeline-design` (all-at-once: a stage below Designed), else stops there.
6. Otherwise `done`: nothing left to plan.

```
next: pipeline-design (new)
packages: web
reason: pipelines to design: web (new)
waiting on user: no
run: /dev-team:pipeline-design
```

`--json` prints `{skill, mode, reason, waiting_on_user}`, plus `packages` for pipeline-design and test-planning; `skill` is `null` when done. `waiting_on_user` is true for `gate`, `done`, a blocked build-planning and api-probe `waiting`. Always exits 0.

### `dt route [<owner> <change> [--from <skill>]] [--done <owner>] [--json]`

Records a change another skill owns, found at a gate, for the owner's Revise: appends `- [ ] <owner> · <change> (from <skill>, <date>)` to `docs/routes.md` (created on first use). Owners: spec-writing, architecture-design, pipeline-design, test-planning. `--done <owner>` ticks every open item routed to it, when the user approves its Revise. With no arguments, lists the open items (`--json`: `[{skill, change, from, date}]`).

### `dt request …`

Records and traces the user's words in `docs/requests.md` (design/requests.md); the only writer of its lines.
- `dt request add <owner> "<words>" --skill S [--about "<context>"] [--replaces UR-NN]` — appends the next UR with today's date (creating the doc on first use, titled from the brief) and prints its ID. `--about` says what the words answer when they don't say it themselves ("Go with A" → `--about "price source: A = Sharadar"`). `--replaces` marks the earlier request `superseded by` the new one.
- `dt request trace UR-NN <ID|§heading>…` — adds IDs or sections that honour it; each must be defined (a section: a heading of the owner's docs) and at least one live in the owner's docs (else exit 2, nothing written). IDs traced earlier that are gone or retired drop out. Refused on a changed or superseded request.
- `dt request change UR-NN "<what instead>" --approved "<the user's words>" --skill S --into ID…` — records a change the user approved, with that approval and the IDs it was written into: each defined and live, at least one in the owner's docs, and every ID that honoured the old words among them (else exit 2, nothing written).
- `dt request change UR-NN --into ID…` — adds IDs to a recorded change; the approval stays.
- `dt request [list] [--open] [--owner O] [--json]` — each request with its owner and trace (`· open` when nothing honours it); `--json`: `[{id, owner, words, about, skill, date, state, trace}]`, state `open | traced | changed | superseded`.

Every write rewrites the header's `Last updated` and leaves every other line as it was.

### `dt next-id <prefix>…`

`PL`, `TC`, `AD`, `CR`, `RF`, `UR`, any spec prefix, `S` (stages), `M`, `M2-T`, `M2-R`. Counts retired IDs and the archive. Prints one ID per prefix.

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
4. `## Interfaces (frozen: …)` — the contract sections the packet needs that `Read:` doesn't already show (`devteam/packet.py`): the contract types the task's steps' `In → Out` cells name, the contract symbols named after a step (its signature), then every section a shown symbol's signature names, followed until nothing new is named. A type is followed by `Sample: <path> (exists|not written yet)`; a pulled section's `<!-- path:line · named by <symbol> -->` says which symbol named it. A `PL-NN` Step (wiring, system) covers every step of the pipeline. Omitted when empty.
   - **Signature:** a section's fenced code, the inline code on its non-bullet lines, and its `**Errors:**` bullet's inline code; `#` comments and string literals dropped. Its CamelCase names (`pkg.Name` kept whole) resolve to a type or CamelCase class section of that name (its own component first, then its package, then any), else to the section whose code defines it inline (`class X`, `X = …`, `NewType("X")`, `X(field: …)`). Python's own names (builtins, `typing`, `collections`, `pathlib`, `datetime`…), common third-party ones (`DataFrame`, `BaseModel`, `FastAPI`…) and qualified names whose first part isn't a component (`pd.DataFrame`) are library names.
5. `## Writes (edit only these files; …)` — the task's `Writes:`, each `(exists)`, `(folder)`, `(from M1-T03)` when an upstream task (`Depends on`, directly or not) names that exact path in its own Writes (an upstream folder claim doesn't count), else `(new)`; the edit boundary. A task with no `Writes:` gets `## Files likely` instead, marked `(exists)` or `(new)`.
6. The task section itself, last.

The task is looked up in `tasks/plan.md` and `tasks/queued/`. Warns on stderr (exit stays 0) when the packet is over 2,000 lines. Exit 1, nothing on stdout, if the task or any `Read:` ID is missing or retired. `--json`: `task`, `package`, `mode`, `kind`, `lines`, `read` (each `ref`, `kind` id|file|reference; a reference adds `where`, `file`, `selector`, `shown` whole|part|outline|missing), `interfaces` (each `id`, `where`, `type`, `sample`, `named_by`: the symbol that named it, or null), `writes` (each `path`, `exists`, `folder`, `from`: the upstream task IDs; empty without a `Writes:` field), `files_likely`, `text` (the packet). The preamble adds `· kind <kind>` when the task has one.

### `dt ready [--json]`

Every task of the active plan that can start now, so an orchestrator fans out in one turn (design §6.4). A task is ready when it isn't ticked in `todo.md` and every `Depends on` inside the plan is (`graph.ready`). A split task whose own dependencies aren't all done but whose interface tasks upstream are (`graph.tester_ready`) is listed as its tester half: the tester writes against the frozen interface. Plan order. Text: `<id> [<kind>, tester half] <title> · writes: …`, or `ready: none`. `--json`: a list of `{"id", "title", "kind", "writes", "part"}`, `part` being `task` or `tester`. No active plan: message on stderr, exit 1.

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

### `dt explain [PL-NN|<pkg>…] [--write]`

The pipelines in plain words, for a person reading the plan: per pipeline, its **Purpose** line (or, without one, the requirements it serves), how it runs (trigger; the system pipeline it is a segment of), then each step in order with what it does (its Spine version), what it takes and gives, and the requirements it serves, quoted from the spec. Library classes are listed under the factory step that builds them; a system pipeline shows its hops between packages and names its segments. Prints the chosen pipelines (default all); `--write` writes one page per package to `docs/explained/<pkg>.md` (`system.md` for system pipelines), outside the doc map. `explain-stale` warns when a written page no longer matches.

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
- **Pipelines** (the package's `pipelines.md`): the entry function's top-level calls (outermost calls per statement, in order; calls used as arguments don't count), read with `ast` only — project code is never imported or run — compared with the step table's function step names (a library-class row, whose Step is CamelCase like `SingleCropSet`, is reached through its factory and skipped). A call is named by its final attribute (`data.load_prices(…)` → `load_prices`) and `from … import x as y` aliases are resolved. Lines: `PL-NN: ok`, `PL-NN: drift — calls […] vs steps […]` (also when the entry function is undefined or the file doesn't parse), `PL-NN: not built (<entry file> missing)`.
- Exit 1 on drift. `--json`: `package`, `root`, `exists`, `tree` (`path`, `dir`, `doc`), `pipelines` (`id`, `entry`, `status` ok|drift|missing|no-entry, `calls`, `steps`, `detail`).
- `devteam/code.py` exposes `pipeline_drift(repo, pipeline)` (the drift detail, or None) and `check_pipeline` for `dt status` and lint.

### `dt lint [paths…] [--changed] [--json] [--hook]`

No paths → the whole doc map (archive excluded). Paths (files or folders; a folder means every doc under it; relative to `--root`, else the current directory) → only problems located in those files; cross-doc checks still read the whole repo. `--changed` → docs changed vs `HEAD` plus untracked ones (outside git: exit 2). Output: `path:line: <code> <message>` sorted by path and line, then `N errors, M warnings`. `--json`: `problems` (`path`, `line`, `code`, `severity` E|W, `message`), `errors`, `warnings`. Exit 1 if any error; warnings don't fail. A malformed doc yields findings, never a traceback.

Checks (code: severity):
- `dup-id` E — an ID with two live definitions, or one with a retired line that is still defined elsewhere
- `missing-ref` E — an ID (`PB-NN` included) in a `Read:`, `Covers`, `Step`, `Pipeline`, `Used by`, `Part of` or `References` field, or a `Covers`, `Pipeline(s)`, `Used by` or `Read` table column, that isn't defined anywhere (archive counts as defined). `Read:` entries that look like paths (`/` or a file extension) are skipped; `PL-02.step` checks `PL-02`; `RF-01:pca_factors` checks `RF-01`, `PB-01:probe.py:get` checks `PB-01`. A decision's `**Probe:**` line isn't checked here (a cited PB with no entry is `probes_unwritten`). Ranges expand. Changelog sections are skipped. (`Depends on` is checked by `depends`.)
- `retired-ref` E — a literal mention of a retired ID (retired line, struck decision heading, struck requirement) anywhere outside code fences, except: retired lines and superseded/removed definitions themselves, the decision named in `Superseded by AD-NN`, and Changelog sections. An ID only reached through the inside of a range (`STAT-01–STAT-06`) isn't flagged
- `budget` W — size budgets (§3), in lines. Package docs are budgeted per unit: contract.md > 8 per live symbol (`### comp.symbol`) + 12; pipelines.md > 35 per live pipeline (or 20 + 1.5 per step row, rounded up, when that is more) + 10, plus the lines of its `## … (pre-build …)` layout section; tests.md > 10 per live TC + 15. Fixed: plan.md and queued plans > 400, a probes.md entry > 10 non-blank lines plus its checks table (header, separator, one per check), a roadmap `## S<n>` or `## M<n>` section > 6 non-blank lines, AGENTS.md/CLAUDE.md `## Docs` + `## Project skills` > 25. docs/brief.md: over 500 words (the `brief_words` count) or more than 5 goals (`brief_goals`)
- `grow-size` W — a package doc over a per-file ceiling (contract.md 200, pipelines.md 300, tests.md 300 lines), however well it keeps to its per-unit budget: the package holds too much for one set of docs, and architecture-design should consider a Grow; not while `grow_held` (above) records the user's one package
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
  - `writes` — two tasks with no `Depends on` path between them (either way) whose writes overlap (same path, or one inside the other's folder glob), across the whole plan: E, or W when either side claims only through `Files likely`. Two wiring tasks whose writes overlap, path or not: same severities. And E (tasks with a Kind): a task other than the interface task writing a shared module (`__init__.py`, `types.py`, `__main__.py`, or a `pipeline.py` that isn't exactly one pipeline's Entry file: a re-exporting one, or one several pipelines enter through); a task other than an interface, wiring or system task writing a pipeline's Entry file
  - `edges` E (interface-first plans) — a `Depends on` whose graph row is mitigated (mitigated edges don't order); a `Depends on` with no graph row (or no `## Dependency graph` section), except on an interface task; a row whose From or To names no task or an undefined one; a Kind outside the six; `none` with no reason; a mitigation that names no `pkg.Symbol`, or one no interface task freezes (in its `Read:`, or a `tests/contracts/<pkg.Symbol>/` path in its `Writes:`); an unmitigated `data` row across a type an interface task freezes (To's step Out ∩ From's step In), or `call` row across a frozen symbol (`<owner>.<step>` of From's steps that To reads or builds): mitigate it instead of waiting on code
  - `kind-title` E — a task title with the word "spine" or "thicken" whose Kind is another (a fold is Kind thicken, never titled a spine)
  - `covers-vs-deferred` — the Scope's Covers and Deferred both list an ID, or a task covers an ID the Scope defers: **E**. A task covers an ID that another step's Covers cell lists and its own step's (`PL-NN.<name>`) doesn't: W. That Covers and Deferred account for every ID is `uncovered` (`dt status`)
  - `step-unplanned` W — `steps_unplanned` (build-planning above), one warning per pipeline at the Scope's Deferred line: every spec ID can be on a task while a step is left out, so each step gets a task or a `PL-NN.step (to M<n>: why)` under Deferred
  - `interface-barrier` W — an interface task followed straight, in plan order, by a non-interface task with no checkpoint heading between them: add `### Checkpoint after M<n>-T<nn> (barrier)`. The build reviews the interface anyway; the block's items guide that review
  - `parallel-step` W — two thicken tasks on one step (`PL-NN.<name>`) with no `Depends on` path between them: the step is one function, so each needs the file the other changes even when their Writes don't overlap
  - `spine-claim` W — a spine task's Reason names (backticked, bare or `<component>.<name>`) a contract function or class that is no pipeline's step or entry and sits outside the step's owner, while the task writes a source file outside that owner's folder or module (owner `train.loop` → `…/train/loop/…`, `…/train/loop.py`): give the symbol its own step, or its home in the step's folder owner. A symbol beside the step's own module raises nothing
  - `deprecated` W — a task's `**Parallel:**` (derived now) or `**Files likely:**` (use `**Writes:**`)
  - `verify-smoke` E — a task whose `Verify:` lacks its Step pipeline's smoke command (tests.md Strategy `Smoke` cell, else the pipeline's Trigger + ` --smoke`) when one is due: always for wiring and system tasks, and for any other task once its `Depends on` path reaches that pipeline's wiring task (with no Kind: every task outside Phase 0). Interface and spine tasks, and thicken tasks beside the wiring, land before the pipeline runs
  - `finding-disposition` E — a finding under a checkpoint with no `→ <disposition>`
  - `task-ref` E — a task ID in a task's Acceptance text, or in a graph row's Mitigated by cell (mitigation or `none:` reason), that names no task in any plan or the archive; a bare `T41` reads as the plan's own milestone's (`M1-T41`)
- `todo-mismatch` E — task IDs in todo.md ≠ plan.md (each side reported in its own file)
- `step-io-types` — in a package pipeline's step table, a type an `In → Out` cell names that no contract type section defines (bare name or `pkg.Name`), or a step whose Out names no contract type (entry arguments on the In side may stay plain). E once any contract has a type section, W before (projects from before typed contracts)
- `packet-type-closure` W — a name contract signatures use (as `dt context` reads a signature) that no contract section defines and that isn't a library name, once per contract doc at its first use, naming the symbols that use it: no packet can show it. A name defined only outside every section (a preamble alias such as `` `Array = np.ndarray` is used throughout ``) is reported too, since no packet shows the preamble
- `type-cases` — a contract type that crosses step owners (steps of two or more owners name it in `In → Out`, reused `PL-NN as built` steps aside, or its `**Boundary:**` line names a consumer) with no `**Cases:**` (or `—`): the interface task writes one sample per case. E once any contract type names a case, W before
- `boundaries` E — a contract function (not a type) with no `**Boundary:**` line whose `Used by` names a package or component other than its own, or a pipeline that isn't its own (its own: the pipelines it is the entry of, or a step of under its component). A function with no own pipeline is flagged only for a pipeline that calls it through a reused step (`PL-01 as built`, or an Owner cell naming a PL). A pipeline section with a `**Used by:**` naming another pipeline or package and no `**Boundary:**` is flagged the same way. The interface task freezes a fake for each Boundary (design §4.1)
- Reference checks (design/references.md):
  - `ref-file` E — an RF entry with no File, or whose file is missing
  - `ref-hash` W — an RF entry whose Hash isn't its file's current one (or has none)
  - `ref-large` W — a task reads an `RF-NN` whose file is over 300 lines with no selector (it would get only the outline)
  - `ref-prefix` E — a spec requirement uses the reserved `RF-` or `UR-` prefix
  - `roadmap-skill` W — a roadmap stage's or milestone's own `**Skills:**` names a skill that isn't installed (same list as `skills_available`)
  - `spec-stage` E — once the roadmap has stages, a spec feature with no `**Stage:**` line (nor a stage heading grouping it), or one naming no stage row
  - `milestone-lines` E — a Designed, Planned or Building milestone with no `**Exit:**` line, or (in a stage cut into more than one milestone) a milestone section with no `**Skills:**` or `**References:**` line (build-planning `cut.md`); a milestone that needs either with no `## M<n>` section at all, at its row
  - `milestone-order` E — a milestone row with a lower ID than a row above it (rows run in build order), or whose Depends names its own or a higher ID
  - `exit-cases-in-scope` E — a TC that a milestone's roadmap Exit or Outline, or its plan's Scope Exit, names (ranges expanded) that no tests.md defines, or whose Pipeline isn't in the milestone's Pipelines (its row's cell, else the inferred set)
  - `milestone-depends` E — a cycle in the roadmap milestones' Depends (IDs outside parentheses), once, at its first milestone's row
  - `roadmap-stage` E — once the roadmap has stages, a milestone row whose Stage cell names no stage row, isn't an `S<n>`, or is empty on a row with no Source of its own
- Request checks (design/requests.md §5):
  - `request-format` E — a `- **UR-NN**` line that isn't the request form, names an unknown owner, or whose trace is none of the three forms
  - `request-trace` E — a trace naming an undefined ID, a `§heading` none of the owner's docs has, or a request that doesn't exist, or IDs (none retired) of which none is defined in the owner's docs (a retired one is `retired-ref`), or a change written into an ID that isn't defined. IDs resolve in the archive too: a plan request traced to task IDs still holds after `dt archive` (an archived plan honours it)
  - `request-open` E — an Approved spec.md or architecture.md with an open request of its owner (`spec`, `architecture`), at that doc's header line
  - `request-edit` E (git) — a request whose words, context, skill or date differ from HEAD, or that is gone: only its trace changes
  - `request-ref` E — a `UR-NN` in any doc that docs/requests.md doesn't define
  - `request-number` W — a number in a traced request's words (or a change's what) that none of the IDs it names states: digits, number words to twenty, `5%` as 0.05, `2k` as 2000; a time ("1 hour") matches only a time ("60 minutes"). Numbers that name rather than state are skipped (`requests.strip_labels`): a numbered thing (`Environment 3`, `variation 4`), a step of a sequence (`1 → 2`), a count of the choices asked (`all seven assumptions`), and a bare number that labels an option in the request's `[context]` (`Go with 2 + 4` for `[2 = …; 4 = …]`); a number with a unit always counts
  - `request-cite` W — a doc citing a superseded request, or a changed one from an ID the change wasn't written into (`--into`)
  - `request-source` W — a test case whose Source is only requests, with an Expected number none of them states (a superseded request reads as its replacement, a changed one as what was done instead)
- `explain-stale` W — a page under `docs/explained/` that differs from what `dt explain --write` writes now, or whose package has no pipelines left
- Probe checks (design/probes.md §4–§5):
  - `probe-fields` E — a PB entry with no Folder, Question or Informs, no checks table, a check with an empty Pass cell, a Status that isn't Draft, Ready, Answered · pass|fail or Waived, or (past Draft) a missing folder
  - `probe-informs` E — an Informs ID (decision, requirement, contract symbol) that isn't defined
  - `probe-cite` E — a decision's `**Probe:**` line naming a retired PB, `none` with no reason, or neither a PB nor `none`
  - `probe-open` E — a decision whose Status is Accepted while its `**Probe:**` names an entry that isn't Answered or Waived (Draft, Ready, or an unreadable Status): it stays Proposed until the probe answers
  - `probe-runner` E — `public.py` (the agent's checks) touches the environment or a key (`os.environ`, `environ`, `getenv`, `.env`, `load_env`, `dotenv`; comments ignored), reported at its line; or a check whose Runner isn't agent or user
  - `probe-leak` E — a `dt probes --scan` hit, at the evidence file and line (the pattern, never the text)
  - `probe-sample` E — a doc names a probe sample (`PB-01 samples/sync_added.json#0`, `PB-01:samples/…`) that doesn't exist, or a PB with no entry
  - `probe-results` E — an `evidence/results.json` that isn't the shape above, or names a check the entry's table lacks (at the file and line)
  - `probe-stale` W — the entry's Hash isn't its code's (unstamped or changed), or results.json is for other code
  - `probe-large` W — a probe over 400 source lines (`.py .sh .js .ts .html`, the copied probe_kit.py aside)
- `closed-open-question` W — a bullet under an Open questions heading that says "routed to <skill>" when docs/routes.md has done changes for that skill and no open one: the Revise landed
- `process-narration` W — history in a doc that states what holds: "revised <date>", "adopted before M<n>", "before M<n> is built", "confirmed by the user, <date>" (also approved, agreed, decided, chosen), a TC or golden value that "doesn't change" or "is unchanged", "previously", "as of <date>", or a `## Replan notes` section outside a plan. Skipped: requests.md, routes.md, todo.md, Changelog sections, code, `**Source:**` lines (a test case's provenance) and a plan's own Replan notes (build-planning `replan.md`)
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

Prints one `S<n>:` or `M<n>: <old> → <new>` line per change, and `Depends cycle: M1 → M2 → M1 (…)` per cycle in the milestones' Depends (as `milestone-depends`), then `roadmap: ok` (`roadmap: statuses ok` beside a cycle) / `roadmap: updated N`. `--check` prints the same and exits 1 instead of writing, on any difference or cycle (`roadmap: Depends cycle` when the statuses are current). Writes the file in place through `edit.py` (no Edit/Write, so hooks don't fire), touching only the Status cells and keeping line endings and the file mode. No roadmap, or neither table has a Status column: message on stderr, exit 1.

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
- **`dt tick <M#-T##> [--undo]`** — ticks (or unticks) that task's checkbox in `todo.md` and prints `ticked: <id>` / `unticked: <id>` (`(already)` if nothing changed). When ticking the task that builds a pipeline (a wiring task; with no Kind, a Phase 0 task) it also prints `next: dt prebuild-clear <PL-NN>` for that pipeline. Exit 1 if there's no todo.md or the task isn't in it; 2 for a malformed ID.
- **`dt references --stamp [RF-NN…]`** — sets each entry's (or only the named entries') `**Hash:**` to the first 8 hex digits of its file's sha256, inserting the field after `**File:**` when absent. Prints `RF-NN: <hash>` per change, then `references: stamped N` or `nothing to stamp`. An entry whose file is missing (or that has no File) is reported and not stamped (exit 1); the rest are still stamped. reference-intake runs it after writing entries; a stamp hides a change from `references_changed`, so stamp only after re-summarizing.
- **`dt probes --stamp [PB-NN…]`** — sets each entry's (or only the named entries') `**Hash:**` to its folder's code hash, inserting the field after `**Folder:**` when absent. Prints `PB-NN: <hash>` per change, then `probes: stamped N` or `nothing to stamp`. An entry with no Folder, or whose folder is missing, is reported and not stamped (exit 1). api-probe runs it after writing a probe's code.
- **`dt base [--sha SHA]`** — sets the active plan header's `**Base:**` to HEAD's short sha (inserted after Status if absent). `build-setup` runs it once its bar is approved and committed, so guard-the-bar diffs start from a commit that already holds the bar. Exit 1 without a plan header or outside git.
