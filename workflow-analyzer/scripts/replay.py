#!/usr/bin/env python3
"""Replay an eval made by to_eval.py: a fresh project, the user's prompts, then grade and compare.

  1. Project: <out>/project, a clone of the scenario's repo at its start commit (with no remote,
     so nothing the agent does can push back), or an empty git repo. The agent runs in its
     `subdir`. Every turn is committed as "turn N", so `git log -p` shows what each one did,
     and the files each commit changed are the turn's `files_changed` in turns.json and
     flow/eval.json, which check.py trusts over the trace's guesses from Bash commands.
  2. Turns: one `claude -p` per prompt, resuming one session, its stream appended to
     <out>/agent_stream.jsonl. Scripted mode sends each prompt as typed (with the original
     project path rewritten to the replay's); simulated mode has a simulated user (a second,
     tool-less `claude -p`) rewrite each original prompt as a reply to what the assistant
     actually said, from the scenario's persona and facts.
  3. Afterwards: the session is built into <out>/flow/ (trace.py), graded against the
     scenario's checks (check.py: <out>/grading.json, <out>/flow/eval.json), and compared with
     the original's workspace (compare.py: <out>/compare.html).

<out> has the layout dev-team's harness reads (agent_stream.jsonl, turns.json, summary.json,
grading.json, flow/), so its runviz.py and package.py work on it too.

The agent runs with --permission-mode bypassPermissions and AskUserQuestion disallowed (a
question becomes text the next prompt answers). It loads the user's own settings, plugins and
CLAUDE.md unless --isolate, which keeps only project/local settings, no CLAUDE.md files and no
MCP servers, as dev-team's driver does; --plugin-dir loads a plugin under test either way.

Env: CLAUDE_BIN (default `claude`).

Usage: replay.py EVAL_DIR [--out RUN_DIR] [--model M] [--user-model M] [--mode scripted|simulated]
                 [--max-turns N] [--plugin-dir DIR ...] [--isolate] [--cost-cap USD]
                 [--turn-timeout SEC] [--label NAME]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare  # noqa: E402
import trace  # noqa: E402

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
STRIP_ENV = ["CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_REMOTE_SESSION_ID", "CLAUDE_CODE_TEE_SDK_STDOUT",
             "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_DIAGNOSTICS_FILE",
             "CLAUDECODE", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR", "CLAUDE_CODE_ENTRYPOINT"]
ENV = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}


def sh(cmd: list[str], cwd: Path, env: dict | None = None, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=env or ENV, capture_output=True, text=True, **kw)


def commit(proj: Path, msg: str) -> None:
    sh(["git", "add", "-A"], proj)
    sh(["git", "-c", "user.email=replay@local", "-c", "user.name=replay", "commit", "-q", "--allow-empty",
        "--no-verify", "-m", msg], proj)


def setup(scn: dict, out: Path) -> tuple[Path, Path]:
    """Returns (repo root, the directory the agent runs in)."""
    proj = out / "project"
    if proj.exists():
        shutil.rmtree(proj)
    st = scn["setup"]
    if st["kind"] == "git":
        r = sh(["git", "clone", "-q", "--no-checkout", st["repo"], str(proj)], out)
        if r.returncode != 0:
            sys.exit(f"clone of {st['repo']} failed: {r.stderr.strip()}")
        r = sh(["git", "checkout", "-q", st["commit"]], proj)
        if r.returncode != 0:
            sys.exit(f"checkout of {st['commit']} failed: {r.stderr.strip()}")
        sh(["git", "checkout", "-q", "-b", "replay"], proj)
        sh(["git", "remote", "remove", "origin"], proj)
    else:
        proj.mkdir(parents=True)
        sh(["git", "init", "-q"], proj)
        commit(proj, "turn 0")
    cwd = proj / st.get("subdir", "") if st.get("subdir") else proj
    cwd.mkdir(parents=True, exist_ok=True)
    return proj, cwd


def mcp_args(out: Path, isolate: bool) -> list[str]:
    if not isolate:
        return []
    (out / "mcp.json").write_text(json.dumps({"mcpServers": {}}))
    return ["--mcp-config", str(out / "mcp.json"), "--strict-mcp-config", "--setting-sources", "project,local"]


def agent_turn(cwd: Path, sid: str, msg: str, first: bool, a, extra: list[str], log: Path, env: dict) -> dict:
    cmd = [CLAUDE_BIN, "-p", msg, "--output-format", "stream-json", "--verbose", "--include-hook-events",
           "--permission-mode", "bypassPermissions", "--disallowedTools", "AskUserQuestion", *extra]
    if a.model:
        cmd += ["--model", a.model]
    for p in a.plugin_dir or []:
        cmd += ["--plugin-dir", str(Path(p).expanduser().resolve())]
    cmd += ["--session-id", sid] if first else ["--resume", sid]
    t0 = time.time()
    try:
        r = sh(cmd, cwd, env=env, timeout=a.turn_timeout)
        stdout, rc, err = r.stdout, r.returncode, r.stderr
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        rc, err = -1, f"timed out after {a.turn_timeout}s"
    secs = time.time() - t0
    with log.open("a") as f:
        f.write(stdout)
    result, usage, tools, skills = "", {}, [], []
    for line in stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "assistant":
            for c in (d.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    tools.append(c["name"])
                    if c["name"] == "Skill":
                        skills.append((c.get("input") or {}).get("skill"))
        if d.get("type") == "result":
            result = d.get("result") or ""
            usage = {"cost_usd": d.get("total_cost_usd"), "duration_ms": d.get("duration_ms"),
                     "usage": d.get("usage"), "num_turns": d.get("num_turns")}
    if not result and rc != 0:
        result = f"[agent error rc={rc}] {err[-500:]}"
    return {"assistant": result, "usage": usage, "tools": tools, "skills": skills, "seconds": round(secs, 1)}


def sim_user(scn: dict, a, original: str, history: list[str], reply: str, last: bool) -> str:
    """The original prompt, rewritten as a reply to what the assistant actually said."""
    facts = "\n".join(f"- {f}" for f in scn.get("facts") or [])
    prompt = f"""{scn.get('persona') or 'You are the user of a coding assistant. You are terse and decisive.'}

FACTS YOU KNOW (your ground truth):
{facts or '- (none beyond your original message below)'}

You are replaying a conversation you once had with a coding assistant. In the original, at this
point you said:
<<<
{original[:6000]}
>>>

Recent conversation in this replay (oldest first):
{chr(10).join(history[-3:])}

THE ASSISTANT'S LATEST MESSAGE:
<<<
{reply[-8000:]}
>>>

Write what you say now. Keep the intent of your original message: ask for the same thing, approve
or decide the same way, give the same facts. Adapt only what no longer fits: answer the questions
this assistant actually asked, from your facts and your original message; don't refer to things it
never said. Never write code or documents yourself.{' This is your last message.' if last else ''}
Return ONLY the message text."""
    r = sh([CLAUDE_BIN, "-p", prompt, "--model", a.user_model, "--tools", "", "--output-format", "json",
            "--no-session-persistence", "--setting-sources", "project,local"], HERE,
           env={**ENV, "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1"}, timeout=600)
    try:
        return json.loads(r.stdout)["result"].strip() or original
    except (ValueError, KeyError):
        return original


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("eval_dir")
    ap.add_argument("--out", help="default: EVAL_DIR/runs/<label>-<YYYYmmdd-HHMM>")
    ap.add_argument("--model", help="the agent's model (default: the CLI's default)")
    ap.add_argument("--user-model", default="sonnet")
    ap.add_argument("--mode", choices=("scripted", "simulated"))
    ap.add_argument("--max-turns", type=int)
    ap.add_argument("--plugin-dir", action="append")
    ap.add_argument("--isolate", action="store_true")
    ap.add_argument("--cost-cap", type=float, default=50.0)
    ap.add_argument("--turn-timeout", type=int, default=1800)
    ap.add_argument("--label", default="replay")
    a = ap.parse_args()

    eval_dir = Path(a.eval_dir).expanduser().resolve()
    scn = json.loads((eval_dir / "scenario.json").read_text(encoding="utf-8"))
    mode = a.mode or scn.get("mode", "scripted")
    if mode == "simulated" and not scn.get("persona"):
        print("replay: simulated mode with no persona in scenario.json; using a generic one", file=sys.stderr)
    out = (Path(a.out).expanduser().resolve() if a.out
           else eval_dir / "runs" / f"{a.label}-{time.strftime('%Y%m%d-%H%M')}")
    out.mkdir(parents=True, exist_ok=True)
    for f in ("agent_stream.jsonl", "turns.json", "summary.json", "grading.json"):
        (out / f).unlink(missing_ok=True)
    proj, cwd = setup(scn, out)
    env = {**ENV, **({"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1"} if a.isolate else {})}
    extra = mcp_args(out, a.isolate)
    old_root = scn["source"]["project"].rstrip("/")

    todo = [t for t in scn["turns"] if t.get("replay")][: a.max_turns or None]
    sid = str(uuid.uuid4())
    turns, history, stop = [], [], "finished"
    t_start = time.time()
    for i, t in enumerate(todo, 1):
        msg = t["prompt"]
        if mode == "simulated" and i > 1:
            msg = sim_user(scn, a, t["prompt"], history, turns[-1]["assistant"], i == len(todo))
        if old_root and old_root != str(cwd):
            msg = msg.replace(old_root, str(cwd))
        rec = agent_turn(cwd, sid, msg, i == 1, a, extra, out / "agent_stream.jsonl", env)
        commit(proj, f"turn {i}")
        changed = sh(["git", "show", "--stat", "--format=", "HEAD"], proj).stdout.strip()
        names = sh(["git", "show", "--name-only", "--format=", "HEAD", "--", "."], cwd).stdout.split()
        sub = scn["setup"].get("subdir") or ""
        files = [n[len(sub) + 1:] if sub and n.startswith(sub + "/") else n for n in names if not sub or n.startswith(sub + "/")]
        rec = {"turn": i, "orig_turn": t["orig_turn"], "user": msg, **rec, "docs_changed": changed,
               "files_changed": files, "stage": None}
        turns.append(rec)
        history.append(f"USER: {msg[:1500]}\nASSISTANT: {rec['assistant'][:1500]}")
        (out / "turns.json").write_text(json.dumps(turns, indent=1))
        last_line = changed.splitlines()[-1] if changed else "-"
        print(f"[{scn['id']}] turn {i}/{len(todo)} ({t['orig_turn']}) {rec['seconds']:.0f}s "
              f"skills={[s for s in rec['skills'] if s]} changed={last_line}", flush=True)
        if rec["assistant"].startswith("[agent error"):
            stop = "agent error"
            break
        if (rec["usage"].get("cost_usd") or 0) > a.cost_cap:
            stop = f"cost cap {a.cost_cap} USD"
            break
    summary = {"trajectory": scn["id"], "mode": mode, "turns": len(turns), "of": len(todo), "session": sid,
               "total_seconds": round(time.time() - t_start, 1),
               "agent_cost_usd": round(max([(x["usage"].get("cost_usd") or 0) for x in turns] or [0]), 3),
               "stop_reason": stop, "agent_model": a.model or "(default)",
               "user_model": a.user_model if mode == "simulated" else None}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary), flush=True)

    # Draw, grade, compare. The transcript is the agent session's, under ~/.claude/projects/.
    hits = sorted(trace.PROJECTS.glob(f"*/{sid}.jsonl"))
    if not hits:
        print(f"replay: no transcript for session {sid}; nothing to draw", file=sys.stderr)
        return 1
    ws = out / "flow"
    ws.mkdir(exist_ok=True)
    prev, cum = 0.0, []
    for x in turns:
        c = x["usage"].get("cost_usd")
        cum.append({"turn": x["turn"], "stage": x["orig_turn"], "seconds": x["seconds"],
                    "cost_usd": round(c - prev, 4) if c is not None else None,
                    "files_changed": x["files_changed"]})
        prev = c if c is not None else prev
    (ws / "eval.json").write_text(json.dumps({"iteration": a.label, "trajectory": scn["id"], "run": str(out),
                                              "summary": summary, "turns": cum,
                                              "compare": [{"label": "compare with the original",
                                                           "href": "../compare.html"}]}, indent=1))
    trace.build(hits[0], scn["source"].get("plugin"), ws, quiet=True)
    cut = ["--upto", str(len(todo))] if a.max_turns and stop == "finished" else []
    subprocess.run([sys.executable, str(HERE / "check.py"), str(eval_dir), str(ws), "--write",
                    "--grading", str(out / "grading.json"), "--label", a.label, *cut])
    orig = Path(scn["source"]["workspace"])
    if not (orig / "index.json").exists():
        trace.build(Path(scn["source"]["transcript"]), scn["source"].get("plugin"), orig, quiet=True)
    if not (orig / "eval.json").exists():
        subprocess.run([sys.executable, str(HERE / "check.py"), str(eval_dir), str(orig), "--write",
                        "--label", "original"], stdout=subprocess.DEVNULL)
    page = compare.write([f"original={orig}", f"{a.label}={ws}"], out / "compare.html",
                         turns=len(turns) if cut else None)
    print(f"replay: {ws / 'flow.html'}\nreplay: {page}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
