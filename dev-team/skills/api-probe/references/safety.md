# Runners, secrets and personal data

The agent never sees a secret, and the script redacts, never the agent. Every mode keeps these rules.

## Runners

| Runner | Allowed when | Examples |
|---|---|---|
| **agent** | The check reads no credential, or only one the vendor publishes for everyone, touches nothing of the user's, and finishes in a few minutes: a sample, never every member | Public docs and pricing pages (WebFetch); keyless endpoints on 10 symbols; a weather API's published `demo` key on its sample city |
| **user** | The check needs any key the user holds, sandbox keys included; or the user's accounts; or it spends something; or it runs longer than a few minutes | Plaid sandbox or production; a paid subscription's API; a keyless batch paced over 500 symbols (80 minutes) |
| **user (manual)** | Only a person can see the answer | A Dashboard's plan page; the licence terms for the user's plan |

- The agent's checks go in `public.py` and the user's in `probe.py`. A keyless check too long for the agent stays in `public.py` as a user step, its README line giving its time and spend. `public.py` contains no `os.environ`, `environ`, `getenv`, `load_env`, `dotenv` or `.env`, docstrings included (`probe-runner` lint), so "the agent may run this" can be checked without trusting the agent. Run it with an empty environment: `env -i PATH="$PATH" python3 probes/PB-NN-<slug>/public.py`.
- Sandbox keys stay with the user. One rule, "any key → the user runs it", can be checked.
- The user runs their checks when they can, on their own time. When they're done they say "ran it". They paste nothing: Record reads `evidence/results.json`.

## Keys

- Scripts read keys through `load_env()`: the environment, else the probe's `.env`. `.env` holds keys only, because every value in it is treated as a secret. Settings (`PLAID_ENV`, a base URL) are read with `os.environ.get(name, default)` and set in the shell. Never from command-line arguments, which end up in shell history. Never printed, logged or echoed in an error.
- The user writes `.env` from `.env.example`. Neither the skill nor the README asks them to paste a key into chat. If they paste one anyway, say it should be rotated, and don't repeat it.
- `dt guard` denies Read, Edit and Write on `**/.env`, `**/.env.*` (not `.env.example`) and `probes/*/out/**`, and Edit and Write on `probes/*/evidence/**`. Through Bash, never `cat`, `grep`, `head`, `source`, `ls -la` or copy those paths either: the guard can't cover every shell command, so the rule is yours to keep.
- `out/` is created `0700` and its files `0600`.

## .gitignore

At the first probe, add whichever of these lines are missing:

```
.env
.env.*
!.env.example
probes/*/out/
probes/*/.env
```

The gate runs `git check-ignore` on each probe's `.env` and `out/` and stops if either isn't ignored.

## Redaction, in the script

- **Allow-list.** `allow(obj, fields)` keeps only the named fields (dotted paths reach inside). Into `record()` go counts, booleans, dates at month resolution (days only when a check needs them), enum values, field names and types. Never amounts, balances, names, masks, ids, tokens or free text.
- **Free text** only when a check asks for it (merchant descriptions for a normalization rule). The check bounds the count, masks digits, and skips person-to-person and payroll rows by category and pattern. The user reviews every line at the Record gate before it is committed.
- **Ids** are salted hashes kept in `out/`, for checks that ids stay stable across runs. Evidence holds counts of ids, never ids.
- **Samples.** `shape_sample(name, rows, keep=(enum fields…))` keeps field names, types, nulls and the named enum values. Numbers become `1` or `1.0` with the sign kept, strings `"<str:N>"`, id-like fields `"<id>"`, and dates move by whole weeks to 2001, keeping weekday and order. The real rows go to `out/<name>.raw.json`.
- **Floats** in `observed` are rounded (4 places), so no long digit run reaches the scan.
- **Scan, fail closed.** `write_evidence()` scans everything it is about to write for token shapes, secret keys (`sk-…`), credentials in URLs, hex runs of 24 or more, mixed base64 runs of 32 or more, runs of 8 or more digits and card-like groups, emails, phone numbers, and every value in `.env` or passed through `load_env()`. On a hit, nothing reaches `evidence/`: the output goes to `out/evidence.rejected.json`, and the script names the pattern and exits 1. Fix the allow-list, never the pattern. `dt probes --scan` runs the same check on committed evidence (`evidence_leaks`).
- **Licensed data.** Vendor terms usually allow personal local storage and forbid redistribution. Market-data samples keep the shape and a few rows with values replaced, and real values stay in `out/`. Record the terms that were checked in Spends or Caveats.

## Spending

A probe can spend what the build needs. Spends names it, and the user agrees at the New gate before anything runs.

- **Check cheaply before spending.** A free lookup (`/institutions/search`) or a free sample goes first, and its failure stops the run before anything is spent.
- **Use the build's exact settings** where a setting can't be changed later.
- **Keep what was spent.** Items that count against a cap stay in `out/`, and the decision's Consequences say the build adopts them. Tokens move to the service's secret store; they never pass through docs.
- **Money.** Name the amount: a subscription month taken before the decision is Accepted is the user's call.
