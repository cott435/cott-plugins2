"""python3 -m fakevendor <sharadar|plaid> [--port N] [--log FILE] [--key EXPECTED]: serve one fake in the foreground."""
import argparse, time

from . import VENDORS, start

ap = argparse.ArgumentParser(prog="fakevendor")
ap.add_argument("name", choices=sorted(VENDORS))
ap.add_argument("--port", type=int, default=0)
ap.add_argument("--log")
ap.add_argument("--key")
a = ap.parse_args()
url, server = start(a.name, a.log, a.key, a.port)
print(url, flush=True)
try:
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    server.shutdown()
