#!/usr/bin/env python3
"""Grade a built run against an eval's scenario.json checks.

WS is any workspace `trace.py build` wrote: a replay's (`<run>/flow/`), or the original's
(which passes its own checks, a sanity check of the scenario). Turns are matched in order: the
k-th prompt of WS that the app did not inject is scenario turn k. Files changed come from the
trace's file ops, plus, for a replay, the files each turn's git commit changed (WS/eval.json).

Check kinds (scenario.json `checks[]`):
  files_changed   `paths` written or edited in turn `turn` (or anywhere, when turn is null);
                  passes when the share found is at least `min_recall` (default 1.0)
  skills_invoked  every one of `skills` invoked in `turn` (or anywhere); a skill matches with
                  or without its plugin prefix
  agents_spawned  every one of `agents` (agent types) spawned somewhere in the run
  final_files     every one of `paths` exists in WS's project when the run ends, with a text
                  similarity to expected/final/<path> of at least `min_similarity`
  budget          `metric` (output_tokens | seconds | tool_calls | errors) summed over the
                  replayed turns is at most `max`

Writes, with --write: WS/eval.json (so the run's page shows the checks and compare.py
compares them) and re-renders WS/flow.html; with --grading FILE, a grading.json in the shape
dev-team's grade.py writes ({"expectations": [{id, text, passed, evidence}], "summary"}).
Prints one PASS/FAIL line per check either way.

With --upto N (replay.py passes it after --max-turns N), only the scenario's first N turns are
graded: later turns' checks and the final-files check are left out, and run-wide checks and
budgets are rebuilt from what those N turns did in the original.

Usage: check.py EVAL_DIR WS [--write] [--grading FILE] [--label NAME] [--upto N]
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow  # noqa: E402
from to_eval import rel, typed  # noqa: E402


def secs(t: dict) -> float:
    try:
        a = datetime.fromisoformat(t["first_ts"].replace("Z", "+00:00"))
        b = datetime.fromisoformat(t["last_ts"].replace("Z", "+00:00"))
        return (b - a).total_seconds()
    except (ValueError, KeyError):
        return 0.0


def more(xs: list) -> str:
    return f" +{len(xs) - 6} more" if len(xs) > 6 else ""


def bare(skill: str) -> str:
    return skill.split(":")[-1].lower()


def run_facts(ws: Path) -> dict:
    index = json.loads((ws / "index.json").read_text(encoding="utf-8"))
    project = index["project"] or ""
    units = {u["unit"]: u for u in index["units"]}
    ev = flow.load_eval(ws) or {}
    # A replay commits each turn, so its eval.json knows exactly which files each turn changed.
    git_changed = {int(x["turn"]): set(x["files_changed"]) for x in ev.get("turns") or [] if "files_changed" in x}
    turns = []
    for t in index["turns"]:
        doc = json.loads((ws / "turns" / f"{t['turn']}.json").read_text(encoding="utf-8"))
        if typed(doc["prompt"]) is None:
            continue
        changed = {rel(o["path"], project) for o in doc["file_ops"]
                   if o["op"] in ("write", "edit") and not o.get("error")} - {None}  # inside the project only
        changed |= git_changed.get(len(turns) + 1, set())
        turns.append({"turn": t["turn"], "changed": changed, "skills": [s for s in t["skills"] if s],
                      "agents": [units[u]["type"] for u in t["units"] if u in units],
                      "output_tokens": t["tokens"]["output"], "seconds": secs(t),
                      "tool_calls": t["tool_calls"], "errors": t["errors"]})
    return {"index": index, "project": project, "turns": turns}


def upto(scn: dict, n: int) -> tuple[dict, int]:
    """The scenario cut to its first n replayed turns, for a replay stopped there on purpose
    (--max-turns): later turns' checks are dropped, run-wide checks are rebuilt from what turns
    1..n did in the original, budgets are scaled to them, and the final-files check is dropped."""
    did = [t["did"] for t in scn["turns"] if t.get("replay")][:n]
    keep = []
    for c in scn["checks"]:
        k, t = c["kind"], c.get("turn")
        if t is not None:
            if t <= n:
                keep.append(c)
            continue
        if k == "files_changed":
            paths = list(dict.fromkeys(p for d in did for p in d["files_changed"]))
            if paths:
                keep.append({**c, "paths": paths, "text": f"turns 1–{n} change all {len(paths)} files they did"})
        elif k == "skills_invoked":
            skills = list(dict.fromkeys(x for d in did for x in d["skills"]))
            if skills:
                keep.append({**c, "skills": skills, "text": f"turns 1–{n} invoke every skill they did"})
        elif k == "agents_spawned":
            agents = list(dict.fromkeys(x for d in did for x in d["agents"]))
            if agents:
                keep.append({**c, "agents": agents, "text": f"turns 1–{n} spawn every agent type they did"})
        elif k == "budget":
            orig = sum(d.get(c["metric"]) or 0 for d in did)
            factor = c["max"] / c["original"] if c.get("original") else 1.5
            keep.append({**c, "original": orig, "max": int(orig * factor),
                         "text": f"{c['metric']} of turns 1–{n} within {factor:g}× the original's {orig:,}"})
    return {**scn, "checks": keep}, len(scn["checks"]) - len(keep)


def grade(scn: dict, eval_dir: Path, facts: dict) -> list[dict]:
    turns = facts["turns"]
    out = []

    def turn_of(n):
        return turns[n - 1] if n and n <= len(turns) else None

    def where(n):
        t = turn_of(n)
        return f" (as {t['turn']})" if t else ""

    for c in scn["checks"]:
        k, n = c["kind"], c.get("turn")
        scope = [turn_of(n)] if n else turns
        if n and scope[0] is None:
            out.append({**c, "passed": False, "evidence": f"the run has only {len(turns)} turns; no turn {n}"})
            continue
        if k == "files_changed":
            got = set().union(*(t["changed"] for t in scope)) if scope else set()
            want = c["paths"]
            hit = [p for p in want if p in got]
            recall = len(hit) / len(want) if want else 1.0
            missing = [p for p in want if p not in got]
            extra = sorted(got - set(want))
            ok = recall >= c.get("min_recall", 1.0)
            ev = (f"{len(hit)}/{len(want)} changed{where(n)}"
                  + (f"; missing: {', '.join(missing[:6])}{more(missing)}" if missing else "")
                  + (f"; also changed: {', '.join(extra[:6])}{more(extra)}" if extra else ""))
        elif k == "skills_invoked":
            got = {bare(s) for t in scope for s in t["skills"]}
            missing = [s for s in c["skills"] if bare(s) not in got]
            ok = not missing
            ev = (f"invoked{where(n)}: {', '.join(sorted(got)) or 'none'}"
                  + (f"; missing: {', '.join(missing)}" if missing else ""))
        elif k == "agents_spawned":
            got = {a.lower() for t in turns for a in t["agents"]} | {bare(a) for t in turns for a in t["agents"]}
            missing = [a for a in c["agents"] if a.lower() not in got and bare(a) not in got]
            ok = not missing
            ev = (f"spawned: {', '.join(sorted({a for t in turns for a in t['agents']})) or 'none'}"
                  + (f"; missing: {', '.join(missing)}" if missing else ""))
        elif k == "final_files":
            root = Path(facts["project"])
            bad, sims = [], []
            for p in c["paths"]:
                f = root / p
                if not f.is_file():
                    bad.append(f"{p} missing")
                    continue
                exp = eval_dir / "expected" / "final" / p
                if exp.is_file():
                    a = exp.read_text(encoding="utf-8", errors="replace").splitlines()
                    b = f.read_text(encoding="utf-8", errors="replace").splitlines()
                    r = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
                    sims.append((p, r))
                    if r < c.get("min_similarity", 0.0):
                        bad.append(f"{p} similarity {r:.2f}")
            ok = not bad
            mean = sum(r for _, r in sims) / len(sims) if sims else None
            ev = (f"{len(c['paths']) - len(bad)}/{len(c['paths'])} present"
                  + (f"; mean line similarity {mean:.2f}" if mean is not None else "")
                  + (f"; least similar: {', '.join(f'{p} {r:.2f}' for p, r in sorted(sims, key=lambda x: x[1])[:3])}" if sims else "")
                  + (f"; {', '.join(bad[:6])}" if bad else ""))
        elif k == "budget":
            m = c["metric"]
            v = sum(t[m] for t in scope)
            ok = v <= c["max"]
            ev = f"{m} {v:,.0f} (max {c['max']:,}; original {c.get('original', '?'):,})" if isinstance(c.get("original"), (int, float)) \
                else f"{m} {v:,.0f} (max {c['max']:,})"
        else:
            ok, ev = False, f"unknown check kind {k!r}"
        out.append({"id": c["id"], "text": c.get("text", ""), "passed": bool(ok), "evidence": ev})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("eval_dir")
    ap.add_argument("ws")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--grading")
    ap.add_argument("--label")
    ap.add_argument("--upto", type=int, help="grade only the scenario's first N turns (a replay cut short on purpose)")
    a = ap.parse_args()
    eval_dir, ws = Path(a.eval_dir).expanduser().resolve(), Path(a.ws).expanduser().resolve()
    scn = json.loads((eval_dir / "scenario.json").read_text(encoding="utf-8"))
    facts = run_facts(ws)
    skipped = 0
    if a.upto and a.upto < sum(1 for t in scn["turns"] if t.get("replay")):
        scn, skipped = upto(scn, a.upto)
    results = grade(scn, eval_dir, facts)
    passed = sum(r["passed"] for r in results)
    for r in results:
        print(("PASS " if r["passed"] else "FAIL ") + f"[{r['id']}] {r['text']}  — {r['evidence'][:200]}")
    print(f"{passed}/{len(results)} checks pass · {len(facts['turns'])} turns graded against "
          f"{a.upto if skipped else sum(1 for t in scn['turns'] if t.get('replay'))} in the scenario"
          + (f" · {skipped} checks of later turns or the final files not graded (--upto {a.upto})" if skipped else ""))
    summary = {"passed": passed, "failed": len(results) - passed, "total": len(results),
               "pass_rate": round(passed / len(results), 3) if results else None}
    if a.grading:
        Path(a.grading).write_text(json.dumps({"expectations": results, "summary": summary}, indent=1))
    if a.write:
        old = flow.load_eval(ws) or {}
        ev = {**old, "iteration": a.label or old.get("iteration") or ws.name, "trajectory": scn["id"],
              "run": str(ws), "checks": results, "summary": {**(old.get("summary") or {}), **summary}}
        (ws / "eval.json").write_text(json.dumps(ev, indent=1), encoding="utf-8")
        flow.write_html(ws)
    return 0


if __name__ == "__main__":
    sys.exit(main())
