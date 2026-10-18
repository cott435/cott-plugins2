# gridload — Pipelines

**Package:** gridload · **Status:** Approved · **Last updated:** 2026-10-17 · **Contract:** [contract.md](contract.md)

## PL-01: Ingest readings
**Entry:** `src/gridload/pipelines/pl01_ingest.py::run_ingest` · **Trigger:** `python -m gridload ingest`
**Covers:** LOAD-01, LOAD-02

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `read_export` | ingest | dates → RawReadings | read a synthetic export | LOAD-01 |
| 2 | `clean_units` | ingest | RawReadings → Readings | every meter in kWh, none removed | LOAD-02 |

## PL-02: Seasonality report
**Entry:** `src/gridload/pipelines/pl02_seasonality.py::run_seasonality` · **Trigger:** `python -m gridload seasonality`
**Covers:** PROF-01, PROF-02

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `load_readings` | ingest | regions, dates → Readings | PL-01 as built | LOAD-01 |
| 2 | `fit_seasonality` | profile | Readings → Profile | daily term only | PROF-01 |
| 3 | `write_report` | profile | Profile → Report | print table | PROF-02 |

Layout: `src/gridload/pipelines/` holds one entry module per pipeline; `src/gridload/pipeline.py` re-exports them.
