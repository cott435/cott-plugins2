# Example: interface-first M1 (gridload, single package)

PL-01 Load meter readings (`read_raw` → `apply_registry`, owner `data`) and PL-02 Seasonality report (`load_readings` as PL-01 built, then `fit_seasonality` → `spectrum` → `deseason` → `write_report`, owner `profile`). Golden cases TC-01 (registry), TC-02 (flat spectrum), TC-03 (planted sine). The contract has a `type` section for every `In → Out`: `data.RawReadings`, `data.Readings`, `profile.Load`, `profile.Profile`, `profile.Spectrum`, `profile.SeasonalityReport`; `data.load_readings` carries a `**Boundary:**` line because PL-02 calls it.

```
wave 0  T01  interface
wave 1  spines T02 read_raw · T03 apply_registry · T04 fit_seasonality · T05 spectrum · T06 deseason · T07 write_report
        testers of T10 registry · T11 LS amplitudes · T12 Fourier seasonality · T13 seasonal removal
wave 2  wiring T08 PL-01 · T09 PL-02 (on the load_readings fake); implementers of T10 ← T03 · T11 ← T05 · T12 ← T04 · T13 ← T06
wave 3  T14  system: PL-02 on the real PL-01
```

14 tasks, critical path 4 (T01 → T05 → T11 → T14, or any other four-task chain), 10 agents in wave 1, every spine and thicken XS or S. Checkpoints after T01 (barrier) and T13, and the milestone exit after T14. No fold: each step's spine is a real baseline worth testing alone.

```markdown
### M1-T01: M1 interface
**Package:** gridload · **Step:** contract · **Kind:** interface · **Covers:** — · **Size:** S · **Mode:** solo
**Read:** PL-01, PL-02, data.RawReadings, data.Readings, profile.Load, profile.Profile, profile.Spectrum, profile.SeasonalityReport, data.load_readings
**Acceptance:**
- [ ] Each type is code in `data/types.py` or `profile/types.py`; each `tests/contracts/<id>.<Type>/` sample validates against its schema
- [ ] Every step and entry function imports and matches its contract signature (its body is the CR-02 stub naming its task; no test checks the body); each `__init__.py` exports its contract; `__main__.py` dispatches each trigger
- [ ] The `data.load_readings` fake passes its contract's cases, written as one test that takes the provider
**Verify:** `pytest tests/contracts` · `scripts/check.sh gate`
**Depends on:** — · **Writes:** src/gridload/data/**, src/gridload/profile/**, tests/contracts/**

### M1-T05: spectrum spine (raw periodogram)
**Package:** gridload · **Step:** PL-02.spectrum · **Kind:** spine · **Covers:** — · **Size:** XS · **Mode:** solo
**Read:** PL-02, profile.Load, profile.Profile, profile.spectrum
**Acceptance:**
- [ ] `spectrum` returns the raw periodogram of the residual on the profile.Load and profile.Profile samples; signature unchanged
**Verify:** `pytest tests/unit/gridload -k spectrum` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/gridload/profile/spectrum.py, tests/unit/gridload/test_spectrum.py

### M1-T09: Wire PL-02
**Package:** gridload · **Step:** PL-02 · **Kind:** wiring · **Covers:** QR-02 · **Size:** S · **Mode:** solo
**Read:** PL-02, data.load_readings
**Acceptance:**
- [ ] `python -m gridload.profile seasonality-report --smoke` runs end to end on the `data.load_readings` fake; committed as PL-02's smoke test, which checks the report's shape, not its values
**Verify:** `python -m gridload.profile seasonality-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T04, M1-T05, M1-T06, M1-T07 · **Writes:** src/gridload/profile/pipeline.py, tests/unit/gridload/test_pl02_smoke.py

### M1-T11: Least-squares amplitudes
**Package:** gridload · **Step:** PL-02.spectrum · **Kind:** thicken · **Covers:** STAT-03 · **Size:** XS · **Mode:** split
**Skills:** data-science
**Read:** PL-02, TC-02, STAT-03, profile.spectrum, profile.Profile
**Acceptance:**
- [ ] TC-02 passes: every fitted Fourier amplitude ≤ the flat-spectrum edge on pure noise; the raw periodogram stays selectable
**Verify:** `pytest tests/intent/gridload tests/unit/gridload -k spectrum` · `scripts/check.sh gate`
**Depends on:** M1-T05 · **Writes:** src/gridload/profile/spectrum.py, tests/intent/gridload/test_spectrum.py, tests/unit/gridload/test_spectrum.py

### M1-T14: PL-02 on the real PL-01
**Package:** gridload · **Step:** PL-02 · **Kind:** system · **Covers:** — · **Size:** XS · **Mode:** solo
**Read:** PL-01, PL-02, data.load_readings, TC-01, TC-02, TC-03
**Acceptance:**
- [ ] PL-02 calls the real `load_readings`; each fake's contract cases pass on the real provider
- [ ] Both smoke commands pass; TC-01–TC-03 pass on the real chain
**Verify:** `python -m gridload.data load --smoke` · `python -m gridload.profile seasonality-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T08, M1-T09, M1-T10, M1-T11, M1-T12, M1-T13 · **Writes:** src/gridload/profile/pipeline.py, tests/unit/gridload/test_load_readings_conformance.py
```

T11's tester starts in wave 1: it tests `spectrum` as T01 declares it and fails on `NotImplementedError("M1-T05")`. Its implementer follows its tester and T05, nothing else. Wiring T09 waits on PL-02's spines because its smoke runs them, but not on PL-01: the fake stands in. The `load_readings` cases are named in T08's acceptance too, since PL-01's wiring builds the real function, so a drift fails there before T14.

The graph, excerpted (one row per `Depends on` other than on T01, 16, plus the mitigated edges):

```markdown
## Dependency graph
| From | To | Kind | Mitigated by |
|---|---|---|---|
| M1-T05 spectrum spine | M1-T04 fit_seasonality spine | data | profile.Profile sample (M1-T01) |
| M1-T09 wire PL-02 | M1-T05 spectrum spine | order | none: integration: the smoke runs it |
| M1-T09 wire PL-02 | M1-T08 wire PL-01 | call | data.load_readings fake (M1-T01) |
| M1-T11 LS amplitudes | M1-T05 spectrum spine | code | none: thickens the same module |
| M1-T11 LS amplitudes | M1-T12 Fourier seasonality | data | profile.Profile sample (M1-T01): the spectrum takes any Profile |
| M1-T14 system | M1-T09 wire PL-02 | file | none: swaps the fake in the entry M1-T09 wrote |
| M1-T14 system | M1-T08 wire PL-01 | order | none: integration: swaps in the real PL-01 |
```

**Multi-package.** The same shape across packages: the interface task freezes each `**Boundary:**` symbol in its `**Fixtures:**` folder (one interface task per provider when one would pass M), spines run in every package at once, a consumer's wiring runs on the provider's fake, and the system task (one per system pipeline, `**Package:**` the owner of its first step, `**Reason:** system task`, `--pkg` on the gate) swaps in the real providers.

**Library classes, a helper folder, a real-collaborator case (LeafLab M1).** PL-01's `SingleCropSet` and `SmallCnn` are step rows behind the `make_dataset` and `make_model` factories (`pipeline-design`'s example), so each gets a spine like any step; `train` owns the folder `core/train/`:

```markdown
### M1-T03: SingleCropSet spine (200 synthetic leaves)
**Package:** leaflab · **Step:** PL-01.SingleCropSet · **Kind:** spine · **Covers:** — · **Size:** XS · **Mode:** solo
**Read:** PL-01, core.Dataset
**Acceptance:**
- [ ] `SingleCropSet(seed=0)` satisfies `core.Dataset`: 200 synthetic leaves, a fixed split; same seed, same split
**Verify:** `pytest tests/unit/leaflab -k singlecrop` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** src/leaflab/singlecrop/dataset.py, tests/unit/leaflab/test_singlecrop.py

### M1-T06: train spine (epoch loop, CSV log)
… **Depends on:** M1-T01 · **Writes:** src/leaflab/core/train/**, tests/unit/leaflab/test_train.py
```

`evaluate`'s spine is its whole behavior and has a golden case, so it is one fold task: `**Kind:** thicken`, `**Mode:** split`, `**Reason:** fold: spine is the whole behavior`. Wiring PL-01 depends on the seven spines and that fold, never on the CNN thicken, so the random-guess `SmallCnn` runs the smoke. TC-04 (the CNN beats the logistic baseline on held-out leaves) needs the real CNN, so it is the system task's acceptance; LeafLab has no fake, and that case alone gives M1 a system task.
