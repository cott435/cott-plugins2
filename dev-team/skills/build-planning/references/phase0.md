# Milestone shape: interface, step spines, wiring, system

Read when writing a milestone's tasks. Examples: `examples-phase0.md`.

A milestone is planned from its pipelines' steps: each step has one owner, one module and typed `In → Out`, so it is the unit of work. The plan freezes every boundary between steps first, so the work on both sides starts at once instead of queueing behind one spine. Every task carries `**Kind:**`:

```
## Phase 0: Interface              interface (solo, first)       types, signatures, samples, fakes, exports, __main__
## Phase 1: Step spines            spine, one per step           each writes its owner module only
## Phase 2: Wiring and thicken     wiring, one per pipeline      its entry module, smoke test
                                   thicken (tasks.md)            each after its step's spine
## Phase 3: System                 system (solo, last)           fakes swapped for real providers
```

Phases name the usual waves; the dependency graph (`tasks.md` step 9) decides what may start. Tester halves of split tasks start right after the interface.

**a. Interface task** (`**Kind:** interface`, `**Step:** contract`, solo, `**Depends on:** —`). It freezes, as code, every boundary in the milestone whose two sides belong to different tasks:
- each contract `type` section named in a milestone step's `In → Out`, every one, since the step's signature needs it, written into its owner's `types.py`, with a schema (pandera for a frame, JSON Schema across runtimes) and one sample per case in `tests/contracts/<component>.<Type>/`. A case naming a probe sample (`PB-01 samples/sync_added.json#0`) puts `PB-01:samples` in `Read:`; the task derives the type's sample from it, never copies it
- each new step's signature in its owner module, with the body `raise NotImplementedError("<task id>")` naming the task that replaces it
- for each function a pipeline calls from another pipeline or package (its `**Boundary:**` line): a fixture-backed fake serving its fixtures, where the caller's tests load it
- for each object with behavior a step passes (a Protocol or class: `core.Dataset`, `runstore.RunWriter`) and each call into another component's function: the Protocol or signature plus a fixture-backed replay double in `tests/contracts/<component>.<Type>/`. The double is that type's sample, not a fake: the system task never swaps it
- each component's `__init__.py` exports, and the package's `__main__.py`: the dispatch from each pipeline's trigger to its entry function, whose signature it stubs naming the wiring task, in that pipeline's own entry module

Not frozen: helpers, private functions, anything one task owns end to end, and boundaries an earlier milestone froze. `Read:` the type and boundary symbols. Acceptance: every sample validates against its type; every signature imports; each fake and replay double serves its fixtures. `Writes:` each component folder as one glob (`src/gridload/profile/**`) plus its contract folders; `task-size` doesn't count them. A milestone across packages may have one interface task per provider, all solo and first; interface tasks never depend on each other. When one runtime's types are generated from another's schema, the providing interface task runs the generator and writes the generated file too (its `Writes:` claims it).

**b. Step spines** (`**Kind:** spine`, `**Step:** PL-NN.<function>`, solo, XS or S). One per new step, library class rows included, each depending only on the interface task: it replaces the stub naming it with the step's spine version from the step table. `Writes:` its owner module, or its owner folder as one glob (`src/leaflab/core/train/**`), and its unit test, nothing else; steps sharing one module share one spine task. A provider waiting on a probe gets no spine: its stand-in row (`pipeline-design`'s `steps.md`) is built instead, and the real spine goes in the milestone the probe's Answer unblocks. Acceptance: the step's input sample gives a schema-valid output; the signature is unchanged. A step another pipeline provides (`PL-01 as built`) gets no spine.

**c. Wiring** (`**Kind:** wiring`, `**Step:** PL-NN`, solo). One per new pipeline: the entry function in the pipeline's own entry module (the layout's, never one module shared by several pipelines), so wiring tasks run side by side, and its smoke test. `__main__.py` is the interface task's. It depends on its pipeline's spines, since the smoke runs them (`order`, `none: integration: …`), never on their thicken tasks. A call to another pipeline or package runs against that boundary's fake, so wiring PL-02 never waits for PL-01. Acceptance: the smoke command runs end to end and is committed as the pipeline's smoke test; the pipeline's pre-build sections are replaced by a `dt layout` pointer (`dt tick` prompts `dt prebuild-clear`).

**d. System task** (`**Kind:** system`, solo, last). It swaps each fake for the real provider, in the entry its wiring wrote (a `file` edge), and runs every smoke command and the milestone's golden cases on the real chain; the boundary samples still validate against real output. Multi-package: one per new system pipeline, `**Step:**` that pipeline, `**Package:**` the owner of its first step, `**Reason:** system task`; the root has no pre-build sections, so no `dt layout` bullet. Single package: `**Step:**` the calling pipeline. A golden case that needs real collaborators (a thickened step, a class's real upgrade) is the system task's acceptance, never the wiring's, so wiring depends only on its pipeline's spines and fold tasks. A milestone with no fake and no such case has no system task.

**Folds** keep the task count down. The pipeline's wiring depends on a fold task, so a fold is allowed only where that task is XS and the critical path doesn't grow. Record each on its task as `**Reason:** fold: <rule>`:
- A step with a golden case whose spine and thicken are both in the milestone, or whose spine version is its whole behavior, may be one task that replaces the stub itself, `**Kind:** thicken` and `**Mode:** split`, never a spine; with a thicken folded in, its acceptance keeps the baseline selectable.
- A trivial step (pass-through, print) is built by its pipeline's wiring task; its stub names the wiring task.

**Fakes and stubs.** A fake is allowed only where a pipeline calls another pipeline or package: both sides test against the same fixtures, so neither drifts from the contract unseen. Mocking a step is forbidden: a step's spine is the real baseline, and its consumer builds against the type's sample (for a Protocol or class, its replay double). The interface stubs are the floor's one stub carve-out (`build-setup`'s CR-02): allowed while the task they name is open; the gate fails on one naming a done task, the milestone exit on any.

**Frozen means frozen.** Changing a frozen type, sample, signature or fake is a `contract-change`: `architecture-design` Revise, then a new interface task naming the symbol in `Read:`, never an edit to make a test pass. The bar enforces it (CR-09): once a contract folder exists at a task's base the implementer can't write it, and `dt guard` asks before any edit no open interface task covers. The re-freeze runs in the main session, since the implementer's guard blocks a folder frozen at the base.
