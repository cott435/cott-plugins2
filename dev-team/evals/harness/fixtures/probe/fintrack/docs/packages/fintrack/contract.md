# fintrack — Contract

**Status:** Approved · **Last updated:** 2026-10-15

### ledger.BankTxn: type
- **Fields:** id: str, account: str, date: date, amount: Cents (outflow > 0), description: str, pending: bool, pending_id: str | None
- **Invariants:** id stable across syncs; a posted row names its pending row
- **Used by:** —

### ledger.Account: type
- **Fields:** id: str, name: str, kind: str, balance: Cents
- **Invariants:** one per linked account
- **Used by:** —

### fx.Rate: type
- **Fields:** day: date, currency: str, usd: Decimal
- **Invariants:** one per currency per day
- **Used by:** —

### imports.Statement: type
- **Fields:** account: str, rows: list[ledger.BankTxn]
- **Invariants:** rows sorted by date
- **Used by:** —
