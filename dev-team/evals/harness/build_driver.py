#!/usr/bin/env python3
"""Build-eval driver (interface-first-design.md §9.2–§9.3, build-phase.md §15): build one fixed project in one arm.

The live-build method (design/evidence/2026-10-17-live-build.md). The dev-team plugin is staged into <out>/plugin/
and the project made from the target fixture with the staged plugin's build-setup templates (minilab's
scripts/make_live.py: the real bar, the arm's plan variant, `dt base`), so the plugin under test supplies the bar,
the agents and dt. One headless session, resumed at each stop:
`claude -p --plugin-dir <plugin> --add-dir <plugin> --agents <the rendered .claude/agents/*.md as JSON, hooks
included, every model pinned to AGENT_MODEL> --allowedTools <the rendered .claude/settings.json allow rules>
--permission-mode acceptEdits --output-format stream-json`. A turn's outcome is its LAST result event (the CLI
resumes the main agent once per background-agent completion, one result event each).

A scripted persona (no model) answers each stop from the project's state (`dt build status`, the contract docs,
the plan), not from the driver's words: a CONTRACT-CHANGE gets a yes, then architecture-design Revise, then
build-planning Replan, then the go (`dt build go`); a TEST-WRONG gets `--test-stands`; a Critical finding is
resolved; a blocked half is retried once; the exit is approved with no fix tasks for the Important findings
(counted) and no merge, so build/M1 is graded. PRESSURE=1 adds the fixture's pressure turns at the stops. After
every turn the tree at HEAD is chained as a `turn N` commit on refs/eval/turns (never on build/M1), for the plan map.

The run ends at the exit, at the turn budget, or after STALL_LIMIT turns in which dt-build/log.jsonl gained
nothing. Then it draws the flow and plan map (runviz.py --run), grades (grade_build.py), and redraws with the checks.

Usage: build_driver.py <target> <arm> <out-dir>      e.g. build_driver.py minilab A3 /tmp/b/minilab-A3-r1/with_skill

Env: CLAUDE_BIN (fake_claude.py with FAKE_MODE=build for a no-cost loop), AGENT_MODEL (default claude-opus-5-5,
every agent), MAX_TURNS, TURN_TIMEOUT (seconds per turn, default 5400), PRESSURE=1, PLUGIN_SRC/SKILLS_SRC (see
plugin.py), REPLICATE (recorded in summary.json). No cost cap.
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
MAX_TURNS = int(os.environ["MAX_TURNS"]) if os.environ.get("MAX_TURNS") else None
TURN_TIMEOUT = int(os.environ.get("TURN_TIMEOUT", "5400"))
PRESSURE = os.environ.get("PRESSURE") == "1"
STALL_LIMIT = 3
TURNS_REF = "refs/eval/turns"
ORACLE_ASK = re.compile(r"(expected\.json|golden (case|fixture)|oracle)[^.?\n]*(change|update|edit|regenerat|fix)"
                        r"|(change|update|edit|regenerat|fix)[^.?\n]*(expected\.json|golden (case|fixture)|oracle)", re.I)
CONTRACT_ASK = re.compile(r"contract[- ]change|CONTRACT-CHANGE|architecture-design|frozen (type|interface)", re.I)


def sh(cmd, cwd, env=None, timeout=None, input=None):
    return subprocess.run(cmd, cwd=cwd, env=env or driver.ENV, capture_output=True, text=True, timeout=timeout,
                          input=input)


def load_make_live(cfg: dict):
    sys.path.insert(0, str(HERE / cfg["fixture"] / "scripts"))
    import make_live  # noqa: E402
    return make_live


# ---- agents and permissions -----------------------------------------------------------------------------

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
    lines = [ln for ln in head.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]

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
    """--agents definitions from the rendered .claude/agents/*.md: description, prompt, tools, hooks; every model
    pinned to AGENT_MODEL."""
    out = {}
    for f in sorted((proj / ".claude" / "agents").glob("*.md")):
        fm, body = parse_frontmatter(f.read_text())
        name = fm.get("name") or f.stem
        d = {"description": fm.get("description", name), "prompt": body.strip(), "model": AGENT_MODEL}
        if fm.get("tools"):
            d["tools"] = [t.strip() for t in str(fm["tools"]).split(",") if t.strip()]
        if fm.get("hooks"):
            d["hooks"] = fm["hooks"]
        out[name] = d
    return out


def allow_rules(proj: pathlib.Path, arm: dict) -> list[str]:
    """The rendered .claude/settings.json allow rules (they apply only in a trusted folder, so they are passed with
    --allowedTools), plus the arm's own."""
    try:
        rules = json.loads((proj / ".claude" / "settings.json").read_text())["permissions"]["allow"]
    except (OSError, ValueError, KeyError):
        rules = []
    return list(dict.fromkeys(rules + arm.get("extra_allow", [])))


# ---- setup ----------------------------------------------------------------------------------------------

def setup(out: pathlib.Path, cfg: dict, arm: dict) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    proj = out / "project"
    if proj.exists():
        shutil.rmtree(proj)
    root = plugin.stage(out / "plugin")
    probs = plugin.check(root)
    if probs:
        sys.exit("plugin staging failed:\n" + "\n".join(probs))
    dt = load_make_live(cfg).make(proj, arm["plan"], root)
    turn_commit(proj, 0)
    return proj, root, dt


def turn_commit(proj: pathlib.Path, n: int) -> None:
    """HEAD's tree as `turn N` on refs/eval/turns, chained on the last one; build/M1 is never touched."""
    prev = sh(["git", "rev-parse", "-q", "--verify", TURNS_REF], proj).stdout.strip()
    tree = sh(["git", "rev-parse", "HEAD^{tree}"], proj).stdout.strip()
    env = dict(driver.ENV, GIT_AUTHOR_NAME="eval", GIT_AUTHOR_EMAIL="e@e", GIT_COMMITTER_NAME="eval",
               GIT_COMMITTER_EMAIL="e@e")
    c = sh(["git", "commit-tree", tree, *(["-p", prev] if prev else []), "-m", f"turn {n}"], proj, env=env).stdout.strip()
    if c:
        sh(["git", "update-ref", TURNS_REF, c], proj)


# ---- one driver turn ------------------------------------------------------------------------------------

def agent_turn(proj, sid, msg, first, out, extra, env):
    cmd = [CLAUDE_BIN, "-p", msg, "--model", AGENT_MODEL, "--output-format", "stream-json", "--verbose",
           "--include-hook-events", *extra, *driver.ISOLATE]
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
    rec = {"result": "", "usage": {}, "results": 0, "tools": [], "skills": [], "errors": [], "hooks": 0, "init": {},
           "agents": [], "workflows": [], "permission_denials": []}
    for line in stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init" and not rec["init"]:
            rec["init"] = {k: d.get(k) for k in ("plugins", "skills", "mcp_servers", "agents", "slash_commands",
                                                 "model", "claude_code_version") if k in d}
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
                                          "isolation": inp.get("isolation"), "background": inp.get("run_in_background"),
                                          "nested": bool(d.get("parent_tool_use_id")),
                                          "prompt": (inp.get("prompt") or "")[:400]})
                if c["name"] == "Workflow":
                    rec["workflows"].append({"script_head": str(inp.get("script") or inp.get("name") or "")[:3000]})
        if d.get("type") == "user":
            for c in (d.get("message") or {}).get("content", []) or []:
                if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                    txt = c.get("content")
                    rec["errors"].append((txt if isinstance(txt, str) else json.dumps(txt))[:300])
        if d.get("type") == "result":          # the last one is the turn's outcome
            rec["results"] += 1
            rec["result"] = d.get("result", "") or ""
            rec["usage"] = {"cost_usd": d.get("total_cost_usd"), "duration_ms": d.get("duration_ms"),
                            "usage": d.get("usage"), "num_turns": d.get("num_turns"), "is_error": d.get("is_error"),
                            "subtype": d.get("subtype")}
            rec["permission_denials"] += d.get("permission_denials") or []
    if not rec["result"] and rc != 0:
        rec["result"] = f"[agent error rc={rc}] {err[-500:]}"
    return rec, secs


# ---- the persona ----------------------------------------------------------------------------------------

class Persona:
    """Answers each stop from the project's state. `cc` follows one contract change: asked → revised → replanned →
    go recorded."""

    def __init__(self, proj: pathlib.Path, dt: pathlib.Path, scn: dict, arm: dict, pressure: list[dict]):
        self.proj, self.dt, self.p, self.arm, self.pressure = proj, dt, scn["build_persona"], arm, pressure
        self.cc_type: str | None = None
        self.retried: set[str] = set()
        self.resolved: set[str] = set()
        self.important = 0

    def status(self) -> dict:
        r = sh([sys.executable, str(self.dt), "--root", str(self.proj), "build", "status"], self.proj)
        try:
            return json.loads(r.stdout)
        except ValueError:
            return {}

    def git(self, *a) -> str:
        return sh(["git", *a], self.proj).stdout

    def contract_revised(self) -> bool:
        diff = self.git("diff", "main", "--", "docs/packages")       # committed on build/M1 or not
        return bool(re.search(r"^\+.*\S", diff, re.M)) and "contract.md" in diff

    def replanned(self) -> bool:
        ids = lambda text: set(re.findall(r"^### (M\d+-T\d+):", text, re.M))  # noqa: E731
        now = (self.proj / "tasks" / "plan.md").read_text()
        return bool(ids(now) - ids(self.git("show", "main:tasks/plan.md")))

    def answer(self, reply: str, st: dict) -> tuple[str, str]:
        """(kind, message), or ("finish", …) when the run ends with this answer."""
        p = self.p
        asks = "?" in reply[-1500:]
        if ORACLE_ASK.search(reply) and asks:
            return "refuse_oracle", p["refuse_oracle"]
        escalations = st.get("escalations") or []
        cc = [e for e in escalations if e.get("kind") == "CONTRACT-CHANGE"]
        if cc and self.cc_type is None:
            self.cc_type = cc[0].get("type") or "the contract"
        if self.cc_type is None and self.arm.get("dispatch") == "session" and CONTRACT_ASK.search(reply) and asks:
            self.cc_type = "the frozen type"
        if self.cc_type is not None:
            if not self.contract_revised():
                return "contract_change", p["contract_change"].format(type=self.cc_type)
            if not self.replanned():
                return "replan", p["replan"].format(type=self.cc_type)
            if self.arm.get("dispatch") != "session" and st.get("go_current") is False:
                return "go", p["go"]
        tw = [e for e in escalations if e.get("kind") == "TEST-WRONG"]
        if tw:
            return "test_wrong", p["test_wrong"].format(task=tw[0]["task"])
        crit = [f for r in st.get("reviews") or [] for f in r.get("critical_open") or []]
        if crit:
            return "critical", p["critical"].format(finding=crit[0])
        blocked = [b for b in st.get("blocked") or [] if b["id"] not in self.retried]
        if blocked:
            self.retried.add(blocked[0]["id"])
            return "retry", (f"Retry {blocked[0]['id']} once: record `dt build resolve {blocked[0]['id']} --note "
                             f"\"retry once\"` and continue.")
        done = st.get("all_landed") and st.get("next_checkpoint") is None
        if self.arm.get("dispatch") == "session":
            done = bool(st.get("all_landed"))
        if done:
            self.important = (st.get("findings") or {}).get("Important", 0)
            return "finish", p["exit"]
        due = [x for x in self.pressure if x["after_checkpoint"] <= len(st.get("reviews") or [])]
        if due:
            self.pressure.remove(due[0])
            return f"pressure:{due[0]['id']}", due[0]["text"]
        return "continue", p["continue"]


# ---- main -----------------------------------------------------------------------------------------------

def progress(proj: pathlib.Path) -> int:
    log = proj / ".git" / "dt-build" / "log.jsonl"
    commits = sh(["git", "rev-list", "--count", "--all"], proj).stdout.strip()
    return (len(log.read_text().splitlines()) if log.exists() else 0) + int(commits or 0)


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__.split("\n\n")[-2])
    target, arm_id, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]).resolve()
    scn = json.loads((HERE / "scenarios.json").read_text())
    cfg, arm = scn["build_targets"][target], dict(scn["arms"][arm_id], id=arm_id)
    out.mkdir(parents=True, exist_ok=True)
    for stale in ("agent_stream.jsonl", "turns.json", "summary.json", "grading.json"):
        (out / stale).unlink(missing_ok=True)
    proj, plugin_root, dt = setup(out, cfg, arm)
    agents = agents_json(proj)
    (out / "agents.json").write_text(json.dumps(agents, indent=1))
    allowed = allow_rules(proj, arm)
    extra = ["--plugin-dir", str(plugin_root), "--add-dir", str(plugin_root), "--permission-mode", "acceptEdits",
             "--disallowedTools", "AskUserQuestion", *arm.get("disallow", [])]
    if arm.get("dispatch") != "session":
        extra += ["--agents", json.dumps(agents)]
    extra += ["--allowedTools", *allowed]
    env = dict(driver.ENV, BUILD_ARM=arm_id, BUILD_TARGET=target, **arm.get("env", {}))
    pressure = json.loads((HERE / cfg["fixture"] / "pressure.json").read_text())["turns"] if PRESSURE else []
    version = sh([CLAUDE_BIN, "--version"], HERE, env=env).stdout.strip()
    persona = Persona(proj, dt, scn, arm, pressure)

    msg = "\n\n".join(x for x in [scn["build_common_prompt"].format(dt=dt),
                                  arm["prompt"].format(cap=arm.get("cap", 6), dt=dt)] if x)
    sid = str(uuid.uuid4())
    turns, t_start, stop, stalled, kind = [], time.time(), "max_turns", 0, "start"
    before = progress(proj)
    print(f"[{target}/{arm_id}] {version}, model {AGENT_MODEL}, {len(allowed)} allow rules", flush=True)
    for t in range(1, (MAX_TURNS or cfg.get("max_turns", 12)) + 1):
        rec, secs = agent_turn(proj, sid, msg, t == 1, out, extra, env)
        turn_commit(proj, t)
        st = persona.status()
        now = progress(proj)
        turn = {"turn": t, "user": msg, "persona": kind, "assistant": rec["result"], "skills": rec["skills"],
                "tools": rec["tools"], "seconds": round(secs, 1), "usage": rec["usage"], "results": rec["results"],
                "tool_errors": rec["errors"], "hook_events": rec["hooks"], "agents": rec["agents"],
                "workflows": rec["workflows"], "permission_denials": rec["permission_denials"],
                "progress": st.get("progress"), "head": sh(["git", "rev-parse", "HEAD"], proj).stdout.strip()}
        if t == 1:
            turn["session_init"] = rec["init"]
        print(f"[{target}/{arm_id}] turn {t} {secs:.0f}s landed {st.get('progress')} agents={len(rec['agents'])} "
              f"results={rec['results']}", flush=True)
        turns.append(turn)
        (out / "turns.json").write_text(json.dumps(turns, indent=1))
        if rec["result"].startswith("[agent error"):
            stop = "agent error"
            break
        if kind == "finish":
            stop = "exit"
            break
        stalled = 0 if now > before else stalled + 1
        before = now
        if stalled >= STALL_LIMIT:
            stop = f"stalled: nothing new in dt-build or git for {STALL_LIMIT} turns"
            break
        kind, msg = persona.answer(rec["result"], st)
        turn["persona_next"] = kind
        (out / "turns.json").write_text(json.dumps(turns, indent=1))
    st = persona.status()
    costs = [(x["usage"].get("cost_usd") or 0) for x in turns]
    summary = {"target": target, "arm": arm_id, "plan": arm["plan"], "dispatch": arm["dispatch"], "tdd": arm["tdd"],
               "cap": arm.get("cap"), "replicate": os.environ.get("REPLICATE"), "turns": len(turns), "stop_reason": stop,
               "finished": stop == "exit", "progress": st.get("progress"),
               "total_seconds": round(time.time() - t_start, 1),
               "agent_cost_usd": round(sum(costs), 3), "turn_costs_usd": costs,
               "agent_output_tokens": sum(((x["usage"].get("usage") or {}).get("output_tokens") or 0) for x in turns),
               "important_findings": persona.important, "findings": st.get("findings"),
               "agent_model": AGENT_MODEL, "claude_version": version, "pressure": PRESSURE,
               "fake": pathlib.Path(CLAUDE_BIN).name.startswith("fake_claude")}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary), flush=True)
    for step in (["runviz.py", "--run", str(out)], ["grade_build.py", str(out), "--quiet"], ["runviz.py", "--run", str(out)]):
        try:
            r = subprocess.run([sys.executable, str(HERE / step[0]), *step[1:]], timeout=1800)
            if r.returncode:
                print(f"{step[0]}: exit {r.returncode} (the run itself is fine)", flush=True)
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"{step[0]}: {e} (the run itself is fine)", flush=True)


if __name__ == "__main__":
    main()
