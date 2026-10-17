"""Fake Yahoo Finance, as the unofficial API yahooquery and yfinance call (design/probes.md §10.1). Served behind
`proxy.py` on Yahoo's own hosts (`finance.yahoo.com`, `fc.yahoo.com`, `query1`/`query2.finance.yahoo.com`), since those
clients take no base URL.

Paths: the cookie pages (any path on `finance.yahoo.com` or `fc.yahoo.com` sets an `A3` cookie), `/v1/test/getcrumb`
(needs the cookie), `/v8/finance/chart/<symbol>` (`period1`, `period2`, `range`, `interval=1d|1wk|1mo`,
`events=div,split`), `/v7/finance/quote?symbols=` and `/v10/finance/quoteSummary/<symbol>?modules=` (both need the
crumb), `/ws/fundamentals-timeseries/v1/finance/timeseries/<symbol>?type=annual…` and `/v1/finance/search?q=`.
Prices are Sharadar's fake series (`sharadar.series`), so a cross-check compares like with like.

Planted facts (what a guess gets wrong):
- No raw close: `close` is split-adjusted as of today and `adjclose` also takes out dividends; raw prices can only be
  rebuilt from the split events.
- Of the persona's 10 delisted names, 7 are gone ("No data found, symbol may be delisted"): LEH, BSC, CFC, MER, SGP,
  WYE, EK. BUD, DNA and WB answer, but for today's holder of the ticker: AB InBev's ADR (from 2009-09-16), Ginkgo
  Bioworks (from 2021-09-17) and Weibo (from 2014-04-17), with nothing earlier. FB is gone too (META holds the series).
- History reaches 2000-01-03 for names listed by then, before Sharadar's 2007 start.
- Fundamentals (quoteSummary statements, the timeseries API) cover only the last 4 fiscal years, dated by period end,
  never by filing date: not point-in-time.
- Without the cookie, a client gets 429 "Too Many Requests" after 60 calls a minute; the quote and quoteSummary
  endpoints answer 401 "Invalid Crumb" without the crumb.
- A range reaching the last day ends with a partial bar whose close and volume are null.
"""
import datetime as dt, json, math, random, re, time

from . import sharadar as sh

SECRET_PARAMS = ("crumb",)
HOSTS = ["yahoo.com"]
START = dt.date(2000, 1, 3)
END = sh.END
GONE = ["LEH", "BSC", "CFC", "MER", "SGP", "WYE", "EK", "FB"]
REUSED = {  # ticker: (today's holder, first day it trades under the ticker)
    "BUD": ("Anheuser-Busch InBev SA/NV", "2009-09-16"),
    "DNA": ("Ginkgo Bioworks Holdings, Inc.", "2021-09-17"),
    "WB": ("Weibo Corporation", "2014-04-17"),
}
REUSED_PERMA = {"DNA": 731102, "WB": 652214}
FREE_CALLS = 60
CRUMB = "fakeCrumb0Yh"
PLANTED = {"adjusted_only": r"no raw|adjusted[- ]only|only (split[- ])?adjusted|split[- ]adjusted",
           "reused": r"Ginkgo|Weibo|InBev|re-?used|reassigned|different compan",
           "missing": ["LEH", "BSC", "CFC", "MER", "SGP", "WYE", "EK"],
           "not_pit": r"period[- ]end|filing date|not point[- ]in[- ]time|four (fiscal )?years|4 (fiscal )?years"}
D = dt.date.fromisoformat


def new_state():
    return {"calls": [], "cookies": set()}


def key_of(req):
    return ""  # Yahoo takes no key


def _security(symbol):
    """(the Sharadar security behind a Yahoo symbol, its first Yahoo day), or (None, None) when Yahoo has nothing."""
    s = symbol.upper()
    if s in GONE:
        return None, None
    if s in REUSED:
        first = D(REUSED[s][1])
        match = [x for x in sh.SECURITIES if x["ticker"] == s and not x["last"]]
        return (match[0] if match else {"ticker": s, "permaticker": REUSED_PERMA[s], "name": REUSED[s][0],
                                        "first": first, "last": None, "splits": {}, "never": True}), first
    match = [x for x in sh.SECURITIES if x["ticker"] == s and not x["last"]]
    if not match:
        return None, None
    x = match[0]
    return x, (x["first"] if x["first"] > sh.START else START)


_EARLY = {}


def _rows(sec, first):
    """Daily rows {date, open, high, low, close, adjclose, volume}: Sharadar's series, plus synthetic rows from 2000
    that end where Sharadar's begin."""
    rows = [{"date": r["date"], "open": r["open"], "high": r["high"], "low": r["low"], "close": r["close"],
             "adjclose": r["closeadj"], "volume": r["volume"]} for r in sh.series(sec) if r["date"] >= first.isoformat()]
    if first < sh.START and rows:
        key = sec["ticker"]
        if key not in _EARLY:
            rng, value, early = random.Random(f"yahoo-{key}"), rows[0]["close"], []
            for d in reversed(list(sh._days(first, sh.START - dt.timedelta(days=1)))):
                value /= math.exp(rng.gauss(0.0003, 0.018))
                early.append({"date": d.isoformat(), "open": round(value, 4), "high": round(value * 1.006, 4),
                              "low": round(value * 0.994, 4), "close": round(value, 4),
                              "adjclose": round(value * rows[0]["adjclose"] / rows[0]["close"], 4),
                              "volume": rng.randint(2_000_000, 40_000_000)})
            _EARLY[key] = list(reversed(early))
        rows = _EARLY[key] + rows
    return rows


def _epoch(d):
    return int(dt.datetime(d.year, d.month, d.day, 14, 30, tzinfo=dt.timezone.utc).timestamp())


def _day(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def _json(code, obj, note, **headers):
    return code, "application/json", json.dumps(obj), {**note, "_headers": headers} if headers else note


def _error(code, kind, desc, note, field="chart"):
    return _json(code, {field: {"result": None, "error": {"code": kind, "description": desc}}}, note)


RANGES = {"1d": 1, "5d": 7, "1mo": 31, "3mo": 92, "6mo": 183, "1y": 366, "2y": 731, "5y": 1827, "10y": 3653}


def chart(symbol, p, note):
    sec, first = _security(symbol)
    if sec is None:
        return _error(404, "Not Found", "No data found, symbol may be delisted", note)
    interval = p.get("interval", "1d")
    if interval not in ("1d", "1wk", "1mo"):
        return _error(422, "Unprocessable Entity", f"Invalid input - interval={interval} is not supported", note)
    if p.get("range") and p["range"] in RANGES:
        hi, lo = END, END - dt.timedelta(days=RANGES[p["range"]])
    elif p.get("range") == "max":
        hi, lo = END, START
    else:
        lo = _day(p.get("period1", 0)) if p.get("period1") else END - dt.timedelta(days=7)
        hi = _day(p.get("period2")) if p.get("period2") else END
    rows = [r for r in _rows(sec, first) if lo.isoformat() <= r["date"] <= hi.isoformat()]
    if interval != "1d":
        step = 5 if interval == "1wk" else 21
        rows = rows[::step]
    partial = bool(rows) and rows[-1]["date"] == END.isoformat()
    q = {k: [r[k] for r in rows] for k in ("open", "high", "low", "close", "volume")}
    if partial:  # today's bar is still forming
        q["close"][-1] = q["volume"][-1] = None
    events = {}
    want = (p.get("events") or "").lower()
    if "split" in want:
        events["splits"] = {str(_epoch(d)): {"date": _epoch(d), "numerator": ratio, "denominator": 1,
                                             "splitRatio": f"{ratio:g}:1"}
                            for d, ratio in sec.get("splits", {}).items() if lo <= d <= hi}
    if "div" in want:
        events["dividends"] = {str(_epoch(d)): {"date": _epoch(d), "amount": 0.25}
                               for d in sh._dividends(sec) if lo <= d <= hi}
    name = REUSED.get(symbol.upper(), (sec["name"],))[0]
    meta = {"currency": "USD", "symbol": symbol.upper(), "exchangeName": "NYQ", "fullExchangeName": "NYSE",
            "instrumentType": "EQUITY", "firstTradeDate": _epoch(first), "regularMarketTime": _epoch(END),
            "gmtoffset": -14400, "timezone": "EDT", "exchangeTimezoneName": "America/New_York",
            "longName": name, "shortName": name[:30], "dataGranularity": interval,
            "regularMarketPrice": rows[-2]["close"] if len(rows) > 1 else None}
    result = {"meta": meta, "timestamp": [_epoch(D(r["date"])) for r in rows],
              "indicators": {"quote": [q], "adjclose": [{"adjclose": [r["adjclose"] for r in rows]}]}}
    if events:
        result["events"] = events
    note.update(symbol=symbol.upper(), rows=len(rows), partial_bar=partial)
    return _json(200, {"chart": {"result": [result], "error": None}}, note)


def _quote(symbol):
    sec, first = _security(symbol)
    if sec is None:
        return None
    name = REUSED.get(symbol.upper(), (sec["name"],))[0]
    last = _rows(sec, first)[-2]
    return {"symbol": symbol.upper(), "longName": name, "shortName": name[:30], "quoteType": "EQUITY",
            "exchange": "NYQ", "currency": "USD", "regularMarketPrice": last["close"],
            "firstTradeDateMilliseconds": _epoch(first) * 1000}


STATEMENTS = ("incomeStatementHistory", "balanceSheetHistory", "cashflowStatementHistory")


def _statements(symbol):
    """Four fiscal years, newest first, dated by period end only."""
    rng = random.Random(f"fund-{symbol}")
    out = []
    for y in range(END.year - 1, END.year - 5, -1):
        out.append({"endDate": {"raw": _epoch(dt.date(y, 12, 31)), "fmt": f"{y}-12-31"},
                    "totalRevenue": {"raw": rng.randint(10**9, 10**11)}, "netIncome": {"raw": rng.randint(10**8, 10**10)},
                    "totalAssets": {"raw": rng.randint(10**10, 10**12)}})
    return out


def quote_summary(symbol, p, note):
    q = _quote(symbol)
    if q is None:
        return _error(404, "Not Found", f"Quote not found for symbol: {symbol.upper()}", note, "quoteSummary")
    out = {}
    for m in (p.get("modules") or "price").split(","):
        if m == "price":
            out["price"] = {"symbol": q["symbol"], "longName": q["longName"], "currency": "USD",
                            "regularMarketPrice": {"raw": q["regularMarketPrice"]}}
        elif m in ("assetProfile", "summaryProfile"):
            out[m] = {"sector": "", "industry": "", "longBusinessSummary": f"{q['longName']}."}
        elif m in STATEMENTS:
            key = {"incomeStatementHistory": "incomeStatementHistory", "balanceSheetHistory": "balanceSheetStatements",
                   "cashflowStatementHistory": "cashflowStatements"}[m]
            out[m] = {key: _statements(symbol)}
    note.update(symbol=symbol.upper(), modules=sorted(out))
    return _json(200, {"quoteSummary": {"result": [out], "error": None}}, note)


def timeseries(symbol, p, note):
    if _quote(symbol) is None:
        return _json(200, {"timeseries": {"result": [], "error": None}}, note)
    result = []
    for t in (p.get("type") or "annualTotalRevenue").split(","):
        rows = [{"asOfDate": f"{y}-12-31", "periodType": "12M", "currencyCode": "USD",
                 "reportedValue": {"raw": r["totalRevenue"]["raw"], "fmt": f"{r['totalRevenue']['raw'] / 1e9:.2f}B"}}
                for y, r in zip(range(END.year - 4, END.year), reversed(_statements(symbol)))]
        result.append({"meta": {"symbol": [symbol.upper()], "type": [t]}, t: rows,
                       "timestamp": [_epoch(D(r["asOfDate"])) for r in rows]})
    note.update(symbol=symbol.upper(), types=len(result))
    return _json(200, {"timeseries": {"result": result, "error": None}}, note)


def search(p, note):
    q = (p.get("q") or "").strip().upper()
    hits = []
    for t in sorted({x["ticker"] for x in sh.SECURITIES} | set(REUSED)):
        quote = _quote(t)
        if quote and (q == t or q and q.lower() in quote["longName"].lower()):
            hits.append({"symbol": t, "shortname": quote["shortName"], "longname": quote["longName"],
                         "quoteType": "EQUITY", "exchange": "NYQ"})
    note.update(q=q, hits=len(hits))
    return _json(200, {"count": len(hits), "quotes": hits, "news": []}, note)


def handle(req, state):
    host = (req["headers"].get("Host") or "").split(":")[0].lower()
    path, p = req["path"], req["params"]
    note = {"host": host}
    cookie = "A3=" in (req["headers"].get("Cookie") or "")
    now = time.time()
    state["calls"] = [t for t in state["calls"] if now - t < 60] + [now]
    if not host.startswith(("query1.", "query2.")):  # the pages clients visit for a cookie
        return 200 if host != "fc.yahoo.com" else 404, "text/html", "<html><body>Yahoo Finance</body></html>", \
            {**note, "_headers": {"Set-Cookie": "A3=d=fake&S=fake; Domain=.yahoo.com; Path=/; Secure"}}
    if not cookie and len(state["calls"]) > FREE_CALLS:
        return 429, "text/plain", "Too Many Requests", {**note, "throttled": True}
    if path.startswith("/v1/test/getcrumb"):
        return (200, "text/plain", CRUMB, note) if cookie else (401, "text/plain", "", note)
    m = re.match(r"^/v8/finance/chart/([^/]+)$", path)
    if m:
        return chart(m.group(1), p, note)
    needs_crumb = path.startswith(("/v7/finance/quote", "/v10/finance/quoteSummary/"))
    if needs_crumb and p.get("crumb") != CRUMB:
        field = "quoteResponse" if path.startswith("/v7") else "quoteSummary"
        return _error(401, "Unauthorized", "Invalid Crumb", note, field)
    if path.startswith("/v7/finance/quote"):
        res = [q for s in (p.get("symbols") or "").split(",") if s and (q := _quote(s))]
        note.update(symbols=p.get("symbols", ""), found=len(res))
        return _json(200, {"quoteResponse": {"result": res, "error": None}}, note)
    m = re.match(r"^/v10/finance/quoteSummary/([^/]+)$", path)
    if m:
        return quote_summary(m.group(1), p, note)
    m = re.match(r"^/ws/fundamentals-timeseries/v1/finance/(?:premium/)?timeseries/([^/]+)$", path)
    if m:
        return timeseries(m.group(1), p, note)
    if path.startswith("/v1/finance/search"):
        return search(p, note)
    return _error(404, "Not Found", "HTTP 404 Not Found", note, "finance")
