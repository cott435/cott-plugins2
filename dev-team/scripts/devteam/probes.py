"""Probe folders (`probes/PB-NN-*/`) against their entries in docs/probes.md (design/probes.md §3.4, §4, §5):
the code hash, `evidence/results.json` and its shape, the redaction scan, and what `dt status` reports. Used by
`dt status`, `dt probes`, `dt context` and lint. Never prints a secret: a scan hit names the file, the line and the
pattern, never the text."""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import md, model
from .repo import IGNORE_DIRS, Repo

FOLDER = "probes"
LARGE_LINES = 400            # `probe-large`: code lines in one probe, the copied probe_kit.py aside
KIT = "probe_kit.py"
SOURCE_SUFFIXES = (".py", ".sh", ".js", ".ts", ".html")
RESULTS = "evidence/results.json"
RUNNERS = ("agent", "user")


# ---- files and the code hash ------------------------------------------------------------------

def code_files(folder: Path) -> list[str]:
    """The probe's code files, relative to its folder (POSIX, sorted): every file except `evidence/` and `out/`,
    dot-files and dot-folders (`.env`, `.env.example`), caches and Markdown (a README edit doesn't change
    results). probe_kit computes `script_hash` over the same files."""
    out = []
    for d, subdirs, names in os.walk(folder):
        rel_d = os.path.relpath(d, folder).replace(os.sep, "/")
        subdirs[:] = sorted(s for s in subdirs if not s.startswith(".") and s not in IGNORE_DIRS
                            and not (rel_d == "." and s in ("evidence", "out")))
        for n in names:
            if n.startswith(".") or n.endswith((".pyc", ".md")):
                continue
            out.append(os.path.normpath(os.path.join(rel_d, n)).replace(os.sep, "/"))
    return sorted(out)


def code_hash(folder: Path) -> str | None:
    """First 8 hex of sha256 over each code file's relative path and bytes, in path order; None when the
    folder doesn't exist."""
    if not folder.is_dir():
        return None
    h = hashlib.sha256()
    for rel in code_files(folder):
        try:
            data = (folder / rel).read_bytes()
        except OSError:
            continue
        h.update(rel.encode() + b"\0" + data + b"\0")
    return h.hexdigest()[:8]


def code_lines(folder: Path) -> int:
    """Lines of source (`.py`, `.sh`, `.js`, `.ts`, `.html`) in the probe, the copied probe_kit.py aside."""
    return sum(line_count(folder / rel) for rel in code_files(folder)
               if rel.endswith(SOURCE_SUFFIXES) and rel.rsplit("/", 1)[-1] != KIT)


def line_count(path: Path) -> int:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def folders(repo: Repo) -> list[Path]:
    base = repo.root / FOLDER
    return sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")) if base.is_dir() else []


def folder_of(repo: Repo, probe: model.Probe) -> Path | None:
    return repo.root / probe.folder if probe.folder else None


def samples(folder: Path) -> list[str]:
    """`evidence/samples/*` files, relative to the probe folder."""
    base = folder / "evidence" / "samples"
    return sorted(f"evidence/samples/{p.name}" for p in base.iterdir() if p.is_file()) if base.is_dir() else []


# ---- results.json (§4.3) ------------------------------------------------------------------------

ISO_TIME = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?")


@dataclass
class Results:
    path: str                                  # repo-relative
    data: dict | None = None
    problems: list[tuple[int, str]] = field(default_factory=list)   # (1-based line, message)

    @property
    def ok(self) -> bool:
        return self.data is not None and not self.problems

    @property
    def run_at(self) -> str:
        v = (self.data or {}).get("run_at")
        return v if isinstance(v, str) else ""

    @property
    def script_hash(self) -> str:
        v = (self.data or {}).get("script_hash")
        return v.lower() if isinstance(v, str) else ""

    @property
    def checks(self) -> dict:
        v = (self.data or {}).get("checks")
        return v if isinstance(v, dict) else {}


def _line_of(text: str, needle: str) -> int:
    i = text.find(needle)
    return text.count("\n", 0, i) + 1 if i >= 0 else 1


def validate(text: str, probe_id: str, check_ids: list[str]) -> tuple[dict | None, list[tuple[int, str]]]:
    """(the parsed object, problems) for results.json text against its entry: `probe`, `script_hash` (8 hex),
    `run_at` (ISO 8601), `runner` (agent|user) and `checks` are required; each check key is a `C<n>` in the
    entry's table, holding an object with `pass` (true, false or null) and `observed`, and an optional string
    `note`. Other keys are kept and not checked."""
    try:
        data = json.loads(text)
    except ValueError as e:
        return None, [(getattr(e, "lineno", 1), f"not valid JSON: {getattr(e, 'msg', e)}")]
    if not isinstance(data, dict):
        return None, [(1, "not a JSON object")]
    out: list[tuple[int, str]] = []
    for key in ("probe", "script_hash", "run_at", "runner", "checks"):
        if key not in data:
            out.append((1, f"no `{key}`"))
    if "probe" in data and data["probe"] != probe_id:
        out.append((_line_of(text, '"probe"'), f"`probe` is {data['probe']!r}, not {probe_id}"))
    if "script_hash" in data and not (isinstance(data["script_hash"], str)
                                      and re.fullmatch(r"[0-9a-fA-F]{8}", data["script_hash"])):
        out.append((_line_of(text, '"script_hash"'), "`script_hash` is not 8 hex digits"))
    if "run_at" in data and not (isinstance(data["run_at"], str) and ISO_TIME.fullmatch(data["run_at"])):
        out.append((_line_of(text, '"run_at"'), "`run_at` is not an ISO 8601 date or time"))
    if "runner" in data and data["runner"] not in RUNNERS:
        out.append((_line_of(text, '"runner"'), f"`runner` is {data['runner']!r}, not agent or user"))
    checks = data.get("checks")
    if "checks" in data and not isinstance(checks, dict):
        out.append((_line_of(text, '"checks"'), "`checks` is not an object"))
    elif isinstance(checks, dict):
        for cid, rec in checks.items():
            line = _line_of(text, f'"{cid}"')
            if cid not in check_ids:
                out.append((line, f"check {cid} is not in {probe_id}'s checks table"))
            if not isinstance(rec, dict):
                out.append((line, f"{cid} is not an object"))
                continue
            if "pass" not in rec or rec["pass"] not in (True, False, None):
                out.append((line, f"{cid} `pass` must be true, false or null"))
            if "observed" not in rec:
                out.append((line, f"{cid} has no `observed`"))
            if "note" in rec and not isinstance(rec["note"], str):
                out.append((line, f"{cid} `note` is not a string"))
    return data, out


def read_results(repo: Repo, probe: model.Probe) -> Results | None:
    """The probe's evidence/results.json, validated against its entry; None when there is none."""
    folder = folder_of(repo, probe)
    if folder is None or not (folder / RESULTS).is_file():
        return None
    rel = f"{probe.folder}/{RESULTS}"
    try:
        text = (folder / RESULTS).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return Results(rel, None, [(1, "unreadable")])
    data, problems = validate(text, probe.id, [c.id for c in probe.checks])
    return Results(rel, data, problems)


def newer(run_at: str, last_run: str) -> bool:
    """Whether results from `run_at` are newer than the entry's Last run (none, a date, or a time; Record copies
    run_at into Last run, so equal is not newer)."""
    if not last_run:
        return True
    if not run_at:
        return False
    if len(last_run) <= 10:
        return run_at[:10] > last_run
    return run_at.replace(" ", "T") > last_run.replace(" ", "T")


# ---- redaction scan (§5.3) --------------------------------------------------------------------------

def _mixed(s: str) -> bool:
    return bool(re.search(r"[A-Z]", s) and re.search(r"[a-z]", s) and re.search(r"\d", s))


# (name, pattern, extra test on the match). Fail closed: a false hit costs a look, a miss leaks.
PATTERNS = [
    ("token", re.compile(r"\b(?:access|public|link|processor)-(?:sandbox|development|production)-[\w-]+"), None),
    ("secret key", re.compile(r"\bsk[-_][A-Za-z0-9_-]{8,}"), None),
    ("credential in URL", re.compile(r"(?i)[?&](?:api[_-]?key|access[_-]?token|token|secret|password|"
                                     r"client[_-]?secret)=[^&\s\"']+"), None),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"), None),
    ("card number", re.compile(r"(?<![\d.])(?:\d[ -]?){12,18}\d(?![\d.])"), None),
    ("long digit run", re.compile(r"\d{8,}"), None),
    ("phone number", re.compile(r"(?<![\w-])(?:\+?\d{1,2}[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?![\w-])"), None),
    ("hex run", re.compile(r"\b[0-9a-fA-F]{24,}\b"), None),
    ("base64 run", re.compile(r"[A-Za-z0-9+/_-]{32,}={0,2}"), _mixed),
]


def env_values(repo: Repo, folder: Path | None) -> list[str]:
    """Values from the probe's `.env` and `.env.*` (not `.env.example`) and the project's `.env` that look like
    secrets (8+ characters, not a URL, with a digit or 16+ long): what evidence must never contain. Read by dt,
    never shown."""
    paths = [repo.root / ".env"]
    if folder is not None and folder.is_dir():
        paths += [p for p in sorted(folder.iterdir())
                  if p.is_file() and (p.name == ".env" or p.name.startswith(".env.")) and p.name != ".env.example"]
    out = []
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            m = re.match(r"^\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*\s*=\s*(.*?)\s*$", line)
            if not m:
                continue
            v = m.group(1).strip().strip("'\"")
            if len(v) >= 8 and not re.match(r"https?://", v) and (re.search(r"\d", v) or len(v) >= 16):
                out.append(v)
    return out


def scan_text(text: str, secrets: list[str] = ()) -> list[tuple[int, str]]:
    """(1-based line, pattern name) for each line that holds a secret or personal-data pattern; one hit per
    line (the first pattern that matches)."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if any(s in line for s in secrets):
            out.append((n, ".env value"))
            continue
        for name, pat, test in PATTERNS:
            if any(test is None or test(m.group(0)) for m in pat.finditer(line)):
                out.append((n, name))
                break
    return out


@dataclass
class Hit:
    path: str            # repo-relative
    line: int
    pattern: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line} ({self.pattern})"


def scan_folder(repo: Repo, folder: Path) -> list[Hit]:
    """Every scan hit in the probe's `evidence/` (text files only)."""
    base = folder / "evidence"
    if not base.is_dir():
        return []
    secrets = env_values(repo, folder)
    out = []
    for d, subdirs, names in os.walk(base):
        subdirs[:] = sorted(s for s in subdirs if s not in IGNORE_DIRS)
        for n in sorted(names):
            p = Path(d) / n
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            rel = os.path.relpath(p, repo.root).replace(os.sep, "/")
            out += [Hit(rel, line, name) for line, name in scan_text(text, secrets)]
    return out


def scan(repo: Repo, only: list[model.Probe] | None = None) -> list[Hit]:
    """Scan hits in the evidence of the given probes' folders, or of every folder under probes/."""
    if only is None:
        targets = folders(repo)
    else:
        targets = [f for p in only if (f := folder_of(repo, p)) is not None]
    return [h for f in targets for h in scan_folder(repo, f)]


# ---- what `dt status` reports (§3.4) ----------------------------------------------------------------

def _ranges(nums: list[int]) -> str:
    """[1, 3, 4, 5, 9] → `C1, C3–C5, C9`."""
    out, nums = [], sorted(set(nums))
    i = 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f"C{nums[i]}" if i == j else f"C{nums[i]}–C{nums[j]}")
        i = j + 1
    return ", ".join(out)


def proposed(repo: Repo, ad: str) -> bool:
    fields = model.decision_fields(repo, ad)
    return bool(fields) and md.strip_md(fields.get("Status", "")).lower().startswith("proposed")


def decisions_of(repo: Repo, probe: model.Probe, citations: list[model.Citation] | None = None) -> list[str]:
    """The decisions a probe informs: its Informs' AD IDs and every decision whose `**Probe:**` line names it."""
    citations = model.probe_citations(repo) if citations is None else citations
    out = list(probe.decisions)
    out += [c.decision for c in citations if c.probe == probe.id and c.decision and c.decision not in out]
    return out


def unrun(probe: model.Probe, results: Results | None) -> list[model.Check]:
    """Checks with no Result recorded and no record in results.json."""
    done = set(results.checks) if results is not None and results.data is not None else set()
    return [c for c in probe.checks if not c.result and c.id not in done]


@dataclass
class State:
    unwritten: list[str] = field(default_factory=list)   # `PB-01 (AD-04)`: cited, no entry
    open: list[str] = field(default_factory=list)        # `PB-01 (user: C1, C3–C9)`: Ready, checks not yet run
    results: list[str] = field(default_factory=list)     # `PB-01 (2026-10-20T18:02:11Z)`: newer than Last run
    stale: list[str] = field(default_factory=list)       # `PB-01 (results 5c1e09ab, code 77aa0b12)`
    leaks: list[str] = field(default_factory=list)       # `path:line (pattern)`
    answered: list[str] = field(default_factory=list)    # `PB-01 pass (AD-04)`: decisions still Proposed
    failed: list[str] = field(default_factory=list)      # `PB-01 (AD-04)`: Answered fail, decisions still Proposed

    @property
    def waiting(self) -> int:
        """For the summary line: results not yet recorded, plus cited probes with no entry."""
        return len(self.unwritten) + len(self.results)


def state(repo: Repo) -> State:
    s = State()
    entries = model.all_probes(repo)
    citations = model.probe_citations(repo)
    for c in citations:
        if c.probe and repo.lookup(c.probe) is None:
            item = f"{c.probe} ({c.decision or c.doc.rel})"
            if item not in s.unwritten:
                s.unwritten.append(item)
    for p in entries:
        res = read_results(repo, p)
        folder = folder_of(repo, p)
        if p.state == "Ready":
            groups: dict[str, list[int]] = {}
            for c in unrun(p, res):
                groups.setdefault(c.runner or "unassigned", []).append(c.number)
            if groups:
                order = sorted(groups, key=lambda r: (r != "user", r != "agent", r))
                s.open.append(f"{p.id} ({'; '.join(f'{r}: {_ranges(groups[r])}' for r in order)})")
        if res is not None and p.state != "Draft":
            if res.data is None or res.problems:
                s.results.append(f"{p.id} (results.json invalid: {res.problems[0][1]})")
            elif newer(res.run_at, p.last_run):
                s.results.append(f"{p.id} ({res.run_at})")
        if res is not None and res.script_hash and folder is not None:
            current = code_hash(folder)
            if current is not None and current != res.script_hash:
                s.stale.append(f"{p.id} (results {res.script_hash}, code {current})")
        if not p.is_open:
            pending = [ad for ad in decisions_of(repo, p, citations) if proposed(repo, ad)]
            if pending:
                label = "waived" if p.state == "Waived" else p.verdict or "answered"
                s.answered.append(f"{p.id} {label} ({', '.join(pending)})")
                if p.state == "Answered" and p.verdict == "fail":
                    s.failed.append(f"{p.id} ({', '.join(pending)})")
    s.leaks = [str(h) for h in scan(repo)]
    return s


def blocking(repo: Repo, unit: str, names: set[str], types: set[str]) -> list[str]:
    """Probes that keep a milestone from being planned (§3.3): open (Draft, Ready), Answered fail with a decision
    still Proposed, or cited by a decision with no entry yet, whose decisions' Scope names one of the
    milestone's packages or components (`names`; `system` meets every milestone), or whose Informs names a type
    of one of them or one its steps pass (`types`). Items read `PB-01 → service, ledger.BankTxn (M1)`."""
    citations = model.probe_citations(repo)
    out = []

    def meets(decisions: list[str], informs_types: list[str]) -> list[str]:
        hit = []
        for ad in decisions:
            fields = model.decision_fields(repo, ad) or {}
            for scope in (md.strip_md(x) for x in md.split_list(fields.get("Scope", ""))):
                if (scope.lower() == "system" or scope in names) and scope not in hit:
                    hit.append(scope)
        hit += [t for t in informs_types if (t.split(".")[0] in names or t in types) and t not in hit]
        return hit

    for p in model.all_probes(repo):
        failed = p.state == "Answered" and p.verdict == "fail"
        decisions = decisions_of(repo, p, citations)
        if not (p.is_open or (failed and any(proposed(repo, ad) for ad in decisions))):
            continue
        hit = meets(decisions, p.types)
        if hit:
            out.append(f"{p.id} → {', '.join(hit)} ({unit})")
    seen = {p.id for p in model.all_probes(repo)}
    for c in citations:
        if c.probe and c.probe not in seen and repo.lookup(c.probe) is None and c.decision:
            hit = meets([c.decision], [])
            if hit:
                out.append(f"{c.probe} → {', '.join(hit)} ({unit})")
                seen.add(c.probe)
    return out
