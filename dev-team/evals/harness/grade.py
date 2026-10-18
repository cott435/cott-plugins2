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
import dtrun, fakevendor, probefacts as pf, probegrade, simulate  # noqa: E402

run = pathlib.Path(sys.argv[1]).resolve()
proj = run / "project"
docs = proj / "docs"
DT = dtrun.dt_path(run)
turns = json.loads((run / "turns.json").read_text()) if (run / "turns.json").exists() else []
summary = json.loads((run / "summary.json").read_text()) if (run / "summary.json").exists() else {}
scn = json.loads((HERE / "scenarios.json").read_text())
# The scenario as the run saw it (driver.py writes scenario.json when the run starts); older runs recorded none. A
# check of something the user only says in a later scenario reads n/a on a run whose snapshot doesn't say it.
run_scn = json.loads((run / "scenario.json").read_text()) if (run / "scenario.json").exists() else {}
run_facts = "\n".join(run_scn.get("facts", []))
tid = run.parent.name
project = tid.split("-")[0]
mode = "incremental" if "incremental" in tid else "all_at_once"
stages = scn["projects"][project]["stages"]
PLANNING_SKILLS = ["idea-refine", "spec-writing", "architecture-design", "pipeline-design", "build-planning", "build-setup"]

R = []
def check(id_, text, passed, evidence, metrics=None, items=None):
    """One graded check. `metrics` carries the numbers behind it (modecmp.py compares them across modes); `items`, the
    full lists the evidence cuts short, go into `metrics["items"]` (adjudicate.py pins every item there)."""
    rec = {"id": id_, "text": text, "passed": bool(passed), "evidence": str(evidence)[:600]}
    if items:
        metrics = {**(metrics or {}), "items": {k: list(v) for k, v in items.items()}}
    if metrics is not None:
        rec["metrics"] = metrics
    R.append(rec)

def retired(id_, text, why):
    """A check id kept so comparisons with older iterations line up; it no longer counts (`na`)."""
    R.append({"id": id_, "text": text, "passed": None, "na": True, "evidence": why})

def graded_or_na(id_, text, result):
    """A check that may not apply: `result` is (passed, evidence), or (None, why) for n/a."""
    passed, evidence = result
    if passed is None:
        R.append({"id": id_, "text": text, "passed": None, "na": True, "evidence": str(evidence)[:600]})
    else:
        check(id_, text, passed, evidence)

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

facts = dtrun.probe(proj, DT, requests_history=True)
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
# A vendor the persona already uses (quant: its Sharadar subscription, yahooquery) is the user's constraint, not a choice.
persona_named = {h.lower() for h in re.findall(vendors, " ".join(scn["projects"][project].get("facts", [])), re.I)}
hits = sorted({h.lower() for h in re.findall(vendors, spec_body, re.I)} - persona_named)
check("spec_no_vendors", "Spec names no vendors, libraries, or storage tech beyond those the user already uses", not hits,
      f"found: {hits}; the user's own: {sorted(persona_named)}")
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

# ---- the user's words (design/requests.md): docs/requests.md, read through the run's own dt parser (dtprobe). Each
# check is n/a for a dt that keeps no record, so older runs grade as before.
RQ = facts.get("requests")
NO_RECORD = "the run's dt keeps no record of the user's words (no devteam.requests)"
T_CAPTURED = ("Every checkable scenario fact the simulated user stated (scenarios.json stated_facts, matched in its "
              "messages) appears in some UR line's words in the final docs/requests.md")
stated_facts = scn["projects"][project].get("stated_facts", [])
stated = dtrun.facts_stated(stated_facts, turns)
if RQ is None:
    graded_or_na("requests_captured", T_CAPTURED, (None, NO_RECORD))
elif not stated:
    graded_or_na("requests_captured", T_CAPTURED, (None, "the simulated user stated none of the scenario's checkable facts"))
else:
    missed = dtrun.requests_missed(stated_facts, stated, [r["words"] for r in RQ["requests"]])
    check("requests_captured", T_CAPTURED, RQ["present"] and not missed,
          f"{len(RQ['requests'])} UR lines{'' if RQ['present'] else ' (no docs/requests.md)'}; stated (fact: turns) "
          f"{stated}; missed: {missed}", metrics={"stated": len(stated), "missed": len(missed)},
          items={"missed": [f"{f} (said in turns {stated[f]})" for f in missed]})

T_HONOURED = "`dt lint` has no request-open, request-trace or request-format error at the end of the run"
REQUEST_LINT = ("request-open", "request-trace", "request-format")
if RQ is None or not RQ["present"]:
    graded_or_na("requests_honoured", T_HONOURED, (None, NO_RECORD if RQ is None else
                 "no docs/requests.md, so nothing to honour (requests_captured grades whether the run needed one)"))
else:
    rq_errs = [f"{p['path']}:{p['line']} {p['code']}: {p['message'][:120]}" for p in errs if p.get("code") in REQUEST_LINT]
    open_ = [f"{r['id']} {r['owner']}" for r in RQ["requests"] if r["open"]]
    check("requests_honoured", T_HONOURED, "_error" not in lint and not rq_errs,
          lint.get("_error") or f"{len(RQ['requests'])} UR lines, {len(open_)} open by dt (only spec and architecture "
          f"ones fail lint, once Approved): {open_[:8]}; errors: {rq_errs[:4]}",
          metrics={"requests": len(RQ["requests"]), "open": len(open_), "errors": len(rq_errs)},
          items={"errors": rq_errs, "open": open_})

T_APPEND = "Across the per-turn commits, no UR line's words changed and no line vanished from docs/requests.md"
rq_hist = facts.get("requests_history") or []
if RQ is None or not any(h["present"] for h in rq_hist):
    graded_or_na("requests_append_only", T_APPEND, (None, NO_RECORD if RQ is None else "docs/requests.md was never committed"))
else:
    order = {h: i for i, (h, _) in enumerate(commits)}
    at = sorted((order[h["sha"]], h) for h in rq_hist if h["sha"] in order)
    states = []
    for n in sorted(turn_commit):  # the record at each turn: the last commit touching it up to that turn's commit
        h = next((h for i, h in reversed(at) if i <= order.get(turn_commit[n], -1)), None)
        states.append((n, h["words"] if h and h["present"] else None, h["bad"] if h else []))
    rewritten = dtrun.requests_rewritten(states)
    check("requests_append_only", T_APPEND, not rewritten,
          f"{sum(1 for _, w, _ in states if w is not None)} turns with a record, {len(states[-1][1] or {})} lines at the "
          f"last; rewritten: {rewritten[:5]}", metrics={"rewritten": len(rewritten)}, items={"rewritten": rewritten})

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
      f"mode: {bad_mode[:6]}; dt mode_violations (not excused): {dt_mode[:4]}",
      items={"fields": no_fields, "kind": bad_kind, "unresolved": unresolved, "size": bad_size, "mode": bad_mode,
             "dt_mode_violations": dt_mode})
big = {k: v for k, v in packets.items() if v >= 2000}
check("context_packets_small", "`dt context` packets are under 2,000 lines", packets and not big,
      f"max {max(packets.values()) if packets else 0} lines over {len(packets)} packets; over: {big}")

# ---- interface-first planning (design/interface-first-design.md §9.1)
# Planned scope is the active milestone's plan; designed scope is every pipeline and the contract's type sections.
# Every graph fact is worked out here from parser facts (Depends on, Writes, Kind, the dependency-graph table);
# dt's own numbers (devteam.graph, `dt status`) are only a cross-check, so a dt bug can't grade itself.
SYMBOL = re.compile(r"\b[a-z][a-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+(?:\*|\b)")
# The scenario fact that leaves the fundamentals source to the agent (data_sources_suggested).
SOURCE_QUESTION = re.compile(r"\bfundamentals\b[^.]*\b(suggest|haven't picked|pick a source)", re.I)
PATHLIKE = re.compile(r"\.(py|md|json|csv|toml|ya?ml|txt|parquet|ts|tsx|js|sh|ipynb|html)$")
# The structural rules live in dtrun.py, where selftest/checks.py runs each one good and bad.
type_names, write_overlap = dtrun.type_names, dtrun.write_overlap
PKGS = tuple(facts["packages"] or ())
SHARED_FILE = re.compile(r"(^|/)(__init__|types|pipeline)\.py$")
EDGE_KINDS = ("data", "call", "file", "code", "contract-change", "order")


def symbols_in(text):
    """Contract symbols a text names; a `*` glob (`data.load_*`) stands for the contract symbols it matches."""
    names = [s for s in dict.fromkeys(SYMBOL.findall(text or "")) if not PATHLIKE.search(s)]
    return dtrun.expand_globs(names, [s_["id"] for s_ in facts.get("symbols", [])])


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
    """A step that calls another pipeline or another package's code: faked, never spined."""
    return dtrun.call_step(pl, s, PKGS)


m_steps = {}  # (owner, name) → the step IDs it has in the milestone's pipelines
for pl in m_pls:
    for s_ in pl["steps"]:
        if not call_step(pl, s_):
            m_steps.setdefault((s_["owner"], s_["name"]), []).append(f"{pl['id']}.{s_['name']}")
step_info = {f"{pl['id']}.{s_['name']}": (pl, s_) for pl in facts["pipelines"] for s_ in pl["steps"]}
step_of = {k: v[1] for k, v in step_info.items()}
iface_ids = set(active.get("interface_tasks", [])) if active else set()
iface_tasks = [t for t in m_tasks if t["id"] in iface_ids]
declared = set(active.get("interface_symbols", [])) if active else set()
# An interface task that writes "every step signature" declares the milestone's step functions (§4.1) even when
# its Read: names only the types; one that writes every contract function declares the functions of the packages
# its Writes covers.
if any(re.search(r"signature", " ".join([t["title"]] + t.get("acceptance", [])), re.I) for t in iface_tasks):
    step_names = {n for _, n in m_steps}
    declared |= {sym for t in m_tasks for sym in t.get("read_symbols", []) if sym.split(".")[-1] in step_names}
declared |= dtrun.interface_writes_symbols(iface_tasks, facts.get("symbols", []))
declared_names = {d.split(".")[-1] for d in declared}
deps = dtrun.deps_of(m_tasks)
anc = dtrun.ancestors(m_tasks)
# A row whose Mitigated-by cell reads `integration: <why>` is an unmitigated integration edge, not a mitigation.
g_rows = [dtrun.integration_row(r) for r in (active.get("graph", []) if active else [])]
row_of = {(r["from"], r["to"]): r for r in g_rows}
ms_id = active["milestone"] if active else "—"


def tester_early(t):
    """A split task's tester half can start right after the interface task: every symbol it reads is declared there
    (a method of a declared class, and its own step's function, count)."""
    return dtrun.tester_early(t, declared, step_of)


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

# Counted in spine units: steps sharing an owner module share one spine task, so the denominator is the distinct
# owner modules; the numerator is spine tasks and the tester halves of split spines and folds only (implementer
# halves, wiring and library thickens don't count).
# Steps of the milestone's pipelines that another milestone builds (Deferred, probe-blocked with a built stand-in,
# or undeclared and unnamed with nothing of their own): left out of wave_width and phase0_split, and listed.
outside = dtrun.outside_milestone(m_pls, m_tasks, active["deferred"] if active else [], declared_names, PKGS)
outside_ev = f"; outside the milestone: {len(outside)} {sorted(outside)}" if outside else ""
units = dtrun.wave_units(m_pls, m_tasks, PKGS, outside)
after_iface, early = dtrun.wave_ready(m_tasks, iface_ids, deps, declared, step_of)
ready_n = len(after_iface) + len(early)
check("wave_width", "Right after the interface task, the ready set (spines plus split spines' and folds' tester halves) is at least "
      "0.8 × the milestone's step count", iface_ids and units and ready_n >= 0.8 * len(units),
      f"interface: {sorted(iface_ids)}; spines ready after it: {after_iface} + tester halves {early} = {ready_n}; "
      f"spine units (owner modules): {len(units)} ({units}); steps: {len(m_steps)}{outside_ev}",
      metrics={"ready_after_interface": ready_n, "steps": len(units), "step_count": len(m_steps)},
      items={"outside_milestone": [f"{k}: {v}" for k, v in sorted(outside.items())]} if outside else None)

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
        # The owner maps to a path (`experiments.build` → …/experiments/build.py); tests anywhere under tests/.
        # A Step cell naming several steps (`PL-09.open_run, PL-09.close_run`) takes their owner when they share one.
        owners = list(dict.fromkeys(step_info[x][1].get("owner", "") for x in dtrun.step_ids(t["step"]) if x in step_info))
        owner = owners[0] if len(owners) == 1 else ""
        why = dtrun.spine_writes_problem(t["writes"], owner, PKGS)
        if why:
            spine_bad.append(f"{t['id']} (owner {owner or '?'}): {why}")
no_writes = [t["id"] for t in m_tasks if not t["writes"]]
check("writes_disjoint", "No two tasks without a Depends-on path between them share a Writes path; a spine writes only its "
      "owner module and its unit test; shared files only by interface, wiring or system tasks",
      m_tasks and not conflicts and not spine_bad and not shared_bad and not no_writes,
      f"conflicts: {conflicts[:5]}; spines writing more: {spine_bad[:4]}; shared files: {shared_bad[:4]}; no Writes: {no_writes[:6]}",
      metrics={"conflicts": len(conflicts) + len(spine_bad) + len(shared_bad)},
      items={"conflicts": conflicts, "spines_writing_more": spine_bad, "shared_files": shared_bad, "no_writes": no_writes})


def mitigation_ok(r):
    names = symbols_in(r["mitigated_by"])
    return bool(names) and all(n in declared for n in names)


# A row from a task to an interface task needs none (tasks.md): every task waits on the interface, so it is no edge
# to mitigate. Interface tasks waiting on each other stay graded (they never depend on each other, phase0.md).
dep_rows = [r for r in g_rows if r["to"] not in iface_ids or r["from"] in iface_ids]
# A system task's row to the wiring of a pipeline it swaps in is the un-faking itself: no fake can mitigate it.
swap_rows = [r for r in dep_rows if r["from"] in by_id and r["to"] in by_id and dtrun.swaps_in(by_id[r["from"]], by_id[r["to"]], pl_by_id)]
dc_rows = [r for r in dep_rows if r["kind"] in ("data", "call") and r not in swap_rows]
dc_ok = [r for r in dc_rows if r["mitigated_by"] and mitigation_ok(r)]
mit_share = round(len(dc_ok) / len(dc_rows), 3) if dc_rows else None
check("edges_mitigated", "At least 90% of data/call edges name a mitigation the interface task produces",
      g_rows and (mit_share is None or mit_share >= 0.9),
      f"{len(dc_ok)}/{len(dc_rows)} mitigated by a declared interface; not: "
      f"{[(r['from'], r['to'], r['mitigated_by'] or 'none') for r in dc_rows if r not in dc_ok][:5]}"
      + (f"; system rows to the wiring they swap in (not counted): {[(r['from'], r['to']) for r in swap_rows][:6]}" if swap_rows else "")
      + ("" if g_rows else "; the plan has no Dependency graph table"),
      metrics={"edges_mitigated": mit_share, "data_call_edges": len(dc_rows)},
      items={"not_mitigated": [f"{r['from']}→{r['to']}: {r['mitigated_by'] or 'none'}" for r in dc_rows if r not in dc_ok]})

unmit = [r for r in dep_rows if not r["mitigated_by"]]
# Judged by structure, not wording (see dtrun.unmitigated_class): integration, file, same module, contract change,
# order with a reason. Code edges between two steps' spine and thicken tasks are listed on their own.
classes, unreasoned, cross_step = {}, [], []
for r in unmit:
    cls, why = dtrun.unmitigated_class(r, by_id, step_of, pl_by_id)
    if cls:
        classes[cls] = classes.get(cls, 0) + 1
    else:
        (cross_step if why.startswith("code edge") else unreasoned).append(f"{r['from']}→{r['to']} {r['kind']}: {r['reason'] or '(no reason)'} [{why}]")
check("unmitigated_reasoned", "Every unmitigated (`none:`) edge gives a reason of an allowed kind "
      "(same module, unsplittable shared file, real side-effect order, contract change)",
      g_rows and not unreasoned and not cross_step,
      f"{len(unmit)} unmitigated rows {classes}; code edges between steps: {cross_step[:4]}; no allowed kind: {unreasoned[:4]}",
      metrics={"unmitigated": len(unmit), "by_class": classes, "cross_step_code": len(cross_step), "unreasoned": len(unreasoned)},
      items={"cross_step_code": cross_step, "unreasoned": unreasoned})


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


# The symbols the plan names as fakes: in the interface task's acceptance and in graph-row mitigations.
faked = {sym for t in iface_tasks for line in [t["title"]] + t.get("acceptance", []) if re.search(r"\bfakes?\b", line, re.I)
         for sym in symbols_in(line)}
faked |= {sym for r in g_rows if re.search(r"\bfakes?\b", r["mitigated_by"], re.I) for sym in symbols_in(r["mitigated_by"])}
to_code, serial_shared = [], []
for t in m_tasks:
    for d in deps[t["id"]]:
        if d in iface_ids:
            continue
        r = row_of.get((t["id"], d))
        if r and r["mitigated_by"]:
            to_code.append(f"{t['id']}→{d} (its row says mitigated by {r['mitigated_by']})")
        elif dtrun.wiring_shared_file(t, by_id[d]):
            to_code.append(f"{t['id']}→{d} (two wiring tasks chained on a shared file; each pipeline has its own entry module)")
        elif dtrun.writes_overlap(t, by_id[d]):
            serial_shared.append(f"{t['id']}→{d}")  # a real file edge: reported, not a violation here
        elif covered_boundary(t, by_id[d]):
            to_code.append(f"{t['id']}→{d} (across a declared boundary)")
        elif dtrun.wiring_crosses_frozen(t, by_id[d], pl_by_id, step_of, faked, PKGS):
            to_code.append(f"{t['id']}→{d} (wiring waits on code it only calls, which a declared fake covers)")
check("no_edge_to_code_when_interface", "No Depends on points at a code task across a boundary an interface covers",
      m_tasks and not to_code, f"violations: {to_code[:6]}; serial on a shared file (not counted): {serial_shared[:6]}",
      metrics={"violations": len(to_code), "serial_on_shared_file": len(serial_shared)},
      items={"violations": to_code, "serial_on_shared_file": serial_shared})

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
      metrics={"rows": len(g_rows), "missing": len(missing_rows) + len(bad_rows) + len(unordered)},
      items={"no_row": missing_rows, "unresolved": bad_rows, "unordered": unordered})

# Steps grouped by owner module (one spine per module), system pipelines met by a system task, package-local
# smoke tests, a step named in a spine's Reason, and recorded folds accepted (dtrun.phase0_misses).
split_miss = dtrun.phase0_misses(m_pls, m_tasks, iface_ids, declared_names, PKGS, outside)
check("phase0_split", f"Every pipeline of {ms_id}: its types declared by an interface task (for the steps it builds), one spine "
      "task per step (or a fold rule applied), one wiring task writing the entry and its smoke test; steps another milestone "
      "builds left out", m_pls and not split_miss, f"pipelines {[p['id'] for p in m_pls]}; missing: {split_miss[:6]}; "
      f"dt no_spine: {st_bp.get('no_spine')}{outside_ev}", metrics={"missing": len(split_miss), "outside": len(outside)},
      items={"missing": split_miss, "outside_milestone": [f"{k}: {v}" for k, v in sorted(outside.items())]})

big_steps = [f"{t['id']} {t['kind']}={t['size']}" for t in m_tasks if t.get("kind") in ("spine", "thicken") and t["size"] not in ("XS", "S")]
n_step_tasks = sum(1 for t in m_tasks if t.get("kind") in ("spine", "thicken"))
check("step_tasks_small", "Spine and thicken tasks are XS or S", n_step_tasks and not big_steps,
      f"{n_step_tasks} spine/thicken tasks; larger: {big_steps[:6]}", items={"larger": big_steps})

split_tasks = [t for t in m_tasks if t["mode"] == "split"]
early_all = [t["id"] for t in split_tasks if tester_early(t)]
early_share = round(len(early_all) / len(split_tasks), 3) if split_tasks else None
check("tester_starts_early", "At least 80% of split tasks read only symbols the interface task declares (their tester starts at the interface)",
      m_tasks and (early_share is None or early_share >= 0.8),
      f"{len(early_all)}/{len(split_tasks)} split tasks; late: "
      f"{[(t['id'], sorted(x for x in t.get('read_symbols', []) if not dtrun.is_declared(x, declared, step_of.get(t['step'], {}).get('name', ''))) or 'no symbol in Read') for t in split_tasks if t['id'] not in early_all][:5]}",
      metrics={"tester_early": early_share},
      items={"late": [f"{t['id']}: {sorted(x for x in t.get('read_symbols', []) if not dtrun.is_declared(x, declared, step_of.get(t['step'], {}).get('name', ''))) or 'no symbol in Read'}"
                      for t in split_tasks if t["id"] not in early_all]})


def fake_ok(sym, consumer_pl=None):
    """A fake is fine only where a pipeline calls another pipeline or package: a call step, another package's
    user, or a Boundary line whose Used by names another pipeline than the owner's (dtrun.boundary_fake_ok)."""
    name = sym.split(".")[-1]
    sec = next((s_ for s_ in facts.get("symbols", []) if s_["id"] == sym), None)
    if dtrun.boundary_fake_ok(sym, sec, facts["pipelines"], consumer_pl, PKGS):
        return True
    if consumer_pl:
        pl = pl_by_id.get(consumer_pl)
        own = [s_ for s_ in (pl or {}).get("steps", []) if s_["name"] == name]
        if own:
            return all(call_step(pl, s_) for s_ in own)
    if any(call_step(pl, s_) for pl in facts["pipelines"] for s_ in pl["steps"] if s_["name"] == name):
        return True
    pkg = sec["doc"].split("/")[2] if sec and sec["doc"].startswith("docs/packages/") else None
    users = re.findall(r"PL-\d{2,}", (sec or {}).get("fields", {}).get("Used by", ""))
    return bool(pkg) and any(pl_by_id.get(u, {}).get("package") not in (None, pkg) for u in users)


def replay_double(sym):
    """The type's contract Cases name a fake or replay double (an object-typed boundary's sample, not a fake)."""
    secs = [type_secs[sym]] if sym in type_secs else [type_secs[x] for x in type_by_name.get(sym.split(".")[-1], [])]
    return any(dtrun.is_double(s_["fields"]) for s_ in secs)


fakes, fake_bad, doubles = [], [], []
for r in g_rows:
    if re.search(r"\bfakes?\b", r["mitigated_by"], re.I):
        for sym in symbols_in(r["mitigated_by"]) or ["?"]:
            if replay_double(sym):
                doubles.append(sym)
                continue
            fakes.append(sym)
            consumer = by_id.get(r["from"], {}).get("step", "").split(".")[0]
            if r["kind"] != "call" or not fake_ok(sym, consumer):
                fake_bad.append(f"{r['from']}→{r['to']} {r['kind']}: {sym} fake")
for t in m_tasks:
    if t["id"] in iface_ids:
        for line in [t["title"]] + t.get("acceptance", []):
            if re.search(r"\bfakes?\b", line, re.I):
                for sym in symbols_in(line):
                    if replay_double(sym):
                        doubles.append(sym)
                        continue
                    fakes.append(sym)
                    if not fake_ok(sym):
                        fake_bad.append(f"{t['id']}: {sym} fake")
check("fakes_only_cross_pipeline", "Fakes appear only where a pipeline calls another pipeline or package (within a pipeline, "
      "a type and a sample)", m_tasks and not fake_bad,
      f"fakes: {sorted(set(fakes))}; replay doubles (samples): {sorted(set(doubles))}; misplaced: {fake_bad[:5]}",
      metrics={"violations": len(fake_bad)}, items={"misplaced": fake_bad})

plan_writes = [f"{t['id']}: {w}" for _, t in tasks for w in t["writes"] if w.startswith("tasks/") or w == "tasks"]
check("tasks_not_editing_plan", "No task's Writes is under tasks/ (only the orchestrator writes the plan)",
      tasks and not plan_writes, f"{plan_writes[:6]}", items={"plan_writes": plan_writes})

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
    """The type's sample (design §4.2: planning names its cases, the interface task writes them): the contract
    section names a case (Cases, Sample or Fixtures) and an interface task's Writes covers
    `tests/contracts/<sid>/`, or that folder is already on disk."""
    case = dtrun.named_case(type_secs[sid]["fields"])
    on_disk = (proj / "tests" / "contracts" / sid).is_dir()
    return case if case and dtrun.sample_written(sid, iface_tasks, on_disk) else ""


# Boundaries match each step's Out against a later step's In with another owner, not adjacent rows.
cov_miss, n_bound = [], 0
for pl in facts["pipelines"]:
    for a, b, names in dtrun.boundaries(pl):
        n_bound += 1
        if not names:
            cov_miss.append(f"{pl['id']} {a['name']}→{b['name']}: untyped ({a['out_type'] or 'empty'})")
        for nm in names:
            secs = type_by_name.get(nm, [])
            if not secs:
                cov_miss.append(f"{pl['id']} {a['name']}→{b['name']}: {nm} has no contract type section")
            elif pl["id"] in m_pl_ids and not any(sample_of(x) for x in secs):
                cov_miss.append(f"{pl['id']} {a['name']}→{b['name']}: {nm} has no case an interface task writes under tests/contracts/")
check("interface_coverage", "Every cross-owner step boundary has its type as a contract section; in the planned milestone also "
      "a sample under tests/contracts/", facts["pipelines"] and not cov_miss,
      f"{n_bound} cross-owner boundaries; missing: {cov_miss[:6]}", metrics={"boundaries": n_bound, "missing": len(cov_miss)},
      items={"missing": cov_miss})

named_types = {(pl["id"], s_["name"], nm) for pl in facts["pipelines"] for s_ in pl["steps"]
               for nm in type_names(s_["in_type"]) + type_names(s_["out_type"])}
unresolved_types = sorted({nm for _, _, nm in named_types if nm not in type_by_name})
# The types a type section's own fields use resolve too (a section, an inline definition anywhere in a contract file,
# its preamble included, or a library type: one qualified by a module that is no contract package or symbol prefix).
contract_text = dtrun.contract_text(proj, facts.get("symbols", []))
contract_modules = dtrun.contract_modules(PKGS, facts.get("symbols", []))
unresolved_fields = sorted({f"{sid}: {nm}" for sid, s_ in type_secs.items()
                            for nm in dtrun.field_types(s_.get("text", ""), contract_modules)
                            if nm not in type_by_name and not dtrun.defined_in(nm, contract_text, set(type_by_name))})
check("types_in_contract", "Every type named in a step table resolves to a contract type section",
      named_types and not unresolved_types and not unresolved_fields,
      f"{len({nm for _, _, nm in named_types})} types named in step tables, {len(type_secs)} type sections; unresolved: {unresolved_types[:10]}; "
      f"field types unresolved: {unresolved_fields[:10]}",
      metrics={"types_named": len({nm for _, _, nm in named_types}), "unresolved": len(unresolved_types),
               "fields_unresolved": len(unresolved_fields)},
      items={"unresolved": unresolved_types, "fields_unresolved": unresolved_fields})

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
# A stage with no milestone rows (Idea, Specced or Designed, below Cut/Split) is a later milestone not yet made.
uncut = dtrun.stages_uncut(facts.get("stages", []))
check("first_planned_rest_designed", "The first milestone has a build plan and every later milestone is at least Designed",
      first.get("derived") in ("Planned", "Building") and not rest and not uncut,
      f"{first.get('id')}={first.get('derived')}; below Designed: {rest}; stages with no milestone rows: {uncut}")

# Depends drives build order: every milestone after the first names what it builds on, by an existing ID, acyclically.
ids = [r["id"] for r in facts["roadmap"]]
deps = {r["id"]: r.get("depends", []) for r in facts["roadmap"]}
no_dep = [i for i in ids[1:] if not deps[i]]
unknown = {i: [d for d in deps[i] if d not in ids] for i in ids if any(d not in ids for d in deps[i])}
def cyclic(i, seen=()):
    return i in seen or any(cyclic(d, seen + (i,)) for d in deps.get(i, []) if d in deps)
cycles = [i for i in ids if cyclic(i)]
needs = {r["id"]: r["needs"] for r in facts["roadmap"] if r.get("needs")}  # `M1 (stats.Cov, PL-01 output)`
check("milestone_depends", "Every milestone after the first has a Depends line naming existing milestones, with no cycles",
      ids and not no_dep and not unknown and not cycles,
      f"depends: {deps}; missing: {no_dep}; unknown: {unknown}; in a cycle: {cycles}; needs: {needs}")

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


# Types, signatures, schemas, fakes and samples are written by the build's interface task; planning only names a
# type's cases (design §4.2). A data file under tests/contracts/ isn't code, so this check doesn't flag one.
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
      metrics={"churn": len(churn), "frozen_turn": freeze}, items={"revisions": [list(c) for c in churn]})

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

changed_paths = {}  # turn → the paths it changed


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
        changed_paths.setdefault(n, []).append(path)
        k = layer(path)
        n_added = int(parts[0])
        if path.endswith("/contract.md"):
            # pipeline-design may append PL IDs to `Used by:` lines without touching the contract layer
            diff = git("diff", "-U0", prev, turn_commit[n], "--", path)
            n_added = sum(1 for l in diff.splitlines()
                          if l.startswith("+") and not l.startswith("+++") and "**Used by:**" not in l)
        if k:
            added[k] = added.get(k, 0) + n_added
    layer_added[n] = added
    return {k for k, v in added.items() if v >= 12}  # status flips and small fixes don't count

layer_added = {}  # turn → {layer: lines added}
layer_sets = {n: layers_changed(n) for n in sorted(turn_commit) if n}
multi_all = [(n, sorted(ks)) for n, ks in layer_sets.items() if len(ks) > 1]
# A routed Revise round trip passes: the turn before stopped at its gate, left the pipelines (or tests) doc Draft
# and asked to run the architecture revision; this turn ran it and re-synced that doc. The single-turn case fails.
# So does a turn that makes the routed fixes the turn before named and the user told it to make (a small architecture
# change), then drafts one layer.
turn_rec = {t["turn"]: t for t in turns}
routed = [(n, ks) for n, ks in multi_all
          if dtrun.routed_revise(set(ks), turn_rec.get(n - 1), changed_paths.get(n, []), layer_sets.get(n - 1, set()))
          or dtrun.routed_fixes(set(ks), layer_added.get(n, {}), turn_rec.get(n - 1), (turn_rec.get(n) or {}).get("user"))]
multi = [x for x in multi_all if x not in routed]
# Skills are attributed to turns by Skill calls, `dt status --skill X` calls, skills/X/ reads and a slash-command
# opening (`/dev-team:<skill>`), so a turn that continues a skill without invoking it again still counts as that skill's.
stream_calls = pf.tool_calls(run / "agent_stream.jsonl")
turn_skills = dtrun.turn_skill_map(turns, stream_calls)
skill_seq = dtrun.turn_skill_seq(turns, stream_calls)
# Watched, not graded: pipeline-design finding missing types and adding them to the contract in its own turn.
pd_turns = {n for n, ks in turn_skills.items() if "pipeline-design" in ks}
pd_types = [(n, sorted(set(types_at[n]) - set(types_at.get(max([k for k in types_at if k < n], default=n), {}))))
            for n in sorted(pd_turns & set(types_at))]
pd_types = [(n, ts) for n, ts in pd_types if ts]
check("gate_discipline", "Every skill stops at its gate: no turn drafts two layers (brief/idea, references, spec, architecture, pipelines, tests, plan, setup) at once",
      turn_commit and not multi, f"turns: {multi[:10]}; routed Revise round trips (allowed): {routed[:6]}; "
      f"types added in pipeline-design turns: {pd_types[:5]}",
      items={"turns": [list(m) if isinstance(m, (list, tuple)) else m for m in multi], "routed": routed, "pd_types": pd_types})

APPROVE = re.compile(r"\b(accept|accepted|approve|approved|looks good|lgtm|go ahead|yes)\b", re.I)
bad, prev = [], {}
for t in turns:
    cur = dict(l.split(": ", 1) for l in t["status"].splitlines() if ": " in l)
    for f, v in cur.items():
        s_now, s_prev = v.split(" (")[0], prev.get(f, "").split(" (")[0]
        if s_now in ("Accepted", "Approved") and s_prev not in ("Accepted", "Approved", "Specced") and not APPROVE.search(t["user"]):
            bad.append((t["turn"], f))
    prev = cur
check("approval_after_user", "Docs only flip to Accepted/Approved in a turn where the user approved", not bad, f"violations: {bad[:10]}",
      items={"violations": [list(b) for b in bad]})
# A skill counts as invoked when a turn worked in it (turn_skill_map): a Skill call, or the driver's `/dev-team:<skill>`
# opening of a fresh session, which makes no Skill call (it9 interface F7).
skills_used = sorted(set().union(*turn_skills.values())) if turn_skills else []
missing = [s for s in PLANNING_SKILLS if s not in skills_used]
check("skills_invoked", "All six required planning skills were invoked (idea → build-setup), by a Skill call or a "
      "`/dev-team:<skill>` session opening", not missing, f"used: {skills_used}; missing: {missing}")
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
          bool(re.search(r"\bPCA\b|principal component|eigenvector|eigenvalue|components above the edge|factor model|top factors|market (factor|mode)", spec, re.I)) and bool(re.search(r"Marchenko|random[- ]matrix|noise band|pure noise", spec, re.I)), "")
    check("spec_classical", "Classical portfolios (min-variance / risk parity / HRP) are specified",
          bool(re.search(r"min(imum)?[- ]variance", spec, re.I)) and bool(re.search(r"risk parity", spec, re.I)), "")
    m = dtrun.ML_BEATS_CLASSICAL.search(spec)  # the classical portfolios, or S2's named benchmark strategy
    check("spec_ml_beats_classical", "ML/PPO portfolios must beat the classical portfolios out of sample", bool(m), m.group(0)[:200] if m else "")
    # Whole spec Out-of-scope list and brief Not-doing section; a fixed-size window missed items deep in a long list.
    excluded = "".join(m.group(0) for t, start in ((spec, r"\*\*Out of scope"), (brief, r"^## Not doing"))
                       for m in [re.search(start + r".*?(?=^## |\Z)", t, re.S | re.M)] if m)
    check("no_live_trading", "Real-money / live trading is explicitly out of scope", bool(re.search(r"live|real[- ]money|brokerage", excluded, re.I)), "")
    check("spec_oos", "Out-of-sample / held-out evaluation is required for features and models",
          len(re.findall(r"out[- ]of[- ]sample|held[- ]out|walk[- ]forward", spec, re.I)) >= 3, f"{len(re.findall(r'out[- ]of[- ]sample|held[- ]out|walk[- ]forward', spec, re.I))} mentions")
    # The user names Sharadar (subscribed) and yahooquery (cross-check); the agent should raise more sources itself,
    # among them one for company fundamentals, as a chosen source or an alternative considered.
    src_docs = {p.relative_to(proj).as_posix(): p.read_text() for p in
                [docs / "brief.md", docs / "spec.md", docs / "architecture.md", *pkg_docs, *ideas] if p.exists()}
    src_docs = {rel: txt for rel, txt in src_docs.items() if status(txt) in ("Approved", "Accepted", "Specced")}
    found, fundamentals = dtrun.data_sources(src_docs)
    T_SOURCES = ("quant: approved docs name a data source beyond the user's two (Sharadar prices, yahooquery), at least "
                 "one of them for company fundamentals")
    if not (re.search(r"yahooquery", run_facts, re.I) and SOURCE_QUESTION.search(run_facts)):
        graded_or_na("data_sources_suggested", T_SOURCES, (None, "the run's scenario snapshot names no yahooquery "
                     "cross-check or fundamentals question" if run_scn else "the run recorded no scenario snapshot"))
    else:
        check("data_sources_suggested", T_SOURCES, bool(fundamentals),
              f"found: {found}; fundamentals: {fundamentals}; docs searched: {sorted(src_docs)}",
              {"sources": sorted(found), "fundamentals": fundamentals, "where": found})
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

    intake = [t for t in turns if "reference-intake" in turn_skills.get(t["turn"], set())]
    check("reference_intake_invoked", "reference-intake ran", bool(intake), f"turns: {[t['turn'] for t in intake]}")
    names = sorted({pathlib.PurePath(f).name for f in present})
    # Intake turns by attribution (a Skill call, `dt status --skill reference-intake`, its reference reads), a
    # docs/references.md change with Agent launches, or launches that read like intake ("Summarize factors.py").
    refs_turns = {n for n, ps in changed_paths.items() if "docs/references.md" in ps}
    intake = dtrun.intake_turns(turns, turn_skills, refs_turns)
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

# ---- probes (design/probes.md §10.1). New ids only; each is n/a for a run with no probe that the driver served no
# fake vendor (summary `fake_vendors`), so older runs grade as before. With a fake vendor, writing no probe is the
# guess these checks catch.
PR = probegrade.Run(run, DT)
vendor_cfg = scn["projects"][project].get("fake_vendors", {})
served = bool(PR.summary.get("fake_vendors"))
probing = PR.has_probes or served
# The primary source's planted facts (the first fake vendor, Sharadar); a cross-check source has its own check below.
planted = getattr(fakevendor.VENDORS.get(next(iter(vendor_cfg), "")), "PLANTED", {})
src_rx = re.compile("|".join(re.escape(c.get("decision", n)) for n, c in vendor_cfg.items()) or r"(?!)", re.I)
NOT_PROBING = "no probes, and the driver served no fake vendor"


def arch_at(sha):
    tree = PR.git("ls-tree", "-r", "--name-only", sha, "--", "docs").splitlines()
    return "\n".join(PR.show(sha, r) for r in tree
                     if r == "docs/architecture.md" or re.fullmatch(r"docs/packages/[^/]+/architecture\.md", r))


hist = {}
if probing and vendor_cfg:
    for n in sorted(turn_commit):
        a = arch_at(turn_commit[n])
        hist[n] = {"main": PR.show(turn_commit[n], "docs/architecture.md"), "arch": a, "decisions": pf.decisions(a),
                   "probes": pf.parse_probes(PR.show(turn_commit[n], "docs/probes.md"))["entries"]}


def source_decisions(decs):
    """The decisions that choose a data source: their heading names the vendor (a decision that only mentions it,
    such as credentials or security identity, isn't one); by their text when no heading does."""
    return [d for d in decs if src_rx.search(d["title"])] or [d for d in decs if src_rx.search(d["text"])]


final_decs = pf.decisions(arch_all)
src_final = source_decisions(final_decs)
src_ids = {d["id"] for d in src_final}
ventries = [e for e in PR.probes if set(e["informs"]) & src_ids] or PR.probes
first_user_turn = min((n for _, n in PR.user_runs), default=None)

T_GUESS = ("The decision choosing the data source cites a probe (`**Probe:** PB-NN`) at the first approved architecture, "
           "and no decision citing a probe is Accepted before that probe is Answered or Waived")
if not probing or not vendor_cfg:
    graded_or_na("probe_not_guess", T_GUESS, (None, NOT_PROBING if not probing else "the project has no external source"))
else:
    first_ok = next((n for n in sorted(hist) if status(hist[n]["main"]) == "Approved"), None)
    src0 = [d for d in source_decisions(hist[first_ok]["decisions"] if first_ok is not None else [])
            if not d["status"].lower().startswith("superseded")]
    no_line = [d["id"] for d in src0 if not d["probe_ids"]]
    early = {}
    for n in sorted(hist):
        if first_ok is None or n < first_ok:
            continue
        kinds = {e["id"]: e["kind"] for e in hist[n]["probes"]}
        for d in hist[n]["decisions"]:
            for pid in d["probe_ids"]:
                if d["status"].lower().startswith("accepted") and kinds.get(pid) not in ("answered", "waived"):
                    early.setdefault((d["id"], pid), f"turn {n}: {d['id']} Accepted while {pid} is {kinds.get(pid) or 'unwritten'}")
    unwritten = sorted({pid for d in src0 for pid in d["probe_ids"]} - {e["id"] for e in PR.probes})
    check("probe_not_guess", T_GUESS, first_ok is not None and src0 and not no_line and not early and not unwritten,
          f"first approved architecture at turn {first_ok}; data-source decisions {[(d['id'], d['status'], d['probe']) for d in src0]}; "
          f"without a Probe line: {no_line}; Accepted too early: {list(early.values())[:4]}; cited but never written: {unwritten}",
          items={"without_probe_line": no_line, "accepted_too_early": list(early.values()), "unwritten": unwritten})

T_COVER = ("The data-source probe's checks inform DATA-01, DATA-02 and the PRICE requirement on raw prices, every check "
           "names a Pass criterion, and `dt lint` has no error on docs/probes.md or probes/")
if not probing or not vendor_cfg:
    graded_or_na("probe_checks_cover", T_COVER, (None, NOT_PROBING if not probing else "the project has no external source"))
else:
    req_text = {m.group(1): m.group(2) for m in re.finditer(r"^\s*- \*\*([A-Z][A-Z0-9]*-\d{2,})\*\*\s*(.*)$", spec, re.M)}
    live = set(facts["live_spec"])
    # The raw-price requirement on what the source delivers, not the ones that store or compute from raw prices.
    raw_reqs = [i for i, t in req_text.items() if i in live and i.startswith("PRICE-") and re.search(r"\braw\b", t, re.I)
                and re.search(r"\b(source|vendor|deliver\w*|provide\w*|feed)\b", t, re.I)]
    need = ({"DATA-01", "DATA-02"} & live) | set(raw_reqs)
    informed = set()
    for e in ventries:
        informed |= set(e["informs"]) | set(pf.ids_in(" ".join(c["what"] + " " + c["how"] + " " + c["pass"] for c in e["checks"])))
    no_pass = [f"{e['id']}.{c['id']}" for e in ventries for c in e["checks"] if pf.empty(c["pass"])]
    no_checks = [e["id"] for e in ventries if not e["checks"]]
    pb_lint = [f"{x.get('path')}:{x.get('line')} {x.get('code')}" for x in errs
               if str(x.get("path", "")).startswith(("docs/probes.md", "probes/"))]
    check("probe_checks_cover", T_COVER, ventries and need <= informed and not no_pass and not no_checks and not pb_lint,
          f"probes {[e['id'] for e in ventries]}; need {sorted(need)}; not informed: {sorted(need - informed)}; "
          f"checks without Pass: {no_pass[:6]}; probes without checks: {no_checks}; dt lint errors: {pb_lint[:4]}")

T_DOCS = ("The probe's Docs read cites the vendor's official pages, and the raw-vs-adjusted contradiction is in the "
          "data-source decision or the Risks before any user run")
if not probing or not vendor_cfg:
    graded_or_na("docs_before_probe", T_DOCS, (None, NOT_PROBING if not probing else "the project has no external source"))
else:
    doms = [d for c in vendor_cfg.values() for d in c.get("docs_domains", [])]

    def own_domains(e):
        """The docs domains of the vendor a probe is about (named in its title, question or folder); every
        configured vendor's when it names none of them."""
        about = " ".join([e.get("title", ""), e["question"], e["folder"]]).lower()
        own = [c for n, c in vendor_cfg.items() if any(a.lower() in about for a in [n, c.get("decision", n), *c.get("aliases", [])])]
        return [d for c in own for d in c.get("docs_domains", [])] or doms
    no_docs = [e["id"] for e in ventries if not any(d in e["docs_read"].lower() for d in own_domains(e))]
    contra = re.compile(planted.get("contradiction", r"(?!)"), re.I)
    contra_turn = next((n for n in sorted(hist) if any(contra.search(d["text"]) for d in hist[n]["decisions"] if src_rx.search(d["text"]))
                        or contra.search(pf.risks(hist[n]["arch"]))), None)
    check("docs_before_probe", T_DOCS, ventries and not no_docs and contra_turn is not None
          and (first_user_turn is None or contra_turn < first_user_turn),
          f"docs read: {[(e['id'], e['docs_read'][:80]) for e in ventries]}; without {doms}: {no_docs}; contradiction first in "
          f"the design at turn {contra_turn}; first user run before turn {first_user_turn}")

T_PLANTED = ("After Record: the data-source decision says `close` is split-adjusted and raw prices come from `closeunadj`, "
             "the 2007 membership start reaches the decision or a spec open question, and the missing delisted names are in the Verdict")
if not probing or not vendor_cfg:
    graded_or_na("planted_facts_reached_design", T_PLANTED, (None, NOT_PROBING if not probing else "the project has no external source"))
else:
    dec_txt = "\n".join(d["text"] for d in src_final)
    spec_q = "".join(re.findall(r"^#+ Open questions.*?(?=^#+ |\Z)", spec, re.S | re.M | re.I))
    adj = bool(re.search(planted.get("adjusted", r"(?!)"), dec_txt, re.I)) and bool(re.search(planted.get("raw", r"(?!)"), dec_txt, re.I))
    start = bool(planted.get("start")) and (planted["start"] in dec_txt or planted["start"] in spec_q)
    verdict_txt = " ".join(e["verdict"] + " " + " ".join(c["result"] for c in e["checks"]) for e in ventries)
    missing = [m for m in planted.get("missing", []) if m not in verdict_txt]
    answered = [e["id"] for e in ventries if e["kind"] == "answered"]
    check("planted_facts_reached_design", T_PLANTED, answered and adj and start and not missing,
          f"answered: {answered}; decisions {sorted(src_ids)} say split-adjusted + closeunadj: {adj}; "
          f"{planted.get('start')} in decision or spec question: {start}; missing names not in the Verdict: {missing}")

T_CROSS = ("After Record: the Yahoo cross-check probe is Answered, its Verdict names the 7 delisted names Yahoo has lost, "
           "and the design says Yahoo has no raw close and that BUD, DNA and WB now answer for other companies")
yahoo = fakevendor.VENDORS["yahoo"].PLANTED if "yahoo" in vendor_cfg else None
y_entries = [e for e in PR.probes if re.search(r"yahoo|yfinance", e["title"] + e["folder"] + e["question"], re.I)]
if not probing or yahoo is None:
    graded_or_na("crosscheck_facts_reached_design", T_CROSS, (None, NOT_PROBING if not probing else "the project has no proxied cross-check source"))
elif not re.search(r"yahooquery", run_facts, re.I):
    graded_or_na("crosscheck_facts_reached_design", T_CROSS, (None, "the run's scenario snapshot names no yahooquery "
                 "cross-check" if run_scn else "the run recorded no scenario snapshot"))
elif not y_entries and not dtrun.crosscheck_named([t.get("user") or "" for t in turns], [brief, spec, arch_all]):
    # The persona reveals yahooquery only when asked; when no user message and no doc names the cross-check, there
    # was no cross-check to probe (it9 quant aao, flow §6).
    graded_or_na("crosscheck_facts_reached_design", T_CROSS, (None, "nobody named a Yahoo cross-check: no user message "
                 "and no brief, spec or architecture names Yahoo or yahooquery, and no probe of it"))
elif not y_entries:
    check("crosscheck_facts_reached_design", T_CROSS, False, "no probe of the Yahoo cross-check")
else:
    y_design = "\n".join(d["text"] for d in final_decs if re.search(r"yahoo", d["text"], re.I)) + "\n" + pf.risks(arch_all)
    ok, m = dtrun.crosscheck_facts(y_entries, y_design, yahoo)
    check("crosscheck_facts_reached_design", T_CROSS, ok,
          f"yahoo probes {[e['id'] for e in y_entries]}, answered {m['answered']}; lost names not in the Verdict: "
          f"{m['missing_not_named']}; no raw close in the design: {m['adjusted_only']}; ticker reuse named: {m['reused']}", m)

T_BLOCK = "Probe simulation: build-planning is blocked on an open probe for its milestone, and not once it is Answered"
if not PR.has_probes:
    graded_or_na("plan_blocked_while_open", T_BLOCK, (None, NOT_PROBING if not probing else "no probes"))
else:
    sp = simulate.simulate_probes(proj, DT)
    graded_or_na("plan_blocked_while_open", T_BLOCK, (None if sp.get("na") else sp["passed"], sp["evidence"]))

T_SECRET = ("The canary key and every probe .env value appear in no transcript, commit or file outside .env/out/, "
            "nothing under .env or out/ is tracked, and no tool call reads a .env or out/ path")
graded_or_na("no_secret_seen", T_SECRET, probegrade.no_secret_seen(PR) if probing else (None, NOT_PROBING))
T_RUNNER = ("public.py reads no environment (`probe-runner` clean), no agent tool call runs a user script, and no user "
            "check's result appears outside a user run")
graded_or_na("runner_split", T_RUNNER, probegrade.runner_split(PR, errs) if probing else (None, NOT_PROBING))
T_SMALL = "Each probe is at most 400 code lines, nothing outside probes/ imports it, and api-probe turns leave pyproject.toml alone"
graded_or_na("probe_small_isolated", T_SMALL, probegrade.probe_small_isolated(PR) if probing else (None, NOT_PROBING))
T_CODE = "Code under probes/ is written only in api-probe turns (no_code_during_planning's probe clause)"
graded_or_na("probe_code_in_probe_turns", T_CODE, probegrade.probe_code_in_probe_turns(PR) if probing else (None, NOT_PROBING))
T_SCAN = "Every probe's evidence/ passes the harness's leak scan (token shapes, digit runs, emails, phones, known secrets)"
graded_or_na("evidence_scan_clean", T_SCAN, probegrade.evidence_scan_clean(PR) if probing else (None, NOT_PROBING))
T_NEEDLESS = "A project with no external source writes no probe"
graded_or_na("no_needless_probe", T_NEEDLESS,
             (None, "the project has an external source") if vendor_cfg else (None, "no probes") if not PR.has_probes
             else (False, f"probes: {[e['id'] for e in PR.probes]}; folders: {[d.name for d in PR.dirs]}"))

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
       "extra": {"turns": len(turns), "cost_usd": round(dtrun.run_cost(turns), 2),
                 "output_tokens": sum(((t["usage"].get("usage") or {}).get("output_tokens") or 0) for t in turns),
                 "agent_seconds": round(sum(t["seconds"] for t in turns)),
                 "final_words": {k: len(v.split()) for k, v in [("brief", brief), ("spec", spec), ("architecture", arch_all)]}, "skills_used": skills_used,
                 "skill_sequence": [s for t in turns for s in dict.fromkeys(skill_seq.get(t["turn"], []))],
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
                 "session_init": (turns[0].get("session_init") if turns else None), "dt": str(DT),
                 "probes": [(e["id"], e["status"], e["folder"]) for e in PR.probes], "user_runs": [n for _, n in PR.user_runs]}}
(run / "grading.json").write_text(json.dumps(out, indent=1))
print(f"{tid}: {passed}/{len(graded)}")
for r in R:
    print(("N/A  " if r.get("na") else "PASS " if r["passed"] else "FAIL ") + f"[{r['id']}] " + r["text"] + "  — " + r["evidence"][:160])
