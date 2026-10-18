"""An HTTPS proxy for fakes on a vendor's real hosts: clients that take no base URL (yahooquery calls Yahoo's hosts by
name), and code that hard-codes a vendor's API host (`https://api.sharadar.com/v1.0` in a probe's public.py).

`start_proxy(certdir, routes, log=None, closed=False)` serves on 127.0.0.1 in a daemon thread and returns
`(url, server, env)`:
- `routes` maps a host suffix (`yahoo.com`), or a host and path prefix (`data.nasdaq.com/api/`), to a fake's request
  handler class (`fakevendor.handler_class`). A CONNECT to a routed host is answered here: TLS is terminated with a
  certificate for that host, signed by a CA made for the run, and each request inside goes to the fake when its path
  is routed. Plain-HTTP requests to a routed host and path go to the fake too. No routed path is ever reached for real.
- A request to a routed host outside its routed paths (the vendor's docs pages) is relayed to the real host, and a
  CONNECT to any other host (the model API, PyPI) is tunnelled untouched; plain HTTP to other hosts gets a 502.
- `closed=True` is the proxy for user and public runs: no live vendor is reached. A request outside the routes is
  refused with a 403, except CONNECTs to the package indexes (`ALLOW`), which `uv run` needs.
- Every CONNECT and refused or relayed request is logged to `log` as one JSON line: {kind, host, proxy}.
- `env` is what a process needs to use it: HTTPS_PROXY/HTTP_PROXY (both cases), NO_PROXY for localhost (the
  base-URL fakes), a CA bundle (the system roots plus the run's CA) in SSL_CERT_FILE, REQUESTS_CA_BUNDLE and
  CURL_CA_BUNDLE, which curl_cffi, requests, curl and urllib read, and the CA alone in NODE_EXTRA_CA_CERTS.
- `shims(bindir, env, public_env=None)` writes `python3`, `python`, `uv` and `curl` wrappers that put `env` back
  before running the real program, so a command started with `env -i PATH="$PATH"` (how api-probe runs public.py)
  still goes through the proxy as long as PATH leads to them. With `public_env`, a command that runs a `public.py`
  gets that environment instead, whatever it was given: the agent's public runs go through the closed proxy.

The CA and leaf certificates are made with the `openssl` CLI into `certdir` (kept out of the project).
"""
import http.client, json, os, select, socket, ssl, subprocess, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SYSTEM_ROOTS = [p for p in ("/etc/ssl/cert.pem", ssl.get_default_verify_paths().cafile or "") if p and os.path.exists(p)]


def make_certs(certdir, hosts):
    """A CA and one leaf certificate covering `hosts` (with `*.` and `*.finance.` forms), plus a bundle of the system
    roots and the CA. Returns (bundle, leaf cert, leaf key)."""
    os.makedirs(certdir, exist_ok=True)
    p = lambda n: os.path.join(certdir, n)
    run = lambda *a: subprocess.run(["openssl", *a], check=True, capture_output=True)
    if not os.path.exists(p("leaf.pem")):
        run("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "30", "-subj", "/CN=dev-team eval fake CA",
            "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign",
            "-keyout", p("ca.key"), "-out", p("ca.pem"))
        sans = sorted({n for h in hosts for n in (h, f"*.{h}", f"*.finance.{h}")})
        with open(p("leaf.ext"), "w") as f:
            f.write("basicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n"
                    "subjectAltName=" + ",".join(f"DNS:{n}" for n in sans) + "\n")
        run("req", "-newkey", "rsa:2048", "-nodes", "-subj", f"/CN={hosts[0]}", "-keyout", p("leaf.key"), "-out", p("leaf.csr"))
        run("x509", "-req", "-in", p("leaf.csr"), "-CA", p("ca.pem"), "-CAkey", p("ca.key"), "-CAcreateserial",
            "-days", "30", "-extfile", p("leaf.ext"), "-out", p("leaf.pem"))
        with open(p("bundle.pem"), "w") as out:
            for root in SYSTEM_ROOTS[:1]:
                out.write(open(root).read().rstrip("\n") + "\n")
            out.write(open(p("ca.pem")).read())
    return p("bundle.pem"), p("leaf.pem"), p("leaf.key")


ALLOW = ("pypi.org", "pythonhosted.org", "github.com", "githubusercontent.com")  # what `uv run` fetches
HOP = {"connection", "keep-alive", "proxy-connection", "transfer-encoding", "te", "trailer", "upgrade",
       "proxy-authorization", "proxy-authenticate"}


def _split(route):
    """A route key as (host suffix, path prefix): `data.nasdaq.com/api/` → ("data.nasdaq.com", "/api/")."""
    host, _, prefix = route.partition("/")
    return host.lower(), "/" + prefix if prefix else ""


def _on(host, suffix):
    host = host.lower().rstrip(".")
    return host == suffix or host.endswith("." + suffix)


def _routed_host(host, routes):
    return any(_on(host, _split(r)[0]) for r in routes)


def _route(host, path, routes):
    """The fake for this host and request path (longest prefix first), or None."""
    path = urllib.parse.urlsplit(path).path or "/"
    hits = [(prefix, cls) for r, cls in routes.items() for h, prefix in [_split(r)] if _on(host, h) and path.startswith(prefix)]
    return max(hits, key=lambda x: len(x[0]))[1] if hits else None


class _Base(BaseHTTPRequestHandler):
    routes, tls, log, closed = {}, None, None, False

    def log_message(self, *a):  # quiet
        pass

    def _note(self, kind, host):
        if self.log:
            with self.server.lock, open(self.log, "a") as f:
                f.write(json.dumps({"kind": kind, "host": host, "proxy": "closed" if self.closed else "open"}) + "\n")

    def _dispatch(self, host):
        """Serve one request for `host`: the fake when its path is routed, else refused (closed) or relayed."""
        cls = _route(host, self.path, self.routes)
        if cls is not None:
            handler = cls.__new__(cls)  # reuse this connection's parsed request
            handler.__dict__.update(self.__dict__)
            getattr(handler, f"do_{self.command}")()
            return
        if self.closed:
            self._note("blocked", host)
            self.send_error(403, "a live vendor host is blocked in a user or public run")
            return
        self._note("relayed", host)
        self._relay(host)

    def _relay(self, host):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        path = urllib.parse.urlsplit(self.path)
        target = (path.path or "/") + (f"?{path.query}" if path.query else "")
        try:
            up = http.client.HTTPSConnection(host, timeout=30, context=ssl.create_default_context())
            up.request(self.command, target, body=body, headers=headers)
            r = up.getresponse()
            data = r.read()
        except (OSError, http.client.HTTPException):
            self.send_error(502, "upstream unreachable")
            return
        self.send_response(r.status, r.reason)
        for k, v in r.getheaders():
            if k.lower() not in HOP and k.lower() != "content-length":
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class _Inner(_Base):
    """The requests inside a terminated TLS connection to a routed host (`host`, from the CONNECT)."""
    protocol_version = "HTTP/1.1"
    host = ""

    def _one(self):
        self._dispatch(self.host or (self.headers.get("Host") or "").split(":")[0])

    do_GET = do_POST = do_HEAD = do_PUT = do_DELETE = do_OPTIONS = _one


class _Proxy(_Base):
    def do_CONNECT(self):
        host, _, port = self.path.rpartition(":")
        if _routed_host(host, self.routes):
            self._note("served", host)
            self.send_response(200, "Connection Established")
            self.end_headers()
            try:
                conn = self.tls.wrap_socket(self.connection, server_side=True)
            except (ssl.SSLError, OSError):
                self.close_connection = True
                return
            inner = type("Inner", (_Inner,), {"routes": self.routes, "log": self.log, "closed": self.closed, "host": host})
            try:
                inner(conn, self.client_address, self.server)
            except OSError:
                pass
            self.close_connection = True
            return
        if self.closed and not any(_on(host, a) for a in ALLOW):
            self._note("blocked", host)
            self.send_error(403, "a live vendor host is blocked in a user or public run")
            return
        self._note("tunnel", host)
        try:
            up = socket.create_connection((host, int(port or 443)), timeout=30)
        except OSError:
            self.send_error(502, "upstream unreachable")
            return
        self.send_response(200, "Connection Established")
        self.end_headers()
        socks = [self.connection, up]
        try:
            while True:
                ready, _, broken = select.select(socks, [], socks, 600)
                if broken or not ready:
                    break
                for s in ready:
                    data = s.recv(65536)
                    if not data:
                        return
                    (up if s is self.connection else self.connection).sendall(data)
        except OSError:
            pass
        finally:
            up.close()
            self.close_connection = True

    def _plain(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        if not _routed_host(host, self.routes):
            if self.closed:
                self._note("blocked", host)
                self.send_error(403, "a live vendor host is blocked in a user or public run")
            else:
                self.send_error(502, "plain HTTP is only proxied to the fakes")
            return
        self._note("served", host)
        if _route(host, self.path, self.routes) is None:
            if self.closed:
                self._note("blocked", host)
                self.send_error(403, "a live vendor host is blocked in a user or public run")
            else:
                self.send_error(502, "plain HTTP is only proxied to the fakes")
            return
        self._dispatch(host)

    do_GET = do_POST = _plain


def start_proxy(certdir, routes, log=None, closed=False):
    bundle, cert, key = make_certs(certdir, sorted({_split(r)[0] for r in routes}))
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert, key)
    handler = type("Proxy", (_Proxy,), {"routes": routes, "tls": tls, "log": str(log) if log else None, "closed": closed})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    server.handle_error = lambda request, address: None  # a client dropping mid-handshake is not news
    server.lock = threading.Lock()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    env = {k: url for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")}
    env.update({k: "localhost,127.0.0.1,::1" for k in ("NO_PROXY", "no_proxy")})
    env.update({k: bundle for k in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")})
    env["NODE_EXTRA_CA_CERTS"] = os.path.join(certdir, "ca.pem")
    return url, server, env


def shims(bindir, env, names=("python3", "python", "uv", "curl"), public_env=None):
    """Wrappers in `bindir` that set `env` (unless already set) and exec the real program; returns `bindir`. With
    `public_env`, a command with a `public.py` argument gets `public_env` instead, set over whatever it was given."""
    import shutil
    os.makedirs(bindir, exist_ok=True)
    exports = "".join(f'[ -n "${{{k}}}" ] || export {k}="{v}"\n' for k, v in env.items())
    forced = "".join(f'export {k}="{v}"; ' for k, v in (public_env or {}).items())
    for n in names:
        real = shutil.which(n, path=os.pathsep.join(p for p in os.environ.get("PATH", "").split(os.pathsep)
                                                   if os.path.abspath(p) != os.path.abspath(bindir)))
        if not real:
            continue
        path = os.path.join(bindir, n)
        public = (f'for a in "$@"; do case "$a" in public.py|*/public.py) {forced}exec {real} "$@";; esac; done\n'
                  if public_env else "")
        with open(path, "w") as f:
            f.write(f"#!/bin/sh\n{public}{exports}exec {real} \"$@\"\n")
        os.chmod(path, 0o755)
    return bindir
