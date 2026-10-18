"""Shared helpers for calling the plugin's `dt` CLI from the harness (driver, grade, simulate).

`dt` is resolved per run: the plugin snapshot the trajectory ran with (<run>/plugin/dev-team/scripts/dt.py, or plugin/dev-team2/ for runs staged under the old name),
else $DT, else this repo's scripts/dt.py. Grading with the run's own snapshot keeps the parser identical.

Also here: the task-graph arithmetic and the logic of the structural checks, as pure functions over dtprobe facts,
so grade.py and its selftest (selftest/checks.py) run the same code.
"""
import fnmatch, json, os, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_DT = HERE.parents[1] / "scripts" / "dt.py"


def dt_path(run_dir=None):
    if run_dir is not None:
        for name in ("dev-team", "dev-team2"):
            snap = pathlib.Path(run_dir) / "plugin" / name / "scripts" / "dt.py"
            if snap.exists():
                return snap
    return pathlib.Path(os.environ.get("DT", REPO_DT))


def run(proj, *args, dt=None, stdin=None):
    """(returncode, stdout, stderr) of `dt --root <proj> <args>`."""
    r = subprocess.run([sys.executable, str(dt or REPO_DT), "--root", str(proj), *args],
                       capture_output=True, text=True, input=stdin, timeout=300)
    return r.returncode, r.stdout, r.stderr


def run_json(proj, *args, dt=None):
    """Parsed `--json` output, or {"_error": …} when dt crashed or printed no JSON."""
    rc, out, err = run(proj, *args, "--json", dt=dt)
    try:
        d = json.loads(out)
        d["_rc"] = rc
        return d
    except Exception:
        return {"_error": f"rc={rc} {err.strip()[-400:]}", "_rc": rc}


def probe(proj, dt=None, requests_history=False):
    """dtprobe.py facts (live spec IDs, pipelines, plans and tasks, derived roadmap rows, doc statuses);
    `requests_history` adds docs/requests.md as dt parses it at every commit that touched it."""
    scripts = pathlib.Path(dt or REPO_DT).parent
    r = subprocess.run([sys.executable, str(HERE / "dtprobe.py"), str(scripts), str(proj),
                        *(["--requests-history"] if requests_history else [])],
                       capture_output=True, text=True, timeout=300)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"_error": r.stderr.strip()[-600:], "live_spec": [], "removed_spec": [], "pipelines": [],
                "plans": [], "roadmap": [], "stages": [], "references": [], "symbols": [], "tests": [], "docs": {},
                "packages": [], "probes": [], "probes_retired": [], "decisions": [], "dt_probes": None,
                "requests": None, "requests_history": []}


def turn_costs(turns):
    """Each turn's own cost from turns.json: total_cost_usd is cumulative within one agent session, so a turn's cost
    is the difference from the previous turn of the same session (`session.id`; a run from before sessions is one)."""
    last, out = {}, []
    for t in turns:
        sid = (t.get("session") or {}).get("id", "")
        cum = (t.get("usage") or {}).get("cost_usd")
        out.append(None if cum is None else round(cum - last.get(sid, 0.0), 4))
        if cum is not None:
            last[sid] = cum
    return out


def run_cost(turns):
    """The run's agent cost: each session's last cumulative total, summed."""
    return sum(c for c in turn_costs(turns) if c is not None)


def skill_name(s):
    """Plugin skills are invoked namespaced (`dev-team:pipeline-design`); compare on the bare name."""
    return (s or "").split(":")[-1]


# ---- the task graph, worked out by the harness itself (dt's numbers are only a cross-check) --------------
# Pure functions over probe task dicts ({id, depends_on, size, ...}). Only `Depends on` orders tasks; graph-table
# rows with a mitigation are documentation. Depends on IDs outside the given tasks (an earlier milestone) are ignored.

SIZE_WEIGHT = {"XS": 1, "S": 2, "M": 4, "L": 8, "XL": 16}


def deps_of(tasks):
    ids = {t["id"] for t in tasks}
    return {t["id"]: [d for d in t.get("depends_on", []) if d in ids and d != t["id"]] for t in tasks}


def cycles(tasks):
    """Task IDs that sit on a Depends-on cycle."""
    deps, out = deps_of(tasks), set()
    def walk(i, path):
        if i in path:
            out.update(path[path.index(i):])
            return
        for d in deps[i]:
            walk(d, path + [i])
    for t in tasks:
        walk(t["id"], [])
    return sorted(out)


def levels(tasks):
    """Task ID → wave (longest Depends-on chain below it); tasks on a cycle, or after one, are left out."""
    deps, bad, memo = deps_of(tasks), set(cycles(tasks)), {}
    up = ancestors(tasks)
    clean = {t["id"] for t in tasks if t["id"] not in bad and not (up[t["id"]] & bad)}
    def lvl(i):
        if i not in memo:
            memo[i] = 0 if not deps[i] else 1 + max(lvl(d) for d in deps[i])
        return memo[i]
    return {i: lvl(i) for i in [t["id"] for t in tasks] if i in clean}


def waves(tasks):
    lv = levels(tasks)
    out = [[] for _ in range(max(lv.values()) + 1)] if lv else []
    for t in tasks:
        if t["id"] in lv:
            out[lv[t["id"]]].append(t["id"])
    return out


def critical_path(tasks, weight=None):
    """The longest Depends-on chain, root first; `weight(task)` makes it the heaviest instead (default: 1 each)."""
    deps, bad = deps_of(tasks), set(cycles(tasks))
    by_id = {t["id"]: t for t in tasks}
    w = weight or (lambda t: 1)
    memo = {}
    def best(i):
        if i not in memo:
            subs = [best(d) for d in deps[i] if d not in bad]
            tail = max(subs, key=lambda x: x[0], default=(0, []))
            memo[i] = (tail[0] + w(by_id[i]), tail[1] + [i])
        return memo[i]
    ends = [best(t["id"]) for t in tasks if t["id"] not in bad]
    return max(ends, key=lambda x: x[0], default=(0, []))[1]


def ancestors(tasks):
    """Task ID → every task it transitively depends on (cycles included)."""
    deps, out = deps_of(tasks), {}
    for t in tasks:
        seen, stack = set(), list(deps[t["id"]])
        while stack:
            d = stack.pop()
            if d not in seen:
                seen.add(d)
                stack.extend(deps[d])
        out[t["id"]] = seen
    return out


def ready(tasks, done):
    deps = deps_of(tasks)
    return [t["id"] for t in tasks if t["id"] not in done and all(d in done for d in deps[t["id"]])]


def graph_metrics(tasks):
    """N, critical path (unweighted and size-weighted XS=1 S=2 M=4), waves, width per wave, N/CP."""
    cp = critical_path(tasks)
    cpw = critical_path(tasks, lambda t: SIZE_WEIGHT.get(t.get("size", ""), 4))
    wv = waves(tasks)
    by_id = {t["id"]: t for t in tasks}
    return {"tasks": len(tasks), "critical_path": len(cp), "critical_path_ids": cp,
            "critical_path_weighted": sum(SIZE_WEIGHT.get(by_id[i].get("size", ""), 4) for i in cpw),
            "critical_path_weighted_ids": cpw, "waves": wv, "widths": [len(x) for x in wv],
            "width": max((len(x) for x in wv), default=0),
            "parallelism": round(len(tasks) / len(cp), 2) if cp else 0.0, "cycles": cycles(tasks)}


# ---- check logic the grader shares with its selftest (selftest/checks.py runs each one good and bad) -------
# Tasks are dtprobe task dicts {id, kind, step, mode, reason, writes, read_symbols, acceptance, ...}; pipelines
# {id, package, system, entry_file, steps: [{name, owner, in_type, out_type, spine}]}; graph rows {from, to,
# kind, mitigated_by, reason}; step_info maps `PL-NN.step` to its step dict.

TYPE_TOKEN = re.compile(r"\b[A-Z][a-z][A-Za-z0-9]*\b")  # CapWords: Cov, CovReport (a lone T or OHLCV is no type)
NOT_TYPES = {"None", "Optional", "List", "Dict", "Tuple", "Any", "Union"}
# Library and language types a contract field may use without a section of its own.
LIBRARY_TYPES = NOT_TYPES | {
    "DataFrame", "Series", "Index", "DatetimeIndex", "MultiIndex", "Path", "Literal", "Protocol", "Callable", "Iterable", "Iterator", "Sequence",
    "Mapping", "MutableMapping", "Generator", "AsyncIterator", "Awaitable", "Coroutine", "Decimal", "Enum", "IntEnum",
    "StrEnum", "Self", "TypeAlias", "TypeVar", "Generic", "Annotated", "Final", "ClassVar", "NamedTuple", "TypedDict",
    "Timestamp", "Timedelta", "Tensor", "Module", "Random", "Record", "Promise", "Array", "Partial", "Readonly",
    "Date", "Map", "Set", "Error", "Response", "Request", "WebSocket", "BaseModel", "Field", "Counter", "Deque",
    "Pattern", "Type", "Never", "NoReturn", "Required", "NotRequired", "Unpack", "Exception", "Event", "Lock",
    "NaN",  # a value (`float | NaN`), not a type (it9 J4)
}
TEST_PATH = re.compile(r"(^|/)tests?/|\.(test|spec)\.(ts|tsx|js|jsx|mjs)$")
FOLDER_GLOB = re.compile(r"[^*]+/\*\*?")
PL_ID = re.compile(r"PL-\d{2,}")
STEP_KINDS = ("spine", "thicken")
UNCUT_STAGE = ("Idea", "Specced", "Designed")  # below Cut (dt now says Split): no milestone rows yet


def type_names(cell):
    return [x for x in dict.fromkeys(TYPE_TOKEN.findall(cell or "")) if x not in NOT_TYPES]


def write_overlap(a, b):
    """Two Writes entries name the same file: equal paths, or one is a directory (`dir/`, `dir/**`) holding the other."""
    da, db = re.sub(r"/(\*\*?)?$", "", a), re.sub(r"/(\*\*?)?$", "", b)
    dir_a, dir_b = da != a, db != b
    return da == db or (dir_a and db.startswith(da + "/")) or (dir_b and da.startswith(db + "/"))


def writes_overlap(a, b):
    """The Writes entries two tasks share."""
    return sorted({x if x == y else f"{x} ~ {y}" for x in a.get("writes", []) for y in b.get("writes", []) if write_overlap(x, y)})


def is_test_path(w):
    """A test file: any `tests/` segment (root or package-local), or `*.test.ts(x)` / `*.spec.ts`."""
    return bool(TEST_PATH.search(w))


def owner_path(owner, packages=()):
    """A step owner as a path fragment: a leading package id dropped, dots → `/` (`experiments.build` →
    `experiments/build`; `web.views.stock` in package web → `views/stock`)."""
    parts = [p for p in (owner or "").split(".") if p]
    if len(parts) > 1 and parts[0] in packages:
        parts = parts[1:]
    return "/".join(parts)


def owns(path, owner, packages=()):
    """`path` is the owner's module (`…/<owner path>.py|.ts|.tsx`) or under its folder (`…/<owner path>/…`)."""
    op = owner_path(owner, packages)
    return bool(op) and bool(re.search(rf"(^|/){re.escape(op)}(\.(py|pyi|ts|tsx|js|jsx)$|/|$)", path))


def spine_writes_problem(writes, owner, packages=()):
    """Why a spine's Writes is more than its owner module and its unit test, or "". The module may be one folder
    glob (`viewer/draw/**`) or files inside the owner's folder (`api/client.ts`, `api/validate.ts` for owner `api`):
    either is the owner itself. The test may sit under any `tests/`, package-local too, but not intent/, contracts/
    or fixtures/."""
    src = [w for w in writes if not is_test_path(w)]
    tests = [w for w in writes if is_test_path(w)]
    why = []
    op = owner_path(owner, packages)
    in_folder = bool(op) and all(re.search(rf"(^|/){re.escape(op)}/", w) for w in src)
    if len(src) > 1 and not in_folder:
        why.append(f"{len(src)} source entries")
    foreign = [w for w in src if owner and not owns(w, owner, packages)]
    if foreign:
        why.append(f"outside owner {owner}: {', '.join(foreign)}")
    bad_glob = [w for w in src if "*" in w and not FOLDER_GLOB.fullmatch(w)]
    if bad_glob:
        why.append(f"not a folder glob: {', '.join(bad_glob)}")
    bad_tests = [w for w in tests if re.search(r"(^|/)(intent|contracts|fixtures)/", w)]
    if bad_tests:
        why.append(f"not its unit test: {', '.join(bad_tests)}")
    return "; ".join(why)


def call_step(pl, s, packages=()):
    """A step that calls another pipeline (its spine cell says that pipeline "as built") or another package's code
    (its owner's first segment is another package): faked, never spined in this pipeline. "as in PL-NN" reuses that
    pipeline's function in this pipeline's own module, and a PL-NN named for its output is data: neither is a call."""
    cell = re.sub(rf"\bas in\s+{PL_ID.pattern}", "", s.get("spine") or "")
    if re.search(r"\bas built\b", cell) and any(x != pl["id"] for x in PL_ID.findall(cell)):
        return True
    first = (s.get("owner") or "").split(".")[0]
    return bool(pl.get("package")) and first in packages and first != pl["package"]


def step_unit(s):
    """The owner module a step's spine task builds: steps sharing a dotted owner (`data.validate`) share one spine
    task; a bare owner (`data`) names no module, so each of its steps is its own."""
    owner = s.get("owner") or ""
    return owner if "." in owner else f"{owner}:{s['name']}"


def unit_key(pl, s):
    """A step's owner module keyed by its pipeline's package too: qserver's `api.schema` and explorer's
    `api.schema` are two modules (it9 interface F4)."""
    return f"{pl.get('package') or ''}:{step_unit(s)}"


def pipeline_of(task):
    m = PL_ID.match(task.get("step") or "")
    return m.group(0) if m else ""


def step_ids(cell):
    """The step IDs a task's Step cell names: `PL-09.open_run, PL-09.close_run` gives both (it9 interface F9)."""
    return [x.strip() for x in re.split(r"\s*[,;]\s*|\s+and\s+", cell or "") if x.strip()]


def entry_pipelines(symbols, pls):
    """The pipelines whose entry function is one of `symbols` (`data.returns_panel` is PL-11's
    `…/pl11_returns_panel.py::returns_panel`); a symbol qualified by a package (not a module, `load.download`) must
    name the pipeline's own package."""
    packages = {pl.get("package") for pl in pls if pl.get("package")}
    out = set()
    for sym in symbols:
        parts = sym.split(".")
        for pl in pls:
            entry = pl.get("entry") or ""
            func = entry.rsplit("::", 1)[-1] if "::" in entry else ""
            if func and parts[-1] == func and not (len(parts) > 1 and parts[0] in packages and parts[0] != pl.get("package")):
                out.add(pl["id"])
    return out


def wired_pipelines(t, pl_by_id=None):
    """The pipelines a wiring task wires (its own), or a system task wires or swaps (its Step, every PL it reads or
    names, and with `pl_by_id` every pipeline whose entry function it reads: it9 quant aao T47 reads
    `data.returns_panel`, PL-11's entry)."""
    ids = set(PL_ID.findall(t.get("step") or ""))
    if t.get("kind") == "system":
        reads = list(t.get("reads") or t.get("read") or [])
        ids |= set(PL_ID.findall(" ".join([t.get("title", "")] + reads + list(t.get("acceptance") or []))))
        if pl_by_id:
            ids |= entry_pipelines(set(reads) | set(t.get("read_symbols") or []), list(pl_by_id.values()))
    return ids


def swaps_in(a, b, pl_by_id=None):
    """A system task's row to the wiring of a pipeline it swaps in (its real provider): un-faking it is what a
    system task does, so no fake can mitigate the row (design §5.1; it9 interface F6). The pipeline is one it
    wires (wired_pipelines), or one whose smoke test (a test path the wiring task writes) its Verify runs."""
    if a.get("kind") != "system" or b.get("kind") != "wiring":
        return False
    verify = " ".join(a.get("verify") or [])
    return pipeline_of(b) in wired_pipelines(a, pl_by_id) or any(
        re.search(rf"(^|[\s/]){re.escape(w.rsplit('/', 1)[-1])}(\s|$|::)", verify) for w in b.get("writes", []) if is_test_path(w))


def same_step_unit(a, b, step_info):
    """A thicken task `a` extends the module spine task `b` built: b's Step is a's, or a step with the same dotted
    owner. Two thicken tasks of one Step build one module only when their Writes overlap (the `file` class), so
    library modules behind one factory step are not one unit."""
    if b.get("kind") != "spine":
        return False
    if a.get("step") and a.get("step") == b.get("step"):
        return True
    sa, sb = step_info.get(a.get("step")), step_info.get(b.get("step"))
    return bool(sa and sb) and "." in (sa.get("owner") or "") and sa.get("owner") == sb.get("owner")


def records_fold(t):
    """A thicken task that records a fold (phase0.md): its Reason names the fold (`fold: …`, `spine folded into the
    thicken`), or it is a split task that keeps the baseline selectable."""
    return t.get("kind") == "thicken" and bool(
        re.search(r"\bfold", t.get("reason") or "", re.I)
        or (t.get("mode") == "split" and re.search(r"baseline", " ".join(t.get("acceptance") or []), re.I)))


def is_fold(t, tasks):
    """A thicken task that stands in for its step's spine: it records the fold and no spine task has its Step."""
    return records_fold(t) and not any(x.get("kind") == "spine" and x.get("step") == t.get("step") for x in tasks)


def integration_row(r):
    """A graph row written as `integration: <why>` in the Mitigated-by cell is an unmitigated integration edge."""
    m = re.match(r"\s*`?integration\b\s*:?\s*(.*)$", r.get("mitigated_by") or "", re.I | re.S)
    if not m:
        return r
    return {**r, "mitigated_by": "", "reason": "integration: " + m.group(1).strip()}


def runs_in(b, wired, step_info, pl_by_id):
    """Task b builds a step (or wires a pipeline) that runs inside one of the `wired` pipelines: its own pipeline
    is one, or its step's owner module is also a step of one (`train.runs` holds open_run and find_runs), or b is
    a system task over one of them."""
    if pipeline_of(b) in wired:
        return True
    if b.get("kind") == "system":
        return bool(wired_pipelines(b, pl_by_id) & wired)
    sb = step_info.get(b.get("step"))
    return bool(sb) and any(step_unit(s) == step_unit(sb) for p in wired for s in (pl_by_id.get(p) or {}).get("steps", []))


def unmitigated_class(r, by_id, step_info, pl_by_id=None):
    """Classify a `none:` row by its structure, not its wording: (class, "") when allowed, ("", why) when not.
    Allowed: integration (a wiring or system task waits on a step task, wiring or system task of a pipeline it
    wires or swaps), file (the two tasks' Writes overlap), same module (a thicken waits on its own step's spine or
    an earlier thicken of that module), contract change, and order with a reason (a real side-effect order; the
    design writes integration rows as `order` with `integration: <why>`). Every class needs a reason. Whatever the
    row's kind, a wiring task never waits on a thicken task that isn't a fold (phase0.md: wiring depends on spines
    and fold tasks only), and a thicken task never waits on a wiring or system task (tasks.md: no thicken waits on
    wiring; it9 quant aao's thickens waited on wire PL-09 for its conftest.py as `order` rows, F1)."""
    reason = (r.get("reason") or "").strip()
    a, b = by_id.get(r.get("from")), by_id.get(r.get("to"))
    if not reason:
        return "", "no reason"
    if a is None or b is None:
        return "", "names a task outside the plan"
    kind = r.get("kind")
    if a.get("kind") == "thicken" and b.get("kind") in ("wiring", "system"):
        return "", f"a thicken task waits on a {b.get('kind')} task"
    if kind == "contract-change":
        return "contract change", ""
    if a.get("kind") == "wiring" and b.get("kind") == "thicken" and not is_fold(b, by_id.values()):
        return "", "wiring waits on a thicken task that isn't a fold"
    if kind == "order":
        return "order", ""
    if writes_overlap(a, b):
        return "file", ""
    if a.get("kind") in ("wiring", "system") and b.get("kind") in ("spine", "thicken", "wiring", "system") \
            and (a.get("kind") == "system" or b.get("kind") != "system") \
            and (runs_in(b, wired_pipelines(a, pl_by_id), step_info, pl_by_id or {}) or swaps_in(a, b, pl_by_id)):
        return "integration", ""
    if a.get("kind") == "thicken" and b.get("kind") in STEP_KINDS and same_step_unit(a, b, step_info):
        return "same module", ""
    if kind == "code" and a.get("kind") in STEP_KINDS and b.get("kind") in STEP_KINDS:
        return "", "code edge between two steps' tasks"
    return "", "no allowed structure"


def is_declared(sym, declared, own_step=""):
    """Declared by the interface: the symbol, its class (`data.Loader.search` when `data.Loader` is), or the
    task's own step function (the interface task stubs every step)."""
    if sym in declared or any(sym.startswith(d + ".") for d in declared):
        return True
    return bool(own_step) and sym.split(".")[-1] == own_step


def tester_early(t, declared, step_info=None):
    """A split task's tester half can start right after the interface task: every symbol it reads is declared
    there (a method of a declared class counts, and so does its own step's function). A split task that reads
    no symbol at all can't."""
    if t.get("mode") != "split" or not t.get("read_symbols"):
        return False
    own = ((step_info or {}).get(t.get("step")) or {}).get("name", "")
    return all(is_declared(s, declared, own) for s in t["read_symbols"])


def expand_globs(names, symbol_ids):
    """Names with each `*` glob (`data.load_*`) replaced by the symbols it matches; a glob matching none stays."""
    out = []
    for n in names:
        hits = [s for s in symbol_ids if fnmatch.fnmatchcase(s, n)] if "*" in n else []
        out += [x for x in hits or [n] if x not in out]
    return out


def contract_class(s):
    """A class section (`### corridor.CorridorEnv: Corridor test environment`): a CapWords symbol that is not a
    boundary type (a heading titled `type`, or `**Kind:** type`) and not a constant (`lab.LADDER`)."""
    kind = (s.get("fields") or {}).get("Kind", "")
    boundary = (s.get("title") or "").strip().lower().startswith("type") or kind.strip().lower().startswith("type")
    return not boundary and bool(re.match(r"[A-Z][a-z]", s["id"].split(".")[-1]))


def interface_writes_symbols(iface_tasks, symbols):
    """Contract symbols an interface task declares when its acceptance says it writes every step or contract
    function with its signature (the functions), and every contract class too when it names them (the class
    sections, not the boundary types), of the packages or components its Writes covers."""
    out = set()
    for t in iface_tasks:
        text = " ".join([t.get("title", "")] + list(t.get("acceptance") or []))
        if not re.search(r"\bevery\b[^.;]*\b(signature|function)", text, re.I):
            continue
        classes = bool(re.search(r"\bevery\b[^.;]*\bclass(es)?\b", text, re.I))
        for s in symbols:
            if s.get("is_type") and not (classes and contract_class(s)):
                continue
            doc = s.get("doc", "")
            names = [x for x in (doc.split("/")[2] if doc.startswith("docs/packages/") else "", s["id"].split(".")[0]) if x]
            if any(re.search(rf"(^|/)({'|'.join(map(re.escape, names))})(/|$)", w) for w in t.get("writes", [])):
                out.add(s["id"])
    return out


def step_units(pls):
    """Step IDs by owner module (unit_key: package and owner), call steps included: a call step's module is still
    built by the spine of its unit (`lab.runs` holds train_seeds, which calls PL-01, and report_runs)."""
    units = {}
    for pl in pls:
        for s in pl["steps"]:
            units.setdefault(unit_key(pl, s), []).append(f"{pl['id']}.{s['name']}")
    return units


def owns_module(path, owner, packages=()):
    """`path` is the owner's module file itself or its folder glob (`…/api/client.ts`, `…/viewer/draw/**`), not just
    a file somewhere under the owner's folder."""
    op = owner_path(owner, packages)
    return bool(op) and bool(re.search(rf"(^|/){re.escape(op)}(\.(py|pyi|ts|tsx|js|jsx)|/\*\*?)$", path))


def covering_tasks(pl, s, tasks, units, packages=()):
    """The spine tasks and recorded folds that build step s: those whose Step is s or shares its owner module;
    else those whose Reason names s (`one module for open_run and close_run`) or whose Writes are s's owner
    module itself. Steps sharing a module share one spine (phase0.md)."""
    builders = [t for t in tasks if t.get("kind") == "spine" or records_fold(t)]
    ids_ = units.get(unit_key(pl, s), [f"{pl['id']}.{s['name']}"])
    own = [t for t in builders if set(step_ids(t.get("step"))) & set(ids_)]
    if own:
        return own
    named = [t for t in builders if re.search(rf"(?<![\w.]){re.escape(s['name'])}(?!\w)", t.get("reason") or "")]
    return named or [t for t in builders if any(owns_module(w, s.get("owner"), packages)
                                                for w in t.get("writes", []) if not is_test_path(w))]


def wiring_folds(pl, s, tasks, packages=()):
    """The pipeline's wiring tasks that build step s themselves (a trivial step folded into the wiring): their
    title, acceptance or Reason names it (`print_scores` is trivial, so this task builds it (fold)), or their
    Writes are its owner module (`api/static.py` for `mount_static`)."""
    out = []
    for t in tasks:
        if t.get("kind") != "wiring" or pipeline_of(t) != pl["id"]:
            continue
        text = " ".join([t.get("title", ""), t.get("reason") or ""] + list(t.get("acceptance") or []))
        if re.search(rf"(?<![\w.]){re.escape(s['name'])}(?!\w)", text) or any(
                owns_module(w, s.get("owner"), packages) for w in t.get("writes", []) if not is_test_path(w)):
            out.append(t)
    return out


PROBE_WAIT = re.compile(r"\bwaits? on (PB-\d{2,})", re.I)


def outside_milestone(m_pls, m_tasks, deferred=(), declared_names=(), packages=()):
    """{step ID: why} for the steps of a milestone's pipelines that this milestone doesn't build. Library classes
    are steps, so a pipeline lists every stage's classes while each milestone plans only its own (it9 interface
    F4). A step no task builds (no spine or recorded fold, no wiring fold; a call step never has one) is outside
    when:
    (a) its Covers meet the plan's Deferred, and its other Covers are covered by steps this milestone builds;
    (b) its spine cell says it waits on a probe (`waits on PB-01`) and a step it builds has the same Out type
        (a spined stand-in, design §6.2);
    (c) the interface doesn't declare it, no task names it, and every one of its Covers is covered by a step this
        milestone builds (it adds no requirement of its own).
    A step with no Covers is never outside: nothing says it is someone else's."""
    units = step_units(m_pls)
    dfr = set(deferred)
    text = " ".join(json.dumps({k: t.get(k) for k in ("title", "acceptance", "reason", "step", "read_symbols", "read")})
                    for t in m_tasks)
    built, unbuilt = [], []
    for pl in m_pls:
        for s in pl["steps"]:
            by = [] if call_step(pl, s, packages) else covering_tasks(pl, s, m_tasks, units, packages) + wiring_folds(pl, s, m_tasks, packages)
            (built if by else unbuilt).append((pl, s))
    built_covers = {c for _, s in built for c in s.get("covers") or []}
    built_out = {x for _, s in built for x in type_names(s.get("out_type"))}
    out = {}
    for pl, s in unbuilt:
        covers = set(s.get("covers") or [])
        sid = f"{pl['id']}.{s['name']}"
        if not covers:
            continue
        if covers & dfr and covers - dfr <= built_covers:
            out[sid] = f"Deferred ({', '.join(sorted(covers & dfr))})"
        elif PROBE_WAIT.search(s.get("spine") or "") and set(type_names(s.get("out_type"))) & built_out:
            out[sid] = f"waits on {PROBE_WAIT.search(s['spine']).group(1)}; a stand-in with Out {s.get('out_type')} is built"
        elif s["name"] not in declared_names and not re.search(rf"(?<![\w.]){re.escape(s['name'])}(?!\w)", text) \
                and covers <= built_covers:
            out[sid] = "not declared, named by no task, its Covers built by other steps"
    return out


def wave_units(m_pls, m_tasks=(), packages=(), outside=()):
    """The spine units a milestone needs: one per task that builds a non-call step's module (covering_tasks), and
    per owner module for a step no task builds (a bare owner counts per step). Steps `outside` the milestone
    (outside_milestone) and steps a wiring task builds itself need none."""
    units = step_units(m_pls)
    keys = set()
    for pl in m_pls:
        for s in pl["steps"]:
            if call_step(pl, s, packages) or f"{pl['id']}.{s['name']}" in outside:
                continue
            cover = covering_tasks(pl, s, m_tasks, units, packages)
            spines = [t for t in cover if t.get("kind") == "spine"]
            pick = spines if spines else cover
            if not pick and wiring_folds(pl, s, m_tasks, packages):
                continue
            keys.add(f"task {pick[0]['id']}" if len(pick) == 1 else unit_key(pl, s))
    return sorted(keys)


def wave_ready(m_tasks, iface_ids, deps, declared, step_info=None):
    """(spine tasks ready right after the interface task, split spine or fold tasks whose tester halves start there).
    Implementer halves, wiring and a library thicken's tester half don't count: they build no step's module."""
    def is_spine(t):
        return t.get("kind") == "spine" or (not t.get("kind") and t.get("is_spine"))
    spines = [t["id"] for t in m_tasks if iface_ids and t["id"] not in iface_ids and is_spine(t) and set(deps[t["id"]]) <= set(iface_ids)]
    testers = [t["id"] for t in m_tasks if t["id"] not in iface_ids and t["id"] not in spines
               and (is_spine(t) or is_fold(t, m_tasks)) and tester_early(t, declared, step_info)]
    return spines, testers


def phase0_misses(m_pls, m_tasks, iface_ids, declared_names, packages=(), outside=()):
    """What `phase0_split` finds missing in a milestone's pipelines: types the interface lacks (of the steps the
    milestone builds); a step unit (owner module) without exactly one spine task, unless a fold applies; a package
    pipeline without one wiring task writing its entry and a smoke test (any test path); a system pipeline no
    system task names. Steps `outside` the milestone (outside_milestone) are left out."""
    units = step_units(m_pls)
    miss = []
    for pl in m_pls:
        pid = pl["id"]
        if pl.get("system"):
            if not any(t.get("kind") == "system" and pid in wired_pipelines(t) for t in m_tasks):
                miss.append(f"{pid}: system pipeline with no system task naming it")
            continue
        steps = [s for s in pl["steps"] if f"{pid}.{s['name']}" not in outside]
        used = {x for s in steps for x in type_names(s.get("in_type")) + type_names(s.get("out_type"))}
        if not iface_ids:
            miss.append(f"{pid}: no interface task")
        elif used - set(declared_names):
            miss.append(f"{pid}: interface lacks {sorted(used - set(declared_names))}")
        wiring = [t for t in m_tasks if t.get("kind") == "wiring" and pipeline_of(t) == pid]
        for s in steps:
            if call_step(pl, s, packages):
                continue
            cover = covering_tasks(pl, s, m_tasks, units, packages)
            spine = [t for t in cover if t.get("kind") == "spine"]
            # Folds: a thicken that records one (records_fold), or a trivial step the wiring builds (wiring_folds).
            folded = [t for t in cover if t.get("kind") != "spine"] + wiring_folds(pl, s, m_tasks, packages)
            if len(spine) != 1 and not folded:
                miss.append(f"{pid}.{s['name']}: {len(spine)} spine tasks")
        entry = [t for t in wiring if any(write_overlap(w, pl.get("entry_file") or "") for w in t.get("writes", []))
                 and any(is_test_path(w) for w in t.get("writes", []))]
        if len(wiring) != 1 or not entry:
            miss.append(f"{pid}: {len(wiring)} wiring tasks, {len(entry)} writing the entry {pl.get('entry_file')} and a smoke test")
    return miss


def wiring_shared_file(a, b):
    """Two wiring tasks chained on a file both write (a shared `__main__.py` or entry module): each pipeline has its
    own entry module (build-planning phase0.md), so the chain is a false serialization (iteration 8's F1)."""
    return a.get("kind") == "wiring" and b.get("kind") == "wiring" and bool(writes_overlap(a, b))


def wiring_crosses_frozen(a, b, pl_by_id, step_info, faked, packages=()):
    """A wiring task waits on a step task of code its pipeline only calls (another package's step, or another
    pipeline's), although the interface task declares a fake for that call: the wiring should run against the
    fake. `faked` holds the symbols the plan names as fakes. Its own pipeline's steps in its own package are
    integration, never this."""
    if a.get("kind") != "wiring" or b.get("kind") not in STEP_KINDS:
        return False
    pa, sb = pl_by_id.get(pipeline_of(a)), step_info.get(b.get("step"))
    if not pa or not sb:
        return False
    if pipeline_of(b) == pa["id"]:
        reach = [s for s in pa["steps"] if s["name"] == sb["name"] and call_step(pa, s, packages)]
    else:
        reach = [s for s in pa["steps"] if call_step(pa, s, packages)
                 and (pipeline_of(b) in PL_ID.findall(s.get("spine") or "") or s.get("owner") == sb.get("owner"))]
    return any(f == s.get("owner") or f.startswith((s.get("owner") or "?") + ".") or f.split(".")[-1] == s["name"]
               for s in reach for f in faked)


def boundary_fake_ok(sym, sec, pls, consumer_pl=None, packages=()):
    """A fake of a cross-pipeline boundary inside one package (design §4.1 fakes any entry or function whose Used by
    names another pipeline): the symbol's contract section has a Boundary line, its Used by names a pipeline other
    than the one owning it (a step of that name that isn't a call, or the pipeline whose entry it is), and the
    consumer's pipeline, when known, is one of the Used by pipelines (it9 rl inc `evaluate.evaluate`, rl aao
    PL-02's entry `train.run_train`; interface F5)."""
    fields = bullet_fields((sec or {}).get("fields") or {})
    if not sec or not (fields.get("Boundary") or "").strip():
        return False
    name = sym.split(".")[-1]
    owners = {pl["id"] for pl in pls for s in pl["steps"] if s["name"] == name and not call_step(pl, s, packages)}
    owners |= entry_pipelines([sym], pls)
    users = set(PL_ID.findall(fields.get("Used by") or ""))
    return bool(users - owners) and (not consumer_pl or consumer_pl in users)


def boundaries(pl):
    """A pipeline's cross-owner boundaries, Out matched to In: (from step, to step, types) for each later step with
    another owner whose In names a type the earlier step's Out names. An adjacent cross-owner pair whose cells
    name no type at all gives types []."""
    out, steps = [], pl["steps"]
    for i, a in enumerate(steps):
        outs = type_names(a.get("out_type"))
        nxt = steps[i + 1] if i + 1 < len(steps) else None
        if not outs and nxt and nxt.get("owner") != a.get("owner") and not type_names(nxt.get("in_type")):
            out.append((a, nxt, []))
            continue
        for b in steps[i + 1:]:
            shared = [t for t in outs if t in type_names(b.get("in_type"))]
            if shared and b.get("owner") != a.get("owner"):
                out.append((a, b, shared))
    return out


CASE_FIELDS = ("cases", "case", "sample", "samples", "fixtures")


def bullet_fields(fields):
    """A section's bullet fields with the ones written on one line split out: `Boundary: server · Fixtures: … ·
    Cases: …` gives Boundary, Fixtures and Cases."""
    out = {}
    for k, v in fields.items():
        parts = re.split(r"\s+·\s+", v or "")
        out[k] = parts[0]
        for p in parts[1:]:
            m = re.match(r"\*{0,2}([A-Z][\w ]{0,30}?):\*{0,2}\s*(.*)$", p)
            if m:
                out.setdefault(m.group(1), m.group(2))
            else:
                out[k] += " · " + p
    return out


def named_case(fields):
    """The cases a contract type section names (its Cases, Sample or Fixtures field), or ""."""
    vals = [v.strip() for k, v in bullet_fields(fields).items() if k.lower() in CASE_FIELDS
            and v.strip().lower() not in ("", "—", "-", "none")]
    return " · ".join(vals)


def is_double(fields):
    """The section's case is a fake or replay double: the type's sample, not a mock of a step."""
    return bool(re.search(r"\b(fake|double|replay)", named_case(fields), re.I))


def sample_written(sid, iface_tasks, on_disk=False):
    """`tests/contracts/<sid>/` exists, or an interface task's Writes covers it (`tests/contracts/**`,
    `tests/contracts/data.*/**`): the interface task writes the samples."""
    target = f"tests/contracts/{sid}/sample"
    return on_disk or any(write_overlap(w, target) or fnmatch.fnmatchcase(target, w)
                          or fnmatch.fnmatchcase(target, re.sub(r"/\*\*?$", "", w) + "/*")
                          for t in iface_tasks for w in t.get("writes", []))


QUALIFIED = re.compile(r"\b([A-Za-z_]\w*)((?:\.\w+)*)\.([A-Z][a-z][A-Za-z0-9]*)\b")


def field_types(text, modules=None):
    """CapWords types a contract type section's code (inline `code` spans and fenced blocks) uses in its field
    annotations (`world: WorldSettings`) and return annotations (`-> Returns`); comments, prose and library
    types left out. With `modules` (the contract's packages and symbol prefixes), a type qualified by any other
    module is a library type too (`JSX.Element`, `duckdb.DuckDBPyConnection`; it9 interface F8)."""
    code, fenced = [], False
    for line in (text or "").splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        code += [line] if fenced else re.findall(r"`([^`]+)`", line)
    names = []

    def tokens(s):
        if modules is not None:
            s = QUALIFIED.sub(lambda m: m.group(0) if m.group(1) in modules else " ", s)
        return TYPE_TOKEN.findall(s)
    for c in code:
        c = c.split("#")[0].split("//")[0]
        for ann in re.findall(r"\b\w+\??\s*:\s*([^;=]+)", c):
            names += tokens(ann)
        for ret in re.findall(r"->\s*([^;:]+)", c):
            names += tokens(ret)
    return [n for n in dict.fromkeys(names) if n not in LIBRARY_TYPES]


def contract_text(proj, symbols):
    """Every contract file the symbols come from, whole (its preamble too: rl aao's `Direction = Literal[…]` sits
    above the first section, it9 interface F8), then each symbol section's text."""
    docs = sorted({s["doc"] for s in symbols if s.get("doc")})
    files = [(pathlib.Path(proj) / rel).read_text() for rel in docs if (pathlib.Path(proj) / rel).is_file()]
    return "\n".join(files + [s.get("text", "") for s in symbols])


def contract_modules(packages, symbols):
    """The names a contract-qualified type may start with: the packages and every symbol's first segment."""
    return set(packages) | {s["id"].split(".")[0] for s in symbols}


def top_level_split(s, sep=","):
    """`s` split at `sep` outside brackets and quotes."""
    parts, depth, cur, quote = [], 0, "", None
    for ch in s:
        if quote:
            quote = None if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        cur += ch
    return parts + [cur]


def defined_in(name, text, known=(), _depth=0):
    """A type defined inline in a contract: `class Name`, `type Name`, `interface Name`, `enum Name`, `Name = …`, a
    note giving its typed fields (`# Name: share: float; passed: bool`, or `` - `Name`: index `date`; `close: float64` ``
    with typed fields anywhere on its line), a constructor whose every parameter is typed (`FixedEntry(spec: str)`),
    or a type that mirrors another (`ActionDto` mirrors `qdata.CorporateAction`, or a deeper path
    `qdata.query.Company`; `ActionMsg` mirrors one `qdata.query.Actions` row; `DayDiffMsg` mirroring `DayDiff`, a
    bare name that is in `known` (has its own section) or is itself defined inline (`DayDiff(day: date, …)`);
    `SpellDto` and `ExitDto` mirror their `qdata` types). A note
    listing bare field names (`# FlagRow: ticker, date`) or a constructor with an untyped parameter
    (`LearnerEntry(kind: str, settings)`) defines nothing."""
    n = re.escape(name)
    if re.search(rf"\b(class|type|interface|enum)\s+{n}\b|\b{n}\s*=[^=]|\b{n}\s*:\s*\w+\??\s*:\s*[A-Za-z]"
                 rf"|`{n}`\s*:[^\n]*?\b\w+\??\s*:\s*`?[A-Za-z]", text):
        return True
    mirror = rf"\b{n}\b[`\w\s,]*?\bmirror(?:s|ing)?\s+(?:one\s+)?"
    if re.search(mirror + r"(`?[a-z]\w*(?:\.\w+)*\.[A-Z]\w*|their\s+`?[a-z]\w*`?\s+types?\b)", text):
        return True
    if any(m.group(1) in known or (_depth < 2 and m.group(1) != name and defined_in(m.group(1), text, known, _depth + 1))
           for m in re.finditer(mirror + r"`?([A-Z]\w*)\b", text)):
        return True
    for m in re.finditer(rf"\b{n}\(", text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += {"(": 1, ")": -1}.get(text[i], 0)
            i += 1
        params = [p.strip() for p in top_level_split(text[m.end():i - 1]) if p.strip()]
        if params and all(re.match(r"\w+\s*:\s*\S", p) for p in params):
            return True
    return False


def stages_uncut(stages):
    """Roadmap stages with no milestone rows yet: Idea, Specced or Designed, below Cut (which dt now calls Split)."""
    return [f"{s['id']} {s.get('name') or ''}={s.get('derived')}" for s in stages if s.get("derived") in UNCUT_STAGE]


def depends_cell(cell):
    """A roadmap Depends cell → (milestone IDs, what each needs), read as dt reads it (`\\bM\\d+\\b`):
    `M1 (stats.Cov, PL-01 output), M2` → (["M1", "M2"], {"M1": "stats.Cov, PL-01 output"})."""
    ids = list(dict.fromkeys(re.findall(r"\bM\d+\b", cell or "")))
    needs = {m.group(1): m.group(2).strip() for m in re.finditer(r"\b(M\d+)\s*\(([^)]*)\)", cell or "")}
    return ids, needs


# Skill attribution per turn: a Skill call, a `dt status --skill X` call, or a read of skills/X/ files.
DT_SKILL = re.compile(r"\bstatus\b[^|;&\n]*?--skill[ =]+([a-z][\w-]*)")
SKILL_READ = re.compile(r"(?:^|/)skills/([a-z][\w-]*)/(?:SKILL\.md|references/)")


SLASH = re.compile(r"^\s*/dev-team:([a-z][\w-]*)")


def slash_skill(t):
    """The skill a turn's user message loads with `/dev-team:<skill>` (the driver opens a fresh session that way,
    and no Skill call follows), or ""; a run whose turns record no user text falls back on the session record
    (`session.new`, unless it says `slash: false`)."""
    m = SLASH.match(t.get("user") or "")
    if m:
        return m.group(1)
    s = t.get("session") or {}
    return s.get("skill") or "" if s.get("new") and s.get("slash") is not False and not t.get("user") else ""


def call_skills(c):
    """The skills one tool call shows at work: a Skill call's skill, `dt status --skill X`, a read of skills/X/."""
    i = c.get("input") or {}
    if c.get("name") == "Skill":
        return [skill_name(i.get("skill") or i.get("name") or "")] if (i.get("skill") or i.get("name")) else []
    text = " ".join(str(i.get(k) or "") for k in ("command", "file_path", "path", "pattern"))
    return DT_SKILL.findall(text) + SKILL_READ.findall(text)


def turn_skill_seq(turns, calls=()):
    """Turn → the skills it worked in, in order: a slash-loaded skill first, then each tool call's (call_skills).
    A turn whose stream has no Skill call (an older stream, or one cut short) adds its recorded `skills` after."""
    out = {t["turn"]: [slash_skill(t)] if slash_skill(t) else [] for t in turns}
    seen_skill = set()
    for c in calls:
        if c.get("turn") in out:
            out[c["turn"]] += call_skills(c)
            if c.get("name") == "Skill":
                seen_skill.add(c["turn"])
    for t in turns:
        if t["turn"] not in seen_skill:
            out[t["turn"]] += [skill_name(s) for s in t.get("skills", [])]
    return {n: [s for s in seq if s] for n, seq in out.items()}


def turn_skill_map(turns, calls=()):
    """Turn → the skills it worked in: its Skill calls, plus each `dt status --skill X` and skills/X/ read among
    its tool calls (`calls`: probefacts.tool_calls records), so a turn that continues a skill without a Skill
    call is still attributed to it. A turn whose user message opens with `/dev-team:<skill>` (the driver's fresh
    sessions) worked in that skill too (it9 interface F7)."""
    seq = turn_skill_seq(turns, calls)
    return {t["turn"]: {skill_name(s) for s in t.get("skills", [])} | set(seq[t["turn"]]) for t in turns}


INTAKE_AGENT = re.compile(r"\b(summari[sz]e|intake)\b.*\.\w{1,5}\b", re.I)


def intake_turns(turns, skills_by_turn, refs_changed=()):
    """Turns that did reference intake: attributed to reference-intake, or that changed docs/references.md and
    launched Agents, or whose Agent launches read like intake (`Summarize factors.py`)."""
    out = []
    for t in turns:
        n = t["turn"]
        by_agent = any(INTAKE_AGENT.search(a.get("description") or "") for a in t.get("agents", []))
        if "reference-intake" in skills_by_turn.get(n, set()) or (n in refs_changed and t.get("agents")) or by_agent:
            out.append(t)
    return out


REVISE_ASK = re.compile(r"\brevis(e|ion|ing)\b", re.I)
UPSTREAM = re.compile(r"\b(architecture|contract)\b", re.I)


def routed_revise(layers, prev_turn, changed, prev_layers=()):
    """A two-layer turn that is a routed Revise round trip: architecture plus pipelines (or tests), after a turn
    that stopped at its own gate (it drafted at most that one other layer), left that pipelines or tests doc
    Draft and asked to run the architecture revision. `prev_turn` is the previous turn record (`status` lines,
    `assistant` text); `changed` the paths this turn changed; `prev_layers` the layers the previous turn drafted."""
    layers = set(layers)
    if not prev_turn or len(layers) != 2 or "arch" not in layers or not (layers - {"arch"}) <= {"pipelines", "tests"}:
        return False
    if not set(prev_layers) <= layers - {"arch"}:
        return False
    suffix = "/pipelines.md" if "pipelines" in layers else "/tests.md"
    prev = dict(l.split(": ", 1) for l in (prev_turn.get("status") or "").splitlines() if ": " in l)
    left_draft = any(p.endswith(suffix) and prev.get(p, "").split(" (")[0].strip() == "Draft" for p in changed)
    text = prev_turn.get("assistant") or ""
    return left_draft and bool(REVISE_ASK.search(text)) and bool(UPSTREAM.search(text))


ROUTED_NAMED = re.compile(r"\brout(ed|es?)\b[^.\n]{0,200}\bfix(es)?\b|\bfix(es)?\b[^.\n]{0,200}\brouted\b", re.I)
MAKE_FIXES = re.compile(r"\b(make|apply|do|run)\b[^.\n]{0,40}\b(routed\s+)?fix(es)?\b", re.I)
ROUTED_ARCH_LINES = 25


def routed_fixes(layers, added, prev_turn, user):
    """A two-layer turn that applies routed fixes the user approved, then drafts one layer: architecture plus one
    other layer, the architecture change small (at most ROUTED_ARCH_LINES added lines, `added`: layer → lines),
    after a turn that named the routed fixes (`prev_turn`'s assistant text) and with a user message telling the
    agent to make them (it9 rl aao turn 13: the TRAIN-03 count and AD-09's corridor, then the M1 plan; interface F10)."""
    layers = set(layers)
    if not prev_turn or len(layers) != 2 or "arch" not in layers or added.get("arch", 0) > ROUTED_ARCH_LINES:
        return False
    return bool(ROUTED_NAMED.search(prev_turn.get("assistant") or "")) and bool(MAKE_FIXES.search(user or ""))


# data_sources_suggested (grade.py): sources the agent may raise beyond the user's Sharadar prices and yahooquery cross-check,
# matched by name: {name: (pattern, is a fundamentals source)}. Sharadar counts only as SF1 or "Sharadar
# Fundamentals"; EODHD counts as fundamentals only where its fundamentals are named.
DATA_SOURCES = {
    "SEC EDGAR / XBRL": (r"\bEDGAR\b|\bXBRL\b|companyfacts|company[- ]facts API", True),
    "SimFin": (r"\bSimFin\b", True),
    "Financial Modeling Prep": (r"Financial Modeling Prep|\bFMP\b", True),
    "Sharadar SF1": (r"\bSF1\b|Sharadar(?:'s)? (?:Core US )?Fundamentals", True),
    "EODHD fundamentals": (r"\bEODHD?\b[^.\n]{0,80}fundamental|fundamental[^.\n]{0,80}\bEODHD?\b", True),
    "Compustat": (r"\bCompustat\b", True),
    "EODHD": (r"\bEODHD?\b|EOD Historical Data", False),
    "Tiingo": (r"\bTiingo\b", False),
    "Polygon": (r"\bPolygon(?:\.io)?\b", False),
    "Alpha Vantage": (r"Alpha ?Vantage", False),
    "Alpaca": (r"\bAlpaca\b", False),
    "Norgate": (r"\bNorgate\b", False),
    "CRSP": (r"\bCRSP\b|\bWRDS\b", False),
    "Stooq": (r"\bStooq\b", False),
    "Databento": (r"\bDatabento\b", False),
    "Intrinio": (r"\bIntrinio\b", False),
    "FRED": (r"\bFRED\b", False),
}


FUNDAMENTALS = re.compile(r"fundamental|earnings|balance[- ]sheet|income statement|financial statement|cash flow|"
                          r"\bXBRL\b|company[- ]?facts|\bSF1\b|\b10-[KQ]\b", re.I)


def sentences(text):
    """Sentences, list items and table cells: a source counts for fundamentals only in one about them."""
    return [s for s in re.split(r"(?<=[.;!?])\s+|\n|\|", text or "") if s.strip()]


def data_sources(texts):
    """({source: [doc, ...]} for every DATA_SOURCES name found in `texts` ({doc: text}), the fundamentals ones).
    A fundamentals source counts as one only where a sentence naming it is about fundamentals (earnings, balance
    sheets, XBRL company facts): it9 quant aao's EDGAR is for SIC sector codes (flow §6)."""
    found = {name: sorted(rel for rel, txt in texts.items() if re.search(pat, txt, re.I))
             for name, (pat, _) in DATA_SOURCES.items()}
    found = {name: rels for name, rels in found.items() if rels}
    fund = [name for name in found if DATA_SOURCES[name][1] and any(
        re.search(DATA_SOURCES[name][0], s, re.I) and FUNDAMENTALS.search(s) for txt in texts.values() for s in sentences(txt))]
    return found, sorted(fund)


CROSSCHECK = re.compile(r"\byahoo(query)?\b|\byfinance\b", re.I)


def crosscheck_named(user_msgs, docs):
    """crosscheck_facts_reached_design applies: a user message or a design doc names the Yahoo cross-check."""
    return any(CROSSCHECK.search(x or "") for x in list(user_msgs) + list(docs))


def crosscheck_facts(entries, design, planted):
    """crosscheck_facts_reached_design (grade.py): (passed, metrics) for the cross-check source's probe `entries`
    (probefacts entries), the `design` text (its decisions and the Risks) and the vendor's PLANTED facts: a probe
    Answered, its Verdict, Caveats or results naming every lost name, the design saying the close isn't raw, and the
    ticker reuse named in either."""
    answered = [e["id"] for e in entries if e["kind"] == "answered"]
    text = " ".join(e["verdict"] + " " + e["caveats"] + " " + " ".join(c["result"] for c in e["checks"]) for e in entries)
    m = {"answered": answered, "missing_not_named": [n for n in planted["missing"] if not re.search(rf"\b{n}\b", text)],
         "adjusted_only": bool(re.search(planted["adjusted_only"], design, re.I)),
         "reused": bool(re.search(planted["reused"], design + " " + text, re.I)),
         "not_point_in_time": bool(re.search(planted["not_pit"], design + " " + text, re.I))}
    return bool(answered and not m["missing_not_named"] and m["adjusted_only"] and m["reused"]), m


# spec_ml_beats_classical: the ML bar names the classical portfolios or the earlier stage's named benchmark.
ML_BEATS_CLASSICAL = re.compile(
    r"(PPO|agent|forecast[- ]driven|ML[- ]driven).{0,600}(min(imum)?[- ]variance|classical|HRP|risk parity|"
    r"S2'?s? (best|named|benchmark)|best (classical|strategy)|benchmark)", re.S | re.I)


# ---- the user's words (design/requests.md): requests_captured and requests_append_only over dtprobe's `requests`
def facts_stated(stated_facts, turns):
    """{fact id: [turn, ...]} for each checkable scenario fact (scenarios.json `stated_facts`: id and pattern) that a
    user message in `turns` matches: what the simulated user actually said, not everything it could have."""
    out = {}
    for f in stated_facts:
        hit = [t["turn"] for t in turns if re.search(f["pattern"], t.get("user") or "", re.I)]
        if hit:
            out[f["id"]] = hit
    return out


def requests_missed(stated_facts, stated, words):
    """requests_captured: the stated facts (`facts_stated`) whose pattern no UR line's quoted `words` match."""
    pat = {f["id"]: f["pattern"] for f in stated_facts}
    return [fid for fid in stated if not any(re.search(pat[fid], w, re.I) for w in words)]


def requests_rewritten(states):
    """requests_append_only: `states` is [(turn, {UR id: words} or None when there is no docs/requests.md, [UR ids
    whose lines don't parse])] in turn order; returns each line whose words changed or that vanished since the turn
    before. A line that stops parsing counts once, and keeps its last words for the turns after."""
    out, prev, broken = [], None, set()
    for turn, cur, bad in states:
        cur = cur or {}
        for id_, w in (prev or {}).items():
            if id_ in bad:
                if id_ not in broken:
                    out.append(f"turn {turn}: {id_} \"{w}\" no longer parses")
            elif id_ not in cur:
                out.append(f"turn {turn}: {id_} \"{w}\" vanished")
            elif cur[id_] != w:
                out.append(f"turn {turn}: {id_} \"{w}\" became \"{cur[id_]}\"")
        broken = {i for i in bad if i in (prev or {})}
        prev = {**cur, **{i: prev[i] for i in broken}}
    return out
