# dt — dev-team2 doc tool

One stdlib-only CLI that parses every planning doc. Skills, hooks and agents get IDs, statuses, sections, coverage and lint from it instead of reading and counting by hand. Design: [design/planning-stage.md §10, §13](../design/planning-stage.md).

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
    model.py               typed views: Task, Checkpoint, Finding, TodoItem, Pipeline, Step, TestCase,
                           Milestone, Reference, Symbol, Component; cross-doc helpers (spine_done,
                           smoke_command, milestone_references…)
    specdocs.py            spec/architecture Changelog matching and fence checks (ported from arch-status.py)
    code.py                project source via ast: module docstrings, entry-function calls, pipeline drift
    outline.py             one file's outline (ast defs/classes, markdown headings) and selections (symbol, heading)
    references.py          references/ vs docs/references.md: file hashes, files waiting for reference-intake
    git.py                 thin git helpers (commit dates, HEAD text, changed files); degrade outside git
    edit.py                byte-preserving, mode-keeping reads/writes; every file dt writes goes through it
    status/                `dt status` reports: common.py, packages.py, one module per skill
    commands/<name>.py     one module per command: add_arguments(parser), run(args, repo) -> int
  tests/
    fixtures/quant/        sample single-package project mid-M1 (the canonical worked example), with two
                           reference files (references/) and their index
    dt_helpers.py          run dt in-process; throwaway fixture copies (optionally under git)
    test_<area>.py         unittest, stdlib only
```

Commands never glob or open docs themselves; they ask `Repo` (doc map, IDs) and `model` (typed views). A parsing fix goes in `md`/`repo`/`model` so every command sees it.

## Doc format (what the parser reads)

- **Doc kinds** come from the path (`repo.KINDS`): brief, idea, roadmap, spec, architecture, package-architecture (`docs/packages/<pkg>/architecture.md`, legacy `docs/architecture/<pkg>.md`), contract, pipelines, tests, references (`docs/references.md`), constraints, agents, plan, todo, queued-plan, archived-plan. `tasks/archive/**` is read only for `next-id` and as a `section` fallback.
- **Header:** first non-blank line after the H1, `**Key:** value` pairs joined by ` · `. Unknown keys are kept.
- **ID sections:** `## <ID>: <Title>` or `### <ID>: <Title>`, outside code fences. A section runs to the next heading of the same or higher level. ID forms: `PL-NN`, `TC-NN`, `AD-NN`, `CR-NN`, `M<n>`, `M<n>-T<nn>`, `M<n>-R<nn>`, `<pkg>.<symbol>` (any `PREFIX-NN` works as a heading ID).
- **Spec requirements:** bold-led lines `- **CODE-NN** …` plus their indented sub-bullets. Struck (`~~`) on the line = removed.
- **CONSTRAINTS rules:** bold-led `- **CR-NN** …` lines and table rows whose first cell is `CR-NN`.
- **Retired:** `- ~~<ID>: <title>~~ Retired YYYY-MM-DD: <reason>`. A decision heading with a struck title (`### AD-02: ~~Old~~`) is superseded and counts as retired.
- **Findings:** list items `- M<n>-R<nn> <Severity> · <rule> · <text> → <disposition>` under a checkpoint's `**Findings:**`.
- **Ranges:** `STAT-01–STAT-04` and `STAT-01–04` expand to every ID in between.
- **Pre-build sections:** any heading containing `(pre-build`.
- **Reference entries** (`docs/references.md`, design/references.md §4): `### RF-NN: <Title>`, then `**File:** \`references/…\` · **Hash:** <8 hex> · **Kind:** code|doc · **Milestones:** M2, M4 | all | —` and bullet fields `- **Purpose:**`, `**Key parts:**`, `**In → Out:**`, `**Use for:**`, `**Caveats:**`. Retired entries are retired lines. "References for M<n>" are derived from `Milestones` (`all` serves every milestone; `—` none); there is no second list. A `Read:` item `RF-NN:<selector>` names the entry `RF-NN`.
- **Roadmap milestone sections** may carry `**Skills:** a, b` (idea-refine writes it): the skills routed to that milestone.

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
- `next ids`: AD, PL, TC, M, plus `M<n>-T` while a plan is active. AD also counts every AD the architecture docs mention, so a broken fence can't hide one.

Every report (any `--skill`, or none) then prints the reference files waiting for `reference-intake`:
- `references_unindexed` — files under `references/` (hidden files and caches skipped) with no entry
- `references_changed` — `RF-NN (path)`: the file's hash differs from the entry's Hash, or the entry has none
- `references_missing` — `RF-NN (path)`: the entry's file is gone

Then skill-specific lines. Lists print as `key: a, b, c` or `key: none`; per-package maps as `pkg=mode, …`. Each key is printed even when empty, so a skill can rely on it. Exit 1 when mode is `blocked`, else 0.

`--json` prints one object with the same keys (`next_ids` for `next ids`); lists stay lists, maps stay objects, `blocked` is `null` when not blocked. `drift` is a list, or the string `"unknown"` until `dt layout`'s drift check is available; build-setup's generated-config checks are `"unknown"` when their input file is absent. `dependents` is `{pkg: [dependents]}`. Structured extras in JSON only: `ideas` and `packages` are objects, `roadmap_rows` is a list of `{id, name, source, status}`, `prefixes` is `{PREFIX: {highest, next}}`, and architecture-design adds arch-status.py's `spec` (`path`, `status`, `live_requirements`) and `architecture` (`path`, `exists`, `status`, `shape`, `last_updated`) objects.

| `--skill` | Modes | Extra keys |
|---|---|---|
| `idea-refine` | new · extend | `brief_words`, `brief_goals` (count), `ideas` (path=status), `roadmap_rows` (`M<n> name [source]`), `references_unassigned` (RF entries with `Milestones: —`) |
| `spec-writing` | blocked · new · extend | `ideas_ready` (Accepted ideas), `prefixes` (`highest→next` per prefix), `reserved_prefixes` (planning prefixes a requirement must not use: AD, CR, EX, PL, RF, TC), `skills` |
| `architecture-design` | blocked · new · extend · current | everything the old `arch-status.py` reported (`uncovered`, `changed_since`, `spec_rows_pending`, `stale`, `next_decision`, `package_docs`, `packages_found`, `skills`, `broken_fences`), plus `contracts_missing` (packages with no `contract.md`; `(no package id yet)` when no id can be found or inferred), `legacy_layout` (`docs/architecture/<pkg>.md` files to move), `grow_triggers`, `stale_contracts` |
| `pipeline-design` | blocked · new · grow · revise · extend · sync · current (per package) | `packages` (pkg=mode), `uncovered_ids` (spec IDs covered by a component in scope but on no pipeline step or Covers, system pipelines included), `components_unowned` (components that own no step), `drift` (entry calls ≠ step table, from `dt layout`), `retired_refs` (`path:line ID`), `misplaced` (pipelines whose Entry lies in another package's source folder) |
| `test-planning` | blocked · new · revise · extend · current (per package) | `packages` (pkg=mode), `pipelines_no_smoke`, `pipelines_no_golden`, `cases_no_source`, `cases_no_tolerance`, `fixtures_missing` (folder or `expected.json`), `fixtures_orphan` (`tests/fixtures/*/TC-NN/` no live case uses), `skills` |
| `build-planning` | blocked · new · extend · replan · advance · foreign · current | `milestone` (active M and status), `progress` (done/total), `next_task`, `blocked_tasks`, `uncovered` (milestone spec IDs on no task and not Deferred), `no_spine` (milestone pipelines with no Phase 0 task, archive included), `mode_violations`, `draft_pipelines`, `changed_since_plan` (milestone docs Approved after the plan's Last updated), `pipelines_inferred` (the planned milestone's pipelines when its roadmap cell is empty, to write into the row), `milestone_references` and `milestone_skills` (the RF IDs whose Milestones name it, and its roadmap `**Skills:**`, for the same milestone as `pipelines_inferred`), `references_unrouted` (`RF-NN (M<n>)`: for the active and each queued plan, a milestone reference in no task's `Read:`, selector ignored), `skills_unrouted` (`skill (M<n>)`: a milestone skill on no task's `**Skills:**`), `skills_missing` (referenced by the plan, its tasks or the milestone's `**Skills:**`, not installed), `skills_available`, `grow_triggers`, `drift` (milestone pipelines), `stale_contracts`, `queued`, `base` |
| `reference-intake` | new · extend · current | `index` (references.md status or `missing`), `files_to_read` (unindexed and changed files), `outline_first` (`.py` files to read over 400 lines: give the subagent `dt outline` plus the first lines), `next_id` (next RF), `milestones` (`M<n> name`, to assign files to) |
| `build-setup` | blocked · new · extend · ratchet · current | `constraints` (status), `config_mismatches`, `contract_mismatches`, `optional_layers_existing`, `deptry_missing`, `protected_gaps`, `ignores_without_exception`, `agents_missing`, `hooks_missing` (hook and check scripts, plus any `scripts/…` an agent file names), `not_executable`, `expired_exceptions`, `tools_missing` (uv, jq), `dependents` (`pkg<-a,b`), `base` |

`skills` and `skills_available` list installed skills by name: the project's `.claude/skills/*/SKILL.md` plus `$CLAUDE_PLUGIN_ROOT/skills/*` when that is set, minus dev-team2's own planning skills (reference-intake included).

`--summary` (SessionStart hook) prints at most 8 lines: active milestone and plan status, progress and next task, blocked tasks, queued plans, docs waiting for approval (Draft), a stale roadmap, `references: N waiting → reference-intake` when any reference file is unindexed, changed or missing, and `dt: python3 <resolved path to dt.py>`. It prints nothing in a project with none of `docs/brief.md`, `docs/spec.md`, `docs/roadmap.md`, `tasks/plan.md`, never fails (an internal error prints one `dt status: error: …` line) and always exits 0.

Mode rules:
- **blocked** — idea-refine never; spec-writing: no brief; architecture-design: no spec (as arch-status.py; a Draft spec shows in `docs`); pipeline-design: architecture missing or not Approved; test-planning: no package has an Approved pipelines.md (a package whose pipelines.md isn't Approved is `pkg=blocked`); build-planning: the next milestone to plan has pipelines not all Approved, or a Revise is open on the active milestone's docs (below); build-setup: no active plan, or the plan is Draft.
- **architecture-design** — `new`: no architecture.md; `extend`: `uncovered`, `changed_since`, `contracts_missing` or `legacy_layout` non-empty (the last two migrate projects designed before contract.md and `docs/packages/`); else `current`.
- **pipeline-design** (per package; the overall mode is the first of new, grow, revise, extend, sync present) — `new`: no pipelines.md; `grow`: `misplaced` lists one of its pipelines; `revise`: pipelines.md is Draft but Approved at git `HEAD`; `sync`: drift; `extend`: uncovered IDs or unowned components; else `current`.
- **test-planning** (per package) — `new`: no tests.md; `revise`: tests.md Draft but Approved at `HEAD`; `extend`: a pipeline with no smoke command or no golden case; else `current`. A pipeline with `**Part of:** PL-NN` (a package's part of a system pipeline) needs no smoke or golden case of its own.
- **build-planning** — first rule that holds: `foreign`: `tasks/plan.md` exists without a dev-team2 header (no `**Milestone:**`) and has unchecked tasks; never overwrite, ask. With an active plan: `advance` when every todo item is checked and the exit checkpoint is ticked (a finished milestone advances even while a Revise is open: that belongs to the next plan); `blocked` (`waiting for <doc> approval (Revise in progress)`) when a pipelines.md or tests.md of the milestone's packages is Draft, or a doc defining one of its pipelines (`draft_pipelines`) is; `replan` when a task is `Blocked`, or `changed_since_plan` is non-empty: the packages' pipelines.md, tests.md or contract.md is Approved with a `Last updated` date later than the plan's (same-day changes aren't seen; a Replan bumps the plan's date); `extend` when the next roadmap milestone is Designed (queue it); else `current`. The milestone's packages are its roadmap Packages, its pipelines' packages and its tasks' Package. With no active plan (missing or between milestones): `extend` if a queued plan exists; otherwise for the first milestone not yet Planned/Building/Done: `new` (no plan ever written) or `extend`, or `blocked` if its pipelines aren't Approved. No roadmap: `new` once any pipelines.md is Approved.
- **Milestone pipelines** (build-planning and `dt roadmap`) — the roadmap row's Pipelines cell; when it names none (idea-refine writes `—`), they are inferred from the row's Source: the spec Changelog rows citing its idea files (`brief` → rows citing brief.md) give the milestone's IDs (minus those marked removed), and its pipelines are the live package and system pipelines whose Covers include any of them (step Covers only for a pipeline with no Covers line, since a reused step cites an earlier milestone's IDs). `pipelines_inferred` prints the inferred set for the milestone the mode acts on (the one to queue or plan, else the active one), empty when its cell is filled; an explicit cell always wins.
- **build-planning task modes** — expected `solo` for Phase 0 (spine) tasks; `split` for any other task with Covers or a `TC-NN` in Read; `solo` otherwise. A `**Reason:**` line on the task overrides.
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

`PL`, `TC`, `AD`, `CR`, `RF`, any spec prefix, `M`, `M2-T`, `M2-R`. Counts retired IDs and the archive. Prints one ID per prefix.

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
   followed by one of: the whole file (no selector, ≤ 300 lines); its outline (`RF-NN:outline`, or no selector on a file over 300 lines, with a note to name a part); one part (`RF-NN:<symbol>` — a module-level def, class or assignment, or `Class.method`, via `ast` — or `RF-NN:<heading>` in markdown, case-insensitive), preceded by `(<selector> · lines a–b of N)`. A selector that names nothing is a problem (exit 1); a missing reference file is noted, not fatal.
3. `## Layout (\`dt layout <pkg>\`)` — the task package's real tree, when its source folder exists (built pipelines point at `dt layout` instead of a planned layout, and the builder shouldn't have to run it).
4. `## Files likely` — the list, each marked `(exists)` or `(new)`.
5. The task section itself, last.

The task is looked up in `tasks/plan.md` and `tasks/queued/`. Warns on stderr (exit stays 0) when the packet is over 2,000 lines. Exit 1, nothing on stdout, if the task or any `Read:` ID is missing or retired. `--json`: `task`, `package`, `mode`, `lines`, `read` (each `ref`, `kind` id|file|reference; a reference adds `where`, `file`, `selector`, `shown` whole|part|outline|missing), `files_likely`, `text` (the packet).

### `dt outline <file|RF-NN>`

One file's outline, read without importing or running it. The first line is `<path> · <kind> · <n> lines`; then:
- `.py` (`python`): `<line>: <signature> — <docstring first line>` for each module-level def and class, methods indented under their class (via `ast`). A file that doesn't parse falls back to the first lines, noted `cannot parse`.
- `.md` (`markdown`): `<line>: ## <heading>` for every heading outside code fences.
- anything else (`text`): the first 40 lines, noted `first N lines`.

`RF-NN` outlines that entry's File. Exit 1 if the file can't be read as UTF-8.

### `dt references [RF-NN…] [--stamp]`

Without `--stamp`: one line per entry, `RF-NN: <file> · ok|changed (now <hash>)|unstamped|missing · <milestones>`, then `unindexed: …` (when no IDs are given). With `--stamp` (mechanical, below): writes each entry's Hash.

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
- `missing-ref` E — an ID in a `Read:`, `Covers`, `Step`, `Pipeline`, `Used by`, `Part of` or `References` field, or a `Covers`, `Pipeline(s)`, `Used by` or `Read` table column, that isn't defined anywhere (archive counts as defined). `Read:` entries that look like paths (`/` or a file extension) are skipped; `PL-02.step` checks `PL-02`; `RF-01:pca_factors` checks `RF-01`. Ranges expand. Changelog sections are skipped. (`Depends on` is checked by `depends`.)
- `retired-ref` E — a literal mention of a retired ID (retired line, struck decision heading, struck requirement) anywhere outside code fences, except: retired lines and superseded/removed definitions themselves, the decision named in `Superseded by AD-NN`, and Changelog sections. An ID only reached through the inside of a range (`STAT-01–STAT-06`) isn't flagged
- `budget` W — size budgets (§3), in lines: contract.md > 60, pipelines.md and tests.md > 120, plan.md and queued plans > 400, a roadmap `## M<n>` section > 6 non-blank lines, AGENTS.md/CLAUDE.md `## Docs` + `## Project skills` > 25
- `approved-edit` W — a doc whose `HEAD` version and working copy are both Approved but whose text (header line and trailing whitespace excluded) differs: it was edited without going back to Draft, or the approval isn't committed yet. Skipped outside git, for files not in `HEAD`, and for plan/queued/todo/roadmap (dt's mechanical edits). In contract.md, `**Used by:**` lines are ignored: pipeline-design appends PL IDs there without a Revise; in references.md, Hash values are ignored (`dt references --stamp` writes them)
- `prebuild-left` E — a pre-build section inside a `PL-NN` section whose pipeline is built, or one outside any pipeline (Planned layout) when every pipeline in that doc is built. Built = `model.pipeline_built`, the same rule as `dt prebuild-clear`: spine task checked in `todo.md`, or (no spine task in the active plan) entry file exists
- `pipeline-fields` E — a package pipeline (`PL-NN` in pipelines.md) with no `Entry` or `Trigger`, or a step row whose Owner or Spine version cell is empty (`—` counts as empty). A system pipeline (`PL-NN` in the root architecture.md: package → package over named contracts) needs only a `Trigger` and steps (a table or a numbered `1. …` list); no Entry, Owner or Spine version
- `contract-heading` E — a contract.md `##`/`###` heading that starts with a `pkg.symbol` but isn't `<pkg>.<symbol>: <title>`: most often one naming several symbols (`train.train / train.train_seeds: …`, split on `/ , · & + and`), else a symbol with no `: <title>`. dt resolves a symbol only from its own heading, so `Read:` and `dt context` would fail on it later
- `spine-mock` W — a pipelines.md Spine version cell containing mock, stub, fake, TODO or placeholder: the spine must be a real baseline (system pipelines are skipped)
- `fixture-size` — per TC with a `Fixture:` folder: folder missing, or no `input.json` / `expected.json` → **E**; folder over 100 KB → W (also for a `tests/fixtures/<pkg>/TC-NN/` folder no TC names, reported at the folder). Optional TC fields such as `Parse:` and `Skills:` aren't checked
- Task checks run on `tasks/plan.md` and `tasks/queued/*.md` written by build-planning (a foreign plan is skipped):
  - `task-size` E — Size not XS/S/M, or `Files likely` count outside the size's range (XS 1, S 1–2, M 3–5)
  - `task-acceptance` E — more than 3 top-level bullets under `**Acceptance:**` (indented sub-bullets don't count)
  - `task-title` E — the word "and" in a task title (any case)
  - `task-fields` E — missing Package, Step, Size, Mode, Read, Acceptance or Verify; Mode not split/solo
  - `task-step` W — Step `PL-NN.<name>` names a step that isn't in that pipeline's table
  - `depends` E — a `Depends on` task that isn't defined, comes at or after the task **in plan order** (position in the file, not ID number: Replan reorders without renumbering), or a cycle (reported once). A task from another plan or the archive resolves
  - `parallel` E — two tasks with the same `Parallel` group sharing a `Files likely` path or a `Read:` contract symbol (`pkg.symbol`)
  - `verify-smoke` E — a task outside Phase 0 whose `Verify:` lacks its Step pipeline's smoke command (tests.md Strategy `Smoke` cell, else the pipeline's Trigger + ` --smoke`)
  - `finding-disposition` E — a finding under a checkpoint with no `→ <disposition>`
- `todo-mismatch` E — task IDs in todo.md ≠ plan.md (each side reported in its own file)
- Reference checks (design/references.md):
  - `ref-file` E — an RF entry with no File, or whose file is missing
  - `ref-hash` W — an RF entry whose Hash isn't its file's current one (or has none)
  - `ref-large` W — a task reads an `RF-NN` whose file is over 300 lines with no selector (it would get only the outline)
  - `ref-prefix` E — a spec requirement uses the reserved `RF-` prefix
  - `roadmap-skill` W — a roadmap milestone's `**Skills:**` names a skill that isn't installed (same list as `skills_available`)
- `foreign-plan` W — tasks/plan.md without a dev-team2 header (no `**Milestone:**`, not Between milestones); it gets no other checks
- `broken-fence` E — a fence that never closes, or one that holds a `## ` line (unless its info string is `markdown`/`md`)
- `header` E — a doc of a known kind with no header line, or no Status. Roadmap needs a header but no Status; todo, AGENTS.md/CLAUDE.md and a foreign plan are exempt
- `unreadable` E — a doc-map file that isn't valid UTF-8
- `internal` W — a check crashed (a `dt` bug); the other checks still run

**`--hook`** (plugin hooks): reads the Claude Code hook JSON on stdin (`hook_event_name`, `cwd`, `tool_input.file_path`), uses `cwd` as the root (ignores `--root`), always exits 0 and fails open (bad JSON or any exception → no output).
- `PostToolUse`: lints only the edited file, and only if it's under `docs/` or `tasks/` or is CONSTRAINTS.md/AGENTS.md/CLAUDE.md. Errors → `{"decision": "block", "reason": "<lines>"}` (feeds the problems back; the edit stays). Warnings only → `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "<lines>"}}`. Clean → nothing.
- `Stop`: like `--changed`; any problems → `{"systemMessage": "dt lint: <n> problem(s)\n<lines>"}`. Never blocks.

### `dt roadmap [--check]`

Rewrites the roadmap's derived `Status*` column: Idea → Specced → Designed → Planned → Building → Done. The first rule that holds, from the top:
- **Done** — an archived plan for it exists, or the roadmap section has an `**Outcome:** Done …` line
- **Building** — it's the active plan and at least one todo item is checked
- **Planned** — a plan for it exists (queued, or active with no checked task)
- **Designed** — every live pipeline of the milestone is defined in an Approved pipelines.md or architecture.md (system pipelines); retired IDs are skipped. The pipelines are its `Pipelines` cell, or, when that names none, the set inferred from its Source (see Milestone pipelines under `dt status`); none at all → not Designed
- **Specced** — every idea file its `Source` cites is Specced; for a `brief` row, the brief is Accepted and the spec Approved
- **Idea** — otherwise

Prints one `M<n>: <old> → <new>` line per change, then `roadmap: ok` / `roadmap: updated N`. `--check` prints the differences and exits 1 instead of writing. Writes the file in place through `edit.py` (no Edit/Write, so hooks don't fire), touching only the Status cells and keeping line endings and the file mode. No roadmap or no Status column: message on stderr, exit 1.

### `dt guard` (PreToolUse hook)

Reads the hook JSON on stdin (`tool_input.file_path`, or `notebook_path`; `cwd`). The path is taken relative to `cwd`. Prints the hook decision JSON:
- `tests/fixtures/**/expected.json` (matched anywhere in the path, so a nested project's oracles are covered too) → `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "Oracle file: …"}}`
- `tasks/archive/**` under `cwd` → `permissionDecision: "deny"` (only `dt archive` writes there)
- anything else → no output, exit 0.

Always exits 0 and fails open: unreadable input or any error → no output. `dt guard --path P` decides for P (relative to `--root`) without stdin. `dt.py` runs it without building a `Repo`.

### Mechanical edits

These write files directly (atomically, via a temp file), keep every untouched byte, line ending and the file's permission bits (a new file, such as the archive, gets 0644 less the umask), and never change a doc's Status. `devteam/edit.py` holds the shared read/write helpers; every dt write (these, `dt roadmap`) goes through it.

- **`dt prebuild-clear <PL-NN>`** — replaces that pipeline's `Entry sketch (pre-build …)` subsection with `Layout: \`dt layout <pkg>\`` (just removes it if the pipeline already has that line). When every pipeline in the doc is built, also removes `## Planned layout (pre-build …)`; otherwise says which aren't. Built = its spine task is checked in `todo.md`, or, for a pipeline with no spine task in the active plan (built in an earlier milestone), its entry file exists. Idempotent: a second run prints `nothing to clear`. Exit 1 if the pipeline isn't found.
- **`dt archive [--date YYYY-MM-DD]`** — refuses (exit 1, nothing written) unless the plan is an active milestone plan, `todo.md` has task items and every one is checked, and the archive file doesn't exist yet. Copies `tasks/plan.md` byte for byte to `tasks/archive/M<n>-<slug>.md` (slug from the plan's H1 name) with the todo appended as a final `## Todo` section; adds `**Outcome:** Done <date>` to the roadmap's milestone section if it has no Outcome (adding the section if missing) and points its `**Plan:**` link at the archive; writes an empty todo (`# Todo`); then replaces `tasks/plan.md` in place with the stub (`# Between milestones` + `**Status:** Between milestones · **Last updated:** <date> · **Roadmap:** …` + a line naming the archive), so the plan is never missing. Prints the archive path.
- **`dt finding <checkpoint-task-id|exit> <severity> <text> [--disposition TEXT]`** — appends `- M<n>-R<nn> <Severity> · <text>[ → disposition]` after the findings already under that checkpoint's `**Findings:**` (the label is created after the checkpoint's last line if absent), with the next free `M<n>-R` ID (archive counted). `exit` = the checkpoint whose title contains "exit". Severities (case-insensitive): Critical, Important, Suggestion, Nit (agent-skills `code-review-and-quality`); anything else exits 2. Prints the new ID.
- **`dt tick <M#-T##> [--undo]`** — ticks (or unticks) that task's checkbox in `todo.md` and prints `ticked: <id>` / `unticked: <id>` (`(already)` if nothing changed). When ticking a Phase 0 task it also prints `next: dt prebuild-clear <PL-NN>` for the task's pipeline. Exit 1 if there's no todo.md or the task isn't in it; 2 for a malformed ID.
- **`dt references --stamp [RF-NN…]`** — sets each entry's (or only the named entries') `**Hash:**` to the first 8 hex digits of its file's sha256, inserting the field after `**File:**` when absent. Prints `RF-NN: <hash>` per change, then `references: stamped N` or `nothing to stamp`. An entry whose file is missing (or that has no File) is reported and not stamped (exit 1); the rest are still stamped. reference-intake runs it after writing entries; a stamp hides a change from `references_changed`, so stamp only after re-summarizing.
- **`dt base [--sha SHA]`** — sets the active plan header's `**Base:**` to HEAD's short sha (inserted after Status if absent). `build-setup` runs it once its bar is approved and committed, so guard-the-bar diffs start from a commit that already holds the bar. Exit 1 without a plan header or outside git.
