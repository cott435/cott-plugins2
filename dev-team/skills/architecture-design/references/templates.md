# Architecture templates

Read when writing `docs/architecture.md` or a package's `architecture.md`. Filled examples: `examples-new.md`, `examples-new-multi.md`. The writing rules are in `writing-rules.md`.

**Single package → `docs/architecture.md`**:

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
| `train` | [one sentence] | TRN-01–TRN-04, QR-01 | `batches`, `loss` |

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
- **Consequences:** [What this makes easy and what it makes hard, in the code and the product.]
- **Probe:** [Only on a decision that picks an external API, vendor or dataset: `PB-NN — question`, or `none — why the docs settle it` (`decisions.md`).]

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
- **System pipelines**: one `### PL-NN: <title>` per flow that crosses packages (IDs from `dt next-id PL`). Each has a `**Trigger:** · **Covers:**` line, a `**Purpose:**` line (one sentence: what running it gives the user) and numbered steps `from → to: <pkg>.<symbol>`, naming the contract each hand-off goes through. No functions, no files: those belong in each package's `pipelines.md`.
- **Shared tech stack and tooling**, **Project layout** (package folders only), **Cross-cutting concerns**, **Decisions** (all of them, each scoped), **Risks and open questions**, **Changelog**

**Each package → `docs/packages/<pkg>/architecture.md`:** the single-package template minus Decisions and Changelog (they stay in the root). Header: `**Package:** <id> · **Status:** · **Last updated:** · **System:** [../../architecture.md](../../architecture.md)`. Its Components table lists modules; its Interfaces section links to `contract.md` beside it.
