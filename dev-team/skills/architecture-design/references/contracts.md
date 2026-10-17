# Contracts

Read when writing or changing a `contract.md`.

Write `docs/packages/<pkg>/contract.md`: the provider's promise to its consumers. Consumers read only this page, so it stands alone.

- **One `###` section per public symbol** (function, class, or type), headed `### <id>.<symbol>: <title>`. `<id>` is the package id. In a single package it is the component id, with sections grouped under `## <component>` (multi-package contracts drop that level and link the `architecture.md` beside them). The ID survives Grow, because the component id becomes the package id.
- **One symbol per heading.** Never `### train.train / train.train_seeds: …` or `### baselines.RandomAgent / ScriptedSnake: …`, however alike the symbols are: dt resolves `Read:` IDs and `dt context` packets only from a symbol's own heading. `dt lint` errors on these (`contract-heading`).
- **Function sections:** the signature in the project's language, then **Invariants** (shapes, ranges, guarantees), **Errors** (what fails and how it's reported), and **Used by** (consuming components or packages, plus `PL-NN` IDs once those pipelines exist).
- **Type sections.** Every type one step hands to another, and every type a public signature takes or returns, is its own section with the title `type`: `### stats.Cov: type`. The first line is its shape as code: a frozen dataclass's fields, a `typing.Protocol`, or a pandera schema's columns for a dataframe. Then **Invariants** and **Used by**. `pipeline-design` names these types in every step's `In → Out`; the build's interface task writes them, as code, into the owner's `types.py`. Freeze only what crosses: a helper's or a private function's types stay out.
- **Contract first:** the contract is defined before either side is built. **The provider owns it.**
- **Boundaries.** A symbol consumed across owners adds one line: `- **Boundary:** <consumers> · **Fixtures:** tests/contracts/<id>.<symbol>/ · **Cases:** <the payloads a fixture must show>`. Every type that crosses step owners has one, components included: consumers are packages, components, or both. This section is the boundary's source of truth. `build-planning`'s interface task freezes it into that folder: a schema (JSON Schema across runtimes; a pandera schema for a dataframe in Python), one sample per case, and, for a function a pipeline calls from another pipeline or package, a fixture-backed fake of the provider. A Protocol or class type's case is a replay double (a fixture-backed recording of the real object's calls, `a recorded 5-step episode`), and so is a function another component's step calls: it is the type's sample, not a fake. Both sides then build at once against the same samples. A type needs at least one case (`dt lint` `type-cases`). Name the cases; don't write the fixtures. A case may name a probe's redacted sample (`a posted purchase (PB-01 samples/sync_added.json#0)`); the interface task derives the type's sample from it, never copies it.
- **Public only, ≤ ~8 lines per symbol.** Helpers, modules and call order belong in the package's architecture or its `pipelines.md`. A retired symbol collapses to one line under `## Retired`: `- ~~stats.foo: Title~~ Retired YYYY-MM-DD: reason`.

````markdown
# [pkg] — Contract

**Package:** [pkg] · **Status:** Draft · **Last updated:** YYYY-MM-DD · **Architecture:** [../../architecture.md](../../architecture.md)

## stats

### stats.Cov: type
`@dataclass(frozen=True) class Cov: matrix: np.ndarray; assets: tuple[str, ...]; n_obs: int`
- **Invariants:** `matrix` N×N for N `assets`; symmetric; positive semi-definite; `n_obs` ≥ 2
- **Boundary:** portfolio · **Fixtures:** tests/contracts/stats.Cov/ · **Cases:** 3 assets from 250 synthetic days
- **Used by:** portfolio

### stats.estimate_cov: Covariance estimate
`def estimate_cov(returns: Returns, *, method: CovMethod = "sample") -> Cov`
- **Invariants:** N×N for T×N input; symmetric; positive semi-definite
- **Errors:** `ValueError` if T < 2 or the input contains NaN
- **Used by:** portfolio
````
