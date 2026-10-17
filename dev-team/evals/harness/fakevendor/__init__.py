"""Local fake vendors for the probe evals (design/probes.md §10): stdlib HTTP servers on 127.0.0.1 that serve a
vendor's documented endpoints from a small planted dataset whose facts differ from the obvious guesses.

- `sharadar`: SEP prices, TICKERS, ACTIONS and SP500 (§10.1), on Sharadar's own API paths and the Nasdaq Data
  Link datatable paths alike. Planted: `close` is split-adjusted and only `closeunadj` is raw; every table starts
  in 2007; 2 of the persona's 10 delisted names are missing; `BUD` resolves to two permatickers.
- `plaid`: institutions, link and sandbox tokens, `/accounts/get` and `/transactions/sync` with pagination and one
  planted mutation error (§10.2). Responses carry redaction canaries (an account name, an amount, a card-like
  number, an email) that must never reach evidence.

`start(name, log=None, expect_key=None)` serves one in a daemon thread and returns `(base_url, server)`; call
`server.shutdown()` to stop. Every request is logged as one JSON line (the key never: only whether one was sent
and whether it was `expect_key`). `python3 -m fakevendor <name> [--port N] [--log F]` serves one in the foreground.
"""
import json, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import plaid, sharadar

VENDORS = {"sharadar": sharadar, "plaid": plaid}


class _Handler(BaseHTTPRequestHandler):
    vendor = None
    log_path = None
    expect_key = None
    state = None

    def log_message(self, *a):  # quiet
        pass

    def _respond(self, method):
        url = urllib.parse.urlsplit(self.path)
        params = {k: v[-1] for k, v in urllib.parse.parse_qs(url.query, keep_blank_values=True).items()}
        body = {}
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            raw = self.rfile.read(n)
            try:
                body = json.loads(raw)
            except ValueError:
                body = {k: v[-1] for k, v in urllib.parse.parse_qs(raw.decode(errors="ignore")).items()}
        req = {"method": method, "path": url.path, "params": params, "body": body, "headers": dict(self.headers)}
        code, ctype, payload, note = self.vendor.handle(req, self.state)
        key = self.vendor.key_of(req)
        if self.log_path:
            entry = {"t": round(time.time(), 3), "method": method, "path": url.path,
                     "params": {k: v for k, v in params.items() if k not in self.vendor.SECRET_PARAMS},
                     "key_sent": bool(key), "key_ok": bool(key) and (self.expect_key is None or key == self.expect_key),
                     "status": code, **note}
            with self.state["lock"]:
                with open(self.log_path, "a") as f:
                    f.write(json.dumps(entry) + "\n")
        data = payload if isinstance(payload, bytes) else payload.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._respond("GET")

    def do_POST(self):
        self._respond("POST")


def start(name, log=None, expect_key=None, port=0):
    vendor = VENDORS[name]
    handler = type(f"{name}Handler", (_Handler,), {"vendor": vendor, "log_path": str(log) if log else None,
                                                    "expect_key": expect_key,
                                                    "state": {"lock": threading.Lock(), **vendor.new_state()}})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}", server


def read_log(path):
    try:
        return [json.loads(l) for l in open(path) if l.strip()]
    except OSError:
        return []
