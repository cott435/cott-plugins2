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


def probe(proj, dt=None):
    """dtprobe.py facts (live spec IDs, pipelines, plans and tasks, derived roadmap rows, doc statuses)."""
    scripts = pathlib.Path(dt or REPO_DT).parent
    r = subprocess.run([sys.executable, str(HERE / "dtprobe.py"), str(scripts), str(proj)],
                       capture_output=True, text=True, timeout=300)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"_error": r.stderr.strip()[-600:], "live_spec": [], "removed_spec": [], "pipelines": [],
                "plans": [], "roadmap": [], "stages": [], "references": [], "symbols": [], "tests": [], "docs": {},
                "packages": [], "probes": [], "probes_retired": [], "decisions": [], "dt_probes": None}


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
    glob (`viewer/draw/**`); the test may sit under any `tests/`, package-local too, but not intent/, contracts/
    or fixtures/."""
    src = [w for w in writes if not is_test_path(w)]
    tests = [w for w in writes if is_test_path(w)]
    why = []
    if len(src) > 1:
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
    """A step that calls another pipeline (its spine is that pipeline as built) or another package's code (its
    owner's first segment is another package): faked, never spined in this pipeline."""
    if any(x != pl["id"] for x in PL_ID.findall(s.get("spine") or "")):
        return True
    first = (s.get("owner") or "").split(".")[0]
    return bool(pl.get("package")) and first in packages and first != pl["package"]


def step_unit(s):
    """The owner module a step's spine task builds: steps sharing a dotted owner (`data.validate`) share one spine
    task; a bare owner (`data`) names no module, so each of its steps is its own."""
    owner = s.get("owner") or ""
    return owner if "." in owner else f"{owner}:{s['name']}"


def pipeline_of(task):
    m = PL_ID.match(task.get("step") or "")
    return m.group(0) if m else ""


def wired_pipelines(t):
    """The pipelines a wiring task wires (its own), or a system task wires or swaps (its Step and every PL it reads
    or names)."""
    ids = set(PL_ID.findall(t.get("step") or ""))
    if t.get("kind") == "system":
        ids |= set(PL_ID.findall(" ".join([t.get("title", "")] + list(t.get("reads") or t.get("read") or [])
                                          + list(t.get("acceptance") or []))))
    return ids


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
        return bool(wired_pipelines(b) & wired)
    sb = step_info.get(b.get("step"))
    return bool(sb) and any(step_unit(s) == step_unit(sb) for p in wired for s in (pl_by_id.get(p) or {}).get("steps", []))


def unmitigated_class(r, by_id, step_info, pl_by_id=None):
    """Classify a `none:` row by its structure, not its wording: (class, "") when allowed, ("", why) when not.
    Allowed: integration (a wiring or system task waits on a step task, wiring or system task of a pipeline it
    wires or swaps), file (the two tasks' Writes overlap), same module (a thicken waits on its own step's spine or
    an earlier thicken of that module), contract change, and order with a reason (a real side-effect order; the
    design writes integration rows as `order` with `integration: <why>`). Every class needs a reason. Whatever the
    row's kind, a wiring task never waits on a thicken task that isn't a fold (phase0.md: wiring depends on spines
    and fold tasks only)."""
    reason = (r.get("reason") or "").strip()
    a, b = by_id.get(r.get("from")), by_id.get(r.get("to"))
    if not reason:
        return "", "no reason"
    if a is None or b is None:
        return "", "names a task outside the plan"
    kind = r.get("kind")
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
            and runs_in(b, wired_pipelines(a), step_info, pl_by_id or {}):
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


def interface_writes_symbols(iface_tasks, symbols):
    """Contract functions an interface task declares when its acceptance says it writes every step or contract
    function with its signature: the non-type symbols of the packages or components its Writes covers."""
    out = set()
    for t in iface_tasks:
        text = " ".join([t.get("title", "")] + list(t.get("acceptance") or []))
        if not re.search(r"\bevery\b[^.;]*\b(signature|function)", text, re.I):
            continue
        for s in symbols:
            if s.get("is_type"):
                continue
            doc = s.get("doc", "")
            names = [x for x in (doc.split("/")[2] if doc.startswith("docs/packages/") else "", s["id"].split(".")[0]) if x]
            if any(re.search(rf"(^|/)({'|'.join(map(re.escape, names))})(/|$)", w) for w in t.get("writes", [])):
                out.add(s["id"])
    return out


def step_units(pls):
    """Step IDs by owner module (step_unit), call steps included: a call step's module is still built by the
    spine of its unit (`lab.runs` holds train_seeds, which calls PL-01, and report_runs)."""
    units = {}
    for pl in pls:
        for s in pl["steps"]:
            units.setdefault(step_unit(s), []).append(f"{pl['id']}.{s['name']}")
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
    ids_ = units.get(step_unit(s), [f"{pl['id']}.{s['name']}"])
    own = [t for t in builders if t.get("step") in ids_]
    if own:
        return own
    named = [t for t in builders if re.search(rf"(?<![\w.]){re.escape(s['name'])}(?!\w)", t.get("reason") or "")]
    return named or [t for t in builders if any(owns_module(w, s.get("owner"), packages)
                                                for w in t.get("writes", []) if not is_test_path(w))]


def wave_units(m_pls, m_tasks=(), packages=()):
    """The spine units a milestone needs: one per task that builds a non-call step's module (covering_tasks), and
    per owner module for a step no task builds (a bare owner counts per step)."""
    units = step_units(m_pls)
    keys = set()
    for pl in m_pls:
        for s in pl["steps"]:
            if call_step(pl, s, packages):
                continue
            cover = covering_tasks(pl, s, m_tasks, units, packages)
            spines = [t for t in cover if t.get("kind") == "spine"]
            pick = spines if spines else cover
            keys.add(f"task {pick[0]['id']}" if len(pick) == 1 else step_unit(s))
    return sorted(keys)


def wave_ready(m_tasks, iface_ids, deps, declared, step_info=None):
    """(spine tasks ready right after the interface task, split tasks whose tester halves start there). Implementer
    halves and wiring don't count."""
    def is_spine(t):
        return t.get("kind") == "spine" or (not t.get("kind") and t.get("is_spine"))
    spines = [t["id"] for t in m_tasks if iface_ids and t["id"] not in iface_ids and is_spine(t) and set(deps[t["id"]]) <= set(iface_ids)]
    testers = [t["id"] for t in m_tasks if t["id"] not in iface_ids and t["id"] not in spines and tester_early(t, declared, step_info)]
    return spines, testers


def phase0_misses(m_pls, m_tasks, iface_ids, declared_names, packages=()):
    """What `phase0_split` finds missing in a milestone's pipelines: types the interface lacks; a step unit
    (owner module) without exactly one spine task, unless a fold applies; a package pipeline without one wiring
    task writing its entry and a smoke test (any test path); a system pipeline no system task names."""
    units = step_units(m_pls)
    miss = []
    for pl in m_pls:
        pid = pl["id"]
        if pl.get("system"):
            if not any(t.get("kind") == "system" and pid in wired_pipelines(t) for t in m_tasks):
                miss.append(f"{pid}: system pipeline with no system task naming it")
            continue
        used = {x for s in pl["steps"] for x in type_names(s.get("in_type")) + type_names(s.get("out_type"))}
        if not iface_ids:
            miss.append(f"{pid}: no interface task")
        elif used - set(declared_names):
            miss.append(f"{pid}: interface lacks {sorted(used - set(declared_names))}")
        wiring = [t for t in m_tasks if t.get("kind") == "wiring" and pipeline_of(t) == pid]
        for s in pl["steps"]:
            if call_step(pl, s, packages):
                continue
            cover = covering_tasks(pl, s, m_tasks, units, packages)
            spine = [t for t in cover if t.get("kind") == "spine"]
            # Folds: a thicken that records one (records_fold), or a trivial step done by the wiring.
            folded = [t for t in cover if t.get("kind") != "spine"]
            folded += [t for t in wiring if re.search(rf"\b{re.escape(s['name'])}\b",
                                                      t.get("title", "") + " " + " ".join(t.get("acceptance") or []))]
            if len(spine) != 1 and not folded:
                miss.append(f"{pid}.{s['name']}: {len(spine)} spine tasks")
        entry = [t for t in wiring if any(write_overlap(w, pl.get("entry_file") or "") for w in t.get("writes", []))
                 and any(is_test_path(w) for w in t.get("writes", []))]
        if len(wiring) != 1 or not entry:
            miss.append(f"{pid}: {len(wiring)} wiring tasks, {len(entry)} writing the entry {pl.get('entry_file')} and a smoke test")
    return miss


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


def field_types(text):
    """CapWords types a contract type section's code (inline `code` spans and fenced blocks) uses in its field
    annotations (`world: WorldSettings`) and return annotations (`-> Returns`); comments, prose and library
    types left out."""
    code, fenced = [], False
    for line in (text or "").splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        code += [line] if fenced else re.findall(r"`([^`]+)`", line)
    names = []
    for c in code:
        c = c.split("#")[0].split("//")[0]
        for ann in re.findall(r"\b\w+\??\s*:\s*([^;=]+)", c):
            names += TYPE_TOKEN.findall(ann)
        for ret in re.findall(r"->\s*([^;:]+)", c):
            names += TYPE_TOKEN.findall(ret)
    return [n for n in dict.fromkeys(names) if n not in LIBRARY_TYPES]


def defined_in(name, text):
    """A type defined inline in a contract: `class Name`, `type Name`, `interface Name`, `enum Name`, `Name = …`, or
    a note giving its typed fields (`# Name: share: float; passed: bool`). A note listing bare field names
    (`# FlagRow: ticker, date`) defines nothing."""
    n = re.escape(name)
    return bool(re.search(rf"\b(class|type|interface|enum)\s+{n}\b|\b{n}\s*=[^=]|\b{n}\s*:\s*\w+\??\s*:\s*[A-Za-z]", text))


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


def turn_skill_map(turns, calls=()):
    """Turn → the skills it worked in: its Skill calls, plus each `dt status --skill X` and skills/X/ read among
    its tool calls (`calls`: probefacts.tool_calls records), so a turn that continues a skill without a Skill
    call is still attributed to it. A turn that opened a session with `/dev-team:<skill>` (`session.new`) worked in
    that skill too."""
    out = {t["turn"]: {skill_name(s) for s in t.get("skills", [])} for t in turns}
    for t in turns:
        s = t.get("session") or {}
        if s.get("new") and s.get("skill"):
            out[t["turn"]].add(s["skill"])
    for c in calls:
        i = c.get("input") or {}
        text = " ".join(str(i.get(k) or "") for k in ("command", "file_path", "path", "pattern"))
        hit = DT_SKILL.findall(text) + SKILL_READ.findall(text)
        if hit and c.get("turn") in out:
            out[c["turn"]] |= set(hit)
    return out


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


def data_sources(texts):
    """({source: [doc, ...]} for every DATA_SOURCES name found in `texts` ({doc: text}), the fundamentals ones)."""
    found = {name: sorted(rel for rel, txt in texts.items() if re.search(pat, txt, re.I))
             for name, (pat, _) in DATA_SOURCES.items()}
    found = {name: rels for name, rels in found.items() if rels}
    return found, sorted(name for name in found if DATA_SOURCES[name][1])


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
