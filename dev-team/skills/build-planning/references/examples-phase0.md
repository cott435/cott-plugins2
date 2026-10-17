# Example: interface-first M1 (quant, single package)

PL-01 Load prices (`read_raw` → `apply_universe`, owner `data`) and PL-02 Covariance report (`load_prices` as PL-01 built, then `estimate_cov` → `clean_eigen` → `pca` → `write_report`, owner `stats`). Golden cases TC-01 (universe), TC-02 (MP cleaning), TC-03 (PCA). The contract has a `type` section for every `In → Out`: `data.RawPrices`, `data.Prices`, `stats.Returns`, `stats.Cov`, `stats.Factors`, `stats.CovReport`; `data.load_prices` carries a `**Boundary:**` line because PL-02 calls it.

```
wave 0  T01  interface
wave 1  spines T02 read_raw · T03 apply_universe · T04 estimate_cov · T05 clean_eigen · T06 pca · T07 write_report
        testers of T10 universe · T11 MP cleaning · T12 shrinkage · T13 PCA
wave 2  wiring T08 PL-01 · T09 PL-02 (on the load_prices fake); implementers of T10 ← T03 · T11 ← T05 · T12 ← T04 · T13 ← T06
wave 3  T14  system: PL-02 on the real PL-01
```

14 tasks, critical path 4 (T01 → T05 → T11 → T14, or any other four-task chain), 10 agents in wave 1, every spine and thicken XS or S. No fold: each step's spine is a real baseline worth testing alone.

```markdown
### M1-T01: M1 interface
**Package:** quant · **Step:** contract · **Kind:** interface · **Covers:** — · **Size:** S · **Mode:** solo
**Read:** PL-01, PL-02, data.RawPrices, data.Prices, stats.Returns, stats.Cov, stats.Factors, stats.CovReport, data.load_prices
**Acceptance:**
- [ ] Each type is code in `data/types.py` or `stats/types.py`; each `tests/contracts/<id>.<Type>/` sample validates against its schema
- [ ] Every step imports with its contract signature, body `raise NotImplementedError("<its spine task>")`; each `__init__.py` exports its contract
- [ ] The `data.load_prices` fake serves its fixtures
**Verify:** `pytest tests/contracts` · `scripts/check.sh gate`
**Depends on:** — · **Writes:** src/quant/data/**, src/quant/stats/**, tests/contracts/**

### M1-T05: clean_eigen spine (no cleaning)
**Package:** quant · **Step:** PL-02.clean_eigen · **Kind:** spine · **Covers:** — · **Size:** XS · **Mode:** solo
**Read:** PL-02, stats.Cov, stats.clean_eigen
**Acceptance:**
- [ ] `clean_eigen` returns its input on the stats.Cov sample; signature unchanged
**Verify:** `pytest tests/unit/quant -k clean_eigen` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/quant/stats/rmt.py, tests/unit/quant/test_rmt.py

### M1-T09: Wire PL-02
**Package:** quant · **Step:** PL-02 · **Kind:** wiring · **Covers:** QR-02 · **Size:** S · **Mode:** solo
**Read:** PL-02, data.load_prices
**Acceptance:**
- [ ] `python -m quant.stats cov-report --smoke` runs end to end on the `data.load_prices` fake; committed as PL-02's smoke test
- [ ] PL-02 pre-build sections replaced by a `dt layout` pointer
**Verify:** `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T04, M1-T05, M1-T06, M1-T07 · **Writes:** src/quant/stats/pipeline.py, src/quant/stats/__main__.py, tests/unit/quant/test_pl02_smoke.py

### M1-T11: Marchenko–Pastur cleaning
**Package:** quant · **Step:** PL-02.clean_eigen · **Kind:** thicken · **Covers:** STAT-03 · **Size:** XS · **Mode:** split
**Skills:** data-science
**Read:** PL-02, TC-02, STAT-03, stats.clean_eigen, stats.Cov
**Acceptance:**
- [ ] TC-02 passes: every cleaned eigenvalue ≤ the MP edge on pure noise; no cleaning stays selectable
**Verify:** `pytest tests/intent/quant tests/unit/quant -k rmt` · `scripts/check.sh gate`
**Depends on:** M1-T05 · **Writes:** src/quant/stats/rmt.py, tests/intent/quant/test_rmt.py, tests/unit/quant/test_rmt.py

### M1-T14: PL-02 on the real PL-01
**Package:** quant · **Step:** PL-02 · **Kind:** system · **Covers:** — · **Size:** XS · **Mode:** solo
**Read:** PL-01, PL-02, data.load_prices, TC-01, TC-02, TC-03
**Acceptance:**
- [ ] PL-02 calls the real `load_prices`; the fake stays for the contract tests
- [ ] Both smoke commands pass; TC-01–TC-03 pass on the real chain
**Verify:** `python -m quant.data load --smoke` · `python -m quant.stats cov-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T08, M1-T09, M1-T10, M1-T11, M1-T12, M1-T13 · **Writes:** src/quant/stats/pipeline.py
```

T11's tester starts in wave 1: it tests `clean_eigen` as T01 declares it and fails on `NotImplementedError("M1-T05")`. Its implementer follows its tester and T05, nothing else. Wiring T09 waits on PL-02's spines because its smoke runs them, but not on PL-01: the fake stands in.

The graph, excerpted (one row per `Depends on` other than on T01, 16, plus the mitigated edges):

```markdown
## Dependency graph
| From | To | Kind | Mitigated by |
|---|---|---|---|
| M1-T05 clean_eigen spine | M1-T04 estimate_cov spine | data | stats.Cov sample (M1-T01) |
| M1-T09 wire PL-02 | M1-T05 clean_eigen spine | code | none: the smoke runs it |
| M1-T09 wire PL-02 | M1-T08 wire PL-01 | call | data.load_prices fake (M1-T01) |
| M1-T11 MP cleaning | M1-T05 clean_eigen spine | code | none: thickens the same module |
| M1-T11 MP cleaning | M1-T12 shrinkage | data | stats.Cov sample (M1-T01): cleaning takes any Cov |
| M1-T14 system | M1-T09 wire PL-02 | file | none: swaps the fake in the entry M1-T09 wrote |
```

**Multi-package.** The same shape across packages: the interface task freezes each `**Boundary:**` symbol in its `**Fixtures:**` folder (one interface task per provider when one would pass M), spines run in every package at once, a consumer's wiring runs on the provider's fake, and the system task (one per system pipeline, `**Package:**` the owner of its first step, `**Reason:** system task`, `--pkg` on the gate) swaps in the real providers.
