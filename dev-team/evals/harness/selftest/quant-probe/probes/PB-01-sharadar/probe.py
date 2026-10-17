"""PB-01 — run by you. SHARADAR_API_KEY from .env; SHARADAR_BASE_URL overrides the host (the evals use a fake).
Prints counts only; real rows stay in out/."""
import csv, json, os, pathlib, urllib.parse, urllib.request

from probe_kit import load_env, record, shape_sample, write_evidence, write_private

HERE = pathlib.Path(__file__).resolve().parent
LONG_LIVED = ["IBM", "KO", "XOM", "JNJ", "PG"]


def base():
    return os.environ.get("SHARADAR_BASE_URL", "https://api.sharadar.com/v1.0/data")


def get(table, **params):
    q = urllib.parse.urlencode({**params, "api_key": os.environ["SHARADAR_API_KEY"], "format": "json"})
    with urllib.request.urlopen(f"{base()}/{table}?{q}", timeout=60) as r:  # the key is never printed
        return json.load(r)


def c2_history():
    first = {t: min(r["date"] for r in get("stocks", ticker=t, to="2012-12-31")) for t in LONG_LIVED}
    earliest = max(first.values())
    record("C2", {"earliest_by_ticker": first}, passed=earliest <= "2006-01-03",
           note=f"latest first date {earliest}; DATA-01 floor 2011-01-03 {'met' if earliest <= '2011-01-03' else 'missed'}")


def c3_delisted():
    members = list(csv.DictReader(open(HERE / "delisted_members.csv")))
    found, perms, short = [], {}, []
    for m in members:
        rows = get("tickers", ticker=m["ticker"])
        perms[m["ticker"]] = sorted({r["permaticker"] for r in rows})
        dead = [r for r in rows if r["isdelisted"] == "Y"]
        if dead:
            found.append(m["ticker"])
            if abs(int(dead[0]["lastpricedate"][:4]) - int(m["delisted_on"][:4])) > 0:
                short.append(m["ticker"])
    write_private("tickers_c3.json", perms)
    missing = [m["ticker"] for m in members if m["ticker"] not in found]
    record("C3", {"listed": len(members), "found": len(found), "missing": missing,
                  "reused_two_permatickers": [t for t in ("BUD", "DNA") if len(perms.get(t, [])) >= 2]},
           passed=not missing and not short, note=f"missing: {', '.join(missing) or 'none'}")


def c4_raw_vs_adjusted():
    rows = {r["date"]: r for r in get("stocks", ticker="AAPL", **{"from": "2020-08-24", "to": "2020-09-04"})}
    before, after = rows["2020-08-28"], rows["2020-08-31"]
    rb, ra = before["closeunadj"] / before["close"], after["closeunadj"] / after["close"]
    record("C4", {"unadj_over_close_before": round(rb, 3), "after": round(ra, 3),
                  "raw_columns": [c for c in before if c.endswith("unadj")]},
           passed=abs(rb - 4) < 0.004 and abs(ra - 1) < 0.001,
           note="close is split-adjusted; only closeunadj is raw (no raw open, high or low)")
    write_private("sep_aapl.json", list(rows.values()))
    shape_sample("sep", list(rows.values())[:3])


def c6_membership():
    rows = get("sp500")
    earliest = min(r["date"] for r in rows)
    record("C6", {"earliest": earliest, "columns": sorted(rows[0])}, passed=earliest <= "2006-01-03",
           note=f"membership starts {earliest}")


if __name__ == "__main__":
    load_env(["SHARADAR_API_KEY"])
    c2_history()
    c3_delisted()
    c4_raw_vs_adjusted()
    c6_membership()
    write_evidence("PB-01", "user", base())
    print("PB-01: evidence written")
