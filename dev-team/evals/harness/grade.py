#!/usr/bin/env python3
"""Programmatic grading of one trajectory run dir (…/<trajectory-id>/with_skill). Writes grading.json there.

Assertions are shared across incremental and all-at-once so the two modes are comparable. Everything past
the architecture is graded through `dt` (lint, status, context, roadmap --check, and dtprobe.py for parser
facts the CLI doesn't print), using the plugin snapshot the run was made with. Each check has a stable `id`.

Usage: grade.py <run-dir>   (run-dir holds project/, turns.json, summary.json; plugin/ when made by driver.py)
"""
import ast, json, re, subprocess, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dtrun, simulate  # noqa: E402

run = pathlib.Path(sys.argv[1]).resolve()
proj = run / "project"
docs = proj / "docs"
DT = dtrun.dt_path(run)
turns = json.loads((run / "turns.json").read_text()) if (run / "turns.json").exists() else []
summary = json.loads((run / "summary.json").read_text()) if (run / "summary.json").exists() else {}
scn = json.loads((HERE / "scenarios.json").read_text())
tid = run.parent.name
project = tid.split("-")[0]
mode = "incremental" if "incremental" in tid else "all_at_once"
stages = scn["projects"][project]["stages"]
PLANNING_SKILLS = ["idea-refine", "spec-writing", "architecture-design", "pipeline-design", "build-planning", "build-setup"]

R = []
def check(id_, text, passed, evidence, metrics=None):
    """One graded check. `metrics` carries the numbers behind it (modecmp.py compares them across modes)."""
    rec = {"id": id_, "text": text, "passed": bool(passed), "evidence": str(evidence)[:600]}
    if metrics is not None:
        rec["metrics"] = metrics
    R.append(rec)

def retired(id_, text, why):
    """A check id kept so comparisons with older iterations line up; it no longer counts (`na`)."""
    R.append({"id": id_, "text": text, "passed": None, "na": True, "evidence": why})

def read(p):
    p = docs / p
    return p.read_text() if p.exists() else ""

def status(txt):
    m = re.search(r"\*\*Status:\*\*\s*([A-Za-z]+)", txt)
    return m.group(1) if m else None

def git(*a):
    return subprocess.run(["git", *a], cwd=proj, capture_output=True, text=True).stdout

def dtj(*a):
    return dtrun.run_json(proj, *a, dt=DT)

brief, spec, arch = read("brief.md"), read("spec.md"), read("architecture.md")
pkg_docs = sorted([*docs.glob("architecture/*.md"), *docs.glob("packages/*/architecture.md"), *docs.glob("packages/*/contract.md")])
arch_all = arch + "\n".join(p.read_text() for p in pkg_docs)
ideas = sorted((docs / "ideas").glob("*.md")) if (docs / "ideas").is_dir() else []
later = sorted([*docs.glob("packages/*/pipelines.md"), *docs.glob("packages/*/tests.md"), *proj.glob("tasks/*.md"),
                *proj.glob("tasks/queued/*.md"), *proj.glob("CONSTRAINTS.md")])
all_docs = "\n".join([brief, spec, arch_all] + [p.read_text() for p in ideas + later])

facts = dtrun.probe(proj, DT)
st_ir, st_ad = dtj("status", "--skill", "idea-refine"), dtj("status", "--skill", "architecture-design")
st_pd, st_bp = dtj("status", "--skill", "pipeline-design"), dtj("status", "--skill", "build-planning")
lint = dtj("lint")

# ---- completion
check("finished", "Trajectory finished: simulated user reached the final stage and signed off", summary.get("finished"),
      f"turns={summary.get('turns')} stages_reached={summary.get('stages_reached')} stop={summary.get('stop_reason')}")
check("define_design_approved", "Brief, spec and architecture all end Accepted/Approved",
      status(brief) == "Accepted" and status(spec) == "Approved" and status(arch) == "Approved",
      f"brief={status(brief)} spec={status(spec)} arch={status(arch)}")
past = {rel: st for rel, st in facts["docs"].items()
        if re.match(r"(docs/packages/[^/]+/(pipelines|tests|contract)\.md|tasks/plan\.md|tasks/queued/.*|CONSTRAINTS\.md)$", rel)}
not_ok = {rel: st for rel, st in past.items() if st not in ("Approved", "In progress")}
check("plan_docs_approved", "Pipelines, test plans, build plan and CONSTRAINTS.md exist and all end Approved",
      any(r.endswith("pipelines.md") for r in past) and "tasks/plan.md" in past and "CONSTRAINTS.md" in past and not not_ok,
      f"not approved: {not_ok}; present: {sorted(past)}")

# ---- brief quality
bw = len(re.sub(r"[#*`|>-]", " ", brief).split())
check("brief_size", "Brief stays about one page (<= 500 words)", 0 < bw <= 500, f"{bw} words")
gsec = re.search(r"## Goals\n(.*?)(\n## |\Z)", brief, re.S)
goal_lines = re.findall(r"^\s*\d+\.\s*(.*)$", gsec.group(1), re.M) if gsec else []
check("brief_goal_count", "Brief has 3-5 numbered goals", 3 <= len(goal_lines) <= 5, f"goals={len(goal_lines)}")
STAGEY = re.compile(r"\b(stage|milestone|phase)\s*\d|\bM\d+\b|\b(first|second|third|next|later|final) (stage|milestone|phase)\b", re.I)
staged = [g[:80] for g in goal_lines if STAGEY.search(g)]
n_goals = st_ir.get("brief_goals", len(goal_lines))
check("brief_goals_stage_neutral", "Brief goals stay <= 5 and stage-neutral (stages live in the roadmap)",
      0 < n_goals <= 5 and not staged, f"dt brief_goals={n_goals}; stage-worded goals: {staged}")
check("brief_not_doing", "Brief has a Not doing list with items", bool(re.search(r"## Not doing\n+\s*- ", brief)), "section present" if "## Not doing" in brief else "missing")

# ---- spec quality
req_blocks = re.split(r"\n(?=\s*- \*\*[A-Z][A-Z0-9]*-\d{2,}\*\*)", spec)
reqs, no_gwt = [], []
for b in req_blocks:
    m = re.match(r"\s*- \*\*([A-Z][A-Z0-9]*-\d{2,})\*\*", b)
    if not m:
        continue
    rid = m.group(1)
    reqs.append(rid)
    first = b.split("\n")[0]
    if "~~" in first:
        continue
    body = b.split("\n- **")[0]
    if rid.startswith("QR-") and re.search(r"\n\s+- \S", body):
        continue  # template: QR items carry a "how it's checked" line instead of GWT
    if not re.search(r"\bGiven\b", body):
        no_gwt.append(rid)
check("spec_gwt", "Every live spec requirement has a Given/When/Then criterion (QR-: a how-checked line)", reqs and not no_gwt,
      f"{len(reqs)} reqs; missing GWT: {no_gwt[:15]}")
dups = sorted({r for r in reqs if reqs.count(r) > 1})
check("spec_ids_unique", "Spec requirement IDs are unique", reqs and not dups, f"duplicates: {dups}")
vendors = r"\b(yfinance|yahoo|polygon|alpaca|quandl|nasdaq data link|sharadar|tiingo|crsp|wrds|pytorch|torch|numpy|pandas|scikit|sklearn|gymnasium|gym\b|pygame|stable[- ]baselines|sb3|tensorflow|jax|lightgbm|xgboost|parquet|duckdb|sqlite|postgres)"
spec_body = re.split(r"## Changelog", spec)[0]
hits = sorted({h.lower() for h in re.findall(vendors, spec_body, re.I)})
check("spec_no_vendors", "Spec names no vendors, libraries, or storage tech", not hits, f"found: {hits}")
if project == "quant":
    check("spec_data_reqs", "Spec has DATA- requirements", bool(re.search(r"\*\*DATA-\d{2}\*\*", spec)), "")
check("spec_baselines", "Learning/model criteria name a baseline to beat", bool(re.search(r"baseline|random (agent|policy)|scripted|equal[- ]weight|beats?", spec, re.I)),
      f"{len(re.findall(r'baseline', spec, re.I))} 'baseline' mentions")

# ---- architecture (dt status --skill architecture-design)
arch_info = st_ad.get("architecture") or {}
shape = arch_info.get("shape") or ""
check("arch_covers_spec", "Architecture covers every live spec requirement (dt uncovered = 0)", arch and not st_ad.get("uncovered") and "_error" not in st_ad,
      f"uncovered: {st_ad.get('uncovered', [])[:20]} {st_ad.get('_error', '')}")
check("arch_no_stale", "Architecture references no stale/removed spec IDs", arch and not st_ad.get("stale") and "_error" not in st_ad, f"stale: {st_ad.get('stale', [])[:20]}")
ads = sorted(set(re.findall(r"### (AD-\d{2,})", arch)))
check("arch_decisions", "Architecture records technical decisions as AD-NN entries (>= 3)", len(ads) >= 3, f"{len(ads)} decisions")
check("arch_shape", "Architecture shape is recorded", bool(shape), shape)

# ---- history integrity (applies to both modes: all-at-once docs also get revised)
log = git("log", "--reverse", "--format=%H %s")
commits = [l.split(" ", 1) for l in log.strip().splitlines()]
turn_commit = {int(s.split()[1]): h for h, s in commits if re.fullmatch(r"turn \d+", s)}


def prev_turn(n):
    """The commit of the nearest earlier turn (the agent may commit too; those land between turn commits)."""
    earlier = [k for k in turn_commit if k < n]
    return turn_commit[max(earlier)] if earlier else None
ever_req, ever_ad = set(), set()
for h, _ in commits:
    tree = git("ls-tree", "-r", "--name-only", h)
    s = git("show", f"{h}:docs/spec.md") if "docs/spec.md" in tree else ""
    ever_req |= set(re.findall(r"\*\*([A-Z][A-Z0-9]*-\d{2,})\*\*", s))
    a = git("show", f"{h}:docs/architecture.md") if "docs/architecture.md" in tree else ""
    ever_ad |= set(re.findall(r"### (AD-\d{2,})", a))
lost_req = sorted(ever_req - set(re.findall(r"\*\*([A-Z][A-Z0-9]*-\d{2,})\*\*", spec)))
lost_ad = sorted(ever_ad - set(ads))
check("no_lost_reqs", "No spec requirement ID ever disappeared (removed ones struck through, not deleted)", not lost_req, f"lost: {lost_req[:20]}")
check("no_lost_decisions", "No architecture decision ever deleted (superseded instead)", not lost_ad, f"lost: {lost_ad}")
cl = len(re.findall(r"^\|\s*\d{4}-\d{2}-\d{2}", re.split(r"## Changelog", spec)[-1], re.M)) if "## Changelog" in spec else 0
check("spec_changelog", "Spec changelog exists with >= 1 row per planning round", cl >= (summary.get("stages_reached", 1) if mode == "incremental" else 1), f"{cl} rows")

# ---- planning past the architecture (design/planning-stage.md §13), graded through dt
lint_problems = lint.get("problems", [])
errs = [p for p in lint_problems if p.get("severity") == "E"]
check("dt_lint_clean", "`dt lint` is clean (no errors)", "_error" not in lint and not errs,
      lint.get("_error") or f"{len(errs)} errors, {lint.get('warnings')} warnings: " +
      "; ".join(f"{p['path']}:{p['line']} {p['code']}" for p in errs[:8]))

on_pipeline = set()
for p in facts["pipelines"]:
    on_pipeline |= set(p["covers"])
    for s in p["steps"]:
        on_pipeline |= set(s["covers"])
deferred = {i for pl in facts["plans"] for i in pl["deferred"]}
off = sorted(set(facts["live_spec"]) - on_pipeline - deferred)
check("spec_on_pipeline_or_deferred", "Every live spec ID sits on a pipeline step (or its Covers) or is Deferred in a plan",
      facts["live_spec"] and facts["pipelines"] and not off,
      f"{len(facts['live_spec'])} live, {len(facts['pipelines'])} pipelines, {len(deferred)} deferred; off: {off[:20]} "
      f"(dt pipeline-design uncovered_ids: {st_pd.get('uncovered_ids', [])[:10]}) {facts.get('_error', '')}")

plans = [p for p in facts["plans"] if p["dev_team"] and p["milestone"]]
rows = {r["id"]: r for r in facts["roadmap"]}
retired("phase0_spine", "Every pipeline of a planned milestone has a Phase 0 spine task (active and queued plans)",
        "replaced by phase0_split: the per-pipeline spine is split into one spine per step plus a wiring task")

tasks = [(p, t) for p in plans for t in p["tasks"]]
packets, unresolved = {}, []
for _, t in tasks:
    c = dtj("context", t["id"])
    if c.get("_rc") != 0 or "_error" in c:
        unresolved.append(f"{t['id']} ({c.get('_error', 'rc=%s' % c.get('_rc'))[:80]})")
    else:
        packets[t["id"]] = c.get("lines", 0)
bad_size = [f"{t['id']}={t['size']}" for _, t in tasks if t["size"] not in ("XS", "S", "M")]
# Split is allowed beside the rule for a task whose symbols the interface task declares (dtprobe's mode_ok).
bad_mode = [f"{t['id']}: {t['mode']} (rule: {t['expected_mode']})" for _, t in tasks
            if not t.get("mode_ok", t["mode"] == t["expected_mode"]) and not t["reason"]]
mode_ok_ids = {t["id"] for _, t in tasks if t.get("mode_ok")}
dt_mode = [v for v in (st_bp.get("mode_violations") or []) if str(v).split(":")[0] not in mode_ok_ids]
KINDS = ("interface", "spine", "wiring", "thicken", "system")
no_fields = [f"{t['id']} lacks {', '.join(k for k, v in t.get('declared', {}).items() if not v)}" for _, t in tasks
             if not all(t.get("declared", {"Kind": False, "Writes": False}).values())]
bad_kind = [f"{t['id']}={t.get('kind')}" for _, t in tasks if t.get("declared", {}).get("Kind") and t.get("kind") not in KINDS]
check("tasks_well_formed", "Every task: Kind and Writes declared, Read IDs resolve (`dt context` exits 0), size <= M, "
      "Mode follows the rule, split allowed for interface-declared symbols (or a Reason)",
      tasks and not unresolved and not bad_size and not bad_mode and not dt_mode and not no_fields and not bad_kind,
      f"{len(tasks)} tasks; fields: {no_fields[:4]}; kind: {bad_kind[:4]}; unresolved: {unresolved[:6]}; size: {bad_size[:6]}; "
      f"mode: {bad_mode[:6]}; dt mode_violations (not excused): {dt_mode[:4]}")
big = {k: v for k, v in packets.items() if v >= 2000}
check("context_packets_small", "`dt context` packets are under 2,000 lines", packets and not big,
      f"max {max(packets.values()) if packets else 0} lines over {len(packets)} packets; over: {big}")

# ---- interface-first planning (design/interface-first-design.md §9.1)
# Planned scope is the active milestone's plan; designed scope is every pipeline and the contract's type sections.
# Every graph fact is worked out here from parser facts (Depends on, Writes, Kind, the dependency-graph table);
# dt's own numbers (devteam.graph, `dt status`) are only a cross-check, so a dt bug can't grade itself.
SYMBOL = re.compile(r"\b[a-z][a-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")
PATHLIKE = re.compile(r"\.(py|md|json|csv|toml|ya?ml|txt|parquet|ts|tsx|js|sh|ipynb|html)$")
TYPE_TOKEN = re.compile(r"\b[A-Z][a-z][A-Za-z0-9]*\b")  # CapWords: Cov, CovReport (a lone T or OHLCV is no type)
NOT_TYPES = {"None", "Optional", "List", "Dict", "Tuple", "Any", "Union"}
SHARED_FILE = re.compile(r"(^|/)(__init__|types|pipeline)\.py$")
EDGE_KINDS = ("data", "call", "file", "code", "contract-change", "order")
# The reasons an edge may stay unmitigated: same module, an unsplittable shared file, a real side-effect order.
REASON_KINDS = {
    "same module": r"same (module|file|step|function)|thickens|extends|replaces the (stub|baseline)",
    "shared file": r"shared (file|module|entry)|unsplittable|__init__|types\.py|entry (module|file)",
    "side-effect order": r"side[- ]effect|runs? the real|real (step|code|pipeline|provider|data)|end to end|"
                         r"swaps? the fake|on disk|must exist|reads? (its|the) output",
    "contract change": r"contract[- ]change|new interface task|revis",
}


def symbols_in(text):
    return [s for s in dict.fromkeys(SYMBOL.findall(text or "")) if not PATHLIKE.search(s)]


def type_names(cell):
    return [x for x in dict.fromkeys(TYPE_TOKEN.findall(cell or "")) if x not in NOT_TYPES]


def write_overlap(a, b):
    """Two Writes entries name the same file: equal paths, or one is a directory (`dir/`, `dir/**`) holding the other."""
    da, db = re.sub(r"/(\*\*?)?$", "", a), re.sub(r"/(\*\*?)?$", "", b)
    dir_a, dir_b = da != a, db != b
    return da == db or (dir_a and db.startswith(da + "/")) or (dir_b and da.startswith(db + "/"))


def find_key(d, key):
    """The first value under `key` anywhere in a nested dt JSON answer."""
    if isinstance(d, dict):
        if key in d:
            return d[key]
        for v in d.values():
            hit = find_key(v, key)
            if hit is not None:
                return hit
    elif isinstance(d, list):
        for v in d:
            hit = find_key(v, key)
            if hit is not None:
                return hit
    return None


pl_by_id = {p["id"]: p for p in facts["pipelines"]}
type_secs = {s["id"]: s for s in facts.get("symbols", []) if s["is_type"]}
type_by_name = {}
for sid in type_secs:
    type_by_name.setdefault(sid.split(".")[-1], []).append(sid)

active = next((p for p in plans if p["kind"] == "plan"), plans[0] if plans else None)
m_tasks = active["tasks"] if active else []
by_id = {t["id"]: t for t in m_tasks}
m_row = rows.get(active["milestone"], {}) if active else {}
m_pls = [pl_by_id[i] for i in m_row.get("pipelines", []) if i in pl_by_id]


def call_step(pl, s):
    """A step that calls another pipeline (its spine is that pipeline as built): faked, never spined."""
    return any(x != pl["id"] for x in re.findall(r"PL-\d{2,}", s.get("spine", "")))


m_steps = {}  # (owner, name) → the step IDs it has in the milestone's pipelines
for pl in m_pls:
    for s_ in pl["steps"]:
        if not call_step(pl, s_):
            m_steps.setdefault((s_["owner"], s_["name"]), []).append(f"{pl['id']}.{s_['name']}")
step_info = {f"{pl['id']}.{s_['name']}": (pl, s_) for pl in facts["pipelines"] for s_ in pl["steps"]}
iface_ids = set(active.get("interface_tasks", [])) if active else set()
declared = set(active.get("interface_symbols", [])) if active else set()
declared_names = {d.split(".")[-1] for d in declared}
deps = dtrun.deps_of(m_tasks)
anc = dtrun.ancestors(m_tasks)
g_rows = active.get("graph", []) if active else []
row_of = {(r["from"], r["to"]): r for r in g_rows}
ms_id = active["milestone"] if active else "—"


def tester_early(t):
    """A split task's tester half can start right after the interface task: every symbol it reads is declared there."""
    return t["mode"] == "split" and bool(t.get("read_symbols")) and set(t["read_symbols"]) <= declared


# graph_metrics: the grader's numbers, with dt's beside them.
gm = dtrun.graph_metrics(m_tasks)
dtg = (active or {}).get("dt_graph") or {}
st_all = dtj("status")
dt_seen, disagree = {}, []
if dtg and "_error" not in dtg:
    dt_seen.update(waves=dtg.get("waves"), critical_path=len(dtg.get("critical_path") or []), width=dtg.get("width"))
for key in ("waves", "critical_path", "width", "parallelism"):
    v = find_key(st_bp, key)
    v = find_key(st_all, key) if v is None else v
    if v is not None:
        dt_seen["status_" + key] = len(v) if key == "critical_path" and isinstance(v, list) else v
mine = {"waves": [sorted(w) for w in gm["waves"]], "critical_path": gm["critical_path"], "width": gm["width"],
        "parallelism": gm["parallelism"]}
for k, v in dt_seen.items():
    base = k.replace("status_", "")
    got = [sorted(w) for w in v] if base == "waves" and isinstance(v, list) else v
    if base == "parallelism":
        if isinstance(v, (int, float)) and abs(v - mine[base]) > 0.01:
            disagree.append(f"{k} {v} vs {mine[base]}")
    elif got != mine[base]:
        disagree.append(f"{k} {got} vs {mine[base]}")
check("graph_metrics", f"{ms_id} task graph worked out by the grader (tasks, critical path plain and size-weighted, waves, "
      "width, N/CP) agrees with dt's", m_tasks and not gm["cycles"] and not disagree,
      f"N={gm['tasks']} CP={gm['critical_path']} ({' → '.join(gm['critical_path_ids'])}) CPw={gm['critical_path_weighted']} "
      f"widths={gm['widths']} N/CP={gm['parallelism']}; cycles: {gm['cycles']}; dt: {dt_seen or 'no graph numbers (dt before interface-first)'}; "
      f"disagree: {disagree}", metrics={k: v for k, v in gm.items() if not k.endswith("_ids")})

check("plan_parallelism", f"{ms_id} parallelism (tasks ÷ critical path) is at least 2.5 when it has 10 or more tasks",
      m_tasks and (gm["tasks"] < 10 or gm["parallelism"] >= 2.5),
      f"N={gm['tasks']} CP={gm['critical_path']} N/CP={gm['parallelism']}" + (" (under 10 tasks: not graded)" if gm["tasks"] < 10 else ""),
      metrics={"tasks": gm["tasks"], "critical_path": gm["critical_path"], "parallelism": gm["parallelism"], "max_width": gm["width"]})

after_iface = [t["id"] for t in m_tasks if t["id"] not in iface_ids and iface_ids and set(deps[t["id"]]) <= iface_ids]
early = [t["id"] for t in m_tasks if t["id"] not in after_iface and t["id"] not in iface_ids and tester_early(t)]
ready_n = len(after_iface) + len(early)
check("wave_width", "Right after the interface task, the ready set (spines plus split tasks' tester halves) is at least "
      "0.8 × the milestone's step count", iface_ids and m_steps and ready_n >= 0.8 * len(m_steps),
      f"interface: {sorted(iface_ids)}; ready after it: {after_iface} + tester halves {early} = {ready_n}; "
      f"steps: {len(m_steps)} ({sorted(n for _, n in m_steps)})",
      metrics={"ready_after_interface": ready_n, "steps": len(m_steps)})

conflicts = []
for i, a in enumerate(m_tasks):
    for b in m_tasks[i + 1:]:
        if a["id"] in anc[b["id"]] or b["id"] in anc[a["id"]]:
            continue
        shared = sorted({x if x == y else f"{x} ~ {y}" for x in a["writes"] for y in b["writes"] if write_overlap(x, y)})
        if shared:
            conflicts.append(f"{a['id']}/{b['id']}: {', '.join(shared)}")
entry_files = {pl["entry_file"] for pl in facts["pipelines"] if pl.get("entry_file")}
spine_bad, shared_bad = [], []
for t in m_tasks:
    if t.get("kind") not in ("interface", "wiring", "system"):
        hit = [w for w in t["writes"] if SHARED_FILE.search(w) or w in entry_files]
        if hit:
            shared_bad.append(f"{t['id']} ({t.get('kind') or 'no kind'}): {', '.join(hit)}")
    if t.get("kind") == "spine":
        owner = step_info.get(t["step"], (None, {}))[1].get("owner", "")
        src = [w for w in t["writes"] if not w.startswith("tests/")]
        tests_ = [w for w in t["writes"] if w.startswith("tests/") and not w.startswith("tests/unit/")]
        foreign = [w for w in src if owner and not re.search(rf"(^|/){re.escape(owner)}(/|\.py$)", w)]
        if len(src) > 1 or foreign or tests_ or any("*" in w for w in src):
            spine_bad.append(f"{t['id']} (owner {owner or '?'}): {', '.join(t['writes'])}")
no_writes = [t["id"] for t in m_tasks if not t["writes"]]
check("writes_disjoint", "No two tasks without a Depends-on path between them share a Writes path; a spine writes only its "
      "owner module and its unit test; shared files only by interface, wiring or system tasks",
      m_tasks and not conflicts and not spine_bad and not shared_bad and not no_writes,
      f"conflicts: {conflicts[:5]}; spines writing more: {spine_bad[:4]}; shared files: {shared_bad[:4]}; no Writes: {no_writes[:6]}",
      metrics={"conflicts": len(conflicts) + len(spine_bad) + len(shared_bad)})


def mitigation_ok(r):
    names = symbols_in(r["mitigated_by"])
    return bool(names) and all(n in declared for n in names)


dc_rows = [r for r in g_rows if r["kind"] in ("data", "call")]
dc_ok = [r for r in dc_rows if r["mitigated_by"] and mitigation_ok(r)]
mit_share = round(len(dc_ok) / len(dc_rows), 3) if dc_rows else None
check("edges_mitigated", "At least 90% of data/call edges name a mitigation the interface task produces",
      g_rows and (mit_share is None or mit_share >= 0.9),
      f"{len(dc_ok)}/{len(dc_rows)} mitigated by a declared interface; not: "
      f"{[(r['from'], r['to'], r['mitigated_by'] or 'none') for r in dc_rows if r not in dc_ok][:5]}"
      + ("" if g_rows else "; the plan has no Dependency graph table"),
      metrics={"edges_mitigated": mit_share, "data_call_edges": len(dc_rows)})

unmit = [r for r in g_rows if not r["mitigated_by"]]
unreasoned = [f"{r['from']}→{r['to']}: {r['reason'] or '(no reason)'}" for r in unmit
              if not any(re.search(p, r["reason"] or "", re.I) for p in REASON_KINDS.values())]
check("unmitigated_reasoned", "Every unmitigated (`none:`) edge gives a reason of an allowed kind "
      "(same module, unsplittable shared file, real side-effect order, contract change)",
      g_rows and not unreasoned, f"{len(unmit)} unmitigated rows; without an allowed reason: {unreasoned[:5]}")


def covered_boundary(a, b):
    """a depends on b across a boundary the interface freezes: b's step output type (or b's pipeline, called by a's
    pipeline through a declared fake) is declared, so a could have run against the sample or fake instead."""
    if b.get("kind") not in ("spine", "thicken", "wiring") or a["step"] == b["step"]:
        return False
    sa, sb = step_info.get(a["step"]), step_info.get(b["step"])
    if sa and sb and a.get("kind") in ("spine", "thicken"):
        return bool(set(type_names(sb[1]["out_type"])) & set(type_names(sa[1]["in_type"])) & declared_names)
    if a.get("kind") == "wiring" and b.get("kind") == "wiring" and a["step"] in pl_by_id:
        pa = pl_by_id[a["step"]]
        return any(call_step(pa, s_) and b["step"] in s_.get("spine", "") and s_["name"] in declared_names for s_ in pa["steps"])
    return False


to_code = []
for t in m_tasks:
    for d in deps[t["id"]]:
        if d in iface_ids:
            continue
        r = row_of.get((t["id"], d))
        if r and r["mitigated_by"]:
            to_code.append(f"{t['id']}→{d} (its row says mitigated by {r['mitigated_by']})")
        elif covered_boundary(t, by_id[d]):
            to_code.append(f"{t['id']}→{d} (across a declared boundary)")
check("no_edge_to_code_when_interface", "No Depends on points at a code task across a boundary an interface covers",
      m_tasks and not to_code, f"violations: {to_code[:6]}", metrics={"violations": len(to_code)})

missing_rows = [f"{t['id']}→{d}" for t in m_tasks for d in deps[t["id"]] if d not in iface_ids and (t["id"], d) not in row_of]
bad_rows = [f"line {r.get('line')}: {r['from'] or '?'}→{r['to'] or '?'} {r['kind']}" for r in g_rows
            if r["from"] not in by_id or r["to"] not in by_id or r["kind"] not in EDGE_KINDS]
unordered = [f"{r['from']}→{r['to']}" for r in unmit if r["from"] in by_id and r["to"] not in by_id[r["from"]]["depends_on"]]
n_deps = sum(1 for t in m_tasks for d in deps[t["id"]] if d not in iface_ids)
check("edge_table_consistent", "Every Depends on (beyond the interface task) has a dependency-graph row, every row resolves "
      "to two tasks and a known kind, and every unmitigated row is in Depends on",
      m_tasks and not missing_rows and not bad_rows and not unordered,
      f"{n_deps} Depends on, {len(g_rows)} rows; no row: {missing_rows[:5]}; unresolved: {bad_rows[:4]}; "
      f"unmitigated but not in Depends on: {unordered[:4]}",
      metrics={"rows": len(g_rows), "missing": len(missing_rows) + len(bad_rows) + len(unordered)})

split_miss = []
for pl in m_pls:
    pid = pl["id"]
    used = {x for s_ in pl["steps"] for x in type_names(s_["in_type"]) + type_names(s_["out_type"])}
    if not iface_ids:
        split_miss.append(f"{pid}: no interface task")
    elif used - declared_names:
        split_miss.append(f"{pid}: interface lacks {sorted(used - declared_names)}")
    wiring = [t for t in m_tasks if t.get("kind") == "wiring" and t["step"].split(".")[0] == pid]
    for s_ in pl["steps"]:
        if call_step(pl, s_):
            continue
        ids_ = m_steps.get((s_["owner"], s_["name"]), [f"{pid}.{s_['name']}"])
        spine = [t for t in m_tasks if t.get("kind") == "spine" and t["step"] in ids_]
        # Fold rules: a split thicken task that keeps the baseline selectable, or a trivial step done by the wiring.
        folded = [t for t in m_tasks if t.get("kind") == "thicken" and t["step"] in ids_ and t["mode"] == "split"
                  and re.search(r"baseline", " ".join(t.get("acceptance", [])), re.I)]
        folded += [t for t in wiring if re.search(rf"\b{re.escape(s_['name'])}\b", t["title"] + " " + " ".join(t.get("acceptance", [])))]
        if len(spine) != 1 and not folded:
            split_miss.append(f"{pid}.{s_['name']}: {len(spine)} spine tasks")
    entry = [t for t in wiring if any(write_overlap(w, pl.get("entry_file", "")) for w in t["writes"])
             and any(w.startswith("tests/") for w in t["writes"])]
    if len(wiring) != 1 or not entry:
        split_miss.append(f"{pid}: {len(wiring)} wiring tasks, {len(entry)} writing the entry {pl.get('entry_file')} and a smoke test")
check("phase0_split", f"Every pipeline of {ms_id}: its types declared by an interface task, one spine task per step (or a fold "
      "rule applied), one wiring task writing the entry and its smoke test",
      m_pls and not split_miss, f"pipelines {[p['id'] for p in m_pls]}; missing: {split_miss[:6]}; "
      f"dt no_spine: {st_bp.get('no_spine')}", metrics={"missing": len(split_miss)})

big_steps = [f"{t['id']} {t['kind']}={t['size']}" for t in m_tasks if t.get("kind") in ("spine", "thicken") and t["size"] not in ("XS", "S")]
n_step_tasks = sum(1 for t in m_tasks if t.get("kind") in ("spine", "thicken"))
check("step_tasks_small", "Spine and thicken tasks are XS or S", n_step_tasks and not big_steps,
      f"{n_step_tasks} spine/thicken tasks; larger: {big_steps[:6]}")

split_tasks = [t for t in m_tasks if t["mode"] == "split"]
early_all = [t["id"] for t in split_tasks if tester_early(t)]
early_share = round(len(early_all) / len(split_tasks), 3) if split_tasks else None
check("tester_starts_early", "At least 80% of split tasks read only symbols the interface task declares (their tester starts at the interface)",
      m_tasks and (early_share is None or early_share >= 0.8),
      f"{len(early_all)}/{len(split_tasks)} split tasks; late: "
      f"{[(t['id'], sorted(set(t.get('read_symbols', [])) - declared) or 'no symbol in Read') for t in split_tasks if t['id'] not in early_all][:5]}",
      metrics={"tester_early": early_share})


def fake_ok(sym, consumer_pl=None):
    """A fake is fine only where a pipeline calls another pipeline or package."""
    name = sym.split(".")[-1]
    if consumer_pl:
        pl = pl_by_id.get(consumer_pl)
        own = [s_ for s_ in (pl or {}).get("steps", []) if s_["name"] == name]
        if own:
            return all(call_step(pl, s_) for s_ in own)
    if any(call_step(pl, s_) for pl in facts["pipelines"] for s_ in pl["steps"] if s_["name"] == name):
        return True
    sec = next((s_ for s_ in facts.get("symbols", []) if s_["id"] == sym), None)
    pkg = sec["doc"].split("/")[2] if sec and sec["doc"].startswith("docs/packages/") else None
    users = re.findall(r"PL-\d{2,}", (sec or {}).get("fields", {}).get("Used by", ""))
    return bool(pkg) and any(pl_by_id.get(u, {}).get("package") not in (None, pkg) for u in users)


fakes, fake_bad = [], []
for r in g_rows:
    if re.search(r"\bfakes?\b", r["mitigated_by"], re.I):
        for sym in symbols_in(r["mitigated_by"]) or ["?"]:
            fakes.append(sym)
            consumer = by_id.get(r["from"], {}).get("step", "").split(".")[0]
            if r["kind"] != "call" or not fake_ok(sym, consumer):
                fake_bad.append(f"{r['from']}→{r['to']} {r['kind']}: {sym} fake")
for t in m_tasks:
    if t["id"] in iface_ids:
        for line in [t["title"]] + t.get("acceptance", []):
            if re.search(r"\bfakes?\b", line, re.I):
                for sym in symbols_in(line):
                    fakes.append(sym)
                    if not fake_ok(sym):
                        fake_bad.append(f"{t['id']}: {sym} fake")
check("fakes_only_cross_pipeline", "Fakes appear only where a pipeline calls another pipeline or package (within a pipeline, "
      "a type and a sample)", m_tasks and not fake_bad, f"fakes: {sorted(set(fakes))}; misplaced: {fake_bad[:5]}",
      metrics={"violations": len(fake_bad)})

plan_writes = [f"{t['id']}: {w}" for _, t in tasks for w in t["writes"] if w.startswith("tasks/") or w == "tasks"]
check("tasks_not_editing_plan", "No task's Writes is under tasks/ (only the orchestrator writes the plan)",
      tasks and not plan_writes, f"{plan_writes[:6]}")

# milestone-size: the critical path the grader worked out, per planned milestone, against the cap.
TRACK_MAX = 15
cps = {p["doc"]: dtrun.graph_metrics(p["tasks"])["critical_path"] for p in plans}
size_lint = [f"{p['path']}: {p['message'][:90]}" for p in lint_problems if p.get("code") == "milestone-size"]
check("milestone_size", f"Every planned milestone's critical path is at most {TRACK_MAX} tasks",
      plans and all(v <= TRACK_MAX for v in cps.values()), f"critical path per plan: {cps}; dt milestone-size: {size_lint[:3]}",
      metrics={"critical_path_max": max(cps.values(), default=0)})

# doc_budgets: plan.md per task (plus its graph rows), contract.md per symbol, types included.
PLAN_PER_TASK, PLAN_BASE, CONTRACT_PER_SYMBOL, CONTRACT_BASE = 12, 40, 8, 12
over = []
for p in plans:
    limit = PLAN_PER_TASK * len(p["tasks"]) + len(p.get("graph", [])) + PLAN_BASE
    if p["lines"] > limit:
        over.append(f"{p['doc']}: {p['lines']} lines, budget {limit} ({PLAN_PER_TASK}/task × {len(p['tasks'])} + {len(p.get('graph', []))} graph rows + {PLAN_BASE})")
    over += [f"{p['doc']} {t['id']}: {t['lines']} lines (budget {PLAN_PER_TASK + 3} per task)" for t in p["tasks"] if t.get("lines", 0) > PLAN_PER_TASK + 3]
by_contract = {}
for s_ in facts.get("symbols", []):
    by_contract.setdefault(s_["doc"], []).append(s_)
for rel, ss in by_contract.items():
    n_lines = len((proj / rel).read_text().splitlines()) if (proj / rel).exists() else 0
    limit = CONTRACT_PER_SYMBOL * len(ss) + CONTRACT_BASE
    if n_lines > limit:
        over.append(f"{rel}: {n_lines} lines, budget {limit} ({CONTRACT_PER_SYMBOL}/symbol × {len(ss)} + {CONTRACT_BASE})")
# dt's flat plan budget is replaced by the per-task one above; its other budget warnings still count.
budget = [p for p in lint_problems if p.get("code") == "budget" and not re.match(r"tasks/", p.get("path", ""))]
check("doc_budgets", "Doc size budgets hold: plan.md per task, contract.md per symbol (types included), the other `dt lint` "
      "budgets, brief <= 500 words", "_error" not in lint and not budget and not over and bw <= 500,
      "; ".join(over[:4] + [f"{p['path']}: {p['message']}" for p in budget[:4]]) or f"brief {bw} words")

# ---- designed scope: every step boundary and the contract's type sections
m_pl_ids = {p["id"] for p in m_pls}


def sample_of(sid):
    """The type's sample: a Sample/Fixtures field under tests/contracts/, or the folder on disk."""
    f = type_secs[sid]["fields"]
    named = [v for k, v in f.items() if k.lower() in ("sample", "samples", "fixtures") and "tests/contracts/" in v]
    return named[0] if named else (f"tests/contracts/{sid}/" if (proj / "tests" / "contracts" / sid).is_dir() else "")


cov_miss, n_bound = [], 0
for pl in facts["pipelines"]:
    for a, b in zip(pl["steps"], pl["steps"][1:]):
        if a["owner"] == b["owner"]:
            continue
        n_bound += 1
        names = type_names(a["out_type"])
        if not names:
            cov_miss.append(f"{pl['id']} {a['name']}→{b['name']}: untyped ({a['out_type'] or 'empty'})")
        for nm in names:
            secs = type_by_name.get(nm, [])
            if not secs:
                cov_miss.append(f"{pl['id']} {a['name']}→{b['name']}: {nm} has no contract type section")
            elif pl["id"] in m_pl_ids and not any(sample_of(x) for x in secs):
                cov_miss.append(f"{pl['id']} {a['name']}→{b['name']}: {nm} has no sample under tests/contracts/")
check("interface_coverage", "Every cross-owner step boundary has its type as a contract section; in the planned milestone also "
      "a sample under tests/contracts/", facts["pipelines"] and not cov_miss,
      f"{n_bound} cross-owner boundaries; missing: {cov_miss[:6]}", metrics={"boundaries": n_bound, "missing": len(cov_miss)})

named_types = {(pl["id"], s_["name"], nm) for pl in facts["pipelines"] for s_ in pl["steps"]
               for nm in type_names(s_["in_type"]) + type_names(s_["out_type"])}
unresolved_types = sorted({nm for _, _, nm in named_types if nm not in type_by_name})
check("types_in_contract", "Every type named in a step table resolves to a contract type section",
      named_types and not unresolved_types,
      f"{len({nm for _, _, nm in named_types})} types named in step tables, {len(type_secs)} type sections; unresolved: {unresolved_types[:10]}",
      metrics={"types_named": len({nm for _, _, nm in named_types}), "unresolved": len(unresolved_types)})

# A stage may become several milestones (build-planning splits a stage too big for one), so milestones map to
# stages, not by position. Incremental: a row sourced from the brief is stage 1, and an idea file belongs to the
# stage that was current when it first appeared. All-at-once rows all cite the brief: match the row's name and
# outline against each stage's keywords (scenarios.json), the name counting triple.
stage_names = [s_["name"] for s_ in stages]
idea_stage = {}
for t in turns:
    for line in t.get("status", "").splitlines():
        mm = re.match(r"(docs/ideas/[^:\s]+\.md):", line)
        if mm and mm.group(1) not in idea_stage and t.get("stage") in stage_names:
            idea_stage[mm.group(1)] = stage_names.index(t["stage"])

def row_stage(r):
    files = ["docs/" + re.sub(r"^(\.\./|\./|docs/)+", "", f) for f in re.findall(r"[\w./-]+\.md", r.get("source", ""))]
    files = [f for f in files if not f.endswith("/brief.md")]
    hits = {idea_stage[f] for f in files if f in idea_stage}
    if len(hits) == 1:
        return hits.pop()
    if mode == "incremental" and not files:
        return 0
    # A milestone cut from a roadmap stage also carries that stage's name and outline.
    name = (r.get("name", "") + " " + r.get("stage_name", "")).lower()
    outline = (r.get("outline", "") + " " + r.get("stage_outline", "")).lower()
    score = [sum(3 * name.count(k) + outline.count(k) for k in s_.get("keywords", [])) for s_ in stages]
    return max(range(len(stages)), key=lambda i: score[i]) if max(score) > 0 else None

reached = summary.get("stages_reached", len(stages)) if mode == "incremental" else len(stages)
stage_rows = {i: [r for r in facts["roadmap"] if row_stage(r) == i] for i in range(len(stages))}
unmapped = [r["id"] for r in facts["roadmap"] if row_stage(r) is None]
no_row = [stage_names[i] for i in range(reached) if not stage_rows[i]]
rc_rm, out_rm, _ = dtrun.run(proj, "roadmap", "--check", dt=DT)
check("roadmap_rows", "Every stage has at least one roadmap row and every row maps to a stage, with derived status (`dt roadmap --check` exits 0)",
      facts["roadmap"] and not no_row and not unmapped and rc_rm == 0,
      f"{ {stage_names[i]: [r['id'] for r in rs] for i, rs in stage_rows.items() if rs} }; stages with no row: {no_row}; "
      f"unmapped rows: {unmapped}; derived: {[(r['id'], r['derived']) for r in facts['roadmap']]}; roadmap --check rc={rc_rm} {out_rm.strip()[:120]}")
# Both modes end at the same bar, so their final roadmaps compare like for like: the first milestone has a
# build plan, and every later one is at least Designed (task plans are written for the next milestone only).
first = facts["roadmap"][0] if facts["roadmap"] else {}
rest = [r["id"] for r in facts["roadmap"][1:] if r["derived"] in ("Idea", "Specced")]
check("first_planned_rest_designed", "The first milestone has a build plan and every later milestone is at least Designed",
      first.get("derived") in ("Planned", "Building") and not rest, f"{first.get('id')}={first.get('derived')}; below Designed: {rest}")

# Depends drives build order: every milestone after the first names what it builds on, by an existing ID, acyclically.
ids = [r["id"] for r in facts["roadmap"]]
deps = {r["id"]: r.get("depends", []) for r in facts["roadmap"]}
no_dep = [i for i in ids[1:] if not deps[i]]
unknown = {i: [d for d in deps[i] if d not in ids] for i in ids if any(d not in ids for d in deps[i])}
def cyclic(i, seen=()):
    return i in seen or any(cyclic(d, seen + (i,)) for d in deps.get(i, []) if d in deps)
cycles = [i for i in ids if cyclic(i)]
check("milestone_depends", "Every milestone after the first has a Depends line naming existing milestones, with no cycles",
      ids and not no_dep and not unknown and not cycles,
      f"depends: {deps}; missing: {no_dep}; unknown: {unknown}; in a cycle: {cycles}")

# Shape per turn, from the architecture header at each turn's commit.
shapes = []
for n in sorted(turn_commit):
    a = git("show", f"{turn_commit[n]}:docs/architecture.md")
    m = re.search(r"\*\*Shape:\*\*\s*([^·\n]+)", a)
    shapes.append((n, m.group(1).strip() if m else None))
if project == "quant":
    # The data stage's TypeScript frontend is a runtime boundary, so the first architecture is already multi-package.
    stage_of = {t["turn"]: t["stage"] for t in turns}
    single = [(n, stage_of.get(n)) for n, s in shapes if s and re.search(r"single", s, re.I)]
    final_multi = bool(shape) and not re.search(r"single", shape, re.I) and len(facts["packages"]) >= 2
    check("quant_multi_from_data", "quant: architecture is multi-package from the data stage (the viz frontend is a separate runtime)",
          final_multi and not single, f"single-package turns (turn, stage): {single}; final shape {shape!r}, packages {facts['packages']}")


def is_code(text):
    """Anything beyond blank lines, comments and a module docstring."""
    try:
        body = ast.parse(text).body
    except SyntaxError:
        return bool(text.strip())
    return any(not (isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant)) for n in body)


# Types, signatures, schemas and fakes are written by the build's interface task, never by planning; samples
# (data files) under tests/contracts/ are planning output like golden fixtures.
CODE_DIRS = re.compile(r"^(src/|tests/intent/|tests/unit/)|(^|/)types\.py$|^tests/contracts/.+\.(py|pyi|ts|tsx|js)$")
code_files = []
for n in sorted(turn_commit):
    if n == 0:
        continue
    prev = prev_turn(n)
    names = git("diff", "--name-status", prev, turn_commit[n]) if prev else git("show", "--name-status", "--format=", turn_commit[n])
    for line in names.splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or parts[0].startswith("D") or not CODE_DIRS.search(parts[-1]):
            continue
        if is_code(git("show", f"{turn_commit[n]}:{parts[-1]}")):
            code_files.append((n, parts[-1]))
untracked = [l[3:] for l in git("status", "--porcelain").splitlines() if CODE_DIRS.search(l[3:])]
check("no_code_during_planning", "No source code written during planning (nothing under src/, tests/intent/, tests/unit/, "
      "no code under tests/contracts/, no types.py, beyond empty or docstring-only files)",
      turn_commit and not code_files and not untracked, f"code: {code_files[:10]}; uncommitted: {untracked[:5]}")

# frozen_interface_churn: how often a type section or contract folder the first milestone froze is revised later,
# over the turn commits. Informational here; modecmp.py compares it across modes (expect all-at-once <= incremental).
HEAD_RE = re.compile(r"^(#{1,3}) (.*)$", re.M)


def type_sections(sha):
    out = {}
    for rel in git("ls-tree", "-r", "--name-only", sha).splitlines():
        if not (rel.startswith("docs/") and rel.endswith("/contract.md")):
            continue
        text = git("show", f"{sha}:{rel}")
        heads = list(HEAD_RE.finditer(text))
        for i, h in enumerate(heads):
            m = re.match(r"([a-z][\w-]*(?:\.\w+)+):\s*(.*)$", h.group(2))
            if len(h.group(1)) != 3 or not m or not (m.group(2).lower().startswith("type") or m.group(1).split(".")[-1][:1].isupper()):
                continue
            end = next((x.start() for x in heads[i + 1:] if len(x.group(1)) <= 3), len(text))
            out[m.group(1)] = "\n".join(l for l in text[h.start():end].splitlines() if "**Used by:**" not in l).strip()
    return out


def contract_blobs(sha):
    return {l.split("\t")[1]: l.split()[2] for l in git("ls-tree", "-r", sha, "--", "tests/contracts").splitlines() if "\t" in l}


types_at = {n: type_sections(turn_commit[n]) for n in sorted(turn_commit)}
freeze = next((n for n in sorted(turn_commit)
               if re.search(r"\*\*Status:\*\*\s*(Approved|In progress)", git("show", f"{turn_commit[n]}:tasks/plan.md"))), None)
churn = []
if freeze is not None:
    frozen_types = set(types_at[freeze])
    blobs0 = contract_blobs(turn_commit[freeze])
    frozen_dirs = {"/".join(k.split("/")[:3]) for k in blobs0}
    prev_t, prev_b = types_at[freeze], blobs0
    for n in [k for k in sorted(turn_commit) if k > freeze]:
        cur_t = types_at[n]
        cur_b = {k: v for k, v in contract_blobs(turn_commit[n]).items() if "/".join(k.split("/")[:3]) in frozen_dirs}
        churn += [(n, sid, "removed" if sid not in cur_t else "revised") for sid in sorted(frozen_types) if cur_t.get(sid) != prev_t.get(sid)]
        churn += [(n, k, "changed") for k in sorted(set(prev_b) | set(cur_b)) if prev_b.get(k) != cur_b.get(k)]
        prev_t, prev_b = cur_t, cur_b
check("frozen_interface_churn", "Reported: revisions to a type section or tests/contracts/ folder after the first plan froze them",
      True, (f"frozen at turn {freeze}: {len(types_at[freeze])} type sections, {len(contract_blobs(turn_commit[freeze]))} contract files; "
             f"{len(churn)} revisions: {churn[:8]}") if freeze is not None else "no plan was approved, nothing frozen",
      metrics={"churn": len(churn), "frozen_turn": freeze})

# ---- gates: one layer per turn; approvals only after the user approves
def layer(path):
    if path.endswith("brief.md") or "/ideas/" in path:
        return "brief"
    if path == "docs/spec.md":
        return "spec"
    if path == "docs/references.md":
        return "references"
    if path.endswith("/pipelines.md"):
        return "pipelines"
    if path.endswith("/tests.md") or path.startswith("tests/fixtures/"):
        return "tests"
    if path.startswith("tasks/"):
        return "plan"
    if "architecture" in path or path.endswith("/contract.md"):
        return "arch"
    if path in ("CONSTRAINTS.md", "pyproject.toml") or path.startswith(("scripts/", ".claude/agents/", ".github/")):
        return "setup"
    return None

def layers_changed(n):
    prev = prev_turn(n)
    if not prev:
        return set()
    added = {}
    for line in git("diff", "--numstat", prev, turn_commit[n]).splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or not parts[0].isdigit():
            continue
        path = parts[2].split(" => ")[-1].rstrip("}")
        k = layer(path)
        n_added = int(parts[0])
        if path.endswith("/contract.md"):
            # pipeline-design may append PL IDs to `Used by:` lines without touching the contract layer
            diff = git("diff", "-U0", prev, turn_commit[n], "--", path)
            n_added = sum(1 for l in diff.splitlines()
                          if l.startswith("+") and not l.startswith("+++") and "**Used by:**" not in l)
        if k:
            added[k] = added.get(k, 0) + n_added
    return {k for k, v in added.items() if v >= 12}  # status flips and small fixes don't count

multi = [(n, sorted(ks)) for n in sorted(turn_commit) if n and len(ks := layers_changed(n)) > 1]
# Watched, not graded: pipeline-design finding missing types and adding them to the contract in its own turn.
pd_turns = {t["turn"] for t in turns if "pipeline-design" in [dtrun.skill_name(x) for x in t["skills"]]}
pd_types = [(n, sorted(set(types_at[n]) - set(types_at.get(max([k for k in types_at if k < n], default=n), {}))))
            for n in sorted(pd_turns & set(types_at))]
pd_types = [(n, ts) for n, ts in pd_types if ts]
check("gate_discipline", "Every skill stops at its gate: no turn drafts two layers (brief/idea, references, spec, architecture, pipelines, tests, plan, setup) at once",
      turn_commit and not multi, f"turns: {multi[:10]}; types added in pipeline-design turns: {pd_types[:5]}")

APPROVE = re.compile(r"\b(accept|accepted|approve|approved|looks good|lgtm|go ahead|yes)\b", re.I)
bad, prev = [], {}
for t in turns:
    cur = dict(l.split(": ", 1) for l in t["status"].splitlines() if ": " in l)
    for f, v in cur.items():
        s_now, s_prev = v.split(" (")[0], prev.get(f, "").split(" (")[0]
        if s_now in ("Accepted", "Approved") and s_prev not in ("Accepted", "Approved", "Specced") and not APPROVE.search(t["user"]):
            bad.append((t["turn"], f))
    prev = cur
check("approval_after_user", "Docs only flip to Accepted/Approved in a turn where the user approved", not bad, f"violations: {bad[:10]}")
skills_used = sorted({dtrun.skill_name(s) for t in turns for s in t["skills"]})
missing = [s for s in PLANNING_SKILLS if s not in skills_used]
check("skills_invoked", "All six required planning skills were invoked (idea → build-setup)", not missing, f"used: {skills_used}; missing: {missing}")
check("test_planning_invoked", "test-planning ran (optional skill; the persona asks for golden cases)", "test-planning" in skills_used, f"used: {skills_used}")

# ---- Replan and Advance simulation on a copy of the final project (no model calls)
sim_n = {}
for r in simulate.simulate(proj, DT):
    kind = next((k.lower().split("-")[0] for k in ("Replan", "Advance", "Ready", "Contract-change") if r["text"].startswith(k)), "setup")
    sim_n[kind] = sim_n.get(kind, 0) + 1
    check(f"sim_{kind}_{sim_n[kind]}", r["text"], r["passed"], r["evidence"])

# ---- project-specific
if project == "quant":
    check("nh_named", "Plan hands feature testing to the null-hypothesis-testing skill by name", "null-hypothesis-testing" in all_docs,
          f"mentions: {all_docs.count('null-hypothesis-testing')}")
    near = re.search(r"null-hypothesis-testing.{0,400}(feature|information gain|signal)|(feature|information gain|signal).{0,400}null-hypothesis-testing", all_docs, re.S | re.I)
    check("nh_at_features", "null-hypothesis-testing is named at the features / information-gain step", bool(near), near.group(0)[:200] if near else "")
    routed = [t["id"] for _, t in tasks if "null-hypothesis-testing" in json.dumps(t)]
    tests_md = "\n".join(p.read_text() for p in docs.glob("packages/*/tests.md"))
    check("nh_routed_in_plan", "null-hypothesis-testing is routed on a test case or task (Skills field), not just mentioned",
          bool(re.search(r"\*\*Skills:\*\*[^\n]*null-hypothesis-testing", tests_md + "\n".join(p.read_text() for p in later))),
          f"tests.md mentions: {tests_md.count('null-hypothesis-testing')}")
    check("spec_bias_guards", "Spec guards look-ahead and survivorship bias as testable requirements",
          bool(re.search(r"look[- ]ahead|published after|known (on|as of)|point[- ]in[- ]time", spec, re.I)) and bool(re.search(r"delist|survivorship", spec, re.I)), "")
    check("spec_pca_mp", "Spec covers PCA market-mode removal and Marchenko–Pastur denoising",
          bool(re.search(r"\bPCA\b|principal component|eigenvector|top factors|market (factor|mode)", spec, re.I)) and bool(re.search(r"Marchenko|random[- ]matrix|noise band|pure noise", spec, re.I)), "")
    check("spec_classical", "Classical portfolios (min-variance / risk parity / HRP) are specified",
          bool(re.search(r"min(imum)?[- ]variance", spec, re.I)) and bool(re.search(r"risk parity", spec, re.I)), "")
    m = re.search(r"(PPO|agent|forecast[- ]driven|ML[- ]driven).{0,600}(min(imum)?[- ]variance|classical|HRP|risk parity)", spec, re.S | re.I)
    check("spec_ml_beats_classical", "ML/PPO portfolios must beat the classical portfolios out of sample", bool(m), m.group(0)[:200] if m else "")
    # Whole spec Out-of-scope list and brief Not-doing section; a fixed-size window missed items deep in a long list.
    excluded = "".join(m.group(0) for t, start in ((spec, r"\*\*Out of scope"), (brief, r"^## Not doing"))
                       for m in [re.search(start + r".*?(?=^## |\Z)", t, re.S | re.M)] if m)
    check("no_live_trading", "Real-money / live trading is explicitly out of scope", bool(re.search(r"live|real[- ]money|brokerage", excluded, re.I)), "")
    check("spec_oos", "Out-of-sample / held-out evaluation is required for features and models",
          len(re.findall(r"out[- ]of[- ]sample|held[- ]out|walk[- ]forward", spec, re.I)) >= 3, f"{len(re.findall(r'out[- ]of[- ]sample|held[- ]out|walk[- ]forward', spec, re.I))} mentions")
    viz = {k: bool(re.search(pat, arch_all, re.I)) for k, pat in
           [("typescript", r"TypeScript"), ("react", r"\bReact\b"), ("websocket", r"WebSocket"), ("json_schema", r"JSON Schema")]}
    check("arch_viz_boundary", "Architecture puts the viz app's TypeScript + React frontend across a WebSocket/HTTP boundary from the Python backend, "
          "with a JSON Schema contract", all(viz.values()), f"{viz}")
else:
    for env, pat in [("snake", r"snake"), ("fish", r"fish|tank|ball"), ("foraging", r"forag|predator|prey")]:
        check(f"spec_{env}", f"Spec covers the {env} environment", bool(re.search(pat, spec, re.I)), "")
    check("arch_shared_core", "Architecture has a shared core reused by all environments", bool(re.search(r"(shared|common|core)", arch_all, re.I)) and bool(re.search(r"interface|protocol|abc|class", arch_all, re.I)), "")
    check("spec_env_baselines", "Each environment's learning criterion beats a random or scripted baseline",
          len(re.findall(r"random|scripted|heuristic", spec, re.I)) >= 3, f"{len(re.findall(r'random|scripted|heuristic', spec, re.I))} mentions")
    check("spec_cpu_budget", "CPU training-time budget (~1 hour) is a quality requirement", bool(re.search(r"(hour|60 min|minutes).{0,120}(CPU|laptop|MacBook|processor)|(CPU|laptop|MacBook|processor).{0,120}(hour|60 min|minutes)", spec, re.I)), "")
    check("rl_single_package", "Proof-of-concept stays single package (no premature monorepo)", "single" in shape.lower(), shape)

# ---- references and stage-level skill routing (design/references.md §10), for projects that have reference files
ref_stage = {f: i for i, s in enumerate(stages) for f in scn["projects"][project].get("references", {}).get(s["name"], [])}
if ref_stage:
    reached = summary.get("stages_reached", len(stages)) if mode == "incremental" else len(stages)
    expected = summary.get("references", [f for f, i in ref_stage.items() if i < reached])
    ref_dir = proj / "references"
    present = sorted(str(p.relative_to(ref_dir)) for p in ref_dir.rglob("*") if p.is_file()) if ref_dir.is_dir() else []
    entries = facts.get("references", [])
    by_file = {pathlib.PurePath(e["file"]).name: e for e in entries if e.get("file")}
    waiting = {k: st_ir.get(k) for k in ("references_unindexed", "references_changed", "references_missing")}
    idx_status = facts["docs"].get("docs/references.md")
    unindexed = [f for f in present if pathlib.PurePath(f).name not in by_file]
    check("refs_indexed_approved", "Every reference file is indexed (an RF entry, hash current) and docs/references.md is Approved",
          present and set(expected) <= {pathlib.PurePath(f).name for f in present} and not unindexed
          and all(v == [] for v in waiting.values()) and idx_status == "Approved",
          f"files {present} (expected {expected}); no entry: {unindexed}; dt {waiting}; index {idx_status}")

    rows_ = facts["roadmap"]
    def want_ms(f):  # the stage's roadmap stage or milestones; empty while it has neither: `—`
        i = ref_stage[f]
        return [r["id"] for r in stage_rows[i]] + [s_["id"] for s_ in facts.get("stages", []) if row_stage(s_) == i]
    def ms_ok(f):  # later milestones that reuse it (PCA residuals in the features stage) may list it too
        got, want = by_file[f]["milestones"], want_ms(f)
        return bool(set(got) & set(want)) if want else not got
    graded = [f for f in expected if f in ref_stage]
    wrong = {f: (by_file[f]["milestones"] if f in by_file else "no entry", want_ms(f)) for f in graded
             if f not in by_file or not ms_ok(f)}
    check("refs_milestones", "Each reference is assigned to the stage it serves, or one of its milestones (`—` while that stage has no roadmap row)",
          graded and not wrong, f"{ {f: by_file.get(f, {}).get('milestones') for f in graded} }; wrong (got, want): {wrong}")

    def open_questions(rel):
        t = (proj / rel).read_text() if (proj / rel).exists() else ""
        m = re.search(r"^#+ Open questions.*?(?=^#+ |\Z)", t, re.S | re.M | re.I)
        return m.group(0) if m else ""
    unrouted = {}
    for ms in [r for r in rows_ if any(p["milestone"] == r["id"] for p in plans)]:
        ms_plans = [p for p in plans if p["milestone"] == ms["id"]]
        reads = {re.sub(r":.*$", "", i) for p in ms_plans for t in p["tasks"] for i in t["read"]}
        task_skills = {s_ for p in ms_plans for t in p["tasks"] for s_ in t.get("skills", [])}
        refs_ms = (ms["references"] if "references" in ms
                   else [e["id"] for e in entries if ms["id"] in e["milestones"] or "all" in e["milestones"]])
        reasons = "\n".join(open_questions(p["doc"]) for p in ms_plans)
        miss = [r for r in refs_ms if r not in reads] + [s_ for s_ in ms.get("skills", []) if s_ not in task_skills]
        miss = [m for m in miss if m not in reasons]  # an item may stay unrouted with a reason under Open questions
        if miss:
            unrouted[ms["id"]] = miss
    # dt lists items as `RF-01 (M2)` / `data-analysis (M2)` across the active and queued plans; reasoned ones are excused.
    all_reasons = "\n".join(open_questions(p["doc"]) for p in plans)
    dt_unrouted = {k: st_bp.get(k) for k in ("references_unrouted", "skills_unrouted")}
    dt_open = [i for v in dt_unrouted.values() for i in (v if isinstance(v, list) else [v]) if i.split(" (")[0] not in all_reasons]
    check("refs_skills_routed", "Every planned milestone routes its references (a task's Read:) and skills (a task's Skills:), "
          "or gives a reason under Open questions; dt references_unrouted and skills_unrouted likewise",
          plans and not unrouted and not dt_open and all(isinstance(v, list) for v in dt_unrouted.values()),
          f"unrouted by milestone: {unrouted}; dt build-planning: {dt_unrouted}")

    # Across the stage's milestones: their **Skills:** lines name each skill, and a planned milestone whose line
    # names one puts it on a task. Only the first milestone gets a plan, so the rest are graded on the lines alone.
    def stage_skills(cid, stage, want_sk, text):
        sms = stage_rows[stage_names.index(stage)]
        if sms:
            line_sk = {k for ms in sms for k in ms.get("skills", [])}
            on_task = {k: [t["id"] for ms in sms if k in ms.get("skills", []) for p in plans if p["milestone"] == ms["id"]
                           for t in p["tasks"] if k in t.get("skills", [])]
                       for k in want_sk}
            planned = {k: [ms["id"] for ms in sms if k in ms.get("skills", []) and any(p["milestone"] == ms["id"] for p in plans)]
                       for k in want_sk}
            ok = all(k in line_sk for k in want_sk) and all(on_task[k] or not planned[k] for k in want_sk)
            ev = f"{[ms['id'] for ms in sms]} **Skills:** {sorted(line_sk)}; planned milestones naming each: {planned}; tasks carrying each: {on_task}"
        else:
            ok, ev = False, f"no {stage} milestone"
        check(cid, text, ok, ev)

    stage_skills("skills_on_data_tasks", "data", ["frontend-design"],
                 "The data milestones route frontend-design for the viz app (their roadmap **Skills:** lines, and a task of the planned milestone that names it)")
    stage_skills("skills_on_structure_tasks", "structure_portfolios", ["data-analysis", "null-hypothesis-testing"],
                 "The structure & classical-portfolios milestones route data-analysis and null-hypothesis-testing "
                 "(their roadmap **Skills:** lines, and a task of each planned milestone that names one)")

    intake = [t for t in turns if "reference-intake" in [dtrun.skill_name(x) for x in t["skills"]]]
    check("reference_intake_invoked", "reference-intake ran", bool(intake), f"turns: {[t['turn'] for t in intake]}")
    names = sorted({pathlib.PurePath(f).name for f in present})
    launches = [a for t in intake for a in t.get("agents", [])]
    def named(a):
        hit = [n for n in names if n in (a.get("description") or "")]
        return hit or [n for n in names if n in (a.get("prompt") or "")]
    per = {n: sum(1 for a in launches if named(a) == [n]) for n in names}
    batched = [a.get("description") for a in launches if len(named(a)) > 1]
    check("intake_subagent_per_file", "reference-intake sent one subagent per reference file (Agent calls in its turns, each naming one file)",
          names and launches and all(per.values()) and not batched,
          f"{len(launches)} Agent calls in intake turns {[t['turn'] for t in intake]}; per file: {per}; batched: {batched}")

    IMPORT_REF = re.compile(r"^\s*(from\s+references\b|import\s+references\b)|sys\.path.*references", re.M)
    imports = [str(p.relative_to(proj)) for d in ("src", "tests") for p in (proj / d).rglob("*.py")
               if IMPORT_REF.search(p.read_text(errors="ignore"))]
    check("no_reference_imports", "Nothing under src/ or tests/ imports from references/ or puts it on sys.path (CR-08)",
          not imports, f"importing: {imports[:10]}")

graded = [r for r in R if not r.get("na")]
passed = sum(r["passed"] for r in graded)
tools = {}
for t in turns:
    for x in t["tools"]:
        tools[x] = tools.get(x, 0) + 1
perm_log = run / "permission_prompts.jsonl"
oracle_prompts = [json.loads(l).get("path") for l in perm_log.read_text().splitlines() if l.strip()] if perm_log.exists() else []
guard_hits = [e for t in turns for e in t.get("tool_errors", []) if re.search(r"oracle|expected\.json|archive", e, re.I)]
out = {"expectations": R,
       "summary": {"passed": passed, "failed": len(graded) - passed, "total": len(graded), "pass_rate": round(passed / len(graded), 3),
                   "not_applicable": [r["id"] for r in R if r.get("na")]},
       "execution_metrics": {"tool_calls": tools, "total_tool_calls": sum(tools.values()), "total_steps": len(turns),
                             "errors_encountered": sum(1 for t in turns if t["assistant"].startswith("[agent error")),
                             "output_chars": len(all_docs)},
       "timing": {"executor_duration_seconds": summary.get("total_seconds"), "total_duration_seconds": summary.get("total_seconds")},
       "extra": {"turns": len(turns), "cost_usd": round(max([(t["usage"].get("cost_usd") or 0) for t in turns] or [0]), 2),
                 "output_tokens": sum(((t["usage"].get("usage") or {}).get("output_tokens") or 0) for t in turns),
                 "agent_seconds": round(sum(t["seconds"] for t in turns)),
                 "final_words": {k: len(v.split()) for k, v in [("brief", brief), ("spec", spec), ("architecture", arch_all)]}, "skills_used": skills_used,
                 "skill_sequence": [s for t in turns for s in t["skills"]],
                 "ideas": [p.name for p in ideas], "package_docs": [str(p.relative_to(docs)) for p in pkg_docs],
                 "spec_reqs": len(reqs), "decisions": len(ads), "brief_words": bw,
                 "shape_by_turn": shapes, "packages": facts["packages"], "pipelines": len(facts["pipelines"]),
                 "plans": {p["doc"]: {"milestone": p["milestone"], "tasks": len(p["tasks"]), "lines": p["lines"]} for p in plans},
                 "graph": {k: v for k, v in gm.items()}, "frozen_interface_churn": churn[:40],
                 "context_lines_max": max(packets.values()) if packets else 0,
                 "lint": {"errors": lint.get("errors"), "warnings": lint.get("warnings")},
                 "roadmap": [(r["id"], r["derived"]) for r in facts["roadmap"]],
                 "references": [(e["id"], e["file"], e["milestones"]) for e in facts.get("references", [])],
                 "milestone_skills": {r["id"]: r.get("skills", []) for r in facts["roadmap"]},
                 "hook_events": sum(t.get("hook_events", 0) for t in turns),
                 "guard_tool_errors": guard_hits[:10], "oracle_prompts_approved": oracle_prompts[:20],
                 "session_init": (turns[0].get("session_init") if turns else None), "dt": str(DT)}}
(run / "grading.json").write_text(json.dumps(out, indent=1))
print(f"{tid}: {passed}/{len(graded)}")
for r in R:
    print(("N/A  " if r.get("na") else "PASS " if r["passed"] else "FAIL ") + f"[{r['id']}] " + r["text"] + "  — " + r["evidence"][:160])
