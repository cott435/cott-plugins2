# Example: interface-first M1 (gridload, single package)

PL-01 Load meter readings (`read_raw` → `apply_registry`, owner `data`) and PL-02 Seasonality report (`load_readings` as PL-01 built, then `fit_seasonality` → `spectrum` → `deseason` → `write_report`, owner `profile`). Golden cases TC-01 (registry), TC-02 (flat spectrum), TC-03 (planted sine). The contract has a `type` section for every `In → Out`: `data.RawReadings`, `data.Readings`, `profile.Load`, `profile.Profile`, `profile.Spectrum`, `profile.SeasonalityReport`; `data.load_readings` carries a `**Boundary:**` line because PL-02 calls it.

```
wave 0  T01  types
wave 1  contract tests T02 data · T03 profile
wave 2  spines T04 read_raw · T05 apply_registry · T06 fit_seasonality · T07 spectrum · T08 deseason · T09 write_report
        testers of T12 registry · T13 LS amplitudes · T14 Fourier seasonality · T15 seasonal removal (during the review)
wave 3  wiring T10 PL-01 · T11 PL-02 (on the load_readings fake); implementers of T12 ← T05 · T13 ← T07 · T14 ← T06 · T15 ← T08
wave 4  T16  system: PL-02 on the real PL-01
```

16 tasks, critical path 5 (T01 → T03 → T07 → T13 → T16, or any other five-task chain), 10 agents in wave 2, every spine and thicken XS or S. Checkpoints after T03 (barrier, reviewing T01–T03) and T15, and the milestone exit after T16. No fold: each step's spine is a real baseline worth testing alone.

```markdown
### M1-T01: M1 types
**Package:** gridload · **Step:** contract · **Kind:** interface · **Covers:** — · **Size:** S · **Mode:** solo
**Read:** PL-01, PL-02, data.RawReadings, data.Readings, profile.Load, profile.Profile, profile.Spectrum, profile.SeasonalityReport, data.load_readings
**Acceptance:**
- [ ] Each type is code in `data/types.py` or `profile/types.py`; the gate's type check passes
- [ ] Every step and entry function imports and matches its contract signature (its body is the CR-02 stub naming its task; no test checks the body); each `__init__.py` exports its contract; `__main__.py` dispatches each trigger
**Verify:** `scripts/check.sh gate`
**Depends on:** — · **Writes:** src/gridload/data/**, src/gridload/profile/**

### M1-T02: data contract tests
**Package:** gridload · **Step:** contract · **Kind:** interface · **Covers:** — · **Size:** S · **Mode:** solo
**Read:** data.RawReadings, data.Readings, data.load_readings
**Acceptance:**
- [ ] Each `tests/contracts/data.<Type>/` sample validates against its schema
- [ ] The `data.load_readings` fake passes its contract's cases, written as one test that takes the provider
**Verify:** `pytest tests/contracts -k data` · `scripts/check.sh gate`
**Depends on:** M1-T01 · **Writes:** tests/contracts/data.RawReadings/**, tests/contracts/data.Readings/**, tests/contracts/data.load_readings/**

### M1-T07: spectrum spine (raw periodogram)
**Package:** gridload · **Step:** PL-02.spectrum · **Kind:** spine · **Covers:** — · **Size:** XS · **Mode:** solo
**Read:** PL-02, profile.Load, profile.Profile, profile.spectrum
**Acceptance:**
- [ ] `spectrum` returns the raw periodogram of the residual on the profile.Load and profile.Profile samples; signature unchanged
**Verify:** `pytest tests/unit/gridload -k spectrum` · `scripts/check.sh gate`
**Depends on:** M1-T03 · **Writes:** src/gridload/profile/spectrum.py, tests/unit/gridload/test_spectrum.py

### M1-T11: Wire PL-02
**Package:** gridload · **Step:** PL-02 · **Kind:** wiring · **Covers:** QR-02 · **Size:** S · **Mode:** solo
**Read:** PL-02, data.load_readings
**Acceptance:**
- [ ] `python -m gridload.profile seasonality-report --smoke` runs end to end on the `data.load_readings` fake; committed as PL-02's smoke test, which checks the report's shape, not its values
**Verify:** `python -m gridload.profile seasonality-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T02, M1-T06, M1-T07, M1-T08, M1-T09 · **Writes:** src/gridload/profile/pipeline.py, tests/unit/gridload/test_pl02_smoke.py

### M1-T13: Least-squares amplitudes
**Package:** gridload · **Step:** PL-02.spectrum · **Kind:** thicken · **Covers:** STAT-03 · **Size:** XS · **Mode:** split
**Skills:** data-science
**Read:** PL-02, TC-02, STAT-03, profile.spectrum, profile.Profile
**Acceptance:**
- [ ] TC-02 passes: every fitted Fourier amplitude ≤ the flat-spectrum edge on pure noise; the raw periodogram stays selectable
**Verify:** `pytest tests/intent/gridload tests/unit/gridload -k spectrum` · `scripts/check.sh gate`
**Depends on:** M1-T03, M1-T07 · **Writes:** src/gridload/profile/spectrum.py, tests/intent/gridload/test_spectrum.py, tests/unit/gridload/test_spectrum.py

### M1-T16: PL-02 on the real PL-01
**Package:** gridload · **Step:** PL-02 · **Kind:** system · **Covers:** — · **Size:** XS · **Mode:** solo
**Read:** PL-01, PL-02, data.load_readings, TC-01, TC-02, TC-03
**Acceptance:**
- [ ] PL-02 calls the real `load_readings`; each fake's contract cases pass on the real provider
- [ ] Both smoke commands pass; TC-01–TC-03 pass on the real chain
**Verify:** `python -m gridload.data load --smoke` · `python -m gridload.profile seasonality-report --smoke` · `scripts/check.sh gate`
**Depends on:** M1-T10, M1-T11, M1-T12, M1-T13, M1-T14, M1-T15 · **Writes:** src/gridload/profile/pipeline.py, tests/unit/gridload/test_load_readings_conformance.py
```

T03 freezes `profile`'s four types the same way. T13's tester starts once T01 and T03 land, while the interface review runs: it tests `spectrum` as T01 declares it and fails on `NotImplementedError("M1-T07")`. Its implementer follows its tester and T07, nothing else. Wiring T11 waits on PL-02's spines because its smoke runs them, but not on PL-01: the fake stands in. The `load_readings` cases are named in T10's acceptance too, since PL-01's wiring builds the real function, so a drift fails there before T16.

The graph, excerpted (one row per `Depends on` other than on an interface task, 16, plus the mitigated edges):

```markdown
## Dependency graph
| From | To | Kind | Mitigated by |
|---|---|---|---|
| M1-T07 spectrum spine | M1-T06 fit_seasonality spine | data | profile.Profile sample (M1-T03) |
| M1-T11 wire PL-02 | M1-T07 spectrum spine | order | none: integration: the smoke runs it |
| M1-T11 wire PL-02 | M1-T10 wire PL-01 | call | data.load_readings fake (M1-T02) |
| M1-T13 LS amplitudes | M1-T07 spectrum spine | code | none: thickens the same module |
| M1-T13 LS amplitudes | M1-T14 Fourier seasonality | data | profile.Profile sample (M1-T03): the spectrum takes any Profile |
| M1-T16 system | M1-T11 wire PL-02 | file | none: swaps the fake in the entry M1-T11 wrote |
| M1-T16 system | M1-T10 wire PL-01 | order | none: integration: swaps in the real PL-01 |
```

**Multi-package.** The same shape across packages: each provider's types task, then its contract tasks, freeze each `**Boundary:**` symbol in its `**Fixtures:**` folder, spines run in every package at once, a consumer's wiring runs on the provider's fake, and the system task (one per system pipeline, `**Package:**` the owner of its first step, `**Reason:** system task`, `--pkg` on the gate) swaps in the real providers.

**Library classes, a helper folder, a real-collaborator case (LeafLab M1).** PL-01's `SingleCropSet` and `SmallCnn` are step rows behind the `make_dataset` and `make_model` factories (`pipeline-design`'s example), so each gets a spine like any step; `train` owns the folder `core/train/`. Every contract type sits in `core`, so M1-T01 is the one interface task, types and contract tests together:

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

**A long run (rl M1).** TC-26, the trained snake beats both baselines over 200 games, needs an hour of real training, so it leaves the system task M1-T31 for a task of its own:

```markdown
### M1-T32: Snake DQN against both baselines
**Package:** rllab · **Step:** PL-01 · **Kind:** system · **Covers:** EVAL-04 · **Size:** XS · **Mode:** solo
**Reason:** long run
**Read:** PL-01, TC-26, QR-01, train.TrainSettings
**Acceptance:**
- [ ] A 50,000-step feasibility run's curve passes the scripted snake's mean in its last third; else TEST-WRONG with the curve, and no full run
- [ ] Within QR-01's 60 minutes, TC-26 passes on the full run
**Verify:** `python -m rllab train --env snake` · `scripts/check.sh gate`
**Depends on:** M1-T31 · **Writes:** tests/unit/rllab/test_snake_long_run.py
```
