#!/usr/bin/env python3
"""Answer questions about a built run from its workspace, citing step ids.

Reads only what `trace.py build` wrote: DIR/index.json, DIR/turns/T<nn>.json and
DIR/units/U<nn>.json. Every line it prints carries the id it came from (T04, U02, D31,
U02.S7), so an answer built from it can cite them.

Usage:
  query.py overview DIR                  the session, its tokens, and one line per turn and unit
  query.py turn DIR T04 [--steps]        one turn: prompt, reply, skills, units, files, tokens
  query.py unit DIR U02 [--steps]        one agent: type, spawner, prompt, files, tokens, return
  query.py step DIR D31|U02.S7 [--full]  one step's input and output (clipped unless --full)
  query.py files DIR [PATTERN]           every read/write/edit of paths containing PATTERN,
                                         with turn, step and who did it
  query.py slow DIR [T04|U02] [--top N]  the longest gaps between consecutive steps: where the
                                         time went (a gap is the step's own run time plus the
                                         model's time to decide the next step)
  query.py grep DIR TEXT [--top N]       steps whose summary, input or output contains TEXT
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def load(d: Path, name: str) -> dict:
    return json.loads((d / name).read_text(encoding="utf-8"))


def ts(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def dur(a: str | None, b: str | None) -> str:
    x, y = ts(a), ts(b)
    if not (x and y):
        return "—"
    sec = int((y - x).total_seconds())
    return f"{sec // 3600}h{sec % 3600 // 60:02d}m" if sec >= 3600 else f"{sec // 60}m{sec % 60:02d}s"


def kt(n: int | None) -> str:
    n = n or 0
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.1f}k" if n >= 1e3 else str(n)


def tok(t: dict | None) -> str:
    t = t or {}
    return (f"out {kt(t.get('output'))} · in {kt(t.get('input'))} · cache-write {kt(t.get('cache_write'))} · "
            f"cache-read {kt(t.get('cache_read'))} · peak ctx {kt(t.get('context_peak'))} · {t.get('requests', 0)} req")


def short(path: str, project: str | None) -> str:
    if project and path.startswith(project.rstrip("/") + "/"):
        return path[len(project.rstrip("/")) + 1:]
    return path.replace(str(Path.home()), "~")


def line(s: str, n: int = 160) -> str:
    s = " ⏎ ".join(x for x in (s or "").strip().splitlines() if x.strip())
    return s if len(s) <= n else s[:n] + " …"


def all_docs(d: Path) -> list[dict]:
    """Every turn and unit document, in id order."""
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((d / "turns").glob("T*.json")) + sorted((d / "units").glob("U*.json"))]


def doc_for(d: Path, ident: str) -> dict:
    ident = ident.upper()
    folder = "turns" if ident.startswith("T") else "units"
    p = d / folder / f"{ident}.json"
    if not p.exists():
        sys.exit(f"no {ident} in {d} (have: {', '.join(x.stem for x in sorted((d / folder).glob('*.json')))})")
    return json.loads(p.read_text(encoding="utf-8"))


def overview(d: Path) -> None:
    i = load(d, "index.json")
    print(f"session {i['session']} · \"{i['title']}\"")
    print(f"project {i['project']} · branch {i['branch']} · models {', '.join(i['models'])}")
    print(f"span {i['first_ts']} → {i['last_ts']} ({dur(i['first_ts'], i['last_ts'])})")
    print(f"tokens all: {tok(i['tokens']['all'])}")
    print(f"tokens main thread: {tok(i['tokens']['main'])}")
    print(f"\n{len(i['turns'])} turns:")
    for t in i["turns"]:
        changed = sorted({short(f["path"], i["project"]) for f in t["files"] if f["op"] in ("write", "edit")})
        errs = f", {t['errors']} err" if t["errors"] else ""
        print(f"  {t['turn']} {t['first_step']}–{t['last_step']} · {dur(t['first_ts'], t['last_ts'])} · "
              f"{t['tool_calls']} calls{errs} · "
              f"out {kt(t['tokens']['output'])}"
              + (f" · skills {', '.join(x for x in t['skills'] if x)}" if any(t["skills"]) else "")
              + (f" · units {', '.join(t['units'])}" if t["units"] else "")
              + (f" · changed {len(changed)}: {', '.join(changed[:4])}{' …' if len(changed) > 4 else ''}" if changed else ""))
        print(f"      user: {line(t['prompt_first_line'], 140)}")
    if i["units"]:
        print(f"\n{len(i['units'])} units (spawned agents):")
        for u in i["units"]:
            print(f"  {u['unit']} {u['type']} · \"{line(u['description'], 60)}\" · by {u['spawner']}"
                  f"{' at ' + u['spawn_step'] if u.get('spawn_step') else ''} · T{u.get('turn') or 0:02d} · "
                  f"{dur(u['first_ts'], u['last_ts'])} · {u['tool_calls']} calls · out {kt(u['tokens']['output'])}"
                  f"{'' if u['finished'] else ' · unfinished'}{' · background' if u['background'] else ''}")


def files_block(ops: list[dict], project: str | None) -> list[str]:
    by: dict[tuple[str, str], list[str]] = {}
    for o in ops:
        by.setdefault((short(o["path"], project), o["op"]), []).append(
            f"{o.get('step')}{'(Bash)' if o.get('via') == 'Bash' else ''}{'(failed)' if o.get('error') else ''}"
            f"{'' if o.get('who') in (None, 'main') else '@' + o['who']}")
    order = {"write": 0, "edit": 1, "read": 2}
    return [f"  {op:5} {path}  [{', '.join(steps)}]" for (path, op), steps in
            sorted(by.items(), key=lambda kv: (order.get(kv[0][1], 9), kv[0][0]))]


def step_line(s: dict) -> str:
    err = " ✗" if s.get("error") else ""
    blocked = " ⛔" if s.get("blocked") or any(h.get("blocked") for h in s.get("hooks") or []) else ""
    return f"  {s['step']:>8} {s['ts'][11:19]} {s['kind']:<10}{err}{blocked} {line(s.get('summary', ''), 170)}"


def turn(d: Path, ident: str, steps: bool) -> None:
    i = load(d, "index.json")
    t = doc_for(d, ident)
    print(f"{t['turn']} · steps {t['first_step']}–{t['last_step']} · {t['first_ts']} → {t['last_ts']} "
          f"({dur(t['first_ts'], t['last_ts'])}) · {t['tool_calls']} calls · {t['errors']} errors · "
          f"{t['hook_blocks']} hook blocks")
    print(f"tokens: {tok(t['tokens'])}  (main {kt(t['tokens_main']['output'])} out, units {kt(t['tokens_units']['output'])} out)")
    print(f"skills: {', '.join(x for x in t['skills'] if x) or 'none'} · units: {', '.join(t['units']) or 'none'}")
    print(f"user said:\n  {line(t['prompt'], 1200)}")
    print(f"assistant's last message:\n  {line(t['return'], 800)}")
    print("files (op path [steps; @unit when an agent did it]):")
    print("\n".join(files_block(t["file_ops"], i["project"])) or "  none")
    if steps:
        print("steps:")
        for s in t["steps"]:
            print(step_line(s))
    page = d / "turns" / f"{t['turn']}.html"
    print(f"page: {page}")


def unit(d: Path, ident: str, steps: bool) -> None:
    i = load(d, "index.json")
    u = doc_for(d, ident)
    print(f"{u['unit']} · {u['type']} · \"{u['description']}\" · spawned by {u['spawner']}"
          f"{' at ' + u['spawn_step'] if u.get('spawn_step') else ''} in T{u.get('turn') or 0:02d}"
          f"{' · background' if u.get('background') else ''}")
    print(f"{u['first_ts']} → {u['last_ts']} ({dur(u['first_ts'], u['last_ts'])}) · {u['tool_calls']} calls · "
          f"{u['errors']} errors · models {', '.join(u.get('models') or [])} · {'finished' if u['finished'] else 'unfinished'}")
    print(f"tokens: {tok(u['tokens'])}")
    print(f"skills: {', '.join(x for x in u.get('skills') or [] if x) or 'none'} · commits: "
          f"{', '.join(c.get('sha', '?') if isinstance(c, dict) else str(c) for c in u.get('commits') or []) or 'none'}")
    print(f"prompt:\n  {line(u['prompt'], 1200)}")
    print(f"returned:\n  {line(u['return'], 800)}")
    print("files:")
    print("\n".join(files_block(u["file_ops"], i["project"])) or "  none")
    if steps:
        print("steps:")
        for s in u["steps"]:
            print(step_line(s))
    print(f"page: {d / 'units' / (u['unit'] + '.html')}")


def find_step(d: Path, sid: str) -> tuple[dict, dict]:
    sid = sid.upper()
    if "." in sid:
        doc = doc_for(d, sid.split(".")[0])
        hits = [s for s in doc["steps"] if s["step"].upper() == sid]
    else:
        doc, hits = {}, []
        for p in sorted((d / "turns").glob("T*.json")):
            doc = json.loads(p.read_text(encoding="utf-8"))
            hits = [s for s in doc["steps"] if s["step"].upper() == sid]
            if hits:
                break
    if not hits:
        sys.exit(f"no step {sid} in {d}")
    return doc, hits[0]


def step(d: Path, sid: str, full: bool) -> None:
    doc, s = find_step(d, sid)
    n = None if full else 3000
    clip = (lambda x: x if n is None or len(x) <= n else x[:n] + f"\n…[+{len(x) - n} chars; --full for all]")
    owner = doc.get("unit") or doc.get("turn")
    print(f"{s['step']} in {owner} · {s['ts']} · {s['kind']}{' · ' + s['tool'] if s.get('tool') else ''}"
          f"{' · ERROR' if s.get('error') else ''}")
    if s["kind"] == "call":
        print("input:\n" + clip(json.dumps(s["input"], indent=1, ensure_ascii=False)))
        print("output:\n" + clip(str(s.get("output") or "")))
        for h in s.get("hooks") or []:
            print(f"hook {h['hook']}{' BLOCKED' if h['blocked'] else ''}: {line(h['text'], 400)}")
    else:
        print(clip(s.get("text") or s.get("summary") or ""))
    page = (d / ("units" if owner.startswith("U") else "turns") / f"{owner}.html")
    print(f"page: {page}#{s['step']}")


def files(d: Path, pattern: str) -> None:
    i = load(d, "index.json")
    rows = []
    for doc in all_docs(d):
        if doc.get("type") != "turn":
            continue
        for o in doc["file_ops"]:
            if pattern in o["path"]:
                rows.append((o["path"], doc["turn"], o))
    if not rows:
        print(f"no file op on a path containing {pattern!r}")
        return
    cur = None
    for path, t, o in sorted(rows, key=lambda r: (r[0], r[1])):
        if path != cur:
            print(short(path, i["project"]))
            cur = path
        print(f"  {t} {o['op']:5} {o.get('step')}{' via Bash' if o.get('via') == 'Bash' else ''}"
              f"{' by ' + o['who'] if o.get('who') not in (None, 'main') else ''}{' (failed)' if o.get('error') else ''}")


def slow(d: Path, scope: str | None, top: int) -> None:
    docs = [doc_for(d, scope)] if scope else all_docs(d)
    gaps = []
    for doc in docs:
        st = doc["steps"]
        end = doc.get("last_ts")
        for a, b in zip(st, st[1:] + [{"ts": end}]):
            x, y = ts(a.get("ts")), ts(b.get("ts"))
            if x and y and y > x:
                gaps.append(((y - x).total_seconds(), doc.get("unit") or doc.get("turn"), a))
    gaps.sort(key=lambda g: -g[0])
    total = sum(g[0] for g in gaps)
    print(f"{len(gaps)} gaps, {int(total)}s in all; the longest:")
    for sec, owner, a in gaps[:top]:
        print(f"  {int(sec) // 60}m{int(sec) % 60:02d}s  {owner}  {step_line(a).strip()}")


def grep(d: Path, text: str, top: int) -> None:
    rx = re.compile(re.escape(text), re.I)
    n = 0
    for doc in all_docs(d):
        for s in doc["steps"]:
            blob = " ".join(str(s.get(k) or "") for k in ("summary", "text", "output")) + json.dumps(s.get("input") or {})
            if rx.search(blob):
                print(f"{doc.get('unit') or doc.get('turn')}  {step_line(s).strip()}")
                n += 1
                if n >= top:
                    print(f"… stopped at {top}; --top N for more")
                    return


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("overview").add_argument("dir")
    for name in ("turn", "unit"):
        p = sub.add_parser(name)
        p.add_argument("dir")
        p.add_argument("id")
        p.add_argument("--steps", action="store_true")
    p = sub.add_parser("step")
    p.add_argument("dir")
    p.add_argument("id")
    p.add_argument("--full", action="store_true")
    p = sub.add_parser("files")
    p.add_argument("dir")
    p.add_argument("pattern", nargs="?", default="")
    p = sub.add_parser("slow")
    p.add_argument("dir")
    p.add_argument("scope", nargs="?")
    p.add_argument("--top", type=int, default=10)
    p = sub.add_parser("grep")
    p.add_argument("dir")
    p.add_argument("text")
    p.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    d = Path(a.dir).expanduser()
    if not (d / "index.json").exists():
        sys.exit(f"{d} has no index.json: build it first with trace.py build")
    if a.cmd == "overview":
        overview(d)
    elif a.cmd == "turn":
        turn(d, a.id, a.steps)
    elif a.cmd == "unit":
        unit(d, a.id, a.steps)
    elif a.cmd == "step":
        step(d, a.id, a.full)
    elif a.cmd == "files":
        files(d, a.pattern)
    elif a.cmd == "slow":
        slow(d, a.scope, a.top)
    else:
        grep(d, a.text, a.top)
    return 0


if __name__ == "__main__":
    sys.exit(main())
