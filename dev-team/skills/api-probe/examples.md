# API Probe Examples

The FinTrack bank-linking probe, PB-01, from New to Record. The entry shape is `references/entry.md`, and the rules are `references/safety.md`.

---

## The situation

FinTrack's architecture is approved, with AD-04 still Proposed: Plaid Trial, Transactions, `days_requested` 730, free (QR-08 ≤ $5/month). It carries `**Probe:** PB-01 — does Plaid Trial cover my institutions, with how much history?` and a Risks line. `ledger.BankTxn`, `ledger.SyncBatch` and `ledger.Account` assume stable ids, `pending_transaction_id`, `merchant_entity_id` and Plaid's sign convention. AD-12 needs real merchant descriptions.

`dt status --skill api-probe` → `mode: new`, `probes_unwritten: PB-01 (AD-04)`.

## New

**Docs read**, one page per question: account/billing, api/institutions, api/products/transactions, link/oauth, errors/rate-limit-exceeded, sandbox.

**Settled by the docs**, cited and not probed:
- Trial gives 10 Production Items to teams created on or after 2026-04-15 in the US or Canada, with Transactions, Refresh, Investments and Liabilities. Removed Items still count.
- `days_requested` is 1–730 and can't be raised on an existing Item.
- `/transactions/sync` returns up to 500 rows a page, and a mutation during pagination means restarting from the first cursor.
- Sandbox Items are free and unlimited.

**Left to checks:** whether *this* team is eligible (a team with a pending Production application can't switch to Trial), whether *these* institutions link, and how much history each keeps ("up to 24 months").

```markdown
### PB-01: Plaid Trial covers my institutions with 12–24 months of history
**Folder:** `probes/PB-01-plaid-coverage/` · **Hash:** 5c1e09ab · **Status:** Draft · **Milestones:** S1 · **Last run:** —
- **Question:** Is my team on the Trial plan, does every institution I use link with Transactions (or the balance product for investment and loan accounts), and how many months of history does each return?
- **Informs:** AD-04, AD-12 · DATA-01, DATA-02, DATA-04, SYNC-03, SYNC-05, LINK-04, LINK-06, QR-08 · ledger.Account, ledger.BankTxn, ledger.SyncBatch
- **Docs read (2026-10-17):** account/billing, api/institutions, api/products/transactions, link/oauth, errors/rate-limit-exceeded, sandbox
- **Spends:** one Production Item per institution, for good; links with AD-04's exact settings (Transactions, 730 days); out/items.json is kept and the service adopts it. OAuth banks may need up to 5 business days to enable
- **Checks:** table below
- **Verdict:** —
- **Caveats:** stdlib urllib; no retries; Link page bound to 127.0.0.1; samples are placeholders, not my values
```

| Check | What | How | Pass | Runner | Result |
|---|---|---|---|---|---|
| C0 | App and company profile filled in | Dashboard → Team settings | Both filled (some banks refuse OAuth otherwise) | user (manual) | — |
| C1 | Trial plan with Items to spare | Dashboard → Settings → Team → Plans | Trial, and Items used + institutions ≤ 10 | user (manual) | — |
| C2 | Each institution supported, before an Item is spent | `/institutions/search` per name in `out/institutions.txt`, then `/institutions/get_by_id` | Every name found and `SUPPORTED`; spending ones list `transactions` | user | — |
| C3 | Each institution links | Local Link page, production, the build's link-token settings | Exchange succeeds for every institution | user | — |
| C4 | History depth | Earliest date per spending account after `HISTORICAL_UPDATE_COMPLETE` | ≥ 12 months where the bank keeps it (DATA-01); measured up to 24 (SYNC-03) | user | — |
| C5 | DATA-02 fields | Presence share per field | Outflow > 0 as `ledger.Cents` assumes; date, account, description, `pending`, unique id on 100%; `merchant_entity_id` share recorded (AD-12) | user | — |
| C6 | Pending → posted | Re-run ≥ 24 h later | ≥ 1 posted row with `pending_transaction_id`, if any were pending (SYNC-05) | user | — |
| C7 | Ids stable | Re-run: hashed ids from run 1 present | 100% (DATA-02) | user | — |
| C8 | Balance-only accounts | `/accounts/get` on investment and loan Items | `balances.current` on every account (LINK-04, DATA-04) | user | — |
| C9 | Refresh on Trial | `/transactions/refresh` | 200, no billing error (QR-08) | user | — |
| C10 | Re-auth path | Sandbox: `/sandbox/item/reset_login`, update-mode link token | `ITEM_LOGIN_REQUIRED` seen; token created (LINK-06) | user (sandbox key) | — |
| C11 | Merchant fixture | 5 descriptions per institution, digits masked, transfers and payroll skipped | 5 per spending institution, approved at Record | user | — |

Every check needs a key or a person, so there is no `public.py`. Even C10's sandbox key is the user's.

**`probe.py`, one check** (C2: it runs before C3 spends anything):

```python
from probe_kit import allow, load_env, private, record, save_private, write_evidence
import plaid_http as plaid   # urllib POST; host from PLAID_BASE_URL, else os.environ.get("PLAID_ENV")

def c2_coverage() -> bool:
    names = [n for n in private("institutions.txt").read_text().splitlines() if n.strip()]
    found = {}
    for name in names:
        hits = plaid.post("/institutions/search", {"query": name, "country_codes": ["US"],
                                                   "products": ["transactions"]})["institutions"]
        inst = next((i for i in hits if i["name"].lower() == name.lower()), None)
        found[name] = inst and allow(inst, ["institution_id", "products", "oauth"])
    save_private("institutions.json", found)          # names and ids stay in out/
    ok = all(found.values())
    record("C2", {"listed": len(names), "found": sum(1 for v in found.values() if v),
                  "oauth": sum(1 for v in found.values() if v and v["oauth"])}, passed=ok)
    return ok

def main():
    load_env(["PLAID_CLIENT_ID", "PLAID_SECRET"])         # keys only; PLAID_ENV is a shell setting
    if c2_coverage():
        ...                    # C3 is link_server.py; C4, C5, C8, C9, C11 from one collect run
    write_evidence(runner="user", env=plaid.ENV, base_url=plaid.BASE)
```

**README order:** C0, C1 (manual) → C10 and a dry run in Sandbox → C2 → C3 → C4, C5, C8, C9, C11 in one collect run → C6, C7 a day later. C2 failing stops the run before C3.

**New gate**, besides the entry:

```
Settled by the docs: the Trial terms, days_requested 1–730 and fixed per Item, sync paging and restarts (cited above).
Contradictions: none.
Spends: one Production Item per institution, for good (6 institutions → 6 of 10). Links with 730 days and
  Transactions, as AD-04 says. out/items.json is kept, so the service adopts these Items instead of linking again.
  Do you agree to that?
Your steps: copy .env.example to .env and fill in your keys; export PLAID_ENV=sandbox for step 1, production after; list your institutions in out/institutions.txt;
  1. python3 probes/PB-01-plaid-coverage/probe.py sandbox   ~2 min, spends nothing
  2. python3 probes/PB-01-plaid-coverage/probe.py coverage  ~1 min, spends nothing; stops if C2 fails
  3. python3 probes/PB-01-plaid-coverage/link_server.py      ~5 min per bank; spends one Item each
  4. python3 probes/PB-01-plaid-coverage/probe.py collect   ≤ 20 min
  5. tomorrow: python3 probes/PB-01-plaid-coverage/probe.py rerun
Agent's results so far: none (every check needs your key or your Dashboard).
Hand-offs: none yet.
```

The user says "Yes, go ahead, 6 Items is fine" → `Ready`. **Stop.** pipeline-design and test-planning can go on. build-planning shows `blocked (waiting for PB-01)` for the milestone that freezes `ledger.BankTxn`.

## Record

Three days later the user says "ran it, both days". `dt status --skill api-probe` → `mode: record`, `probes_results: PB-01`. `dt probes --scan` is clean, and `results.json`'s `script_hash` is `5c1e09ab`, the entry's Hash. The user reports C0 as filled and C1 as Trial with 0 of 10 Items used.

```json
{"probe": "PB-01", "script_hash": "5c1e09ab", "run_at": "2026-10-21T08:40:02Z", "runner": "user",
 "env": "production", "base_url": "https://production.plaid.com",
 "checks": {"C2": {"pass": true, "observed": {"listed": 6, "found": 6, "oauth": 4}},
            "C4": {"pass": true, "observed": {"a1": 24, "a2": 24, "a3": 13, "a4": 3}, "note": "a4: card opened 3 months ago"},
            "C5": {"pass": true, "observed": {"outflow_positive": true, "merchant_entity_id_share": 0.62}},
            "C9": {"pass": true, "observed": {"status": 200}}}}
```

C3, C6–C8, C10 and C11 are recorded the same way (shortened here); C11 holds 25 masked lines.

Result cells filled, for example C4 `pass: 13–24 months; a4: 3, opened 3 months ago` and C5 `pass: merchant_entity_id on 62%`. Last run `2026-10-21T08:40:02Z`. Verdict `pass`.

**Record gate**, besides the entry:

```
Free text for your approval (C11, 25 lines, digits masked), e.g. "SQ *BLUE BOTTLE #### OAKLAND".
Hand-offs:
- architecture-design Revise: AD-04 Context cites "PB-01, 2026-10-21: 6 of 6 institutions link; history 13–24
  months (a card opened 3 months ago has 3)"; Proposed → Accepted; delete the Risks line. Consequences: the
  service adopts PB-01's 6 Items (a build task in S1's first milestone).
- architecture-design Revise: AD-12 Consequences quote merchant_entity_id on 62% of spending rows;
  ledger.BankTxn's Cases can name PB-01 samples/sync_added.json rows.
```

The user approves the lines → `Answered · pass · 2026-10-21`, and an offer to commit `docs/probes.md` and `probes/PB-01-plaid-coverage/` (`.env` and `out/` stay ignored). **Stop.** Next is architecture-design Revise.

**Had C1 failed** (no Trial): the Verdict is `fail: C1, team not eligible for Trial`. The hand-off goes to spec-writing through the user, since Pay-as-you-go bills Transactions monthly per Item and QR-08's $5 probably fails. api-probe names QR-08 and the finding, and edits nothing else.
