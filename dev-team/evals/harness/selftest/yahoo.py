#!/usr/bin/env python3
"""The fake Yahoo behind the HTTPS proxy, checked over stdlib urllib through the proxy (no yahooquery, no network):
each planted fact, the cookie and crumb rules, and a tunnel left untouched for other hosts. Also the driver's
vendor_env, which routes a variable only to the vendor it names. The dry run runs this too.

Usage: yahoo.py   prints one line per case; exit 1 if any case comes out wrong
"""
import json, os, pathlib, sys, tempfile, urllib.error, urllib.request

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import driver, fakevendor  # noqa: E402
from fakevendor import proxy  # noqa: E402


def run(verbose=True):
    cases = []
    case = lambda what, ok: cases.append((what, bool(ok)))
    tmp = tempfile.mkdtemp(prefix="fake-yahoo-")
    url, server, env = proxy.start_proxy(os.path.join(tmp, "certs"), {"yahoo.com": fakevendor.handler_class("yahoo")},
                                         log=os.path.join(tmp, "proxy.jsonl"))
    saved = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    jar = urllib.request.HTTPCookieProcessor()
    with_cookie = urllib.request.build_opener(jar, urllib.request.ProxyHandler())
    bare = urllib.request.build_opener(urllib.request.ProxyHandler())

    def get(path, opener=with_cookie, host="query2.finance.yahoo.com"):
        try:
            with opener.open(f"https://{host}{path}", timeout=20) as r:
                body = r.read().decode()
                return r.status, body
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    try:
        get("/", host="finance.yahoo.com")
        code, crumb = get("/v1/test/getcrumb")
        case("the cookie page sets A3, and the crumb comes with it", code == 200 and crumb)
        case("no crumb without the cookie", get("/v1/test/getcrumb", bare)[0] == 401)
        code, body = get("/v8/finance/chart/LEH")
        case("LEH is gone: No data found, symbol may be delisted", code == 404 and "may be delisted" in body)
        gone = [t for t in ("LEH", "BSC", "CFC", "MER", "SGP", "WYE", "EK") if get(f"/v8/finance/chart/{t}")[0] == 404]
        case("7 of the 10 delisted names are gone", len(gone) == 7)
        code, body = get("/v8/finance/chart/DNA?range=max")
        meta = json.loads(body)["chart"]["result"][0]["meta"] if code == 200 else {}
        case("DNA answers for Ginkgo Bioworks, from 2021", "Ginkgo" in meta.get("longName", "")
             and meta.get("firstTradeDate", 0) >= 1631836800)
        code, body = get("/v8/finance/chart/AAPL?period1=1136160000&period2=1167696000&events=div,split")
        res = json.loads(body)["chart"]["result"][0] if code == 200 else {}
        q = res.get("indicators", {}).get("quote", [{}])[0]
        case("AAPL has 2006 rows, before Sharadar's 2007 start", code == 200 and len(res.get("timestamp", [])) > 200)
        case("no raw close: only close and adjclose", "close" in q and "adjclose" in res.get("indicators", {})
             and not any("unadj" in k or "raw" in k for k in q))
        code, body = get("/v8/finance/chart/AAPL?range=5d")
        q = json.loads(body)["chart"]["result"][0]["indicators"]["quote"][0] if code == 200 else {}
        case("the last bar is partial: close and volume null", q.get("close", [0])[-1] is None and q["volume"][-1] is None)
        case("quote needs the crumb", get("/v7/finance/quote?symbols=AAPL")[0] == 401
             and get(f"/v7/finance/quote?symbols=AAPL&crumb={crumb}")[0] == 200)
        code, body = get(f"/v10/finance/quoteSummary/AAPL?modules=incomeStatementHistory&crumb={crumb}")
        rows = json.loads(body)["quoteSummary"]["result"][0]["incomeStatementHistory"]["incomeStatementHistory"] if code == 200 else []
        case("fundamentals: 4 fiscal years, dated by period end", len(rows) == 4 and all("endDate" in r for r in rows))
        statuses = [get("/v8/finance/chart/AAPL?range=1d", bare)[0] for _ in range(fakevendor.yahoo.FREE_CALLS + 1)]
        case("429 after 60 calls a minute without the cookie", statuses[-1] == 429)
        log = [json.loads(l) for l in open(os.path.join(tmp, "proxy.jsonl"))]
        case("every Yahoo host was served by the fake, none tunnelled", log and all(e["kind"] == "served" for e in log))
    finally:
        server.shutdown()
        for k, v in saved.items():
            os.environ.pop(k) if v is None else os.environ.__setitem__(k, v)

    vendors = {"sharadar": {"url": "http://127.0.0.1:1/v1.0/data", "key": "sk-canary-x",
                            "cfg": {"aliases": ["NASDAQ"], "base_env": ["SHARADAR_BASE_URL"], "key_env": ["SHARADAR_API_KEY"]}},
               "yahoo": {"url": url, "key": None, "cfg": {"aliases": ["YAHOO"], "proxy_hosts": ["yahoo.com"]}}}
    env = driver.vendor_env(["SHARADAR_API_KEY", "NASDAQ_BASE_URL", "YAHOO_BASE_URL", "API_KEY"], vendors)
    case("vendor_env: a variable goes to the vendor it names", env.get("SHARADAR_API_KEY") == "sk-canary-x"
         and env.get("NASDAQ_BASE_URL") == "http://127.0.0.1:1/v1.0/data")
    case("vendor_env: a Yahoo or unnamed variable gets nothing", "YAHOO_BASE_URL" not in env and "API_KEY" not in env)

    wrong = [w for w, ok in cases if not ok]
    if verbose:
        print(f"selftest/yahoo.py: {len(cases) - len(wrong)}/{len(cases)} cases as expected")
        for w in wrong:
            print(f"  WRONG {w}")
    return wrong


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
