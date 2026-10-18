---
name: architecture-design
description: Designs and maintains the project architecture (docs/architecture.md) and each package's contract (docs/packages/{pkg}/contract.md) - components, dependencies, interfaces and technical decisions, from a single package to a monorepo. Use when docs/spec.md is approved and no architecture exists, when new requirements need a home, when a technical decision must be made or reversed, when a package should split, or when the code has drifted from the design.
---

# Architecture Design

The architecture (`docs/architecture.md`) says **how** the spec gets built: components, their dependencies, the contracts between them, and the technical decisions (libraries, data sources, model types). Every requirement has a home and every significant choice a reason. Each package's public API is its own `docs/packages/<pkg>/contract.md`, so a consumer reads only that page.

**Not for:** what or why (`spec-writing`, `idea-refine`); pipelines, file layout and tasks (`pipeline-design`, `build-planning`); API style rules (`api-and-interface-design` if available).

It owns `docs/architecture.md`, each package's `contract.md` and, in a multi-package design, each package's `architecture.md`. It mints the `AD-NN` decision IDs, the System pipelines' `PL-NN` IDs, and the contract IDs `<id>.<symbol>`. It writes a decision's `**Probe:**` line, never `docs/probes.md` or `probes/` (`api-probe`'s).

`dt` means `python3 ../../scripts/dt.py`, relative to this skill's folder, run from the project root; write it out each call, never as a shell variable.

**Preconditions:** an `Approved` spec (else ask). Read the brief's constraints, the spec in full, and in a codebase its structure, dependencies and ADRs. Read the `docs/references.md` entries for the milestone in scope (references waiting: `reference-intake` first), and `docs/requests.md`, the user's own words: `requests_open` lists the ones the architecture must honour. Follow `../idea-refine/references/requests.md` for them and for every answer you get.

## Modes

Start with `dt status --skill architecture-design`. Take the mode, shape, gap keys and next `AD` and `PL` IDs from it, never from counting. Load the mode's file and only the references it names.

| Mode | When | Do |
|---|---|---|
| **New** | No `docs/architecture.md` | `references/new.md` |
| **Extend** | Uncovered or changed spec requirements | `references/extend.md` |
| **Revise** | A technical change with no spec change, probe results to fold in (`probes_answered`, `probes_failed`), a change another skill routed here (`routed_changes`), or the user's words the Approved architecture doesn't honour (`requests_open`) | `references/revise.md` |
| **Grow** | A Grow trigger fires, or the user wants a split | `references/grow.md` |
| **Sync** | Code and doc disagree, or code has no doc | `references/sync.md` |

**Old layout:** if `legacy_layout` or `contracts_missing` is non-empty, fix it this round, whatever the mode: `git mv` each `docs/architecture/<pkg>.md` to `docs/packages/<pkg>/architecture.md`, fix links, and move each Interfaces section into its `contract.md`, leaving a link.

**Asking.** One question at a time, with your recommendation and a default, only on what the user must decide: the shape, expensive-to-reverse choices, scope cuts. Infer the rest as ASSUMPTIONS. Headless: write the Draft with the questions under Risks and open questions, and leave Draft.

## Review Gate (CRITICAL)

Rerun `dt status`: `uncovered`, `changed_since` and `stale` empty, or each gap under Risks and open questions; `broken_fences` (move lines added after a closing fence inside it), `contracts_missing`, `legacy_layout` and `probes_failed` empty. `dt lint docs/` reports no errors. Check by hand that a superseded decision is cited only by its own line, its replacement and the Changelog, and that nothing Accepted contradicts a newer decision (search the counts, ranges and names changed).

Then:
1. Summarize: files, shape, components or packages, decisions needing attention, uncovered requirements, the **Your words** line (requests honoured and changed).
2. **ASSUMPTIONS** (names, types, signatures, dependency directions you chose), then open questions.
3. Ask the user to approve or request changes. **STOP YOUR TURN.**

Approval is an unambiguous yes in the user's words; a hedge ("looks fine I guess") is not, so ask what's open.

| The user says | Do | Then |
|---|---|---|
| Approved, nothing to change | 1. Run `dt probes`: each decision whose `**Probe:**` names a probe not Answered or Waived stays `Proposed`, with its Risks line. 2. Set `Approved` on every doc and contract touched, the other `Proposed` decisions to `Accepted`, the date; `dt route --done architecture-design` if `routed_changes` listed any. 3. Offer to commit; commit only on a yes | **Stop.** Next is `pipeline-design`, and `api-probe` for each probe with no entry yet |
| Approved, with a change | Make exactly that edit. Fully specified and changing no decision or contract: set Approved. Otherwise keep Draft | **Stop.** List what you changed |
| Changes requested | Edit, keep Draft | Repeat this gate |

After approval this skill is done: "go ahead" means `pipeline-design`, never layout, plans or code. A new idea goes to `idea-refine`.
