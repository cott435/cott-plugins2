# The probe entry and its folder

Every mode writes to this shape. `dt` parses it, so keep the field names and order exactly.

## Index template: `docs/probes.md`

````markdown
# <Project> — Probes

**Status:** Draft · **Last updated:** YYYY-MM-DD

### PB-01: <the claim being checked, as a sentence that can be true or false>
**Folder:** `probes/PB-01-<slug>/` · **Hash:** — · **Status:** Draft · **Milestones:** S<n> · **Last run:** —
- **Question:** <what the decision needs to know, in the user's terms>
- **Informs:** <AD-NN, …> · <requirement IDs> · <contract types, `<component>.<Type>`>
- **Docs read (YYYY-MM-DD):** <the official pages, one per question, never a homepage>
- **Spends:** <Items, paid calls, a subscription month, settings fixed for good; "nothing" only after looking>
- **Checks:** table below
- **Verdict:** —
- **Caveats:** <what a builder must not reuse as is: no retries, localhost-only, placeholder samples>

| Check | What | How | Pass | Runner | Result |
|---|---|---|---|---|---|
| C1 | <one unknown> | <endpoint, page or comparison> | <the threshold, from the requirement it informs> | agent | — |

## Retired
````

- **Title** states the claim ("Plaid Trial covers my institutions with 12–24 months of history"), so a fail reads as the claim being false.
- **Folder** is `probes/PB-NN-<slug>/`, slug in lower-case kebab.
- **Hash** stays `—` until `dt probes --stamp` writes it. Never type one.
- **Milestones**: the stage or milestone whose plan waits on the probe, as in `docs/references.md`: `S<n>`, `M<n>`, `all` or `—`. `dt` routes the probe's code to that milestone's tasks like an `RF-NN` entry.
- **Last run** is the `run_at` date of the `results.json` that Record last read.
- **Informs** lists only IDs that exist (`probe-informs` lint). The contract types are the ones whose fields the evidence could change.
- **Docs read** names the pages behind every claim the entry settles without a check, with the date read.
- **Checks**, one row per unknown, addressable as `PB-01.C3`. Every row has a **Pass** cell. A measure-only check states the threshold it is compared with, taken from the requirement. A check only a person can see has runner `user (manual)`; a check that runs on a sandbox key has `user (sandbox key)`. Runners are defined in `safety.md`.
- **Result** is `—` until a run, then `pass`, `fail` or `pass, note` in a few words ("13–24 months; a4: 3, opened 3 months ago").
- **Verdict** is `pass` when every check passed. A fail names the checks and why, in one line.
- **Size:** about 8 lines plus one line per check.

## Status

`Draft` (spec waiting for approval) → `Ready` (approved, code written, waiting for a run) → `Answered · pass|fail · YYYY-MM-DD`, or `Waived · YYYY-MM-DD — <the user's reason>`.

- A decision that cites a Ready probe stays `Proposed`. build-planning won't plan a milestone the probe reaches until it is Answered or Waived.
- Waiving is only ever the user's call, in their words. The decision's Risks line stays.
- A withdrawn probe collapses to one struck line under `## Retired`: `- ~~PB-04: EODHD lists reused tickers~~ Retired 2026-11-02: AD-04 dropped EODHD`. Its folder is deleted after the user agrees, and the ID is never reused. Omit the heading until the first retirement.

## Folder

```
probes/PB-NN-<slug>/
  probe.py          the user's checks; reads keys through load_env()
  public.py         optional: the agent's checks; no os.environ, getenv or .env anywhere in it
  probe_kit.py      copied from templates/, unchanged
  README.md         from templates/README.md: who runs what, in order, and what each step spends
  .env.example      variable names only
  evidence/         committed, written only by the scripts: results.json, schema.json, samples/
  out/              gitignored, 0700: raw responses, tokens, hashed ids, the user's own lists
  .env              gitignored, written by the user
```

- **Small.** Each function answers one check. No retries, config layers, classes or abstractions beyond what a check needs. `dt lint` warns over 400 code lines (`probe-large`).
- **Raw HTTP.** Stdlib `urllib` against the documented endpoints, so the evidence is the payload the adapter will see. When an SDK is unavoidable, declare it in PEP 723 inline metadata and run with `uv run`. `pyproject.toml` never changes.
- **Base URL from the environment, real by default** (`PLAID_BASE_URL`, `SHARADAR_BASE_URL`), so the evals can point a probe at a fake vendor.
- **Use the build's settings** wherever a setting can't be changed later (Plaid's `days_requested`).
- **One entry per check** in the code: a `cN_<what>()` function that ends in `record("CN", …)`. `main()` calls them in the README's order, then `write_evidence()`, once.
- Errors print the HTTP status and the vendor's error code, never headers, URLs with keys in them, or bodies.

## Evidence

`evidence/results.json`, written by `write_evidence()`, is the only file Record reads:

```json
{"probe": "PB-01", "script_hash": "5c1e09ab", "run_at": "2026-10-20T18:02:11Z",
 "runner": "user", "env": "production", "base_url": "https://production.plaid.com",
 "checks": {"C2": {"pass": true, "observed": {"listed": 6, "found": 6}, "note": "brokerage: investments only"}}}
```

A re-run of the same code keeps the checks it didn't record again, so a second-day run adds C6 and C7 to the first day's. A run of changed code replaces them all. `samples/<name>.json` holds shape-faithful rows from `shape_sample()`. `schema.json` lists each field path seen, with its types and null count. Contract `**Cases:**` cells and adapter tests cite samples as `PB-01 samples/sync_added.json#0`.
