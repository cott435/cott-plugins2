#!/usr/bin/env python3
"""Draw the plan a run wrote, from its `plan.json`: how it grew turn by turn, and per milestone
what would be built in parallel and what in series.

`plan.json` (schema `plan-map/1`) sits in a run's workspace beside `index.json`. A producer
(dev-team's `planexport.py`, or anything else) writes it; nothing here knows dev-team:

  {"schema": "plan-map/1", "producer": "...", "levels": ["stage", "milestone", "task", ...],
   "snapshots": [{"turn": 14, "commit": "ab12", "ts": "...", "skill": "build-planning",
                  "nodes": [{"id", "level", "parent", "title", "hash", "attrs": {...},
                             "expects": {"acceptance", "verify", "reads", "writes", "tests", ...}}],
                  "edges": [{"from", "to", "kind", "mitigated_by"?, "reason"?}],
                  "builds": [{"milestone", "state", "critical_path", "waves"}]},
                 {"turn": 15, "same_as": 14}]}

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
  T<nn>.html  the plan as of that turn as a tree, what it added, changed and removed marked,
              each node's expectations.
  M<n>.html   one milestone's build: columns are waves, lanes are task kinds; interface tasks
              are diamonds whose "unblocks" edges are dashed; a split task is two segments,
              tester then implementer; the critical path is thick. Waves are the longest path
              to each segment; a barycenter pass orders each cell. Metrics, the producer's own
              numbers beside them, and a thumbnail per turn that changed the graph.

`write(out)` draws them and returns `plan/index.html`, or None when `out/plan.json` is absent
or unreadable. `flow.write_html` calls it, adds a Plan section to `flow.html`, and links each
turn page to the plan as of that turn.

Usage: planmap.py DIR        re-render DIR/plan/ from DIR/plan.json
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import charts
import flow

SCHEMA = "plan-map/1"
LEVELS = ["stage", "milestone", "task", "pipeline", "step", "test", "type", "symbol"]
KINDS = ["interface", "spine", "wiring", "thicken", "system"]
KIND_COLOR = {"interface": "c6", "spine": "c0", "wiring": "c2", "thicken": "c1", "system": "c3"}
GRAPH_KINDS = ("data", "call", "file", "code", "contract-change", "order")
SIZE_W = {"XS": 1, "S": 2, "M": 4, "L": 8, "XL": 16}
CP_CAP = 15
PLURAL = {"stage": "Stages", "milestone": "Milestones", "task": "Tasks", "pipeline": "Pipelines",
          "step": "Steps", "test": "Tests", "type": "Types", "symbol": "Symbols"}
TITLED = {"stage", "milestone", "pipeline"}  # levels whose ledger chips carry the title
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
        elif self.schema != SCHEMA:
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
    implementer. The tester half waits only on the interface tasks the task depends on (when
    the milestone has any; otherwise on all of them); the implementer on its tester and the
    task's dependencies."""

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
        self.cycles: list[tuple[str, str]] = []
        self._segments()
        self._layers()
        self._critical_path()
        self._task_waves()

    def last(self, t: str) -> tuple[str, str]:
        return (t, "impl") if self.split[t] else (t, "")

    def _segments(self) -> None:
        self.preds: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for t in sorted(self.ids, key=natural):
            deps = [self.last(d) for d in self.deps[t]]
            if self.split[t]:
                tdeps = [self.last(d) for d in self.deps[t] if self.kind[d] == "interface"] \
                    if self.interface_first else deps
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
        """A longest path. Ties go to the producer's own critical path, then to an edge between
        two tasks over one inside a split task, then to the heavier size, then to the id."""
        self.cp_segments: list[tuple[str, str]] = []
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
        self.cp_segments = path
        self.cp = list(dict.fromkeys(k[0] for k in path))
        self.cp_pairs = set(zip(path, path[1:]))

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

    def metrics(self) -> dict:
        width = [len(w) for w in self.waves]
        mitigated = [e for e in self.graph_edges if e["mitigated_by"]]
        return {"tasks": len(self.tasks), "cp": len(self.cp), "waves": self.n_waves, "width": width,
                "widest": max(width, default=0), "parallelism": len(self.tasks) / len(self.cp) if self.cp else 0.0,
                "edges": len(self.graph_edges), "mitigated": len(mitigated)}


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
svg .arrowhead{fill:var(--muted)}svg .arrowcp{fill:var(--fg)}svg a:hover .nb{stroke:var(--fg)}
.thumbs{display:flex;flex-wrap:wrap;gap:10px}.thumb{border:1px solid var(--line);border-radius:6px;padding:4px 6px;
background:var(--box);font-size:11.5px;color:var(--muted);text-decoration:none}.thumb.cur{border-color:var(--fg)}
.thumb b{color:var(--fg)}svg.th .e{stroke-width:1}svg.th .e.cp{stroke-width:2}
.warnp{color:var(--warn)}
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
        mitigated = f"{m['mitigated']} of {m['edges']}" if m["edges"] else "—"
        rows.append(f'<tr><td><a href="{mpage(mid)}"><b>{esc(mid)}</b></a></td><td>{esc(node["title"])}'
                    f'{"" if alive or mid not in plan.ever else " <span class=bad>(removed)</span>"}</td>'
                    f'<td>{esc(node.get("status") or "—")}</td><td>T{s.turn:02d}</td><td>{m["tasks"]}</td>'
                    f'<td class="{"bad" if m["cp"] > CP_CAP else ""}">{m["cp"]}</td><td>{m["waves"]}</td>'
                    f'<td>{m["widest"]}</td><td>{m["parallelism"]:.1f}</td>'
                    f'<td>{mitigated}</td></tr>')
    if not rows:
        return "<p>No milestone has tasks yet.</p>"
    return ('<table><tr><th>Milestone</th><th>Title</th><th>Status</th><th>As of</th><th>Tasks</th><th>Critical path</th>'
            '<th>Waves</th><th>Widest wave</th><th>Parallelism</th><th>Edges mitigated</th></tr>' + "".join(rows) + "</table>")


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
    body = f"""<h1>Plan map · {esc(run_title(plan))}</h1>
<div class="sub">{esc(plan.producer or 'unknown producer')} · {esc(plan.schema or 'no schema')} · {len(plan.snaps)} snapshots,
turns T{plan.snaps[0].turn:02d}–T{plan.snaps[-1].turn:02d}</div>
{notes}
{charts.tiles(tiles)}
<h2>Milestones</h2>
<p class="legend">Each opens its build view: what would run in parallel and what in series. Critical path is in tasks
(cap {CP_CAP}); parallelism is tasks ÷ critical path; edges mitigated are the dependency-graph rows an interface
removes from the order.</p>
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


# ---------------------------------------------------------------- T<nn>.html


def expects_table(n: dict) -> str:
    rows = []
    order = ["acceptance", "verify", "reads", "writes", "tests", "covers"]
    ex = n["expects"]
    for k in [*[k for k in order if k in ex], *[k for k in ex if k not in order]]:
        v = ex[k]
        if v in (None, "", []):
            continue
        if k == "acceptance" and isinstance(v, list):
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


def edges_block(s: Snap, nid: str, link) -> str:
    rows = []
    for kind, vals in sorted(s.out.get(nid, {}).items()):
        items = []
        for e in [e for e in s.edges if e["from"] == nid and e["kind"] == kind]:
            extra = (f" — mitigated by {esc(e['mitigated_by'])}" if e["mitigated_by"]
                     else f" — none: {esc(e['reason'])}" if e["reason"] else "")
            items.append(link(e["to"]) + extra)
        label = "depends on" if kind == "depends" else kind
        rows.append(f"<tr><td>{esc(label)}</td><td>{(', ' if kind in ('depends', 'implements') else '<br>').join(items)}</td></tr>")
    back = [e for e in s.into.get(nid, []) if e["kind"] in ("verifies", "implements")]
    for kind in ("implements", "verifies"):
        who = [link(e["from"]) for e in back if e["kind"] == kind]
        if who:
            rows.append(f"<tr><td>{'implemented by' if kind == 'implements' else 'verified by'}</td><td>{', '.join(who)}</td></tr>")
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


NW, NH, CW, LW, TOP, VG = 148, 42, 178, 112, 40, 12


def node_tip(g: Graph, t: str, half: str) -> str:
    n = g.snap.nodes[t]
    a = n["attrs"]
    deps = ", ".join(g.deps[t]) or "—"
    writes = ", ".join(n["expects"].get("writes") or []) or "—"
    what = {"test": "tester half", "impl": "implementer half"}.get(half, "")
    return (f"{t} · {n['title']}" + (f" ({what})" if what else "")
            + f"\n{' · '.join(str(a[x]) for x in ('kind', 'size', 'mode') if a.get(x)) or 'no kind'}"
            + (f" · {n['status']}" if n["status"] else "")
            + f"\ndepends on: {deps}\nwrites: {writes}" + ("\non the critical path" if t in g.cp else ""))


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
    edges = []
    for k, ps in g.preds.items():
        for p in ps:
            x1, y1 = xy(p)
            x2, y2 = xy(k)
            ax, ay, bx, by = x1 + NW, y1 + NH / 2, x2, y2 + NH / 2
            cp = (p, k) in getattr(g, "cp_pairs", set())
            inside = p[0] == k[0]
            unb = g.kind.get(p[0]) == "interface"
            cls = "e" + (" cp" if cp else " sp" if inside else " unb" if unb else "")
            dx = max(30, (bx - ax) / 2)
            what = ("tester then implementer" if inside else f"{k[0]} depends on {p[0]}"
                    + (" (unblocked by the interface)" if unb else ""))
            edges.append((cp, f'<path d="M{ax:.1f},{ay:.1f} C{ax + dx:.1f},{ay:.1f} {bx - dx:.1f},{by:.1f} {bx:.1f},{by:.1f}" '
                              f'class="{cls}" marker-end="url(#{"acp" if cp else "a"})"><title>{esc(what)}</title></path>'))
    out += [e for cp, e in edges if not cp] + [e for cp, e in edges if cp]
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
                    f'<text x="{x + NW / 2}" y="{y + 32}" text-anchor="middle" class="nmeta">{esc(meta)}</text>')
            done = False
        else:
            shape = (f'<rect x="{x}" y="{y}" width="{NW}" height="{NH}" rx="6" class="nb{" cpn" if on_cp else ""}'
                     f'{" half" if half == "test" else ""}"/>'
                     f'<rect x="{x}" y="{y}" width="5" height="{NH}" rx="2" class="{KIND_COLOR.get(kind, "cx")}"/>')
            text = (f'<text x="{x + 11}" y="{y + 16}"><tspan class="nid">{esc(short(t, g.mid))}</tspan> '
                    f'<tspan class="ntl">{esc(fit(n["title"], 17))}</tspan></text>'
                    f'<text x="{x + 11}" y="{y + 32}" class="nmeta">{esc(meta)}</text>')
        tick = f'<text x="{x + NW - 6}" y="{y + 15}" text-anchor="end" class="done">✓</text>' if done else ""
        out.append(f'<a href="{tpage(turn)}#{anchor(t)}"><g><title>{esc(tip)}</title>{shape}{text}{tick}</g></a>')
    defs = ('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">'
            '<path d="M0,0 L10,5 L0,10 z" class="arrowhead"/></marker>'
            '<marker id="acp" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">'
            '<path d="M0,0 L10,5 L0,10 z" class="arrowcp"/></marker></defs>')
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
            cp = (p, k) in getattr(g, "cp_pairs", set())
            out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="e{" cp" if cp else ""}"/>')
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
             (str(m["cp"]), "critical path (tasks)", f'<i class="{"bad" if m["cp"] > CP_CAP else "ok"}">cap {CP_CAP}</i>'),
             (str(m["waves"]), "waves", ""), (str(m["widest"]), "agents in the widest wave", ""),
             (f"{m['parallelism']:.1f}", "parallelism (tasks ÷ critical path)", ""),
             (f"{m['mitigated']}/{m['edges']}" if m["edges"] else "—", "graph edges mitigated",
              f"<i>{m['mitigated'] / m['edges']:.0%}</i>" if m["edges"] else "")]
    notes = []
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
    cp = " → ".join(short(t, mid) for t in g.cp)
    body = f"""<h1>{esc(mid)} · {esc(node['title'])} · build view</h1>
<div class="sub">as of T{s.turn:02d}{' · ' + esc(s.skill) if s.skill else ''} · {esc(node.get('status') or 'no status')}
 · critical path {esc(cp or '—')}</div>
{charts.tiles(tiles)}
{''.join(notes)}
<h2>Waves</h2>
<p class="legend">Left to right is the order work can start: a task sits in the first wave after everything it depends
on. Rows are task kinds. <span class="c6 sw" style="transform:rotate(45deg)"></span>An interface task is a diamond;
dashed edges are what it unblocks. Solid edges are other <code>depends</code>; a split task is two boxes, the tester
(dashed border) then the implementer. The critical path is the thick line and the bold boxes; ✓ is done. Edges
an interface mitigates do not order the tasks and are listed below, not drawn. Hover a box for its dependencies and
writes; click it for the task on the turn's page.</p>
<div class="scroll">{graph_svg(g, plan.page_for(s.turn).turn if plan.page_for(s.turn) else s.turn)}</div>
<h2>Agents per wave</h2>
<table><tr><th>Wave</th><th>Agents</th><th>Segments</th></tr>{width_rows}</table>
<h2>Dependency graph</h2>
{('<table><tr><th>From</th><th>To</th><th>Kind</th><th>Mitigated by</th><th>In depends</th></tr>' + edge_rows + '</table>') if edge_rows else '<p>No dependency-graph rows for this milestone.</p>'}
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
    return write_index(plan, d)


def section(out: Path) -> str:
    """The Plan section of `flow.html`, or "" when the run has no plan.json."""
    plan = load(Path(out))
    if plan is None or not plan.snaps or not (Path(out) / "plan" / "index.html").exists():
        return ""
    f = plan.final
    counts = ", ".join(f"{len(f.by_level(lv))} {PLURAL.get(lv, lv).lower()}" for lv in plan.levels if f.by_level(lv))
    ms = " · ".join(f'<a href="plan/{mpage(m)}">{esc(m)} build view</a>' for m in plan.milestones())
    return (f'<h2>Plan</h2><p>The plan this run wrote: {esc(counts) or "no nodes"}, changed in {len(plan.changed)} '
            f'turns. <a href="plan/index.html"><b>Plan map</b></a>: how it grew turn by turn, and every node against '
            f'the turns that changed it.{" " + ms if ms else ""}</p>')


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
