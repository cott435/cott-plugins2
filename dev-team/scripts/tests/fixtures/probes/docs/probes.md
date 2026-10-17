# Quant Lab — Probes

**Last updated:** 2026-10-17

### PB-01: Sharadar delivers raw and adjusted closes we can tell apart
**Folder:** `probes/PB-01-sharadar-prices/` · **Hash:** 5c7242e5 · **Status:** Answered · pass · 2026-10-16 · **Milestones:** M1 · **Last run:** 2026-10-16T18:02:11Z
- **Question:** Are SEP's `close` and `closeunadj` the adjusted and raw closes, and does its history reach 2006?
- **Informs:** AD-03 · DATA-01, DATA-02 · data.RawPrices
- **Docs read (2026-10-15):** sharadar.com/docs/stocks
- **Spends:** API calls on the existing subscription
- **Checks:** table below
- **Verdict:** pass
- **Caveats:** licensed data: samples keep shape, values replaced; reuse the paging, not the plumbing

| Check | What | How | Pass | Runner | Result |
|---|---|---|---|---|---|
| C1 | Raw vs adjusted | AAPL around its 2020-08-31 split | closeunadj/close = 4 ± 0.1% before the split | user | pass: 4.0; only the close is raw |
| C2 | History depth | Earliest SEP date for IBM | ≤ 2006-01-03 (DATA-01) | user | pass: 1998-01 |

### PB-02: FRED serves daily 3-month T-bill rates back to 2006
**Folder:** `probes/PB-02-fred-rates/` · **Hash:** bdf9f525 · **Status:** Ready · **Milestones:** M2 · **Last run:** —
- **Question:** Does FRED's DTB3 series give daily rates from 2006 on, under terms that allow local storage?
- **Informs:** AD-04 · PORT-02 · portfolio.Comparison
- **Docs read (2026-10-17):** fred.stlouisfed.org/docs/api/fred/series_observations.html
- **Spends:** nothing (free key)
- **Checks:** table below
- **Verdict:** —
- **Caveats:** stdlib urllib, no retries

| Check | What | How | Pass | Runner | Result |
|---|---|---|---|---|---|
| C1 | Series exists | Public CSV, no key | DTB3 header row returned | agent | — |
| C2 | History | /series/observations with your key | First observation ≤ 2006-01-03 | user | — |
| C3 | Terms | FRED terms of use page | Local storage allowed | user (manual) | — |

## Retired
- ~~PB-03: Tiingo lists delisted tickers~~ Retired 2026-10-16: Tiingo dropped as a candidate
