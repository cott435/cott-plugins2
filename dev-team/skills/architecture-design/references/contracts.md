# Contracts

Read when writing or changing a `contract.md`.

Write `docs/packages/<pkg>/contract.md`: the provider's promise to its consumers. Consumers read only this page, so it stands alone.

- **One `###` section per public symbol** (function, class, or type), headed `### <id>.<symbol>: <title>`. `<id>` is the package id. In a single package it is the component id, with sections grouped under `## <component>` (multi-package contracts drop that level and link the `architecture.md` beside them). The ID survives Grow, because the component id becomes the package id.
- **One symbol per heading.** Never `### train.train / train.train_seeds: …` or `### baselines.MajorityClass / LogisticBaseline: …`, however alike the symbols are: dt resolves `Read:` IDs and `dt context` packets only from a symbol's own heading. `dt lint` errors on these (`contract-heading`).
- **Function sections:** the signature in the project's language, then **Invariants** (shapes, ranges, guarantees), **Errors** (what fails and how it's reported), and **Used by** (consuming components or packages, plus `PL-NN` IDs once those pipelines exist).
- **Type sections.** Every type one step hands to another, and every type a public signature or method takes or returns, is its own section with the title `type`: `### profile.Profile: type`. An object one call returns and another takes back (`store.StagedRun`, from `begin` into `commit`) is a `typing.Protocol` of its methods with a replay double case, never a code comment. The first line is its shape as code: a frozen dataclass's fields, a `typing.Protocol`, or a pandera schema's columns for a dataframe. Then **Invariants** and **Used by**. `pipeline-design` names these types in every step's `In → Out`; the build's interface task writes them, as code, into the owner's `types.py`. Freeze only what crosses: a helper's or a private function's types stay out.
- **Every type a field annotation uses is defined:** its own `type` section, a typed inline definition (`weather: Weather(temp_c: float, issued: datetime)`), or a section whose first line mirrors another (`mirrors data.Readings, field for field`). A name defined nowhere (`Leaf | Stem`) or a field with no type (`settings`) is a gap the build would guess at.
- **Contract first:** the contract is defined before either side is built. **The provider owns it.**
- **Boundaries.** A symbol consumed across owners adds one line: `- **Boundary:** <consumers> · **Fixtures:** tests/contracts/<id>.<symbol>/ · **Cases:** <the payloads a fixture must show>`. Every type that crosses step owners has one, components included: consumers are packages, components, or both. So does every contract function or pipeline entry whose **Used by** names another package or pipeline (`data.load_readings`, run by PL-02 as PL-01 built it): it gets a fake, so the caller's wiring never waits for the provider. This section is the boundary's source of truth. `build-planning`'s interface task freezes it into that folder: a schema (JSON Schema across runtimes; a pandera schema for a dataframe in Python), one sample per case, and, for a function a pipeline calls from another pipeline or package, a fixture-backed fake of the provider. A Protocol or class type's case is a replay double (a fixture-backed recording of the real object's calls, `a recorded 5-batch epoch`), and so is a function another component's step calls: it is the type's sample, not a fake. Both sides then build at once against the same samples. A type needs at least one case (`dt lint` `type-cases`). Name the cases; don't write the fixtures. A case may name a probe's redacted sample (`a posted purchase (PB-01 samples/sync_added.json#0)`); the interface task derives the type's sample from it, never copies it.
- **Public only, ≤ ~8 lines per symbol.** Helpers, modules and call order belong in the package's architecture or its `pipelines.md`. A retired symbol collapses to one line under `## Retired`: `- ~~profile.foo: Title~~ Retired YYYY-MM-DD: reason`.

````markdown
# [pkg] — Contract

**Package:** [pkg] · **Status:** Draft · **Last updated:** YYYY-MM-DD · **Architecture:** [../../architecture.md](../../architecture.md)

## profile

### profile.Profile: type
`@dataclass(frozen=True) class Profile: coefs: np.ndarray; periods: tuple[float, ...]; residuals: np.ndarray`
- **Invariants:** `coefs` 2×K for K `periods` (a sine and a cosine each); `residuals` has one entry per hour, at least 168
- **Boundary:** forecast · **Fixtures:** tests/contracts/profile.Profile/ · **Cases:** a planted daily sine over 4 synthetic weeks
- **Used by:** forecast

### profile.fit_seasonality: Seasonal profile fit
`def fit_seasonality(demand: Demand, *, terms: Terms = "daily+weekly") -> Profile`
- **Invariants:** one sine/cosine pair per harmonic; `residuals` has the input's length and mean zero
- **Errors:** `ValueError` if there are fewer than 168 hours or the input contains NaN
- **Used by:** forecast
````
