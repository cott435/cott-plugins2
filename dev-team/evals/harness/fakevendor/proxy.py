"""An HTTPS proxy for fakes whose clients take no base URL (yahooquery calls Yahoo's hosts by name).

`start_proxy(certdir, routes)` serves on 127.0.0.1 in a daemon thread and returns `(url, server, env)`:
- `routes` maps a host suffix (`yahoo.com`) to a fake's request handler class (`fakevendor.handler_class`). A
  CONNECT to a routed host is answered here: TLS is terminated with a certificate for that host, signed by a CA made
  for the run, and the requests inside go to the fake. Plain-HTTP requests to a routed host go to the fake too. No
  routed host is ever reached for real.
- A CONNECT to any other host (the model API, PyPI) is tunnelled untouched; plain HTTP to other hosts gets a 502.
- `env` is what a process needs to use it: HTTPS_PROXY/HTTP_PROXY (both cases), NO_PROXY for localhost (the
  base-URL fakes), a CA bundle (the system roots plus the run's CA) in SSL_CERT_FILE, REQUESTS_CA_BUNDLE and
  CURL_CA_BUNDLE, which curl_cffi, requests, curl and urllib read, and the CA alone in NODE_EXTRA_CA_CERTS.
- `shims(bindir, env)` writes `python3`, `python`, `uv` and `curl` wrappers that put `env` back before running the
  real program, so a command started with `env -i PATH="$PATH"` (how api-probe runs public.py) still goes through
  the proxy as long as PATH leads to them.

The CA and leaf certificates are made with the `openssl` CLI into `certdir` (kept out of the project).
"""
import os, select, socket, ssl, subprocess, threading
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


def _routed(host, routes):
    host = host.lower().rstrip(".")
    return next((cls for suffix, cls in routes.items() if host == suffix or host.endswith("." + suffix)), None)


class _Proxy(BaseHTTPRequestHandler):
    routes, tls, log = {}, None, None

    def log_message(self, *a):  # quiet
        pass

    def _note(self, kind, host):
        if self.log:
            with self.server.lock, open(self.log, "a") as f:
                f.write(f'{{"kind": "{kind}", "host": "{host}"}}\n')

    def do_CONNECT(self):
        host, _, port = self.path.rpartition(":")
        cls = _routed(host, self.routes)
        if cls is not None:
            self._note("served", host)
            self.send_response(200, "Connection Established")
            self.end_headers()
            try:
                conn = self.tls.wrap_socket(self.connection, server_side=True)
            except (ssl.SSLError, OSError):
                self.close_connection = True
                return
            try:
                cls(conn, self.client_address, self.server)
            except OSError:
                pass
            self.close_connection = True
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
        cls = _routed(host, self.routes)
        if cls is None:
            self.send_error(502, "plain HTTP is only proxied to the fakes")
            return
        self._note("served", host)
        handler = cls.__new__(cls)  # reuse this connection's parsed request
        handler.__dict__.update(self.__dict__)
        getattr(handler, f"do_{self.command}")()

    do_GET = do_POST = _plain


def start_proxy(certdir, routes, log=None):
    bundle, cert, key = make_certs(certdir, sorted(routes))
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert, key)
    handler = type("Proxy", (_Proxy,), {"routes": routes, "tls": tls, "log": str(log) if log else None})
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


def shims(bindir, env, names=("python3", "python", "uv", "curl")):
    """Wrappers in `bindir` that set `env` (unless already set) and exec the real program; returns `bindir`."""
    import shutil
    os.makedirs(bindir, exist_ok=True)
    exports = "".join(f'[ -n "${{{k}}}" ] || export {k}="{v}"\n' for k, v in env.items())
    for n in names:
        real = shutil.which(n, path=os.pathsep.join(p for p in os.environ.get("PATH", "").split(os.pathsep)
                                                   if os.path.abspath(p) != os.path.abspath(bindir)))
        if not real:
            continue
        path = os.path.join(bindir, n)
        with open(path, "w") as f:
            f.write(f"#!/bin/sh\n{exports}exec {real} \"$@\"\n")
        os.chmod(path, 0o755)
    return bindir
