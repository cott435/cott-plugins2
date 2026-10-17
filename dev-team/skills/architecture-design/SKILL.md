---
name: architecture-design
description: Designs and maintains the project architecture (docs/architecture.md) and each package's contract (docs/packages/{pkg}/contract.md) - components, dependencies, interfaces and technical decisions, from a single package to a monorepo. Use when docs/spec.md is approved and no architecture exists, when new requirements need a home, when a technical decision must be made or reversed, when a package should split, or when the code has drifted from the design.
---

# Architecture Design

The architecture (`docs/architecture.md`) says **how** the spec gets built: components, their dependencies, the contracts between them, and the technical decisions (libraries, data sources, model types). Every requirement has a home and every significant choice a reason. Each package's public API is its own `docs/packages/<pkg>/contract.md`, so a consumer reads only that page.

**Not for:** what or why (`spec-writing`, `idea-refine`); pipelines, file layout and tasks (`pipeline-design`, `build-planning`); API style rules (`api-and-interface-design` if available).

`dt` means `python3 ../../scripts/dt.py`, relative to this skill's folder, run from the project root. Examples: `examples.md` (a single-package proof of concept), `references/examples-multi.md`, `references/examples-modes.md`.

## Modes

Start with `dt status --skill architecture-design`. Take the mode, shape, gap keys and next `AD` and `PL` IDs from it, never from counting.

| Mode | When | Do |
|---|---|---|
| **New** | No `docs/architecture.md` | The process below |
| **Extend** | Uncovered or changed spec requirements | `references/modes.md` |
| **Revise** | A technical change with no spec change | `references/modes.md` |
| **Grow** | A Grow trigger fires, or the user wants a split | `references/modes.md` |
| **Sync** | Code and doc disagree, or code has no doc | `references/modes.md` |

**Preconditions:** an `Approved` spec (else ask). Read the brief's constraints, the spec in full, and in a codebase its structure, dependencies and ADRs. Read the `docs/references.md` entries for the milestone in scope (references waiting: `reference-intake` first).

**Old layout:** if `legacy_layout` or `contracts_missing` is non-empty, fix it this round (`references/modes.md`).

**Asking.** One question at a time, with your recommendation and a default, only on what the user must decide: the shape, expensive-to-reverse choices, scope cuts. Infer the rest as ASSUMPTIONS. Headless: write the Draft with the questions under Risks and open questions, and leave Draft.

## Process (New)

```
READ ─→ SHAPE ─→ COMPONENTS ─→ CONTRACTS ─→ DECISIONS ─→ WRITE ─→ [user approves] ─→ pipeline-design
```

**1. Shape.** Read `references/shape.md`, propose single or multi-package with a one-line reason, and record it in the header. Multi-package: first propose the package ids, dependency direction and cross-package flows.

**2. Components.** Each: one responsibility in a sentence, the spec IDs it covers, what it depends on. Every live requirement (`QR-`, `DATA-` included) is covered, cross-cutting ones under Cross-cutting concerns. Dependencies point one way; two components needing each other are one, or miss an interface. Single package: one subfolder per component, its `__init__` exporting its contract.

**3. Contracts.** Read `references/contracts.md`. One section per public symbol: functions with signature, Invariants, Errors and Used by; each type passed between steps as a `type` section (`### stats.Cov: type`). A symbol consumed across components or packages gets a `**Boundary:**` line naming its fixture cases.

**4. Decisions.** For each significant open choice (language, libraries, storage, deployment, data sources, model approach): 2-3 real options checked against the requirements that constrain them (`DATA-`; model criteria and baseline), and a recommendation. Ask about expensive-to-reverse ones. Record each as `AD-NN`, citing an informing reference by `RF-NN`, never its path. Small reversible choices go only in the tech stack table. A repo with its own ADRs keeps that convention.

**Route steps to installed skills.** Each skill on the stage's `**Skills:**` line, and any installed skill owning a step (a hypothesis test, a security review), is named on the component running the step, whose contract takes what the skill needs. Never design a replacement procedure.

**5. Write** from `references/templates.md`, following `references/writing-rules.md`.

## Review Gate (CRITICAL)

Rerun `dt status`: `uncovered`, `changed_since` and `stale` empty, or each gap under Risks and open questions; `broken_fences` (move lines added after a closing fence inside it), `contracts_missing` and `legacy_layout` empty. `dt lint docs/` reports no errors. Check by hand that a superseded decision is cited only by its own line, its replacement and the Changelog, and that nothing Accepted contradicts a newer decision (search the counts, ranges and names changed).

Then:
1. Summarize: files, shape, components or packages, decisions needing attention, uncovered requirements.
2. **ASSUMPTIONS** (names, types, signatures, dependency directions you chose), then open questions.
3. Ask the user to approve or request changes. **STOP YOUR TURN.**

Approval is an unambiguous yes in the user's words; a hedge ("looks fine I guess") is not, so ask what's open.

| The user says | Do | Then |
|---|---|---|
| Approved, nothing to change | Set `Approved` on every doc and contract touched, `Proposed` decisions to `Accepted`, the date. Offer to commit; commit only on a yes | **Stop.** Next is `pipeline-design` |
| Approved, with a change | Make exactly that edit. Fully specified and changing no decision or contract: set Approved. Otherwise keep Draft | **Stop.** List what you changed |
| Changes requested | Edit, keep Draft | Repeat this gate |

After approval this skill is done: "go ahead" means `pipeline-design`, never layout, plans or code. A new idea goes to `idea-refine`.
