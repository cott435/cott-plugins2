# Milestone shape: interface, step spines, wiring, system, long runs

Read when writing a milestone's tasks. Examples: `examples-phase0.md`.

A milestone is planned from its pipelines' steps: each step has one owner, one module and typed `In → Out`, so it is the unit of work. The plan freezes every boundary between steps first, so the work on both sides starts at once instead of queueing behind one spine. Every task carries `**Kind:**`:

```
## Phase 0: Interface              types (solo, first)           types, signatures, stubs, exports, __main__
                                   contract, one per component   samples, fakes, doubles, contract tests
## Phase 1: Step spines            spine, one per step           each writes its owner module only
## Phase 2: Wiring and thicken     wiring, one per pipeline      its entry module, smoke test
                                   thicken (tasks.md)            each after its step's spine
## Phase 3: System                 system (solo, last)           fakes swapped for real providers
                                   long run, after it            real training, within a time budget
```

Phases name the usual waves; the dependency graph (`tasks.md` step 9) decides what may start. Tester halves of split tasks start once the interface tasks their task depends on land, while the interface review runs; no code starts before it passes.

**a. Interface tasks** (`**Kind:** interface`, `**Step:** contract`, solo, first): a types task, then one contract task per component, freezing every boundary between tasks. What they freeze, the fakes and stubs, and what frozen means: `interface.md`.

**b. Step spines** (`**Kind:** spine`, `**Step:** PL-NN.<function>`, solo, XS or S). One per new step, library class rows included, each depending only on interface tasks: it replaces the stub naming it with the step's spine version from the step table. `Writes:` its owner module, or its owner folder as one glob (`src/leaflab/core/train/**`), and its unit test, nothing else; steps sharing one module share one spine task. A provider waiting on a probe gets no spine: its stand-in row (`pipeline-design`'s `steps.md`) is built instead, and the real spine goes in the milestone the probe's Answer unblocks. Acceptance: the step's input sample gives a schema-valid output; the signature is unchanged. A step another pipeline provides (`PL-01 as built`) gets no spine.

**c. Wiring** (`**Kind:** wiring`, `**Step:** PL-NN`, solo). One per new pipeline: the entry function in the pipeline's own entry module (the layout's, never one module shared by several pipelines), so wiring tasks run side by side, and its smoke test. `__main__.py` is the types task's. It depends on the spines and fold tasks of the steps its pipeline builds, since the smoke runs them (`order`, `none: integration: …`), never on their thicken tasks, and never on a step it only calls (`PL-01 as built`, another pipeline or package): that call runs on its boundary's fake, so wiring PL-02 never waits for PL-01. Acceptance: the smoke command runs end to end on the contract tasks' fakes and doubles, and is committed as the pipeline's smoke test, which checks that the pipeline runs and the shape of what it writes, never a value a thicken or a real provider sets (a real episode, a trained model: the system task's, or its long run's). `dt prebuild-clear` replaces the pipeline's pre-build sections once the wiring lands; that is dt's step, not an acceptance bullet.

**d. System task** (`**Kind:** system`, solo, last). It swaps each fake for the real provider, in the entry its wiring wrote (a `file` edge), and runs every smoke command and the milestone's golden cases on the real chain. Its `Writes:` name each fake's conformance test (`tests/unit/<pkg>/test_<symbol>_conformance.py`), and its acceptance reads "each fake's contract cases pass on the real provider". Its row to the provider's wiring is `order` · `none: integration: swaps in the real <provider>`. System tasks never depend on each other, but for a long run on its own (e): each builds its golden-case stores from fixtures, and a case that needs another system pipeline's real output joins that pipeline's system task. Multi-package: one per new system pipeline, `**Step:**` that pipeline, `**Package:**` the owner of its first step, `**Reason:** system task`. Single package: `**Step:**` the calling pipeline. A golden case that needs real collaborators (a thickened step, a class's real upgrade) is the system task's acceptance, never the wiring's, so wiring waits only on what c names. A milestone with no fake and no such case has no system task.

**e. Long run** (`**Kind:** system`, `**Reason:** long run`). Real training, a sweep, or any run longer than a few minutes never goes in the system task: it is a task of its own after it, holding the golden cases that need it (beats both baselines). Its acceptance names a time budget (the QR that sets one) and starts with a feasibility run: a short run whose curve shows the target in reach, else it escalates TEST-WRONG with that curve before any full run.

**Folds** keep the task count down. The pipeline's wiring depends on a fold task, so a fold is allowed only where that task is XS (`tasks.md` step 5) and the critical path doesn't grow. Record each on its task as `**Reason:** fold: <rule>`:
- A step with a golden case whose spine and thicken are both in the milestone, or whose spine version is its whole behavior, may be one task that replaces the stub itself, `**Kind:** thicken` and `**Mode:** split`, never a spine; with a thicken folded in, its acceptance keeps the baseline selectable.
- A trivial step (pass-through, print) is built by its pipeline's wiring task; its stub names the wiring task.
