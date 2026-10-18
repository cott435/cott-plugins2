# gridload — Contract

**Package:** gridload · **Status:** Approved · **Last updated:** 2026-10-17 · **Architecture:** [../../architecture.md](../../architecture.md)

## ingest

### ingest.RawReadings: type
`@dataclass(frozen=True) class RawReadings: rows: pd.DataFrame  # hour, meter, kwh`
- **Invariants:** one row per (hour, meter); hours sorted; units not yet normalized
- **Used by:** PL-01

### ingest.Readings: type
`@dataclass(frozen=True) class Readings: load: pd.DataFrame  # hours × regions, kWh`
- **Invariants:** a meter counts only before its removal date; every value in kWh
- **Boundary:** profile · **Fixtures:** tests/contracts/ingest.Readings/ · **Cases:** one region's week
- **Used by:** PL-01, PL-02

### ingest.load_readings: Hourly readings per region
`def load_readings(regions: tuple[str, ...], start: date, end: date) -> Readings`
- **Invariants:** hours × regions; decommissioned meters kept until removal
- **Errors:** `KeyError` for an unknown region; `ValueError` if start > end
- **Boundary:** profile · **Fixtures:** tests/contracts/ingest.load_readings/ · **Cases:** one region's week
- **Used by:** profile; PL-01, PL-02

## profile

### profile.Profile: type
`@dataclass(frozen=True) class Profile: terms: pd.DataFrame; share: dict[str, float]  # region × term`
- **Invariants:** shares in [0, 1], summing to ≤ 1 per region
- **Boundary:** forecast · **Fixtures:** tests/contracts/profile.Profile/ · **Cases:** a planted daily sine
- **Used by:** PL-02

### profile.Report: type
`@dataclass(frozen=True) class Report: table: str; profile: Profile`
- **Invariants:** `table` lists every term in `profile`
- **Used by:** PL-02

### profile.fit_seasonality: Daily and weekly terms
`def fit_seasonality(readings: Readings, *, terms: int = 3) -> Profile`
- **Invariants:** one row per region; daily and weekly terms
- **Errors:** `ValueError` with under two weeks of readings
- **Used by:** PL-02
