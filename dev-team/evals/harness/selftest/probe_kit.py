"""Probe kit (design/probes.md §4.1), the eval fixtures' copy: copied into each probe folder, never imported
across folders. Keys come from the environment, else this folder's .env; evidence is written only after scan().
"""
import datetime as dt, hashlib, json, os, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
PATTERNS = {
    "token": re.compile(r"\b(?:access|public|link)-(?:production|sandbox|development)-[\w-]{6,}|\bsk-[A-Za-z0-9_-]{8,}"),
    "long hex": re.compile(r"\b[0-9a-f]{32,}\b", re.I),
    "base64": re.compile(r"[A-Za-z0-9+/]{40,}={0,2}"),
    "digit run": re.compile(r"(?<![\d.])\d{8,}(?!\d)|\b\d{4}([ -])\d{4}\1\d{4}\1\d{4}\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z][\w.]*"),
    "phone": re.compile(r"(?<!\d)\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
}
_results, _samples, _secrets = {}, {}, []


def load_env(names):
    """Each name from the environment, else this folder's .env; never printed."""
    file = {}
    if (HERE / ".env").exists():
        for line in (HERE / ".env").read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                file[k.strip()] = v.strip().strip("'\"")
    for n in names:
        v = os.environ.get(n) or file.get(n)
        if not v:
            raise SystemExit(f"{n} is not set: copy .env.example to .env and fill it in")
        os.environ[n] = v
        _secrets.append(v)
    _secrets.extend(v for v in file.values() if len(v) >= 6 and not v.startswith("http"))


def private(name):
    """A path in out/ (gitignored, owner-only)."""
    out = HERE / "out"
    out.mkdir(mode=0o700, exist_ok=True)
    return out / name


def write_private(name, obj):
    p = private(name)
    p.write_text(json.dumps(obj, indent=1, default=str))
    p.chmod(0o600)


def allow(obj, fields):
    return {k: obj[k] for k in fields if k in obj}


def record(check, observed, passed, note=""):
    _results[check] = {"pass": bool(passed), "observed": observed, **({"note": note} if note else {})}


def _shape(v):
    if isinstance(v, dict):
        return {k: _shape(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_shape(x) for x in v[:3]]
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return -1.0 if v < 0 else 1.0
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
        d = dt.date.fromisoformat(v)
        return dt.date(2000, d.month, min(d.day, 28)).isoformat()
    return f"<str:{len(str(v))}>"


def shape_sample(name, rows):
    """A shape-faithful sample: field names, types and nulls kept, every value replaced."""
    _samples[name] = [_shape(r) for r in rows]


def scan(text):
    hits = [name for name, rx in PATTERNS.items() if rx.search(text)]
    return hits + ["a .env value"] * any(s in text for s in _secrets)


def script_hash():
    h = hashlib.sha256()
    for p in sorted(HERE.rglob("*")):
        rel = p.relative_to(HERE)
        if p.is_file() and rel.parts[0] not in ("evidence", "out", "__pycache__") and not p.name.startswith(".env") \
                and p.suffix in (".py", ".md", ".sh"):
            h.update(str(rel).encode() + b"\0" + p.read_bytes())
    return h.hexdigest()[:8]


def write_evidence(probe, runner, base_url=""):
    """results.json and samples/, after the scan; a hit writes out/evidence.rejected.json instead and stops."""
    doc = {"probe": probe, "script_hash": script_hash(), "run_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "runner": runner, "base_url": re.sub(r"\?.*", "", base_url), "checks": _results}
    text = json.dumps(doc, indent=1, sort_keys=True)
    samples = {n: json.dumps(r, indent=1, sort_keys=True) for n, r in _samples.items()}
    hits = scan(text + "\n".join(samples.values()))
    if hits:
        write_private("evidence.rejected.json", {"results": doc, "samples": _samples})
        raise SystemExit(f"evidence rejected ({', '.join(sorted(set(hits)))}); kept in out/evidence.rejected.json")
    ev = HERE / "evidence"
    (ev / "samples").mkdir(parents=True, exist_ok=True)
    (ev / "results.json").write_text(text + "\n")
    for n, s in samples.items():
        (ev / "samples" / f"{n}.json").write_text(s + "\n")
