# pandera: DataFrame validation (runtime)

Related: [ruff_domain.md](ruff_domain.md)

| | |
|---|---|
| **What it does** | Validates a DataFrame against a schema (columns, dtypes, value checks) at runtime |
| **Speed** | Runs each time you call `validate`, in proportion to the data size. Not a lint step |
| **Config** | In your code, not `pyproject.toml` |
| **Hook tier** | None. It is code your project calls. Test it with pytest; validate at data boundaries (ingest), not inside hot loops |

> **Not verified:** the API was not run in the tooling verification; pandera wasn't installed there. Check against the installed version before writing a schema.

## What it catches

```python
import pandera as pa

schema = pa.DataFrameSchema({
    "date":  pa.Column("datetime64[ns]"),
    "close": pa.Column(float, pa.Check.gt(0)),
    "volume": pa.Column(int, pa.Check.ge(0)),
})

schema.validate(df)
# SchemaError: Column 'close' failed validator: greater_than(0)
```
Why: bad vendor data (negative meter readings, missing columns, strings where numbers should be) breaks a model quietly, with no exception, just wrong output. Ruff and type checkers can't see this; they never see your data.

## When build-setup adds it

Only when a DataFrame crosses a contract (an `<pkg>.<symbol>` in `contract.md` takes or returns one). Then `pandera` is a runtime dependency of that package, and the schema is part of the contract.

## Where to put it

- Validate right after loading raw data.
- Put one schema per data shape in its own module, with a test that a good frame passes and a bad frame raises.
- In tests, use `schema.validate(df, lazy=True)` to see all failures at once.
