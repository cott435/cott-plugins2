#!/usr/bin/env python3
"""Two or more built runs side by side: what changed between them, turn by turn.

Each argument is a workspace `trace.py build` wrote (it holds `index.json`), optionally as
`LABEL=DIR`. The first is the baseline every delta is measured from. Writes one page, no
network; a run's turn points link to that run's turn pages.

  headline   turns, wall and working time, tokens, peak context, agents and how many ran at
             once, tool calls and errors, files written and read, cost and checks (with eval.json),
             each with its change from the baseline
  checks     with eval.json in both: every check whose result differs, then the rest
  per turn   cumulative output tokens, wall time and peak context, one line per run
  skills     per skill: the turns that invoked it, and their output tokens and time
  agents     per agent type: runs, output tokens and time
  files      every file written or edited in any run: in which turns of each run

Each run may also be a session (an id or prefix, a .jsonl path, `latest`, or words from the
chat's title, as trace.py takes them), optionally as `LABEL=SESSION`: it is built into its
workspace first. Without --out the page is
`$RUN_FLOW_HOME/compare/<id8>-vs-<id8>[-vs-…].html`.

--turns N compares each run as of the end of its N-th turn (a replay cut short with
--max-turns against its whole original), keeping only the checks every run was graded on.

Usage: compare.py [LABEL=]DIR|SESSION [LABEL=]DIR|SESSION ... [--out PAGE.html] [--project TEXT]
                  [--turns N]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charts  # noqa: E402
import flow  # noqa: E402

esc = charts.esc


def cut(index: dict, n: int | None) -> dict:
    """The run as of the end of its n-th turn: those turns, the agents they spawned, their tokens."""
    if not n or n >= len(index["turns"]):
        return index
    turns = index["turns"][:n]
    mine = {u for t in turns for u in t["units"]}
    tok = {k: sum((t["tokens"] or {}).get(k, 0) for t in turns)
           for k in ("input", "cache_write", "cache_read", "output", "requests")}
    tok["context_peak"] = max(((t["tokens"] or {}).get("context_peak", 0) for t in turns), default=0)
    return {**index, "turns": turns, "units": [u for u in index["units"] if u["unit"] in mine],
            "last_ts": turns[-1]["last_ts"], "tokens": {**(index.get("tokens") or {}), "all": tok}}


def load(spec: str, turns: int | None = None) -> dict:
    label, _, d = spec.rpartition("=") if "=" in spec else ("", "", spec)
    ws = Path(d).resolve()
    index = cut(json.loads((ws / "index.json").read_text(encoding="utf-8")), turns)
    ev = flow.load_eval(ws)
    if not label:
        label = (ev or {}).get("iteration") or index["session"][:8]
    return {"label": label, "ws": ws, "index": index, "eval": ev, "stats": flow.run_stats(index),
            "extra": {t["turn"]: t for t in (ev or {}).get("turns") or []}}


def delta(a, b, fmt, lower_is_better: bool | None) -> str:
    """The change from a to b; green when it is better, red when worse, plain when neither."""
    if a is None or b is None or a == b:
        return ""
    d = b - a
    pct = f" ({d / a:+.0%})" if a else ""
    cls = "" if lower_is_better is None else ' class="ok"' if (d < 0) == lower_is_better else ' class="bad"'
    return f'<i{cls}>{"+" if d > 0 else "−"}{fmt(abs(d))}{pct}</i>'


def headline(runs: list[dict]) -> str:
    def cost(r):
        return sum(e.get("cost_usd") or 0 for e in r["extra"].values()) if r["extra"] else None

    def passed(r):
        c = (r["eval"] or {}).get("checks") or []
        return sum(1 for x in c if x.get("passed")) if c else None

    metrics = [
        ("Turns", lambda r: r["stats"]["turns"], str, True),
        ("Wall time", lambda r: r["stats"]["wall"], charts.dur, True),
        ("Working (turns)", lambda r: r["stats"]["busy"], charts.dur, True),
        ("Output tokens", lambda r: r["stats"]["output"], charts.kt, True),
        ("New input tokens", lambda r: r["stats"]["fresh_in"], charts.kt, True),
        ("Cached input tokens", lambda r: r["stats"]["cache_read"], charts.kt, True),
        ("Peak context", lambda r: r["stats"]["context_peak"], charts.kt, True),
        ("Agents spawned", lambda r: r["stats"]["units"], str, None),
        ("Most agents at once", lambda r: r["stats"]["parallel"], str, None),
        ("Tool calls", lambda r: r["stats"]["tool_calls"], str, True),
        ("Tool errors", lambda r: r["stats"]["errors"], str, True),
        ("Files written or edited", lambda r: r["stats"]["files_changed"], str, None),
        ("Files read", lambda r: r["stats"]["files_read"], str, None),
        ("Agent cost", cost, lambda v: f"${v:.2f}", True),
        ("Checks passed", passed, str, False),
    ]
    head = "<tr><th>Measure</th>" + "".join(f"<th>{esc(r['label'])}</th>" for r in runs) + "</tr>"
    body = []
    base = runs[0]
    for name, get, fmt, lower in metrics:
        vals = [get(r) for r in runs]
        if all(v is None for v in vals):
            continue
        cells = []
        for k, (r, v) in enumerate(zip(runs, vals)):
            d = "" if k == 0 else delta(vals[0], v, fmt, lower)
            cells.append(f"<td>{esc(fmt(v)) if v is not None else '—'} {d}</td>")
        body.append(f"<tr><td>{esc(name)}</td>{''.join(cells)}</tr>")
    note = f"Changes are against {esc(base['label'])}: <span class=ok>green</span> is better, <span class=bad>red</span> worse."
    return f"<p>{note}</p><table class='cmp'>{head}{''.join(body)}</table>"


def checks(runs: list[dict]) -> str:
    have = [r for r in runs if (r["eval"] or {}).get("checks")]
    if len(have) < 2:
        return ""
    ids = list(dict.fromkeys(c["id"] for r in have for c in r["eval"]["checks"]))
    res = {r["label"]: {c["id"]: c for c in r["eval"]["checks"]} for r in have}
    text = {c["id"]: c.get("text", "") for r in have for c in r["eval"]["checks"]}

    def cell(r, i):
        c = res[r["label"]].get(i)
        if c is None:
            return "<td class='idle'>—</td>"
        mark, cls = ("✓ pass", "ok") if c.get("passed") else ("✗ fail", "bad")
        return f"<td class='{cls}' title='{esc((c.get('evidence') or '')[:600])}'>{mark}</td>"

    def row(i):
        return f"<tr><td><code>{esc(i)}</code></td><td>{esc(text[i])}</td>{''.join(cell(r, i) for r in have)}</tr>"

    changed = [i for i in ids if len({(res[r["label"]].get(i) or {}).get("passed") for r in have}) > 1]
    same = [i for i in ids if i not in changed]
    head = "<tr><th>Check</th><th>What it checks</th>" + "".join(f"<th>{esc(r['label'])}</th>" for r in have) + "</tr>"
    return (f"<h2>Checks</h2><p>{len(changed)} of {len(ids)} checks differ between the runs. Hover a result for "
            f"its evidence.</p><table>{head}{''.join(row(i) for i in changed) or ''}</table>"
            f"<details><summary>{len(same)} checks with the same result in every run</summary>"
            f"<table>{head}{''.join(row(i) for i in same)}</table></details>")


def href(run: dict, page: Path, turn: str) -> str:
    return Path(os.path.relpath(run["ws"] / "turns" / f"{turn}.html", page.parent)).as_posix()


def per_turn(runs: list[dict], page: Path) -> str:
    def cum(xs):
        out, acc = [], 0
        for x in xs:
            acc += x
            out.append(acc)
        return out

    series = lambda get: [(r["label"], charts.cat(k), get(r)) for k, r in enumerate(runs)]  # noqa: E731
    links = [[href(r, page, t["turn"]) for t in r["index"]["turns"]] for r in runs]
    parts = [
        charts.line_chart("Output tokens, cumulative", series(
            lambda r: cum([t["tokens"]["output"] for t in r["index"]["turns"]])), charts.kt, hrefs=links),
        charts.line_chart("Wall time per turn", series(
            lambda r: [charts.span(t["first_ts"], t["last_ts"]) or 0 for t in r["index"]["turns"]]),
            charts.dur, hrefs=links),
        charts.line_chart("Peak context per turn", series(
            lambda r: [t["tokens"]["context_peak"] for t in r["index"]["turns"]]), charts.kt, hrefs=links),
    ]
    if all(r["extra"] for r in runs):
        parts.append(charts.line_chart("Agent cost, cumulative", series(
            lambda r: cum([(r["extra"].get(t["n"]) or {}).get("cost_usd") or 0 for t in r["index"]["turns"]])),
            lambda v: f"${v:.2f}", hrefs=links))
    legend = "".join(f'<span><i class="sw {charts.cat(k)}"></i>{esc(r["label"])}</span>' for k, r in enumerate(runs))
    return ("<h2>Per turn</h2><p class='legend'>Turn numbers line up by position, not by what the turn did: the "
            f"runs can reach the same step at different turns. Click a point for that turn's page. {legend}</p>"
            + '<div class="grid2">' + "".join(f"<div>{p}</div>" for p in parts) + "</div>")


def bars(vals: list[float], fmt) -> list[str]:
    hi = max(vals) or 1
    return [f'<span class="bar c{k if k < 8 else "x"}" style="width:{max(v / hi * 120, 1 if v else 0):.0f}px"></span> '
            f'{esc(fmt(v))}' for k, v in enumerate(vals)]


def by_skill(runs: list[dict]) -> str:
    skills = list(dict.fromkeys(x for r in runs for t in r["index"]["turns"] for x in t["skills"] if x))
    if not skills:
        return ""
    under = {r["label"]: charts.active_skills(r["index"]["turns"]) for r in runs}
    rows = []
    for sk in skills:
        def turns_of(r):
            return [t for t, (a, _) in zip(r["index"]["turns"], under[r["label"]]) if a == sk]
        n = [len(turns_of(r)) for r in runs]
        out = [sum(t["tokens"]["output"] for t in turns_of(r)) for r in runs]
        sec = [sum(charts.span(t["first_ts"], t["last_ts"]) or 0 for t in turns_of(r)) for r in runs]
        rows.append(f"<tr><td>{esc(sk.split(':')[-1])}</td>"
                    + "".join(f"<td>{x}</td>" for x in n)
                    + "".join(f"<td>{x}</td>" for x in bars(out, charts.kt))
                    + "".join(f"<td>{x}</td>" for x in bars(sec, charts.dur)) + "</tr>")
    labels = [esc(r["label"]) for r in runs]
    head = ("<tr><th rowspan=2>Skill</th>" + f"<th colspan={len(runs)}>Turns</th>"
            f"<th colspan={len(runs)}>Output tokens in those turns</th><th colspan={len(runs)}>Time in those turns</th></tr>"
            "<tr>" + "".join(f"<th>{x}</th>" for x in labels * 3) + "</tr>")
    return ("<h2>By skill</h2><p class='legend'>A turn belongs to the skill it invoked, or else to the last one "
            "invoked before it (a skill stays loaded in a resumed session). Bars compare the runs within a row.</p>"
            f"<table class='nw'>{head}{''.join(rows)}</table>")


def by_agent(runs: list[dict]) -> str:
    roles = list(dict.fromkeys(u["type"] for r in runs for u in r["index"]["units"]))
    if not roles:
        return ""
    rows = []
    for role in roles:
        def mine(r):
            return [u for u in r["index"]["units"] if u["type"] == role]
        n = [len(mine(r)) for r in runs]
        out = [sum((u.get("tokens") or {}).get("output", 0) for u in mine(r)) for r in runs]
        sec = [sum(charts.span(u["first_ts"], u["last_ts"]) or 0 for u in mine(r)) for r in runs]
        rows.append(f"<tr><td>{esc(role)}</td>" + "".join(f"<td>{x}</td>" for x in n)
                    + "".join(f"<td>{x}</td>" for x in bars(out, charts.kt))
                    + "".join(f"<td>{x}</td>" for x in bars(sec, charts.dur)) + "</tr>")
    labels = [esc(r["label"]) for r in runs]
    head = ("<tr><th rowspan=2>Agent type</th>" + f"<th colspan={len(runs)}>Runs</th>"
            f"<th colspan={len(runs)}>Output tokens</th><th colspan={len(runs)}>Time</th></tr>"
            "<tr>" + "".join(f"<th>{x}</th>" for x in labels * 3) + "</tr>")
    return f"<h2>By agent type</h2><table class='nw'>{head}{''.join(rows)}</table>"


def files(runs: list[dict], page: Path) -> str:
    def rel(r, p):
        return charts.short(p, r["index"].get("project"))

    touched: dict[str, list[list[tuple[int, str]]]] = {}
    for k, r in enumerate(runs):
        for t in r["index"]["turns"]:
            for f in t["files"]:
                if f["op"] in ("write", "edit"):
                    cell = touched.setdefault(rel(r, f["path"]), [[] for _ in runs])[k]
                    if (t["n"], t["turn"]) not in cell:
                        cell.append((t["n"], t["turn"]))
    if not touched:
        return ""
    rows = []
    for path in sorted(touched, key=lambda p: (min((c[0][0] for c in touched[p] if c), default=0), p)):
        cells = touched[path]
        only = [k for k, c in enumerate(cells) if c]
        cls = "" if len(only) == len(runs) else " class='warn'"
        tds = "".join("<td>" + (" ".join(f'<a href="{esc(href(r, page, t))}">T{n}</a>' for n, t in c) or "—") + "</td>"
                      for r, c in zip(runs, cells))
        rows.append(f"<tr><td{cls}><code>{esc(path)}</code></td>{tds}</tr>")
    head = "<tr><th>File</th>" + "".join(f"<th>{esc(r['label'])}: turns that changed it</th>" for r in runs) + "</tr>"
    return ("<h2>Files written or edited</h2><p class='legend'>Paths are relative to each run's project. "
            "<span class=warn>Amber</span>: not changed in every run.</p>"
            f'<div class="scroll"><table>{head}{"".join(rows)}</table></div>')


def write(specs: list[str], page: Path, turns: int | None = None) -> Path:
    runs = [load(s, turns) for s in specs]
    if turns:  # checks graded over different spans of turns don't compare; keep the ones every run has
        have = [r for r in runs if (r["eval"] or {}).get("checks")]
        common = set.intersection(*({c["id"] for c in r["eval"]["checks"]} for r in have)) if have else set()
        for r in have:
            r["eval"] = {**r["eval"], "checks": [c for c in r["eval"]["checks"] if c["id"] in common]}
    its = {(r["eval"] or {}).get("iteration") for r in runs}
    trajs = [(r["eval"] or {}).get("trajectory") for r in runs]
    if len(its) == 1 and None not in its and len(set(trajs)) == len(runs):
        for r, t in zip(runs, trajs):  # one iteration, several trajectories: name them by trajectory
            r["label"] = t
    page = page.resolve()
    title = " vs ".join(r["label"] for r in runs) + (f" · first {turns} turn{'' if turns == 1 else 's'}" if turns else "")
    traj = {(r["eval"] or {}).get("trajectory") for r in runs} - {None}
    sub = "".join(
        f'<div class="sub"><i class="sw {charts.cat(k)}"></i><b>{esc(r["label"])}</b> · '
        f'<a href="{esc(Path(os.path.relpath(r["ws"] / "flow.html", page.parent)).as_posix())}">its run page</a> · '
        f'session {esc(r["index"]["session"][:8])} · {esc(r["index"].get("title") or "")} · '
        f'{esc(r["index"]["first_ts"][:16].replace("T", " "))} UTC</div>' for k, r in enumerate(runs))
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Run comparison</title>
<style>{flow.CSS}{charts.CHART_CSS}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(760px,100%),1fr));gap:8px 24px}}
.grid2 svg{{max-width:100%;height:auto}}table.cmp td i{{font-style:normal;font-size:12px;margin-left:4px}}
td.warn{{color:var(--warn)}}table.nw td{{white-space:nowrap}}</style></head>
<body>
<h1>{esc(" · ".join(sorted(traj)) + " · " if traj else "")}{esc(title)}</h1>
{sub}
<h2>Headline</h2>
{headline(runs)}
{checks(runs)}
{per_turn(runs, page)}
{by_skill(runs)}
{by_agent(runs)}
{files(runs, page)}
</body></html>"""
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(html, encoding="utf-8")
    return page


def built(spec: str, project: str | None) -> str:
    """LABEL=DIR as given when DIR holds a built run; otherwise resolve it as a session and build it."""
    import trace  # noqa: E402  (only needed here; trace imports flow, already loaded)
    label, _, ref = spec.rpartition("=") if "=" in spec else ("", "", spec)
    if (Path(ref).expanduser() / "index.json").exists():
        return spec
    path = trace.resolve(ref, None, project)
    ws = trace.workspace_for(path)
    trace.build(path, None, ws, quiet=True)
    return f"{label}={ws}" if label else str(ws)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", help="[LABEL=]DIR or [LABEL=]SESSION; the first is the baseline")
    ap.add_argument("--out")
    ap.add_argument("--project", help="narrows `latest` and title words, as in trace.py")
    ap.add_argument("--turns", type=int, help="compare only each run's first N turns (e.g. a replay cut short)")
    a = ap.parse_args()
    if len(a.runs) < 2:
        ap.error("give at least two runs")
    specs = [built(x, a.project) for x in a.runs]
    if a.out:
        page = Path(a.out).expanduser()
    else:
        import trace  # noqa: E402
        ids = [json.loads((Path(x.rpartition("=")[2]).expanduser() / "index.json").read_text())["session"][:8]
               for x in specs]
        page = trace.RUNS / "compare" / f"{'-vs-'.join(ids)}.html"
    print(write(specs, page, a.turns))
    return 0


if __name__ == "__main__":
    sys.exit(main())
