# Extend, Revise, Grow and Sync

Read when `dt status --skill architecture-design` reports one of these modes. Each ends at the Review Gate in `../SKILL.md`. Examples: `examples-modes.md`.

## Extend

The spec gained requirements (usually from a specced idea) or changed some.

1. Take the `uncovered` and `changed_since` IDs and the `spec_rows_pending` rows from `dt status`. Read the idea file each row cites for context.
2. **Grow check.** Check every trigger, and say at the gate which (if any) fired. `grow_triggers` reports the measurable ones; judge the rest from the spec and idea file.
   - The new requirements bring a dependency stack the rest shouldn't carry (torch, gym).
   - A one-way dependency is worth enforcing (data must never import models, to prevent leakage).
   - A package exceeds ~3 pipelines or ~12 modules, or its docs no longer fit a 2,000-line agent context, or `dt lint` warns `grow-size` on one of them.
   - A part runs or deploys on its own (a paper-trading service).

   If one fires, propose Grow to the user (one question, with your recommendation) before placing anything.
3. For each requirement, choose: an existing component covers it (add the ID to Covers), an existing component grows (update its contract), or a new component is needed (add it and its contract section, check the dependency direction). Lines added to a code block (the storage or project layout) go inside it, before its closing fence.
4. Any new technical choice gets a new `AD-NN`. Then find every Accepted decision it touches: search the doc for the components, data, counts and names it changes.
   - It reverses an old choice → supersede the old decision, which collapses to its superseded line.
   - It changes part of an old choice → revise the old decision in place (`writing-rules.md`, *Accepted decisions stay true*). Examples: a third holdout added to a decision that set up two, or a new caller of an interface that a decision said only one study uses.
   - It only adds a member to a set a shared decision governs (another claim family, another run folder) → add the member where the set is listed and cite the shared decision. Don't revise it (`writing-rules.md`, *Shared decisions state a rule*).
5. Requirements *removed* from the spec: take their IDs out of Covers; if a component now covers nothing, propose removing it.
6. Consolidate: merge new risks into the one Risks list, and delete the risks this round resolved. Rewrite the Overview and any section still worded for an earlier stage so it describes the whole system. Every count, list and range the round changed is updated everywhere it appears: Overview, Covers cells (`claims` still covering "EDA-06, OOS-10" after later stages added 26 claim families), contracts (such as the kinds of test a log entry accepts), cross-cutting concerns (such as which claims a skill tests), section headings, and older decisions. That includes text the round didn't set out to touch. Search for stage lists ("Stages 2 and 3", "both studies"), superlatives the new parts falsify ("the top of the dependency chain") and "later stage" or "milestone" framing for stages that now exist. Delete notes on how the design got here, code comments included ("unchanged since the Snake stage", "Since the arena stage, …", "Older … files load into this form").
7. Add one one-line Changelog row that cites the source files of `spec_rows_pending` (`writing-rules.md`). Set Status to Draft on every doc and contract changed, and run the Review Gate, highlighting only what changed.

## Revise

A technical change with no spec change. Write a new decision whose Context explains what was learned ("the simulator is 40× too slow for QR-02 at 1M steps"). Then supersede the old decision if the new one reverses it, or revise it in place if the new one changes only part of it (Extend step 4). Update every section and contract the change touches (tech stack, components, Overview), and run the Review Gate. If a contract changes, list its consumers (its **Used by**): their pipelines and tasks need revisiting. A frozen interface's type, samples and fake change with it, in a new interface task Replan adds (a `contract-change` edge).

## Grow: single package to multi-package

When a Grow trigger fires or the user wants a split:

1. Write a decision (`AD-NN`, scope `system`) explaining why now: the trigger, and the new boundary, owner, runtime, or release need.
2. Propose the package list and dependency rules. Component ids become package ids where possible, so Covers entries and contract IDs (`stats.estimate_cov`) carry over unchanged.
3. Move each package's detail from `docs/architecture.md` into `docs/packages/<pkg>/architecture.md`, and each `## <component>` group of the old contract into `docs/packages/<pkg>/contract.md`. Rewrite the root as the system map.
4. Add System pipelines for the flows that now cross packages, each with a new ID from `dt next-id PL`. A package pipeline whose flow now crosses keeps its own `PL-NN` ID: it stays the segment of the package that owns its entry, and `pipeline-design` Grow marks it `**Part of:**` the new system pipeline. Name that source pipeline at the gate. Never give a system pipeline an ID a package pipeline already holds.
5. Change the header to `**Shape:** Multi-package`, add a Changelog row, and run the Review Gate. After approval, point to `pipeline-design` (Grow mode).

## Sync

The code and the doc disagree, or there's code with no doc. Document what *is* first: components, dependencies, and contracts as built (a component's `__init__` exports are its contract). Then list each mismatch for the user and ask which way it resolves: update the doc to match the code (record a decision if it was a real choice), or keep the doc and plan a fix. Never silently rewrite the doc to match code that broke a dependency rule.

## Old layout

When `legacy_layout` or `contracts_missing` is non-empty: `git mv` each `docs/architecture/<pkg>.md` to `docs/packages/<pkg>/architecture.md`, fix links, and move each Interfaces section into its `contract.md`, leaving a link.
