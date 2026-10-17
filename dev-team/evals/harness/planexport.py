#!/usr/bin/env python3
"""The plan map's data: `<run>/flow/plan.json` (schema `plan-map/1`), one plan snapshot per turn that changed the plan
(design/interface-first-design.md §8.2–8.3). workflow-analyzer's `planmap.write` draws it.

For each `turn N` commit of the run's project (driver.py commits one per turn), a turn whose commit leaves `docs/`
and `tasks/` as they were is recorded as `{"turn": N, "same_as": <last changed turn>}`. Any other turn's snapshot
comes from, in order:
1. the snapshot driver.py kept right after that turn (`<run>/plans/T<nnn>.json`, when its commit matches);
2. the run's own dt snapshot run on that commit, extracted with `git archive` into a temp dir (the run's
   project is never checked out): `dt plan --json` when that dt has it, else built here from dtprobe facts
   with the same node levels, edge kinds and builds.
A snapshot identical to the last one is also recorded as `same_as`.

Usage: planexport.py <run-dir> [--out <dir>]   (default out: <run-dir>/flow; prints the plan.json path)
"""
import argparse, hashlib, io, json, pathlib, re, shutil, subprocess, sys, tarfile, tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dtrun  # noqa: E402

SCHEMA = "plan-map/1"
LEVELS = ["stage", "milestone", "task", "pipeline", "step", "test", "type", "symbol"]


def digest(obj):
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:12]


def node(id_, level, parent, title, attrs, expects=None):
    expects = expects or {}
    return {"id": id_, "level": level, "parent": parent or "", "title": title, "hash": digest([title, attrs, expects]),
            "attrs": attrs, "expects": expects}


def from_probe(f):
    """A plan-map snapshot body built from dtprobe facts (for dt snapshots that have no `dt plan --json`)."""
    nodes, edges, builds = [], [], []
    for s in f.get("stages", []):
        nodes.append(node(s["id"], "stage", "", s["name"], {"status": s.get("derived"), "skills": s.get("skills", [])},
                          {"outline": s.get("outline", "")}))
    first_ms = {}
    for r in f.get("roadmap", []):
        nodes.append(node(r["id"], "milestone", r.get("stage", ""), r["name"],
                          {"status": r.get("derived"), "packages": r.get("packages", []), "pipelines": r.get("pipelines", []),
                           "skills": r.get("skills", [])},
                          {"exit": r.get("exit", ""), "outline": r.get("outline", ""), "references": r.get("references", [])}))
        edges += [{"from": r["id"], "to": d, "kind": "depends"} for d in r.get("depends", [])]
        for pid in r.get("pipelines", []):
            first_ms.setdefault(pid, r["id"])
    step_ids = set()
    for p in f.get("pipelines", []):
        nodes.append(node(p["id"], "pipeline", first_ms.get(p["id"], ""), p.get("title", p["id"]),
                          {"package": p.get("package"), "status": p.get("doc_status"), "system": p.get("system", False)},
                          {"entry": p.get("entry", ""), "covers": p.get("covers", [])}))
        for s in p["steps"]:
            sid = f"{p['id']}.{s['name']}"
            step_ids.add(sid)
            nodes.append(node(sid, "step", p["id"], s["name"], {"owner": s.get("owner", "")},
                              {"in": s.get("in_type", ""), "out": s.get("out_type", ""), "spine": s.get("spine", ""),
                               "covers": s.get("covers", [])}))
    for tc in f.get("tests", []):
        nodes.append(node(tc["id"], "test", tc.get("pipeline", ""), tc["title"], {"fixture": tc.get("fixture", "")},
                          {"covers": tc.get("covers", [])}))
        if tc.get("pipeline"):
            edges.append({"from": tc["id"], "to": tc["pipeline"], "kind": "verifies"})
    for s in f.get("symbols", []):
        code = re.findall(r"`([^`]+)`", s.get("text", ""))
        nodes.append(node(s["id"], "type" if s.get("is_type") else "symbol", "", s["title"],
                          {"component": s["id"].split(".")[0], "doc": s.get("doc", "")},
                          {"signature": code[0] if code else "", **{k.lower(): v for k, v in s.get("fields", {}).items()}}))
    for p in f.get("plans", []):
        if not p.get("milestone"):
            continue
        for t in p["tasks"]:
            status = "done" if t.get("done") else "blocked" if t.get("blocked") else "todo"
            nodes.append(node(t["id"], "task", p["milestone"], t["title"],
                              {"kind": t.get("kind", ""), "size": t.get("size", ""), "mode": t.get("mode", ""),
                               "package": t.get("package", ""), "step": t.get("step", ""), "status": status},
                              {"acceptance": t.get("acceptance", []), "verify": t.get("verify", []),
                               "reads": t.get("reads", t.get("read", [])), "writes": t.get("writes", []),
                               "tests": [i for i in t.get("reads", t.get("read", [])) if i.startswith("TC-")],
                               "covers": t.get("covers", [])}))
            edges += [{"from": t["id"], "to": d, "kind": "depends"} for d in t.get("depends_on", [])]
            if t.get("step") in step_ids:
                edges.append({"from": t["id"], "to": t["step"], "kind": "implements"})
            elif re.fullmatch(r"PL-\d{2,}", t.get("step", "")):
                edges.append({"from": t["id"], "to": t["step"], "kind": "implements"})
        for r in p.get("graph", []):
            e = {"from": r["from"], "to": r["to"], "kind": r["kind"], "mitigated_by": r["mitigated_by"]}
            if r.get("reason"):
                e["reason"] = r["reason"]
            edges.append(e)
        gm = dtrun.graph_metrics(p["tasks"])
        builds.append({"milestone": p["milestone"], "state": "active" if p["kind"] == "plan" else "queued",
                       "critical_path": gm["critical_path_ids"], "waves": gm["waves"]})
    return {"nodes": nodes, "edges": edges, "builds": builds}


def snapshot_body(proj, dt, facts=None):
    """`dt plan --json` when this dt has it, else the body built from dtprobe facts (`source` says which)."""
    rc, out, _ = dtrun.run(proj, "plan", "--json", dt=dt)
    try:
        d = json.loads(out)
        if rc == 0 and isinstance(d, dict) and "nodes" in d:
            d.pop("schema", None)
            return {**d, "source": "dt plan --json"}
    except Exception:
        pass
    f = facts if facts is not None else dtrun.probe(proj, dt)
    return {**from_probe(f), "source": "dtprobe"}


def dt_version(dt):
    pj = pathlib.Path(dt).parent.parent / ".claude-plugin" / "plugin.json"
    try:
        return json.loads(pj.read_text()).get("version", "?")
    except (OSError, json.JSONDecodeError):
        return "?"


def git(proj, *a, **kw):
    return subprocess.run(["git", *a], cwd=proj, capture_output=True, **kw)


def turn_commits(proj):
    out = git(proj, "log", "--reverse", "--format=%H%x09%cI%x09%s", text=True).stdout
    res = []
    for line in out.splitlines():
        sha, ts, subj = (line.split("\t", 2) + ["", ""])[:3]
        m = re.fullmatch(r"turn (\d+)", subj)
        if m:
            res.append((int(m.group(1)), sha, ts))
    return res


def body_at(proj, sha, dt):
    """The snapshot body of one commit, from a `git archive` copy in a temp dir."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="planexport-"))
    try:
        tar = git(proj, "archive", "--format=tar", sha).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
            try:
                tf.extractall(tmp, filter="data")
            except TypeError:  # Python before 3.12 has no extraction filters
                tf.extractall(tmp)
        return snapshot_body(tmp, dt)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def turn_skills(run):
    try:
        turns = json.loads((run / "turns.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    out = {}
    for t in turns:
        own = [dtrun.skill_name(s) for s in t.get("skills", []) if str(s).startswith("dev-team")] or \
              [dtrun.skill_name(s) for s in t.get("skills", [])]
        out[int(t["turn"])] = own[-1] if own else ""
    return out


def export(run, out=None):
    """Write <out>/plan.json for one run folder; returns its path (None when the run has no project repo)."""
    run = pathlib.Path(run).resolve()
    proj = run / "project"
    if not (proj / ".git").exists():
        return None
    out = pathlib.Path(out) if out else run / "flow"
    out.mkdir(parents=True, exist_ok=True)
    dt = dtrun.dt_path(run)
    skills = turn_skills(run)
    snaps, prev_sha, last_turn, last_digest, source = [], None, None, None, set()
    for n, sha, ts in turn_commits(proj):
        if n == 0:
            prev_sha = sha
            continue
        unchanged = prev_sha is not None and git(proj, "diff", "--quiet", prev_sha, sha, "--", "docs", "tasks").returncode == 0
        prev_sha = sha
        if unchanged and last_turn is not None:
            snaps.append({"turn": n, "same_as": last_turn})
            continue
        kept = run / "plans" / f"T{n:03d}.json"
        body = None
        if kept.exists():
            try:
                k = json.loads(kept.read_text())
                body = k["body"] if k.get("commit") == sha else None
            except (OSError, json.JSONDecodeError, KeyError):
                body = None
        body = body or body_at(proj, sha, dt)
        source.add(body.pop("source", "?"))
        d = digest([body.get("nodes"), body.get("edges"), body.get("builds")])
        if d == last_digest and last_turn is not None:
            snaps.append({"turn": n, "same_as": last_turn})
            continue
        body.pop("producer", None)
        snaps.append({"turn": n, "commit": sha, "ts": ts, "skill": skills.get(n, ""), **body})
        last_turn, last_digest = n, d
    doc = {"schema": SCHEMA, "producer": f"dev-team planexport (dt {dt_version(dt)}; {', '.join(sorted(source)) or 'no snapshots'})",
           "levels": LEVELS, "snapshots": snaps}
    path = out / "plan.json"
    path.write_text(json.dumps(doc, indent=1))
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--out")
    a = ap.parse_args()
    path = export(pathlib.Path(a.run), a.out)
    if path is None:
        sys.exit(f"planexport: {a.run} has no project/ git repo")
    print(path)


if __name__ == "__main__":
    main()
