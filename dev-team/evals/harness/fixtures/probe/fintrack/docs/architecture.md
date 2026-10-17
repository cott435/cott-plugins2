# FinTrack — Architecture

**Status:** Approved · **Shape:** Single package · **Last updated:** 2026-10-15 · **Spec:** [spec.md](spec.md)

## Overview
One Python package, `fintrack`: `service` pulls transactions from the bank-linking service, `imports` reads OFX exports, `fx` converts currencies, and `ledger` stores and categorizes.

## Tech stack
| Area | Choice | Decision |
|---|---|---|
| Language | Python 3.12 | AD-01 |
| Bank linking | Plaid Transactions | AD-04 |
| Currency rates | Frankfurter | AD-07 |
| Credit union | OFX export | AD-08 |

## Components
| Component | Responsibility | Covers | Depends on |
|---|---|---|---|
| `service` | Link accounts and sync transactions | DATA-01, DATA-02, SYNC-01, SYNC-02, QR-01 | `ledger` |
| `imports` | Import OFX exports | IMP-01 | `ledger` |
| `fx` | Daily currency rates | FX-01 | — |
| `ledger` | Store and categorize transactions | DATA-02 | `fx` |

## Interfaces
See [packages/fintrack/contract.md](packages/fintrack/contract.md).

## Decisions
### AD-01: Python 3.12 single package, managed with uv
**Status:** Accepted · **Date:** 2026-10-15 · **Scope:** system
- **Context:** Solo developer, one laptop and a small server.
- **Decision:** One package, uv.
- **Alternatives:** Poetry — slower.
- **Consequences:** One lock file.

### AD-04: Plaid Transactions on the Trial plan, 730 days requested
**Status:** Proposed · **Date:** 2026-10-15 · **Scope:** service
**Probe:** PB-03 — does Plaid Transactions return what ledger.BankTxn assumes (sign, pending links, stable ids, pagination), linked with 730 days?
- **Context:** DATA-01 needs 12 months of history; Plaid's docs promise up to 24 and let a link ask for up to 730 days, fixed per Item.
- **Decision:** Plaid Transactions via `/transactions/sync`, Items linked with `days_requested` 730.
- **Alternatives:** Manual exports — what the user does today.
- **Consequences:** The sign convention, pending links and id stability that ledger.BankTxn assumes are unconfirmed until PB-03 is answered (Risks).

### AD-07: Frankfurter for daily currency rates
**Status:** Accepted · **Date:** 2026-10-15 · **Scope:** fx
**Probe:** PB-01 — does Frankfurter return a daily EUR→USD rate for past dates?
- **Context:** PB-01 (2026-10-15): daily rates back to 1999 for EUR and GBP, weekends carry Friday's rate.
- **Decision:** Frankfurter's `/{date}` endpoint, no key.
- **Alternatives:** A paid FX API — not needed.
- **Consequences:** Weekend purchases use Friday's rate.

### AD-08: Canary Credit Union through its OFX export
**Status:** Proposed · **Date:** 2026-10-15 · **Scope:** imports
**Probe:** PB-02 — does Canary Credit Union's OFX export parse into imports.Statement?
- **Context:** The credit union isn't on the bank-linking service.
- **Decision:** Import its monthly OFX export.
- **Alternatives:** Typing it in — what the user does today.
- **Consequences:** Unconfirmed until PB-02 is answered (Risks).

## Risks and open questions
- Plaid's sign convention, pending links and id stability: PB-03.
- Canary Credit Union's OFX export: PB-02, waiting on the user's download.

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| 2026-10-15 | Initial architecture | brief.md | AD-01, AD-04, AD-07, AD-08 |
