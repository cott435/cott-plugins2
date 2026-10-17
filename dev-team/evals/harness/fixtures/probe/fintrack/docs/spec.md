# FinTrack — Spec

**Status:** Approved · **Last updated:** 2026-10-15 · **Brief:** [brief.md](brief.md)

## Features

### Bank data (`DATA`)
**Serves:** Goal 1, Goal 2

**Requirements**
- **DATA-01** Each spending account's history is imported back 12 months when the bank keeps it.
  - Given a newly linked account, when the first sync finishes, then transactions from 12 months back are in the ledger.
- **DATA-02** Every transaction carries a date, an account, a description, a pending flag and a stable id.
  - Given two syncs a day apart, when the same posted transaction comes back, then its id is unchanged.

### Sync (`SYNC`)
**Serves:** Goal 1

**Requirements**
- **SYNC-01** Accounts sync once a day.
  - Given a linked account, when a day passes, then new transactions appear without a manual step.
- **SYNC-02** A pending transaction is replaced by its posted one.
  - Given a pending charge, when it posts, then the ledger shows one posted row linked to the pending one.

### Currency (`FX`)
**Serves:** Goal 3

**Requirements**
- **FX-01** A foreign-currency amount is shown in dollars at that day's rate.
  - Given a purchase in euros, when it is shown, then its dollar amount uses the rate of its date.

### Imports (`IMP`)
**Serves:** Goal 2

**Requirements**
- **IMP-01** A credit union that can't be linked is imported from its OFX export.
  - Given an OFX file, when it is imported, then its transactions are in the ledger like linked ones.

### Quality
- **QR-01** Running costs stay under $5 a month.
  - Given a month of daily syncs, when the bill comes, then it is under $5.

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| 2026-10-15 | Initial spec | brief.md | DATA-01, DATA-02, SYNC-01, SYNC-02, FX-01, IMP-01, QR-01 |
