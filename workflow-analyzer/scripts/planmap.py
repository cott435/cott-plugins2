#!/usr/bin/env python3
"""Draw the plan a run wrote, from its `plan.json`: how it grew turn by turn, and per milestone
what would be built in parallel and what in series.

`plan.json` (schema `plan-map/2`) sits in a run's workspace beside `index.json`. A producer
(dev-team's `planexport.py`, or anything else) writes it; nothing here knows dev-team:

  {"schema": "plan-map/2", "producer": "...", "levels": ["goal", "stage", "feature", "requirement", ...],
   "snapshots": [{"turn": 14, "commit": "ab12", "ts": "...", "skill": "build-planning",
                  "nodes": [{"id", "level", "parent", "title", "hash", "attrs": {...},
                             "expects": {"acceptance", "verify", "reads", "writes", "tests", ...}}],
                  "edges": [{"from", "to", "kind", "mitigated_by"?, "reason"?}],
                  "builds": [{"milestone", "state", "critical_path", "waves"}]},
                 {"turn": 15, "same_as": 14}]}

Goals, features and requirements are the plan's why: a feature `serves` goals and sits under its stage, a
requirement sits under its feature, and pipelines, steps, tests and tasks `cover` requirements. `plan-map/1`
(no such levels or edges) still draws; its plan has no trace page.

One snapshot per turn that changed the plan. The producer reports state; the diffs are
computed here: a node is added, removed, or changed by its `hash` and fields (title, parent,
attrs, expects, the edges leaving it). A change to `status` alone is hidden unless the page's
"status changes" box is ticked. A node with no `hash`, a snapshot with no `builds`, a plan
with no `levels` or no `kind` on its tasks all still draw.

Pages, all static HTML and inline SVG with no scripts, written into `<out>/plan/`:

  index.html  tiles; a growth strip on the run's turn axis (the skill that wrote the plan, then
              per level the live nodes, added above the line and removed below); a node × turn
              matrix, one collapsible table per level and one column per turn that changed the
              plan (A added, C changed, R removed); and a change ledger.
  trace.html  the final plan from goals to build: goals, stages and their features, the pipelines that
              cover them and the milestones that build those, as columns; then per goal and per feature how
              many requirements a pipeline, a test and a task cover, and each requirement's coverage.
  T<nn>.html  the plan as of that turn as a tree, what it added, changed and removed marked,
              each node's expectations.
  M<n>.html   one milestone's build: columns are waves, lanes are task kinds; interface tasks
              are diamonds whose "unblocks" edges are dashed; a split task is two segments,
              tester then implementer, and the tester waits only on interface tasks; every
              tied critical path is thick; an edge between two wiring tasks that write one entry
              module is orange. Waves are the longest path to each segment; a barycenter
              pass orders each cell. Metrics (waves of segments and of whole tasks; data and
              call edges mitigated; unmitigated rows by why they stay), the producer's own
              numbers beside them, and a thumbnail per turn that changed the graph.

`write(out)` draws them and returns `plan/index.html`, or None when `out/plan.json` is absent
or unreadable. `flow.write_html` calls it, adds a Plan section to `flow.html`, and links each
turn page to the plan as of that turn.

Usage: planmap.py DIR        re-render DIR/plan/ from DIR/plan.json
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import sys
from pathlib import Path

import charts
import flow

SCHEMA = "plan-map/2"
KNOWN = ("plan-map/1", SCHEMA)
LEVELS = ["goal", "stage", "feature", "requirement", "milestone", "task", "pipeline", "step", "test", "type", "symbol"]
KINDS = ["interface", "spine", "wiring", "thicken", "system"]
KIND_COLOR = {"interface": "c6", "spine": "c0", "wiring": "c2", "thicken": "c1", "system": "c3"}
GRAPH_KINDS = ("data", "call", "file", "code", "contract-change", "order")
SIZE_W = {"XS": 1, "S": 2, "M": 4, "L": 8, "XL": 16}
CP_CAP = 15
ENTRY_NAMES = ("__main__.py", "pipeline.py")  # a file by these names is a pipeline entry module
PLURAL = {"goal": "Goals", "feature": "Features", "requirement": "Requirements", "stage": "Stages", "milestone": "Milestones", "task": "Tasks", "pipeline": "Pipelines",
          "step": "Steps", "test": "Tests", "type": "Types", "symbol": "Symbols"}
TITLED = {"goal", "stage", "feature", "milestone", "pipeline"}  # levels whose ledger chips carry the title
CHIPS = 40

esc = charts.esc


def natural(s: str) -> list:
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", s)]


def anchor(nid: str) -> str:
    return "n-" + re.sub(r"[^\w.-]", "_", nid)


def tpage(n: int) -> str:
    return f"T{n:02d}.html"


def mpage(mid: str) -> str:
    return re.sub(r"[^\w.-]", "-", mid) + ".html"


def fit(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def short(nid: str, mid: str) -> str:
    """`M1-T05` → `T05` inside M1's own page."""
    return nid[len(mid) + 1:] if nid.startswith(mid + "-") else nid


# ---------------------------------------------------------------- model


def status_of(n: dict) -> str:
    return str(n.get("status") or (n.get("attrs") or {}).get("status") or "")


def norm_node(n: dict) -> dict | None:
    if not isinstance(n, dict) or not n.get("id"):
        return None
    attrs = n.get("attrs") if isinstance(n.get("attrs"), dict) else {}
    out = {"id": str(n["id"]), "level": str(n.get("level") or "?"), "parent": n.get("parent") or None,
           "title": str(n.get("title") or ""), "attrs": attrs,
           "expects": n.get("expects") if isinstance(n.get("expects"), dict) else {},
           "status": status_of(n)}
    body = {k: v for k, v in n.items() if k != "hash"}
    out["hash"] = n.get("hash") or hashlib.sha1(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]
    out["own_hash"] = bool(n.get("hash"))
    return out


def norm_edge(e: dict) -> dict | None:
    if not isinstance(e, dict) or not e.get("from") or not e.get("to"):
        return None
    return {"from": str(e["from"]), "to": str(e["to"]), "kind": str(e.get("kind") or "depends"),
            "mitigated_by": str(e.get("mitigated_by") or ""), "reason": str(e.get("reason") or "")}


def edge_value(e: dict) -> str:
    if e["mitigated_by"]:
        return f"{e['to']} (mitigated by {e['mitigated_by']})"
    if e["kind"] in GRAPH_KINDS and e["reason"]:
        return f"{e['to']} (none: {e['reason']})"
    return e["to"]


def node_fields(n: dict, out_edges: dict[str, set[str]]) -> dict[str, tuple[str, object]]:
    """field -> (category, value) for comparing two versions of a node."""
    f: dict[str, tuple[str, object]] = {"title": ("text", n["title"]), "parent": ("parent", n["parent"] or "")}
    for k, v in n["attrs"].items():
        if k != "status":
            f[k] = ("attrs", v)
    for k, v in n["expects"].items():
        f[k] = ("expects", v)
    for k, v in out_edges.items():
        if k not in n["expects"]:  # an edge kind the expectations already list (covers) is compared there
            f[k] = ("edges", v)
    return f


def changes(old: dict, new: dict, old_e: dict, new_e: dict) -> list[tuple[str, str, object, object]]:
    """(field, category, before, after) for every field that differs, status included."""
    a, b = node_fields(old, old_e), node_fields(new, new_e)
    empty = (None, "", [], set(), {})
    out = []
    for k in dict.fromkeys([*a, *b]):
        (ca, va), (cb, vb) = a.get(k, ("", None)), b.get(k, ("", None))
        if va != vb and not (va in empty and vb in empty):
            out.append((k, ca or cb, va, vb))
    if old["status"] != new["status"]:
        out.append(("status", "status", old["status"], new["status"]))
    if not out and old["own_hash"] and new["own_hash"] and old["hash"] != new["hash"]:
        out.append(("hash", "other", old["hash"], new["hash"]))
    return out


class Snap:
    def __init__(self, turn: int, body: dict, same_as: int | None = None):
        self.turn = turn
        self.same_as = same_as
        self.commit = str(body.get("commit") or "")
        self.ts = str(body.get("ts") or "")
        self.skill = str(body.get("skill") or "")
        nodes = [x for x in map(norm_node, body.get("nodes") or []) if x]
        self.nodes = {n["id"]: n for n in nodes}
        self.edges = [x for x in map(norm_edge, body.get("edges") or []) if x]
        self.builds = {str(b.get("milestone")): b for b in body.get("builds") or [] if isinstance(b, dict)}
        self.out: dict[str, dict[str, set[str]]] = {}
        for e in self.edges:
            self.out.setdefault(e["from"], {}).setdefault(e["kind"], set()).add(edge_value(e))
        self.into: dict[str, list[dict]] = {}
        for e in self.edges:
            self.into.setdefault(e["to"], []).append(e)
        # filled by Plan
        self.added: list[str] = []
        self.removed: list[str] = []
        self.changed: dict[str, list] = {}  # id -> non-status changes
        self.status: dict[str, tuple[str, str]] = {}  # id -> (before, after), status-only changes
        self.kind = "same"  # same | status | changed

    def by_level(self, level: str) -> list[dict]:
        return [n for n in self.nodes.values() if n["level"] == level]


class Plan:
    def __init__(self, doc: dict, out: Path):
        self.out = out
        self.schema = str(doc.get("schema") or "")
        self.producer = str(doc.get("producer") or "")
        self.notes: list[str] = []
        if not self.schema.startswith("plan-map/"):
            self.notes.append(f"schema is {self.schema or 'missing'}, not {SCHEMA}; drawn as {SCHEMA}")
        elif self.schema not in KNOWN:
            self.notes.append(f"schema {self.schema} is not {SCHEMA}; fields this page does not know are skipped")
        raw = sorted((s for s in doc.get("snapshots") or [] if isinstance(s, dict) and isinstance(s.get("turn"), int)),
                     key=lambda s: s["turn"])
        bodies: dict[int, dict] = {}
        self.snaps: list[Snap] = []
        for s in raw:
            if "same_as" in s:
                ref = bodies.get(s["same_as"])
                if ref is None:
                    self.notes.append(f"T{s['turn']:02d} is same_as T{s['same_as']:02d}, which has no snapshot; skipped")
                    continue
                bodies[s["turn"]] = ref
                self.snaps.append(Snap(s["turn"], {**ref, "turn": s["turn"]}, s["same_as"]))
            else:
                bodies[s["turn"]] = s
                self.snaps.append(Snap(s["turn"], s))
        seen = [n["level"] for s in self.snaps for n in s.nodes.values()]
        given = [str(x) for x in doc.get("levels") or [] if x]
        base = given or [x for x in LEVELS if x in seen]
        self.levels = list(dict.fromkeys([*base, *seen]))
        prev = None
        for s in self.snaps:
            self._diff(prev, s)
            prev = s
        self.changed = [s for s in self.snaps if s.kind == "changed"]
        self.status_only = [s for s in self.snaps if s.kind == "status"]
        self.final = self.snaps[-1] if self.snaps else None
        self.ever: dict[str, dict] = {}  # every node ever seen, at its last version
        self.first: dict[str, int] = {}
        for s in self.snaps:
            for nid, n in s.nodes.items():
                self.ever[nid] = n
                self.first.setdefault(nid, s.turn)
        self.index = load_json(out / "index.json")
        self.run_turns = {t.get("n"): t for t in (self.index or {}).get("turns") or [] if isinstance(t.get("n"), int)}
        self._doc_steps: dict[int, list[str]] = {}

    def _diff(self, prev: Snap | None, s: Snap) -> None:
        old = prev.nodes if prev else {}
        s.added = sorted((k for k in s.nodes if k not in old), key=natural)
        s.removed = sorted((k for k in old if k not in s.nodes), key=natural)
        for k in s.nodes:
            if k not in old:
                continue
            ch = changes(old[k], s.nodes[k], prev.out.get(k, {}), s.out.get(k, {}))
            rest = [c for c in ch if c[1] != "status"]
            if rest:
                s.changed[k] = rest
            st = [c for c in ch if c[1] == "status"]
            if st:
                s.status[k] = (st[0][2], st[0][3])
        if s.added or s.removed or s.changed:
            s.kind = "changed"
        elif s.status:
            s.kind = "status"

    def at(self, turn: int) -> Snap | None:
        """The snapshot in force at `turn`: the last one at or before it."""
        best = None
        for s in self.snaps:
            if s.turn <= turn:
                best = s
        return best

    def page_for(self, turn: int) -> Snap | None:
        """The changed turn whose page shows the plan as of `turn`."""
        best = None
        for s in self.changed:
            if s.turn <= turn:
                best = s
        return best

    def axis(self) -> list[int]:
        turns = set(self.run_turns) | {s.turn for s in self.snaps}
        return sorted(turns) if turns else []

    def milestones(self) -> list[str]:
        """Every milestone that ever had tasks, in id order."""
        ms = {n["parent"] for s in self.snaps for n in s.nodes.values() if n["level"] == "task" and n["parent"]}
        return sorted(ms, key=natural)

    def doc_steps(self, turn: int) -> list[str]:
        """The run's steps in `turn` that wrote a file under docs/ or tasks/, when the run is traced."""
        if turn not in self._doc_steps:
            d = load_json(self.out / "turns" / f"T{turn:02d}.json") or {}
            project = (self.index or {}).get("project")
            hits = []
            for o in d.get("file_ops") or []:
                p = o.get("path") or ""
                if o.get("op") in ("write", "edit") and re.search(r"(^|/)(docs|tasks)/", p):
                    hits.append(f"{o.get('step')} {charts.short(p, project)}")
            self._doc_steps[turn] = list(dict.fromkeys(hits))
        return self._doc_steps[turn]


def load_json(f: Path) -> dict | None:
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    except (OSError, ValueError):
        return None


_CACHE: dict[str, tuple[float, Plan | None]] = {}


def load(out: Path) -> Plan | None:
    f = Path(out) / "plan.json"
    if not f.exists():
        return None
    key, mtime = str(f.resolve()), f.stat().st_mtime
    if key in _CACHE and _CACHE[key][0] == mtime:
        return _CACHE[key][1]
    plan = None
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and isinstance(doc.get("snapshots"), list):
            plan = Plan(doc, Path(out))
        else:
            print(f"planmap: {f}: no snapshots list; not drawn", file=sys.stderr)
    except (OSError, ValueError) as e:
        print(f"planmap: {f}: {e}; not drawn", file=sys.stderr)
    _CACHE[key] = (mtime, plan)
    return plan


# ---------------------------------------------------------------- the build graph of one milestone


class Graph:
    """One milestone's tasks in one snapshot, as segments: a split task is two, tester then
    implementer. When the milestone has interface tasks, the tester half waits only on them:
    on those among the task's ancestors, else on all of the milestone's, so a tester never
    starts beside the interface. Without interface tasks it waits on everything the task
    depends on. The implementer waits on its tester and the task's dependencies."""

    def __init__(self, s: Snap, mid: str):
        self.snap, self.mid = s, mid
        self.tasks = sorted((n for n in s.nodes.values() if n["level"] == "task" and n["parent"] == mid),
                            key=lambda n: natural(n["id"]))
        ids = {t["id"] for t in self.tasks}
        self.ids = ids
        self.kind = {t["id"]: str(t["attrs"].get("kind") or "").lower() for t in self.tasks}
        self.split = {t["id"]: str(t["attrs"].get("mode") or "").lower() == "split" for t in self.tasks}
        self.deps: dict[str, list[str]] = {t: [] for t in ids}
        self.external: list[dict] = []
        for e in s.edges:
            if e["kind"] == "depends" and e["from"] in ids:
                if e["to"] in ids:
                    if e["to"] not in self.deps[e["from"]] and e["to"] != e["from"]:
                        self.deps[e["from"]].append(e["to"])
                else:
                    self.external.append(e)
        self.graph_edges = [e for e in s.edges if e["kind"] in GRAPH_KINDS and e["from"] in ids and e["to"] in ids]
        self.interface_first = any(k == "interface" for k in self.kind.values())
        self.entry_pairs = {(t, d): f for t in sorted(ids, key=natural) for d in self.deps[t]
                            if (f := self.shared_entry(t, d))}
        self.cycles: list[tuple[str, str]] = []
        self._segments()
        self._layers()
        self._critical_path()
        self._task_waves()

    def last(self, t: str) -> tuple[str, str]:
        return (t, "impl") if self.split[t] else (t, "")

    def _ancestors(self) -> dict[str, set[str]]:
        """Every task each task reaches through `depends`, itself left out; safe on a cycle."""
        anc: dict[str, set[str]] = {}
        for t in self.ids:
            seen, todo = set(), list(self.deps[t])
            while todo:
                d = todo.pop()
                if d not in seen and d != t:
                    seen.add(d)
                    todo.extend(self.deps[d])
            anc[t] = seen
        return anc

    def tester_waits_on(self, t: str) -> list[str]:
        """The interface tasks a split task's tester half waits on: those among the task's
        ancestors, else every interface task of the milestone. Only the last of a chain is kept
        (an interface that another one already waits on adds no order)."""
        ifaces = {d for d in self.anc[t] if self.kind[d] == "interface"} or \
                 {d for d in self.ids if self.kind[d] == "interface" and d != t}
        last = [i for i in ifaces if not any(i in self.anc[j] for j in ifaces if j != i)]
        return sorted(last or ifaces, key=natural)  # a cycle among interfaces keeps them all

    def _segments(self) -> None:
        self.anc = self._ancestors()
        self.preds: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for t in sorted(self.ids, key=natural):
            deps = [self.last(d) for d in self.deps[t]]
            if self.split[t]:
                tdeps = [self.last(d) for d in self.tester_waits_on(t)] if self.interface_first else deps
                self.preds[(t, "test")] = tdeps
                self.preds[(t, "impl")] = [(t, "test"), *deps]
            else:
                self.preds[(t, "")] = deps
        self.succs: dict[tuple[str, str], list[tuple[str, str]]] = {k: [] for k in self.preds}
        for k, ps in self.preds.items():
            for p in ps:
                self.succs[p].append(k)

    def _layers(self) -> None:
        layer: dict = {}
        state: dict = {}

        def visit(k) -> int:
            if k in layer:
                return layer[k]
            state[k] = 1
            best = 0
            for p in list(self.preds[k]):
                if state.get(p) == 1:  # a cycle: drop this edge and say so
                    self.cycles.append((k[0], p[0]))
                    self.preds[k].remove(p)
                    self.succs[p].remove(k)
                    continue
                best = max(best, visit(p) + 1)
            state[k] = 2
            layer[k] = best
            return best

        sys.setrecursionlimit(max(1000, 4 * len(self.preds) + 100))
        for k in sorted(self.preds, key=lambda k: natural(k[0])):
            visit(k)
        self.layer = layer
        self.n_waves = max(layer.values(), default=-1) + 1
        self.waves = [sorted((k for k in layer if layer[k] == w), key=lambda k: natural(k[0])) for w in range(self.n_waves)]

    def _critical_path(self) -> None:
        """Every longest path, drawn: `cp_segments` and `cp_pairs` are the segments and edges on
        any of them, `cp_lanes` the paths as task chains, tied ones merged where they differ in one
        task. `cp` is one of them, named in the metrics. Ties for it go to the producer's own
        critical path, then to an edge between two tasks over one inside a split task, then to the
        heavier size, then to the id."""
        self.cp_segments: set[tuple[str, str]] = set()
        self.cp_pairs: set = set()
        self.cp_lanes: list[list[list[str]]] = []
        self.cp_paths = 0
        self.cp: list[str] = []
        if not self.layer:
            return
        theirs = set((self.snap.builds.get(self.mid) or {}).get("critical_path") or [])
        size = {t["id"]: SIZE_W.get(str(t["attrs"].get("size") or "").upper(), 1) for t in self.tasks}

        def key(k, nxt=None):
            return (k[0] in theirs, nxt is None or k[0] != nxt[0], size.get(k[0], 1))

        def by_id(ks):  # max() keeps the first of equals, so the lowest id wins what is left
            return sorted(ks, key=lambda k: natural(k[0]))

        top = self.n_waves - 1
        cur = max(by_id(k for k in self.layer if self.layer[k] == top), key=key)
        path = [cur]
        while self.layer[cur] > 0:
            cands = by_id(p for p in self.preds[cur] if self.layer[p] == self.layer[cur] - 1)
            cur = max(cands, key=lambda p, c=cur: key(p, c))
            path.append(cur)
        path.reverse()
        self.cp = list(dict.fromkeys(k[0] for k in path))
        # height: the longest run of segments after k; k is on a longest path when layer + height = top
        height: dict = {}
        for k in sorted(self.layer, key=lambda k: -self.layer[k]):
            height[k] = max((height[s] + 1 for s in self.succs[k]), default=0)
        self.cp_segments = {k for k in self.layer if self.layer[k] + height[k] == top}
        self.cp_pairs = {(p, k) for k in self.cp_segments for p in self.preds[k]
                         if p in self.cp_segments and self.layer[p] + 1 + height[k] == top}
        self._cp_lanes(path)

    def _cp_lanes(self, primary: list[tuple[str, str]], cap: int = 200) -> None:
        """The longest paths as task chains, the primary first. Chains of one length that differ in
        a single task merge into one lane with alternatives there. Past `cap` paths only the
        primary is listed; `cp_paths` still counts them all."""
        into: dict = {}
        for p, k in self.cp_pairs:
            into.setdefault(k, []).append(p)
        count: dict = {}
        for k in sorted(self.cp_segments, key=lambda k: self.layer[k]):
            count[k] = sum(count[p] for p in into.get(k, [])) or 1
        ends = [k for k in self.cp_segments if self.layer[k] == self.n_waves - 1]
        self.cp_paths = sum(count[k] for k in ends)

        def tasks(path) -> tuple[str, ...]:
            return tuple(dict.fromkeys(k[0] for k in path))

        first = tasks(primary)
        if self.cp_paths > cap:
            self.cp_lanes = [[[t] for t in first]]
            return
        paths: list[list] = [[k] for k in self.cp_segments if self.layer[k] == 0]
        for _ in range(self.n_waves - 1):
            paths = [p + [k] for p in paths for k in self.succs[p[-1]] if (p[-1], k) in self.cp_pairs]
        chains = sorted({tasks(p) for p in paths}, key=lambda c: (c != first, [natural(t) for t in c]))
        lanes = [[{t} for t in c] for c in chains]
        merged = True
        while merged:
            merged = False
            for i in range(len(lanes)):
                for j in range(i + 1, len(lanes)):
                    a, b = lanes[i], lanes[j]
                    diff = [x for x in range(len(a)) if a[x] != b[x]] if len(a) == len(b) else []
                    if len(diff) == 1:
                        a[diff[0]] |= b[diff[0]]
                        del lanes[j]
                        merged = True
                        break
                if merged:
                    break
        self.cp_lanes = [[sorted(s, key=natural) for s in lane] for lane in lanes]

    def _task_waves(self) -> None:
        """Waves of whole tasks, the way a producer counts them, to set beside its numbers."""
        lvl: dict[str, int] = {}

        def visit(t, seen=()) -> int:
            if t not in lvl:
                lvl[t] = 0
                lvl[t] = 1 + max((visit(d, seen + (t,)) for d in self.deps[t] if d not in seen), default=-1)
            return lvl[t]

        for t in self.ids:
            visit(t)
        self.task_waves = [sorted((t for t in lvl if lvl[t] == w), key=natural) for w in range(max(lvl.values(), default=-1) + 1)]

    def lanes(self) -> list[str]:
        present = list(dict.fromkeys(self.kind[t["id"]] for t in self.tasks))
        return [k for k in KINDS if k in present] + [k for k in present if k not in KINDS]

    def layout(self) -> tuple[dict, list[str], dict[str, int]]:
        """(segment -> (wave, lane, slot), lanes, rows per lane), with a barycenter pass over each
        cell's order: down by predecessors, up by successors, down again."""
        lanes = self.lanes()
        cells: dict[tuple[int, str], list] = {}
        for k in sorted(self.layer, key=lambda k: natural(k[0])):
            cells.setdefault((self.layer[k], self.kind[k[0]]), []).append(k)
        rows = {ln: max((len(v) for (w, l2), v in cells.items() if l2 == ln), default=1) for ln in lanes}
        off, acc = {}, 0
        for ln in lanes:
            off[ln] = acc
            acc += rows[ln]

        def pos(k) -> float:
            cell = cells[(self.layer[k], self.kind[k[0]])]
            return off[self.kind[k[0]]] + cell.index(k)

        for direction in (1, -1, 1):
            order = range(self.n_waves) if direction == 1 else range(self.n_waves - 1, -1, -1)
            for w in order:
                for ln in lanes:
                    cell = cells.get((w, ln))
                    if not cell or len(cell) < 2:
                        continue
                    nb = self.preds if direction == 1 else self.succs
                    bary = {k: (sum(pos(p) for p in nb[k]) / len(nb[k])) if nb[k] else pos(k) for k in cell}
                    cell.sort(key=lambda k: (bary[k], natural(k[0])))
        place = {}
        for (w, ln), cell in cells.items():
            for i, k in enumerate(cell):
                place[k] = (w, ln, i)
        return place, lanes, rows

    def signature(self) -> str:
        return json.dumps([[t["id"], self.kind[t["id"]], self.split[t["id"]], sorted(self.deps[t["id"]])]
                           for t in self.tasks])

    def writes(self, t: str) -> list[str]:
        w = self.snap.nodes[t]["expects"].get("writes") or []
        return [str(x) for x in w] if isinstance(w, list) else [str(w)]

    def shared_entry(self, a: str, b: str) -> list[str]:
        """The entry modules (`__main__.py`, `pipeline.py`) two wiring tasks both write: an edge
        between them only serializes the two."""
        if self.kind.get(a) != "wiring" or self.kind.get(b) != "wiring":
            return []
        return sorted({x for x in self.writes(a) if x.rsplit("/", 1)[-1] in ENTRY_NAMES
                       and write_overlap([x], self.writes(b))})

    def reason_class(self, e: dict) -> str:
        """Why an unmitigated dependency-graph row stays, read from its structure (the kinds of
        its two tasks, their steps and Writes), not its wording. "" for a mitigated row. A file
        row and integration are tested before a generic order, in step with dev-team's
        `dtrun.unmitigated_class`: the design writes integration rows as `order`."""
        if e["mitigated_by"]:
            return ""
        a, b, kind = e["from"], e["to"], e["kind"]
        ka, kb = self.kind.get(a, ""), self.kind.get(b, "")
        if kind in ("data", "call"):
            return "data or call, not mitigated"
        if kind == "contract-change":
            return "contract change"
        if kind == "order" and not e["reason"]:
            return "order, no reason"
        if kind == "file":
            return "shared file"
        if ka in ("wiring", "system"):
            return "integration"
        if kind == "code" and ka in ("spine", "thicken") and kb in ("spine", "thicken"):
            sa = self.snap.nodes[a]["attrs"].get("step")
            sb = self.snap.nodes[b]["attrs"].get("step")
            if (sa and sa == sb) or write_overlap(self.writes(a), self.writes(b)):
                return "same module"
            return "across steps"
        if kind == "order":
            return "side-effect order"
        return "other"

    def metrics(self) -> dict:
        width = [len(w) for w in self.waves]
        mitigated = [e for e in self.graph_edges if e["mitigated_by"]]
        dc = [e for e in self.graph_edges if e["kind"] in ("data", "call")]
        why: dict[str, int] = {}
        for e in self.graph_edges:
            c = self.reason_class(e)
            if c:
                why[c] = why.get(c, 0) + 1
        return {"tasks": len(self.tasks), "cp": len(self.cp), "waves": self.n_waves, "width": width,
                "task_waves": len(self.task_waves), "widest_tasks": max(map(len, self.task_waves), default=0),
                "widest": max(width, default=0), "parallelism": len(self.tasks) / len(self.cp) if self.cp else 0.0,
                "edges": len(self.graph_edges), "mitigated": len(mitigated),
                "dc": len(dc), "dc_mitigated": sum(1 for e in dc if e["mitigated_by"]),
                "unmitigated": dict(sorted(why.items(), key=lambda kv: (REASON_ORDER.index(kv[0]), kv[0])))}


# Unmitigated-row classes, in the order they are listed; the last three are worth a look.
REASON_ORDER = ["integration", "same module", "shared file", "side-effect order", "contract change",
                "across steps", "data or call, not mitigated", "order, no reason", "other"]
REASON_FLAG = {"across steps", "data or call, not mitigated", "order, no reason", "other"}
REASON_TIP = {
    "integration": "a wiring or system task waits on what it wires or runs",
    "same module": "a code edge between spine or thicken tasks of the same step, or whose Writes overlap",
    "shared file": "a file edge: the two tasks write the same file",
    "side-effect order": "an order edge with a reason that is neither shared file nor integration",
    "contract change": "a contract-change edge",
    "across steps": "a code edge between spine or thicken tasks of different steps: it serializes them",
    "data or call, not mitigated": "an interface could have frozen this boundary",
    "order, no reason": "an order edge that gives no reason",
    "other": "none of the above",
}


def write_overlap(a: list[str], b: list[str]) -> bool:
    """Two Writes lists name a common file, a glob on one side matching a path on the other."""
    return any(x == y or fnmatch.fnmatchcase(x, y) or fnmatch.fnmatchcase(y, x) for x in a for y in b)


# ---------------------------------------------------------------- shared html


PLAN_CSS = """
.pa{background:var(--ok);color:var(--bg)}.pc{background:var(--warn);color:var(--bg)}.pr{background:var(--bad);color:var(--bg)}
.pl{background:var(--rowp)}.ps{background:var(--read);color:var(--readfg)}
.fm td.cell.pa,.fm td.cell.pc,.fm td.cell.pr{font-weight:700}.fm td.f.l1{padding-left:14px}.fm td.f.l2{padding-left:28px}
.fm td.t{text-align:left;color:var(--muted);white-space:nowrap;max-width:320px;overflow:hidden;text-overflow:ellipsis;
padding:0 10px 0 2px;font-size:11.5px}
details.lv{margin:6px 0}details.lv>summary{font-size:13px;color:var(--fg);font-weight:600;margin:4px 0}
.tog{margin:0 4px 0 0;vertical-align:-1px}.togl{font-size:12px;color:var(--muted);margin-right:16px}
.st{display:none}.tog-st:checked~* td.st,.tog-st:checked~* th.st{display:table-cell}
.tog-st:checked~* tr.st{display:table-row}.tog-st:checked~* span.st,.tog-st:checked~* div.st{display:inline}
.tog-q:checked~* .quiet{display:none}.tog-st:checked~* td.sx{background:var(--read);color:var(--readfg)}
.chip.st{display:none}.tog-st:checked~* .chip.st{display:inline-block}
.fm.pm td,.fm.pm th{box-sizing:border-box}.fm.pm td.f,.fm.pm th.f{width:170px;min-width:170px;max-width:170px}.fm.pm td.t,.fm.pm th.t{width:300px;min-width:300px;max-width:300px}
td.nw{white-space:nowrap}
.chip{display:inline-block;margin:0 6px 3px 0;padding:0 5px;border-radius:4px;font-size:12px;white-space:nowrap}
.chip.add{color:var(--ok);border:1px solid var(--ok)}.chip.chg{color:var(--warn);border:1px solid var(--warn)}
.chip.rem{color:var(--bad);border:1px solid var(--bad);text-decoration:line-through}
.chip.sts{color:var(--muted);border:1px dashed var(--line)}
.nav{font-size:13px}.nav a{margin-right:12px}
.tree details,.tree .leaf{margin:2px 0 2px 0;border-left:3px solid transparent;padding-left:8px}
.tree .kids{margin-left:18px}.tree summary{cursor:pointer;color:var(--fg);font-size:13.5px}
.tree .add{border-left-color:var(--ok)}.tree .chg{border-left-color:var(--warn)}.tree .rem{border-left-color:var(--bad)}
.tree .rem>summary .ttl,.tree .rem.leaf .ttl{text-decoration:line-through;color:var(--muted)}
.lvl{font:11px ui-monospace,Menlo,monospace;color:var(--muted);margin-right:6px}.nid{font-weight:700;margin-right:6px}
.tags{font-size:12px;color:var(--muted);margin-left:8px}.mark{font-size:11.5px;font-weight:700;margin-left:8px}
.mark.add{color:var(--ok)}.mark.chg{color:var(--warn)}.mark.rem{color:var(--bad)}
.nbody{margin:4px 0 6px 2px;font-size:13px}.nbody table{margin:2px 0}.nbody td{padding:2px 8px;border:0}
.nbody td:first-child{color:var(--muted);white-space:nowrap}.nbody ul{margin:0;padding-left:18px}
.nbody code{font-size:12px}.diff td{border-bottom:1px solid var(--line)!important}.was{color:var(--bad)}.now{color:var(--ok)}
svg.gs text,svg.mg text,svg.th text{font-size:10.5px;fill:var(--muted)}svg .rowl{fill:var(--fg);font-size:11.5px;font-weight:600}
svg .live{fill:var(--read)}svg .gadd{fill:var(--ok)}svg .grem{fill:var(--bad)}svg .lbl-in{fill:#fff;font-size:10.5px;font-weight:600}
svg .hit{fill:transparent}svg a:hover .hit{fill:var(--rowp);opacity:.6}
svg.mg .lane0{fill:var(--rowp);opacity:.45}svg.mg .lane1{fill:transparent}
svg.mg .nb{fill:var(--box);stroke:var(--line);stroke-width:1}svg.mg .nb.iface{stroke:var(--c6);stroke-width:2}svg.mg .cpn{stroke:var(--fg);stroke-width:2.2}
svg.mg .half{stroke-dasharray:4 3}svg.mg .done{fill:var(--ok);font-weight:700}
svg.mg .nid{fill:var(--fg);font-size:11.5px;font-weight:700}svg.mg .ntl{fill:var(--fg);font-size:10.5px}
svg.mg .nmeta{fill:var(--muted);font-size:10px}svg.mg .head{fill:var(--fg);font-size:12px;font-weight:700}
svg.mg .lanel{fill:var(--fg);font-size:12px;font-weight:700}
svg .e{fill:none;stroke:var(--muted);stroke-width:1.2;opacity:.75}svg .e.unb{stroke-dasharray:5 4;opacity:.4}
svg .e.cp{stroke:var(--fg);stroke-width:3;opacity:1}svg .e.sp{stroke:var(--muted);stroke-width:2;opacity:.9}
svg .e.ent{stroke:var(--warn);opacity:1}svg .e.ent:not(.cp){stroke-width:2}svg .arrowent{fill:var(--warn)}
svg.mg .entl{fill:var(--warn);font-size:9px;font-weight:700}
svg .arrowhead{fill:var(--muted)}svg .arrowcp{fill:var(--fg)}svg a:hover .nb{stroke:var(--fg)}
.thumbs{display:flex;flex-wrap:wrap;gap:10px}.thumb{border:1px solid var(--line);border-radius:6px;padding:4px 6px;
background:var(--box);font-size:11.5px;color:var(--muted);text-decoration:none}.thumb.cur{border-color:var(--fg)}
.thumb b{color:var(--fg)}svg.th .e{stroke-width:1}svg.th .e.cp{stroke-width:2}
.warnp{color:var(--warn)}
svg.tr .band{opacity:.09}svg.mg .nb.gap{stroke:var(--warn);stroke-width:2}
details.ft{margin:3px 0 3px 4px}details.ft>summary{cursor:pointer;font-size:13.5px}details.ft .ttl{margin-right:4px}
table.rq td{vertical-align:top;font-size:12.5px}h3 .sw{margin-right:6px}
"""


def page(title: str, nav: str, body: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>
<style>{flow.CSS}{charts.CHART_CSS}{flow.PAGE_CSS}{PLAN_CSS}</style></head>
<body>
<p class="top nav">{nav}</p>
{body}
</body></html>"""


def toggles(plan: Plan, quiet: bool = False) -> str:
    """Checkboxes that show status-only changes (and, on a turn page, hide what did not change),
    in CSS alone: the content they act on must follow them as siblings."""
    out = (f'<input type="checkbox" id="st" class="tog tog-st"><label for="st" class="togl">show status-only '
           f'changes ({sum(len(s.status) for s in plan.snaps)} in {len(plan.status_only)} turns of their own)</label>')
    if quiet:
        out = ('<input type="checkbox" id="q" class="tog tog-q"><label for="q" class="togl">only what changed</label>'
               + out)
    return out


def list_cell(v) -> str:
    if isinstance(v, (list, set, tuple)):
        items = sorted(v, key=lambda x: natural(str(x))) if isinstance(v, set) else list(v)
        return ", ".join(esc(x) for x in items) or "—"
    return esc(v if v not in (None, "") else "—")


def run_title(plan: Plan) -> str:
    ev = flow.load_eval(plan.out) or {}
    if ev.get("trajectory"):
        return f"{ev.get('trajectory')} · {ev.get('iteration', '')}"
    return (plan.index or {}).get("title") or plan.producer or "plan"


def back_nav(plan: Plan, here_index: bool = False) -> list[str]:
    nav = []
    if not here_index:
        nav.append('<a href="index.html">← plan map</a>')
    if (plan.out / "flow.html").exists():
        nav.append('<a href="../flow.html">the run\'s flow chart</a>')
    return nav


# ---------------------------------------------------------------- index.html


def growth_strip(plan: Plan) -> str:
    turns = plan.axis()
    if not turns:
        return "<p>No snapshots.</p>"
    left, width = 118, max(900, 118 + 30 * len(turns) + 20)
    bw = (width - left - 12) / len(turns)
    snap_at = {s.turn: s for s in plan.snaps}
    skills = list(dict.fromkeys(
        x for n in turns for x in [(snap_at[n].skill if n in snap_at and snap_at[n].skill else None) or
                                   (((plan.run_turns.get(n) or {}).get("skills") or [None])[-1] or "").split(":")[-1]
                                   or None] if x))
    color = {s: charts.cat(i) for i, s in enumerate(skills)}
    out, y = [f'<text x="8" y="17" class="rowl">Skill</text>'], 4
    for i, n in enumerate(turns):
        s = snap_at.get(n)
        x = left + i * bw
        sk = (s.skill if s and s.skill else None) or ((((plan.run_turns.get(n) or {}).get("skills") or [None])[-1]
                                                       or "").split(":")[-1] or None)
        wrote = bool(s and s.kind != "same")
        tip = f"T{n:02d}: " + (f"{sk} " if sk else "") + (
            f"changed the plan (+{len(s.added)} −{len(s.removed)} ~{len(s.changed)}"
            f"{', ' + str(len(s.status)) + ' status' if s.status else ''})" if wrote and s.kind == "changed"
            else "changed only statuses" if wrote else "plan unchanged" if s or plan.at(n) else "no plan yet")
        if not sk:
            out.append(f'<g><title>{esc(tip)}</title><rect x="{x + 1:.1f}" y="{y + 8}" width="{max(bw - 2, 1):.1f}" '
                       f'height="2" class="cx"/></g>')
            continue
        h_, y_ = (18, y) if wrote else (6, y + 6)
        label = (f'<text x="{x + 3:.1f}" y="{y + 13}" class="lbl-in">{esc(sk[:int(bw / 6.5)])}</text>'
                 if wrote and bw > 40 else "")
        out.append(f'<g><title>{esc(tip)}</title><rect x="{x + 1:.1f}" y="{y_}" width="{max(bw - 2, 1):.1f}" '
                   f'height="{h_}" rx="2" class="{color.get(sk, "cx")}"/>{label}</g>')
    y += 30
    above, below = 34, 14
    for lv in plan.levels:
        live = [len((plan.at(n).by_level(lv) if plan.at(n) else [])) for n in turns]
        if not any(live) and not any(plan.ever[k]["level"] == lv for k in plan.ever):
            continue
        top = max(live) or 1
        k = above / top
        base = y + above
        out.append(f'<text x="8" y="{y + 13}" class="rowl">{esc(PLURAL.get(lv, lv))}</text>'
                   f'<text x="8" y="{y + 27}">max {top}</text>'
                   f'<line x1="{left}" y1="{base}" x2="{width - 12}" y2="{base}" class="axis"/>')
        for i, n in enumerate(turns):
            s = snap_at.get(n)
            x = left + i * bw
            add = sum(1 for a in (s.added if s else []) if s.nodes[a]["level"] == lv)
            rem = sum(1 for r in (s.removed if s else []) if plan.ever[r]["level"] == lv)
            chg = sum(1 for c in (s.changed if s else {}) if s.nodes[c]["level"] == lv)
            h_live = live[i] * k
            h_add = add * k
            segs = []
            if h_live - h_add > 0:
                segs.append(f'<rect x="{x + 2:.1f}" y="{base - h_live:.1f}" width="{max(bw - 4, 1):.1f}" '
                            f'height="{h_live - h_add:.1f}" class="live"/>')
            if add:
                segs.append(f'<rect x="{x + 2:.1f}" y="{base - h_add:.1f}" width="{max(bw - 4, 1):.1f}" '
                            f'height="{max(h_add, 1.5):.1f}" class="gadd"/>')
            if rem:
                segs.append(f'<rect x="{x + 2:.1f}" y="{base + 1}" width="{max(bw - 4, 1):.1f}" '
                            f'height="{min(max(rem * k, 2), below):.1f}" class="grem"/>')
            if chg:
                segs.append(f'<circle cx="{x + bw / 2:.1f}" cy="{base + below / 2 + 1:.1f}" r="2.5" class="warn"/>')
            tip = (f"T{n:02d} · {PLURAL.get(lv, lv).lower()}: {live[i]} live" + (f", +{add} added" if add else "")
                   + (f", −{rem} removed" if rem else "") + (f", ~{chg} changed" if chg else ""))
            g = (f'<g><title>{esc(tip)}</title><rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="{above + below}" '
                 f'class="hit"/>{"".join(segs)}</g>')
            out.append(f'<a href="{tpage(s.turn)}">{g}</a>' if s and s.kind == "changed" else g)
            if live[i] and (i == 0 or live[i] != live[i - 1]) and bw >= 16:
                out.append(f'<text x="{x + bw / 2:.1f}" y="{base - h_live - 3:.1f}" text-anchor="middle">{live[i]}</text>')
        y = base + below + 10
    every = max(1, int(28 // bw) + 1)
    for i, n in enumerate(turns):
        if i % every == 0:
            out.append(f'<text x="{left + i * bw + bw / 2:.1f}" y="{y + 4}" text-anchor="middle">T{n}</text>')
    height = y + 10
    legend = "".join(f'<span><i class="sw {color[s]}"></i>{esc(s)}</span>' for s in skills)
    return (f'<p class="legend">One column per turn of the run. The top row is the skill that ran; a full block '
            f'is a turn that wrote the plan, a thin band one that did not. Below it, one row per level: the bar is the '
            f'nodes live after that turn, <span><i class="sw" style="background:var(--ok)"></i>added in it</span> '
            f'on top, <span><i class="sw" style="background:var(--bad)"></i>removed</span> below the line, and '
            f'<span class="warn">●</span> some changed. Click a column for the plan as of that turn. {legend}</p>'
            f'<div class="scroll"><svg class="gs" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="How the plan grew per turn">{"".join(out)}</svg></div>')


def cell_tip(plan: Plan, s: Snap, nid: str, what: str) -> str:
    tip = f"T{s.turn:02d}" + (f" · {s.skill}" if s.skill else "") + f" · {nid} {what}"
    steps = plan.doc_steps(s.turn)
    if steps:
        tip += "\nwritten at " + "; ".join(steps[:4]) + (f" (+{len(steps) - 4} more)" if len(steps) > 4 else "")
    elif s.commit:
        tip += f"\ncommit {s.commit}"
    return tip


def matrix(plan: Plan) -> str:
    cols = [s for s in plan.snaps if s.kind != "same"]
    if not cols:
        return "<p>The plan never changed.</p>"
    head = "".join(f'<th class="{"st" if s.kind == "status" else ""}"><a href="{tpage(s.turn) if s.kind == "changed" else tpage(plan.page_for(s.turn).turn) if plan.page_for(s.turn) else "#"}">'
                   f'T{s.turn}</a></th>' for s in cols)
    parts = []
    for lv in plan.levels:
        ids = [k for k, n in plan.ever.items() if n["level"] == lv]
        if not ids:
            continue
        groups: dict[str, list[str]] = {}
        for k in ids:
            p = plan.ever[k]["parent"] or ""
            groups.setdefault(p if p in plan.ever and plan.ever[p]["level"] != lv else "", []).append(k)
        rows = []
        for g in sorted(groups, key=lambda g: (g != "", natural(g))):
            if g:
                pn = plan.ever[g]
                rows.append(f'<tr class="grp"><td colspan="{len(cols) + 2}">{esc(g)} · {esc(fit(pn["title"], 60))}</td></tr>')
            for k in sorted(groups[g], key=natural):
                n = plan.ever[k]
                tds = []
                for s in cols:
                    alive = k in s.nodes
                    if k in s.added:
                        tds.append(f'<td class="cell pa" title="{esc(cell_tip(plan, s, k, "added"))}">A</td>')
                    elif k in s.removed:
                        tds.append(f'<td class="cell pr" title="{esc(cell_tip(plan, s, k, "removed"))}">R</td>')
                    elif k in s.changed:
                        what = "changed: " + ", ".join(c[0] for c in s.changed[k])
                        tds.append(f'<td class="cell pc" title="{esc(cell_tip(plan, s, k, what))}">C</td>')
                    elif k in s.status:
                        a, b = s.status[k]
                        cls = "cell pl sx" + (" st" if s.kind == "status" else "")
                        tip = cell_tip(plan, s, k, f"status {a or '—'} → {b or '—'}")
                        tds.append(f'<td class="{cls}" title="{esc(tip)}"><span class="st">s</span></td>')
                    else:
                        tds.append(f'<td class="cell{" pl" if alive else ""}{" st" if s.kind == "status" else ""}"></td>')
                ind = " l1" if g else ""
                rows.append(f'<tr><td class="f{ind}" title="{esc(k)}">{esc(fit(k, 40))}</td>'
                            f'<td class="t" title="{esc(n["title"])}">{esc(fit(n["title"], 48))}</td>{"".join(tds)}</tr>')
        big = len(ids) > 60
        parts.append(f'<details class="lv"{"" if big else " open"}><summary>{esc(PLURAL.get(lv, lv))} · {len(ids)}'
                     f'</summary><div class="scroll"><table class="fm pm"><tr><th class="f">Id</th><th class="t"></th>{head}</tr>'
                     f'{"".join(rows)}</table></div></details>')
    key = ('<p class="legend"><span class="key pa">A</span>added <span class="key pc">C</span>changed (title, parent, '
           'attributes, expectations or the edges leaving it) <span class="key pr">R</span>removed '
           '<span class="key pl">&nbsp;</span>live, unchanged <span class="key ps">s</span>status only. One column per '
           'turn that changed the plan; hover a cell for what changed and the step that wrote it, click a column for '
           'the plan as of that turn.</p>')
    return key + "".join(parts)


def chip(plan: Plan, s: Snap, nid: str, how: str) -> str:
    n = s.nodes.get(nid) or plan.ever.get(nid) or {"title": "", "level": ""}
    if how == "add":
        text = f"+{nid}" + (f" {fit(n['title'], 28)}" if n["level"] in TITLED else "")
    elif how == "rem":
        text = f"−{nid}"
    elif how == "chg":
        text = f"~{nid} " + ", ".join(dict.fromkeys(c[0] for c in s.changed[nid]))
    else:
        a, b = s.status[nid]
        text = f"{nid} {a or '—'}→{b or '—'}"
    cls = "chip " + {"add": "add", "rem": "rem", "chg": "chg", "sts": "sts st"}[how]
    return (f'<a class="{cls}" href="{tpage(s.turn) if s.kind == "changed" else "#"}#{anchor(nid)}" '
            f'title="{esc(n["level"])} · {esc(n["title"])}">{esc(text)}</a>')


def ledger(plan: Plan) -> str:
    rows = []
    for s in plan.snaps:
        if s.kind == "same":
            continue
        chips = ([chip(plan, s, k, "add") for k in s.added] + [chip(plan, s, k, "chg") for k in sorted(s.changed, key=natural)]
                 + [chip(plan, s, k, "rem") for k in s.removed] + [chip(plan, s, k, "sts") for k in sorted(s.status, key=natural)])
        shown = "".join(chips[:CHIPS])
        if len(chips) > CHIPS:
            shown += f'<details><summary>{len(chips) - CHIPS} more</summary>{"".join(chips[CHIPS:])}</details>'
        turn = (f'<a href="{tpage(s.turn)}">T{s.turn:02d}</a>' if s.kind == "changed" else f"T{s.turn:02d}")
        rt = (f' <a class="sub" href="../turns/T{s.turn:02d}.html" title="what the run did in this turn">run ↗</a>'
              if (plan.out / "turns" / f"T{s.turn:02d}.html").exists() else "")
        rows.append(f'<tr class="{"st" if s.kind == "status" else ""}"><td class="nw">{turn}{rt}</td><td>{esc(s.skill or "—")}</td>'
                    f'<td><code>{esc(s.commit[:10] or "—")}</code></td>'
                    f'<td>{len(s.added) or ""}</td><td>{len(s.changed) or ""}</td><td>{len(s.removed) or ""}</td>'
                    f'<td class="chips">{shown}</td></tr>')
    if not rows:
        return "<p>No turn changed the plan.</p>"
    return ('<div class="scroll"><table><tr><th>Turn</th><th>Skill</th><th>Commit</th><th>+</th><th>~</th><th>−</th>'
            '<th>Changes</th></tr>' + "".join(rows) + "</table></div>")


def milestone_rows(plan: Plan) -> str:
    rows = []
    for mid in plan.milestones():
        s = last_with_tasks(plan, mid)
        g = Graph(s, mid)
        m = g.metrics()
        node = plan.ever.get(mid) or {"title": "", "status": ""}
        alive = plan.final and mid in plan.final.nodes
        mitigated = f"{m['dc_mitigated']} of {m['dc']}" if m["dc"] else "—"
        rows.append(f'<tr><td><a href="{mpage(mid)}"><b>{esc(mid)}</b></a></td><td>{esc(node["title"])}'
                    f'{"" if alive or mid not in plan.ever else " <span class=bad>(removed)</span>"}</td>'
                    f'<td>{esc(node.get("status") or "—")}</td><td>T{s.turn:02d}</td><td>{m["tasks"]}</td>'
                    f'<td class="{"bad" if m["cp"] > CP_CAP else ""}">{m["cp"]}</td>'
                    f'<td>{m["waves"]} ({m["task_waves"]})</td>'
                    f'<td>{m["widest"]} ({m["widest_tasks"]})</td><td>{m["parallelism"]:.1f}</td>'
                    f'<td>{mitigated}</td></tr>')
    if not rows:
        return "<p>No milestone has tasks yet.</p>"
    return ('<table><tr><th>Milestone</th><th>Title</th><th>Status</th><th>As of</th><th>Tasks</th><th>Critical path</th>'
            '<th>Waves of boxes (of whole tasks)</th><th>Widest wave, boxes (whole tasks)</th><th>Parallelism</th>'
            '<th>Data and call edges mitigated</th></tr>' + "".join(rows) + "</table>")


def last_with_tasks(plan: Plan, mid: str) -> Snap:
    """The last snapshot of its own (not `same_as` another) in which `mid` has tasks."""
    mine = [s for s in plan.snaps if any(n["level"] == "task" and n["parent"] == mid for n in s.nodes.values())]
    return ([s for s in mine if s.same_as is None] or mine)[-1]


def write_index(plan: Plan, d: Path) -> Path:
    f = plan.final
    tiles = []
    for lv in plan.levels:
        c = len(f.by_level(lv)) if f else 0
        if c:
            tiles.append((str(c), PLURAL.get(lv, lv).lower(), ""))
    replans = [s for s in plan.changed if s.removed or any(
        (s.nodes.get(k) or {}).get("level") in ("task", "milestone") for k in s.changed)]
    tiles.append((str(len(plan.changed)), "turns changed the plan", ""))
    tiles.append((str(len(replans)), "replans", ""))
    ms = plan.milestones()
    if ms:
        longest = max(((Graph(last_with_tasks(plan, m), m).metrics()["cp"], m) for m in ms))
        tiles.append((f"{longest[0]}", f"longest critical path ({longest[1]})",
                      f'<i class="{"bad" if longest[0] > CP_CAP else ""}">cap {CP_CAP}</i>'))
    notes = "".join(f'<p class="warnp">{esc(x)}</p>' for x in plan.notes)
    nav = back_nav(plan, here_index=True)
    if plan.changed:
        nav.append(f'<a href="{tpage(plan.changed[-1].turn)}">the final plan (T{plan.changed[-1].turn:02d})</a>')
    trace = ""
    if has_trace(f):
        nav.append('<a href="trace.html">goals to build</a>')
        t = Trace(f)
        rs = [r["id"] for r in t.reqs]
        trace = (f'<h2>Goals to build</h2><p><a href="trace.html"><b>Goals to build</b></a>: {len(t.goals)} goals, '
                 f'{len(t.features)} features in {len(t.stages)} stages, {len(rs)} requirements, of which '
                 + ", ".join(f"{t.covered(rs, k)} are on a {k}" for k in COVER)
                 + '. How each goal reaches features, stages, pipelines and milestones.</p>')
    body = f"""<h1>Plan map · {esc(run_title(plan))}</h1>
<div class="sub">{esc(plan.producer or 'unknown producer')} · {esc(plan.schema or 'no schema')} · {len(plan.snaps)} snapshots,
turns T{plan.snaps[0].turn:02d}–T{plan.snaps[-1].turn:02d}</div>
{notes}
{charts.tiles(tiles)}
{trace}
<h2>Milestones</h2>
<p class="legend">Each opens its build view: what would run in parallel and what in series. Critical path is in tasks
(cap {CP_CAP}); waves count boxes, a split task's tester and implementer apart, with the waves of whole tasks in
brackets; parallelism is tasks ÷ critical path; mitigated are the data and call rows of the dependency graph that
an interface removes from the order (the other rows can never be).</p>
{milestone_rows(plan)}
<h2>Growth</h2>
{growth_strip(plan)}
{toggles(plan)}
<div>
<h2>Nodes by turn</h2>
{matrix(plan)}
<h2>Change ledger</h2>
<p class="legend">One row per turn that changed the plan: <span class="chip add">+added</span><span class="chip chg">~changed:
fields</span><span class="chip rem">−removed</span>. Each opens that node on the turn's page.</p>
{ledger(plan)}
</div>"""
    path = d / "index.html"
    path.write_text(page(f"Plan map · {run_title(plan)}", " · ".join(nav), body), encoding="utf-8")
    return path


# ---------------------------------------------------------------- trace.html


COVER = ("pipeline", "test", "task")  # what a requirement's coverage is counted by; a step counts for its pipeline


class Trace:
    """One snapshot from goals to build: which goals each feature serves, the stages it sits in, its
    requirements, and per requirement the pipelines (and steps), tests and tasks that cover it."""

    def __init__(self, s: Snap):
        self.s = s
        lv = s.by_level
        self.goals = sorted(lv("goal"), key=lambda n: natural(n["id"]))
        self.stages = sorted(lv("stage"), key=lambda n: natural(n["id"]))
        self.features = lv("feature")  # the producer's order, which is the spec's
        self.reqs = lv("requirement")
        self.milestones = sorted(lv("milestone"), key=lambda n: natural(n["id"]))
        self.pipelines = sorted(lv("pipeline"), key=lambda n: natural(n["id"]))
        self.serves = {f["id"]: sorted({e["to"] for e in s.edges if e["from"] == f["id"] and e["kind"] == "serves"},
                                       key=natural) for f in self.features}
        self.freqs = {f["id"]: [r["id"] for r in self.reqs if r["parent"] == f["id"]] for f in self.features}
        self.cov: dict[str, dict[str, set[str]]] = {r["id"]: {k: set() for k in (*COVER, "step")} for r in self.reqs}
        for e in s.edges:
            src = s.nodes.get(e["from"])
            if e["kind"] != "covers" or e["to"] not in self.cov or not src:
                continue
            c = self.cov[e["to"]]
            if src["level"] == "step":
                c["step"].add(src["id"])
                if src["parent"]:
                    c["pipeline"].add(src["parent"])
            elif src["level"] in c:
                c[src["level"]].add(src["id"])
        self.stage_ix = {st["id"]: i for i, st in enumerate(self.stages)}
        self.pipe_ms: dict[str, list[str]] = {}
        for m in self.milestones:
            listed = m["attrs"].get("pipelines") or [p["id"] for p in self.pipelines if p["parent"] == m["id"]]
            for p in listed:
                self.pipe_ms.setdefault(str(p), []).append(m["id"])

    def stages_of(self, f: dict) -> list[str]:
        return [str(x) for x in f["attrs"].get("stages") or ([f["parent"]] if f["parent"] else [])]

    def covered(self, reqs: list[str], kind: str) -> int:
        return sum(1 for r in reqs if self.cov.get(r, {}).get(kind))

    def union(self, reqs: list[str], kind: str) -> list[str]:
        return sorted(set().union(*(self.cov[r][kind] for r in reqs if r in self.cov)), key=natural)

    def feature_ms(self, reqs: list[str]) -> list[str]:
        """Milestones that build these requirements: those listing a covering pipeline, and those whose tasks
        cover them."""
        ms = {m for p in self.union(reqs, "pipeline") for m in self.pipe_ms.get(p, [])}
        ms |= {self.s.nodes[t]["parent"] for t in self.union(reqs, "task") if self.s.nodes[t]["parent"]}
        return sorted(ms, key=natural)

    def color(self, stage: str | None) -> str:
        return f"var(--c{self.stage_ix[stage] % 8})" if stage in self.stage_ix else "var(--cx)"


def frac(n: int, of: int) -> str:
    return f"{n}/{of}" if of else "—"


def cov_cell(n: int, of: int) -> str:
    cls = "" if not of else "ok" if n == of else "bad" if n == 0 else "warnp"
    return f'<td class="{cls}">{frac(n, of)}</td>'


TW = {"goal": 220, "feature": 250, "pipeline": 230, "milestone": 210}
TH, TG, TGAP, TTOP = 36, 8, 110, 44


def stack(items: list[tuple[str, float | None]], top: float) -> dict[str, float]:
    """Each item's box top, as near its wanted centre as the boxes above it allow; those with no wanted
    centre (nothing links them) go below the rest."""
    out, y = {}, top
    for k, want in sorted(items, key=lambda kv: (kv[1] is None, kv[1] or 0, natural(kv[0]))):
        y = max(y, want - TH / 2) if want is not None else y
        out[k] = y
        y += TH + TG
    return out


def trace_svg(t: Trace, href) -> str:
    """Four columns: goals, features in stage bands, the pipelines that cover them, the milestones that list
    those pipelines. Edges: serves; covers (thicker for more requirements); builds."""
    xg = 10
    xf = xg + TW["goal"] + TGAP
    xp = xf + TW["feature"] + TGAP
    xm = xp + TW["pipeline"] + TGAP
    out, edges = [], []
    # features, banded by their first stage
    bands = [(st["id"], st["title"]) for st in t.stages] + [("", "no single stage")]
    fy, y = {}, TTOP
    for sid, title in bands:
        fs = [f for f in t.features if (f["parent"] or "") == sid]
        if not fs:
            continue
        h = 22 + len(fs) * (TH + TG)
        out.append(f'<rect x="{xf - 8}" y="{y}" width="{TW["feature"] + 16}" height="{h}" rx="6" class="band" '
                   f'style="fill:{t.color(sid) if sid else "var(--cx)"}"/>'
                   f'<text x="{xf}" y="{y + 15}" class="head">{esc(fit((sid + " · " if sid else "") + title, 34))}</text>')
        y += 22
        for f in fs:
            fy[f["id"]] = y
            y += TH + TG
        y += 14
    bottom = y

    def mid(yy: float) -> float:
        return yy + TH / 2

    def bary(pairs: list[tuple[float, float]]) -> float | None:
        """The weighted mean of (centre, weight) pairs, or None for none."""
        w = sum(n for _, n in pairs)
        return sum(c * n for c, n in pairs) / w if w else None

    gy = stack([(g["id"], bary([(mid(fy[f]), 1) for f in fy if g["id"] in t.serves[f]])) for g in t.goals], TTOP)
    weight: dict[tuple[str, str], list[str]] = {}
    for f in t.features:
        for r in t.freqs[f["id"]]:
            for p in t.cov[r]["pipeline"]:
                weight.setdefault((f["id"], p), []).append(r)
    pipes = [p for p in t.pipelines if any(k[1] == p["id"] for k in weight) or p["id"] in t.pipe_ms]
    py = stack([(p["id"], bary([(mid(fy[f]), len(rs)) for (f, q), rs in weight.items() if q == p["id"]]))
                for p in pipes], TTOP)
    mpipes = {m["id"]: [p for p in py if m["id"] in t.pipe_ms.get(p, [])] for m in t.milestones}
    my = stack([(m["id"], bary([(mid(py[p]), 1) for p in mpipes[m["id"]]])) for m in t.milestones], TTOP)
    for col in (gy, py, my):
        bottom = max([bottom, *(v + TH + TG for v in col.values())])
    width, height = xm + TW["milestone"] + 10, bottom + 6

    def curve(x1, y1, x2, y2, w, color, tip, dash=False):
        dx = (x2 - x1) / 2
        edges.append(f'<path d="M{x1:.1f},{y1:.1f} C{x1 + dx:.1f},{y1:.1f} {x2 - dx:.1f},{y2:.1f} {x2:.1f},{y2:.1f}" '
                     f'class="e{" unb" if dash else ""}" style="stroke:{color};stroke-width:{w:.1f}">'
                     f'<title>{esc(tip)}</title></path>')

    for f in t.features:
        for g in t.serves[f["id"]]:
            if g in gy:
                curve(xg + TW["goal"], mid(gy[g]), xf, mid(fy[f["id"]]), 1.4, "var(--muted)", f"{f['id']} serves {g}")
    for (f, p), rs in weight.items():
        if p in py:
            n = t.s.nodes[f]
            curve(xf + TW["feature"], mid(fy[f]), xp, mid(py[p]), 1 + min(5, len(rs) / 2), t.color(n["parent"]),
                  f"{p} covers {len(rs)} of {f}'s {len(t.freqs[f])} requirements: {', '.join(sorted(rs, key=natural))}")
    for m in t.milestones:
        for p in mpipes[m["id"]]:
            curve(xp + TW["pipeline"], mid(py[p]), xm, mid(my[m["id"]]), 1.2, t.color(m["parent"]),
                  f"{m['id']} builds {p}", dash=True)

    def box(n: dict, x: float, yy: float, w: int, stripe: str, meta: str, tip: str, gap: bool = False) -> str:
        l1 = fit(n["title"], max(8, int((w - 22) / 6.3) - len(n["id"])))
        return (f'<a href="{href(n["id"])}"><g><title>{esc(tip)}</title>'
                f'<rect x="{x}" y="{yy}" width="{w}" height="{TH}" rx="5" class="nb{" gap" if gap else ""}"/>'
                f'<rect x="{x}" y="{yy}" width="5" height="{TH}" rx="2" style="fill:{stripe}"/>'
                f'<text x="{x + 11}" y="{yy + 14}"><tspan class="nid">{esc(n["id"])}</tspan> '
                f'<tspan class="ntl">{esc(l1)}</tspan></text>'
                f'<text x="{x + 11}" y="{yy + 28}" class="nmeta">{esc(meta)}</text></g></a>')

    for g in t.goals:
        fs = [f for f in t.features if g["id"] in t.serves[f["id"]]]
        st = sorted({s for f in fs for s in t.stages_of(f)}, key=natural)
        out.append(box(g, xg, gy[g["id"]], TW["goal"], "var(--cx)",
                       f"{len(fs)} feature{'' if len(fs) == 1 else 's'}" + (f" · {', '.join(st)}" if st else ""),
                       f"{g['id']} · {g['title']}", gap=not fs))
    for f in t.features:
        rs = t.freqs[f["id"]]
        also = [s for s in t.stages_of(f) if s != f["parent"]]
        meta = (f"{len(rs)} req · pipeline {frac(t.covered(rs, 'pipeline'), len(rs))} · test "
                f"{frac(t.covered(rs, 'test'), len(rs))} · task {frac(t.covered(rs, 'task'), len(rs))}")
        tip = (f"{f['id']} · {f['title']}\nserves {', '.join(t.serves[f['id']]) or 'no goal'}"
               + (f"\nalso in {', '.join(also)}" if also else "")
               + (f"\nstage from {f['attrs']['stage_via']}" if f["attrs"].get("stage_via") else "\nno stage found"))
        out.append(box(f, xf, fy[f["id"]], TW["feature"], t.color(f["parent"]), meta, tip,
                       gap=not t.covered(rs, "pipeline")))
    for p in pipes:
        ms = t.pipe_ms.get(p["id"], [])
        # its first milestone's stage, else the stage of most of the requirements it covers
        share: dict[str, int] = {}
        for (f, q), rs in weight.items():
            if q == p["id"] and t.s.nodes[f]["parent"]:
                share[t.s.nodes[f]["parent"]] = share.get(t.s.nodes[f]["parent"], 0) + len(rs)
        first = (t.s.nodes[ms[0]]["parent"] if ms and ms[0] in t.s.nodes else None) or \
            (max(share, key=lambda k: (share[k], -t.stage_ix.get(k, 0))) if share else None)
        tests = sum(1 for n in t.s.by_level("test") if n["parent"] == p["id"])
        meta = " · ".join(x for x in (str(p["attrs"].get("package") or ""), f"{tests} test{'' if tests == 1 else 's'}",
                                      ", ".join(ms) or "no milestone") if x)
        out.append(box(p, xp, py[p["id"]], TW["pipeline"], t.color(first), meta, f"{p['id']} · {p['title']}"))
    for m in t.milestones:
        tasks = sum(1 for n in t.s.by_level("task") if n["parent"] == m["id"])
        meta = " · ".join(x for x in (m["parent"] or "", m["status"], f"{tasks} tasks" if tasks else "") if x)
        out.append(box(m, xm, my[m["id"]], TW["milestone"], t.color(m["parent"]), meta, f"{m['id']} · {m['title']}"))
    heads = "".join(f'<text x="{x}" y="18" class="head">{h}</text>'
                    for x, h in ((xg, "Goals"), (xf, "Stages and their features"), (xp, "Pipelines that cover them"),
                                 (xm, "Milestones that build them")))
    return (f'<svg class="mg tr" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="Goals to build">{heads}{"".join(edges)}'
            f'{"".join(out)}</svg>')


def trace_tables(t: Trace, link) -> tuple[str, str]:
    """(the goals table, the per-stage feature blocks with each requirement's coverage)."""
    rows = []
    for g in t.goals:
        fs = [f for f in t.features if g["id"] in t.serves[f["id"]]]
        rs = [r for f in fs for r in t.freqs[f["id"]]]
        st = sorted({s for f in fs for s in t.stages_of(f)}, key=natural)
        rows.append(f'<tr><td>{link(g["id"])}</td><td>{esc(g["title"])}</td>'
                    f'<td class="{"" if fs else "bad"}">{", ".join(link(f["id"]) for f in fs) or "none"}</td>'
                    f'<td>{esc(", ".join(st)) or "—"}</td><td>{len(rs)}</td>'
                    + "".join(cov_cell(t.covered(rs, k), len(rs)) for k in COVER)
                    + f'<td>{esc(", ".join(t.feature_ms(rs))) or "—"}</td></tr>')
    goals = ('<table><tr><th>Goal</th><th></th><th>Features serving it</th><th>Stages</th><th>Requirements</th>'
             '<th>On a pipeline</th><th>On a test</th><th>On a task</th><th>Milestones</th></tr>' + "".join(rows)
             + "</table>") if rows else "<p>No goals in this plan.</p>"

    def req_rows(ids: list[str]) -> str:
        out = []
        for r in ids:
            n, c = t.s.nodes[r], t.cov[r]
            pipes = ", ".join(link(p) for p in sorted(c["pipeline"], key=natural))
            steps = ", ".join(sorted(c["step"], key=natural))
            cells = [f'<td title="{esc(steps)}">{pipes}</td>' if pipes else '<td class="bad">—</td>']
            cells += [f'<td>{", ".join(link(x) for x in sorted(c[k], key=natural))}</td>' if c[k]
                      else '<td class="warnp">—</td>' for k in ("test", "task")]
            out.append(f'<tr><td class="nw">{link(r)}</td><td title="{esc(n["title"])}">{esc(fit(n["title"], 110))}</td>'
                       + "".join(cells) + "</tr>")
        return ('<table class="rq"><tr><th>Requirement</th><th></th><th>Pipelines (hover for steps)</th><th>Tests</th>'
                '<th>Tasks</th></tr>' + "".join(out) + "</table>")

    def feature_block(f: dict) -> str:
        rs = t.freqs[f["id"]]
        also = [s for s in t.stages_of(f) if s != f["parent"]]
        bits = [f"serves {', '.join(t.serves[f['id']]) or 'no goal'}", f"{len(rs)} requirements"]
        bits += [f"{k} {frac(t.covered(rs, k), len(rs))}" for k in COVER]
        ms = t.feature_ms(rs)
        bits.append("built in " + ", ".join(ms) if ms else "no milestone yet")
        if also:
            bits.append("also in " + ", ".join(also))
        warn = rs and t.covered(rs, "pipeline") < len(rs)
        return (f'<details class="ft" id="{anchor(f["id"])}"><summary><span class="nid">{esc(f["id"])}</span>'
                f'<span class="ttl">{esc(f["title"])}</span><span class="tags{" warnp" if warn else ""}">'
                f'{esc(" · ".join(bits))}</span></summary>{req_rows(rs) if rs else "<p>No requirements.</p>"}</details>')

    parts = []
    for st in [*t.stages, None]:
        sid = st["id"] if st else ""
        fs = [f for f in t.features if (f["parent"] or "") == sid]
        if not fs:
            continue
        rs = [r for f in fs for r in t.freqs[f["id"]]]
        head = (f'{esc(sid)} · {esc(st["title"])}' + (f' · {esc(st["status"])}' if st["status"] else "")
                if st else "Features with no single stage")
        note = ""
        if not st:
            via = {f["id"]: ", ".join(t.stages_of(f)) for f in fs}
            note = ('<p class="legend">The plan does not tie these to one stage. ' + "; ".join(
                f"{esc(k)}: covered by pipelines of {esc(v)}" if v else f"{esc(k)}: no stage" for k, v in via.items())
                    + ".</p>")
        parts.append(f'<h3><i class="sw" style="background:{t.color(sid or None)}"></i>{head}</h3>'
                     f'<p class="legend">{len(fs)} features, {len(rs)} requirements: on a pipeline '
                     f'{frac(t.covered(rs, "pipeline"), len(rs))}, on a test {frac(t.covered(rs, "test"), len(rs))}, '
                     f'on a task {frac(t.covered(rs, "task"), len(rs))}.</p>{note}'
                     + "".join(feature_block(f) for f in fs))
    loose = [r["id"] for r in t.reqs if not r["parent"] or r["parent"] not in t.freqs]
    if loose:
        by_sec: dict[str, list[str]] = {}
        for r in loose:
            by_sec.setdefault(str(t.s.nodes[r]["attrs"].get("section") or "no section"), []).append(r)
        parts.append("<h3>Requirements outside any feature</h3>" + "".join(
            f'<details class="ft"><summary><span class="ttl">{esc(sec)}</span><span class="tags">{len(ids)} requirements · '
            + " · ".join(f"{k} {frac(t.covered(ids, k), len(ids))}" for k in COVER)
            + f"</span></summary>{req_rows(ids)}</details>" for sec, ids in by_sec.items()))
    return goals, "".join(parts)


def has_trace(s: Snap | None) -> bool:
    return bool(s and (s.by_level("goal") or s.by_level("feature") or s.by_level("requirement")))


def write_trace(plan: Plan, d: Path) -> Path:
    s = plan.final
    t = Trace(s)
    at = plan.page_for(s.turn)
    tp = tpage(at.turn) if at else ""

    def href(k: str) -> str:
        return f"{tp}#{anchor(k)}" if tp else "#"

    def link(k: str) -> str:
        if k in t.freqs:
            return f'<a href="#{anchor(k)}">{esc(k)}</a>'
        return f'<a href="{href(k)}">{esc(k)}</a>' if k in s.nodes else esc(k)

    rs = [r["id"] for r in t.reqs]
    unplaced = [f for f in t.features if not f["parent"]]
    via: dict[str, int] = {}
    for f in t.features:
        k = str(f["attrs"].get("stage_via") or "not found")
        via[k] = via.get(k, 0) + 1
    tiles = [(str(len(t.goals)), "goals", f'<i class="bad">{n} with no feature</i>' if (n := sum(
                 1 for g in t.goals if not any(g["id"] in v for v in t.serves.values()))) else ""),
             (str(len(t.features)), "features", f'<i class="warnp">{len(unplaced)} in no single stage</i>' if unplaced else ""),
             (str(len(rs)), "requirements", "")]
    tiles += [(frac(t.covered(rs, k), len(rs)), f"requirements on a {k}",
               f"<i>{t.covered(rs, k) / len(rs):.0%}</i>" if rs else "") for k in COVER]
    goals, stages = trace_tables(t, link)
    nav = back_nav(plan)
    if tp:
        nav.append(f'<a href="{tp}">the final plan (T{at.turn:02d})</a>')
    body = f"""<h1>Goals to build · {esc(run_title(plan))}</h1>
<div class="sub">as of T{s.turn:02d}{' · ' + esc(s.skill) if s.skill else ''} · each feature's stage from
{esc(', '.join(f'{k} ({n})' for k, n in via.items())) or 'no features'}</div>
{charts.tiles(tiles)}
<h2>From goals to milestones</h2>
<p class="legend">Left to right: the brief's goals; the spec's features in bands by stage; the pipelines whose
Covers name their requirements, the line thicker for more requirements; the milestones that list those pipelines,
dashed. A box with an amber border is a goal no feature serves or a feature no pipeline covers. Hover a box or line
for detail; click a box for that node in the final plan.</p>
<div class="scroll">{trace_svg(t, href)}</div>
<h2>Goals</h2>
<p class="legend">A requirement counts for a goal through the features that serve it. On a pipeline: a pipeline or one
of its steps covers it. On a test: a golden case covers it. On a task: a planned task covers it (only the milestones
with a plan have tasks).</p>
{goals}
<h2>Stages and features</h2>
<p class="legend">Each feature opens to its requirements and what covers each one. <span class="bad">—</span> under
Pipelines is a requirement no design holds yet.</p>
{stages}"""
    path = d / "trace.html"
    path.write_text(page(f"Goals to build · {run_title(plan)}", " · ".join(nav), body), encoding="utf-8")
    return path


# ---------------------------------------------------------------- T<nn>.html


def expects_table(n: dict) -> str:
    rows = []
    order = ["acceptance", "criteria", "verify", "reads", "writes", "tests", "covers"]
    ex = n["expects"]
    for k in [*[k for k in order if k in ex], *[k for k in ex if k not in order]]:
        v = ex[k]
        if v in (None, "", []):
            continue
        if k in ("acceptance", "criteria") and isinstance(v, list):
            cell = "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in v) + "</ul>"
        elif isinstance(v, list):
            code = k in ("verify", "writes", "reads")
            cell = " · ".join((f"<code>{esc(x)}</code>" if code else esc(x)) for x in v)
        else:
            cell = esc(v)
        rows.append(f"<tr><td>{esc(k)}</td><td>{cell}</td></tr>")
    return "<table>" + "".join(rows) + "</table>" if rows else ""


def diff_table(ch: list) -> str:
    rows = []
    for field, cat, a, b in ch:
        if isinstance(a, (list, set)) or isinstance(b, (list, set)):
            la, lb = list(a or []), list(b or [])
            gone = [x for x in la if x not in lb]
            new = [x for x in lb if x not in la]
            cell = "".join(f'<div class="was">− {esc(x)}</div>' for x in gone) + "".join(
                f'<div class="now">+ {esc(x)}</div>' for x in new) or "reordered"
        else:
            cell = f'<span class="was">{esc(a if a not in (None, "") else "—")}</span> → <span class="now">{esc(b if b not in (None, "") else "—")}</span>'
        rows.append(f"<tr><td>{esc(field)}</td><td>{cell}</td></tr>")
    return '<table class="diff">' + "".join(rows) + "</table>"


LISTED = ("depends", "implements", "covers", "serves")  # edge kinds shown as one comma list
BACK = {"implements": "implemented by", "verifies": "verified by", "covers": "covered by", "serves": "served by"}


def edges_block(s: Snap, nid: str, link) -> str:
    rows = []
    for kind, vals in sorted(s.out.get(nid, {}).items()):
        items = []
        for e in [e for e in s.edges if e["from"] == nid and e["kind"] == kind]:
            extra = (f" — mitigated by {esc(e['mitigated_by'])}" if e["mitigated_by"]
                     else f" — none: {esc(e['reason'])}" if e["reason"] else "")
            items.append(link(e["to"]) + extra)
        label = "depends on" if kind == "depends" else kind
        rows.append(f"<tr><td>{esc(label)}</td><td>{(', ' if kind in LISTED else '<br>').join(items)}</td></tr>")
    back = s.into.get(nid, [])
    for kind, label in BACK.items():
        who = sorted((e["from"] for e in back if e["kind"] == kind), key=natural)
        if who:
            rows.append(f"<tr><td>{label}</td><td>{', '.join(link(w) for w in who)}</td></tr>")
    return "<table>" + "".join(rows) + "</table>" if rows else ""


def write_turn(plan: Plan, s: Snap, d: Path) -> Path:
    prev = None
    for x in plan.snaps:
        if x.turn < s.turn:
            prev = x
    removed = {k: prev.nodes[k] for k in s.removed} if prev else {}
    present = {**s.nodes, **removed}
    kids: dict[str, list[str]] = {}
    roots = []
    for k, n in present.items():
        p = n["parent"]
        if p and p in present and p != k:
            kids.setdefault(p, []).append(k)
        else:
            roots.append(k)
    lvl_i = {lv: i for i, lv in enumerate(plan.levels)}

    def order(ids):
        return sorted(ids, key=lambda k: (lvl_i.get(present[k]["level"], 99), natural(k)))

    def link(k):
        return f'<a href="#{anchor(k)}">{esc(k)}</a>' if k in present else esc(k)

    loud: dict[str, bool] = {}

    def is_loud(k) -> bool:
        if k not in loud:
            loud[k] = k in s.added or k in s.changed or k in removed or any(is_loud(c) for c in kids.get(k, []))
        return loud[k]

    def block(k) -> str:
        n = present[k]
        how = "add" if k in s.added else "rem" if k in removed else "chg" if k in s.changed else ""
        mark = {"add": "added", "rem": "removed", "chg": "changed: " + ", ".join(c[0] for c in s.changed.get(k, []))}.get(how, "")
        a = n["attrs"]
        tags = [str(a[x]) for x in ("kind", "size", "mode") if a.get(x)]
        if n["status"]:
            tags.append(n["status"])
        st = ""
        if k in s.status:
            b4, af = s.status[k]
            st = f'<span class="mark st">status {esc(b4 or "—")} → {esc(af or "—")}</span>'
        summ = (f'<span class="lvl">{esc(n["level"])}</span><span class="nid">{esc(k)}</span><span class="ttl">'
                f'{esc(n["title"])}</span><span class="tags">{esc(" · ".join(tags))}</span>'
                + (f'<span class="mark {how}">{esc(mark)}</span>' if mark else "") + st)
        body = []
        if k in s.changed:
            body.append(diff_table(s.changed[k]))
        other = {x: v for x, v in a.items() if x not in ("kind", "size", "mode", "status")}
        if other:
            body.append("<table>" + "".join(f"<tr><td>{esc(x)}</td><td>{list_cell(v)}</td></tr>" for x, v in other.items())
                        + "</table>")
        body.append(expects_table(n))
        body.append(edges_block(s if how != "rem" else prev, k, link))
        inner = "".join(x for x in body if x)
        ch = order(kids.get(k, []))
        cls = (how + ("" if is_loud(k) else " quiet")).strip()
        if not inner and not ch:
            return f'<div class="leaf {cls}" id="{anchor(k)}">{summ}</div>'
        is_open = ch or how in ("add", "chg")
        return (f'<details class="{cls}" id="{anchor(k)}"{" open" if is_open else ""}><summary>{summ}</summary>'
                f'<div class="nbody">{inner}</div>'
                + (f'<div class="kids">{"".join(block(c) for c in ch)}</div>' if ch else "") + "</details>")

    by_level: dict[str, list[str]] = {}
    for k in order(roots):
        by_level.setdefault(present[k]["level"], []).append(k)
    sections = "".join(f'<div class="{"" if any(is_loud(k) for k in ids) else "quiet"}"><h2>{esc(PLURAL.get(lv, lv))}</h2>'
                       + "".join(block(k) for k in ids) + "</div>" for lv, ids in by_level.items())

    changed = plan.changed
    i = next((j for j, x in enumerate(changed) if x.turn == s.turn), None)
    nav = back_nav(plan)
    if i is not None and i > 0:
        nav.append(f'<a href="{tpage(changed[i - 1].turn)}">← T{changed[i - 1].turn:02d}</a>')
    if i is not None and i + 1 < len(changed):
        nav.append(f'<a href="{tpage(changed[i + 1].turn)}">T{changed[i + 1].turn:02d} →</a>')
    if (plan.out / "turns" / f"T{s.turn:02d}.html").exists():
        nav.append(f'<a href="../turns/T{s.turn:02d}.html">what turn T{s.turn:02d} did</a>')
    ms = [m for m in plan.milestones() if any(n["level"] == "task" and n["parent"] == m for n in s.nodes.values())]
    nav += [f'<a href="{mpage(m)}">{esc(m)} build view</a>' for m in ms]
    later = [x.turn for x in plan.snaps if x.turn > s.turn and (i is None or i + 1 >= len(changed) or x.turn < changed[i + 1].turn)]
    span = f"T{s.turn:02d}" + (f"–T{later[-1]:02d}" if later else "")
    summary = (f"{len(s.added)} added, {len(s.changed)} changed, {len(s.removed)} removed"
               + (f", {len(s.status)} status changes (shown with the box below)" if s.status else "")
               + f". In force for {span}.")
    steps = plan.doc_steps(s.turn)
    body = f"""<h1>Plan as of T{s.turn:02d}{' · ' + esc(s.skill) if s.skill else ''}</h1>
<div class="sub">commit <code>{esc(s.commit or '—')}</code> · {esc(s.ts[:16].replace('T', ' ') or '—')} · {len(s.nodes)} nodes, {len(s.edges)} edges</div>
<p>{esc(summary)}{' Written at ' + esc('; '.join(steps[:6])) + '.' if steps else ''}</p>
<p class="legend"><span class="chip add">added</span><span class="chip chg">changed, with its field diff</span>
<span class="chip rem">removed</span> Each node opens to its attributes, expectations and edges.</p>
{toggles(plan, quiet=True)}
<div class="tree">{sections or '<p>No nodes.</p>'}</div>"""
    path = d / tpage(s.turn)
    path.write_text(page(f"Plan T{s.turn:02d}", " · ".join(nav), body), encoding="utf-8")
    return path


# ---------------------------------------------------------------- M<n>.html


NW, NH, CW, LW, TOP, VG = 164, 56, 194, 112, 40, 12
LINE1, LINE2 = 21, 26  # title characters on a box's first line (after the id) and second


def wrap2(title: str, first: int = LINE1, second: int = LINE2) -> tuple[str, str]:
    """A title on two lines, broken at a space where one fits; the second is cut with …."""
    if len(title) <= first:
        return title, ""
    cut = title.rfind(" ", 0, first + 1)
    if cut <= first // 3:
        cut = first
    return title[:cut].rstrip(), fit(title[cut:].strip(), second)


def node_tip(g: Graph, t: str, half: str) -> str:
    n = g.snap.nodes[t]
    a = n["attrs"]
    deps = ", ".join(g.deps[t]) or "—"
    writes = ", ".join(n["expects"].get("writes") or []) or "—"
    what = {"test": "tester half", "impl": "implementer half"}.get(half, "")
    return (f"{t} · {n['title']}" + (f" ({what})" if what else "")
            + f"\n{' · '.join(str(a[x]) for x in ('kind', 'size', 'mode') if a.get(x)) or 'no kind'}"
            + (f" · {n['status']}" if n["status"] else "")
            + f"\ndepends on: {deps}\nwrites: {writes}" + ("\non the critical path" if any(k[0] == t for k in g.cp_segments) else ""))


def graph_svg(g: Graph, turn: int) -> str:
    place, lanes, rows = g.layout()
    if not place:
        return "<p>No tasks.</p>"
    lane_h = {ln: rows[ln] * (NH + VG) + VG for ln in lanes}
    lane_y, acc = {}, TOP
    for ln in lanes:
        lane_y[ln] = acc
        acc += lane_h[ln]
    width = LW + g.n_waves * CW + 10
    height = acc + 8

    def xy(k):
        w, ln, slot = place[k]
        return LW + w * CW + (CW - NW) / 2, lane_y[ln] + VG / 2 + slot * (NH + VG) + 2

    out = []
    for i, ln in enumerate(lanes):
        n = sum(1 for t in g.tasks if g.kind[t["id"]] == ln)
        out.append(f'<rect x="0" y="{lane_y[ln]}" width="{width}" height="{lane_h[ln]}" class="lane{i % 2}"/>'
                   f'<rect x="4" y="{lane_y[ln] + 6}" width="4" height="{lane_h[ln] - 12}" rx="2" '
                   f'class="{KIND_COLOR.get(ln, "cx")}"/>'
                   f'<text x="14" y="{lane_y[ln] + 20}" class="lanel">{esc(ln or "(no kind)")}</text>'
                   f'<text x="14" y="{lane_y[ln] + 34}">{n} task{"" if n == 1 else "s"}</text>')
    for w in range(g.n_waves):
        x = LW + w * CW
        out.append(f'<line x1="{x}" y1="{TOP - 6}" x2="{x}" y2="{height}" class="grid"/>'
                   f'<text x="{x + CW / 2}" y="16" text-anchor="middle" class="head">W{w}</text>'
                   f'<text x="{x + CW / 2}" y="30" text-anchor="middle">{len(g.waves[w])} agent'
                   f'{"" if len(g.waves[w]) == 1 else "s"}</text>')
    edges, labels = [], []
    for k, ps in g.preds.items():
        for p in ps:
            x1, y1 = xy(p)
            x2, y2 = xy(k)
            ax, ay, bx, by = x1 + NW, y1 + NH / 2, x2, y2 + NH / 2
            cp = (p, k) in g.cp_pairs
            inside = p[0] == k[0]
            unb = g.kind.get(p[0]) == "interface"
            ent = g.entry_pairs.get((k[0], p[0])) if not inside else None
            cls = "e" + (" cp" if cp else " sp" if inside else " unb" if unb else "") + (" ent" if ent else "")
            dx = max(30, (bx - ax) / 2)
            what = ("tester then implementer" if inside
                    else f"{k[0]}'s tester waits on the interface {p[0]}" if k[1] == "test"
                    else f"{k[0]} depends on {p[0]}" + (" (unblocked by the interface)" if unb else ""))
            if ent:
                what += f"; both write {', '.join(ent)}: a shared entry module serializes two wiring tasks"
            mark = "aent" if ent else "acp" if cp else "a"
            if ent:  # by the arrowhead, over the boxes: the gap between two waves is narrow and edges cross
                labels.append(f'<text x="{bx - 15:.1f}" y="{by - 6:.1f}" text-anchor="middle" '
                              f'class="entl"><title>{esc(what)}</title>entry</text>')
            edges.append((cp or bool(ent), f'<path d="M{ax:.1f},{ay:.1f} C{ax + dx:.1f},{ay:.1f} {bx - dx:.1f},{by:.1f} {bx:.1f},{by:.1f}" '
                                           f'class="{cls}" marker-end="url(#{mark})"><title>{esc(what)}</title></path>'))
    out += [e for top, e in edges if not top] + [e for top, e in edges if top]
    for k in place:
        t, half = k
        x, y = xy(k)
        n = g.snap.nodes[t]
        a = n["attrs"]
        kind = g.kind[t]
        on_cp = k in g.cp_segments
        meta = " · ".join(str(a[x_]) for x_ in ("size", "mode") if a.get(x_))
        if half:
            meta = ("tester" if half == "test" else "implementer") + (f" · {a.get('size')}" if a.get("size") else "")
        done = n["status"].lower() in ("done", "complete", "completed")
        tip = node_tip(g, t, half)
        if kind == "interface":
            shape = (f'<polygon points="{x},{y + NH / 2} {x + NW / 2},{y - 8} {x + NW},{y + NH / 2} {x + NW / 2},{y + NH + 8}" '
                     f'class="nb iface{" cpn" if on_cp else ""}"/>')
            ok = ' <tspan class="done">✓</tspan>' if done else ""
            text = (f'<text x="{x + NW / 2}" y="{y + 18}" text-anchor="middle" class="nid">{esc(short(t, g.mid))}{ok}</text>'
                    f'<text x="{x + NW / 2}" y="{y + 31}" text-anchor="middle" class="ntl">{esc(fit(n["title"], 18))}</text>'
                    f'<text x="{x + NW / 2}" y="{y + 44}" text-anchor="middle" class="nmeta">{esc(meta)}</text>')
            done = False
        else:
            shape = (f'<rect x="{x}" y="{y}" width="{NW}" height="{NH}" rx="6" class="nb{" cpn" if on_cp else ""}'
                     f'{" half" if half == "test" else ""}"/>'
                     f'<rect x="{x}" y="{y}" width="5" height="{NH}" rx="2" class="{KIND_COLOR.get(kind, "cx")}"/>')
            sid = short(t, g.mid)
            l1, l2 = wrap2(n["title"], LINE1 + 4 - len(sid))
            text = (f'<text x="{x + 11}" y="{y + 15}"><tspan class="nid">{esc(sid)}</tspan> '
                    f'<tspan class="ntl">{esc(l1)}</tspan></text>'
                    + (f'<text x="{x + 11}" y="{y + 29}" class="ntl">{esc(l2)}</text>' if l2 else "")
                    + f'<text x="{x + 11}" y="{y + 46}" class="nmeta">{esc(meta)}</text>')
        tick = f'<text x="{x + NW - 6}" y="{y + 15}" text-anchor="end" class="done">✓</text>' if done else ""
        out.append(f'<a href="{tpage(turn)}#{anchor(t)}"><g><title>{esc(tip)}</title>{shape}{text}{tick}</g></a>')
    out += labels
    defs = ('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">'
            '<path d="M0,0 L10,5 L0,10 z" class="arrowhead"/></marker>'
            '<marker id="acp" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">'
            '<path d="M0,0 L10,5 L0,10 z" class="arrowcp"/></marker>'
            '<marker id="aent" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">'
            '<path d="M0,0 L10,5 L0,10 z" class="arrowent"/></marker></defs>')
    return (f'<svg class="mg" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="Build waves of {esc(g.mid)}">{defs}{"".join(out)}</svg>')


def thumb_svg(g: Graph, tw: int = 168, th: int = 86) -> str:
    place, lanes, rows = g.layout()
    total = sum(rows.values()) or 1
    off, acc = {}, 0
    for ln in lanes:
        off[ln] = acc
        acc += rows[ln]
    cw = (tw - 8) / max(g.n_waves, 1)
    rh = (th - 8) / total

    def xy(k):
        w, ln, slot = place[k]
        return 4 + w * cw + cw / 2 + (-cw / 5 if k[1] == "test" else cw / 5 if k[1] == "impl" else 0), 4 + (off[ln] + slot) * rh + rh / 2

    out = []
    for k, ps in g.preds.items():
        for p in ps:
            (x1, y1), (x2, y2) = xy(p), xy(k)
            cp = (p, k) in g.cp_pairs
            ent = p[0] != k[0] and (k[0], p[0]) in g.entry_pairs
            out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                       f'class="e{" cp" if cp else ""}{" ent" if ent else ""}"/>')
    for k in place:
        x, y = xy(k)
        r = min(4.0, rh / 2.4, cw / 5)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(r, 1.6):.1f}" class="{KIND_COLOR.get(g.kind[k[0]], "cx")}"/>')
    return (f'<svg class="th" xmlns="http://www.w3.org/2000/svg" width="{tw}" height="{th}" viewBox="0 0 {tw} {th}" '
            f'role="img" aria-label="{esc(g.mid)} graph">{"".join(out)}</svg>')


def write_milestone(plan: Plan, mid: str, d: Path) -> Path:
    s = last_with_tasks(plan, mid)
    g = Graph(s, mid)
    m = g.metrics()
    node = plan.ever.get(mid) or {"title": "", "status": "", "expects": {}}
    theirs = s.builds.get(mid) or {}
    tiles = [(str(m["tasks"]), "tasks", ""),
             (str(m["cp"]), "critical path (tasks)", f'<i class="{"bad" if m["cp"] > CP_CAP else "ok"}">cap {CP_CAP}</i>'
              + (f" <i>· {len(g.cp_lanes)} lanes tie</i>" if len(g.cp_lanes) > 1 else "")),
             (str(m["waves"]), "waves of boxes (tester and implementer apart)",
              f"<i>whole tasks: {m['task_waves']}</i>"),
             (f"{m['widest']} boxes", "agents in the widest wave", f"<i>({m['widest_tasks']} whole tasks)</i>"),
             (f"{m['parallelism']:.1f}", "parallelism (tasks ÷ critical path)", ""),
             (f"{m['dc_mitigated']}/{m['dc']}" if m["dc"] else "—", "data and call edges mitigated",
              f"<i>{m['dc_mitigated'] / m['dc']:.0%}</i>" if m["dc"] else "")]
    notes = []
    if m["unmitigated"]:
        parts = [f'<span class="{"warnp" if c in REASON_FLAG else ""}" title="{esc(REASON_TIP.get(c, ""))}">'
                 f'{esc(c)} {n}</span>' for c, n in m["unmitigated"].items()]
        notes.append(f'<p>Unmitigated dependency-graph rows, {sum(m["unmitigated"].values())} of {m["edges"]}, '
                     f'by why they stay: {" · ".join(parts)}. Integration, same-module, shared-file, order and '
                     f'contract-change rows can never be mitigated; the rest are worth a look. Hover a class for '
                     f'what it means.</p>')
    if theirs:
        tw = [list(w) for w in theirs.get("waves") or []]
        tcp = list(theirs.get("critical_path") or [])
        agree = tw == g.task_waves and len(tcp) == len(g.cp)
        notes.append(f'<p class="{"" if agree else "warnp"}">The producer says: {esc(theirs.get("state") or "no state")}, '
                     f'critical path {len(tcp)} ({esc(" → ".join(tcp) or "—")}), {len(tw)} waves of whole tasks, widest '
                     f'{max((len(w) for w in tw), default=0)}. '
                     + ("Recomputed here from <code>depends</code> edges: the same." if agree else
                        f"Recomputed here from <code>depends</code> edges: critical path {len(g.cp)}, "
                        f"{len(g.task_waves)} waves of whole tasks ({esc(' | '.join(', '.join(w) for w in g.task_waves))}).")
                     + "</p>")
    if g.entry_pairs:
        by_files: dict[tuple, list[str]] = {}
        for (t, dep), f in g.entry_pairs.items():
            by_files.setdefault(tuple(f), []).append(f"{short(dep, mid)} → {short(t, mid)}")
        on_cp = sum(1 for t, dep in g.entry_pairs if any(p[0] == dep and k[0] == t for p, k in g.cp_pairs))
        groups = "; ".join(f'{esc(", ".join(f))}: {esc(", ".join(e))}' for f, e in by_files.items())
        notes.append(f'<p class="warnp">{len(g.entry_pairs)} wiring → wiring edge{"" if len(g.entry_pairs) == 1 else "s"} '
                     f'through a shared entry module, {on_cp} on the critical path. Both tasks write {groups}. '
                     f'Each only serializes two wiring tasks; drawn in orange on the map.</p>')
    if g.cycles:
        notes.append(f'<p class="bad">Cycle in depends: dropped {esc(", ".join(f"{a} → {b}" for a, b in g.cycles))} to draw it.</p>')
    if not g.interface_first and any(g.split.values()):
        notes.append('<p class="legend">No task here has kind <code>interface</code>, so each tester half waits on '
                     'everything its task depends on.</p>')
    width_rows = "".join(
        f"<tr><td>W{w}</td><td>{len(segs)}</td><td>{esc(', '.join(short(k[0], mid) + {'test': ' (tester)', 'impl': ' (implementer)'}.get(k[1], '') for k in segs))}</td></tr>"
        for w, segs in enumerate(g.waves))
    edge_rows = "".join(
        f"<tr><td>{esc(e['from'])}</td><td>{esc(e['to'])}</td><td>{esc(e['kind'])}</td>"
        f"<td class=\"{'ok' if e['mitigated_by'] else ''}\">{esc(e['mitigated_by'] or ('none: ' + e['reason'] if e['reason'] else 'none'))}</td>"
        f"<td class=\"{'warnp' if g.reason_class(e) in REASON_FLAG or g.shared_entry(e['from'], e['to']) else ''}\">"
        f"{esc(g.reason_class(e) or '—')}{' · shared entry module' if g.shared_entry(e['from'], e['to']) else ''}</td>"
        f"<td>{'yes' if e['to'] in g.deps.get(e['from'], []) else 'no'}</td></tr>"
        for e in sorted(g.graph_edges, key=lambda e: (natural(e["from"]), natural(e["to"]))))
    ext = "".join(f"<li>{esc(e['from'])} → {esc(e['to'])}</li>" for e in g.external)
    # thumbnails: each turn this milestone's graph took a new shape
    thumbs, last_sig, shown = [], None, g.signature()
    for x in plan.snaps:
        if not any(n["level"] == "task" and n["parent"] == mid for n in x.nodes.values()):
            continue
        gx = Graph(x, mid)
        sig = gx.signature()
        if sig == last_sig:
            continue
        last_sig = sig
        mx = gx.metrics()
        thumbs.append(f'<a class="thumb{" cur" if sig == shown else ""}" href="{tpage(plan.page_for(x.turn).turn) if plan.page_for(x.turn) else "#"}">'
                      f'{thumb_svg(gx)}<div><b>T{x.turn:02d}</b> · {mx["tasks"]} tasks · CP {mx["cp"]} · widest {mx["widest"]}</div></a>')
    nav = back_nav(plan)
    nav.append(f'<a href="{tpage(plan.page_for(s.turn).turn) if plan.page_for(s.turn) else "#"}">the plan as of T{s.turn:02d}</a>')
    nav += [f'<a href="{mpage(o)}">{esc(o)}</a>' for o in plan.milestones() if o != mid]
    cp = "; ".join(" → ".join(short(alt[0], mid) if len(alt) == 1 else "(" + " | ".join(short(t, mid) for t in alt) + ")"
                              for alt in lane) for lane in g.cp_lanes)
    body = f"""<h1>{esc(mid)} · {esc(node['title'])} · build view</h1>
<div class="sub">as of T{s.turn:02d}{' · ' + esc(s.skill) if s.skill else ''} · {esc(node.get('status') or 'no status')}
 · critical path{f"s ({len(g.cp_lanes)} lanes tie)" if len(g.cp_lanes) > 1 else ""} {esc(cp or '—')}</div>
{charts.tiles(tiles)}
{''.join(notes)}
<h2>Waves</h2>
<p class="legend">Left to right is the order work can start: a task sits in the first wave after everything it depends
on. Rows are task kinds. <span class="c6 sw" style="transform:rotate(45deg)"></span>An interface task is a diamond;
dashed edges are what it unblocks. Solid edges are other <code>depends</code>; a split task is two boxes, the tester
(dashed border) then the implementer. A tester waits only on the interface: the interface tasks among its task's
ancestors, else all of the milestone's. Waves count boxes, so a split task can take two. The critical path is the thick
line and the bold boxes, every tied one drawn (in the line above, a lane's alternatives are in brackets); ✓ is done. An
orange edge marked "entry" joins two wiring tasks that write the same entry module (<code>__main__.py</code> or <code>pipeline.py</code>). Edges
an interface mitigates do not order the tasks and are listed below, not drawn. Hover a box for its dependencies and
writes; click it for the task on the turn's page.</p>
<div class="scroll">{graph_svg(g, plan.page_for(s.turn).turn if plan.page_for(s.turn) else s.turn)}</div>
<h2>Agents per wave</h2>
<table><tr><th>Wave</th><th>Agents</th><th>Segments</th></tr>{width_rows}</table>
<h2>Dependency graph</h2>
{('<table><tr><th>From</th><th>To</th><th>Kind</th><th>Mitigated by</th><th>Why it stays</th><th>In depends</th></tr>' + edge_rows + '</table>') if edge_rows else '<p>No dependency-graph rows for this milestone.</p>'}
{f'<p>Depends on tasks outside {esc(mid)}:</p><ul>{ext}</ul>' if ext else ''}
<h2>How the graph changed</h2>
<p class="legend">One thumbnail per turn that gave this milestone's graph a new shape (tasks, kinds, modes or depends);
the outlined one is drawn above. Click one for the plan as of that turn.</p>
<div class="thumbs">{''.join(thumbs)}</div>"""
    path = d / mpage(mid)
    path.write_text(page(f"{mid} build view", " · ".join(nav), body), encoding="utf-8")
    return path


# ---------------------------------------------------------------- entry points


def write(out: Path) -> Path | None:
    """Draw `out/plan/` from `out/plan.json`; the index page, or None when there is no plan."""
    out = Path(out)
    plan = load(out)
    if plan is None or not plan.snaps:
        return None
    d = out / "plan"
    d.mkdir(exist_ok=True)
    for s in plan.changed:
        write_turn(plan, s, d)
    for mid in plan.milestones():
        write_milestone(plan, mid, d)
    if has_trace(plan.final):
        write_trace(plan, d)
    return write_index(plan, d)


def section(out: Path) -> str:
    """The Plan section of `flow.html`, or "" when the run has no plan.json."""
    plan = load(Path(out))
    if plan is None or not plan.snaps or not (Path(out) / "plan" / "index.html").exists():
        return ""
    f = plan.final
    counts = ", ".join(f"{len(f.by_level(lv))} {PLURAL.get(lv, lv).lower()}" for lv in plan.levels if f.by_level(lv))
    ms = " · ".join(f'<a href="plan/{mpage(m)}">{esc(m)} build view</a>' for m in plan.milestones())
    trace = (' <a href="plan/trace.html">Goals to build</a>: goals through features and stages to pipelines and '
             'milestones.' if (Path(out) / "plan" / "trace.html").exists() and has_trace(f) else "")
    return (f'<h2>Plan</h2><p>The plan this run wrote: {esc(counts) or "no nodes"}, changed in {len(plan.changed)} '
            f'turns. <a href="plan/index.html"><b>Plan map</b></a>: how it grew turn by turn, and every node against '
            f'the turns that changed it.{trace}{" " + ms if ms else ""}</p>')


def turn_link(out: Path, n: int) -> str:
    """A line for the run's turn page `turns/T<nn>.html`: the plan as of that turn."""
    plan = load(Path(out))
    if plan is None or not (Path(out) / "plan" / "index.html").exists():
        return ""
    s = plan.page_for(n)
    if s is None:
        return ""
    here = next((x for x in plan.snaps if x.turn == n), None)
    what = (f"this turn changed the plan (+{len(here.added)} ~{len(here.changed)} −{len(here.removed)})"
            if here and here.kind == "changed" else f"unchanged since T{s.turn:02d}")
    return (f'<p class="top"><a href="../plan/{tpage(s.turn)}">The plan as of T{n:02d}</a>: {esc(what)} · '
            f'<a href="../plan/index.html">plan map</a></p>')


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(sys.argv) == 2 else 2
    path = write(Path(sys.argv[1]))
    if path is None:
        print(f"planmap: no readable plan.json in {sys.argv[1]}", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
