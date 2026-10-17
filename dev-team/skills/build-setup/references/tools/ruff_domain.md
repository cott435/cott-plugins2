# Ruff: domain rules (time series, dates, NumPy, pandas)

Related: [ruff_core.md](ruff_core.md) · [pandera.md](pandera.md)

| | |
|---|---|
| **What it covers** | Naive datetimes (`DTZ`), legacy and removed NumPy APIs (`NPY`), pandas pitfalls (`PD`) |
| **Speed** | Instant, same as the rest of Ruff |
| **Config** | Add `"DTZ"`, `"NPY"`, `"PD"` to `select` (`{{domain_rules}}` in the template). Don't list `PD901`: Ruff removed it |
| **When** | From the tech stack ADs: `DTZ` for any code handling timestamps, `NPY` with NumPy, `PD` with pandas. Extend adds a family when a milestone brings the library |
| **Hook tier** | Per-edit and Stop gate, same as core Ruff |

> **Verified** in `design/tooling-verification.md` (2026-10-16): the families run clean on the sample's pandas and NumPy code.

---

## DTZ: naive datetimes (very relevant for meter data)

**DTZ005 `datetime.now()` without tz**
```python
ts = datetime.now()                       # DTZ005 -> datetime.now(tz=UTC)
```

**DTZ007 `strptime` without `%z`**
```python
datetime.strptime(s, "%Y-%m-%d %H:%M")    # DTZ007
```
Why: naive timestamps mix local time, UTC and the meter's own clock. Joins and hourly alignment go wrong around DST changes.

## NPY: NumPy

**NPY002 legacy global RNG**
```python
np.random.seed(0)
x = np.random.rand(10)   # NPY002 -> rng = np.random.default_rng(0)
```
Why: global state makes forecasts and simulations hard to reproduce, especially with parallel work.

**NPY201 NumPy 2.0 removals**
```python
np.float_(1.0)           # NPY201 -> np.float64
np.NaN                   # NPY201 -> np.nan
```
Why: these raise `AttributeError` on NumPy 2.

## PD: pandas-vet

**PD002 `inplace=True`**
```python
df.dropna(inplace=True)  # PD002 -> df = df.dropna()
```
Why: `inplace` rarely saves memory and breaks method chaining. It also causes SettingWithCopy confusion.

**PD011 `.values`**
```python
arr = df["kwh"].values   # PD011 -> .to_numpy()
```
Why: `.values` may return an array or an extension type, depending on dtype. `.to_numpy()` is explicit.


## Related rules from other families that matter for data code

- **B905**: `zip(readings, timestamps)` without `strict=True`. See [ruff_core.md](ruff_core.md#b-flake8-bugbear-likely-bugs).
- **S301**: `pickle.load` on models or datasets. See [ruff_core.md](ruff_core.md#s-flake8-bandit-security).
- **RUF012 / B006**: shared mutable state between runs.

## What Ruff can't catch for data work

Ruff can't tell if a column has the wrong dtype or if readings are negative. That is runtime validation: see [pandera.md](pandera.md). With pandas, add `pandas-stubs` to the dev group too (mypy strict needs it; see [mypy.md](mypy.md)).
