#!/usr/bin/env python3
"""Facts the grader needs that `dt`'s CLI doesn't print as JSON, read through dt's own parser.

Runs against a given dt scripts/ folder (the plugin snapshot a trajectory used), so grading and the
run see the same parser. Prints one JSON object.

Interface-first fields (task `kind` and `writes`, the `## Dependency graph` rows, step In/Out types, contract
type sections) come from dt's parser when it has them (`Task.kind`, `Task.writes`, `model.graph_edges`) and
are read from the raw task fields and tables otherwise, so old snapshots and new ones give the same facts.
dt's own graph numbers (`devteam.graph`) are reported beside them as `dt_graph`, only for the grader's
cross-check: the grader works the graph out itself. Probes (design/probes.md §4) are the same: `probes` and
`decisions` come from the harness's own parse (probefacts.py), and dt's probes parser, once it has one, is
reported beside them as `dt_probes`.

`requests` is docs/requests.md read through dt's own parser (None for a dt that keeps no record); with
`--requests-history`, `requests_history` is the same parse at every commit that touched it.

Usage: dtprobe.py <scripts-dir> <project-dir> [--requests-history]
"""
import json, pathlib, re, subprocess, sys

sys.path.insert(0, sys.argv[1])
sys.path.insert(1, str(pathlib.Path(__file__).resolve().parent))
import dtrun, probefacts  # noqa: E402
from devteam import md, model  # noqa: E402
from devteam.repo import Repo  # noqa: E402
from devteam.commands import roadmap as roadmap_cmd  # noqa: E402

try:  # dt's status internals move between versions; fall back to the §5.4 step 7 rule they implement.
    from devteam.status.build_planning import expected_mode  # noqa: E402
except ImportError:
    try:
        from devteam.commands.status import _expected_mode as expected_mode  # noqa: E402
    except ImportError:
        def expected_mode(t):
            if t.is_spine:
                return "solo"
            return "split" if t.covers or any(i.startswith("TC-") for i in t.read) else "solo"
try:  # waves, critical path and ready set (interface-first dt); absent before it.
    from devteam import graph as dt_graph_mod  # noqa: E402
except ImportError:
    dt_graph_mod = None

PATHLIKE = re.compile(r"\.(py|md|json|csv|toml|ya?ml|txt|parquet|ts|tsx|js|sh|ipynb|html)$")
EDGE_KINDS = ("data", "call", "file", "code", "contract-change", "order")


def symbol_ids(text):
    """Contract-symbol-like IDs (`stats.Cov`, `quant.load_prices`) in text, file names left out."""
    return list(dict.fromkeys(s for s in re.findall(rf"\b{md.SYMBOL_ID}\b", text or "") if not PATHLIKE.search(s)))


def task_kind(t):
    k = getattr(t, "kind", None)
    if isinstance(k, str):
        return k
    v = md.strip_md(t.get("Kind")).lower()
    return v.split()[0] if v else ""


def task_writes(t):
    w = getattr(t, "writes", None)
    if isinstance(w, list):
        return w
    raw = t.get("Writes")
    return [s.strip("`") for s in md.split_list(raw)] if raw else list(t.files_likely)


def graph_rows(doc):
    """The plan's `## Dependency graph` rows: {from, to, kind, mitigated_by, reason, line}."""
    if hasattr(model, "graph_edges"):
        try:
            return [{"from": e.src, "to": e.dst, "kind": e.kind, "mitigated_by": e.mitigated_by,
                     "reason": e.reason, "line": getattr(e, "line", None)} for e in model.graph_edges(doc)]
        except Exception:  # an early dt-core may still be settling; read the table ourselves
            pass
    h = next((h for h in doc.headings if h.level == 2 and h.text.lower().startswith("dependency graph")), None)
    if not h:
        return []
    out = []
    for _, head, rows in doc.tables(h.line + 1, h.end):
        if not any(c.lower() == "from" for c in head):
            continue
        for n, row in md.table_dicts(head, rows):
            col = lambda name: next((v for k, v in row.items() if k.lower().startswith(name)), "")
            first = lambda cell: (re.findall(md.TASK_ID, cell) or [""])[0]
            mit = col("mitigat").replace("`", "").strip()
            none = re.match(r"\s*none\b\s*:?\s*(.*)$", mit, re.I | re.S)
            out.append({"from": first(col("from")), "to": first(col("to")), "kind": md.strip_md(col("kind")).lower(),
                        "mitigated_by": "" if none else mit, "reason": none.group(1).strip() if none else "",
                        "line": n + 1})
    return out


def split_io(s):
    io = getattr(s, "io", "") or ""
    parts = re.split(r"\s*(?:→|->)\s*", md.strip_md(io), maxsplit=1)
    return (getattr(s, "in_type", None) or parts[0].strip(),
            getattr(s, "out_type", None) or (parts[1].strip() if len(parts) > 1 else ""))


def plan_facts(doc, done):
    scope = md.fields_in(doc.lines, 0, len(doc.lines))
    tasks = model.tasks(doc)
    kinds = {t.id: task_kind(t) for t in tasks}
    iface = [t for t in tasks if kinds[t.id] == "interface" or (not kinds[t.id] and getattr(t, "is_contract", False))]
    declared = set()
    for t in iface:
        declared |= set(symbol_ids(t.text))
    facts = []
    for t in tasks:
        reads = [md.strip_md(i).split(" (")[0] for i in t.read]
        read_syms = [i for i in reads if re.fullmatch(md.SYMBOL_ID, i) and not PATHLIKE.search(i)]
        want = expected_mode(t)
        facts.append({
            "id": t.id, "title": t.title, "phase": t.phase, "is_spine": t.is_spine,
            "spine_pipeline": model.spine_pipeline(t), "package": t.package, "step": t.step,
            "kind": kinds[t.id], "size": t.size, "mode": t.mode, "expected_mode": want,
            # Split is fine for a task whose symbols a frozen interface declares (the tester writes against it).
            "mode_ok": t.mode == want or (t.mode == "split" and bool(read_syms) and set(read_syms) <= declared),
            "reason": md.strip_md(t.get("Reason")), "read": t.read, "reads": reads, "read_symbols": read_syms,
            "files_likely": t.files_likely, "writes": task_writes(t), "depends_on": t.depends_on,
            "declared": {"Kind": "Kind" in t.fields, "Writes": "Writes" in t.fields},
            "parallel": t.parallel, "covers": t.covers, "blocked": t.blocked, "skills": getattr(t, "skills", []),
            "acceptance": [c.text for c in t.acceptance], "verify": t.verify, "done": done.get(t.id, False),
            "lines": t.end - t.start})
    dtg = None
    if dt_graph_mod is not None:
        try:
            dtg = {"waves": dt_graph_mod.waves(tasks), "critical_path": dt_graph_mod.critical_path(tasks),
                   "width": dt_graph_mod.width(tasks), "ready_fresh": dt_graph_mod.ready(tasks, set())}
        except Exception as e:  # report, never fail the probe
            dtg = {"_error": repr(e)[:200]}
    return {
        "doc": doc.rel, "kind": doc.kind, "status": doc.status, "lines": len(doc.lines),
        "milestone": roadmap_cmd._plan_milestone(doc), "dev_team": model.is_dev_team_plan(doc),
        "covers": md.expand_refs(scope.get("Covers", "")), "deferred": md.expand_refs(scope.get("Deferred", "")) + dtrun.named_steps(scope.get("Deferred", "")),
        "tasks": facts, "graph": graph_rows(doc), "interface_tasks": [t.id for t in iface],
        "interface_symbols": sorted(declared), "dt_graph": dtg,
    }


def depends_ids(ms):
    """A milestone's Depends IDs: dt's own `Milestone.depends` when it has one, else the same `\\bM\\d+\\b` read."""
    d = getattr(ms, "depends", None)
    return list(d) if isinstance(d, (list, tuple)) else dtrun.depends_cell(md.strip_md(ms.row.get("Depends", "")))[0]


def symbol_facts(doc):
    out = []
    for s in model.symbols(doc):
        body = md.bullet_fields(doc.lines, s.start + 1, s.end)
        last = s.id.split(".")[-1]
        kind = getattr(s, "kind", None)
        is_type = kind == "type" if isinstance(kind, str) and kind else (
            s.title.strip().lower().startswith("type") or last[:1].isupper())
        out.append({"id": s.id, "title": s.title, "doc": doc.rel, "is_type": is_type,
                    "fields": {k: md.strip_md(v) for k, v in body.items()},
                    "text": "\n".join(doc.lines[s.start:s.end]), "lines": s.end - s.start})
    return out


repo = Repo(sys.argv[2])
live, removed = set(), set()
if repo.spec:
    for d in repo.spec.definitions():
        if d.how == "requirement":
            (removed if d.retired else live).add(d.id)
live -= removed

todo = model.todo_state(repo)
plans = [plan_facts(d, todo if d.kind == "plan" else {}) for d in sorted(repo.docs("plan", "queued-plan"), key=lambda d: d.rel)]
pipelines = []
for p in model.all_pipelines(repo):
    steps = []
    for s in p.steps:
        it, ot = split_io(s)
        steps.append({"name": s.name, "owner": s.owner, "covers": s.covers, "in_type": it, "out_type": ot,
                      "spine": md.strip_md(s.spine)})
    pipelines.append({"id": p.id, "title": p.title, "doc": p.doc.rel, "doc_status": p.doc.status, "system": p.is_system,
                      "package": p.package, "covers": p.covers, "entry": p.entry, "entry_file": p.entry_file,
                      "steps": steps})
symbols = [s for d in sorted(repo.docs("contract"), key=lambda d: d.rel) for s in symbol_facts(d)]
tests = [{"id": tc.id, "title": tc.title, "doc": d.rel, "pipeline": tc.pipeline, "fixture": tc.fixture,
          "covers": tc.covers, "step": md.strip_md(tc.fields.get("Step", ""))}
         for d in sorted(repo.docs("tests"), key=lambda d: d.rel) for tc in model.test_cases(d)]
rows, stage_rows = [], []
if repo.roadmap:
    # Stages (dt versions before stages have none): a milestone's source, skills and references fall back to its stage's.
    for st in (model.stages(repo.roadmap) if hasattr(model, "stages") else []):
        stage_rows.append({"id": st.id, "name": st.name, "source": md.strip_md(st.source), "skills": st.skills,
                           "outline": md.strip_md(st.fields.get("Outline", "")),
                           "derived": roadmap_cmd.stage_status(repo, st)})
    for ms in model.milestones(repo.roadmap):
        stage = getattr(ms, "stage_of", None)
        rows.append({"id": ms.id, "name": ms.name, "source": md.strip_md(ms.source), "packages": ms.packages,
                     "pipelines": ms.pipelines, "derived": roadmap_cmd.milestone_status(repo, ms),
                     "skills": getattr(ms, "skills", []), "outline": md.strip_md(ms.fields.get("Outline", "")),
                     "exit": md.strip_md(ms.fields.get("Exit", "")),
                     "stage": stage.id if stage else "", "stage_name": stage.name if stage else "",
                     "stage_outline": md.strip_md(stage.fields.get("Outline", "")) if stage else "",
                     "references": (model.milestone_references(repo, ms.id) if hasattr(model, "milestone_references") else []),
                     # IDs as dt reads them (`ms.depends`), the skill's `M1 (stats.Cov, PL-01 output)` note kept
                     # apart as what each one needs.
                     "depends": depends_ids(ms), "needs": dtrun.depends_cell(md.strip_md(ms.row.get("Depends", "")))[1]})
# docs/references.md entries (dt versions before the references feature have none).
refs = [{"id": r.id, "title": r.title, "file": r.file, "hash": r.hash, "kind": r.kind, "milestones": r.milestones}
        for r in (model.all_references(repo) if hasattr(model, "all_references") else [])]


def dt_probes(repo):
    """dt's own parse of docs/probes.md (`model.all_probes` / `model.probes`), or None before dt has one."""
    fn = getattr(model, "all_probes", None)
    try:
        items = fn(repo) if fn else None
        if items is None and hasattr(model, "probes") and getattr(repo, "probes", None) is not None:
            items = model.probes(repo.probes)
        if items is None:
            return None
        return [{"id": getattr(e, "id", ""), "status": md.strip_md(str(getattr(e, "status", "") or "")),
                 "folder": str(getattr(e, "folder", "") or ""), "hash": str(getattr(e, "hash", "") or ""),
                 "checks": [getattr(c, "id", str(c)) for c in (getattr(e, "checks", None) or [])]} for e in items]
    except Exception as ex:  # report, never fail the probe
        return {"_error": repr(ex)[:200]}


root = pathlib.Path(sys.argv[2])
try:  # docs/requests.md (design/requests.md); absent before dt kept a record of the user's words.
    from devteam import requests as dt_requests  # noqa: E402
    from devteam.repo import Doc  # noqa: E402
except ImportError:
    dt_requests = None


def requests_at(text):
    """docs/requests.md as dt's own parser reads it (`devteam.requests.parse`): its UR lines and the ones that don't parse."""
    reqs, bad = dt_requests.parse(Doc(root, dt_requests.PATH, text))
    return reqs, [{"id": b.id, "line": b.line + 1, "message": b.message} for b in bad]


def requests_facts():
    """The record now, with dt's open/traced state per line; None when the run's dt keeps no record."""
    if dt_requests is None:
        return None
    path = root / dt_requests.PATH
    if not path.exists():
        return {"present": False, "requests": [], "bad": []}
    try:
        reqs, bad = requests_at(path.read_text(encoding="utf-8"))
        return {"present": True, "bad": bad,
                "requests": [{"id": r.id, "line": r.line + 1, "owner": r.owner, "words": r.words, "about": r.about,
                              "skill": r.skill, "date": r.date, "trace": r.trace, "state": r.state,
                              "open": dt_requests.is_open(repo, r)} for r in reqs]}
    except Exception as ex:  # report, never fail the probe
        return {"present": True, "_error": repr(ex)[:200], "requests": [], "bad": []}


def requests_history():
    """{sha, present, words: {UR id: words}, bad: [UR id]} at every commit that touched docs/requests.md, oldest first."""
    if dt_requests is None:
        return []
    git = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, text=True)
    out = []
    for sha in git("log", "--reverse", "--format=%H", "--", dt_requests.PATH).stdout.split():
        shown = git("show", f"{sha}:{dt_requests.PATH}")
        if shown.returncode:
            out.append({"sha": sha, "present": False, "words": {}, "bad": []})
            continue
        reqs, bad = requests_at(shown.stdout)
        out.append({"sha": sha, "present": True, "words": {r.id: r.words for r in reqs}, "bad": [b["id"] for b in bad]})
    return out


pb_text = (root / "docs" / "probes.md").read_text(errors="ignore") if (root / "docs" / "probes.md").exists() else ""
probe_doc = probefacts.parse_probes(pb_text)
decision_list = []
for rel in ["docs/architecture.md", *sorted(str(p.relative_to(root)) for p in root.glob("docs/packages/*/architecture.md"))]:
    if (root / rel).exists():
        decision_list += [{**{k: v for k, v in d.items() if k != "text"}, "doc": rel}
                          for d in probefacts.decisions((root / rel).read_text(errors="ignore"))]
print(json.dumps({
    "live_spec": sorted(live), "removed_spec": sorted(removed),
    "pipelines": pipelines, "plans": plans, "roadmap": rows, "stages": stage_rows, "references": refs,
    "symbols": symbols, "tests": tests,
    "docs": {d.rel: d.status for d in sorted(repo.docs(), key=lambda d: d.rel)},
    "packages": repo.packages(),
    "probes": [{k: v for k, v in e.items() if k != "text"} for e in probe_doc["entries"]],
    "probes_retired": probe_doc["retired"], "decisions": decision_list, "dt_probes": dt_probes(repo),
    "requests": requests_facts(), "requests_history": requests_history() if "--requests-history" in sys.argv[3:] else [],
}))
