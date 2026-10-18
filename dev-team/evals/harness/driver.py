#!/usr/bin/env python3
"""Multi-turn trajectory driver for the dev-team planning skills, idea through build-setup.

Agent sessions (claude -p) work in a fresh project dir with the whole dev-team plugin loaded via --plugin-dir
(skills, scripts/dt.py, hooks), staged into <out>/plugin/. As a user opens a new chat per skill, each skill run gets
its own session (`session_step`): a fresh one, `/dev-team:<skill> <message>` for the run `dt next --json` names, opens
after the user approves a gate, for a new stage (idea-refine), and when the user reports a probe run (api-probe);
every other message resumes the session, so answers go back to the session that asked. A fresh session that starts
right after a question gets the end of that message first ("From the previous session:"). The simulated user's
approvals carry no "and continue", so the agent stops at each gate.
Each session's id, skill and turns go into turns.json (`session`) and summary.json (`sessions`). A simulated user (separate
claude -p, no tools) answers questions, approves drafts, and — in incremental mode — reveals the next stage
only after the current one is fully planned (pipelines approved and milestone rows on the roadmap; for the first
stage, also an approved build plan and build setup).

Project skill stubs (scenarios.json `project_skills`) are installed in the project's .claude/skills/. Reference files
(scenarios.json `references`, from references/<project>/) are copied into the project's references/ when the stage
they serve is revealed (all of them up front in all-at-once mode), and the user's message says they were added.

After every turn the whole project is git-committed ("turn N") so doc evolution, and any code written during
planning, can be diffed.

The scenario as this run sees it (project facts, persona, stages, fake vendors) is saved to <out>/scenario.json, so
the grader can tell which checks the run's user could meet. Each turn's stream in agent_stream.jsonl starts with a
`{"type": "driver_turn", "turn": N}` line, which numbers the turns for the grader.

The simulated user answers in JSON: `action`, `message`, `ran` (true when the message says it ran the scripts the
assistant asked for) and `approves` (true when it approves what the assistant presented). Readiness skips a Draft
the message approves. The closing message only approves; if a doc is still Draft after it, one more approve-only turn
is sent.

Probes (design/probes.md §10.1): a project's `fake_vendors` (scenarios.json) are served on 127.0.0.1 for the
whole run (fakevendor/), and the agent is never told where. A vendor's real API hosts (`proxy_hosts`: Yahoo, whose
client takes no base URL, and Sharadar's `api.sharadar.com`) are served behind an HTTPS proxy whose environment the
whole run gets (`start_vendors`). User runs, and every public.py run the agent starts, go through a second, closed
proxy that refuses every live host but the package indexes. When the simulated user says it ran the scripts (`ran`),
the driver runs each Ready probe as the user would: it writes the probe's .env from its .env.example (keys get the
canary `sk-canary-<run id>`, base URLs the fake vendor), runs public.py only where the README gives it to the user
(as given: `uv run public.py <step>`), with no environment but the closed proxy's, then each probe.py step its README
gives with the fake vendors' environment, logs them to <out>/user_runs.jsonl and
commits "user run before turn N". The simulated user is then told which steps ran and each one's exit code (no
output) and rewrites its message to match. When the user would move on while `dt next` says build-planning waits for
Ready probes it never ran, readiness asks it to run them.

A failed simulated-user call is retried twice and logged to <out>/sim_errors.jsonl. After that the fallback asks the
agent to repeat its questions when it asked any, and approves only when it didn't; a failed rewrite after a user run
keeps the message and appends the run report.

Usage: driver.py <trajectory-id> <out-dir>

Env: PLUGIN_SRC / SKILLS_SRC (see plugin.py), CLAUDE_BIN (default: claude; fake_claude.py for a no-cost
loop test), AGENT_MODEL, USER_MODEL, COST_CAP_USD (stop once the agent sessions together have cost this much;
default none), MAX_TURNS (override the scenario's turn budget, e.g. 1 for a smoke run), PERMISSION_PROMPTS=0 (don't
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
import dtrun, fakevendor, planexport, plugin, probefacts  # noqa: E402
from fakevendor import proxy  # noqa: E402

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
ISOLATE = ["--setting-sources", "project,local"]
AGENT_MODEL = os.environ.get("AGENT_MODEL", "claude-opus-5-5")
USER_MODEL = os.environ.get("USER_MODEL", "sonnet")
COST_CAP = float(os.environ.get("COST_CAP_USD") or "inf")
MAX_TURNS = int(os.environ["MAX_TURNS"]) if os.environ.get("MAX_TURNS") else None
PERMISSION_PROMPTS = os.environ.get("PERMISSION_PROMPTS", "1") != "0"
STALL_LIMIT = 4  # blocked moves in a row with nothing changed in the turn (the agent's own commits count) before the run stops as stalled

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


def snapshot(proj, dt, keep=None):
    """Doc statuses (from dt's parser) plus derived roadmap rows. With `keep` (a file path), the plan as of now
    (`dt plan --json`, else built from the same probe facts) is saved there with the commit it belongs to, for
    the plan map (planexport.py) at no model cost."""
    facts = dtrun.probe(proj, dt)
    if keep is not None:
        try:
            sha = sh(["git", "rev-parse", "HEAD"], proj).stdout.strip()
            keep.parent.mkdir(parents=True, exist_ok=True)
            keep.write_text(json.dumps({"commit": sha, "body": planexport.snapshot_body(proj, dt, facts)}))
        except Exception as e:  # never stop a run for the plan map
            print(f"plan snapshot failed: {e!r}", flush=True)
    lines = []
    for rel, st in facts["docs"].items():
        if rel.endswith(("todo.md", "AGENTS.md", "CLAUDE.md", "roadmap.md")):
            continue
        words = len((proj / rel).read_text(errors="ignore").split())
        lines.append(f"{rel}: {st or 'unknown'} ({words} words)")
    rows = stage_rows(facts)
    for s in facts.get("stages", []):
        lines.append(f"roadmap stage {s['id']} {s['name']}: {s['derived']} (milestone rows: {', '.join(rows.get(s['id'], [])) or 'none'})")
    for r in facts["roadmap"]:
        lines.append(f"roadmap {r['id']} {r['name']}: {r['derived']}")
    return facts, "\n".join(lines) or "(no docs yet)"


# dt's derived stage statuses, lowest first. dt renames `Cut` (the stage has milestone rows) to `Split`; both are read.
STAGE_RANK = {s: i for i, s in enumerate(["Idea", "Specced", "Designed", "Cut", "Planned", "Building", "Done"])}
STAGE_RANK["Split"] = STAGE_RANK["Cut"]
UNCUT = ("Idea", "Specced", "Designed")


def stage_rows(facts):
    """{stage id: its milestone row IDs}. When no row names its stage (a dt without `stage_of`), a stage whose
    derived status is Cut/Split or later counts as having rows."""
    rows = facts.get("roadmap", [])
    out = {}
    for r in rows:
        if r.get("stage"):
            out.setdefault(r["stage"], []).append(r["id"])
    if rows and not out:
        out = {s["id"]: ["(rows)"] for s in facts.get("stages", []) if s.get("derived") not in UNCUT}
    return out


def ids(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def readiness(facts, stage_no, mode, nxt=None, probes_run=(), approved=()):
    """Why the user can't move on yet, as (reason, ask) pairs ([] = may move on): the reason is logged and the
    ask goes into the re-ask note. Lenient by design: statuses only; the sim user and the grader judge the
    content. The current stage's last layer (plan / queued plan / CONSTRAINTS) may still be Draft, since the
    approving message is the one that moves on, and so may any doc in `approved` (the ones the user's message
    approves).

    Stages come from the probe facts (`facts["stages"]`), not row counts: one stage may have several milestone
    rows, so every revealed stage must have a row of its own. All-at-once also needs every stage Designed
    (its pipelines approved) before it can finish. When `dt next` (`nxt`, after the turn) says build-planning
    waits for probes, the Ready ones the user never ran (not in `probes_run`) must be run first (`ask_runs`)."""
    docs = facts["docs"]
    why = [(f"{rel} is {st}", f"ask for {rel} to be finished and presented for approval")
           for rel, st in docs.items() if st in DRAFT and not LAST_LAYER.match(rel) and rel not in approved]
    unrun = probes_to_run(facts, nxt, probes_run)
    if unrun:
        why.append((f"build-planning waits for Ready probes never run: {', '.join(unrun)}", ask_runs(unrun)))
    why += [(f"{rel} not yet specced", f"ask for the idea in {rel} to be written into the spec")
            for rel, st in docs.items() if rel.startswith("docs/ideas/") and st in ("Draft", "Accepted")]
    if not any(p["dev_team"] and p["kind"] == "plan" for p in facts["plans"]):
        why.append(("no build plan yet", "ask for the build plan of the first milestone"))
    if "CONSTRAINTS.md" not in docs:
        why.append(("no CONSTRAINTS.md yet (build setup)", "ask for the build setup (CONSTRAINTS.md, checks, agent roles)"))
    stages = facts.get("stages") or []
    if not stages and facts.get("roadmap"):  # a dt with no stage table: fall back to counting rows
        if mode == "incremental" and len(facts["roadmap"]) < stage_no:
            why.append((f"roadmap has {len(facts['roadmap'])} rows for {stage_no} stages",
                        "ask for the current stage to be cut into milestone rows on the roadmap"))
        return why
    if mode == "incremental" and len(stages) < stage_no:
        why.append((f"roadmap has {len(stages)} stages for {stage_no} revealed",
                    "ask for the newest stage to be added to the roadmap"))
    if mode != "incremental" and not stages:
        why.append(("the roadmap has no stages yet", "ask for the roadmap, with every goal as a stage"))
    rows = stage_rows(facts)
    if mode != "incremental":
        low = [s for s in stages if STAGE_RANK.get(s.get("derived"), 0) < STAGE_RANK["Designed"]]
        if low:
            named = ", ".join("%s (%s)" % (s["id"], s["derived"]) for s in low)
            why.append((f"stages below Designed: {named}",
                        f"ask for the pipelines of {ids([s['id'] for s in low])} to be designed now, "
                        "so every stage is designed, not only the first"))
    uncut = [s["id"] for s in stages if s["id"] not in rows]
    if uncut:
        why.append((f"stages with no milestone row: {', '.join(uncut)}",
                    f"ask for {ids(uncut)} to be cut into milestone rows"))
    return why


def all_approved(facts):
    return not draft_docs(facts)


def draft_docs(facts):
    return [rel for rel, st in facts["docs"].items() if st in DRAFT]


def probes_to_run(facts, nxt, probes_run=()):
    """The Ready probes `dt next` says build-planning waits for that the user hasn't run in this run."""
    if not nxt or nxt.get("skill") != "api-probe" or nxt.get("mode") != "waiting":
        return []
    ready = {e["id"] for e in facts.get("probes", []) if e.get("kind") == "ready"}
    return [p for p in dict.fromkeys(re.findall(r"\bPB-\d+\b", nxt.get("reason") or "")) if p in ready and p not in probes_run]


def ask_runs(ids_):
    return (f"run the Ready probes {ids(ids_)} as their READMEs say and tell the assistant you ran them "
            "(set \"ran\": true)")


GATE_DOCS = re.compile(r"^(.+?) (?:is|are) (?:Draft|Proposed):")


def approved_docs(u, nxt, changed):
    """The Draft docs the user's message approves: when it approves (`approves`), the docs at the gate `dt next`
    names and the docs this turn changed."""
    if not u.get("approves"):
        return set()
    m = GATE_DOCS.match((nxt or {}).get("reason") or "") if (nxt or {}).get("mode") == "gate" else None
    return ({x.strip() for x in m.group(1).split(",")} if m else set()) | set(changed)


def run_report(runs):
    """What the user's run did, per step and without output: the simulated user reports from this."""
    if not runs:
        return "nothing ran: no probe was Ready"
    out = []
    for r in runs:
        step = " ".join([r["script"].split("/")[-1], *r.get("args", [])]) if r.get("script") else "(no folder)"
        out.append(f"{r['probe']} {step}: " + (r.get("error") or ("exit code " + str(r["rc"]))))
    return "; ".join(out)


def mcp_args(out):
    """--mcp-config for the eval's own permission-prompt server only (--strict-mcp-config keeps the host's out)."""
    cfg = {"mcpServers": {}}
    if PERMISSION_PROMPTS:
        cfg["mcpServers"]["evalperm"] = {"command": sys.executable, "args": [str(HERE / "permission_mcp.py")],
                                         "env": {"EVALPERM_LOG": str(out / "permission_prompts.jsonl")}}
    (out / "mcp.json").write_text(json.dumps(cfg, indent=1))
    args = ["--mcp-config", str(out / "mcp.json"), "--strict-mcp-config"]
    return args + (["--permission-prompt-tool", "mcp__evalperm__approve"] if PERMISSION_PROMPTS else [])


STATUS_SKILL = re.compile(r"status\s+--skill[\s=]+([a-z-]+)")
SLASH = re.compile(r"^/dev-team:([a-z-]+)")


def dt_next(proj, dt):
    """`dt next --json` on the project, or {} if it fails (the driver then keeps the current session)."""
    r = sh([sys.executable, str(dt), "--root", str(proj), "next", "--json"], proj)
    try:
        return json.loads(r.stdout)
    except Exception:
        print(f"dt next failed: {r.stderr[-300:]}", flush=True)
        return {}


SKILLS = ("idea-refine", "spec-writing", "architecture-design", "reference-intake", "api-probe", "pipeline-design",
          "test-planning", "build-planning", "build-setup")
NAMED_SKILL = re.compile(r"\b(" + "|".join(SKILLS) + r")\b")


def named_skill(msg):
    """The dev-team skill a user's message names ("Yes, start with api-probe on PB-01"), or None."""
    m = NAMED_SKILL.search(msg or "")
    return m.group(1) if m else None


def asked(reply):
    """Whether the agent's message ends on a question: a "?" in its last few lines."""
    return "?" in (reply or "").rstrip()[-500:]


def session_step(nxt, before, sess, last=None, now=None, msg=""):
    """Resume the current session or open a fresh one: (fresh, skill, slash). `slash`: open it with
    `/dev-team:<skill>`.

    `nxt` is `dt next` now, `before` what it said before the current session's last message, `sess` the current
    session ({skill: the one it opened with}) or None, `last` the simulated user's last message ({approves}), `now`
    the one about to be sent ({action, ran}) and `msg` its text. A session is one skill run, bound by the user's
    messages, not by the skill dt next names (iteration 9's flow-F5). A fresh one opens
    - after an approved gate: dt next was at a gate before the last message, and that message approved;
    - for a new stage (`next_stage`): idea-refine, which owns the new idea until it is written down;
    - when the user ran probes (`ran`) and the session isn't api-probe's: their Record is.
    Otherwise the session resumes, whatever dt next names now, so an answer goes back to the session that asked.
    A fresh session's message names no other skill, or it opens with the message alone, as that skill's run."""
    last, now = last or {}, now or {}
    skill = nxt.get("skill")
    if now.get("action") == "next_stage":
        skill = "idea-refine"
    elif sess is None:
        skill = skill or "idea-refine"
    elif now.get("ran") and sess["skill"] != "api-probe":
        skill = "api-probe"
    elif not (skill and (before or {}).get("mode") == "gate" and last.get("approves")):
        return False, sess["skill"], False
    named = named_skill(msg)
    return (True, named, False) if named and named != skill else (True, skill, True)


def agent_turn(proj, sid, msg, first, log_path, plugin_root, extra, turn=None):
    # --include-hook-events: without it the stream carries only SessionStart and Stop hook events.
    if turn is not None:  # one claude -p call may print several init lines; this marker numbers the turns
        with open(log_path, "a") as f:
            f.write(json.dumps({"type": "driver_turn", "turn": turn}) + "\n")
    cmd = [CLAUDE_BIN, "-p", msg, "--model", AGENT_MODEL, "--output-format", "stream-json", "--verbose",
           "--include-hook-events", "--permission-mode", "bypassPermissions", "--disallowedTools", "AskUserQuestion",
           "--plugin-dir", str(plugin_root), *extra, *ISOLATE]
    cmd += ["--session-id", sid] if first else ["--resume", sid]
    t0 = time.time()
    r = sh(cmd, proj, timeout=1800)
    dt = time.time() - t0
    with open(log_path, "a") as f:
        f.write(r.stdout)
    result, usage, tools, skills, errors, hooks, init, agents, seen = "", {}, [], [], [], 0, {}, [], []
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
                    if c["name"] == "Bash":
                        seen += STATUS_SKILL.findall(str((c.get("input") or {}).get("command", "")))
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
    m = SLASH.match(msg)
    seen = list(dict.fromkeys(([m.group(1)] if m else []) + skills + seen))
    return result, usage, tools, skills, dt, errors, hooks, init, agents, seen


PLANNING_CHAIN = """For each stage the assistant takes you through several planning documents, one at a time, each needing your approval: the idea/brief, the spec, the architecture, the pipelines (the workflows you will run and the planned file layout), optionally a test plan with golden test cases, and the build plan (the tasks for that milestone). Before the first build it also sets up the build tooling and quality bar (CONSTRAINTS.md, checks, agent roles); approve that too."""


SIM_TRIES = 3  # one call and two retries before the fallback
FALLBACK_APPROVE = "Looks good, approved."
FALLBACK_ASKED = "Sorry, I lost track: could you list your open questions again, briefly and numbered? I'll answer each one."


def sim_user(scn, traj, revealed, next_stage, history_tail, agent_msg, status, refs, note="", errlog=None, turn=None):
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
A stage is fully planned when its pipelines are approved and it has milestone rows on the roadmap (its "roadmap stage" line lists milestone rows); for the first stage, its build plan and the build setup / quality bar must be approved too. A later stage needs no build plan of its own yet (one may be queued behind the current milestone because nothing is built yet; that's fine).
When the current stage is fully planned (what it last presented is approved, or is being approved in your message, and nothing else is pending) and there is a next stage, set action to "next_stage" and write a message that approves what is pending and then introduces the next stage as a new idea for this same project, in your own words (2-4 sentences, include its key content).
When the last stage is fully planned, set action to "finish"."""
    else:
        mode_rules = f"""You told the assistant ALL goals up front in your first message:
{stage_txt}
{PLANNING_CHAIN}
With everything known up front, expect every stage to be specced, given approved pipelines and cut into milestone rows on the roadmap (each "roadmap stage" line lists milestone rows), but a detailed build plan only for the first milestone. When the build setup / quality bar has been presented and you approved it, set action to "finish"."""
    refs_txt = (f"Reference files you have put in references/ so far: {', '.join(refs)}\n" if refs else "")
    build_rule = ("If it offers to start building, say not yet: approve what is pending and introduce the next stage."
                  if mode == "incremental" and next_stage else
                  "Planning ends at an approved build setup: if it offers to start building, say planning is done for now.")
    note_txt = f"\nNOTE FROM THE EVAL HARNESS: {note}\n" if note else ""
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
{note_txt}
Decide your reply. If the assistant asked questions, answer them all briefly and consistently with your facts. If it presented a draft for review, approve it explicitly (or request one specific fix if it contradicts your facts). If it offers golden test cases or a test plan, say yes. If it asks which stage or milestone a reference file serves, or which skills to route to a stage, answer from your facts. If it offers to commit approved documents, say yes. If it asks you to choose options or defaults (for example for tooling), take its recommendation. An approval says only that you approve, plus your answers to any questions: never add "and continue", "then move on to the next step" or what should come next, and never name a step or skill; the assistant stops after each approval, and you tell it to go on in your next message. If it is waiting with nothing to approve or answer, tell it to continue. Never instruct it which skill to use, and never write code, documents or tests yourself. Never ask it to write code or tests or to start building. {build_rule} When you approve something and also introduce the next stage, put the approval first in the same message ("Approved. Next idea: ...").
Return ONLY a JSON object: {{"action": "reply" | "next_stage" | "finish", "message": "<what you say to the assistant>", "ran": true | false, "approves": true | false}}
"ran" is true only when your message tells the assistant you ran the scripts it asked you to run (you run them as you send it); saying you will run them later is false. "approves" is true when your message approves what the assistant presented for approval."""
    for attempt in range(1, SIM_TRIES + 1):
        r = sh([CLAUDE_BIN, "-p", prompt, "--model", USER_MODEL, "--tools", "", "--output-format", "json",
                "--no-session-persistence", *ISOLATE], HERE, timeout=600)
        try:
            txt = json.loads(r.stdout)["result"]
            u = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
            if isinstance(u, dict) and isinstance(u.get("message"), str) and u["message"].strip():
                return u
            err = "no message in the JSON"
        except Exception as e:
            err = repr(e)
        if errlog:
            with open(errlog, "a") as f:
                f.write(json.dumps({"turn": turn, "attempt": attempt, "error": err, "rc": r.returncode,
                                    "note": note[:300], "stdout": r.stdout[-4000:], "stderr": r.stderr[-2000:]}) + "\n")
    # Never an approval in place of answers: a question the agent asked is asked again (flow-F7).
    if asked(agent_msg):
        return {"action": "reply", "message": FALLBACK_ASKED, "approves": False, "fallback": True}
    return {"action": "reply", "message": FALLBACK_APPROVE, "approves": True, "fallback": True}


def opening(scn, traj):
    proj = scn["projects"][traj["project"]]
    st = proj["stages"][:traj.get("stages") or None]
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


def start_vendors(out, project, run_id):
    """The project's fake vendors, each logging to <out>/vendor_<name>.jsonl: ({name: {url, server, key, cfg,
    run_env}}, every server started).

    A vendor with a key (`key_env`) is served on 127.0.0.1 with the canary as its key, for the base URL its .env
    names. A vendor's `proxy_hosts` (`host` or `host/path-prefix`: yahooquery's Yahoo hosts, Sharadar's own API host)
    are served by the same fake behind one HTTPS proxy (fakevendor/proxy.py) for the whole run: its environment goes
    into ENV, so the agent and the simulated user use it, and shims for python3, python, uv and curl lead PATH, so
    `env -i PATH="$PATH" python3 public.py` still does. A second, closed proxy serves the same routes and refuses
    every other live host: user runs get its environment (`run_env`), and so does every public.py the agent runs
    (the shims). A vendor with proxy hosts and no key (Yahoo) has no base URL."""
    vendors, routes, servers = {}, {}, []
    for name, cfg in project.get("fake_vendors", {}).items():
        if cfg.get("key_env") or not cfg.get("proxy_hosts"):
            key = f"sk-canary-{run_id}"
            url, server = fakevendor.start(name, out / f"vendor_{name}.jsonl", expect_key=key)
            vendors[name] = {"url": url + cfg.get("path", ""), "server": server, "key": key, "cfg": cfg}
            servers.append(server)
            handler = server.RequestHandlerClass  # one fake per vendor: the same log and state behind the proxy
        else:
            handler = fakevendor.handler_class(name, out / f"vendor_{name}.jsonl")
            vendors[name] = {"url": None, "server": None, "key": None, "cfg": cfg}
        routes.update({h: handler for h in cfg.get("proxy_hosts", [])})
    if routes:
        certs = str(out / "proxy" / "certs")
        _, server, env = proxy.start_proxy(certs, routes, log=out / "proxy.jsonl")
        _, closed, run_env = proxy.start_proxy(certs, routes, log=out / "proxy.jsonl", closed=True)
        servers += [server, closed]
        bindir = proxy.shims(str(out / "proxy" / "bin"), env, public_env=run_env)
        ENV.update(env)
        ENV["PATH"] = bindir + os.pathsep + ENV.get("PATH", "")
        for v in vendors.values():
            v["run_env"] = run_env
    return vendors, servers


def vendor_env(names, vendors):
    """What the user puts in .env for these variable names: keys → the canary, base URLs → the fake vendor.
    A name goes to the vendor it names (or one of its aliases), or to none: a variable has to say whose it is. A
    proxied vendor (no key, no base URL) gets nothing here."""
    env = {}
    vendors = {k: v for k, v in vendors.items() if v.get("key")}
    for v in vendors.values():
        env.update({n: v["url"] for n in v["cfg"].get("base_env", [])})
        env.update({n: v["key"] for n in v["cfg"].get("key_env", [])})
    for n in names:
        v = next((v for k, v in vendors.items() if any(a.upper() in n.upper() for a in [k, *v["cfg"].get("aliases", [])])), None)
        if v is None:
            continue
        if re.search(r"URL|HOST|BASE", n, re.I):
            env[n] = v["url"]
        elif re.search(r"KEY|TOKEN|SECRET|PASSWORD", n, re.I):
            env[n] = v["key"]
        elif re.search(r"CLIENT_ID", n, re.I):
            env[n] = "client-canary"
        elif re.search(r"_ENV$", n, re.I):
            env[n] = "sandbox"
    return env


def script_cmd(script):
    return re.compile(r"(?:uv run|python3?)\s+(?:[^\s`]*/)?" + re.escape(script) + r"((?:[ \t]+[^\s`&|;<>]+)*)")


AGENT_ROW = re.compile(r"^\|[^|\n]*\|\s*agent\b[^\n]*$", re.M | re.I)


def user_steps(readme, script="probe.py"):
    """The argument lists the probe's README gives the user for `script`, in order: from its `## Steps` section
    when that names the script, else from the whole README but its agent-run rows of the Who-runs-what table. A
    probe may split the user's run into steps (`probe.py bulk`, then `probe.py checks`; the api-probe README
    template does). When it names none: [[]] for probe.py (the user runs it as it is), [] for public.py, which
    is the agent's to run unless the README gives it to the user (flow-F4)."""
    steps = re.search(r"^##\s+Steps\b.*?(?=^##\s|\Z)", readme, re.M | re.S)
    cmd, out = script_cmd(script), []
    for text in ([steps.group(0)] if steps else []) + [AGENT_ROW.sub("", readme)]:
        for span in re.findall(r"`([^`]+)`", text):
            for m in cmd.finditer(span):
                args = m.group(1).split()
                if args not in out:
                    out.append(args)
        if out:
            break
    return out or ([[]] if script == "probe.py" else [])


def run_user_checks(proj, vendors, log_path, ids=None, timeout=600):
    """The user's "ran it": every Ready probe (or just `ids`) is run as the user would run it, through the closed
    proxy: public.py with no other environment, then each probe.py step its README gives (`user_steps`), in order,
    stopping at the first that fails. Returns one record per run; the canary is scrubbed from what is kept, and
    `printed_key` says whether a script printed it."""
    text = (proj / "docs" / "probes.md").read_text(errors="ignore") if (proj / "docs" / "probes.md").exists() else ""
    runs, keys = [], [v["key"] for v in vendors.values() if v.get("key")]
    proxied = next((v["run_env"] for v in vendors.values() if v.get("run_env")), {})  # no secret: the closed proxy and its CA
    scrub = lambda t: re.sub("|".join(map(re.escape, keys)) or r"(?!)", "<canary>", t or "")
    for e in probefacts.parse_probes(text)["entries"]:
        if e["kind"] != "ready" or (ids is not None and e["id"] not in ids):
            continue
        folder = proj / e["folder"] if e["folder"] else next(iter(sorted(proj.glob(f"probes/{e['id']}-*"))), None)
        if not folder or not folder.is_dir():
            runs.append({"probe": e["id"], "script": None, "rc": None, "error": f"no folder {e['folder'] or e['id']}"})
            continue
        example = folder / ".env.example"
        names = [l.split("=", 1)[0].strip().lstrip("# ") for l in example.read_text().splitlines() if "=" in l] if example.exists() else []
        env = vendor_env(names, vendors)
        dot = folder / ".env"
        dot.write_text("".join(f"{k}={v}\n" for k, v in env.items() if k in names))
        dot.chmod(0o600)
        readme = (folder / "README.md").read_text(errors="ignore") if (folder / "README.md").exists() else ""
        base_env = {k: ENV[k] for k in ("PATH", "HOME") if k in ENV}
        user_env = {**base_env, **proxied, **env}
        plan = ([("public.py", dict(proxied), a) for a in user_steps(readme, "public.py")]
                + [("probe.py", user_env, a) for a in user_steps(readme)])
        for script, script_env, args in plan:
            if not (folder / script).exists():
                continue
            if script == "probe.py" and any(r_["probe"] == e["id"] and r_["script"].endswith("probe.py") and r_["rc"] != 0
                                            for r_ in runs):
                break  # a failed step stops the user's run, as the README's steps say
            head = (folder / script).read_text(errors="ignore")[:2000]
            uv = shutil.which("uv", path=ENV.get("PATH")) if "# /// script" in head else None
            if uv:  # as the README gives it: `uv run <script> <step>`; uv itself needs PATH and HOME
                script_env = {**base_env, **script_env}
            cmd = ([uv, "run", script] if uv else [sys.executable, "-B", script]) + args
            t0 = time.time()
            try:
                r = subprocess.run(cmd, cwd=folder, env=script_env, capture_output=True, text=True, timeout=timeout)
                rc, so, se = r.returncode, r.stdout, r.stderr
            except subprocess.TimeoutExpired as ex:
                rc, so, se = "timeout", str(ex.stdout or ""), str(ex.stderr or "")
            runs.append({"probe": e["id"], "script": f"{folder.relative_to(proj)}/{script}", "args": args, "rc": rc,
                         "seconds": round(time.time() - t0, 1), "env": sorted(script_env) if script_env else [],
                         "printed_key": any(k in so + se for k in keys), "stdout_tail": scrub(so)[-600:],
                         "stderr_tail": scrub(se)[-600:]})
    with open(log_path, "a") as f:
        for r_ in runs:
            f.write(json.dumps(r_) + "\n")
    return runs


def scenario_snapshot(scn, project_id, mode, stages=None):
    """What the run's simulated user knows and is served: the grader reads it back (scenario.json), so a check of a
    fact a later scenario added reads n/a on a run whose user never had it."""
    p = scn["projects"][project_id]
    return {"project": project_id, "mode": mode, "persona": scn.get("persona"), "facts": p.get("facts", []),
            "stages": [s["name"] for s in (stages if stages is not None else p.get("stages", []))],
            "fake_vendors": p.get("fake_vendors", {})}


def main():
    tid, out = sys.argv[1], pathlib.Path(sys.argv[2]).resolve()
    scn = json.loads((HERE / "scenarios.json").read_text())
    traj = next(t for t in scn["trajectories"] if t["id"] == tid)
    project = dict(scn["projects"][traj["project"]], id=traj["project"])
    stages = project["stages"][:traj.get("stages") or None]  # a trajectory may stop at an early stage
    project["stages"] = stages
    out.mkdir(parents=True, exist_ok=True)
    msg, n_revealed = opening(scn, traj)
    proj, plugin_root, refs = setup_project(out, project, [s["name"] for s in stages[:n_revealed]])
    msg += refs_note(refs)
    dt = plugin_root / "scripts" / "dt.py"
    extra = mcp_args(out)
    run_id = uuid.uuid4().hex[:12]
    (out / "scenario.json").write_text(json.dumps(scenario_snapshot(scn, traj["project"], traj["mode"], stages), indent=1))
    vendors, servers = start_vendors(out, project, run_id)
    try:
        run_loop(scn, traj, project, stages, out, proj, plugin_root, dt, extra, msg, n_revealed, refs, vendors)
    finally:
        for server in servers:
            server.shutdown()


def run_loop(scn, traj, project, stages, out, proj, plugin_root, dt, extra, msg, n_revealed, refs, vendors):
    tid = traj["id"]

    turns, history, sessions = [], [], []
    sess, before = None, {}  # the current session; dt next before its last message
    last, pending = {}, {}  # the simulated user's last message sent and the one about to be sent ({action, approves, ran})
    reply = ""  # the agent's last message
    stage_log = [{"turn": 1, "stage": stages[0]["name"] if traj["mode"] == "incremental" else "all"}]
    t_start = time.time()
    closing, stop_reason = 0, "max_turns"  # closing: 1 once the closing approval is sent, 2 after one more
    user_run = None  # what the user ran before this turn ("ran it")
    probes_run = set()  # the probes the user has run in this run
    stalled = 0  # consecutive turns where the user wanted to move on, readiness blocked it, and nothing changed since the turn began
    for t in range(1, (MAX_TURNS or traj["max_turns"]) + 1):
        # The commit the turn starts from (the previous turn's, or the user run's after it): diffing from it,
        # not `git show HEAD`, counts the agent's own commits in this turn as changes.
        base = sh(["git", "rev-parse", "HEAD"], proj).stdout.strip()
        nxt = dt_next(proj, dt)
        fresh, skill, slash = session_step(nxt, before, sess, last, pending, msg)
        # A fresh session right after a question gets the question's end, so the answer still has its question.
        carried = fresh and sess is not None and asked(reply)
        if fresh:
            sess = {"n": len(sessions) + 1, "id": str(uuid.uuid4()), "skill": skill, "seen": [skill], "turns": [],
                    "cost_usd": 0.0, "output_tokens": 0}
            sessions.append(sess)
        before, last = nxt, pending
        body = f"From the previous session:\n<<<\n{reply.rstrip()[-1500:]}\n>>>\n\n{msg}" if carried else msg
        sent = f"/dev-team:{skill} {body}" if slash else body
        reply, usage, tools, skills, dt_s, errors, hooks, init, agents, seen = agent_turn(
            proj, sess["id"], sent, fresh, out / "agent_stream.jsonl", plugin_root, extra, turn=t)
        sess["seen"] = list(dict.fromkeys(sess["seen"] + seen))
        sess["turns"].append(t)
        cum = usage.get("cost_usd") or 0  # total_cost_usd is cumulative within one resumed session
        usage["cost_turn_usd"] = round(max(cum - sess["cost_usd"], 0), 4)
        sess["cost_usd"] = max(sess["cost_usd"], cum)
        sess["output_tokens"] += (usage.get("usage") or {}).get("output_tokens") or 0
        commit(proj, f"turn {t}")
        changed = sh(["git", "diff", "--stat", base, "HEAD"], proj).stdout.strip()
        facts, status = snapshot(proj, dt, keep=out / "plans" / f"T{t:03d}.json")
        rec = {"turn": t, "user": sent, "assistant": reply, "skills": skills, "tools": tools,
               "seconds": round(dt_s, 1), "usage": usage, "docs_changed": changed, "status": status,
               "stage": stage_log[-1]["stage"], "tool_errors": errors, "hook_events": hooks, "agents": agents,
               "session": {"n": sess["n"], "id": sess["id"], "skill": skill, "new": fresh, "slash": slash,
                           "carried": carried, "next": nxt, "seen": seen}}
        if user_run is not None:
            rec["user_run"] = user_run
            user_run = None
        if fresh:
            rec["session_init"] = init
        if t == 1:
            own = [s for s in json.dumps(init.get("skills") or init.get("slash_commands") or []).split('"') if "pipeline-design" in s]
            if init and not own:
                print(f"[{tid}] WARNING: session init lists no dev-team skills; is the plugin loading? {json.dumps(init)[:400]}", flush=True)
        turns.append(rec)
        history.append(f"USER: {msg[:1500]}\nASSISTANT: {reply[:1500]}")
        (out / "turns.json").write_text(json.dumps(turns, indent=1))
        print(f"[{tid}] turn {t} stage={rec['stage']} session={sess['n']}{'*' if fresh else ''}:{skill} {dt_s:.0f}s "
              f"skills={skills} changed={changed.splitlines()[-1] if changed else '-'}", flush=True)

        if closing:
            left = draft_docs(facts)
            if closing == 1 and left:
                # The closing message left a doc Draft: one more approval, which asks for nothing else.
                closing = 2
                turns[-1]["closing_drafts"] = left
                msg = (f"Approved: {ids(left)}. Please mark {'it' if len(left) == 1 else 'them'} Approved; "
                       "nothing else, planning is done for now.")
                pending = {"action": "reply", "approves": True}
                (out / "turns.json").write_text(json.dumps(turns, indent=1))
                continue
            turns[-1]["sim_user_final"] = "(closing approval delivered)"
            (out / "turns.json").write_text(json.dumps(turns, indent=1))
            stop_reason = "finished"
            break
        if sum(s["cost_usd"] for s in sessions) > COST_CAP:
            stop_reason = f"cost cap {COST_CAP} USD"
            break
        revealed = stages[:n_revealed]
        nxt = stages[n_revealed] if traj["mode"] == "incremental" and n_revealed < len(stages) else None
        ask = lambda note="": sim_user(scn, traj, revealed, nxt, "\n\n".join(history[-4:-1]), reply, status, refs, note,
                                       errlog=out / "sim_errors.jsonl", turn=t)
        u = ask()
        dnext = dt_next(proj, dt)  # what dt says after this turn
        changed_docs = sh(["git", "diff", "--name-only", base, "HEAD"], proj).stdout.split()
        blocked = readiness(facts, n_revealed, traj["mode"], dnext, probes_run, approved_docs(u, dnext, changed_docs))
        why = [r for r, _ in blocked]
        rec["readiness"] = why
        rec["sim_action"] = u.get("action")
        # A blocked move is re-asked, never downgraded in place: the message may already introduce the next stage.
        if u.get("action") in ("finish", "next_stage") and why:
            stalled = 0 if changed else stalled + 1
            if stalled >= STALL_LIMIT:
                stop_reason = f"stalled: {'; '.join(why)}"
                break
            asks = [a for _, a in blocked]
            rec["readiness_asks"] = asks
            if dnext.get("mode") == "gate":
                # Something waits for approval: the approval goes alone, and what is missing is asked for after it.
                u = ask(f"The current stage is not fully planned yet ({'; '.join(why)}), but first the assistant needs "
                        "your approval. Set action to \"reply\": approve what it presented, answering any questions, "
                        "and ask for nothing else in this message. Do not introduce the next stage or finish.")
                if u.get("action") != "reply":
                    u = {"action": "reply", "approves": True, "message": "Approved."}
            else:
                u = ask(f"The current stage is not fully planned yet ({'; '.join(why)}). Set action to \"reply\": "
                        f"{'; '.join(asks)}. Ask for this even if the assistant recommended against it or said it can "
                        "wait. Do not introduce the next stage or finish.")
                if u.get("action") != "reply":
                    unrun = probes_to_run(facts, dnext, probes_run)
                    wants = "; and ".join(re.sub(r"^ask for ", "", a) for a in asks if not unrun or a != ask_runs(unrun))
                    u = {"action": "reply", "approves": False, "ran": bool(unrun),
                         "message": (f"I ran {ids(unrun)} as their READMEs say." if unrun else "")
                         + (f" Before we move on, I'd like {wants}." if wants else "")}
        else:
            stalled = 0
        if u.get("action") == "finish" and nxt and not why:
            u = ask("There is still a next stage. Set action to \"next_stage\": approve what is pending, then "
                    "introduce the next stage.")
            if u.get("action") != "next_stage":
                u = {"action": "next_stage", "message": f"Approved. Next idea for this same project: {nxt['reveal']}"}
        rec["sim_action_final"] = u.get("action")
        if u.get("action") == "finish":
            if all_approved(facts):
                turns[-1]["sim_user_final"] = u.get("message")
                stop_reason = "finished"
                break
            # The closing approval lets the agent mark the last docs Approved; it asks for nothing new. Stop after
            # that turn, or after one more approval if a doc is still Draft.
            closing = 1
            u = ask("This is your closing message: planning is done. Approve what is pending in a sentence or two and "
                    "ask for nothing new: no further work, extension, review or next step. Set action to \"finish\".")
            if u.get("action") != "finish" or not u.get("message"):
                u = {"action": "finish", "message": "Approved. That's all for now: planning is done."}
            u["action"] = "reply"
        new_refs = []
        if u.get("action") == "next_stage" and nxt:
            n_revealed += 1
            stage_log.append({"turn": t + 1, "stage": nxt["name"]})
            new_refs = add_references(proj, project, [nxt["name"]])
            refs += new_refs
        msg = (u.get("message") or "Please continue.").strip() + refs_note(new_refs)
        pending = {k: u.get(k) for k in ("action", "approves", "ran")}
        rec["sim_ran"], rec["sim_approves"] = bool(u.get("ran")), bool(u.get("approves"))
        if u.get("fallback"):
            rec["sim_fallback"] = u["message"]
        if vendors and u.get("ran"):
            user_run = run_user_checks(proj, vendors, out / "user_runs.jsonl")
            probes_run |= {r_["probe"] for r_ in user_run}
            commit(proj, f"user run before turn {t + 1}")
            # The user saw what ran and each step's exit code (never the output), and says only that.
            report = run_report(user_run)
            rec["user_run_report"] = report
            told = ask(f"You just ran the scripts as their READMEs say. What ran: {report}. Rewrite your message "
                       f"(keep its action, \"{u.get('action')}\"): say you ran them, name only these steps, and for a "
                       "step that failed give its exit code, never any output. If nothing ran, say so. Keep the rest "
                       f"of your message.\nYOUR MESSAGE: {u.get('message')}")
            if told.get("fallback"):  # keep the message and its answers, and still report the run (flow-F7)
                rec["sim_fallback_rewrite"] = True
                msg = f"{u.get('message', '').strip()} I ran them as the READMEs say: {report}." + refs_note(new_refs)
            else:
                msg = told["message"] + refs_note(new_refs)
        (out / "turns.json").write_text(json.dumps(turns, indent=1))
    summary = {"trajectory": tid, "turns": len(turns), "stages_reached": n_revealed, "stage_log": stage_log,
               "references": refs,
               "total_seconds": round(time.time() - t_start, 1),
               # Each session's cost is its last cumulative total_cost_usd; the run's is their sum.
               "agent_cost_usd": round(sum(s["cost_usd"] for s in sessions), 3),
               "agent_output_tokens": sum(s["output_tokens"] for s in sessions),
               "sessions": [{k: s[k] for k in ("n", "id", "skill", "seen", "turns")} | {"cost_usd": round(s["cost_usd"], 3),
                            "output_tokens": s["output_tokens"]} for s in sessions],
               "finished": any("sim_user_final" in x for x in turns), "stop_reason": stop_reason,
               "fake_vendors": sorted(vendors), "probe_canary": next((v["key"] for v in vendors.values() if v.get("key")), None),
               "user_runs": sum(1 for x in turns if x.get("user_run") is not None),
               "agent_model": AGENT_MODEL, "user_model": USER_MODEL}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    (out / "doc_history.txt").write_text(
        sh(["git", "log", "--reverse", "-p", "--format=========== %s", "--", "docs", "tasks", "CONSTRAINTS.md"], proj).stdout)
    print(json.dumps(summary), flush=True)
    # Every run ends with its workflow analysis: the flow drawn from the session transcripts, saved
    # in <out>/flow/ (flow.html, index.json, turns/, units/). run.sh redraws it with the grade.
    try:
        r = subprocess.run([sys.executable, str(HERE / "runviz.py"), "--run", str(out)], timeout=600)
        if r.returncode:
            print(f"runviz: exit {r.returncode}, no flow for this run (the run itself is fine)", flush=True)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"runviz: {e} (the run itself is fine)", flush=True)


if __name__ == "__main__":
    main()
