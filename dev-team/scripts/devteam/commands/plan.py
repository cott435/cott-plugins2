"""The plan as one snapshot for workflow-analyzer's plan map (`plan-map/2`, interface-first-design.md §8.3): goals,
stages, features, requirements, milestones, tasks, pipelines, steps, test cases, contract types and symbols, the
edges between them, and per planned milestone the build graph (waves, critical path)."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .. import graph, md, model
from .roadmap import _plan_milestone, active_plan, source_ids

SCHEMA = "plan-map/2"
LEVELS = ["goal", "stage", "feature", "requirement", "milestone", "task", "pipeline", "step", "test", "type", "symbol"]


def add_arguments(parser):
    parser.add_argument("--json", action="store_true", help="print the plan-map/2 snapshot body")


def dt_version() -> str:
    manifest = Path(__file__).resolve().parents[3] / ".claude-plugin" / "plugin.json"
    try:
        return json.loads(manifest.read_text(encoding="utf-8")).get("version", "?")
    except (OSError, ValueError):
        return "?"


def _status(row: dict[str, str]) -> str:
    return md.strip_md(next((v for k, v in row.items() if k.lower().startswith("status")), ""))


def _node(id_: str, level: str, parent: str | None, title: str, attrs: dict, expects: dict | None = None) -> dict:
    node = {"id": id_, "level": level, "parent": parent, "title": md.strip_md(title), "attrs": attrs,
            "expects": expects or {}}
    node["hash"] = hashlib.sha1(json.dumps(node, sort_keys=True).encode()).hexdigest()[:12]
    return node


def _plans(repo) -> list[tuple[str, str, list[model.Task]]]:
    """(milestone, state, tasks) for the active plan and each queued plan."""
    out = []
    active = active_plan(repo)
    if active is not None:
        out.append((model.milestone_of(active), "active", model.tasks(active)))
    for d in sorted(repo.docs("queued-plan"), key=lambda d: d.rel):
        mid = _plan_milestone(d)
        if mid and model.is_dev_team_plan(d):
            out.append((mid, "queued", model.tasks(d)))
    return out


def _task_steps(t: model.Task, pipelines: dict[str, model.Pipeline]) -> list[str]:
    """Node IDs a task implements: `PL-02.pca` → that step; `PL-02` → the pipeline."""
    out = []
    for m in re.finditer(r"(PL-\d{2,})(?:\.(\w+))?", t.step):
        if m.group(1) in pipelines:
            out.append(m.group(0))
    return out


def _feature_stages(repo, feats: list[model.Feature], stages: list[model.Stage], milestones: list[model.Milestone],
                    pipelines: dict[str, model.Pipeline]) -> dict[str, tuple[list[str], str]]:
    """code -> (the stages a feature belongs to, how that was found), from the first rule that places it:
    its spec Stage line, else the spec heading that groups it; else the stages whose Source added its
    requirements, earliest first, when Sources tell stages apart; else the stages whose milestones' pipelines
    cover them."""
    ids = [s.id for s in stages]
    added = {s.id: source_ids(repo, s, added_only=True) for s in stages}
    by_source = len({frozenset(v) for v in added.values()}) > 1
    covered: dict[str, set[str]] = {s: set() for s in ids}
    for m in milestones:
        for pid in m.pipelines:
            p = pipelines.get(pid)
            if p and m.stage in covered:
                covered[m.stage] |= set(p.covers).union(*(st.covers for st in p.steps))
    out = {}
    for f in feats:
        reqs = set(f.requirements)
        if f.stage in ids:
            out[f.code] = ([f.stage], f.stage_via)
        elif by_source and (hit := [s for s in ids if reqs & added[s]]):
            out[f.code] = (hit, "stage source")
        elif hit := [s for s in ids if reqs & covered[s]]:
            out[f.code] = (hit, "milestone pipelines")
        else:
            out[f.code] = ([], "")
    return out


def snapshot(repo) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    builds: list[dict] = []
    roadmap = repo.roadmap
    stages = model.stages(roadmap) if roadmap else []
    milestones = model.milestones(roadmap) if roadmap else []
    pipelines = {p.id: p for p in model.all_pipelines(repo)}
    brief = repo.doc("docs/brief.md")
    for g in model.goals(brief) if brief else []:
        nodes.append(_node(g.id, "goal", None, g.text, {}))
    feats, reqs = model.spec_features(repo.spec) if repo.spec else ([], [])
    req_ids = {r.id for r in reqs}
    for s in stages:
        nodes.append(_node(s.id, "stage", None, s.name, {"status": _status(s.row), "source": md.strip_md(s.source)}))
    placed = _feature_stages(repo, feats, stages, milestones, pipelines)
    for f in feats:
        on, via = placed[f.code]
        # Shared pipelines can cover a feature from every stage, so that rule places it only when one stage does.
        parent = on[0] if on and (via != "milestone pipelines" or len(on) == 1) else None
        nodes.append(_node(f.code, "feature", parent, f.name,
                           {"stages": on, "stage_via": via, "source": f.source}))
        edges += [{"from": f.code, "to": g, "kind": "serves"} for g in f.serves]
    for r in reqs:
        nodes.append(_node(r.id, "requirement", r.feature or None, r.text,
                           {} if r.feature else {"section": r.section}, {"criteria": r.criteria}))
    for m in milestones:
        nodes.append(_node(m.id, "milestone", m.stage or None, m.name,
                           {"status": _status(m.row), "packages": m.packages, "pipelines": m.pipelines,
                            "depends": m.depends}))

    def covers(src: str, ids) -> list[dict]:
        return [{"from": src, "to": i, "kind": "covers"} for i in dict.fromkeys(ids) if i in req_ids]

    done = model.todo_state(repo)
    for mid, state, tasks in _plans(repo):
        for t in tasks:
            status = "done" if state == "active" and done.get(t.id) else "blocked" if md.strip_md(t.blocked) else "open"
            nodes.append(_node(t.id, "task", mid, t.title,
                               {"kind": t.kind, "size": t.size, "mode": t.mode, "package": t.package,
                                "step": t.step, "status": status},
                               {"acceptance": [c.text for c in t.acceptance], "verify": t.verify,
                                "reads": [md.strip_md(r) for r in t.read], "writes": t.writes,
                                "tests": [r for r in (md.strip_md(i) for i in t.read) if re.fullmatch(r"TC-\d{2,}", r)],
                                "covers": t.covers}))
            edges += [{"from": t.id, "to": d, "kind": "depends"} for d in t.depends_on]
            edges += [{"from": t.id, "to": s, "kind": "implements"} for s in _task_steps(t, pipelines)]
            edges += covers(t.id, t.covers)
        plan_doc = tasks[0].doc if tasks else None
        if plan_doc is not None:
            edges += [{"from": e.src, "to": e.dst, "kind": e.kind, "mitigated_by": e.mitigated_by, "reason": e.reason}
                      for e in model.graph_edges(plan_doc) if e.src and e.dst]
        builds.append({"milestone": mid, "state": state, "tasks": len(tasks), **graph.metrics(tasks)})

    owner_ms = {}
    for m in milestones:
        for pid in m.pipelines:
            owner_ms.setdefault(pid, m.id)
    for p in pipelines.values():
        nodes.append(_node(p.id, "pipeline", owner_ms.get(p.id), p.title,
                           {"package": p.package or "", "system": p.is_system, "entry": p.entry,
                            "trigger": p.trigger}, {"covers": p.covers}))
        edges += covers(p.id, p.covers)
        for s in p.steps:
            nodes.append(_node(f"{p.id}.{s.name}", "step", p.id, s.name,
                               {"num": md.strip_md(s.num), "owner": s.owner, "in_out": md.strip_md(s.io),
                                "spine": md.strip_md(s.spine)},
                               {"covers": s.covers, "in_types": s.in_types, "out_types": s.out_types}))
            edges += covers(f"{p.id}.{s.name}", s.covers)
    for doc in repo.docs("tests"):
        for tc in model.test_cases(doc):
            nodes.append(_node(tc.id, "test", tc.pipeline or None, tc.title,
                               {"pipeline": tc.pipeline, "fixture": tc.fixture,
                                "kind": md.strip_md(tc.fields.get("Kind", ""))}, {"covers": tc.covers}))
            if tc.pipeline:
                edges.append({"from": tc.id, "to": tc.pipeline, "kind": "verifies"})
            edges += covers(tc.id, tc.covers)
    for sym in model.all_symbols(repo):
        attrs = {"package": sym.package or ""}
        if sym.is_type:
            attrs["sample"] = sym.sample
        nodes.append(_node(sym.id, "type" if sym.is_type else "symbol", None, sym.title, attrs))

    order = {lv: n for n, lv in enumerate(LEVELS)}
    nodes.sort(key=lambda n: order[n["level"]])
    return {"schema": SCHEMA, "producer": f"dt {dt_version()}", "levels": LEVELS,
            "nodes": nodes, "edges": edges, "builds": builds}


def run(args, repo) -> int:
    snap = snapshot(repo)
    if args.json:
        print(json.dumps(snap, indent=2))
        return 0
    counts = {lv: sum(1 for n in snap["nodes"] if n["level"] == lv) for lv in LEVELS}
    print("nodes: " + " · ".join(f"{lv} {n}" for lv, n in counts.items()))
    level = {n["id"]: n["level"] for n in snap["nodes"]}
    on: dict[str, set[str]] = {}
    for e in snap["edges"]:
        if e["kind"] == "covers":
            on.setdefault({"step": "pipeline"}.get(level[e["from"]], level[e["from"]]), set()).add(e["to"])
    if counts["requirement"]:
        print(f"requirements: {counts['requirement']} · " + " · ".join(
            f"{len(on.get(lv, ()))} on a {lv}" for lv in ("pipeline", "test", "task")))
    for b in snap["builds"]:
        print(f"{b['milestone']} ({b['state']}): {b['tasks']} tasks · critical path {len(b['critical_path'])} "
              f"({' → '.join(b['critical_path'])}) · width {b['width']} · parallelism {b['parallelism']}")
        for n, w in enumerate(b["waves"]):
            print(f"  wave {n}: {', '.join(w)}")
    return 0
