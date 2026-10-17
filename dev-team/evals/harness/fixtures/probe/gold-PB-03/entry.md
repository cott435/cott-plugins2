### PB-03: Plaid Transactions returns what ledger.BankTxn assumes
**Folder:** `probes/PB-03-plaid-transactions/` · **Hash:** — · **Status:** Draft · **Milestones:** M1 · **Last run:** —
- **Question:** Do both institutions link in Sandbox with 730 days, and does `/transactions/sync` return outflows as positive amounts, a pending flag, unique ids and 12 months of history?
- **Informs:** AD-04 · DATA-01, DATA-02, SYNC-02 · ledger.BankTxn, ledger.Account
- **Docs read (2026-10-15):** plaid.com/docs/api/institutions; plaid.com/docs/api/products/transactions; plaid.com/docs/sandbox
- **Spends:** nothing (Sandbox Items are free); links with AD-04's settings (Transactions, 730 days)
- **Checks:** table below
- **Verdict:** —
- **Caveats:** stdlib urllib, no retries; Sandbox data, not the user's banks

| Check | What | How | Pass | Runner | Result |
|---|---|---|---|---|---|
| C2 | Institutions supported | `/institutions/search` with products transactions | both found | user | — |
| C3 | Items link | `/sandbox/public_token/create` with `days_requested` 730, then exchange | both link | user | — |
| C4 | History depth | `/transactions/sync`, every page; earliest date per account | ≥ 12 months on a spending account (DATA-01) | user | — |
| C5 | ledger.BankTxn fields | share of rows with each field; sign of non-income amounts; id uniqueness | outflows > 0 on ≥ 90%; date, account, description, pending, id on 100%; ids unique (DATA-02) | user | — |
| C8 | Balances | `/accounts/get` | every account has `balances.current` | user | — |
