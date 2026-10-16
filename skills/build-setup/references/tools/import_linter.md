# import-linter: architecture rules

| | |
|---|---|
| **What it does** | Enforces which modules may import which, so layers and boundaries stay clean |
| **Speed** | Seconds on small repos, tens of seconds on large ones, because it builds the whole import graph |
| **Config** | `[tool.importlinter]` and `[[tool.importlinter.contracts]]` |
| **Hook tier** | Implementer gate (CR-24), reviewer and CI. Not per-edit. 0.2 s on the sample |

> **Verified** in `design/tooling-verification.md` (2026-10-16): import-linter 2.15. The gate caught `data` importing `stats`; the shipped gate (without lint-imports) had passed it.

## What it catches

```python
# yourpackage/core/engine.py
from yourpackage.cli import main     # violates "core must not import cli"
```
```text
Layers: cli > services > core
  yourpackage.core is not allowed to import yourpackage.cli
```
Why: low-level code that imports high-level code creates cycles, makes testing hard, and defeats the point of splitting into layers. Agents add the "quick" import that creates this.

## Config

```toml
[tool.importlinter]
root_package = "yourpackage"

# Higher layers may import lower ones, never the reverse.
[[tool.importlinter.contracts]]
name = "Layers: cli > services > core"
type = "layers"
layers = [
    "yourpackage.cli",
    "yourpackage.services",
    "yourpackage.core",
]

# Example: forbid the core package from using a heavy library.
[[tool.importlinter.contracts]]
name = "core stays free of pandas"
type = "forbidden"
source_modules = ["yourpackage.core"]
forbidden_modules = ["pandas"]
```

Run: `lint-imports --no-logo` (the logo fills the agent's feedback tail).

## Generating contracts from the architecture

Contracts are generated, never hand-written (CONSTRAINTS.md Boundaries says "do not edit"):
- **Source:** single package: each component's `Depends on` column. Multi-package: the package dependency rules. Contracts sit between component subfolders (`pkg.data`) in a single package and between packages in multi.
- **Shape:** order the components so every dependency points down, then write one `layers` contract, top first. Components that don't depend on each other share a layer: `"pkg.a | pkg.b"` (independent siblings).
- **Narrower rules:** if a component may import only some of the layers below it (`portfolio` → `stats`, never `data`), add a `forbidden` contract for that pair.
- **Not built yet:** wrap a module that doesn't exist in parentheses, `"(pkg.report)"`. The layer is optional while missing and enforced once it exists (verified). Without that, a fresh skeleton fails with `Missing layer`. `dt status` flags parentheses around a module that now exists; Extend removes them.
- **Grow:** when a component becomes a package, Extend rewrites its component contract as a package contract. The rule is the same, so code that passed keeps passing.

```toml
[[tool.importlinter.contracts]]
name = "Layers: report > stats > data"
type = "layers"
layers = ["(quant.report)", "quant.stats", "quant.data"]
```
