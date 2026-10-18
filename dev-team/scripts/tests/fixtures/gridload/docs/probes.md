# GridLoad — Probes

**Last updated:** 2026-10-17

### PB-01: The weather API's hourly history reaches 2015
**Folder:** `probes/PB-01-weather-history/` · **Hash:** — · **Status:** Draft · **Milestones:** M2 · **Last run:** —
- **Question:** Does the hourly history reach 2015-01-01, and are its timestamps local time or UTC?
- **Informs:** AD-02 · LOAD-01
- **Spends:** nothing (free key)
- **Checks:** table below
- **Verdict:** —

| Check | What | How | Pass | Runner | Result |
|---|---|---|---|---|---|
| C1 | History depth | Earliest hour for one station | ≤ 2015-01-01 | user | — |
| C2 | Time zone | Compare a known DST change | Timestamps stated as UTC | user | — |
