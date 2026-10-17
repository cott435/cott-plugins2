# Example domains

**Status:** Fixed · **Last updated:** 2026-10-17

The skills' worked examples never use the eval projects' domains, so an eval run plans its project rather than copying an example. The evals plan a quant research platform and an RL lab (`evals/harness/scenarios.json`); the examples use the two domains below instead. Every example that spans skills uses the same names, so they line up from brief to plan.

## Banned in `skills/**`

Terms from the eval scenarios that no skill text may contain: PCA, principal component, Marchenko, random-matrix, Ledoit, shrinkage, covariance, min-variance, minimum-variance, risk parity, HRP, hierarchical risk, factor model, market factor, delist, survivorship, corporate action, point-in-time universe, ticker, equity, equities, stock, portfolio, backtest, Sharadar, EODHD, TFT, temporal fusion, null-hypothesis, null hypothesis, quant, Snake, fish, foraging, predator, prey, DQN, PPO, policy gradient, reinforcement, RL lab, episode, gym, self-play, co-evolution. (`dt`'s own tests and fixtures in `scripts/tests/` may keep them; agents never load those.)

## Replacement for the quant examples: GridLoad

An electricity-demand forecasting lab for one utility's service area.

| Lesson the quant example taught | GridLoad version |
|---|---|
| A data-dependent brief: does usable data exist, at what cost | Hourly meter readings by region from the utility's own export, plus weather from a public weather API |
| Survivorship / delisted names | Decommissioned meters missing from today's registry; history must include them |
| Corporate actions | Meter replacements and unit changes (kWh vs MWh) |
| Point-in-time universe | The active-meter registry as of a date |
| Look-ahead leak | Using weather actuals where only the forecast was known at the time |
| PCA to remove the market factor | Removing the seasonal profile (daily and weekly Fourier terms) |
| Marchenko–Pastur known-answer case | A planted daily sine is recovered by the decomposition; pure noise leaves a flat spectrum |
| Sample covariance, then shrinkage | Seasonal-naive forecast, then gradient-boosted forecast |
| Min-variance / risk parity baselines | Equal reserve split before an optimized reserve allocation |
| `stats.estimate_cov`, PL-02 Covariance report | `profile.fit_seasonality`, PL-02 Seasonality report |
| Classical before ML, ML must beat it | Seasonal-naive before boosting; boosting must beat it on held-out weeks |
| `null-hypothesis-testing` stage skill | `significance-check`, a project skill that tests whether a feature's lift is real |
| `data-analysis` stage skill | `profile-report` |
| `frontend-design` for the viz app | unchanged (a TypeScript + React dashboard over a Python backend) |
| Reference files `market_decomposition.py`, `tft_dataset.py`, `tft_targets.py` | `seasonal_profile.py` (fit on the full sample: a deliberate look-ahead caveat), `gbm_windows.py`, `holiday_calendar.py` |
| Sharadar / EODHD in api-probe | A public weather API: does it return hourly history back to 2015, in local time or UTC |
| Stages: data → structure & portfolios → features & ML → forecasting & agents | ingest & clean → seasonality & baselines → features & boosting → day-ahead forecasts & reserve planning |

## Replacement for the rl examples: LeafLab

A small image-classification lab for plant-leaf diseases, built to learn ML by building.

| Lesson the rl example taught | LeafLab version |
|---|---|
| Environments 1–3, each teaching a concept | Datasets 1–3: a clean single-crop set, a multi-crop set with label noise, a field-photo set with distribution shift |
| `core.Env`, `core.Agent` Protocols | `core.Dataset`, `core.Model` Protocols |
| Snake grid world | The single-crop leaf set |
| DQN, then PPO | Logistic regression on features, then a small CNN |
| Episodes, steps, rewards | Epochs, batches, loss |
| Multi-seed runs, evaluation against baselines | Multi-seed runs, evaluation against a majority-class and a logistic baseline |
| Replay recording and viewer | Prediction gallery and confusion-matrix viewer |
| Self-play / multi-agent non-stationarity | Training on one field site, evaluating on another |
