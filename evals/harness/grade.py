#!/usr/bin/env python3
"""Programmatic grading of one trajectory run dir (…/with_skill). Writes grading.json there.

Assertions are shared across incremental and all-at-once so the two modes are comparable.
"""
import json, re, subprocess, sys, pathlib

run = pathlib.Path(sys.argv[1]).resolve()
proj = run / "project"
docs = proj / "docs"
turns = json.loads((run / "turns.json").read_text())
summary = json.loads((run / "summary.json").read_text()) if (run / "summary.json").exists() else {}
tid = run.parent.name
project = tid.split("-")[0]
mode = "incremental" if "incremental" in tid else "all_at_once"

R = []
def check(text, passed, evidence):
    R.append({"text": text, "passed": bool(passed), "evidence": str(evidence)[:600]})

def read(p):
    p = docs / p
    return p.read_text() if p.exists() else ""

def status(txt):
    m = re.search(r"\*\*Status:\*\*\s*([A-Za-z]+)", txt)
    return m.group(1) if m else None

def git(*a):
    return subprocess.run(["git", *a], cwd=proj, capture_output=True, text=True).stdout

brief, spec, arch = read("brief.md"), read("spec.md"), read("architecture.md")
pkg_docs = sorted((docs / "architecture").glob("*.md")) if (docs / "architecture").is_dir() else []
arch_all = arch + "\n".join(p.read_text() for p in pkg_docs)
ideas = sorted((docs / "ideas").glob("*.md")) if (docs / "ideas").is_dir() else []
all_docs = "\n".join([brief, spec, arch_all] + [p.read_text() for p in ideas])

# ---- completion
check("Trajectory finished: simulated user reached the final stage and signed off", summary.get("finished"),
      f"turns={summary.get('turns')} stages_reached={summary.get('stages_reached')}")
check("Brief, spec and architecture all end Accepted/Approved",
      status(brief) == "Accepted" and status(spec) == "Approved" and status(arch) == "Approved",
      f"brief={status(brief)} spec={status(spec)} arch={status(arch)}")

# ---- brief quality
bw = len(re.sub(r"[#*`|>-]", " ", brief).split())
check("Brief stays about one page (<= 500 words)", 0 < bw <= 500, f"{bw} words")
gsec = re.search(r"## Goals\n(.*?)(\n## |\Z)", brief, re.S)
goals = re.findall(r"^\s*(\d+)\.", gsec.group(1), re.M) if gsec else []
check("Brief has 3-5 numbered goals", 3 <= len(goals) <= 5, f"goals={goals}")
check("Brief has a Not doing list with items", bool(re.search(r"## Not doing\n+\s*- ", brief)), "section present" if "## Not doing" in brief else "missing")

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
check("Every live spec requirement has a Given/When/Then criterion (QR-: a how-checked line)", reqs and not no_gwt,
      f"{len(reqs)} reqs; missing GWT: {no_gwt[:15]}")
dups = sorted({r for r in reqs if reqs.count(r) > 1})
check("Spec requirement IDs are unique", reqs and not dups, f"duplicates: {dups}")
vendors = r"\b(yfinance|yahoo|polygon|alpaca|quandl|nasdaq data link|sharadar|tiingo|crsp|wrds|pytorch|torch|numpy|pandas|scikit|sklearn|gymnasium|gym\b|pygame|stable[- ]baselines|sb3|tensorflow|jax|lightgbm|xgboost|parquet|duckdb|sqlite|postgres)"
spec_body = re.split(r"## Changelog", spec)[0]
hits = sorted({h.lower() for h in re.findall(vendors, spec_body, re.I)})
check("Spec names no vendors, libraries, or storage tech", not hits, f"found: {hits}")
if project == "quant":
    check("Spec has DATA- requirements", bool(re.search(r"\*\*DATA-\d{2}\*\*", spec)), "")
model_reqs = [b for b in req_blocks if re.search(r"(learn|model|agent|forecast|predict|portfolio|feature)", b, re.I)]
check("Learning/model criteria name a baseline to beat", bool(re.search(r"baseline|random (agent|policy)|scripted|equal[- ]weight|beats?", spec, re.I)),
      f"{len(re.findall(r'baseline', spec, re.I))} 'baseline' mentions")

# ---- architecture
try:
    st = json.loads(subprocess.run(["python3", str(proj / ".claude/skills/architecture-design/scripts/arch-status.py"), "docs", "."],
                                   cwd=proj, capture_output=True, text=True).stdout)
except Exception as e:
    st = {"uncovered": ["<error>"], "stale": [], "architecture": {}}
check("Architecture covers every live spec requirement (arch-status uncovered = 0)", arch and not st.get("uncovered"),
      f"uncovered: {st.get('uncovered', [])[:20]}")
check("Architecture references no stale/removed spec IDs", arch and not st.get("stale"), f"stale: {st.get('stale', [])[:20]}")
ads = sorted(set(re.findall(r"### (AD-\d{2,})", arch)))
check("Architecture records technical decisions as AD-NN entries (>= 3)", len(ads) >= 3, f"{len(ads)} decisions")
check("Architecture shape is recorded", bool(re.search(r"\*\*Shape:\*\*", arch)), (st.get("architecture") or {}).get("shape"))

# ---- history integrity (applies to both modes: all-at-once docs also get revised)
log = git("log", "--reverse", "--format=%H %s")
commits = [l.split(" ", 1) for l in log.strip().splitlines()]
ever_req, ever_ad, ever_goal1 = set(), set(), None
for h, _ in commits:
    s = git("show", f"{h}:docs/spec.md") if "docs/spec.md" in git("ls-tree", "-r", "--name-only", h) else ""
    ever_req |= set(re.findall(r"\*\*([A-Z][A-Z0-9]*-\d{2,})\*\*", s))
    a = git("show", f"{h}:docs/architecture.md") if "docs/architecture.md" in git("ls-tree", "-r", "--name-only", h) else ""
    ever_ad |= set(re.findall(r"### (AD-\d{2,})", a))
lost_req = sorted(ever_req - set(re.findall(r"\*\*([A-Z][A-Z0-9]*-\d{2,})\*\*", spec)))
lost_ad = sorted(ever_ad - set(ads))
check("No spec requirement ID ever disappeared (removed ones struck through, not deleted)", not lost_req, f"lost: {lost_req[:20]}")
check("No architecture decision ever deleted (superseded instead)", not lost_ad, f"lost: {lost_ad}")
cl = len(re.findall(r"^\|\s*\d{4}-\d{2}-\d{2}", re.split(r"## Changelog", spec)[-1], re.M)) if "## Changelog" in spec else 0
check("Spec changelog exists with >= 1 row per planning round", cl >= (summary.get("stages_reached", 1) if mode == "incremental" else 1), f"{cl} rows")

# ---- gates: one layer per turn; approvals only after the user approves
def kinds_changed(turn_no):
    stat = git("show", "--numstat", "--format=", commits[turn_no][0])
    ks = set()
    for line in stat.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or not parts[0].isdigit():
            continue
        add, path = int(parts[0]), parts[2]
        if add < 12:  # status flips, small fixes
            continue
        k = "brief" if path.endswith("brief.md") or "/ideas/" in path else "spec" if path.endswith("spec.md") else "arch" if "architecture" in path else None
        if k:
            ks.add(k)
    return ks
multi = []
for i in range(1, len(commits)):
    ks = kinds_changed(i)
    if len(ks) > 1:
        multi.append((i, sorted(ks)))
check("Gate discipline: no turn drafts two layers (brief/idea, spec, architecture) at once", not multi, f"turns: {multi[:10]}")

APPROVE = re.compile(r"\b(accept|accepted|approve|approved|looks good|lgtm|go ahead|yes)\b", re.I)
bad = []
prev = {}
for t in turns:
    cur = dict(l.split(": ", 1) for l in t["status"].splitlines() if ": " in l)
    for f, v in cur.items():
        s_now = v.split(" (")[0]
        s_prev = prev.get(f, "").split(" (")[0]
        if s_now in ("Accepted", "Approved", "Specced") and s_prev not in ("Accepted", "Approved", "Specced") and s_now != "Specced":
            if not APPROVE.search(t["user"]):
                bad.append((t["turn"], f))
    prev = cur
check("Docs only flip to Accepted/Approved in a turn where the user approved", not bad, f"violations: {bad[:10]}")
skills_used = sorted({s for t in turns for s in t["skills"]})
check("All three planning skills were invoked", {"idea-refine", "spec-writing", "architecture-design"} <= set(skills_used), f"used: {skills_used}")

# ---- project-specific
if project == "quant":
    check("Plan hands feature testing to the null-hypothesis-testing skill by name", "null-hypothesis-testing" in all_docs,
          f"mentions: {all_docs.count('null-hypothesis-testing')}")
    near = re.search(r"null-hypothesis-testing.{0,400}(feature|information gain|signal)|(feature|information gain|signal).{0,400}null-hypothesis-testing", all_docs, re.S | re.I)
    check("null-hypothesis-testing is named at the features / information-gain step", bool(near), near.group(0)[:200] if near else "")
    check("Spec guards look-ahead and survivorship bias as testable requirements",
          bool(re.search(r"look[- ]ahead|published after|known (on|as of)|point[- ]in[- ]time", spec, re.I)) and bool(re.search(r"delist|survivorship", spec, re.I)), "")
    check("Spec covers PCA market-mode removal and Marchenko–Pastur denoising",
          bool(re.search(r"\bPCA\b|principal component|eigenvector|top factors|market (factor|mode)", spec, re.I)) and bool(re.search(r"Marchenko|random[- ]matrix|noise band|pure noise", spec, re.I)), "")
    check("Classical portfolios (min-variance / risk parity / HRP) are specified",
          bool(re.search(r"min(imum)?[- ]variance", spec, re.I)) and bool(re.search(r"risk parity", spec, re.I)), "")
    m = re.search(r"(PPO|agent|forecast[- ]driven|ML[- ]driven).{0,600}(min(imum)?[- ]variance|classical|HRP|risk parity)", spec, re.S | re.I)
    check("ML/PPO portfolios must beat the classical portfolios out of sample", bool(m), m.group(0)[:200] if m else "")
    check("Real-money / live trading is explicitly out of scope", bool(re.search(r"(Out of scope|Not doing).{0,1500}(live|real[- ]money|brokerage)", brief + spec, re.S | re.I)), "")
    check("Out-of-sample / held-out evaluation is required for features and models",
          len(re.findall(r"out[- ]of[- ]sample|held[- ]out|walk[- ]forward", spec, re.I)) >= 3, f"{len(re.findall(r'out[- ]of[- ]sample|held[- ]out|walk[- ]forward', spec, re.I))} mentions")
else:
    for env, pat in [("snake", r"snake"), ("fish", r"fish|tank|ball"), ("foraging", r"forag|predator|prey")]:
        check(f"Spec covers the {env} environment", bool(re.search(pat, spec, re.I)), "")
    check("Architecture has a shared core reused by all environments", bool(re.search(r"(shared|common|core)", arch_all, re.I)) and bool(re.search(r"interface|protocol|abc|class", arch_all, re.I)), "")
    check("Each environment's learning criterion beats a random or scripted baseline",
          len(re.findall(r"random|scripted|heuristic", spec, re.I)) >= 3, f"{len(re.findall(r'random|scripted|heuristic', spec, re.I))} mentions")
    check("CPU training-time budget (~1 hour) is a quality requirement", bool(re.search(r"(hour|60 min|minutes).{0,120}(CPU|laptop)|(CPU|laptop).{0,120}(hour|60 min|minutes)", spec, re.I)), "")
    check("Proof-of-concept stays single package (no premature monorepo)", "Single" in ((st.get("architecture") or {}).get("shape") or ""), (st.get("architecture") or {}).get("shape"))

passed = sum(r["passed"] for r in R)
tools = {}
for t in turns:
    for x in t["tools"]:
        tools[x] = tools.get(x, 0) + 1
out = {"expectations": R,
       "summary": {"passed": passed, "failed": len(R) - passed, "total": len(R), "pass_rate": round(passed / len(R), 3)},
       "execution_metrics": {"tool_calls": tools, "total_tool_calls": sum(tools.values()), "total_steps": len(turns),
                             "errors_encountered": sum(1 for t in turns if t["assistant"].startswith("[agent error")),
                             "output_chars": len(all_docs)},
       "timing": {"executor_duration_seconds": summary.get("total_seconds"), "total_duration_seconds": summary.get("total_seconds")},
       "extra": {"turns": len(turns), "cost_usd": round(max((t["usage"].get("cost_usd") or 0) for t in turns), 2),
                 "output_tokens": sum(((t["usage"].get("usage") or {}).get("output_tokens") or 0) for t in turns),
                 "agent_seconds": round(sum(t["seconds"] for t in turns)),
                 "final_words": {k: len(v.split()) for k, v in [("brief", brief), ("spec", spec), ("architecture", arch_all)]}, "skills_used": skills_used,
                 "ideas": [p.name for p in ideas], "package_docs": [p.name for p in pkg_docs],
                 "spec_reqs": len(reqs), "decisions": len(ads), "brief_words": bw}}
(run / "grading.json").write_text(json.dumps(out, indent=1))
print(f"{tid}: {passed}/{len(R)}")
for r in R:
    print(("PASS " if r["passed"] else "FAIL ") + r["text"] + "  — " + r["evidence"][:140])
