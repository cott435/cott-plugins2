# Phase 0: contract, spines, integration

Read when writing Phase 0. Examples: `examples-phase0.md`.

`## Phase 0: Spine` makes every new pipeline of the milestone run end to end, contract first, so packages build in parallel instead of queueing behind one task.

**a. Contract task** (multi-package, when the milestone crosses a package boundary). One solo task, first, `**Step:** contract`, no Parallel group, `**Package:**` the provider's. Boundaries that don't fit one M task, or have different providers, get one contract task each, still serial and first. It freezes each boundary the milestone uses (every contract symbol with a `**Boundary:**` line naming a consumer in the milestone) as executable artifacts in the symbol's `**Fixtures:**` folder:
- a schema: JSON Schema or a typed model for a payload; for a Python or data project, a pandera schema for a frame
- golden fixture payloads that validate against it (a sample frame for data), one per case the contract section lists
- a fixture-backed fake of the provider side, written where the consumer's tooling can load it, serving only those fixtures

Its Acceptance: every fixture validates against the schema; the fake serves each fixture. Its `Read:` is the boundary symbols. A boundary already frozen by an earlier milestone isn't frozen again.

**b. Package spines.** One task per new package pipeline, `**Step:** PL-NN`, solo. Each depends on the contract task, and on an earlier spine of the same package only when it calls it or shares its files. Spines of different packages share no file, and the boundary symbols they both read are frozen, so they carry a `**Parallel:**` group and build side by side. A consumer's spine runs against the contract fake; a provider's spine asserts that its output validates against the boundary schema.

**c. System spine, last.** One task per new system pipeline, no Parallel group, depending on the package spines it joins: the integration. It swaps each fake for the real provider and runs the system pipeline end to end; the boundary fixtures still validate against the real output. System pipelines have no Entry, so its Package is the package that owns the system pipeline's first step, with `**Reason:** system spine`. The root has no pre-build sections, so its acceptance has no `dt layout` bullet; each package spine clears its own package's.

Single package, or a milestone whose packages share no boundary: no contract task, no system spine; spines as in b, with `Depends on` where one calls another.

Every spine task (b and c):
- builds every step at its spine version (a real baseline), so the pipeline runs end to end on fixture or synthetic data
- commits the smoke command, and replaces the pipeline's pre-build sections with a `dt layout` pointer (`dt tick` prompts `dt prebuild-clear`)

**Fakes.** A boundary fake generated from an approved contract is allowed: both sides are tested against the same fixtures (the provider asserts its output validates, the consumer consumes the fixtures), so neither can drift from the contract unseen. Mocking a step inside a package is still forbidden: a spine step is the real baseline from the step table. Changing a frozen schema or fixture is a contract change: `architecture-design` Revise, never an edit to make a test pass. The bar enforces it (CR-09): once a contract folder exists at a task's base, the implementer can't write it and `dt guard` asks before any edit no open contract task covers. The re-freeze after a Revise is a new contract task naming the symbol in `Read:`; it runs in the main session, since the implementer's guard blocks a folder frozen at the base.
