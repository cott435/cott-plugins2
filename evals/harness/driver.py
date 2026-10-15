#!/usr/bin/env python3
"""Multi-turn trajectory driver for dev-team2 planning skills.

An agent session (claude -p, resumed each turn) works in a fresh project dir with the
dev-team2 skills installed under .claude/skills. A simulated user (separate claude -p,
no tools) answers questions, accepts drafts, and — in incremental mode — reveals the
next stage only after the current one has been fully planned.

After every turn the project's docs/ are git-committed so doc evolution can be diffed.

Usage: driver.py <trajectory-id> <out-dir>

Env: SKILLS_SRC (skills to install; default: this repo's skills/), CLAUDE_BIN (default: claude),
AGENT_MODEL, USER_MODEL. Both sessions load project/local settings only and no CLAUDE.md files, so the
host's user-level instructions, skills and plugins don't leak into the trajectory.
"""
import json, os, re, subprocess, sys, time, uuid, shutil, pathlib

HERE = pathlib.Path(__file__).resolve().parent
SKILLS_SRC = pathlib.Path(os.environ.get("SKILLS_SRC", HERE.parents[1] / "skills"))
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
ISOLATE = ["--setting-sources", "project,local"]
AGENT_MODEL = os.environ.get("AGENT_MODEL", "claude-opus-5-5")
USER_MODEL = os.environ.get("USER_MODEL", "sonnet")

STRIP_ENV = ["CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_REMOTE_SESSION_ID", "CLAUDE_CODE_TEE_SDK_STDOUT",
             "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_DIAGNOSTICS_FILE",
             "CLAUDECODE"]
ENV = {k: v for k, v in os.environ.items() if k not in STRIP_ENV}
ENV["CLAUDE_CODE_DISABLE_CLAUDE_MDS"] = "1"  # --setting-sources alone still loads the host's ~/.claude/CLAUDE.md


def sh(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True, **kw)


def doc_status(proj):
    out = []
    docs = proj / "docs"
    if not docs.exists():
        return "(no docs/ yet)"
    for p in sorted(docs.rglob("*.md")):
        txt = p.read_text(errors="ignore")
        m = re.search(r"\*\*Status:\*\*\s*([A-Za-z ]+?)(?:\s*·|\n|$)", txt)
        out.append(f"{p.relative_to(proj)}: {m.group(1).strip() if m else 'unknown'} ({len(txt.split())} words)")
    return "\n".join(out) or "(docs/ empty)"


def agent_turn(proj, sid, msg, first, log_path):
    cmd = [CLAUDE_BIN, "-p", msg, "--model", AGENT_MODEL, "--output-format", "stream-json", "--verbose",
           "--permission-mode", "bypassPermissions", "--disallowedTools", "AskUserQuestion", *ISOLATE]
    cmd += ["--session-id", sid] if first else ["--resume", sid]
    t0 = time.time()
    r = sh(cmd, proj, timeout=1800)
    dt = time.time() - t0
    with open(log_path, "a") as f:
        f.write(r.stdout)
    result, usage, tools, skills = "", {}, [], []
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "assistant":
            for c in d["message"].get("content", []):
                if c.get("type") == "tool_use":
                    tools.append(c["name"])
                    if c["name"] == "Skill":
                        skills.append(c["input"].get("skill"))
        if d.get("type") == "result":
            result = d.get("result", "")
            usage = {"cost_usd": d.get("total_cost_usd"), "duration_ms": d.get("duration_ms"),
                     "usage": d.get("usage"), "num_turns": d.get("num_turns")}
    if not result and r.returncode != 0:
        result = f"[agent error rc={r.returncode}] {r.stderr[-500:]}"
    return result, usage, tools, skills, dt


def sim_user(scn, traj, revealed, next_stage, history_tail, agent_msg, status):
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
A stage is fully planned when its idea/brief, the spec covering it, and the architecture covering it have all been written AND you have accepted/approved each.
When the current stage is fully planned (the architecture covering it was just approved, nothing pending) and there is a next stage, set action to "next_stage" and write a message introducing the next stage as a new idea for this same project, in your own words (2-4 sentences, include its key content).
When the last stage is fully planned, set action to "finish"."""
    else:
        mode_rules = f"""You told the assistant ALL goals up front in your first message:
{stage_txt}
When the brief, spec and architecture have all been written and you approved the architecture, set action to "finish"."""
    prompt = f"""{scn['persona']}

PROJECT FACTS (your ground truth; only use facts relevant to revealed stages):
{chr(10).join('- ' + f for f in proj['facts'])}

{mode_rules}

Current document statuses on disk:
{status}

Recent conversation (oldest first):
{history_tail}

ASSISTANT'S LATEST MESSAGE:
<<<
{agent_msg[-9000:]}
>>>

Decide your reply. If the assistant asked questions, answer them all briefly and consistently with your facts. If it presented a draft for review, accept/approve it explicitly (or request one specific fix if it contradicts your facts). If it is waiting with nothing to answer, tell it to continue to the next step. Never instruct it which skill to use. Planning ends at an approved architecture: never ask for an implementation plan, tasks, or code. When you approve something and also introduce the next stage, put the approval first in the same message ("Approved. Next idea: ...").
Return ONLY a JSON object: {{"action": "reply" | "next_stage" | "finish", "message": "<what you say to the assistant>"}}"""
    r = sh([CLAUDE_BIN, "-p", prompt, "--model", USER_MODEL, "--tools", "", "--output-format", "json",
            "--no-session-persistence", *ISOLATE], HERE, timeout=600)
    try:
        txt = json.loads(r.stdout)["result"]
        m = re.search(r"\{.*\}", txt, re.S)
        return json.loads(m.group(0))
    except Exception:
        return {"action": "reply", "message": "Looks good, accepted. Please continue."}


def opening(scn, traj):
    proj = scn["projects"][traj["project"]]
    st = proj["stages"]
    if traj["project"] == "rl":
        intro = ("I want to start a small ML project: an RL lab of little 2D environments where agents learn a "
                 "concept through reinforcement learning, so I can learn RL by building. Let's refine the idea and plan it.")
    else:
        intro = ("I want to start a personal quant research platform for market research on US equities, built in stages. "
                 "Let's refine the idea and plan it.")
    if traj["mode"] == "incremental":
        return f"{intro}\n\nI'm starting with just the first piece: {st[0]['reveal']}", 1
    goals = "\n".join(f"{i+1}. {s['reveal']}" for i, s in enumerate(st))
    return f"{intro}\n\nHere is everything I eventually want it to do:\n{goals}", len(st)


def main():
    tid, out = sys.argv[1], pathlib.Path(sys.argv[2]).resolve()
    scn = json.loads((HERE / "scenarios.json").read_text())
    traj = next(t for t in scn["trajectories"] if t["id"] == tid)
    stages = scn["projects"][traj["project"]]["stages"]
    proj = out / "project"
    if proj.exists():
        shutil.rmtree(proj)
    (proj / ".claude" / "skills").mkdir(parents=True)
    for s in ["idea-refine", "spec-writing", "architecture-design"]:
        shutil.copytree(SKILLS_SRC / s, proj / ".claude" / "skills" / s)
    # Skills reference `skills/<name>/scripts/...`; mirror the dev-team2 layout so those paths resolve.
    os.symlink(".claude/skills", proj / "skills")
    nh = proj / ".claude" / "skills" / "null-hypothesis-testing"
    nh.mkdir()
    shutil.copy(HERE / "stub_null_hypothesis_SKILL.md", nh / "SKILL.md")
    sh(["git", "init", "-q"], proj)
    sh(["git", "-c", "user.email=e@e", "-c", "user.name=eval", "commit", "-q", "--allow-empty", "-m", "turn 0"], proj)

    sid = str(uuid.uuid4())
    msg, n_revealed = opening(scn, traj)
    turns, history = [], []
    stage_log = [{"turn": 1, "stage": stages[0]["name"] if traj["mode"] == "incremental" else "all"}]
    t_start = time.time()
    closing = False
    for t in range(1, traj["max_turns"] + 1):
        reply, usage, tools, skills, dt = agent_turn(proj, sid, msg, t == 1, out / "agent_stream.jsonl")
        sh(["git", "add", "-A", "docs"], proj)
        sh(["git", "-c", "user.email=e@e", "-c", "user.name=eval", "commit", "-q", "--allow-empty", "-m", f"turn {t}"], proj)
        changed = sh(["git", "show", "--stat", "--format=", "HEAD"], proj).stdout.strip()
        rec = {"turn": t, "user": msg, "assistant": reply, "skills": skills, "tools": tools,
               "seconds": round(dt, 1), "usage": usage, "docs_changed": changed, "status": doc_status(proj),
               "stage": stage_log[-1]["stage"]}
        turns.append(rec)
        history.append(f"USER: {msg[:1500]}\nASSISTANT: {reply[:1500]}")
        (out / "turns.json").write_text(json.dumps(turns, indent=1))
        print(f"[{tid}] turn {t} stage={rec['stage']} {dt:.0f}s skills={skills} changed={changed.splitlines()[-1] if changed else '-'}", flush=True)

        if closing:
            turns[-1]["sim_user_final"] = "(closing approval delivered)"
            (out / "turns.json").write_text(json.dumps(turns, indent=1))
            break
        revealed = stages[:n_revealed]
        nxt = stages[n_revealed] if traj["mode"] == "incremental" and n_revealed < len(stages) else None
        u = sim_user(scn, traj, revealed, nxt, "\n\n".join(history[-4:-1]), reply, rec["status"])
        # Guard: only advance/finish when the spec is Approved, an architecture exists, and no idea is still open.
        st = rec["status"]
        ready = ("docs/spec.md: Approved" in st and "docs/architecture.md:" in st and
                 not re.search(r"docs/ideas/\S+: (Draft|Accepted)", st) and "docs/brief.md: Draft" not in st)
        if u.get("action") in ("finish", "next_stage") and not ready:
            u["action"] = "reply"
        if u.get("action") == "finish":
            if "docs/architecture.md: Approved" in st or closing:
                turns[-1]["sim_user_final"] = u.get("message")
                break
            # Send the closing approval so the agent can mark the architecture Approved; stop after that turn.
            closing = True
            u["action"] = "reply"
        if u.get("action") == "next_stage" and nxt:
            n_revealed += 1
            stage_log.append({"turn": t + 1, "stage": nxt["name"]})
        msg = u.get("message") or "Accepted. Continue."
        # Write the unsent sim-user message on the final iteration so the record is complete.
    summary = {"trajectory": tid, "turns": len(turns), "stages_reached": n_revealed, "stage_log": stage_log,
               "total_seconds": round(time.time() - t_start, 1),
               "agent_cost_usd": round(sum((x["usage"].get("cost_usd") or 0) for x in turns), 3),
               "agent_output_tokens": sum(((x["usage"].get("usage") or {}).get("output_tokens") or 0) for x in turns),
               "finished": any("sim_user_final" in x for x in turns)}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    sh(["git", "log", "--stat", "--format=== %s"], proj).stdout and (out / "doc_history.txt").write_text(
        sh(["git", "log", "--reverse", "-p", "--format=========== %s", "--", "docs"], proj).stdout)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
