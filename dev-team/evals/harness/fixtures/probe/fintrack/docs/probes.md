# FinTrack — Probes

**Last updated:** 2026-10-15

### PB-01: Frankfurter returns daily EUR→USD rates for past dates
**Folder:** `probes/PB-01-fx-rates/` · **Hash:** HASH01 · **Status:** Answered · pass · 2026-10-15 · **Milestones:** M1 · **Last run:** 2026-10-15T17:20:00Z
- **Question:** Does Frankfurter return a daily EUR→USD rate for any past date, and what happens on weekends?
- **Informs:** AD-07 · FX-01 · fx.Rate
- **Docs read (2026-10-15):** frankfurter.dev/docs
- **Spends:** nothing (no key)
- **Checks:** table below
- **Verdict:** pass — rates back to 1999; weekends carry Friday's rate
- **Caveats:** stdlib urllib, no retries

| Check | What | How | Pass | Runner | Result |
|---|---|---|---|---|---|
| C1 | Past rate | `/2024-03-15?from=EUR&to=USD` | a rate for that date | agent | pass: 1 rate |
| C2 | Weekend | `/2024-03-16?from=EUR&to=USD` | a rate, dated the Friday before | agent | pass: dated 2024-03-15 |

### PB-02: Canary Credit Union's OFX export parses into imports.Statement
**Folder:** `probes/PB-02-ofx-export/` · **Hash:** HASH02 · **Status:** Ready · **Milestones:** M1 · **Last run:** —
- **Question:** Does the credit union's OFX export carry a date, amount, description and a stable id per row?
- **Informs:** AD-08 · IMP-01, DATA-02 · imports.Statement, ledger.BankTxn
- **Docs read (2026-10-15):** ofx.net/downloads/OFX 2.2.pdf (STMTTRN)
- **Spends:** nothing; the user downloads the export with their online-banking password
- **Checks:** table below
- **Verdict:** —
- **Caveats:** reads out/statement.ofx, which the user saves there

| Check | What | How | Pass | Runner | Result |
|---|---|---|---|---|---|
| C1 | Rows parse | STMTTRN blocks in out/statement.ofx | every row has DTPOSTED, TRNAMT, NAME, FITID | user | — |
| C2 | Ids stable | FITIDs of two exports a month apart | the overlapping rows keep their FITID (DATA-02) | user | — |
