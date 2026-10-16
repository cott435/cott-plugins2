---
name: architecture-design
description: Designs and maintains the project architecture (docs/architecture.md) and each package's contract (docs/packages/<pkg>/contract.md) — system design, components, dependencies, interfaces, and technical decisions — from an approved spec. Scales from a single-package proof of concept to a multi-package monorepo, and keeps the architecture in step as the spec grows, decisions change, or a project outgrows one package. Use when docs/spec.md is approved and no architecture exists, when new spec requirements need a home in the design, when a technical decision (library, data source, model type, storage) must be made or reversed, when a package should split, or when the code has drifted from the documented design.
---

# Architecture Design

## Overview

The brief says **why**, the spec says **what**, and the architecture (`docs/architecture.md`) says **how it will be built**: the components, how they depend on each other, the contracts between them, and the technical decisions behind them, including which libraries, data sources, and model types to use. Every spec requirement has a home in some component, and every significant choice has a recorded reason. Each package's public API lives in its own `docs/packages/<pkg>/contract.md`, so whoever consumes it reads only that page.

The architecture is sized to the project. A proof of concept gets one short file and one contract. A monorepo gets a system map plus an architecture doc and a contract per package.

## When to Use

- `docs/spec.md` is `Approved` and `docs/architecture.md` does not exist
- The spec gained or changed requirements (an idea was specced) and the design must place them
- A technical decision needs making or reversing: library, framework, storage, data vendor, model type, deployment
- A single package is growing into several
- The code no longer matches the documented design, or an existing codebase has no architecture doc

**Not for:**
- Deciding *what* to build or *why* (use `spec-writing` / `idea-refine`)
- Pipelines, file layout and tasks (use `pipeline-design`, then `build-planning`, after the architecture is approved)
- Detailed API style rules (follow `api-and-interface-design` if available; this skill records the contracts)

## Shape: Single Package vs Multi-Package

Decide the shape first and record it in the header (`**Shape:** Single package` or `Multi-package`). It sets which files exist and how much goes in them.

| | **Single package** | **Multi-package** |
|---|---|---|
| Typical project | Proof of concept, library, one service, research code | Platform or monorepo of separately installed/deployed packages |
| Files | `docs/architecture.md` + `docs/packages/<pkg>/contract.md` | Root `docs/architecture.md` (system map) + `docs/packages/<pkg>/architecture.md` and `contract.md` per package |
| "Components" are | Modules inside the package, one subfolder each | Packages; modules are described in each package doc |
| Interfaces | `contract.md`, one `## <component>` group per component | Each package's `contract.md`; the root lists cross-package contracts and System pipelines |
| Dependencies | Third-party libraries | Package dependency graph and layering rules, plus third-party libraries |
| Decisions | In `docs/architecture.md` | All in the root doc, each tagged with a scope (`system` or a package id) |
| Typical length | 1-3 pages; contract ≤ 1 page | Root 2-4 pages; each package doc 1-3 pages, contract ≤ 1 page |

**Choose multi-package only when there is a real boundary:** parts that are installed, versioned, or deployed separately; different runtimes or languages; different owners; or a dependency direction worth enforcing with tooling. Otherwise choose single package. **A proof of concept is almost always a single package.**

**Don't build the platform inside the proof of concept.** In a single package, name the seams that would become packages later (for example, "the data loader is behind `DataSource` so it can move out"), and stop there.

## Modes

Start with `python3 ../../scripts/dt.py status --skill architecture-design`. The path is relative to this skill's folder: resolve it from where this SKILL.md lives, and run the command from the project root. Take the mode, the shape and the next free `AD` and `PL` IDs from its output, never from counting. Its gap keys are used in the steps below: `uncovered` (spec requirements with no home), `spec_rows_pending` and `changed_since` (spec changes not yet absorbed), `stale` (cited IDs the spec removed or lacks), `contracts_missing`, `legacy_layout`, `grow_triggers`, `package_docs` vs `packages_found`, `skills`, and `broken_fences` (fences that leave doc text inside a code block).

| Mode | When | Do |
|---|---|---|
| **New** | No `docs/architecture.md` | Full process below |
| **Extend** | The spec has requirements not yet covered, or `changed_since` lists requirements whose change the design hasn't absorbed | Grow check; place each one; update contracts; add decisions |
| **Revise** | A technical change with no spec change (a library fails, performance problems found in the build, a better data source) | New decision; supersede or revise the old one; update the affected sections and contracts |
| **Grow** | A Grow trigger fires, or the user wants a package split | Split into packages (see [Grow](#grow-single-package-to-multi-package)) |
| **Sync** | The code differs from the doc or a contract, or code exists with no doc | Document what *is*, mark gaps, then decide which side changes |

**Preconditions:** `docs/spec.md` must be `Approved`. If it's `Draft`, ask the user to approve it first. Read the brief for constraints (budget, platform, team) and the spec in full. In a codebase, read the existing structure, dependency files, and any existing ADRs.

**Old layout.** If `legacy_layout` or `contracts_missing` is non-empty, fix it in this round: `git mv` each `docs/architecture/<pkg>.md` to `docs/packages/<pkg>/architecture.md`, fix the links, and move each Interfaces section (root or package) into the matching `contract.md`, leaving a link.

**Asking.** Ask one question at a time, each with your recommendation and the default you'll take if the user has no view. Ask only what the user must decide: the shape, expensive-to-reverse choices, scope cuts. Infer the rest and list it under ASSUMPTIONS at the gate. With no live user (a headless run), don't invent answers: write the Draft, put the questions under Risks and open questions, and leave it at Draft.

## The Process (New Mode)

```
READ ─→ SHAPE ─→ COMPONENTS ─→ CONTRACTS ─→ DECISIONS ─→ WRITE ─→ [user approves] ─→ pipeline-design
```

### Step 1: Shape

Propose single package or multi-package, with a one-line reason from the table above. For multi-package, propose the package list with ids, the dependency direction, and the flows that cross packages before anything else; it's cheap to review and expensive to get wrong.

### Step 2: Components and Spec Coverage

Split the system into components (modules or packages). For each, give one responsibility, the spec requirement IDs it covers, and what it depends on.

- **Every live spec requirement is covered by at least one component.** Quality (`QR-`) and data (`DATA-`) requirements count. Cross-cutting ones may be covered under Cross-cutting concerns.
- **Dependencies point one way.** No cycles. If two components each need the other, they're one component, or a shared interface is missing.
- **Components should be small enough to explain in one sentence.** "Handles data and also the backtest" is two components.
- **Single package: one subfolder per component** (`src/<pkg>/<component>/`). Its `__init__` exports the component's contract, and other components import only from there. Grow is then a folder move.

### Step 3: Contracts

Write `docs/packages/<pkg>/contract.md`: the provider's promise to its consumers. Consumers read only this page, so it stands alone.

- **One `###` section per public symbol** (function, class, or a type consumers see), headed `### <id>.<symbol>: <title>`. `<id>` is the package id. In a single package it is the component id, with sections grouped under `## <component>` (multi-package contracts drop that level and link the `architecture.md` beside them). The ID survives Grow, because the component id becomes the package id.
- **Each section:** the signature in the project's language, then **Invariants** (shapes, ranges, guarantees), **Errors** (what fails and how it's reported), and **Used by** (consuming components or packages, plus `PL-NN` IDs once those pipelines exist).
- **Contract first:** the contract is defined before either side is built. **The provider owns it.**
- **Public only, ≤ 1 page.** Helpers, modules and call order belong in the package's architecture or its `pipelines.md`. A retired symbol collapses to one line under `## Retired`: `- ~~stats.foo: Title~~ Retired YYYY-MM-DD: reason`.

````markdown
# [pkg] — Contract

**Package:** [pkg] · **Status:** Draft · **Last updated:** YYYY-MM-DD · **Architecture:** [../../architecture.md](../../architecture.md)

## stats

### stats.estimate_cov: Covariance estimate
`def estimate_cov(returns: Returns, *, method: CovMethod = "sample") -> Cov`
- **Invariants:** N×N for T×N input; symmetric; positive semi-definite
- **Errors:** `ValueError` if T < 2 or the input contains NaN
- **Used by:** portfolio
````

### Step 4: Technical Decisions

Make the choices the spec deliberately left open: language and versions, key libraries, storage, deployment, data sources, model approach. For each significant one:

1. List 2-3 real options.
2. Check each against the requirements that constrain it. Data sources are checked against the spec's `DATA-` requirements; model approaches against the model-quality criteria and baseline.
3. Recommend one with a reason. **Ask the user** (see *Asking*) about decisions that are expensive to reverse or that they may have opinions on: language, framework, paid services, infrastructure.

Record each as a decision (`AD-NN`) in the template format. Small, easily reversed choices (a formatting tool) go in the tech stack table without a decision entry.

**Route steps to installed skills.** `dt status` lists the project's other skills under `skills`, and your context lists any others. If one owns a step the design contains, such as a hypothesis test or a security review, the component that runs that step names the skill. Its contract takes what the skill needs: for a hypothesis test, the hypothesis, the statistic, the null construction and the data split. Don't design a replacement procedure. If the spec names a skill for a step, the design must route to it.

**If the repo already has ADRs** (for example `docs/decisions/` or `docs/adr/`), follow that convention instead: write the ADR files there and list them in the Decisions section with links.

### Step 5: Write the Architecture

**Single package → `docs/architecture.md`** (filled example in `examples.md`):

````markdown
# [Project Name] — Architecture

**Status:** Draft · **Shape:** Single package · **Last updated:** YYYY-MM-DD · **Spec:** [spec.md](spec.md)

## Overview
[2-4 sentences: how the system works end to end. Optionally one Mermaid flowchart.]

## Tech stack
| Area | Choice | Decision |
|---|---|---|
| Language | Python 3.12 | AD-01 |

## Components
| Component | Responsibility | Covers | Depends on |
|---|---|---|---|
| `env` | [one sentence] | ENV-01–ENV-04, QR-01 | `sim`, `reward` |

## Interfaces
See [packages/<pkg>/contract.md](packages/<pkg>/contract.md).

## Data
[Data and ML projects: sources chosen (with the DATA- IDs they satisfy), storage, data flow, training/evaluation setup. Other projects: data model and storage. Omit if trivial.]

## Cross-cutting concerns
[Errors, configuration, logging, testing approach, performance, security — how the QR- requirements are met. One or two lines each.]

## Project layout
```
src/<pkg>/<component>/   → one folder per component; __init__ exports its contract
tests/                   → folders only; files are planned in pipelines.md
```

## Decisions
### AD-01: [Title]
**Status:** Accepted · **Date:** YYYY-MM-DD · **Scope:** system
- **Context:** [The problem and the requirements that constrain it.]
- **Decision:** [What we chose.]
- **Alternatives:** [Option — why not.] [Option — why not.]
- **Consequences:** [What this makes easy, what it makes hard, what we must now live with.]

### AD-02: ~~[Old title]~~
**Status:** Superseded by AD-07 · YYYY-MM-DD — [one-line reason]

## Risks and open questions
- [Technical risk — mitigation, or the question and who answers it. One list for the whole system, live items only.]

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| YYYY-MM-DD | Initial architecture | spec.md | AD-01–AD-NN |
````

**Multi-package → root `docs/architecture.md`** uses the same header (`**Shape:** Multi-package`) with these sections instead:

- **Overview** with a system diagram of packages and data flow
- **Packages** table: package id, path, responsibility, Covers (spec IDs, coarse), depends on, link to `packages/<pkg>/architecture.md`
- **Dependency rules**: layering and allowed directions ("`core` imports nothing internal; `strategies` may import `core` and `data`, never `execution`"), and how they're enforced (an import linter, CI check)
- **Cross-package contracts**: one line per contract with a link to the provider's `packages/<pkg>/contract.md`
- **System pipelines**: one `### PL-NN: <title>` per flow that crosses packages (IDs from `python3 ../../scripts/dt.py next-id PL`). Each has a `**Trigger:** · **Covers:**` line and numbered steps `from → to: <pkg>.<symbol>`, naming the contract each hand-off goes through. No functions, no files: those belong in each package's `pipelines.md`.
- **Shared tech stack and tooling**, **Project layout** (package folders only), **Cross-cutting concerns**, **Decisions** (all of them, each scoped), **Risks and open questions**, **Changelog**

**Each package → `docs/packages/<pkg>/architecture.md`:** the single-package template minus Decisions and Changelog (they stay in the root). Header: `**Package:** <id> · **Status:** · **Last updated:** · **System:** [../../architecture.md](../../architecture.md)`. Its Components table lists modules; its Interfaces section links to `contract.md` beside it.

**Writing rules:**

- **Decision IDs are permanent; superseded decisions shrink.** `AD-NN` IDs are never reused or renumbered, and the heading is never deleted. A reversed decision collapses to its heading with the title struck, plus one status line: `**Status:** Superseded by AD-NN · date — reason`. Delete its Context, Decision, Alternatives and Consequences. The new decision's Context says what the old one chose and why that no longer holds. Then update every section that cited the old decision (tech stack, contracts, code comments, layout, risks) so that only the superseded line, the new decision and the Changelog mention it. `PL-NN` IDs are permanent too; a retired system pipeline collapses to `- ~~PL-NN: title~~ Retired YYYY-MM-DD: reason`.
- **Accepted decisions stay true.** When a new decision changes only part of an Accepted one, revise the old one instead of superseding it. Rewrite the sentences that are no longer true, in its Context as well as its Decision and Consequences, and point to the new decision for the part it now owns. "Two holdouts, one per study" becomes "one holdout per study; AD-26 sets the ranges". The old decision stays Accepted. Supersede only when its choice is reversed as a whole. Readers take an Accepted decision as current, so a stale count in one is a defect.
- **Shared decisions state a rule, not a roster.** A decision that later stages build on (where claims go, which modules may import a library, where runs are stored) is worded to stay true as stages join: "every module that makes a significance claim writes a `Claim`", not "`eda` and `backtest` write claims". Its Context cites the requirements that set the rule, not each one that uses it. The members and their per-stage details (claim families, importers, run folders, time budgets) are listed once, where they live: a component's row and Covers, a contract section, the storage layout, or that stage's own decision. A new stage adds its members there and cites the shared decision. Revise the shared decision only when its rule changes. If one already lists members, move them out the next time a round touches it.
- **Describe the design as it is now, not how it got here.** No process notes ("no code was built before this change"), no struck-through risks, no per-stage blocks of risks or notes. Git keeps the rest.
- **The Changelog has one row per round, one line long.** IDs are the new decisions, as ranges (`AD-12–AD-15`). Don't repeat the spec row's ID list. The exception is a spec row with no source file: copy its IDs with their marks (`AD-16; QR-03 (changed)`). Source names the source files of the spec rows the round absorbs, as `spec_rows_pending` lists them: usually one idea file, sometimes `brief.md`. Use `spec.md` when those rows have none, as in a first architecture written from the initial spec alone. `dt status` matches this Source (or, for a row with no source file, those IDs) against the spec's Changelog to decide which spec changes the design has absorbed. A row that doesn't cite them leaves `changed_since` stuck on those requirements.
- **Risks and open questions is one consolidated list.** Each round merges into it: add new risks, rewrite ones that changed, and delete ones that are resolved. Record a resolution in a decision or the Changelog, not as a struck-through risk.
- **Size to the project.** A proof of concept with three modules doesn't need a Cross-cutting section longer than its Components table. Omit sections that would only say "N/A". Pin versions for the language and key libraries, not every transitive dependency.
- **No requirements restated.** Reference spec IDs; don't copy their text.

### Step 6: Review Gate (CRITICAL)

Before presenting the Draft, run `dt status` again. `uncovered`, `changed_since` and `stale` should be empty, or each gap should be listed under Risks and open questions. `broken_fences`, `contracts_missing` and `legacy_layout` must be empty: for a broken fence, move lines added after a block's closing fence inside it and delete the stray fence. Also check two things by hand:

- A superseded decision is cited only by its own line, the decision that replaced it, and the Changelog.
- No Accepted decision, Overview sentence or contract contradicts a newer decision. Search for the counts, ranges and names this round changed.

After saving the Draft:

1. Summarize: the files written, the shape, the components (or packages), the decisions that need the user's attention, and any spec requirements that couldn't be covered.
2. List **ASSUMPTIONS:** the names, types, signatures and dependency directions you chose without asking. Then the open questions.
3. Ask the user to approve or request changes.
4. **STOP YOUR TURN.** Do not start pipelines, planning or code in the same turn.

**Handling the reply.** Requested edits are the whole turn, and nothing follows an approval. Approval is an unambiguous yes in the user's own words; a hedge ("looks fine I guess") is not approval, so ask what's still open.

| The user says | Do | Then |
|---|---|---|
| Approved, nothing to change | Set Status to `Approved` on the root and every package doc and contract touched, set `Proposed` decisions to `Accepted`, update the date. Offer to commit the approved docs; commit only on a yes | **Stop.** See below |
| Approved, with a change ("approved, but rename `sim` to `world`") | Make exactly that edit. If the user fully specified it and it changes no decision or contract (moving text, splitting files, renaming), set Approved. Otherwise keep Draft. | **Stop.** List what you changed |
| Changes requested | Edit, keep Draft | Repeat this gate |

**After approval, this skill is done.** Do not write pipelines, a file layout, a build plan, tasks, milestones, `docs/plan.md`, or code, even if the user says "go ahead" or "continue". Tell the user the architecture is approved and the next step is `pipeline-design`, then end the turn. "Go ahead" means start `pipeline-design`, never code. If the user brings a new idea or stage, that goes to `idea-refine`.

## Extend Mode

The spec gained requirements (usually from a specced idea) or changed some.

1. Take the `uncovered` and `changed_since` IDs and the `spec_rows_pending` rows from `dt status`. Read the idea file each row cites for context.
2. **Grow check.** Check every trigger, and say at the gate which (if any) fired. `grow_triggers` reports the measurable ones; judge the rest from the spec and idea file.
   - The new requirements bring a dependency stack the rest shouldn't carry (torch, gym).
   - A one-way dependency is worth enforcing (data must never import models, to prevent leakage).
   - A package exceeds ~3 pipelines or ~12 modules, or its docs no longer fit a 2,000-line agent context.
   - A part runs or deploys on its own (a paper-trading service).

   If one fires, propose Grow to the user (one question, with your recommendation) before placing anything.
3. For each requirement, choose: an existing component covers it (add the ID to Covers), an existing component grows (update its contract), or a new component is needed (add it and its contract section, check the dependency direction). Lines added to a code block (the storage or project layout) go inside it, before its closing fence.
4. Any new technical choice gets a new `AD-NN`. Then find every Accepted decision it touches: search the doc for the components, data, counts and names it changes.
   - It reverses an old choice → supersede the old decision, which collapses to its superseded line.
   - It changes part of an old choice → revise the old decision in place (see *Accepted decisions stay true*). Examples: a third holdout added to a decision that set up two, or a new caller of an interface that a decision said only one study uses.
   - It only adds a member to a set a shared decision governs (another claim family, another run folder) → add the member where the set is listed and cite the shared decision. Don't revise it (see *Shared decisions state a rule*).
5. Requirements *removed* from the spec: take their IDs out of Covers; if a component now covers nothing, propose removing it.
6. Consolidate: merge new risks into the one Risks list, and delete the risks this round resolved. Rewrite the Overview and any section still worded for an earlier stage so it describes the whole system. Every count, list and range the round changed is updated everywhere it appears: Overview, Covers cells (`claims` still covering "EDA-06, OOS-10" after later stages added 26 claim families), contracts (such as the kinds of test a log entry accepts), cross-cutting concerns (such as which claims a skill tests), section headings, and older decisions. That includes text the round didn't set out to touch. Search for stage lists ("Stages 2 and 3", "both studies"), superlatives the new parts falsify ("the top of the dependency chain") and "later stage" or "milestone" framing for stages that now exist. Delete notes on how the design got here, code comments included ("unchanged since the Snake stage", "Since the arena stage, …", "Older … files load into this form").
7. Add one one-line Changelog row that cites the source files of `spec_rows_pending` (see the Changelog writing rule). Set Status to Draft on every doc and contract changed, and run the Review Gate, highlighting only what changed.

## Revise Mode

A technical change with no spec change. Write a new decision whose Context explains what was learned ("the simulator is 40× too slow for QR-02 at 1M steps"). Then supersede the old decision if the new one reverses it, or revise it in place if the new one changes only part of it (Extend step 4). Update every section and contract the change touches (tech stack, components, Overview), and run the Review Gate. If a contract changes, list its consumers (its **Used by**): their pipelines and tasks need revisiting.

## Grow: Single Package to Multi-Package

When a Grow trigger fires or the user wants a split:

1. Write a decision (`AD-NN`, scope `system`) explaining why now: the trigger, and the new boundary, owner, runtime, or release need.
2. Propose the package list and dependency rules. Component ids become package ids where possible, so Covers entries and contract IDs (`stats.estimate_cov`) carry over unchanged.
3. Move each package's detail from `docs/architecture.md` into `docs/packages/<pkg>/architecture.md`, and each `## <component>` group of the old contract into `docs/packages/<pkg>/contract.md`. Rewrite the root as the system map.
4. Add System pipelines for the flows that now cross packages, each with a new ID from `dt next-id PL`. A package pipeline whose flow now crosses keeps its own `PL-NN` ID: it stays the segment of the package that owns its entry, and `pipeline-design` Grow marks it `**Part of:**` the new system pipeline. Name that source pipeline at the gate. Never give a system pipeline an ID a package pipeline already holds.
5. Change the header to `**Shape:** Multi-package`, add a Changelog row, and run the Review Gate. After approval, point to `pipeline-design` (Grow mode).

## Sync Mode

The code and the doc disagree, or there's code with no doc. Document what *is* first: components, dependencies, and contracts as built (a component's `__init__` exports are its contract). Then list each mismatch for the user and ask which way it resolves: update the doc to match the code (record a decision if it was a real choice), or keep the doc and plan a fix. Never silently rewrite the doc to match code that broke a dependency rule.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It's a proof of concept, it doesn't need an architecture" | It needs a short one. One page that names the contracts and the three choices that matter saves the rewrite. |
| "We'll need a monorepo eventually, so start with one" | Packages you don't need yet cost tooling, versioning, and boundary friction every day. Name the seams; split when a Grow trigger fires. |
| "It's one more component, no need for the Grow check" | No eval run ever entered Grow; it was never checked. Check the four triggers every Extend. |
| "Consumers can read the architecture for the API" | They then read internals too, and depend on them. The contract is the whole promise, on one page. |
| "The decision is obvious, no need to record it" | Obvious today, mysterious in six months. A three-line decision entry is enough. |
| "I'll pick the data vendor myself, it's a technical detail" | Paid services and data sources are expensive to reverse. Check them against DATA- requirements and ask the user. |
| "I'll just update the old decision with the new choice" | If the choice is reversed, the reason for the original, and why it changed, is lost. Supersede it: the new decision's Context records both, and the old one shrinks to one line. |
| "The old decision is still mostly right; the new one covers the change" | Readers trust an Accepted decision as written. If it says two holdouts and there are three, it's wrong. Revise the sentences that changed and point to the new decision. |
| "I'll keep the superseded decision in full for the record" | Git is the record. A full superseded decision gets read as current, and every round adds more of them. |
| "The user said go ahead, so I'll lay out the files and plan the build" | An approved architecture is where this skill stops. Pipelines and files are `pipeline-design`'s, with their own review. |

## Red Flags

- A spec requirement with no component covering it, a component covering nothing, a dependency cycle, or "depends on" lists that include everything
- Multi-package shape for a proof of concept, or a single package with several separately deployed parts
- Tech choices with no decision entry where reversing them would be expensive
- Decisions deleted, a reversed decision edited in place instead of superseded, superseded decisions kept in full or still cited elsewhere
- Struck-through risks, or a new Risks block per stage
- An Accepted decision, the Overview or a contract contradicted by a newer decision (a count, range or list it changed)
- A shared decision that lists each stage's members, or is revised in every round
- A Changelog row that doesn't cite the idea file of the spec rows it absorbed, leaving `changed_since` non-empty
- A step an installed skill owns, designed as a home-made procedure instead of routed to the skill
- A contract in prose only, a section with no Errors, internals in `contract.md`, or an Interfaces section that restates the contract
- A system pipeline that names functions or files; a Project layout that lists files; package docs still under `docs/architecture/`
- An Extend round with no Grow check
- Data sources or model types chosen without checking the spec's DATA- and model-quality requirements
- Pipelines, planning or code started in the same turn the architecture was written, or after it was approved

## Verification

Before pointing to `pipeline-design`:

- [ ] Spec is `Approved` and linked; the shape is recorded and justified
- [ ] `dt status` reports no uncovered, changed or stale requirements (or each gap is listed under Risks and open questions), no broken fences, no missing contracts and no legacy layout
- [ ] Dependency direction is one-way with no cycles; multi-package has written dependency rules and System pipelines for every cross-package flow
- [ ] Every package has a `contract.md` with one section per public symbol: signature, invariants, errors, used by
- [ ] Every expensive-to-reverse choice has an `AD-NN` entry with alternatives and consequences; in data and ML projects, sources and model approach are decisions checked against the spec's DATA- and model-quality requirements
- [ ] Extend: the Grow triggers were checked and reported at the gate
- [ ] Changes after the first approval: a one-line Changelog row citing the spec rows' source files, superseded decisions collapsed to one line with nothing else citing them, decisions changed in part revised (with the Overview and contracts), Risks consolidated, Status back to Draft until approved
- [ ] Steps owned by an installed skill are routed to it by name
- [ ] The gate listed ASSUMPTIONS and open questions; the turn ended after the Draft was saved; approval was an unambiguous yes in a later turn; nothing was designed past the architecture after approval

Read `examples.md` in this skill directory for a single-package proof of concept with its contract, and a multi-package platform with System pipelines.
