# Mini — Architecture

**Status:** Approved · **Shape:** Single package · **Last updated:** 2026-10-17 · **Spec:** [spec.md](spec.md)

## Overview
One Python package, `mini`, with one component: `core` summarizes numbers.

## Tech stack
| Area | Choice | Decision |
|---|---|---|
| Language | Python 3.11, standard library only | AD-01 |

## Components
| Component | Responsibility | Covers | Depends on |
|---|---|---|---|
| `core` | Read and summarize numbers | SUM-01, SUM-02 | — |

## Interfaces
See [packages/mini/contract.md](packages/mini/contract.md).

## Project layout
```
src/mini/
tests/
```

## Decisions
### AD-01: Python 3.11 single package, managed with uv
**Status:** Accepted · **Date:** 2026-10-17 · **Scope:** system
- **Context:** A smoke-test project.
- **Decision:** One package, uv, no dependencies.
- **Alternatives:** None worth the cost.
- **Consequences:** One lock file.

## Risks and open questions

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| 2026-10-17 | Initial architecture | brief.md | AD-01 |
