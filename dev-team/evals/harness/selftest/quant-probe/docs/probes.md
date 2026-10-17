# Quant Lab — Probes

**Last updated:** 2026-10-15

### PB-01: Sharadar delivers what the DATA- requirements need
**Folder:** `probes/PB-01-sharadar/` · **Hash:** — · **Status:** Ready · **Milestones:** M1 · **Last run:** —
- **Question:** Does Sharadar give 2006+ history, delisted members with permanent ids, raw and adjusted prices we can tell apart, and point-in-time S&P 500 membership?
- **Informs:** AD-04 · DATA-01, DATA-02 · data.RawPrices, data.Prices
- **Docs read (2026-10-15):** sharadar.com/docs/stocks; sharadar.com/blog/posts/sharadar-stock-prices-fund-prices-and-adjustments
- **Spends:** API calls on the existing subscription only
- **Checks:** table below
- **Verdict:** —
- **Caveats:** licensed data: samples keep the shape with values replaced; real rows stay in out/

| Check | What | How | Pass | Runner | Result |
|---|---|---|---|---|---|
| C2 | History depth | Earliest SEP date for IBM, KO, XOM, JNJ, PG | ≤ 2006-01-03 (DATA-01 target); fail if > 2011-01-03 | user | — |
| C3 | Delisted members | delisted_members.csv against TICKERS | each with `isdelisted = Y`, a permaticker and prices to its delisting date; reused tickers give two permatickers (DATA-02) | user | — |
| C4 | Raw vs adjusted | AAPL around its 4-for-1 split on 2020-08-31: `closeunadj/close` | 4 before and 1 after; record that no raw open, high or low exist (DATA-01) | user | — |
| C6 | S&P 500 membership | SP500 table: earliest record | ≤ 2006-01-03 (DATA-02's point-in-time universe) | user | — |
