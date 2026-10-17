#!/usr/bin/env python3
"""Build-eval driver (interface-first-design.md §9.2–§9.3): build one fixed project in one arm.

A fresh copy of the target fixture at "planning done" (docs, CONSTRAINTS.md, agents, checks) gets the arm's
plan variant (`plan-spine/` or `plan-interface/`) as tasks/. The whole dev-team plugin is staged into
<out>/plugin/ and loaded with --plugin-dir, as driver.py does; the project's agents (tester, implementer,
reviewer, re-rendered from the staged build-setup templates, plus the fixture's check and merge agents) are
passed with --agents, so their hooks fire without a trust prompt (build-phase-notes §4). The orchestrator
session (claude -p, resumed each turn) gets the common build rules and the arm's prompt from scenarios.json;
parallel arms write one workflow per checkpoint segment (CLAUDE_CODE_WORKFLOWS=1), serial arms run with
background tasks off. Between turns a deterministic build persona answers: it approves a checkpoint,
refuses any oracle edit, says yes to a contract change through Revise, and otherwise says continue
(PRESSURE=1 swaps in the fixture's pressure turns). evalperm denies oracle writes (EVALPERM_POLICY=
deny-oracle). The project is committed after every turn (`turn N`); agents commit their own work.

The run ends when todo.md is all ticked, at the turn budget, at the cost cap, or after STALL_LIMIT turns
with no new tick. Then it draws the flow (runviz.py --run; plan map when planexport exists), grades
(grade_build.py) and redraws the flow with the checks.

Usage: build_driver.py <target> <arm> <out-dir>      e.g. build_driver.py minilab A3 /tmp/b/minilab-A3-r1/with_skill

Env: CLAUDE_BIN (fake_claude.py with FAKE_MODE=build for a no-cost loop), AGENT_MODEL, COST_CAP_USD
(default none), MAX_TURNS, TURN_TIMEOUT (seconds per turn, default 5400), PRESSURE=1, PLUGIN_SRC/SKILLS_SRC
(see plugin.py), REPLICATE (recorded in summary.json).
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import uuid

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver, plugin  # noqa: E402

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
AGENT_MODEL = os.environ.get("AGENT_MODEL", "claude-opus-5-5")
COST_CAP = float(os.environ.get("COST_CAP_USD") or "inf")
MAX_TURNS = int(os.environ["MAX_TURNS"]) if os.environ.get("MAX_TURNS") else None
TURN_TIMEOUT = int(os.environ.get("TURN_TIMEOUT", "5400"))
PRESSURE = os.environ.get("PRESSURE") == "1"
STALL_LIMIT = 3
SOURCE_GLOBS = '"packages/*/src/**"'
ORACLE_ASK = re.compile(r"(expected\.json|golden (case|fixture)|oracle)[^.?\n]*(change|update|edit|regenerat|fix)"
                        r"|(change|update|edit|regenerat|fix)[^.?\n]*(expected\.json|golden (case|fixture)|oracle)", re.I)
CONTRACT_ASK = re.compile(r"contract[- ]change|architecture-design|Revise|frozen (type|interface)", re.I)


def sh(cmd, cwd, env=None, timeout=None):
    return subprocess.run(cmd, cwd=cwd, env=env or driver.ENV, capture_output=True, text=True, timeout=timeout)


# ---- agents ---------------------------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """An agent file's YAML frontmatter (the subset build-setup writes: scalars, nested maps, lists of maps)
    and its body. PyYAML when installed, else this small reader."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    head, body = m.groups()
    try:
        import yaml  # type: ignore
        return yaml.safe_load(head) or {}, body
    except ImportError:
        pass
    lines = [l for l in head.splitlines() if l.strip() and not l.lstrip().startswith("#")]

    def scalar(v: str):
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            return v[1:-1] if v[0] == "'" else json.loads(v)
        return v

    def block(i: int, ind: int):
        if i < len(lines) and lines[i].lstrip().startswith("- ") and len(lines[i]) - len(lines[i].lstrip()) == ind:
            out = []
            while i < len(lines) and len(lines[i]) - len(lines[i].lstrip()) == ind and lines[i].lstrip().startswith("- "):
                rest = lines[i].lstrip()[2:]
                lines[i] = " " * (ind + 2) + rest
                item, i = block(i, ind + 2)
                out.append(item)
            return out, i
        out = {}
        while i < len(lines):
            cur = len(lines[i]) - len(lines[i].lstrip())
            if cur < ind:
                break
            k, _, v = lines[i].strip().partition(":")
            i += 1
            if v.strip():
                out[k] = scalar(v)
            else:
                nxt = len(lines[i]) - len(lines[i].lstrip()) if i < len(lines) else -1
                out[k], i = block(i, nxt) if nxt > cur or (nxt == cur and i < len(lines) and lines[i].lstrip().startswith("- ")) else ({}, i)
        return out, i

    return block(0, 0)[0], body


def agents_json(proj: pathlib.Path) -> dict:
    """--agents definitions from .claude/agents/*.md: description, prompt, tools, model, hooks."""
    out = {}
    for f in sorted((proj / ".claude" / "agents").glob("*.md")):
        fm, body = parse_frontmatter(f.read_text())
        name = fm.get("name") or f.stem
        d = {"description": fm.get("description", name), "prompt": body.strip()}
        if fm.get("tools"):
            d["tools"] = [t.strip() for t in str(fm["tools"]).split(",") if t.strip()]
        for k in ("model", "hooks"):
            if fm.get(k):
                d[k] = fm[k]
        out[name] = d
    return out


def refresh_from_plugin(proj: pathlib.Path, root: pathlib.Path) -> list[str]:
    """The plugin under test supplies the role prompts and hook scripts: re-render the fixture's tester,
    implementer and reviewer from the staged build-setup templates, and copy its hook scripts. A template
    with a placeholder this fixture can't fill keeps the fixture's copy (and is reported)."""
    tpl = root / "skills" / "build-setup" / "templates"
    notes = []
    for name in ("tester", "implementer", "reviewer"):
        src = tpl / ".claude" / "agents" / f"{name}.md"
        if not src.exists():
            continue
        text = src.read_text().replace("{{source_globs}}", SOURCE_GLOBS)
        if "{{" in text:
            notes.append(f"{name}.md: template has placeholders this fixture can't fill; kept the fixture's copy")
            continue
        (proj / ".claude" / "agents" / f"{name}.md").write_text(text)
    for f in sorted((tpl / "scripts" / "hooks").glob("*.sh")) if (tpl / "scripts" / "hooks").is_dir() else []:
        shutil.copy(f, proj / "scripts" / "hooks" / f.name)
    return notes


# ---- setup ----------------------------------------------------------------------------------------------

def setup(out: pathlib.Path, target: str, cfg: dict, arm: dict) -> tuple[pathlib.Path, pathlib.Path, list[str]]:
    fixture = HERE / cfg["fixture"]
    proj = out / "project"
    if proj.exists():
        shutil.rmtree(proj)
    shutil.copytree(fixture / "project", proj)
    shutil.copytree(fixture / cfg["plans"][arm["plan"]] / "tasks", proj / "tasks")
    root = plugin.stage(out / "plugin")
    probs = plugin.check(root)
    if probs:
        sys.exit("plugin staging failed:\n" + "\n".join(probs))
    notes = refresh_from_plugin(proj, root)
    sh(["git", "init", "-q", "-b", "main"], proj)
    (proj / ".git" / "info" / "exclude").write_text("\n".join(driver.CACHE_DIRS + [".dt/"]) + "\n")
    driver.commit(proj, "turn 0")
    base = sh(["git", "rev-parse", "HEAD"], proj).stdout.strip()
    plan = proj / "tasks" / "plan.md"
    plan.write_text(re.sub(r"\*\*Base:\*\* —", f"**Base:** {base[:7]}", plan.read_text(), count=1))
    driver.commit(proj, "turn 0: base")
    sh(["git", "update-ref", "refs/checks/base", "HEAD"], proj)
    return proj, root, notes


def mcp_args(out: pathlib.Path) -> list[str]:
    cfg = {"mcpServers": {"evalperm": {"command": sys.executable, "args": [str(HERE / "permission_mcp.py")],
                                       "env": {"EVALPERM_LOG": str(out / "permission_prompts.jsonl"),
                                               "EVALPERM_POLICY": "deny-oracle"}}}}
    (out / "mcp.json").write_text(json.dumps(cfg, indent=1))
    return ["--mcp-config", str(out / "mcp.json"), "--strict-mcp-config",
            "--permission-prompt-tool", "mcp__evalperm__approve"]


# ---- one orchestrator turn ------------------------------------------------------------------------------

def agent_turn(proj, sid, msg, first, out, plugin_root, extra, env):
    cmd = [CLAUDE_BIN, "-p", msg, "--model", AGENT_MODEL, "--output-format", "stream-json", "--verbose",
           "--include-hook-events", "--permission-mode", "bypassPermissions", "--disallowedTools", "AskUserQuestion",
           "--plugin-dir", str(plugin_root), *extra, *driver.ISOLATE]
    cmd += ["--session-id", sid] if first else ["--resume", sid]
    t0 = time.time()
    try:
        r = sh(cmd, proj, env=env, timeout=TURN_TIMEOUT)
        stdout, rc, err = r.stdout, r.returncode, r.stderr
    except subprocess.TimeoutExpired as e:
        stdout, rc, err = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), -1, "timeout"
    secs = time.time() - t0
    with open(out / "agent_stream.jsonl", "a") as f:
        f.write(stdout)
    rec = {"result": "", "usage": {}, "tools": [], "skills": [], "errors": [], "hooks": 0, "init": {},
           "agents": [], "workflows": []}
    for line in stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init" and not rec["init"]:
            rec["init"] = {k: d.get(k) for k in ("plugins", "skills", "mcp_servers", "agents", "slash_commands") if k in d}
        if d.get("type") == "system" and "hook" in str(d.get("subtype", "")):
            rec["hooks"] += 1
        if d.get("type") == "assistant":
            for c in d["message"].get("content", []):
                if c.get("type") != "tool_use":
                    continue
                rec["tools"].append(c["name"])
                inp = c.get("input") or {}
                if c["name"] == "Skill":
                    rec["skills"].append(str(inp.get("skill", "")).split(":")[-1])
                if c["name"] in ("Agent", "Task"):
                    rec["agents"].append({"subagent_type": inp.get("subagent_type"), "description": inp.get("description"),
                                          "isolation": inp.get("isolation"), "nested": bool(d.get("parent_tool_use_id")),
                                          "prompt": (inp.get("prompt") or "")[:2000]})
                if c["name"] == "Workflow":
                    rec["workflows"].append({"script_head": str(inp.get("script") or inp.get("name") or "")[:3000]})
        if d.get("type") == "user":
            for c in (d.get("message") or {}).get("content", []) or []:
                if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                    txt = c.get("content")
                    rec["errors"].append((txt if isinstance(txt, str) else json.dumps(txt))[:300])
        if d.get("type") == "result":
            rec["result"] = d.get("result", "")
            rec["usage"] = {"cost_usd": d.get("total_cost_usd"), "duration_ms": d.get("duration_ms"),
                            "usage": d.get("usage"), "num_turns": d.get("num_turns")}
    if not rec["result"] and rc != 0:
        rec["result"] = f"[agent error rc={rc}] {err[-500:]}"
    return rec, secs


# ---- the build persona ----------------------------------------------------------------------------------

def ticked(proj: pathlib.Path) -> tuple[set[str], list[str]]:
    todo = proj / "tasks" / "todo.md"
    text = todo.read_text() if todo.exists() else ""
    return set(re.findall(r"^- \[x\] (M\d+-T\d+)", text, re.M)), re.findall(r"^- \[ \] (M\d+-T\d+)", text, re.M)


def persona(reply: str, new_ticks: bool, approvals: int, scn: dict, pressure: list[dict]) -> tuple[str, str]:
    """(kind, message): the deterministic build persona's answer to the orchestrator's last message."""
    p = scn["build_persona"]
    asks = "?" in reply[-1500:]
    if ORACLE_ASK.search(reply) and asks:
        return "refuse_oracle", p["refuse_oracle"]
    if CONTRACT_ASK.search(reply) and asks:
        return "contract_change", p["contract_change"]
    if new_ticks or re.search(r"checkpoint", reply, re.I):
        due = [x for x in pressure if x["after_checkpoint"] == approvals + 1]
        if due:
            return f"pressure:{due[0]['id']}", due[0]["text"]
        return "approve", p["approve"]
    return "continue", p["continue"]


# ---- main -----------------------------------------------------------------------------------------------

def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__.split("\n\n")[-2])
    target, arm_id, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]).resolve()
    scn = json.loads((HERE / "scenarios.json").read_text())
    cfg, arm = scn["build_targets"][target], dict(scn["arms"][arm_id], id=arm_id)
    out.mkdir(parents=True, exist_ok=True)
    for stale in ("agent_stream.jsonl", "permission_prompts.jsonl"):
        (out / stale).unlink(missing_ok=True)
    proj, plugin_root, notes = setup(out, target, cfg, arm)
    for n in notes:
        print(f"[{target}/{arm_id}] note: {n}", flush=True)
    dt = plugin_root / "scripts" / "dt.py"
    agents = agents_json(proj)
    (out / "agents.json").write_text(json.dumps(agents, indent=1))
    extra = mcp_args(out) + ["--agents", json.dumps(agents)]
    env = dict(driver.ENV, CLAUDE_CODE_WORKFLOWS="1", BUILD_ARM=arm_id, BUILD_TARGET=target, **arm.get("env", {}))
    pressure = json.loads((HERE / cfg["fixture"] / "pressure.json").read_text())["turns"] if PRESSURE else []
    version = sh([CLAUDE_BIN, "--version"], HERE, env=env).stdout.strip()

    msg = "\n\n".join([scn["build_common_prompt"].format(dt=dt), arm["prompt"], scn["build_persona"]["start"]])
    sid = str(uuid.uuid4())
    turns, t_start, stop, stalled, approvals = [], time.time(), "max_turns", 0, 0
    done_before: set[str] = set()
    for t in range(1, (MAX_TURNS or cfg.get("max_turns", 12)) + 1):
        rec, secs = agent_turn(proj, sid, msg, t == 1, out, plugin_root, extra, env)
        driver.commit(proj, f"turn {t}")
        done, open_ = ticked(proj)
        new = done - done_before
        done_before = done
        changed = sh(["git", "show", "--stat", "--format=", "HEAD"], proj).stdout.strip()
        turn = {"turn": t, "user": msg, "assistant": rec["result"], "skills": rec["skills"], "tools": rec["tools"],
                "seconds": round(secs, 1), "usage": rec["usage"], "docs_changed": changed, "tool_errors": rec["errors"],
                "hook_events": rec["hooks"], "agents": rec["agents"], "workflows": rec["workflows"],
                "ticked": sorted(done), "new_ticks": sorted(new), "open": open_,
                "persona": "start" if t == 1 else turns[-1]["persona_next"]}
        if t == 1:
            turn["session_init"] = rec["init"]
        print(f"[{target}/{arm_id}] turn {t} {secs:.0f}s ticked {len(done)}/{len(done) + len(open_)} "
              f"agents={len(rec['agents'])} workflows={len(rec['workflows'])}", flush=True)
        turns.append(turn)
        (out / "turns.json").write_text(json.dumps(turns, indent=1))
        if not open_ and done:
            stop = "finished"
            turn["persona_next"] = "finish"
            break
        if (rec["usage"].get("cost_usd") or 0) > COST_CAP:
            stop = f"cost cap {COST_CAP} USD"
            break
        if rec["result"].startswith("[agent error"):
            stop = "agent error"
            break
        stalled = 0 if new else stalled + 1
        if stalled >= STALL_LIMIT:
            stop = f"stalled: no task ticked in {STALL_LIMIT} turns"
            break
        kind, msg = persona(rec["result"], bool(new), approvals, scn, pressure)
        approvals += kind == "approve" or kind.startswith("pressure")
        turn["persona_next"] = kind
        (out / "turns.json").write_text(json.dumps(turns, indent=1))
    done, open_ = ticked(proj)
    summary = {"target": target, "arm": arm_id, "plan": arm["plan"], "dispatch": arm["dispatch"], "tdd": arm["tdd"],
               "replicate": os.environ.get("REPLICATE"), "turns": len(turns), "stop_reason": stop,
               "finished": stop == "finished", "ticked": len(done), "open": open_,
               "total_seconds": round(time.time() - t_start, 1),
               "agent_cost_usd": round(max([(x["usage"].get("cost_usd") or 0) for x in turns] or [0]), 3),
               "agent_output_tokens": sum(((x["usage"].get("usage") or {}).get("output_tokens") or 0) for x in turns),
               "agent_model": AGENT_MODEL, "claude_version": version, "pressure": PRESSURE,
               "fake": pathlib.Path(CLAUDE_BIN).name.startswith("fake_claude")}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary), flush=True)
    # Every run ends with its flow (and plan map, once planexport exists), graded, then redrawn with the checks.
    for step in (["runviz.py", "--run", str(out)], ["grade_build.py", str(out), "--quiet"], ["runviz.py", "--run", str(out)]):
        try:
            r = subprocess.run([sys.executable, str(HERE / step[0]), *step[1:]], timeout=1200)
            if r.returncode:
                print(f"{step[0]}: exit {r.returncode} (the run itself is fine)", flush=True)
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"{step[0]}: {e} (the run itself is fine)", flush=True)


if __name__ == "__main__":
    main()
