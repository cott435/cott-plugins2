"""Fake Sharadar (design/probes.md §9, §10.1): SEP, TICKERS, ACTIONS and SP500 for 40 securities, 2007–2026.

Paths: Sharadar's own API (`/v1.0/data/<stocks|tickers|actions|sp500>`, `format=json|csv`) and the Nasdaq Data
Link datatables (`/api/v3/datatables/SHARADAR/<SEP|TICKERS|ACTIONS|SP500>.json`) route by table name, so any base
URL prefix works. Both need an `api_key` parameter. Filters: `ticker` (comma list), `permaticker`, `action`,
`isdelisted`, `date`, `date.gte|gt|lte|lt`, `from`/`to`, `qopts.columns`. Pages hold 10,000 rows (`cursor` /
`qopts.cursor_id`). Bulk: `years=full&status=true` or `qopts.export=true` gives the file size without the file.

Planted facts (what a guess gets wrong):
- `close`, `open`, `high`, `low` and `volume` are split-adjusted as of today; `closeunadj` is the only raw price;
  `closeadj` also folds in dividends. AAPL's 4-for-1 split on 2020-08-31: `closeunadj/close` is 4 before, 1 after.
- Every table starts on 2007-01-03, so no member has prices before 2007 (DATA-01's 2006 target fails, a 2011
  floor passes), and the SP500 table's earliest record is 2007-01-03.
- Of the persona's 10 delisted names, MER and WYE are missing entirely; the other 8 are in TICKERS with
  `isdelisted = Y` and prices to their delisting date.
- `BUD` resolves to two permatickers: Anheuser-Busch (to 2008-11-18) and AB InBev's ADR (from 2009-09-16).
- FB → META (2022-06-09) keeps one permaticker; SEP carries the whole series under META.
- A split's ACTIONS `value` is new shares per old share inverted (4-for-1 → 0.25).
"""
import csv, datetime as dt, io, json, math, random, re

SECRET_PARAMS = ("api_key",)
PAGE = 10_000
START, END = dt.date(2007, 1, 3), dt.date(2026, 10, 16)
PERSONA_DELISTED = ["BUD", "DNA", "WB", "LEH", "BSC", "CFC", "MER", "SGP", "WYE", "EK"]
MISSING = ["MER", "WYE"]
# What the grader looks for once the planted facts reach the design (grade.py, planted_facts_reached_design;
# docs_before_probe for the contradiction the vendor's own docs already show).
PLANTED = {"adjusted": r"split[- ]adjusted", "raw": r"closeunadj", "start": "2007", "missing": MISSING,
           "contradiction": r"split[- ]adjusted|closeunadj"}
D = dt.date.fromisoformat

# ticker, permaticker, name, first, last, splits {date: new shares per old}, sp500 (added, removed), delisting
ACTIVE = [
    ("AAPL", 199059, "Apple Inc", None, None, {"2014-06-09": 7, "2020-08-31": 4}, (None, None)),
    ("MSFT", 194319, "Microsoft Corp", None, None, {}, (None, None)),
    ("IBM", 194362, "International Business Machines Corp", None, None, {}, (None, None)),
    ("KO", 194212, "Coca-Cola Co", None, None, {"2012-08-13": 2}, (None, None)),
    ("XOM", 194290, "Exxon Mobil Corp", None, None, {}, (None, None)),
    ("JNJ", 194356, "Johnson & Johnson", None, None, {}, (None, None)),
    ("PG", 194327, "Procter & Gamble Co", None, None, {}, (None, None)),
    ("JPM", 194395, "JPMorgan Chase & Co", None, None, {}, (None, None)),
    ("WMT", 194425, "Walmart Inc", None, None, {"2024-02-26": 3}, (None, None)),
    ("PFE", 194398, "Pfizer Inc", None, None, {}, (None, None)),
    ("MRK", 194351, "Merck & Co Inc", None, None, {}, (None, None)),
    ("CVX", 194277, "Chevron Corp", None, None, {}, (None, None)),
    ("INTC", 194448, "Intel Corp", None, None, {}, (None, None)),
    ("CSCO", 198929, "Cisco Systems Inc", None, None, {}, (None, None)),
    ("ORCL", 196937, "Oracle Corp", None, None, {}, (None, None)),
    ("T", 194229, "AT&T Inc", None, None, {}, (None, None)),
    ("VZ", 194334, "Verizon Communications Inc", None, None, {}, (None, None)),
    ("HD", 194367, "Home Depot Inc", None, None, {}, (None, None)),
    ("MCD", 194310, "McDonald's Corp", None, None, {}, (None, None)),
    ("DIS", 194281, "Walt Disney Co", None, None, {}, (None, None)),
    ("BA", 194245, "Boeing Co", None, None, {}, (None, None)),
    ("CAT", 194263, "Caterpillar Inc", None, None, {}, (None, None)),
    ("MMM", 194300, "3M Co", None, None, {}, (None, None)),
    ("GE", 194288, "General Electric Co", None, None, {"2021-08-02": 0.125}, (None, None)),
    ("GS", 199823, "Goldman Sachs Group Inc", None, None, {}, (None, None)),
    ("AMZN", 199145, "Amazon.com Inc", None, None, {"2022-06-06": 20}, (None, None)),
    ("GOOGL", 199631, "Alphabet Inc", None, None, {"2022-07-18": 20}, (None, None)),
    ("NVDA", 199533, "NVIDIA Corp", None, None, {"2007-09-11": 1.5, "2021-07-20": 4, "2024-06-10": 10}, (None, None)),
    ("META", 194817, "Meta Platforms Inc", "2012-05-18", None, {}, ("2013-12-23", None)),
    ("TSLA", 195222, "Tesla Inc", "2010-06-29", None, {"2020-08-31": 5, "2022-08-25": 3}, ("2020-12-21", None)),
    ("NFLX", 194916, "Netflix Inc", None, None, {"2015-07-15": 7}, ("2010-12-20", None)),
    ("BUD", 637212, "Anheuser-Busch InBev SA/NV (ADR)", "2009-09-16", None, {}, ("never", None)),
]
DELISTED = [  # ticker, permaticker, name, last price date, action, acquirer
    ("BUD", 196201, "Anheuser-Busch Companies Inc", "2008-11-18", "acquisitionby", ("ABI", "InBev NV")),
    ("DNA", 197842, "Genentech Inc", "2009-03-26", "acquisitionby", ("RHHBY", "Roche Holding AG")),
    ("WB", 194413, "Wachovia Corp", "2008-12-31", "acquisitionby", ("WFC", "Wells Fargo & Co")),
    ("LEH", 196622, "Lehman Brothers Holdings Inc", "2008-09-17", "bankruptcyliquidation", None),
    ("BSC", 196190, "Bear Stearns Companies Inc", "2008-05-30", "acquisitionby", ("JPM", "JPMorgan Chase & Co")),
    ("CFC", 194990, "Countrywide Financial Corp", "2008-07-01", "acquisitionby", ("BAC", "Bank of America Corp")),
    ("SGP", 194379, "Schering-Plough Corp", "2009-11-03", "mergerto", ("MRK", "Merck & Co Inc")),
    ("EK", 194284, "Eastman Kodak Co", "2012-01-19", "bankruptcyliquidation", None),
]
SP500_REMOVED = {"EK": "2010-12-20", "LEH": "2008-09-16"}
DIVIDEND_PAYERS = {"AAPL": "2012-08-09", "KO": None, "XOM": None, "JNJ": None, "PG": None, "MSFT": None, "IBM": None,
                   "PFE": None, "MRK": None, "CVX": None, "T": None, "VZ": None, "MCD": None, "WMT": None}
FILLERS = 464  # synthetic constant members, so daily membership counts land near 500
COLUMNS = {
    "sep": ["ticker", "date", "open", "high", "low", "close", "volume", "closeadj", "closeunadj", "lastupdated"],
    "tickers": ["table", "permaticker", "ticker", "name", "exchange", "isdelisted", "category", "sector",
                "firstpricedate", "lastpricedate", "relatedtickers", "currency", "lastupdated"],
    "actions": ["date", "action", "ticker", "name", "value", "contraticker", "contraname"],
    "sp500": ["date", "action", "ticker", "name", "contraticker", "contraname", "note"],
}
TABLE_ALIASES = {"stocks": "sep", "sep": "sep", "prices": "sep", "daily": "sep", "tickers": "tickers",
                 "actions": "actions", "sp500": "sp500"}


def _days(a, b):
    d = a
    while d <= b:
        if d.weekday() < 5:
            yield d
        d += dt.timedelta(days=1)


def _securities():
    out = []
    for t, perm, name, first, last, splits, (added, removed) in ACTIVE:
        out.append({"ticker": t, "permaticker": perm, "name": name, "first": D(first) if first else START,
                    "last": None, "splits": {D(k): v for k, v in splits.items()},
                    "added": None if added == "never" else D(added) if added else START, "never": added == "never",
                    "removed": None, "action": None, "contra": None, "related": "FB" if t == "META" else ""})
    for t, perm, name, last, action, contra in DELISTED:
        out.append({"ticker": t, "permaticker": perm, "name": name, "first": START, "last": D(last), "splits": {},
                    "added": START, "never": False, "removed": D(SP500_REMOVED.get(t, last)), "action": action,
                    "contra": contra, "related": ""})
    return out


SECURITIES = _securities()
_SERIES = {}


def _dividends(s):
    if s["ticker"] not in DIVIDEND_PAYERS or s["never"]:
        return []
    first = D(DIVIDEND_PAYERS[s["ticker"]]) if DIVIDEND_PAYERS[s["ticker"]] else dt.date(2007, 2, 8)
    out, d = [], first
    while d <= (s["last"] or END):
        out.append(d + dt.timedelta(days=max(0, d.weekday() - 4) and 7 - d.weekday()))  # weekends → Monday
        m = d.month + 3
        d = dt.date(d.year + (m - 1) // 12, (m - 1) % 12 + 1, min(d.day, 28))
    return out


def series(s):
    """SEP rows for one security (cached): split-adjusted OHLCV as of today, raw `closeunadj`, `closeadj`."""
    key = (s["ticker"], s["permaticker"])
    if key in _SERIES:
        return _SERIES[key]
    rng = random.Random(s["permaticker"])
    total = math.prod(s["splits"].values()) if s["splits"] else 1
    divs = _dividends(s)
    value, rows = 20 + rng.random() * 180, []
    for d in _days(s["first"], s["last"] or END):
        value *= math.exp(rng.gauss(0.0003, 0.018))
        shares = math.prod(v for k, v in s["splits"].items() if k <= d) if s["splits"] else 1
        raw = value / shares
        close = value / total
        div_factor = 0.996 ** sum(1 for x in divs if x > d)
        o = close * (1 + rng.gauss(0, 0.004))
        rows.append({"ticker": s["ticker"], "date": d.isoformat(), "open": round(o, 4),
                     "high": round(max(o, close) * (1 + abs(rng.gauss(0, 0.006))), 4),
                     "low": round(min(o, close) * (1 - abs(rng.gauss(0, 0.006))), 4), "close": round(close, 4),
                     "volume": round(rng.uniform(2e6, 4e7) * total / shares), "closeadj": round(close * div_factor, 4),
                     "closeunadj": round(raw, 4), "lastupdated": END.isoformat()})
    _SERIES[key] = rows
    return rows


def tickers_rows():
    return [{"table": "SEP", "permaticker": s["permaticker"], "ticker": s["ticker"], "name": s["name"],
             "exchange": "NYSE",
             "isdelisted": "Y" if s["last"] else "N",
             "category": "ADR Common Stock" if s["never"] else "Domestic Common Stock", "sector": "",
             "firstpricedate": s["first"].isoformat(), "lastpricedate": (s["last"] or END).isoformat(),
             "relatedtickers": s["related"], "currency": "USD", "lastupdated": END.isoformat()} for s in SECURITIES]


def actions_rows():
    out = []
    for s in SECURITIES:
        for d, ratio in sorted(s["splits"].items()):
            out.append({"date": d.isoformat(), "action": "split", "ticker": s["ticker"], "name": s["name"],
                        "value": round(1 / ratio, 6), "contraticker": "", "contraname": ""})
        for d in _dividends(s):
            out.append({"date": d.isoformat(), "action": "dividend", "ticker": s["ticker"], "name": s["name"],
                        "value": 0.25, "contraticker": "", "contraname": ""})
        if s["last"]:
            ct, cn = s["contra"] or ("", "")
            out.append({"date": s["last"].isoformat(), "action": s["action"], "ticker": s["ticker"], "name": s["name"],
                        "value": "", "contraticker": ct, "contraname": cn})
            out.append({"date": s["last"].isoformat(), "action": "delisted", "ticker": s["ticker"], "name": s["name"],
                        "value": "", "contraticker": "", "contraname": ""})
    out.append({"date": "2022-06-09", "action": "tickerchangefrom", "ticker": "META", "name": "Meta Platforms Inc",
                "value": "", "contraticker": "FB", "contraname": "Facebook Inc"})
    out.append({"date": "2022-06-09", "action": "tickerchangeto", "ticker": "FB", "name": "Facebook Inc",
                "value": "", "contraticker": "META", "contraname": "Meta Platforms Inc"})
    return sorted(out, key=lambda r: (r["date"], r["ticker"], r["action"]))


def sp500_rows():
    """`historical` rows for the members on 2007-01-03, then `added` and `removed`; plus `current` rows today."""
    out = []
    members = [s for s in SECURITIES if not s["never"]]
    for s in members:
        if s["added"] == START:
            out.append({"date": START.isoformat(), "action": "historical", "ticker": s["ticker"], "name": s["name"],
                        "contraticker": "", "contraname": "", "note": ""})
        elif s["added"]:
            out.append({"date": s["added"].isoformat(), "action": "added", "ticker": s["ticker"], "name": s["name"],
                        "contraticker": "", "contraname": "", "note": ""})
        if s["removed"]:
            out.append({"date": s["removed"].isoformat(), "action": "removed", "ticker": s["ticker"], "name": s["name"],
                        "contraticker": "", "contraname": "", "note": ""})
        elif s["added"]:
            out.append({"date": END.isoformat(), "action": "current", "ticker": s["ticker"], "name": s["name"],
                        "contraticker": "", "contraname": "", "note": ""})
    for i in range(1, FILLERS + 1):
        t = f"X{i:03d}"
        for action, d in (("historical", START), ("current", END)):
            out.append({"date": d.isoformat(), "action": action, "ticker": t, "name": f"Synthetic member {i:03d}",
                        "contraticker": "", "contraname": "", "note": ""})
    return sorted(out, key=lambda r: (r["date"], r["ticker"], r["action"]))


def table_rows(table, params):
    if table == "sep":
        want = _list(params.get("ticker"))
        perms = _list(params.get("permaticker"))
        rows = []  # both BUDs share the ticker: SEP returns both series, told apart by date
        for s in SECURITIES:
            if want and s["ticker"] not in want:
                continue
            if perms and str(s["permaticker"]) not in perms:
                continue
            if not want and not perms:
                continue  # no full-table dumps outside bulk
            rows += series(s)
    elif table == "tickers":
        rows = tickers_rows()
    elif table == "actions":
        rows = actions_rows()
    else:
        rows = sp500_rows()
    return [r for r in rows if _match(r, params, table)]


def _list(v):
    return [x.strip().upper() if not x.strip().isdigit() else x.strip() for x in (v or "").split(",") if x.strip()]


def _match(r, p, table):
    if table != "sep" and p.get("ticker") and r.get("ticker") not in _list(p["ticker"]):
        return False
    if p.get("permaticker") and "permaticker" in r and str(r["permaticker"]) not in _list(p["permaticker"]):
        return False
    for k in ("action", "isdelisted"):
        if p.get(k) and str(r.get(k, "")).lower() not in [x.lower() for x in _list(p[k])]:
            return False
    d = r.get("date") or r.get("firstpricedate")
    if "date" in r:
        lo = p.get("date.gte") or p.get("from") or p.get("date_gte")
        hi = p.get("date.lte") or p.get("to") or p.get("date_lte")
        if p.get("date") and d != p["date"]:
            return False
        if lo and d < lo or hi and d > hi:
            return False
        if p.get("date.gt") and d <= p["date.gt"] or p.get("date.lt") and d >= p["date.lt"]:
            return False
    return True


def new_state():
    return {}


def key_of(req):
    return req["params"].get("api_key") or req["headers"].get("X-Api-Key") or req["headers"].get("x-api-key") or ""


def _table_name(path):
    parts = [re.sub(r"\.(json|csv)$", "", x).lower() for x in path.split("/") if x]
    for x in reversed(parts):
        if x in TABLE_ALIASES:
            return TABLE_ALIASES[x]
    return None


def handle(req, state):
    """(status, content type, body, log note)."""
    p, path = req["params"], req["path"]
    ndl = "datatables" in path.lower()
    table = _table_name(path)
    note = {"table": table, "style": "ndl" if ndl else "sharadar"}
    if not key_of(req):
        return 403, "application/json", json.dumps({"error": {"code": "missing_api_key", "message": "api_key is required"}}), note
    if not table:
        return 404, "application/json", json.dumps({"error": {"code": "not_found", "message": f"no table at {path}"}}), note
    cols = COLUMNS[table]
    if p.get("status", "").lower() == "true" or p.get("qopts.export", "").lower() == "true":
        n = {"sep": 5_100_000, "tickers": 40, "actions": 2_400, "sp500": 1_000}[table]
        size = n * (96 if table == "sep" else 140)
        note["bulk"] = True
        if ndl:
            return 200, "application/json", json.dumps({"datatable_bulk_download": {"file": {
                "status": "fresh", "link": f"http://127.0.0.1/bulk/{table}.zip", "data_snapshot_time": f"{END} 21:00:00 UTC",
                "file_size": size}, "datatable": {"last_refreshed_time": f"{END} 21:00:00 UTC"}}}), note
        return 200, "application/json", json.dumps({"table": table.upper(), "status": "fresh", "rows": n,
                                                    "file_size": size, "years": p.get("years", "full")}), note
    rows = table_rows(table, p)
    pick = [c for c in (p.get("qopts.columns") or p.get("columns") or "").split(",") if c in cols] or cols
    cursor = int(p.get("cursor") or p.get("qopts.cursor_id") or 0)
    page, nxt = rows[cursor:cursor + PAGE], (cursor + PAGE if cursor + PAGE < len(rows) else None)
    note.update(rows=len(page), tickers=sorted({str(r.get("ticker")) for r in page})[:12])
    if ndl:
        types = {"date": "Date", "ticker": "String", "volume": "BigDecimal(15,0)"}
        return 200, "application/json", json.dumps({
            "datatable": {"data": [[r.get(c) for c in pick] for r in page],
                          "columns": [{"name": c, "type": types.get(c, "BigDecimal(15,4)" if table == "sep" else "String")} for c in pick]},
            "meta": {"next_cursor_id": str(nxt) if nxt is not None else None}}), note
    if (p.get("format") or "csv").lower() == "json":
        body = [{c: r.get(c) for c in pick} for r in page]
        if nxt is not None:
            note["next_cursor"] = nxt
            return 200, "application/json", json.dumps({"data": body, "next_cursor": nxt}), note
        return 200, "application/json", json.dumps(body), note
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=pick, extrasaction="ignore")
    w.writeheader()
    w.writerows(page)
    return 200, "text/csv", buf.getvalue(), note
