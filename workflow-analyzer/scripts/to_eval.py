#!/usr/bin/env python3
"""Turn a built run into a replayable eval: a scenario, its checks and the expected evidence.

Reads a workspace `trace.py build` wrote and writes EVAL_DIR:

  scenario.json        what to replay and what to expect:
      source           the session, its transcript, project, branch, models, span, workspace
      setup            how replay.py recreates the starting project: `git` (clone REPO at the
                       last commit before the session started, then run in SUBDIR) or `empty`
      mode             `scripted` (send the user's prompts verbatim) or `simulated` (a simulated
                       user adapts each prompt to what the assistant actually said; needs persona)
      persona, facts   for simulated mode: who the user is and what they know (left for the
                       run-to-eval skill to write from the prompts)
      turns            one per prompt the user typed: its text (without the <system-reminder>
                       context the app prepends), the original turn it came from,
                       and what that turn did (files changed and read, skills, agents, tokens,
                       seconds). `replay: false` marks prompts the app injected (task
                       notifications, session events), which a replay skips
      checks           what a replay is graded on (see check.py): files changed per turn and in
                       all, skills invoked, agent types spawned, the final files, and budgets
  expected/final/      the final content of every file the session wrote or edited inside the
                       project, as it is on disk now (a file changed since the session ended is
                       flagged in scenario.json, `final_files[].changed_since`)
  expected/file_ops.json  every read/write/edit per original turn, paths relative to the project

Usage: to_eval.py WS [--out EVAL_DIR] [--id NAME] [--mode scripted|simulated]
                  [--budget-factor 1.5] [--no-final]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

INJECTED = re.compile(r"^\s*(<(task-notification|side-sessions-event|ci-monitor-event|local-command|command-message|"
                      r"user-prompt-submit-hook|bash-)|\[Request interrupted)", re.I)
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>\s*", re.S)


def typed(prompt: str | None) -> str | None:
    """What the user typed: the prompt without the context blocks the app prepends, or None for a
    message the app injected on its own (a task notification, an interruption, an empty turn)."""
    text = REMINDER.sub("", prompt or "").strip()
    return None if not text or INJECTED.match(text) else text
RUNS = Path(os.environ.get("RUN_FLOW_HOME") or Path.home() / ".claude" / "run-flow")


def git(cwd: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def setup_of(index: dict) -> dict:
    """The repo and commit the session started from, when the project is still a git checkout."""
    cwd = Path(index["project"] or "")
    if not cwd.is_dir():
        return {"kind": "empty", "why": f"{cwd} no longer exists"}
    top = git(cwd, "rev-parse", "--show-toplevel")
    if not top:
        return {"kind": "empty", "why": f"{cwd} is not a git checkout"}
    before = index["first_ts"]
    commit = None
    for ref in [index.get("branch"), "HEAD"]:
        if ref and ref != "HEAD" and not git(cwd, "rev-parse", "--verify", "-q", ref):
            continue
        commit = git(cwd, "rev-list", "-1", f"--before={before}", ref or "HEAD")
        if commit:
            break
    if not commit:
        return {"kind": "empty", "why": f"no commit in {top} before {before}"}
    sub = cwd.resolve().relative_to(Path(top).resolve()).as_posix()
    return {"kind": "git", "repo": top, "commit": commit, "subdir": "" if sub == "." else sub,
            "note": "uncommitted changes the project had when the session started are not reproduced"}


def rel(path: str, project: str) -> str | None:
    p = project.rstrip("/") + "/"
    return path[len(p):] if path.startswith(p) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ws")
    ap.add_argument("--out", help="default: $RUN_FLOW_HOME/evals/<id>")
    ap.add_argument("--id")
    ap.add_argument("--mode", choices=("scripted", "simulated"), default="scripted")
    ap.add_argument("--budget-factor", type=float, default=1.5)
    ap.add_argument("--no-final", action="store_true", help="don't copy the final files")
    a = ap.parse_args()

    ws = Path(a.ws).expanduser().resolve()
    index = json.loads((ws / "index.json").read_text(encoding="utf-8"))
    sid = index["session"]
    slug = re.sub(r"[^a-z0-9]+", "-", index["title"].lower()).strip("-")[:40].strip("-")
    eval_id = a.id or f"{slug}-{sid[:8]}"
    out = Path(a.out).expanduser().resolve() if a.out else RUNS / "evals" / eval_id
    out.mkdir(parents=True, exist_ok=True)
    project = index["project"] or ""
    plugin = index.get("plugin")
    units = {u["unit"]: u for u in index["units"]}

    turns, ops_by_turn = [], {}
    changed_all, read_all, skills_all, agents_all = [], [], [], []
    for t in index["turns"]:
        doc = json.loads((ws / "turns" / f"{t['turn']}.json").read_text(encoding="utf-8"))
        text = typed(doc["prompt"])
        injected = text is None
        prompt = text or doc["prompt"] or ""
        ops = [{**o, "path": rel(o["path"], project) or o["path"], "inside": rel(o["path"], project) is not None}
               for o in doc["file_ops"]]
        ops_by_turn[t["turn"]] = ops
        changed = list(dict.fromkeys(o["path"] for o in ops if o["inside"] and o["op"] in ("write", "edit")
                                     and not o.get("error")))
        read = list(dict.fromkeys(o["path"] for o in ops if o["inside"] and o["op"] == "read" and not o.get("error")))
        skills = [s for s in t["skills"] if s]
        agents = [units[u]["type"] for u in t["units"] if u in units]
        changed_all += changed
        read_all += read
        skills_all += skills
        agents_all += agents
        secs = None
        try:
            secs = round((dt.datetime.fromisoformat(t["last_ts"].replace("Z", "+00:00"))
                          - dt.datetime.fromisoformat(t["first_ts"].replace("Z", "+00:00"))).total_seconds())
        except ValueError:
            pass
        turns.append({"orig_turn": t["turn"], "replay": not injected, "prompt": prompt,
                      "did": {"files_changed": changed, "files_read": read, "skills": skills, "agents": agents,
                              "output_tokens": t["tokens"]["output"], "seconds": secs,
                              "tool_calls": t["tool_calls"], "errors": t["errors"]}})
    n = 0
    for t in turns:
        if t["replay"]:
            n += 1
            t["n"] = n
    replayed = [t for t in turns if t["replay"]]

    finals = []
    if not a.no_final:
        last = dt.datetime.fromisoformat(index["last_ts"].replace("Z", "+00:00")).timestamp() if index["last_ts"] else None
        for p in dict.fromkeys(changed_all):
            src = Path(project) / p
            if not src.is_file():
                finals.append({"path": p, "exists": False})
                continue
            dst = out / "expected" / "final" / p
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            mt = src.stat().st_mtime
            finals.append({"path": p, "exists": True, "bytes": src.stat().st_size,
                           **({"changed_since": dt.datetime.fromtimestamp(mt).isoformat(timespec="seconds")}
                              if last and mt > last + 60 else {})})
    (out / "expected").mkdir(exist_ok=True)
    (out / "expected" / "file_ops.json").write_text(json.dumps(ops_by_turn, indent=1), encoding="utf-8")

    checks = []
    for t in replayed:
        if t["did"]["files_changed"]:
            checks.append({"id": f"T{t['n']:02d}.files", "kind": "files_changed", "turn": t["n"],
                           "paths": t["did"]["files_changed"], "min_recall": 1.0,
                           "text": f"turn {t['n']} changes {', '.join(t['did']['files_changed'][:5])}"
                                   + (" …" if len(t["did"]["files_changed"]) > 5 else "")})
        if t["did"]["skills"]:
            checks.append({"id": f"T{t['n']:02d}.skills", "kind": "skills_invoked", "turn": t["n"],
                           "skills": list(dict.fromkeys(t["did"]["skills"])),
                           "text": f"turn {t['n']} invokes {', '.join(dict.fromkeys(t['did']['skills']))}"})
    all_changed = list(dict.fromkeys(changed_all))
    if all_changed:
        checks.append({"id": "run.files", "kind": "files_changed", "turn": None, "paths": all_changed,
                       "min_recall": 1.0, "text": f"the run changes all {len(all_changed)} files the original did"})
    if skills_all:
        checks.append({"id": "run.skills", "kind": "skills_invoked", "turn": None,
                       "skills": list(dict.fromkeys(skills_all)), "text": "the run invokes every skill the original did"})
    if agents_all:
        checks.append({"id": "run.agents", "kind": "agents_spawned", "turn": None,
                       "agents": list(dict.fromkeys(agents_all)), "text": "the run spawns every agent type the original did"})
    if finals and any(f["exists"] for f in finals):
        checks.append({"id": "run.final", "kind": "final_files", "paths": [f["path"] for f in finals if f["exists"]],
                       "min_similarity": 0.0,
                       "text": "every file the original ended with exists (similarity to the original is reported)"})
    tok = sum(t["did"]["output_tokens"] for t in replayed)
    secs = sum(t["did"]["seconds"] or 0 for t in replayed)
    checks.append({"id": "budget.output_tokens", "kind": "budget", "metric": "output_tokens",
                   "max": int(tok * a.budget_factor), "original": tok,
                   "text": f"output tokens within {a.budget_factor}× the original's {tok:,}"})
    checks.append({"id": "budget.seconds", "kind": "budget", "metric": "seconds",
                   "max": int(secs * a.budget_factor), "original": secs,
                   "text": f"wall time of the replayed turns within {a.budget_factor}× the original's {secs}s"})

    scenario = {
        "id": eval_id,
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "source": {"session": sid, "transcript": index["transcript"], "title": index["title"],
                   "project": project, "branch": index["branch"], "models": index["models"], "plugin": plugin,
                   "first_ts": index["first_ts"], "last_ts": index["last_ts"], "workspace": str(ws)},
        "setup": setup_of(index),
        "mode": a.mode,
        "persona": "",
        "facts": [],
        "turns": turns,
        "final_files": finals,
        "checks": checks,
    }
    (out / "scenario.json").write_text(json.dumps(scenario, indent=1, ensure_ascii=False), encoding="utf-8")

    skipped = [t["orig_turn"] for t in turns if not t["replay"]]
    print(f"eval: {out / 'scenario.json'}")
    print(f"  id {scenario['id']} · {len(replayed)} prompts to replay"
          + (f" · skipped as injected: {', '.join(skipped)}" if skipped else "")
          + f" · {len(checks)} checks · setup {scenario['setup']['kind']}"
          + (f" ({scenario['setup']['repo']} @ {scenario['setup']['commit'][:10]})" if scenario["setup"]["kind"] == "git" else
             f" ({scenario['setup'].get('why')})"))
    print(f"  expected: {len(all_changed)} files changed, {len(set(read_all))} read, "
          f"skills {', '.join(dict.fromkeys(skills_all)) or 'none'}, agents {', '.join(dict.fromkeys(agents_all)) or 'none'}")
    moved = [f["path"] for f in finals if f.get("changed_since")]
    gone = [f["path"] for f in finals if not f["exists"]]
    if moved:
        print(f"  ⚠ changed on disk since the session ended (expected/final holds today's version): {', '.join(moved[:6])}")
    if gone:
        print(f"  ⚠ no longer on disk: {', '.join(gone[:6])}")
    outside = sorted({o["path"] for ops in ops_by_turn.values() for o in ops
                      if not o["inside"] and o["op"] in ("write", "edit")})
    if outside:
        print(f"  ⚠ wrote outside the project (not checked, and a replay may write there too): {', '.join(outside[:6])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
