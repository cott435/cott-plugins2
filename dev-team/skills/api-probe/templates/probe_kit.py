"""probe_kit: the shared helper for one dev-team probe. Copied into each probes/PB-NN-<slug>/ folder.

Never imported across folders. Stdlib only. Keys come from the environment, else this folder's .env.
Evidence is written only through record(), allow() and shape_sample(), and scan() checks it before
anything reaches evidence/. On a hit, the output goes to out/evidence.rejected.json and the run fails.
probe.py ends in run({"<step>": function, ...}): every run writes evidence, a failed one with its error.

    python3 probe_kit.py --self-test     # no network, no keys: a planted secret must stop the write
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE, OUT = HERE / "evidence", HERE / "out"

_secrets: set[str] = set()
_checks: dict[str, dict] = {}
_samples: dict[str, object] = {}
_schema: dict[str, dict] = {}

PATTERNS = {
    "token": re.compile(r"\b(?:access|public|link|processor)-(?:sandbox|development|production)-[\w-]+"),
    "secret key": re.compile(r"\b(?:sk|pk|rk)[-_][\w-]{8,}"),
    "credential in URL": re.compile(r"://[^/\s:@\"]+:[^/\s@\"]+@|[?&](?:api_key|apikey|token|secret|key)=[^&\s\"]+"),
    "hex run": re.compile(r"\b[0-9a-fA-F]{24,}\b"),
    "base64 run": re.compile(r"(?<![\w+/-])(?=[\w+/=-]*\d)(?=[\w+/=-]*[A-Za-z])[\w+/=-]{32,}"),
    "digit run": re.compile(r"\d{8,}|\b\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{1,7}\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    "phone": re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
}


def load_env(names: list[str]) -> dict[str, str]:
    """The named keys, from the environment else .env. Every value, and every other .env value, is a
    secret to scan() for, as `dt probes --scan` treats it. So .env holds keys only: read settings such
    as PLAID_ENV or a base URL with os.environ.get(name, default), never through load_env or .env."""
    file = {}
    if (HERE / ".env").is_file():
        for line in (HERE / ".env").read_text().splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and not key.startswith("#"):
                file[key.strip()] = value.strip().strip("'\"")
    values = {n: os.environ.get(n) or file.get(n, "") for n in names}
    missing = [n for n, v in values.items() if not v]
    if missing:
        raise Missing(missing)
    os.environ.update(values)
    _secrets.update(v for k, v in {**file, **values}.items() if len(v) >= 4)
    return values


class Missing(SystemExit):
    """Keys absent from the environment and .env. Uncaught, it exits 1 with the message."""

    def __init__(self, names: list[str]):
        super().__init__(f"missing {', '.join(names)}: set them in {HERE.name}/.env (see .env.example)")
        self.names = names


def private(name: str) -> Path:
    """A path in out/ (0700): raw responses, tokens, hashed ids. Never committed, never read by the agent."""
    OUT.mkdir(mode=0o700, exist_ok=True)
    os.chmod(OUT, 0o700)
    return OUT / name


def save_private(name: str, obj: object) -> None:
    path = private(name)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=1, default=str)


def load_private(name: str, default: object = None) -> object:
    path = private(name)
    return json.loads(path.read_text()) if path.is_file() else default


def allow(obj, fields: list[str]):
    """Only the named fields (dotted paths reach into dicts); lists are filtered item by item."""
    if isinstance(obj, list):
        return [allow(o, fields) for o in obj]
    kept: dict = {}
    for path in fields:
        head, _, rest = path.partition(".")
        if not isinstance(obj, dict) or head not in obj:
            continue
        value = obj[head]
        if rest and isinstance(value, (dict, list)):
            value = allow(value, [rest])
            if isinstance(value, dict) and isinstance(kept.get(head), dict):
                value = {**kept[head], **value}
        kept[head] = value
    return kept


def record(check: str, observed: object, passed: bool | None, note: str = "") -> None:
    """One check's result: counts, booleans, months, enum values, field names. Never amounts or ids.
    passed=None: measured, with the verdict left to Record against the entry's Pass cell."""
    _checks[check] = {"pass": None if passed is None else bool(passed), "observed": observed,
                      **({"note": note} if note else {})}


DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
ID_KEY = re.compile(r"(^|_)(id|ids|token|cursor|mask|account_number|routing)$", re.I)


def shape_sample(name: str, rows: list, keep: tuple[str, ...] = ()) -> None:
    """Shape-faithful rows for evidence/samples/<name>.json. Field names, types, nulls and the `keep`
    enum fields stay; numbers become 1.00 with the sign kept, strings "<str:N>", ids "<id>", dates move
    by whole weeks to 2001 (weekday and order kept). The real rows go to out/<name>.raw.json."""
    save_private(f"{name}.raw.json", rows)
    firsts = [m for m in (DATE.match(s) for s in _strings(rows)) if m]
    shift = dt.timedelta(0)
    if firsts:
        first = min(dt.date(*map(int, m.groups())) for m in firsts)
        shift = dt.timedelta(weeks=round((dt.date(2001, 1, 1) - first).days / 7))

    def mask(v, key=""):
        if isinstance(v, dict):
            return {k: mask(x, k) for k, x in v.items()}
        if isinstance(v, list):
            return [mask(x, key) for x in v]
        if v is None or isinstance(v, bool) or key in keep:
            return v
        if ID_KEY.search(key):
            return "<id>"
        if isinstance(v, (int, float)):
            return (-1 if v < 0 else 1) * (1 if isinstance(v, int) else 1.0)
        m = DATE.match(v)
        if m:
            return (dt.date(*map(int, m.groups())) + shift).isoformat() + v[10:]
        return f"<str:{len(v)}>"

    _samples[name] = mask(rows)
    observe_schema(name, rows)


def observe_schema(endpoint: str, rows: list) -> None:
    """Every field path seen in `rows`, its types and null count, for evidence/schema.json."""
    seen = _schema.setdefault(endpoint, {})

    def walk(v, path):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, f"{path}.{k}" if path else k)
            return
        if isinstance(v, list) and v and isinstance(v[0], dict):
            for x in v:
                walk(x, f"{path}[]")
            return
        entry = seen.setdefault(path or "$", {"types": [], "nulls": 0, "seen": 0})
        entry["seen"] += 1
        if v is None:
            entry["nulls"] += 1
        elif type(v).__name__ not in entry["types"]:
            entry["types"].append(type(v).__name__)

    for row in rows:
        walk(row, "")


def scan(text: str) -> list[str]:
    """The patterns `text` hits: token shapes, secret keys, credentials in URLs, long hex or base64
    runs, 8+ digit runs, card numbers, emails, phones, and any .env value. Empty means clean."""
    hits = [name for name, pattern in PATTERNS.items() if pattern.search(text)]
    return hits + (["a .env value"] if any(s in text for s in _secrets) else [])


def script_hash(folder: Path = HERE) -> str:
    """First 8 hex of sha256 over the folder's code files, as `dt probes --stamp` computes it: every
    file except top-level evidence/ and out/, dot-files and dot-folders, __pycache__/, *.pyc and *.md."""
    files = []
    for d, subs, names in os.walk(folder):
        rel_d = os.path.relpath(d, folder).replace(os.sep, "/")
        subs[:] = sorted(x for x in subs if not x.startswith(".") and x != "__pycache__"
                         and not (rel_d == "." and x in ("evidence", "out")))
        files += [os.path.normpath(os.path.join(rel_d, n)).replace(os.sep, "/") for n in names
                  if not n.startswith(".") and not n.endswith((".pyc", ".md"))]
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode() + b"\0" + (Path(folder) / rel).read_bytes() + b"\0")
    return h.hexdigest()[:8]


def run(steps: dict, runner: str = "user", env: str = "", base_url: str = "", keys: list[str] = ()) -> None:
    """`python3 probe.py <step>`: load_env(keys), run that step, then write_evidence() once. A missing or
    unknown step, a missing key or a step that raises still writes evidence, with `error` {kind: usage,
    missing or exception, step}, then exits 1: a failed run is never invisible to Record."""
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    error, message = None, ""
    if step not in steps:  # the given text is never recorded: it could be anything the user typed
        error = {"kind": "usage", "steps": list(steps)}
        message = f"usage: python3 {Path(sys.argv[0]).name} {'|'.join(steps)}"
    else:
        try:
            if keys:
                load_env(list(keys))
            steps[step]()
        except Missing as e:
            error, message = {"kind": "missing", "step": step, "names": e.names}, str(e)
        except Exception as e:  # the class, an HTTP status, a file name: never the message or the request
            error = {"kind": "exception", "step": step, "type": type(e).__name__,
                     **({"status": e.code} if isinstance(getattr(e, "code", None), int) else {}),
                     **({"file": Path(e.filename).name} if getattr(e, "filename", None) else {})}
            message = f"{step} stopped: " + ", ".join(str(v) for k, v in error.items() if k not in ("kind", "step"))
    write_evidence(runner, env, base_url, error)
    if error:
        sys.exit(f"{message}\nevidence written with error {error['kind']}: say \"ran it\" all the same")


def write_evidence(runner: str = "user", env: str = "", base_url: str = "", error: dict | None = None) -> None:
    """Scan, then write evidence/results.json, samples/ and schema.json. A re-run of the
    same code keeps the checks it didn't record again (a day-2 run adds C6, C7); other code replaces them.
    `error` comes from run(); a clean run has none. On a scan hit nothing reaches evidence/: the output
    goes to out/evidence.rejected.json and we exit 1."""
    digest = script_hash()
    old = {}
    if (EVIDENCE / "results.json").is_file():
        prior = json.loads((EVIDENCE / "results.json").read_text())
        old = prior.get("checks", {}) if prior.get("script_hash") == digest else {}
    results = {"probe": "-".join(HERE.name.split("-")[:2]), "script_hash": digest,
               "run_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "runner": runner, "env": env, "base_url": base_url,
               "checks": dict(sorted({**old, **_checks}.items(), key=lambda kv: (len(kv[0]), kv[0]))),
               **({"error": error} if error else {})}
    files = {"results.json": results, **({"schema.json": _schema} if _schema else {}),
             **{f"samples/{n}.json": s for n, s in _samples.items()}}
    text = {rel: json.dumps(obj, indent=1, sort_keys=False) + "\n" for rel, obj in files.items()}
    hits = sorted({h for t in text.values() for h in scan(t.replace(digest, ""))})
    if hits:
        save_private("evidence.rejected.json", files)
        sys.exit(f"evidence NOT written: matched {', '.join(hits)}. "
                 f"Review {HERE.name}/out/evidence.rejected.json yourself, then fix the allow-list.")
    for rel, t in text.items():
        (EVIDENCE / rel).parent.mkdir(parents=True, exist_ok=True)
        (EVIDENCE / rel).write_text(t)
    print(f"evidence written: {', '.join(text)} ({len(results['checks'])} checks)")


def _strings(v):
    if isinstance(v, dict):
        v = list(v.values())
    if isinstance(v, list):
        for x in v:
            yield from _strings(x)
    elif isinstance(v, str):
        yield v


def _self_test() -> None:
    """Run in a scratch copy of this file: no network, no keys. Exits non-zero on any failure."""
    import shutil
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "PB-99-selftest"
        probe.mkdir()
        shutil.copy(__file__, probe / "probe_kit.py")
        (probe / ".env").write_text("FAKE_SECRET=s3cr3t-value-0042\n")
        (probe / "README.md").write_text("not code: no part of the hash\n")
        body = ("from probe_kit import *\n"
                "load_env(['FAKE_SECRET'])\n"
                "record('C1', {'found': 3}, passed=True)\n"
                "shape_sample('rows', [{'amount': -12.5, 'name': 'CANARY-ACCT-7731', 'date': '2026-10-19',"
                " 'account_id': 'abc', 'type': 'depository'}], keep=('type',))\n"
                "LEAK = {'none': None, 'secret': {'note': os.environ['FAKE_SECRET']},"
                " 'card': {'note': 'card 4111 1111 1111 1111'}, 'email': {'note': 'me@example.com'},"
                " 'digits': {'note': 'acct 12345678'}, 'url': {'note': 'https://x.test/v1?api_key=abc123'}}[sys.argv[1]]\n"
                "if LEAK: record('C2', LEAK, passed=True)\n"
                "write_evidence(runner='agent', env=os.environ.get('FAKE_ENV', 'sandbox'))\n")
        (probe / "probe.py").write_text(body)
        run = lambda case: subprocess.run([sys.executable, "probe.py", case], cwd=probe,  # noqa: E731
                                          capture_output=True, text=True,
                                          env={"PATH": os.environ["PATH"], "FAKE_ENV": "sandbox"})
        failures = []
        for case in ("secret", "card", "email", "digits", "url"):
            (probe / "out" / "evidence.rejected.json").unlink(missing_ok=True)
            r = run(case)
            if r.returncode == 0 or (probe / "evidence").exists():
                failures.append(f"planted {case}: evidence was written")
            if not (probe / "out" / "evidence.rejected.json").is_file():
                failures.append(f"planted {case}: no out/evidence.rejected.json")
        r = run("none")
        results = probe / "evidence" / "results.json"
        if r.returncode != 0 or not results.is_file():
            failures.append(f"clean run failed: {r.stderr.strip()[-200:]}")
        else:
            data = json.loads(results.read_text())
            sample = json.loads((probe / "evidence" / "samples" / "rows.json").read_text())[0]
            if set(data) != {"probe", "script_hash", "run_at", "runner", "env", "base_url", "checks"}:
                failures.append(f"results.json keys: {sorted(data)}")
            if data["probe"] != "PB-99" or data["script_hash"] != script_hash(probe):
                failures.append("results.json probe or script_hash wrong")
            if sample != {"amount": -1.0, "name": "<str:16>", "date": "2001-01-01",
                          "account_id": "<id>", "type": "depository"}:
                failures.append(f"sample not shape-faithful: {sample}")
            if oct((probe / "out").stat().st_mode & 0o777) != "0o700":
                failures.append("out/ is not 0700")
        (probe / "steps.py").write_text("from probe_kit import *\n"
                                        "def ok(): record('C1', {'found': 1}, passed=True)\n"
                                        "def boom(): load_private('x') or open(private('members.json'))\n"
                                        "run({'ok': ok, 'boom': boom})\n")
        for args, want in (([], {"kind": "usage", "steps": ["ok", "boom"]}),
                           (["s3cr3t-typed"], {"kind": "usage", "steps": ["ok", "boom"]}),
                           (["boom"], {"kind": "exception", "step": "boom", "type": "FileNotFoundError",
                                       "file": "members.json"}),
                           (["ok"], None)):
            r = subprocess.run([sys.executable, "steps.py", *args], cwd=probe, capture_output=True, text=True,
                               env={"PATH": os.environ["PATH"]})
            text = results.read_text() if results.is_file() else ""
            got = json.loads(text).get("error") if text else "no results.json"
            if got != want or (r.returncode == 0) != (want is None) or "s3cr3t" in text:
                failures.append(f"run {args}: rc {r.returncode}, error {got}")
    if failures:
        sys.exit("self-test FAILED:\n  " + "\n  ".join(failures))
    print("self-test passed: a planted .env secret, card, email, digit run and URL key each stopped the write; "
          "a clean run wrote results.json and a shape-faithful sample; a missing, unknown or failing step "
          "wrote its error")


if __name__ == "__main__" and sys.argv[1:] == ["--self-test"]:
    _self_test()
