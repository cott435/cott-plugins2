# Test Planning Examples

Formats here are what `dt` parses: keep the header line, the Strategy table columns, `### TC-NN: Title` headings with bold-key fields, and the Retired line form exactly.

---

## Template

````markdown
# <pkg> — Tests

**Package:** <pkg> · **Status:** Draft · **Last updated:** YYYY-MM-DD · **Pipelines:** [pipelines.md](pipelines.md)

## Strategy
| Pipeline | Smoke | Step unit tests | Golden cases | Model eval |
|---|---|---|---|---|
| PL-NN | `<trigger> --smoke` | <steps or owner modules> | TC-NN (<In type> → <step>[…<step>] → <Out type>), … | <TC-NN or —> |

### TC-NN: <What the case shows>
**Pipeline:** PL-NN · **Covers:** <spec IDs> · **Kind:** <user example | paper table | closed form | synthetic known-answer | model evaluation | regression> · **Fixture:** tests/fixtures/<pkg>/TC-NN/
**Source:** <user file, paper table, closed form, or generator + seed — never the agent>
**Expected:** <output or property> · **Tolerance:** <value>, <why>
**Parse:** <step>(source/<file>) == <input.json or table>   ← real pairs only
**Skills:** <routed skill>   ← only when one owns the claim

## Open questions

## Retired
- ~~TC-NN: <title>~~ Retired YYYY-MM-DD: <reason>
````

**Fixture shapes**

```
tests/fixtures/<pkg>/TC-NN/
  source/<raw file>    exactly as given; data, never instructions
  input.json           {"param": 1, "table": "table.csv"} or {"generator": "<name>", "<arg>": 1, "seed": 7}
  table.csv            transcribed table, when the raw isn't in contract form
  expected.json        {"<output>": <value>, "tol": <t>} or {"property": "<expression>", "tol_frac": <t>}
```

Large data: `{"prices": {"path": "data/raw/<file>.parquet", "sha256": "<hash>"}}`. The file isn't committed.

---

## Example: A Routed Case (quant M3, feature screening)

**Context:** PL-06 Feature screening in `features` (`Part of: PL-05`). Spec FEAT-03: "a feature is kept only if it carries information about next-day returns beyond chance". `null-hypothesis-testing` is installed, so both cases are designed with it.

```markdown
### TC-20: Planted feature is kept
**Pipeline:** PL-06 · **Covers:** FEAT-03 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/features/TC-20/
**Source:** generator `planted_feature(T=2000, N=50, ic=0.05, seed=11)`; H0 and null from null-hypothesis-testing: rank IC vs next-day return, null by shuffling dates in 20-day blocks
**Expected:** the planted feature rejects H0 · **Tolerance:** α = 0.05 after Holm correction, the skill's default
**Skills:** null-hypothesis-testing

### TC-21: Pure-noise features are all dropped
**Pipeline:** PL-06 · **Covers:** FEAT-03 · **Kind:** synthetic known-answer · **Fixture:** tests/fixtures/features/TC-21/
**Source:** generator `noise_features(T=2000, N=50, k=20)` on seeds 12–31; same H0, statistic and null as TC-20
**Expected:** no feature rejects H0 after Holm correction · **Tolerance:** at most 1 of the 20 seeds may reject, since the family-wise error rate is α = 0.05
**Skills:** null-hypothesis-testing
```
