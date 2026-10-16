#!/usr/bin/env python3
"""Multi-turn trajectory driver for the dev-team2 planning skills, idea through build-setup.

An agent session (claude -p, resumed each turn) works in a fresh project dir with the whole dev-team2 plugin
loaded via --plugin-dir (skills, scripts/dt.py, hooks), staged into <out>/plugin/. A simulated user (separate
claude -p, no tools) answers questions, approves drafts, and — in incremental mode — reveals the next stage
only after the current one has been planned through its build plan.

Project skill stubs (scenarios.json `project_skills`) are installed in the project's .claude/skills/. Reference files
(scenarios.json `references`, from references/<project>/) are copied into the project's references/ when the stage
they serve is revealed (all of them up front in all-at-once mode), and the user's message says they were added.

After every turn the whole project is git-committed ("turn N") so doc evolution, and any code written during
planning, can be diffed.

Usage: driver.py <trajectory-id> <out-dir>

Env: PLUGIN_SRC / SKILLS_SRC (see plugin.py), CLAUDE_BIN (default: claude; fake_claude.py for a no-cost
loop test), AGENT_MODEL, USER_MODEL, COST_CAP_USD (stop once the agent session has cost this much; default
150), MAX_TURNS (override the scenario's turn budget, e.g. 1 for a smoke run), PERMISSION_PROMPTS=0 (don't
answer the oracle guard's "ask" prompts; see permission_mcp.py). Both sessions load project/local settings
only, no CLAUDE.md files and no MCP servers but the eval's own, so the host's user-level instructions, skills,
plugins and MCP servers don't leak into the trajectory.

Agent frontmatter hooks (the .claude/agents/*.md files build-setup writes) don't fire in a headless run in an
untrusted folder (checked live: skipped silently) unless the agents are passed with --agents or installed
user-level; planning never runs those agents, so this harness doesn't need them.
"""
import json, os, re, subprocess, sys, time, uuid, shutil, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dtrun, plugin  # noqa: E402

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
ISOLATE = ["--setting-sources", "project,local"]
AGENT_MODEL = os.environ.get("AGENT_MODEL", "claude-opus-5-5")
USER_MODEL = os.environ.get("USER_MODEL", "sonnet")
COST_CAP = float(os.environ.get("COST_CAP_USD", "150"))
MAX_TURNS = int(os.environ["MAX_TURNS"]) if os.environ.get("MAX_TURNS") else None
PERMISSION_PROMPTS = os.environ.get("PERMISSION_PROMPTS", "1") != "0"

STRIP_ENV = ["CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_REMOTE_SESSION_ID", "CLAUDE_CODE_TEE_SDK_STDOUT",
             "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_DIAGNOSTICS_FILE",
             "CLAUDECODE", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR"]
ENV = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
ENV["CLAUDE_CODE_DISABLE_CLAUDE_MDS"] = "1"  # --setting-sources alone still loads the host's ~/.claude/CLAUDE.md
DRAFT = ("Draft", "Proposed")
# The last layer of a stage may still be Draft when the user approves it and moves on in the same message.
LAST_LAYER = re.compile(r"^(tasks/plan\.md|tasks/queued/.*|CONSTRAINTS\.md)$")
CACHE_DIRS = [".venv/", "__pycache__/", "*.py[cod]", ".pytest_cache/", ".mypy_cache/", ".ruff_cache/",
              ".hypothesis/", ".import_linter_cache/", ".coverage", "node_modules/", ".claude/.stop_attempts_*"]


def sh(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True, **kw)


def commit(proj, msg):
    sh(["git", "add", "-A"], proj)
    sh(["git", "-c", "user.email=e@e", "-c", "user.name=eval", "commit", "-q", "--allow-empty", "--no-verify", "-m", msg], proj)


def snapshot(proj, dt):
    """Doc statuses (from dt's parser) plus derived roadmap rows."""
    facts = dtrun.probe(proj, dt)
    lines = []
    for rel, st in facts["docs"].items():
        if rel.endswith(("todo.md", "AGENTS.md", "CLAUDE.md", "roadmap.md")):
            continue
        words = len((proj / rel).read_text(errors="ignore").split())
        lines.append(f"{rel}: {st or 'unknown'} ({words} words)")
    for r in facts["roadmap"]:
        lines.append(f"roadmap {r['id']} {r['name']}: {r['derived']}")
    return facts, "\n".join(lines) or "(no docs yet)"


def readiness(facts, stage_no, mode):
    """Why the user can't move on yet ([] = may move on). Lenient by design: statuses only; the sim user and
    the grader judge the content. The current stage's last layer (plan / queued plan / CONSTRAINTS) may still
    be Draft, since the approving message is the one that moves on."""
    docs = facts["docs"]
    why = [f"{rel} is {st}" for rel, st in docs.items() if st in DRAFT and not LAST_LAYER.match(rel)]
    why += [f"{rel} not yet specced" for rel, st in docs.items() if rel.startswith("docs/ideas/") and st in ("Draft", "Accepted")]
    if not any(p["dev_team"] and p["kind"] == "plan" for p in facts["plans"]):
        why.append("no build plan yet")
    if "CONSTRAINTS.md" not in docs:
        why.append("no CONSTRAINTS.md yet (build setup)")
    if mode == "incremental" and len(facts["roadmap"]) < stage_no:
        why.append(f"roadmap has {len(facts['roadmap'])} rows for {stage_no} stages")
    return why


def all_approved(facts):
    return not any(st in DRAFT for st in facts["docs"].values())


def mcp_args(out):
    """--mcp-config for the eval's own permission-prompt server only (--strict-mcp-config keeps the host's out)."""
    cfg = {"mcpServers": {}}
    if PERMISSION_PROMPTS:
        cfg["mcpServers"]["evalperm"] = {"command": sys.executable, "args": [str(HERE / "permission_mcp.py")],
                                         "env": {"EVALPERM_LOG": str(out / "permission_prompts.jsonl")}}
    (out / "mcp.json").write_text(json.dumps(cfg, indent=1))
    args = ["--mcp-config", str(out / "mcp.json"), "--strict-mcp-config"]
    return args + (["--permission-prompt-tool", "mcp__evalperm__approve"] if PERMISSION_PROMPTS else [])


def agent_turn(proj, sid, msg, first, log_path, plugin_root, extra):
    # --include-hook-events: without it the stream carries only SessionStart and Stop hook events.
    cmd = [CLAUDE_BIN, "-p", msg, "--model", AGENT_MODEL, "--output-format", "stream-json", "--verbose",
           "--include-hook-events", "--permission-mode", "bypassPermissions", "--disallowedTools", "AskUserQuestion",
           "--plugin-dir", str(plugin_root), *extra, *ISOLATE]
    cmd += ["--session-id", sid] if first else ["--resume", sid]
    t0 = time.time()
    r = sh(cmd, proj, timeout=1800)
    dt = time.time() - t0
    with open(log_path, "a") as f:
        f.write(r.stdout)
    result, usage, tools, skills, errors, hooks, init, agents = "", {}, [], [], [], 0, {}, []
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init" and not init:
            # What the session actually loaded: proves the plugin, its skills and the permission server are live.
            init = {k: d.get(k) for k in ("plugins", "skills", "mcp_servers", "slash_commands") if k in d}
        if d.get("type") == "system" and "hook" in str(d.get("subtype", "")):
            hooks += 1
        if d.get("type") == "assistant":
            for c in d["message"].get("content", []):
                if c.get("type") == "tool_use":
                    tools.append(c["name"])
                    if c["name"] == "Skill":
                        skills.append(dtrun.skill_name(c["input"].get("skill")))
                    if c["name"] in ("Agent", "Task") and not d.get("parent_tool_use_id"):
                        # Top-level subagent launches (reference-intake sends one per file); graded per file name.
                        inp = c.get("input") or {}
                        agents.append({"subagent_type": inp.get("subagent_type"), "description": inp.get("description"),
                                       "prompt": (inp.get("prompt") or "")[:4000]})
        if d.get("type") == "user":
            for c in (d.get("message") or {}).get("content", []) or []:
                if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                    txt = c.get("content")
                    txt = txt if isinstance(txt, str) else json.dumps(txt)
                    errors.append(txt[:300])
        if d.get("type") == "result":
            result = d.get("result", "")
            usage = {"cost_usd": d.get("total_cost_usd"), "duration_ms": d.get("duration_ms"),
                     "usage": d.get("usage"), "num_turns": d.get("num_turns")}
    if not result and r.returncode != 0:
        result = f"[agent error rc={r.returncode}] {r.stderr[-500:]}"
    return result, usage, tools, skills, dt, errors, hooks, init, agents


PLANNING_CHAIN = """For each stage the assistant takes you through several planning documents, one at a time, each needing your approval: the idea/brief, the spec, the architecture, the pipelines (the workflows you will run and the planned file layout), optionally a test plan with golden test cases, and the build plan (the tasks for that milestone). Before the first build it also sets up the build tooling and quality bar (CONSTRAINTS.md, checks, agent roles); approve that too."""


def sim_user(scn, traj, revealed, next_stage, history_tail, agent_msg, status, refs):
    proj = scn["projects"][traj["project"]]
    mode = traj["mode"]
    stage_txt = "\n".join(f"- {s['reveal']}" for s in revealed)
    if mode == "incremental":
        nxt = (f"NEXT STAGE (not yet told to the assistant): {next_stage['reveal']}" if next_stage
               else "There is no next stage; this was the last one.")
        mode_rules = f"""You are planning this project ONE STAGE AT A TIME. Stages revealed so far:
{stage_txt}
{nxt}
Rules: Only talk about revealed stages. If asked about plans beyond them, say you're focusing on the current stage for now and haven't decided what comes next (do not hint at future stages).
{PLANNING_CHAIN}
A stage is fully planned when its build plan has been written and you approved it (for the first stage, the build setup / quality bar too). A later stage's build plan may be queued behind the current milestone because nothing is built yet; that's fine.
When the current stage is fully planned (its build plan was just presented for approval, or approved, and nothing else is pending) and there is a next stage, set action to "next_stage" and write a message that approves what is pending and then introduces the next stage as a new idea for this same project, in your own words (2-4 sentences, include its key content).
When the last stage is fully planned, set action to "finish"."""
    else:
        mode_rules = f"""You told the assistant ALL goals up front in your first message:
{stage_txt}
{PLANNING_CHAIN}
With everything known up front, expect all stages to be specced, designed and given pipelines, but a detailed build plan only for the first milestone. When the build setup / quality bar has been presented and you approved it, set action to "finish"."""
    refs_txt = (f"Reference files you have put in references/ so far: {', '.join(refs)}\n" if refs else "")
    prompt = f"""{scn['persona']}

PROJECT FACTS (your ground truth; only use facts relevant to revealed stages):
{chr(10).join('- ' + f for f in proj['facts'])}

{mode_rules}

Current document statuses on disk (roadmap lines show each milestone's derived status):
{status}
{refs_txt}
Recent conversation (oldest first):
{history_tail}

ASSISTANT'S LATEST MESSAGE:
<<<
{agent_msg[-9000:]}
>>>

Decide your reply. If the assistant asked questions, answer them all briefly and consistently with your facts. If it presented a draft for review, approve it explicitly (or request one specific fix if it contradicts your facts). If it offers golden test cases or a test plan, say yes. If it asks which stage or milestone a reference file serves, or which skills to route to a stage, answer from your facts. If it offers to commit approved documents, say yes. If it asks you to choose options or defaults (for example for tooling), take its recommendation. If it is waiting with nothing to answer, tell it to continue to the next planning step. Never instruct it which skill to use, and never write code, documents or tests yourself. Planning ends at an approved build setup: never ask it to write code or tests or to start building, and if it offers to start building, say planning is done for now. When you approve something and also introduce the next stage, put the approval first in the same message ("Approved. Next idea: ...").
Return ONLY a JSON object: {{"action": "reply" | "next_stage" | "finish", "message": "<what you say to the assistant>"}}"""
    r = sh([CLAUDE_BIN, "-p", prompt, "--model", USER_MODEL, "--tools", "", "--output-format", "json",
            "--no-session-persistence", *ISOLATE], HERE, timeout=600)
    try:
        txt = json.loads(r.stdout)["result"]
        m = re.search(r"\{.*\}", txt, re.S)
        return json.loads(m.group(0))
    except Exception:
        return {"action": "reply", "message": "Looks good, approved. Please continue."}


def opening(scn, traj):
    proj = scn["projects"][traj["project"]]
    st = proj["stages"]
    if traj["project"] == "rl":
        intro = ("I want to start a small ML project: an RL lab of little 2D environments where agents learn a "
                 "concept through reinforcement learning, so I can learn RL by building. Let's refine the idea and "
                 "plan it until it's ready to build.")
    else:
        intro = ("I want to start a personal quant research platform for market research on US equities, built in stages. "
                 "Let's refine the idea and plan it until it's ready to build.")
    if traj["mode"] == "incremental":
        return f"{intro}\n\nI'm starting with just the first piece: {st[0]['reveal']}", 1
    goals = "\n".join(f"{i+1}. {s['reveal']}" for i, s in enumerate(st))
    return f"{intro}\n\nHere is everything I eventually want it to do:\n{goals}", len(st)


def add_references(proj, project, stage_names):
    """Copy the reference files for these stages into <proj>/references/; returns the file names copied."""
    names = [f for s in stage_names for f in project.get("references", {}).get(s, [])]
    for f in names:
        (proj / "references").mkdir(exist_ok=True)
        shutil.copy(HERE / "references" / project["id"] / f, proj / "references" / f)
    return names


def refs_note(names):
    return f"\n\nI've put my reference code for this in references/: {', '.join(names)}." if names else ""


def setup_project(out, project, ref_stages=()):
    """Fresh project dir plus the staged plugin, the project's skill stubs and the opening reference files;
    returns (project, plugin root, reference files copied)."""
    proj = out / "project"
    if proj.exists():
        shutil.rmtree(proj)
    root = plugin.stage(out / "plugin")
    probs = plugin.check(root)
    if probs:
        sys.exit("plugin staging failed:\n" + "\n".join(probs))
    # Project skills, as the user would have them (stubs: planning only routes them, never runs them).
    for name, stub in project.get("project_skills", {"null-hypothesis-testing": "stub_null_hypothesis_SKILL.md"}).items():
        (proj / ".claude" / "skills" / name).mkdir(parents=True)
        shutil.copy(HERE / stub, proj / ".claude" / "skills" / name / "SKILL.md")
    refs = add_references(proj, project, ref_stages)
    if os.environ.get("SKILLS_SRC"):
        # Older skill snapshots call `skills/<name>/scripts/...` from the project root; keep those paths resolving.
        os.symlink(root / "skills", proj / "skills")
    sh(["git", "init", "-q"], proj)
    # build-setup runs `check.sh gate` once, which creates a venv and tool caches; keep them out of the
    # per-turn commits without putting a .gitignore where the agent would see it.
    (proj / ".git" / "info" / "exclude").write_text("\n".join(CACHE_DIRS) + "\n")
    commit(proj, "turn 0")
    return proj, root, refs


def main():
    tid, out = sys.argv[1], pathlib.Path(sys.argv[2]).resolve()
    scn = json.loads((HERE / "scenarios.json").read_text())
    traj = next(t for t in scn["trajectories"] if t["id"] == tid)
    project = dict(scn["projects"][traj["project"]], id=traj["project"])
    stages = project["stages"]
    out.mkdir(parents=True, exist_ok=True)
    msg, n_revealed = opening(scn, traj)
    proj, plugin_root, refs = setup_project(out, project, [s["name"] for s in stages[:n_revealed]])
    msg += refs_note(refs)
    dt = plugin_root / "scripts" / "dt.py"
    extra = mcp_args(out)

    sid = str(uuid.uuid4())
    turns, history = [], []
    stage_log = [{"turn": 1, "stage": stages[0]["name"] if traj["mode"] == "incremental" else "all"}]
    t_start = time.time()
    closing, stop_reason = False, "max_turns"
    for t in range(1, (MAX_TURNS or traj["max_turns"]) + 1):
        reply, usage, tools, skills, dt_s, errors, hooks, init, agents = agent_turn(
            proj, sid, msg, t == 1, out / "agent_stream.jsonl", plugin_root, extra)
        commit(proj, f"turn {t}")
        changed = sh(["git", "show", "--stat", "--format=", "HEAD"], proj).stdout.strip()
        facts, status = snapshot(proj, dt)
        rec = {"turn": t, "user": msg, "assistant": reply, "skills": skills, "tools": tools,
               "seconds": round(dt_s, 1), "usage": usage, "docs_changed": changed, "status": status,
               "stage": stage_log[-1]["stage"], "tool_errors": errors, "hook_events": hooks, "agents": agents}
        if t == 1:
            rec["session_init"] = init
            own = [s for s in json.dumps(init.get("skills") or init.get("slash_commands") or []).split('"') if "pipeline-design" in s]
            if init and not own:
                print(f"[{tid}] WARNING: session init lists no dev-team2 skills; is the plugin loading? {json.dumps(init)[:400]}", flush=True)
        turns.append(rec)
        history.append(f"USER: {msg[:1500]}\nASSISTANT: {reply[:1500]}")
        (out / "turns.json").write_text(json.dumps(turns, indent=1))
        print(f"[{tid}] turn {t} stage={rec['stage']} {dt_s:.0f}s skills={skills} changed={changed.splitlines()[-1] if changed else '-'}", flush=True)

        if closing:
            turns[-1]["sim_user_final"] = "(closing approval delivered)"
            (out / "turns.json").write_text(json.dumps(turns, indent=1))
            stop_reason = "finished"
            break
        if (usage.get("cost_usd") or 0) > COST_CAP:
            stop_reason = f"cost cap {COST_CAP} USD"
            break
        revealed = stages[:n_revealed]
        nxt = stages[n_revealed] if traj["mode"] == "incremental" and n_revealed < len(stages) else None
        u = sim_user(scn, traj, revealed, nxt, "\n\n".join(history[-4:-1]), reply, status, refs)
        why = readiness(facts, n_revealed, traj["mode"])
        rec["readiness"] = why
        if u.get("action") in ("finish", "next_stage") and why:
            u["action"] = "reply"
        if u.get("action") == "finish":
            if all_approved(facts):
                turns[-1]["sim_user_final"] = u.get("message")
                stop_reason = "finished"
                break
            # Send the closing approval so the agent can mark the last doc Approved; stop after that turn.
            closing = True
            u["action"] = "reply"
        new_refs = []
        if u.get("action") == "next_stage" and nxt:
            n_revealed += 1
            stage_log.append({"turn": t + 1, "stage": nxt["name"]})
            new_refs = add_references(proj, project, [nxt["name"]])
            refs += new_refs
        msg = (u.get("message") or "Approved. Continue.") + refs_note(new_refs)
        (out / "turns.json").write_text(json.dumps(turns, indent=1))
    summary = {"trajectory": tid, "turns": len(turns), "stages_reached": n_revealed, "stage_log": stage_log,
               "references": refs,
               "total_seconds": round(time.time() - t_start, 1),
               # total_cost_usd is cumulative over a resumed session, so the last turn's value is the run's cost.
               "agent_cost_usd": round(max([(x["usage"].get("cost_usd") or 0) for x in turns] or [0]), 3),
               "agent_output_tokens": sum(((x["usage"].get("usage") or {}).get("output_tokens") or 0) for x in turns),
               "finished": any("sim_user_final" in x for x in turns), "stop_reason": stop_reason,
               "agent_model": AGENT_MODEL, "user_model": USER_MODEL}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    (out / "doc_history.txt").write_text(
        sh(["git", "log", "--reverse", "-p", "--format=========== %s", "--", "docs", "tasks", "CONSTRAINTS.md"], proj).stdout)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
