"""PB-01 — run by you. SHARADAR_API_KEY from .env; nothing is printed but counts."""
import json
import os
import urllib.parse
import urllib.request


def get(table, **params):
    base = os.environ.get("SHARADAR_BASE_URL", "https://api.sharadar.com/v1.0/data")
    q = urllib.parse.urlencode({**params, "api_key": os.environ["SHARADAR_API_KEY"], "format": "json"})
    with urllib.request.urlopen(f"{base}/{table}?{q}", timeout=60) as r:
        return json.load(r)


def c1_raw_vs_adjusted():
    """closeunadj / close around AAPL's 4-for-1 split."""
    rows = {r["date"]: r for r in get("stocks", ticker="AAPL", **{"from": "2020-08-24", "to": "2020-09-04"})}
    before = rows["2020-08-28"]
    return round(before["closeunadj"] / before["close"], 4)


def c2_history_depth():
    """Earliest SEP date for IBM."""
    return min(r["date"] for r in get("stocks", ticker="IBM"))
