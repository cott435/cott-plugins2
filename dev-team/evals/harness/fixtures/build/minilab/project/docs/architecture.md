# Minilab — Architecture

**Status:** Approved · **Shape:** Multi-package · **Last updated:** 2026-10-17 · **Spec:** [spec.md](spec.md)

## Overview
`mdata` turns price CSVs into aligned daily prices. `risk` turns those prices into returns, rolling volatility and a JSON risk report. `risk` reads prices only through `mdata.load_prices`.

## Packages
| Package | Path | Responsibility | Covers | Depends on | Doc |
|---|---|---|---|---|---|
| `mdata` | packages/mdata | Read, validate and align daily prices | DATA-01–DATA-04, QR-01 | — | [mdata](packages/mdata/architecture.md) |
| `risk` | packages/risk | Returns, volatility, drawdown, report | RISK-01–RISK-05, REP-01, QR-01 | `mdata` | [risk](packages/risk/architecture.md) |

## Dependency rules
- `mdata` imports nothing internal.
- `risk` imports only `mdata`'s contract: `mdata.types` and `mdata.load_prices` (late-bound, so a fake can stand in), never its step modules.

## Cross-package contracts
- `mdata.load_prices` → `mdata.Prices`, provided by `mdata`, used by `risk` (PL-02). [Contract](packages/mdata/contract.md)

## System pipelines
None: PL-02 calls PL-01 through `mdata.load_prices`; PL-03 calls PL-02 through `risk.vol_series`.

## Project layout
```
packages/mdata/src/mdata/  packages/risk/src/risk/
tests/intent/<pkg>/  tests/unit/<pkg>/  tests/fixtures/<pkg>/  tests/contracts/  tests/system/
```

## Shared tech stack and tooling
| Area | Choice | Decision |
|---|---|---|
| Language | Python 3.10+, standard library only | AD-01 |
| Tests | pytest, `pythonpath` over both `src/` folders | AD-02 |

## Decisions
### AD-01: Standard library only
**Status:** Accepted · **Date:** 2026-10-17 · **Scope:** system
- **Context:** Inputs are a few small CSV files (brief, Constraints).
- **Decision:** `csv`, `math`, `statistics`, `dataclasses`; no pandas or numpy.
- **Alternatives:** pandas — a heavy dependency for a few hundred rows.
- **Consequences:** Types are frozen dataclasses of tuples; the code is explicit about windows and denominators.

### AD-02: One test tree, no install step
**Status:** Accepted · **Date:** 2026-10-17 · **Scope:** system
- **Context:** Two packages in one repo, built by several agents at once.
- **Decision:** pytest's `pythonpath` lists `packages/*/src`; tests live under `tests/` by role and package.
- **Alternatives:** A uv workspace — needs a lock and network for no gain here.
- **Consequences:** `python -m pytest` from the root is the whole test run.

## Risks and open questions
- Missing dates are filled with the previous close; a long gap would invent prices, so DATA-04 makes it an error.

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| 2026-10-17 | Initial architecture | spec.md | AD-01, AD-02 |
