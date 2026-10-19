# mini — Pipelines

**Package:** mini · **Status:** Approved · **Last updated:** 2026-10-17 · **Contract:** [contract.md](contract.md)

## PL-01: Summarize numbers
**Entry:** `src/mini/pipeline.py::run_summary` · **Trigger:** `python -m mini summarize`
**Covers:** SUM-01, SUM-02

| # | Step | Owner | In → Out | Spine version | Covers |
|---|---|---|---|---|---|
| 1 | `summarize` | core | Numbers → Summary | count and total, no mean | SUM-01, SUM-02 |

### Entry sketch (pre-build — removed by spine task)
```python
def run_summary(path: Path) -> Summary:
    numbers = Numbers(tuple(json.loads(path.read_text())["numbers"]))
    summary = summarize(numbers)
    print(summary)
    return summary
```

## Open questions

## Retired
