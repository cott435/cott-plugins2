# Build Planning Templates

The plan, todo, roadmap milestone and AGENTS.md doc map templates. Worked examples on the quant project are in `references/`: `examples-new.md` (New, and cutting a large stage), `examples-advance-replan.md` (Advance into M2, Replan), `examples-phase0.md` (contract-first Phase 0, skill and reference routing, a foreign plan).

`dt` means `python3 ../../scripts/dt.py`, run from the project root.

## Templates

### `tasks/plan.md` skeleton

A queued plan (`tasks/queued/M<n>-<slug>.md`) uses the same skeleton and has no todo until it's promoted.

`**Base:** —` means pending. build-planning always writes `—`; `build-setup` runs `dt base` after its bar is approved and committed, which sets it to HEAD's short sha.

````markdown
# M<n>: <Milestone name> — Plan

**Milestone:** M<n> · **Status:** Draft · **Base:** — · **Last updated:** YYYY-MM-DD · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)

## Scope
**Exit:** <the capability, and the cases that prove it, in one sentence>
**Covers:** <spec IDs; ranges use an en dash, STAT-01–STAT-04> · **Deferred:** <ID (to M<k>: reason)>, or none
**Skills:** <skill (which steps)>, or none

## Phase 0: Spine

### M<n>-T01: <PL-NN spine with its baseline>
…

## Phase 1: Thicken

### M<n>-T02: <one step upgrade>
…

### Checkpoint after M<n>-T03
…

### Checkpoint: milestone exit
…

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| <risk> | <what goes wrong> | <the task or case that catches it> |

## Open questions

## Replan notes
````

Status runs Draft → Approved → In progress → Done, then `dt archive` replaces the file with the stub.

### Task templates

**Spine task** (Phase 0). Step is the whole pipeline; Mode is always `solo`. A contract task (multi-package) has Step `contract`; see `references/examples-phase0.md`.

```markdown
### M2-T01: PL-03 spine with equal weights
**Package:** quant · **Step:** PL-03 · **Covers:** — · **Size:** M · **Mode:** solo
**Skills:** —
**Read:** PL-03, portfolio.min_variance, stats.estimate_cov, PORT-01
**Acceptance:**
- [ ] `python -m quant.portfolio backtest --smoke` runs end to end on synthetic returns, every step at its spine version
- [ ] The smoke run is committed as PL-03's smoke test
- [ ] PL-03 pre-build sections replaced by a `dt layout` pointer
**Verify:** `python -m quant.portfolio backtest --smoke` · `scripts/check.sh gate`
**Depends on:** — · **Files likely:** src/quant/portfolio/__init__.py, src/quant/portfolio/__main__.py, src/quant/portfolio/pipeline.py, src/quant/portfolio/minvar.py, src/quant/portfolio/compare.py
```

**Thicken task.** One step, one package, at most 3 bullets, smoke command in Verify.

```markdown
### M2-T03: Minimum-variance weights
**Package:** quant · **Step:** PL-03.min_variance · **Covers:** PORT-01 · **Size:** S · **Mode:** split
**Skills:** data-science
**Read:** PL-03, TC-04, PORT-01, portfolio.min_variance
**Acceptance:**
- [ ] TC-04 passes within tolerance; equal weight stays selectable as the baseline
- [ ] PL-03 smoke test still passes
**Verify:** `pytest tests/intent/quant tests/unit/quant -k minvar` · `python -m quant.portfolio backtest --smoke` · `scripts/check.sh gate`
**Depends on:** M2-T01 · **Parallel:** G1 · **Files likely:** src/quant/portfolio/minvar.py, tests/unit/quant/test_minvar.py
```

| Field | Rule (lint code) |
|---|---|
| `Package` | One package id (`task-fields`) |
| `Step` | `PL-NN.<function>` from the step table (`task-step`); `PL-NN` on a spine task; `contract` on a contract task |
| `Covers` | Spec IDs the task satisfies |
| `Size` | XS = 1 file, S = 1–2, M = 3–5 in `Files likely` (`task-size`) |
| `Mode` | `split` for checkable behavior, `solo` for contract, spine, refactor, glue, doc-sync |
| `Skills` | Skill names, or `—`. Every skill on the milestone's `**Skills:**` line (else its stage's) lands on at least one task (`skills_unrouted`). A missing skill is still named |
| `Read` | IDs and repo paths, comma-separated. Everything the builder needs, nothing more (`missing-ref`). References by ID with an optional selector: `RF-01:residualize`, `RF-01:outline`, `RF-03:<heading>`; a long one with none warns (`ref-large`). Every milestone reference lands on at least one task (`references_unrouted`) |
| `Acceptance` | ≤ 3 checkbox bullets, each test-backed (`task-acceptance`) |
| `Verify` | Backticked commands joined by ` · `. After Phase 0, includes the smoke command (`verify-smoke`) |
| `Depends on` | Task IDs earlier in the plan, or `—` (`depends`) |
| `Parallel` | Optional `G<n>`. No shared file or contract symbol in a group (`parallel`). Package spines carry one; the contract task and the system spine never do (they count in full toward `milestone-size`) |
| `Files likely` | Comma-separated paths |
| `Reason` | Optional one line: a mode override, or a second package or step |
| `Blocked` | Added when a task is paused; Replan removes it once resolved |

Title rule: no " and " (`task-title`). Required fields: Package, Step, Size, Mode, Read, Acceptance, Verify (`task-fields`).

### Checkpoint blocks

Every 2–3 tasks:

```markdown
### Checkpoint after M2-T03
- [ ] Every pipeline in the milestone runs end to end (smoke commands)
- [ ] All golden cases pass
- [ ] Entry functions still read top to bottom as the step table says (Sync if not)
- [ ] No new abstraction without a second implementation or an AD
- [ ] contract.md matches the contract code (`dt status` freshness check)
- [ ] `dt layout` output reviewed; Definition of Done holds
- [ ] `scripts/check.sh full` passes; Review checklist done; every finding has a disposition
```

Last, after the final task: the same list under `### Checkpoint: milestone exit`, plus `- [ ] The Scope's Exit holds`.

Findings are not written by this skill. The orchestrator records the reviewer's findings with `dt finding`, and they look like this:

```markdown
**Findings:**
- M2-R01 Important · CR-21 · `portfolio/compare.py::compare` complexity 14 → fix task M2-T05
- M2-R02 Nit · readability · column names → won't fix: match the paper's notation
```

A finding whose disposition is a fix task means Replan adds that task.

### `tasks/todo.md`

One line per task, `<ID> <title> (<package>, <size>, <mode>)`. No checkpoints. Lines start unchecked; only `dt tick` checks them.

```markdown
# M2: Classical portfolios — Todo

- [ ] M2-T01 PL-03 spine with equal weights (quant, M, solo)
- [ ] M2-T02 Out-of-sample comparison (quant, S, split)
- [ ] M2-T03 Minimum-variance weights (quant, S, split)
- [ ] M2-T04 Shrinkage as the backtest default (quant, XS, solo)
```

### Stub plan (between milestones)

Written by `dt archive`. Never deleted; replaced only by the next plan.

```markdown
# Between milestones

**Status:** Between milestones · **Last updated:** 2026-11-02 · **Roadmap:** [../docs/roadmap.md](../docs/roadmap.md)
```

### Milestone rows

`idea-refine` adds the stage (`S<n>`: Name, Source, and a section with Outline and Skills). When the stage's pipelines are approved, this skill cuts it: one milestone row per slice under the milestone table (add the table below the stage table if it's missing), and a section with the slice's `**Outline:**`, then `**Exit:**`, `**Plan:**` and outcome text once planned. `dt roadmap` writes both `Status*` columns; never edit them.

```markdown
| Stage | Name | Source | Status* |
|---|---|---|---|
| S1 | Data + stats | brief | Building |
| S2 | Classical portfolios | ideas/classical-portfolios.md | Planned |

| Milestone | Stage | Name | Packages | Pipelines | Depends | Status* |
|---|---|---|---|---|---|---|
| M1 | S1 | Data + stats | quant | PL-01, PL-02 | — | Building |
| M2 | S2 | Classical portfolios | quant | PL-03 | M1 | Planned |

## M2: Classical portfolios
**Outline:** A walk-forward backtest compares min-var with equal weight.
**Exit:** Min-var beats equal weight on out-of-sample variance; TC-04 passes.
**Plan:** [../tasks/plan.md](../tasks/plan.md)
```

A stage that fits one milestone gets one, and the milestone inherits the stage's Skills and references. A stage cut into several gives each milestone `**Skills:**` and `**References:**` lines from the stage's (`references/examples-new.md`). Later milestones get only the row and a 3–6 line section (Outline, Exit, and Plan once a plan exists).

### AGENTS.md doc map

Written in New mode, ≤ 25 lines, no script paths (the session-start hook supplies them). Replace only these two sections; leave the rest of the file alone. If the repo has `CLAUDE.md` and no `AGENTS.md`, write them there.

```markdown
## Docs
- Plan with dev-team2's `build-planning`, not agent-skills' `/plan`.
- Your task's context: `dt context <M#-T##>`. Read only what it prints.
- Any section by ID: `dt section <ID>...` (e.g. PL-02 TC-02 STAT-02 AD-03)
- Package docs: `docs/packages/<pkg>/{architecture,contract,pipelines,tests}.md`
- Real layout: `dt layout <pkg>` (planned layouts are gone once the spine lands)
- Quality bar: CONSTRAINTS.md. Oracle files (tests/fixtures/*/expected.json) need user approval to change.
## Project skills
- data-science — stats steps
```

Use real IDs from the project in the `dt section` example. List each project skill with the steps it's routed to.
