"""PB-03 — run by you, against Plaid's Sandbox. PLAID_CLIENT_ID and PLAID_SECRET from .env; PLAID_BASE_URL
overrides the host. Prints nothing but counts; access tokens stay in out/."""
import datetime as dt, json, os, urllib.error, urllib.request

from probe_kit import load_env, record, shape_sample, write_evidence, write_private

INSTITUTIONS = ["First Platypus Bank", "Canary Credit Union"]
DAYS = 730  # AD-04's setting; fixed per Item, so the probe links as the build will
FIELDS = ("date", "account_id", "name", "pending", "transaction_id")


def base():
    return os.environ.get("PLAID_BASE_URL", "https://sandbox.plaid.com")


def post(path, body):
    body = {"client_id": os.environ["PLAID_CLIENT_ID"], "secret": os.environ["PLAID_SECRET"], **body}
    req = urllib.request.Request(base() + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:  # the error code only; never the request
        return {"error_code": json.load(e).get("error_code")}


def c2_coverage():
    found = {}
    for name in INSTITUTIONS:
        hits = post("/institutions/search", {"query": name, "products": ["transactions"], "country_codes": ["US"]})
        inst = next((i for i in hits.get("institutions", []) if i["name"].lower() == name.lower()), None)
        found[name] = inst["institution_id"] if inst else None
    record("C2", {"listed": len(found), "found": sum(1 for v in found.values() if v)}, passed=all(found.values()))
    return [v for v in found.values() if v]


def link(inst):
    pt = post("/sandbox/public_token/create", {"institution_id": inst, "initial_products": ["transactions"],
                                               "options": {"transactions": {"days_requested": DAYS}}})
    return post("/item/public_token/exchange", {"public_token": pt.get("public_token")}).get("access_token")


def sync_all(token):
    """Every page; a mutation during pagination restarts from the first cursor, as Plaid's docs say."""
    restarts = 0
    while True:
        cursor, rows = "", []
        while True:
            page = post("/transactions/sync", {"access_token": token, "cursor": cursor, "count": 500})
            if page.get("error_code") == "TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION":
                restarts += 1
                break
            rows += page["added"]
            cursor = page["next_cursor"]
            if not page["has_more"]:
                return rows, restarts


def months_back(rows, today):
    first = min(dt.date.fromisoformat(r["date"]) for r in rows)
    return (today.year - first.year) * 12 + today.month - first.month


if __name__ == "__main__":
    load_env(["PLAID_CLIENT_ID", "PLAID_SECRET"])
    insts = c2_coverage()
    tokens = [t for t in (link(i) for i in insts) if t]
    record("C3", {"linked": len(tokens), "of": len(insts)}, passed=bool(insts) and len(tokens) == len(insts))
    write_private("items.json", tokens)
    today, months, rows_all, restarts, balances = dt.date.today(), {}, [], 0, []
    for n, tok in enumerate(tokens, 1):
        rows, r = sync_all(tok)
        restarts += r
        rows_all += rows
        for k, acct in enumerate(sorted({x["account_id"] for x in rows}), 1):
            months[f"item{n}_account{k}"] = months_back([x for x in rows if x["account_id"] == acct], today)
        balances += [a.get("balances", {}).get("current") is not None for a in post("/accounts/get", {"access_token": tok}).get("accounts", [])]
    record("C4", {"months": months, "restarts": restarts}, passed=bool(months) and max(months.values()) >= 12,
           note="a card opened recently has less history")
    spend = [x for x in rows_all if (x.get("personal_finance_category") or {}).get("primary") not in ("INCOME", "TRANSFER_IN")]
    share = {f: round(sum(1 for x in rows_all if x.get(f) is not None) / max(len(rows_all), 1), 3) for f in FIELDS}
    outflow = round(sum(1 for x in spend if x["amount"] > 0) / max(len(spend), 1), 3)
    unique = len({x["transaction_id"] for x in rows_all}) == len(rows_all)
    record("C5", {"rows": len(rows_all), "outflow_positive": outflow, "field_share": share, "ids_unique": unique},
           passed=outflow >= 0.9 and all(v == 1.0 for v in share.values()) and unique)
    record("C8", {"accounts": len(balances), "with_balance": sum(balances)}, passed=bool(balances) and all(balances))
    shape_sample("sync_added", rows_all[:3])
    write_evidence("PB-03", "user", base())
    print(f"PB-03: {len(rows_all)} rows over {len(tokens)} Items; evidence written")
