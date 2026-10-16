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
def check(id_, text, passed, evidence):
    R.append({"id": id_, "text": text, "passed": bool(passed), "evidence": str(evidence)[:600]})

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
budget = [p for p in lint_problems if p.get("code") == "budget"]
check("doc_budgets", "Doc size budgets hold (no `dt lint` budget warnings; brief <= 500 words)", "_error" not in lint and not budget and bw <= 500,
      "; ".join(f"{p['path']}: {p['message']}" for p in budget[:6]) or f"brief {bw} words")

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
spined = {t["spine_pipeline"] for p in plans for t in p["tasks"] if t["spine_pipeline"]}
rows = {r["id"]: r for r in facts["roadmap"]}
no_spine = sorted({f"{p['milestone']}:{pl}" for p in plans for pl in rows.get(p["milestone"], {}).get("pipelines", []) if pl not in spined})
check("phase0_spine", "Every pipeline of a planned milestone has a Phase 0 spine task (active and queued plans)",
      plans and not no_spine and not st_bp.get("no_spine"),
      f"plans: {[p['doc'] for p in plans]}; missing: {no_spine}; dt no_spine: {st_bp.get('no_spine')}")

tasks = [(p, t) for p in plans for t in p["tasks"]]
packets, unresolved = {}, []
for _, t in tasks:
    c = dtj("context", t["id"])
    if c.get("_rc") != 0 or "_error" in c:
        unresolved.append(f"{t['id']} ({c.get('_error', 'rc=%s' % c.get('_rc'))[:80]})")
    else:
        packets[t["id"]] = c.get("lines", 0)
bad_size = [f"{t['id']}={t['size']}" for _, t in tasks if t["size"] not in ("XS", "S", "M")]
bad_mode = [f"{t['id']}: {t['mode']} (rule: {t['expected_mode']})" for _, t in tasks
            if t["mode"] != t["expected_mode"] and not t["reason"]]
check("tasks_well_formed", "Every task: Read IDs resolve (`dt context` exits 0), size <= M, Mode follows the rule (or gives a Reason)",
      tasks and not unresolved and not bad_size and not bad_mode and not st_bp.get("mode_violations"),
      f"{len(tasks)} tasks; unresolved: {unresolved[:6]}; size: {bad_size[:6]}; mode: {bad_mode[:6]}; dt mode_violations: {st_bp.get('mode_violations')}")
big = {k: v for k, v in packets.items() if v >= 2000}
check("context_packets_small", "`dt context` packets are under 2,000 lines", packets and not big,
      f"max {max(packets.values()) if packets else 0} lines over {len(packets)} packets; over: {big}")

rc_rm, out_rm, _ = dtrun.run(proj, "roadmap", "--check", dt=DT)
want_rows = summary.get("stages_reached", len(stages)) if mode == "incremental" else len(stages)
check("roadmap_rows", "One roadmap row per stage, with derived status (`dt roadmap --check` exits 0)",
      len(facts["roadmap"]) == want_rows and rc_rm == 0,
      f"{len(facts['roadmap'])} rows for {want_rows} stages: {[(r['id'], r['derived']) for r in facts['roadmap']]}; roadmap --check rc={rc_rm} {out_rm.strip()[:120]}")
if mode == "incremental":
    unplanned = [r["id"] for r in facts["roadmap"] if r["derived"] not in ("Planned", "Building", "Done")]
    check("incremental_all_planned", "Incremental: every revealed stage's milestone has a build plan (active or queued)",
          facts["roadmap"] and not unplanned, f"not planned: {unplanned}")
else:
    first = facts["roadmap"][0]["derived"] if facts["roadmap"] else None
    rest = [r["id"] for r in facts["roadmap"][1:] if r["derived"] in ("Idea", "Specced")]
    check("upfront_m1_planned", "All-at-once: M1 has a build plan and every later milestone is at least Designed",
          first in ("Planned", "Building") and not rest, f"M1={first}; below Designed: {rest}")

# Shape per turn, from the architecture header at each turn's commit.
shapes = []
for n in sorted(turn_commit):
    a = git("show", f"{turn_commit[n]}:docs/architecture.md")
    m = re.search(r"\*\*Shape:\*\*\s*([^·\n]+)", a)
    shapes.append((n, m.group(1).strip() if m else None))
if project == "quant":
    stage_of = {t["turn"]: t["stage"] for t in turns}
    multi = [(n, s) for n, s in shapes if s and not re.search(r"single", s, re.I)]
    grow_turn = multi[0][0] if multi else None
    final_multi = bool(shape) and not re.search(r"single", shape, re.I) and len(facts["packages"]) >= 2
    if mode == "incremental":
        ok = final_multi and stage_of.get(grow_turn) == "features_ml"
        ev = f"first multi-package turn {grow_turn} (stage {stage_of.get(grow_turn)}); final shape {shape!r}, packages {facts['packages']}"
    else:
        ok, ev = final_multi, f"final shape {shape!r}, packages {facts['packages']}"
    check("quant_grow_at_features", "quant: architecture Grows to multi-package at the features milestone (not before)", ok, ev)


def is_code(text):
    """Anything beyond blank lines, comments and a module docstring."""
    try:
        body = ast.parse(text).body
    except SyntaxError:
        return bool(text.strip())
    return any(not (isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant)) for n in body)


CODE_DIRS = re.compile(r"^(src/|tests/intent/|tests/unit/)")
code_files = []
for n in sorted(turn_commit):
    if n == 0:
        continue
    prev = prev_turn(n)
    names = git("diff", "--name-status", prev, turn_commit[n]) if prev else git("show", "--name-status", "--format=", turn_commit[n])
    for line in names.splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or parts[0].startswith("D") or not CODE_DIRS.match(parts[-1]):
            continue
        if is_code(git("show", f"{turn_commit[n]}:{parts[-1]}")):
            code_files.append((n, parts[-1]))
untracked = [l[3:] for l in git("status", "--porcelain").splitlines() if CODE_DIRS.match(l[3:])]
check("no_code_during_planning", "No source code written during planning (nothing under src/, tests/intent/, tests/unit/ beyond empty or docstring-only files)",
      turn_commit and not code_files and not untracked, f"code: {code_files[:10]}; uncommitted: {untracked[:5]}")

# ---- gates: one layer per turn; approvals only after the user approves
def layer(path):
    if path.endswith("brief.md") or "/ideas/" in path:
        return "brief"
    if path == "docs/spec.md":
        return "spec"
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
        k = layer(parts[2].split(" => ")[-1].rstrip("}"))
        if k:
            added[k] = added.get(k, 0) + int(parts[0])
    return {k for k, v in added.items() if v >= 12}  # status flips and small fixes don't count

multi = [(n, sorted(ks)) for n in sorted(turn_commit) if n and len(ks := layers_changed(n)) > 1]
check("gate_discipline", "Every skill stops at its gate: no turn drafts two layers (brief/idea, spec, architecture, pipelines, tests, plan, setup) at once",
      turn_commit and not multi, f"turns: {multi[:10]}")

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
    kind = "replan" if r["text"].startswith("Replan") else "advance" if r["text"].startswith("Advance") else "setup"
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
else:
    for env, pat in [("snake", r"snake"), ("fish", r"fish|tank|ball"), ("foraging", r"forag|predator|prey")]:
        check(f"spec_{env}", f"Spec covers the {env} environment", bool(re.search(pat, spec, re.I)), "")
    check("arch_shared_core", "Architecture has a shared core reused by all environments", bool(re.search(r"(shared|common|core)", arch_all, re.I)) and bool(re.search(r"interface|protocol|abc|class", arch_all, re.I)), "")
    check("spec_env_baselines", "Each environment's learning criterion beats a random or scripted baseline",
          len(re.findall(r"random|scripted|heuristic", spec, re.I)) >= 3, f"{len(re.findall(r'random|scripted|heuristic', spec, re.I))} mentions")
    check("spec_cpu_budget", "CPU training-time budget (~1 hour) is a quality requirement", bool(re.search(r"(hour|60 min|minutes).{0,120}(CPU|laptop|MacBook|processor)|(CPU|laptop|MacBook|processor).{0,120}(hour|60 min|minutes)", spec, re.I)), "")
    check("rl_single_package", "Proof-of-concept stays single package (no premature monorepo)", "single" in shape.lower(), shape)

passed = sum(r["passed"] for r in R)
tools = {}
for t in turns:
    for x in t["tools"]:
        tools[x] = tools.get(x, 0) + 1
perm_log = run / "permission_prompts.jsonl"
oracle_prompts = [json.loads(l).get("path") for l in perm_log.read_text().splitlines() if l.strip()] if perm_log.exists() else []
guard_hits = [e for t in turns for e in t.get("tool_errors", []) if re.search(r"oracle|expected\.json|archive", e, re.I)]
out = {"expectations": R,
       "summary": {"passed": passed, "failed": len(R) - passed, "total": len(R), "pass_rate": round(passed / len(R), 3)},
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
                 "context_lines_max": max(packets.values()) if packets else 0,
                 "lint": {"errors": lint.get("errors"), "warnings": lint.get("warnings")},
                 "roadmap": [(r["id"], r["derived"]) for r in facts["roadmap"]],
                 "hook_events": sum(t.get("hook_events", 0) for t in turns),
                 "guard_tool_errors": guard_hits[:10], "oracle_prompts_approved": oracle_prompts[:20],
                 "session_init": (turns[0].get("session_init") if turns else None), "dt": str(DT)}}
(run / "grading.json").write_text(json.dumps(out, indent=1))
print(f"{tid}: {passed}/{len(R)}")
for r in R:
    print(("PASS " if r["passed"] else "FAIL ") + f"[{r['id']}] " + r["text"] + "  — " + r["evidence"][:160])
