"""Charts shared by flow.py and compare.py, drawn from a workspace's `index.json`.

Everything is inline SVG or plain HTML. Hovering a mark shows its numbers (SVG `<title>`), and
every number a chart shows is also in a table on the same page, so nothing needs the hover.

  timeline     wall time left to right: one bar per turn of the main thread, and below it one
               bar per agent, packed into as many rows as ran at once, so stacked bars are agents
               that ran in parallel. Idle gaps longer than three minutes are cut to a short break.
  turn_bars    small multiples, one column per turn: the skill it invoked, wall time, output
               tokens (main thread and its agents), and the largest context one request carried.
  files_matrix every file read, written or edited, by turn.
  line_chart   one measure per turn for several runs, for compare.py.

Colours are the validated categorical palette (`.c0`–`.c7`), assigned in fixed order to roles or
skills as they first appear; a ninth and later share the neutral `.cx`. Every coloured mark also
carries its name in a label, a legend or its tooltip.
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

CHART_CSS = """
:root{--c0:#2a78d6;--c1:#eb6834;--c2:#1baf7a;--c3:#eda100;--c4:#e87ba4;--c5:#008300;--c6:#6250d6;--c7:#e34948;
--cx:#8a8985;--main:#52514e;--read:#dcdbd5;--readfg:#1d1d1f}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--c0:#3987e5;--c1:#d95926;--c2:#199e70;
--c3:#c98500;--c4:#d55181;--c5:#008300;--c6:#9085e9;--c7:#e66767;--cx:#77766f;--main:#c3c2b7;--read:#3b3b40;
--readfg:#ececf0}}
:root[data-theme="dark"]{--c0:#3987e5;--c1:#d95926;--c2:#199e70;--c3:#c98500;--c4:#d55181;--c5:#008300;
--c6:#9085e9;--c7:#e66767;--cx:#77766f;--main:#c3c2b7;--read:#3b3b40;--readfg:#ececf0}
.c0{fill:var(--c0);background:var(--c0)}.c1{fill:var(--c1);background:var(--c1)}.c2{fill:var(--c2);background:var(--c2)}
.c3{fill:var(--c3);background:var(--c3)}.c4{fill:var(--c4);background:var(--c4)}.c5{fill:var(--c5);background:var(--c5)}
.c6{fill:var(--c6);background:var(--c6)}.c7{fill:var(--c7);background:var(--c7)}.cx{fill:var(--cx);background:var(--cx)}
.cmain{fill:var(--main)}.sc0{stroke:var(--c0)}.sc1{stroke:var(--c1)}.sc2{stroke:var(--c2)}
.tl text,.sm text,.lc text{font-size:10.5px;fill:var(--muted)}.tl .lbl-in,.sm .lbl-in{fill:#fff;font-size:10.5px;font-weight:600}
.tl .rowl,.sm .rowl,.lc .rowl{fill:var(--fg);font-size:11.5px;font-weight:600}.tl .band{fill:var(--rowp)}
.tl .brk{stroke:var(--muted);stroke-dasharray:2 3}.tl a:hover rect,.sm a:hover rect{stroke:var(--fg);stroke-width:1.5}
.axis{stroke:var(--line)}.sm .val{fill:var(--fg);font-weight:600}.lc path.ln{fill:none;stroke-width:2}
.lc circle{stroke:var(--bg);stroke-width:2}.lc .end{font-weight:600;fill:var(--fg)}
.tiles{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}.tile{border:1px solid var(--line);border-radius:8px;
padding:8px 12px;min-width:110px;background:var(--box)}.tile b{display:block;font-size:20px;line-height:1.2}
.tile span{font-size:12px;color:var(--muted)}.tile i{font-style:normal;font-size:12px;margin-left:6px}
.fm{border-collapse:separate;border-spacing:2px}.fm td,.fm th{border:0;padding:0;text-align:center;font-size:11px}
.fm th{padding:0 2px;font-weight:600}.fm td.f,.fm th.f{text-align:left;padding-right:10px;white-space:nowrap;
position:sticky;left:0;background:var(--bg);font:11.5px ui-monospace,Menlo,monospace;
max-width:380px;overflow:hidden;text-overflow:ellipsis}
.fm td.cell{min-width:22px;height:20px;border-radius:3px}.fm td.fw{background:var(--c0);color:#fff;font-weight:700}
.fm td.fe{background:var(--c1);color:#fff;font-weight:700}.fm td.fr{background:var(--read);color:var(--readfg)}
.fm td.n{color:var(--muted);padding:0 6px}.fm tr.grp td{text-align:left;padding-top:8px;color:var(--muted);
font-weight:600}
.key{display:inline-block;min-width:18px;text-align:center;border-radius:3px;font-size:11px;margin-right:4px}
.bar{display:inline-block;height:9px;border-radius:2px;vertical-align:0}
"""

ROW, GAP = 20, 4
GAP_CUT = 180.0  # seconds of idle time beyond which the timeline cuts the gap


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def epoch(s: str | None) -> float | None:
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def span(a: str | None, b: str | None) -> float | None:
    x, y = epoch(a), epoch(b)
    return y - x if x is not None and y is not None else None


def kt(n) -> str:
    n = n or 0
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    if n >= 1e5:
        return f"{n / 1e3:.0f}k"
    if n >= 1e3:
        return f"{n / 1e3:.1f}k"
    return str(int(n))


def dur(sec: float | None) -> str:
    if sec is None:
        return "?"
    if sec < 60:
        return f"{sec:.0f}s"
    m = sec / 60
    return f"{m:.1f} min" if m < 10 else f"{m:.0f} min" if m < 120 else f"{m / 60:.1f} h"


def cat(i: int) -> str:
    return f"c{i}" if i < 8 else "cx"


def short(path: str, project: str | None) -> str:
    """A path relative to the project, `../` paths for its siblings (an eval run's plugin), else `~/…`."""
    if not path:
        return ""
    if project:
        proj = project.rstrip("/")
        if path.startswith(proj + "/"):
            return path[len(proj) + 1:]
        parent = str(Path(proj).parent)
        if path.startswith(parent + "/"):
            return "../" + path[len(parent) + 1:]
    home = str(Path.home())
    return "~" + path[len(home):] if path.startswith(home) else path


def active_skills(turns: list[dict]) -> list[tuple[str | None, bool]]:
    """Per turn, (the skill it works under, whether it invoked it itself). A skill stays loaded in
    a resumed session, so a turn that invokes none works under the last one invoked before it."""
    out, cur = [], None
    for t in turns:
        mine = [x for x in t.get("skills") or [] if x]
        if mine:
            cur = mine[-1]
        out.append((mine[0] if mine else cur, bool(mine)))
    return out


def tok_line(t: dict | None) -> str:
    t = t or {}
    fresh = t.get("input", 0) + t.get("cache_write", 0)
    return (f"{kt(t.get('output'))} out · {kt(fresh)} new in · {kt(t.get('cache_read'))} cached in · "
            f"peak context {kt(t.get('context_peak'))}")


def tiles(items: list[tuple[str, str, str]]) -> str:
    """Stat tiles: (value, label, delta html)."""
    return '<div class="tiles">' + "".join(
        f'<div class="tile"><b>{esc(v)}{d}</b><span>{esc(k)}</span></div>' for v, k, d in items) + "</div>"


# ---------------------------------------------------------------- timeline


class Axis:
    """Wall time to x, with idle gaps longer than GAP_CUT cut to a fixed break."""

    def __init__(self, intervals: list[tuple[float, float]], x0: float, width: float):
        blocks: list[list[float]] = []
        for a, b in sorted(intervals):
            if blocks and a <= blocks[-1][1] + GAP_CUT:
                blocks[-1][1] = max(blocks[-1][1], b)
            else:
                blocks.append([a, b])
        self.blocks = blocks
        active = sum(b - a for a, b in blocks) or 1.0
        self.brk = active * 0.03 if len(blocks) > 1 else 0.0
        self.off, acc = [], 0.0
        for a, b in blocks:
            self.off.append(acc)
            acc += (b - a) + self.brk
        self.k = width / max(acc - self.brk, 1.0)
        self.x0 = x0

    def x(self, t: float) -> float:
        for (a, b), off in zip(self.blocks, self.off):
            if t <= b:
                return self.x0 + (off + max(0.0, t - a)) * self.k
        a, b = self.blocks[-1]
        return self.x0 + (self.off[-1] + b - a) * self.k

    def breaks(self) -> list[tuple[float, float]]:
        """(x at the break, idle seconds cut) for each gap."""
        return [(self.x(self.blocks[i][1]) + self.brk * self.k / 2, self.blocks[i + 1][0] - self.blocks[i][1])
                for i in range(len(self.blocks) - 1)]

    def ticks(self, every_px: float = 90) -> list[tuple[float, float]]:
        steps = [10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200]
        step = next((s for s in steps if s * self.k >= every_px), steps[-1])
        out = []
        for a, b in self.blocks:
            t = (a // step + 1) * step
            while t < b:
                out.append((self.x(t), t))
                t += step
        return out


def pack(items: list[tuple[float, float, dict]]) -> list[list[tuple[float, float, dict]]]:
    """Greedy interval packing: each item goes in the first row free at its start."""
    rows: list[list[tuple[float, float, dict]]] = []
    for a, b, d in sorted(items, key=lambda x: (x[0], x[1])):
        for r in rows:
            if r[-1][1] <= a:
                r.append((a, b, d))
                break
        else:
            rows.append([(a, b, d)])
    return rows


def unit_tip(u: dict) -> str:
    sec = span(u.get("first_ts"), u.get("last_ts"))
    return (f"{u['unit']} · {u['type']}\n{u.get('description', '')}\n{dur(sec)} · {u.get('tool_calls', 0)} tools · "
            f"{u.get('errors', 0)} errors\n{tok_line(u.get('tokens'))}\n"
            f"{len(u.get('files_read') or [])} files read · {len(u.get('files_edited') or [])} written or edited\n"
            f"returned: {u.get('return_first_line') or '(still running)'}")


def turn_tip(t: dict, extra: dict | None = None) -> str:
    sec = span(t.get("first_ts"), t.get("last_ts"))
    edited = [f["path"].rsplit("/", 1)[-1] for f in t.get("files", []) if f["op"] in ("write", "edit")]
    extra = extra or {}
    return (f"{t['turn']}" + (f" · {extra['stage']}" if extra.get("stage") else "")
            + f" · {dur(sec)}" + (f" · ${extra['cost_usd']:.2f}" if extra.get("cost_usd") is not None else "")
            + f"\nprompt: {t.get('prompt_first_line', '')[:140]}\nskills: {', '.join(t.get('skills') or []) or '—'}"
            f" · {t.get('tool_calls', 0)} tools · {len(t.get('units') or [])} agents\n{tok_line(t.get('tokens'))}\n"
            f"wrote or edited: {', '.join(dict.fromkeys(edited)) or 'nothing'}")


def timeline(index: dict, roles: list[str], unit_href, turn_href, extra: dict | None = None,
             width: int = 1120) -> str:
    """The run against wall time; `extra` maps a turn number to eval facts (stage, cost)."""
    extra = extra or {}
    turns, units = index.get("turns") or [], index["units"]
    spans_ = []
    for x in [*turns, *units]:
        a, b = epoch(x.get("first_ts")), epoch(x.get("last_ts"))
        if a is not None:
            spans_.append((a, max(b or a, a + 1)))
    if not spans_:
        return "<p>No timestamps to draw.</p>"
    left, top = 118, 22
    width = max(width, left + 24 * len(turns) + 20)
    plot = width - left - 12
    ax = Axis(spans_, left, plot)
    lanes = pack([(epoch(u["first_ts"]), max(epoch(u["last_ts"]) or 0, epoch(u["first_ts"]) + 1), u)
                  for u in units if epoch(u.get("first_ts")) is not None])
    y_main = top + 4
    y_units = y_main + ROW + 14
    height = y_units + max(len(lanes), 1) * (ROW + GAP) + 26
    color = {r: cat(i) for i, r in enumerate(roles)}
    out = []
    # turn bands across every row, alternating
    for i, t in enumerate(turns):
        a = epoch(t["first_ts"])
        nxt = epoch(turns[i + 1]["first_ts"]) if i + 1 < len(turns) else epoch(t["last_ts"])
        if a is None or nxt is None:
            continue
        x1, x2 = ax.x(a), ax.x(max(nxt, a + 1))
        if i % 2 == 0:
            out.append(f'<rect x="{x1:.1f}" y="{top - 4}" width="{max(x2 - x1, 1):.1f}" '
                       f'height="{height - top - 18}" class="band"/>')
        if x2 - x1 >= 18:
            out.append(f'<text x="{(x1 + x2) / 2:.1f}" y="{top - 8}" text-anchor="middle">T{t["n"]}</text>')
    out.append(f'<text x="8" y="{y_main + 14}" class="rowl">main thread</text>')
    for t in turns:
        a, b = epoch(t["first_ts"]), epoch(t["last_ts"])
        if a is None:
            continue
        x1, x2 = ax.x(a), ax.x(max(b or a, a + 1))
        out.append(f'<a href="{esc(turn_href(t["turn"]))}"><g><title>{esc(turn_tip(t, extra.get(t["n"])))}</title>'
                   f'<rect x="{x1:.1f}" y="{y_main}" width="{max(x2 - x1, 2):.1f}" height="{ROW}" rx="3" '
                   f'class="cmain"/></g></a>')
    if lanes:
        out.append(f'<text x="8" y="{y_units + 14}" class="rowl">agents</text>')
        if len(lanes) > 1:
            out.append(f'<text x="8" y="{y_units + 28}">up to {len(lanes)} at once</text>')
    for k, lane in enumerate(lanes):
        y = y_units + k * (ROW + GAP)
        for a, b, u in lane:
            x1, x2 = ax.x(a), ax.x(b)
            w = max(x2 - x1, 2)
            label = f"{u['unit']} {u['role']}"
            inner = (f'<text x="{x1 + 5:.1f}" y="{y + 14}" class="lbl-in">{esc(label)}</text>'
                     if w > 7 * len(label) + 10 else "")
            out.append(f'<a href="{esc(unit_href(u["unit"]))}"><g><title>{esc(unit_tip(u))}</title>'
                       f'<rect x="{x1:.1f}" y="{y}" width="{w:.1f}" height="{ROW}" rx="3" '
                       f'class="{color.get(u["role"], "cx")}"/>{inner}</g></a>')
    base = height - 22
    out.append(f'<line x1="{left}" y1="{base}" x2="{left + plot}" y2="{base}" class="axis"/>')
    ticks = ax.ticks()
    clock = "%H:%M:%S" if len(ticks) > 1 and ticks[1][1] - ticks[0][1] < 60 else "%H:%M"
    for x, t in ticks:
        out.append(f'<line x1="{x:.1f}" y1="{base}" x2="{x:.1f}" y2="{base + 4}" class="axis"/>'
                   f'<text x="{x:.1f}" y="{base + 15}" text-anchor="middle">'
                   f'{datetime.fromtimestamp(t).strftime(clock)}</text>')
    for x, idle in ax.breaks():
        out.append(f'<g><title>{esc(dur(idle))} idle, cut</title><line x1="{x:.1f}" y1="{top - 2}" x2="{x:.1f}" '
                   f'y2="{base}" class="brk"/><text x="{x:.1f}" y="{base + 15}" text-anchor="middle">'
                   f'⋯{esc(dur(idle))}</text></g>')
    return (f'<svg class="tl" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="Timeline of the run">{"".join(out)}</svg>')


# ---------------------------------------------------------------- per-turn small multiples


def turn_bars(index: dict, skills: list[str], turn_href, extra: dict | None = None, width: int = 1120) -> str:
    """One column per turn, one row per measure, each row on its own scale."""
    extra = extra or {}
    turns = index.get("turns") or []
    if not turns:
        return "<p>No turns.</p>"
    left = 118
    width = max(width, left + 16 * len(turns) + 20)
    bw = (width - left - 12) / len(turns)
    skill_color = {s: cat(i) for i, s in enumerate(skills)}
    rows: list[tuple[str, list[list[tuple[float, str, str]]], callable]] = []

    def stack(t: dict, *parts) -> list[tuple[float, str, str]]:
        return [p for p in parts if p[0]]

    rows.append(("Wall time", [stack(t, (span(t["first_ts"], t["last_ts"]) or 0, "cmain", "")) for t in turns], dur))
    rows.append(("Output tokens", [stack(t, (t["tokens_main"]["output"], "cmain", "main thread"),
                                         (t["tokens_units"]["output"], "cx", "agents")) for t in turns], kt))
    rows.append(("Peak context", [stack(t, (t["tokens"]["context_peak"], "cmain", "")) for t in turns], kt))
    if any((extra.get(t["n"]) or {}).get("cost_usd") is not None for t in turns):
        rows.append(("Cost", [stack(t, ((extra.get(t["n"]) or {}).get("cost_usd") or 0, "cmain", ""))
                              for t in turns], lambda v: f"${v:.2f}"))
    h, gap = 58, 14
    y = 4
    out = [f'<text x="8" y="{y + 13}" class="rowl">Skill</text>']
    for i, (t, (sk, invoked)) in enumerate(zip(turns, active_skills(turns))):
        x = left + i * bw
        name = (sk or "").split(":")[-1]
        tip = f"{t['turn']}: " + (f"invoked {', '.join(t['skills'])}" if invoked
                                  else f"still under {sk}" if sk else "no skill yet")
        if not sk:
            out.append(f'<g><title>{esc(tip)}</title><rect x="{x + 1:.1f}" y="{y + 8}" width="{max(bw - 2, 1):.1f}" '
                       f'height="2" class="cx"/></g>')
            continue
        # a turn that invoked the skill is a full block with its name; one still under it is a thin band
        label = (f'<text x="{x + 3:.1f}" y="{y + 13}" class="lbl-in">{esc(name[:int(bw / 6.5)])}</text>'
                 if invoked and bw > 40 else "")
        h_, y_ = (18, y) if invoked else (6, y + 6)
        out.append(f'<g><title>{esc(tip)}</title><rect x="{x + 1:.1f}" y="{y_}" width="{max(bw - 2, 1):.1f}" '
                   f'height="{h_}" rx="2" class="{skill_color.get(sk, "cx")}"/>{label}</g>')
    y += 18 + gap
    for name, series, fmt in rows:
        top = max((sum(v for v, _, _ in s) for s in series), default=0) or 1
        out.append(f'<text x="8" y="{y + 13}" class="rowl">{esc(name)}</text>'
                   f'<text x="8" y="{y + 27}">max {esc(fmt(top))}</text>')
        base = y + h
        out.append(f'<line x1="{left}" y1="{base}" x2="{width - 12}" y2="{base}" class="axis"/>')
        peak_i = max(range(len(series)), key=lambda i: sum(v for v, _, _ in series[i]))
        for i, (t, parts) in enumerate(zip(turns, series)):
            x = left + i * bw
            acc = 0.0
            segs = []
            for v, cls, label in parts:
                hgt = v / top * h
                segs.append(f'<rect x="{x + 1:.1f}" y="{base - acc - hgt:.1f}" width="{max(bw - 2, 1):.1f}" '
                            f'height="{max(hgt - (1 if acc else 0), 0.5):.1f}" rx="2" class="{cls}"/>')
                acc += hgt
            tip = f"{t['turn']} · {name}: " + " + ".join(
                f"{fmt(v)}{' ' + lbl if lbl else ''}" for v, _, lbl in parts) if parts else f"{t['turn']}: 0"
            # the hit target is the whole column, not just the painted bar
            out.append(f'<a href="{esc(turn_href(t["turn"]))}"><g><title>{esc(tip)}</title>'
                       f'<rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="{h}" fill="transparent"/>'
                       f'{"".join(segs)}</g></a>')
            if i == peak_i and parts:
                out.append(f'<text x="{x + bw / 2:.1f}" y="{base - acc - 3:.1f}" text-anchor="middle" '
                           f'class="val">{esc(fmt(sum(v for v, _, _ in parts)))}</text>')
        y = base + gap
    every = max(1, int(28 // bw) + 1)
    for i, t in enumerate(turns):
        if i % every == 0:
            out.append(f'<text x="{left + i * bw + bw / 2:.1f}" y="{y + 4}" text-anchor="middle">T{t["n"]}</text>')
    height = y + 10
    return (f'<svg class="sm" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="Per-turn measures">{"".join(out)}</svg>')


# ---------------------------------------------------------------- files by turn


OPS = (("write", "W", "fw"), ("edit", "E", "fe"), ("read", "R", "fr"))


def files_matrix(index: dict, turn_href) -> str:
    turns = index.get("turns") or []
    project = index.get("project")
    cells: dict[str, dict[int, dict[str, dict]]] = {}
    first: dict[str, int] = {}
    for t in turns:
        for f in t.get("files", []):
            cells.setdefault(f["path"], {}).setdefault(t["n"], {})[f["op"]] = f
            first.setdefault(f["path"], t["n"])
    if not cells:
        return "<p>No file was read or changed.</p>"

    def changed(p: str) -> bool:
        return any(op in ("write", "edit") for d in cells[p].values() for op in d)

    inside = (lambda p: bool(project) and p.startswith(project.rstrip("/") + "/"))
    groups = [
        ("Changed in the project", [p for p in cells if inside(p) and changed(p)]),
        ("Only read, in the project", [p for p in cells if inside(p) and not changed(p)]),
        ("Outside the project (plugin, skills, home)", [p for p in cells if not inside(p)]),
    ]
    head = "".join(f'<th><a href="{esc(turn_href(t["turn"]))}">T{t["n"]}</a></th>' for t in turns)

    def row(p: str) -> str:
        tds = []
        for t in turns:
            d = cells[p].get(t["n"])
            if not d:
                tds.append('<td class="cell"></td>')
                continue
            letters = "".join(ch for op, ch, _ in OPS if op in d)
            cls = next(c for op, _, c in OPS if op in d)
            sub = any(w != "main" for f in d.values() for w in f["who"])
            tip = f"T{t['n']} · {short(p, project)}\n" + "\n".join(
                f"{op} {f['n']}× by {', '.join(f['who'])} via {', '.join(f['via'])}" for op, f in d.items())
            tds.append(f'<td class="cell {cls}" title="{esc(tip)}">{letters}{"*" if sub else ""}</td>')
        reads = sum(f["n"] for d in cells[p].values() for op, f in d.items() if op == "read")
        edits = sum(f["n"] for d in cells[p].values() for op, f in d.items() if op != "read")
        name = short(p, project)
        name = name if len(name) <= 56 else "…" + name[-55:]
        return (f'<tr><td class="f" title="{esc(p)}">{esc(name)}</td>{"".join(tds)}'
                f'<td class="n">{reads or ""}</td><td class="n">{edits or ""}</td></tr>')

    body = []
    for label, paths in groups:
        if not paths:
            continue
        paths.sort(key=lambda p: (first[p], p))
        body.append(f'<tr class="grp"><td colspan="{len(turns) + 3}">{esc(label)} · {len(paths)} files</td></tr>'
                    + "".join(row(p) for p in paths))
    key = ('<p class="legend"><span class="key" style="background:var(--c0);color:#fff">W</span>written '
           '(created or replaced) <span class="key" style="background:var(--c1);color:#fff">E</span>edited '
           '(an Edit, or an append) <span class="key" style="background:var(--read);color:var(--readfg)">R</span>read '
           '· <b>*</b> by an agent, not the main thread · reads and writes through Bash are what its command '
           'shows (<code>cat</code>, <code>sed -n</code>, <code>&gt;</code>, <code>&gt;&gt;</code>, <code>tee</code>); '
           'hover a cell for who and how often.</p>')
    return (key + f'<div class="scroll"><table class="fm"><tr><th class="f">File</th>{head}<th>reads</th>'
            f'<th>edits</th></tr>{"".join(body)}</table></div>')


# ---------------------------------------------------------------- compare


def line_chart(title: str, series: list[tuple[str, str, list[float | None]]], fmt, width: int = 760,
               height: int = 220, hrefs: list[list[str]] | None = None) -> str:
    """Several runs' values per turn on one shared axis: (label, colour class, values)."""
    n = max((len(v) for _, _, v in series), default=0)
    if not n:
        return ""
    left, right, top, bottom = 58, 120, 26, 26
    pw, ph = width - left - right, height - top - bottom
    hi = max((x for _, _, v in series for x in v if x is not None), default=0) or 1
    sx = (lambda i: left + (i / max(n - 1, 1)) * pw)
    sy = (lambda v: top + ph - (v / hi) * ph)
    out = [f'<text x="0" y="14" class="rowl">{esc(title)}</text>']
    for f in (0, 0.5, 1):
        y = sy(hi * f)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + pw}" y2="{y:.1f}" class="axis"/>'
                   f'<text x="{left - 10}" y="{y + 3:.1f}" text-anchor="end">{esc(fmt(hi * f))}</text>')
    every = max(1, n // 12)
    for i in range(0, n, every):
        out.append(f'<text x="{sx(i):.1f}" y="{height - 8}" text-anchor="middle">T{i + 1}</text>')
    ends = []
    for k, (label, cls, vals) in enumerate(series):
        pts = [(sx(i), sy(v), v, i) for i, v in enumerate(vals) if v is not None]
        if not pts:
            continue
        d = " ".join(f"{'M' if j == 0 else 'L'}{x:.1f},{y:.1f}" for j, (x, y, _, _) in enumerate(pts))
        out.append(f'<path d="{d}" class="ln s{cls}"/>')
        for x, y, v, i in pts:
            # past 30 turns the dots would merge into the line: keep only the hit targets
            dot = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" class="{cls}"/>' if n <= 30 else ""
            hit = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{min(12, max(pw / n / 2, 4)):.1f}" fill="transparent"/>'
            g = f'<g><title>{esc(label)} · T{i + 1}: {esc(fmt(v))}</title>{hit}{dot}</g>'
            href = hrefs[k][i] if hrefs and k < len(hrefs) and i < len(hrefs[k]) else None
            out.append(f'<a href="{esc(href)}">{g}</a>' if href else g)
        ends.append([pts[-1][1], label, pts[-1][2], cls])
    ends.sort()
    for j in range(1, len(ends)):  # keep end labels apart
        ends[j][0] = max(ends[j][0], ends[j - 1][0] + 14)
    for y, label, v, cls in ends:
        out.append(f'<text x="{left + pw + 8}" y="{y + 4:.1f}" class="end">{esc(label)} {esc(fmt(v))}</text>')
    return (f'<svg class="lc" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">{"".join(out)}</svg>')
