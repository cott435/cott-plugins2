# Contracts

Read when writing or changing a `contract.md`.

Write `docs/packages/<pkg>/contract.md`: the provider's promise to its consumers. Consumers read only this page, so it stands alone.

- **One `###` section per public symbol** (function, class, or a type consumers see), headed `### <id>.<symbol>: <title>`. `<id>` is the package id. In a single package it is the component id, with sections grouped under `## <component>` (multi-package contracts drop that level and link the `architecture.md` beside them). The ID survives Grow, because the component id becomes the package id.
- **One symbol per heading.** Never `### train.train / train.train_seeds: …` or `### baselines.RandomAgent / ScriptedSnake: …`, however alike the symbols are: dt resolves `Read:` IDs and `dt context` packets only from a symbol's own heading. `dt lint` errors on these (`contract-heading`).
- **Each section:** the signature in the project's language, then **Invariants** (shapes, ranges, guarantees), **Errors** (what fails and how it's reported), and **Used by** (consuming components or packages, plus `PL-NN` IDs once those pipelines exist).
- **Contract first:** the contract is defined before either side is built. **The provider owns it.**
- **Boundaries (multi-package).** A symbol another package consumes adds one line: `- **Boundary:** <consumer packages> · **Fixtures:** tests/contracts/<pkg>.<symbol>/ · **Cases:** <the payloads a fixture must show>`. This section is the boundary's source of truth. `build-planning`'s Phase 0 contract task freezes it into executable artifacts in that folder: a schema (JSON Schema across languages or runtimes; a pandera schema for a dataframe between Python packages), one fixture per case, and a fixture-backed fake of the provider, so both sides build in parallel against the same fixtures. Name the cases; don't write the fixtures.
- **Public only, ≤ ~8 lines per symbol.** Helpers, modules and call order belong in the package's architecture or its `pipelines.md`. A retired symbol collapses to one line under `## Retired`: `- ~~stats.foo: Title~~ Retired YYYY-MM-DD: reason`.

````markdown
# [pkg] — Contract

**Package:** [pkg] · **Status:** Draft · **Last updated:** YYYY-MM-DD · **Architecture:** [../../architecture.md](../../architecture.md)

## stats

### stats.estimate_cov: Covariance estimate
`def estimate_cov(returns: Returns, *, method: CovMethod = "sample") -> Cov`
- **Invariants:** N×N for T×N input; symmetric; positive semi-definite
- **Errors:** `ValueError` if T < 2 or the input contains NaN
- **Used by:** portfolio
````
