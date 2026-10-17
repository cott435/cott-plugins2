#!/usr/bin/env python3
"""Draw what each eval run did, from its session transcripts: the workflow-analyzer plugin's scripts
over the eval layout.

For a run folder (`<iteration>/<trajectory>/with_skill/`) it finds the agent session the driver
ran (the `session_id` in `agent_stream.jsonl`, whose transcript is under ~/.claude/projects/),
writes `eval.json` beside the trace (the trajectory, its checks from `grading.json`, and per turn
the stage and cost from `turns.json`), and builds `<run>/flow/`: `flow.html` with the timeline,
tokens and time per turn and per agent, files read and edited per turn, the wave chart, and one
page per turn and per agent.

For an iteration it does that for every run, compares each with the same trajectory in the
previous iteration (or `--against`), and writes `<iteration>/runflow/index.html`, the
iteration's runs side by side with links to every run page and comparison.

driver.py runs the single-run form after every trajectory and run.sh the iteration form after
grading, so every eval gets its pages. Failures here never fail the eval.

The transcript reader and the pages (trace.py, flow.py, charts.py, compare.py) live in the
workflow-analyzer plugin beside this one in the marketplace, which draws any session, not just
evals; this file is only the eval-layout adapter. It finds the plugin's scripts/ at
$WORKFLOW_ANALYZER_SCRIPTS, else in the marketplace checkout (../workflow-analyzer/scripts from
the plugin root), else in the newest installed copy under ~/.claude/plugins/cache/.

Usage:
  runviz.py <iteration> [--against <iteration>]   (relative to $EVAL_WS, like package.py)
  runviz.py --run <run-dir>
  runviz.py --compare <run-dir> <run-dir> [...] --out PAGE.html
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent


def analyzer_scripts() -> pathlib.Path:
    env = os.environ.get("WORKFLOW_ANALYZER_SCRIPTS")
    cached = sorted(pathlib.Path.home().glob(".claude/plugins/cache/*/workflow-analyzer/*/scripts"),
                    key=lambda p: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p.parent.name)])
    for cand in ([pathlib.Path(env).expanduser()] if env else []) + \
            [HERE.parents[2] / "workflow-analyzer" / "scripts"] + cached[::-1]:
        if (cand / "trace.py").exists():
            return cand
    sys.exit("runviz: the workflow-analyzer plugin's scripts were not found; install it "
             "(/plugin install workflow-analyzer@cott-plugins2) or set WORKFLOW_ANALYZER_SCRIPTS")


sys.path.insert(0, str(analyzer_scripts()))
import charts  # noqa: E402
import compare  # noqa: E402
import flow  # noqa: E402
import trace  # noqa: E402

WS = pathlib.Path(os.environ.get("EVAL_WS", HERE.parents[3] / "dev-team-workspace"))
PLUGIN = "dev-team"


def session_of(run: pathlib.Path) -> pathlib.Path | None:
    """The transcript of the agent session the driver ran in this folder."""
    stream = run / "agent_stream.jsonl"
    if not stream.exists():
        return None
    sid = None
    with stream.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.search(r'"session_id":\s*"([0-9a-f-]{36})"', line)
            if m:
                sid = m.group(1)
                break
    if not sid:
        return None
    hits = sorted(trace.PROJECTS.glob(f"*/{sid}.jsonl"))
    return hits[0] if hits else None


def eval_facts(run: pathlib.Path, compare_links: list[dict] | None = None) -> dict:
    def read(name):
        try:
            return json.loads((run / name).read_text())
        except (OSError, json.JSONDecodeError):
            return None

    turns = read("turns.json") or []
    prev, per_turn = 0.0, []
    for t in turns:
        cum = (t.get("usage") or {}).get("cost_usd")  # cumulative over the resumed session
        per_turn.append({"turn": int(t["turn"]), "stage": t.get("stage"), "seconds": t.get("seconds"),
                         "cost_usd": round(cum - prev, 4) if cum is not None else None})
        prev = cum if cum is not None else prev
    grading = read("grading.json") or {}
    return {"iteration": run.parents[1].name, "trajectory": run.parent.name, "run": str(run),
            "summary": read("summary.json") or {}, "checks": grading.get("expectations") or [],
            "turns": per_turn, "compare": compare_links or []}


def build_run(run: pathlib.Path, compare_links: list[dict] | None = None, quiet: bool = True) -> pathlib.Path | None:
    run = run.resolve()
    session = session_of(run)
    if session is None:
        print(f"runviz: no session transcript for {run}; skipped", file=sys.stderr)
        return None
    out = run / "flow"
    out.mkdir(exist_ok=True)
    (out / "eval.json").write_text(json.dumps(eval_facts(run, compare_links), indent=1))
    trace.build(session, PLUGIN, out, quiet=True)
    if not quiet:
        print(out / "flow.html")
    return out


def natural(name: str) -> list:
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", name)]


def previous(iteration: str) -> str | None:
    """The iteration listed just before this one in $EVAL_WS, by natural order of their names."""
    sibs = sorted((p.name for p in WS.iterdir() if p.is_dir() and p.name.startswith("iteration-")), key=natural)
    if iteration not in sibs:
        return None
    i = sibs.index(iteration)
    return sibs[i - 1] if i else None


def runs_of(iteration: str) -> dict[str, pathlib.Path]:
    it = WS / iteration
    return {p.parent.name: p for p in sorted(it.glob("*/with_skill")) if (p / "agent_stream.jsonl").exists()}


def build_iteration(iteration: str, against: str | None) -> pathlib.Path:
    against = against or previous(iteration)
    page_dir = WS / iteration / "runflow"
    page_dir.mkdir(parents=True, exist_ok=True)
    mine, theirs = runs_of(iteration), runs_of(against) if against else {}
    cards = []
    for traj, run in mine.items():
        base = theirs.get(traj)
        cmp_page = page_dir / f"{traj}-vs-{against}.html" if base else None
        links = ([{"label": f"compare with {against}",
                   "href": os.path.relpath(cmp_page, run / "flow")}] if cmp_page else [])
        out = build_run(run, links)
        if out is None:
            continue
        base_out = None
        if base:
            base_out = base / "flow" if (base / "flow" / "index.json").exists() else build_run(base)
        if base_out and cmp_page:
            compare.write([f"{against}={base_out}", f"{iteration}={out}"], cmp_page)
        cards.append((traj, out, base_out, cmp_page))
        print(f"runviz: {traj}: {out / 'flow.html'}" + (f" · vs {against}: {cmp_page}" if cmp_page else ""))
    index = write_index(iteration, against, cards, page_dir)
    print(f"runviz: {index}")
    return index


def write_index(iteration: str, against: str | None, cards: list, page_dir: pathlib.Path) -> pathlib.Path:
    def rel(p):
        return pathlib.Path(os.path.relpath(p, page_dir)).as_posix()

    def stats(out):
        idx = json.loads((out / "index.json").read_text())
        ev = flow.load_eval(out) or {}
        st = flow.run_stats(idx)
        checks = ev.get("checks") or []
        st["cost"] = sum(t.get("cost_usd") or 0 for t in ev.get("turns") or []) or None
        st["passed"] = (sum(1 for c in checks if c.get("passed")), len(checks)) if checks else None
        return st

    rows = []
    metrics = [("Turns", "turns", str, True), ("Working time", "busy", charts.dur, True),
               ("Output tokens", "output", charts.kt, True), ("Peak context", "context_peak", charts.kt, True),
               ("Agents", "units", str, None), ("Files changed", "files_changed", str, None),
               ("Cost", "cost", lambda v: f"${v:.2f}", True)]
    for traj, out, base_out, cmp_page in cards:
        a, b = stats(out), (stats(base_out) if base_out else None)
        cells = []
        for _, key, fmt, lower in metrics:
            v = a.get(key)
            d = compare.delta(b.get(key), v, fmt, lower) if b else ""
            cells.append(f"<td>{charts.esc(fmt(v)) if v is not None else '—'} {d}</td>")
        p = a["passed"]
        pb = b["passed"] if b else None
        grade = f"{p[0]}/{p[1]}" if p else "—"
        if p and pb:
            grade += " " + compare.delta(pb[0], p[0], str, False)
        rows.append(f'<tr><td><a href="{rel(out / "flow.html")}"><b>{charts.esc(traj)}</b></a></td><td>{grade}</td>'
                    + "".join(cells)
                    + (f'<td><a href="{rel(cmp_page)}">vs {charts.esc(against)}</a></td>' if cmp_page else "<td>—</td>")
                    + "</tr>")
    head = ("<tr><th>Trajectory</th><th>Checks</th>" + "".join(f"<th>{m[0]}</th>" for m in metrics)
            + "<th>Comparison</th></tr>")
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Eval runs</title>
<style>{flow.CSS}{charts.CHART_CSS}td i{{font-style:normal;font-size:12px;margin-left:4px}}</style></head>
<body>
<h1>{charts.esc(iteration)} · eval runs</h1>
<div class="sub">{len(cards)} trajectories{f" · changes against {charts.esc(against)}: <span class=ok>green</span> better, <span class=bad>red</span> worse" if against else ""}</div>
<div class="scroll"><table>{head}{"".join(rows)}</table></div>
<p class="legend">Each trajectory opens its run page: the timeline, tokens and time per turn and per agent, the files
each turn read and edited, and a page per turn and per agent with every step.</p>
</body></html>"""
    path = page_dir / "index.html"
    path.write_text(html, encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("iteration", nargs="?")
    ap.add_argument("--against", help="the iteration to compare with (default: the one before)")
    ap.add_argument("--run", help="build one run folder")
    ap.add_argument("--compare", nargs="+", help="run folders to compare; the first is the baseline")
    ap.add_argument("--out", help="the comparison page, with --compare")
    a = ap.parse_args()
    if a.run:
        return 0 if build_run(pathlib.Path(a.run), quiet=False) else 1
    if a.compare:
        if not a.out or len(a.compare) < 2:
            ap.error("--compare needs two or more run folders and --out")
        outs = []
        for r in map(pathlib.Path, a.compare):
            r = r.resolve()
            built = r / "flow" if (r / "flow" / "index.json").exists() else build_run(r)
            if built is None:
                return 1
            outs.append(str(built))
        print(compare.write(outs, pathlib.Path(a.out)))
        return 0
    if not a.iteration:
        ap.error("give an iteration, --run or --compare")
    build_iteration(a.iteration, a.against)
    return 0


if __name__ == "__main__":
    sys.exit(main())
