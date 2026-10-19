#!/usr/bin/env python3
"""Cases for the driver's own decisions: driver.session_step (when a turn resumes the current agent session and when
it opens a fresh one, for which skill, and whether with `/dev-team:<skill>`), driver.user_steps (the probe.py and
public.py steps a probe's README gives the user, run in order on "ran it"), driver.readiness's probe and approval
clauses, run_report (what the simulated user is told after its run), sim_user's fallback when every call fails and
sim_answer's when it answers in prose, working_skill (the skill a turn worked in), start_vendors' proxied Sharadar
(no base URL; the closed proxy serves api.sharadar.com with the canary key), and agent_turn past the turn limit (a
hanging CLI killed with its child, its stream kept, the run told and going on), the sim user's rule that its facts' bars
and constraints stay, and a user's probe step's time limit (the time its README states, `stated_seconds` and
`step_limit`; a step past it killed with its child and reported in plain words). No dt, no model calls; the dry run
runs this too.

Usage: sessions.py   prints one line per case; exit 1 if any case comes out wrong
"""
import json, os, pathlib, subprocess, sys, tempfile, textwrap, time, urllib.request

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import driver  # noqa: E402
from driver import (FALLBACK_APPROVE, FALLBACK_ASKED, approved_docs, asked, readiness, run_report,  # noqa: E402
                    ran_said, session_step, sim_answer, sim_user, stated_seconds, step_limit, timeout_note, user_steps,
                    vendor_env, working_skill)


def sess(skill, *seen):
    return {"skill": skill, "seen": [skill, *seen]}


def nxt(skill, mode):
    return {"skill": skill, "mode": mode}


OK, ASKS = {"approves": True}, {"approves": False}  # the user's last message: approved / answered or asked
REPLY, RAN, NEW_STAGE = {"action": "reply"}, {"action": "reply", "ran": True}, {"action": "next_stage"}
# A session that ran a whole stage: every skill seen, which iteration 9's `seen` test resumed for ever (flow-F5).
LONG = sess("idea-refine", "spec-writing", "architecture-design", "pipeline-design", "build-planning", "build-setup")
# (what, dt next now, dt next before the session's last message, session, the user's last message, the one about to
# be sent, its text, expected (fresh, skill, slash))
CASES = [
    ("the first turn opens the run's first skill", nxt("idea-refine", "new"), {}, None, {}, {}, "I want…",
     (True, "idea-refine", True)),
    ("a skill still asking, no Draft yet, resumes", nxt("idea-refine", "new"), nxt("idea-refine", "new"),
     sess("idea-refine"), ASKS, REPLY, "", (False, "idea-refine", False)),
    ("a Draft at the session's own gate resumes", nxt("spec-writing", "gate"), nxt("spec-writing", "new"),
     sess("spec-writing"), ASKS, REPLY, "", (False, "spec-writing", False)),
    ("a requested fix at the gate goes back to the session that drafted it", nxt("spec-writing", "gate"),
     nxt("spec-writing", "gate"), sess("spec-writing"), ASKS, REPLY, "", (False, "spec-writing", False)),
    ("an approved gate hands on to a fresh session", nxt("architecture-design", "new"), nxt("spec-writing", "gate"),
     sess("spec-writing"), OK, REPLY, "Please continue.", (True, "architecture-design", True)),
    ("the same skill again after its gate opens a fresh session", nxt("pipeline-design", "extend"),
     nxt("pipeline-design", "gate"), sess("pipeline-design"), OK, REPLY, "", (True, "pipeline-design", True)),
    # Iteration 9 resumed here: the agent moved on in the approving turn, so architecture-design was "seen".
    ("approved, and the agent moved on in the same turn: still a fresh session for what it moved on to (flow-F5)",
     nxt("architecture-design", "gate"), nxt("spec-writing", "gate"), sess("spec-writing", "architecture-design"), OK,
     REPLY, "Yes, A.", (True, "architecture-design", True)),
    ("approval at a session's gate with nothing left to plan resumes", {"skill": None, "mode": "done"},
     nxt("build-setup", "gate"), sess("build-setup"), OK, REPLY, "", (False, "build-setup", False)),
    # Iteration 9 opened a fresh api-probe session here, mid-question ("What was 'A'?", interface-F11, flow-F6).
    ("dt next flips mid-question: the answer goes back to the session that asked", nxt("api-probe", "record"),
     nxt("architecture-design", "gate"), sess("architecture-design"), ASKS, REPLY, "Go with A.",
     (False, "architecture-design", False)),
    ("a Draft another session left, mid-question: the asking session resumes", nxt("pipeline-design", "gate"),
     nxt("test-planning", "new"), sess("test-planning"), ASKS, REPLY, "", (False, "test-planning", False)),
    ("a routed change after an approved gate opens its owner's Revise", nxt("architecture-design", "revise"),
     nxt("pipeline-design", "gate"), sess("pipeline-design"), OK, REPLY, "", (True, "architecture-design", True)),
    ("a probe run goes to a fresh api-probe session for its Record", nxt("api-probe", "record"),
     nxt("architecture-design", "gate"), sess("architecture-design"), ASKS, RAN, "I ran PB-01 access.",
     (True, "api-probe", True)),
    ("a probe run reported to api-probe's own session resumes it", nxt("api-probe", "record"),
     nxt("api-probe", "waiting"), sess("api-probe"), ASKS, RAN, "I ran it.", (False, "api-probe", False)),
    # Iteration 10 opened api-probe here, then build-planning, five sessions for one plan approval (H3).
    ("a probe run while another skill's gate is open stays in that skill's session", nxt("build-planning", "gate"),
     nxt("build-planning", "gate"), sess("build-planning"), ASKS, RAN, "I ran PB-01 and PB-03.",
     (False, "build-planning", False)),
    ("the gate approved, its session hands the run's Record on to a fresh api-probe", nxt("api-probe", "record"),
     nxt("build-planning", "gate"), sess("build-planning"), OK, REPLY, "Please continue.", (True, "api-probe", True)),
    ("a probe run at api-probe's own gate still goes to api-probe", nxt("api-probe", "gate"),
     nxt("architecture-design", "gate"), sess("architecture-design"), ASKS, RAN, "I ran it.", (True, "api-probe", True)),
    ("nothing left to plan: a new stage goes to idea-refine", {"skill": None, "mode": "done"},
     nxt("build-setup", "gate"), sess("build-setup"), OK, NEW_STAGE, "Approved. Next idea: …", (True, "idea-refine", True)),
    ("a new stage goes to idea-refine whatever dt next names", nxt("build-planning", "new"),
     nxt("build-setup", "gate"), LONG, OK, NEW_STAGE, "Approved. Next idea: …", (True, "idea-refine", True)),
    ("the second stage's spec after its approved brief: fresh, though a long session saw spec-writing",
     nxt("spec-writing", "new"), nxt("idea-refine", "gate"), LONG, OK, REPLY, "Please continue.",
     (True, "spec-writing", True)),
    ("nothing left to plan: a reply stays", {"skill": None, "mode": "done"}, nxt("build-setup", "gate"),
     sess("build-setup"), ASKS, REPLY, "", (False, "build-setup", False)),
    ("no answer from dt next: the session stays", {}, nxt("spec-writing", "gate"), sess("spec-writing"), OK, REPLY, "",
     (False, "spec-writing", False)),
    # Iteration 9 sent "/dev-team:test-planning Yes, start with api-probe…" (flow-F5).
    ("a fresh session whose message names another skill opens with the message alone, as that skill",
     nxt("test-planning", "new"), nxt("pipeline-design", "gate"), sess("pipeline-design"), OK, REPLY,
     "Yes, start with api-probe on PB-01.", (True, "api-probe", False)),
    ("a skill mentioned in passing isn't a next step: the prefix stays", nxt("pipeline-design", "new"),
     nxt("reference-intake", "gate"), sess("reference-intake"), OK, REPLY, "The reference-intake summaries look right.",
     (True, "pipeline-design", True)),
    ("a message naming the skill dt next names keeps the prefix", nxt("api-probe", "new"),
     nxt("pipeline-design", "gate"), sess("pipeline-design"), OK, REPLY, "Yes, start with api-probe.",
     (True, "api-probe", True)),
]


# PB-03's README from iteration 10's quant incremental run (Who runs what and Steps, as written).
PB03_README = """# PB-03: yahooquery returns AAPL's daily history since 1998 with splits and dividends

## Who runs what

| Check | Runner | Command |
|---|---|---|
| C1–C3 | agent | `uv run --script probes/PB-03-yahooquery-history/public.py shape` |
| C5 | agent | `uv run --script probes/PB-03-yahooquery-history/public.py burst` |
| C4 | user | `uv run --script probes/PB-03-yahooquery-history/probe.py compare` |

## Steps, in order

C4 reads `../PB-01-sharadar-coverage/out/aapl_stocks.json` and `aapl_actions.json`, written by PB-01's
step 2 (`collect`).

1. `uv run --script probes/PB-03-yahooquery-history/probe.py compare` — under a minute; one Yahoo request.

When you've finished, say "ran it", whether or not it failed. Don't paste the output.

## Files

- `probe.py` (yours), `public.py` (the agent's: it reads no environment at all), `yahoo.py` (the
  yahooquery call both use), `probe_kit.py` (the shared helper, copied in).
"""

STEPS_README = """## Who runs what

| Check | Runner | Command |
|---|---|---|
| C1 | agent | `python3 probes/PB-01-x/public.py` |
| C8 | user | `python3 probes/PB-01-x/probe.py bulk` |
| C3–C7 | user | `python3 probes/PB-01-x/probe.py checks` |

## Steps, in order

1. `python3 probes/PB-01-x/probe.py ping` — seconds.
2. `uv run probes/PB-01-x/probe.py bulk` — an hour.
3. `cd probes/PB-01-x && python3 probe.py checks > log.txt` — minutes.

## Files
- `probe.py` (yours to run)
"""
# (what, README text, expected argument lists)
STEPS = [
    ("the Steps section's commands, in its order", STEPS_README, [["ping"], ["bulk"], ["checks"]]),
    ("no Steps section: the table's", STEPS_README.split("## Steps")[0], [["bulk"], ["checks"]]),
    ("one plain command", "3. `cd probes/PB-01-sharadar && python3 probe.py` (about a minute).", [[]]),
    ("no README", "", [[]]),
    ("public.py in agent rows only: the user doesn't run it (flow-F4)", STEPS_README, [], "public.py"),
    ("the agent's `uv run public.py <step>` rows: not the user's either", "| C1, C2 | agent | "
     "`uv run probes/PB-03-y/public.py adjust` |\n| C3 | user | `uv run probes/PB-03-y/probe.py coverage` |", [], "public.py"),
    ("public.py in the user's Steps: run as given, with its step", "## Steps, in order\n\n1. "
     "`uv run probes/PB-03-y/public.py adjust` — a minute.\n2. `uv run probes/PB-03-y/probe.py coverage`\n",
     [["adjust"]], "public.py"),
    ("public.py in a user row of the table", "| C6 | user | `uv run probes/PB-03-y/public.py chart` |", [["chart"]],
     "public.py"),
    # Iteration 10 ran PB-03's probe.py 15 times with no step (H2): `uv run --script` wasn't read.
    ("`uv run --script <path> <step>`: the step is kept (iteration 10's PB-03)", PB03_README, [["compare"]]),
    ("PB-03's public.py, in agent rows only, isn't the user's", PB03_README, [], "public.py"),
    ("options before the script are skipped, their values too", "1. `uv run --with yahooquery==2.4.1 --script "
     "probes/PB-03-y/probe.py compare`\n2. `python3 -B probe.py checks`", [["compare"], ["checks"]]),
]


# A stage that is otherwise fully planned: the plan and CONSTRAINTS exist, its one stage has a milestone row.
FACTS = {"docs": {"docs/spec.md": "Approved", "docs/architecture.md": "Draft", "CONSTRAINTS.md": "Approved"},
         "plans": [{"dev_team": True, "kind": "plan"}], "stages": [{"id": "S1", "derived": "Planned"}],
         "roadmap": [{"id": "M1", "stage": "S1"}, {"id": "M2", "stage": "S1"}],
         "probes": [{"id": "PB-01", "kind": "ready"}, {"id": "PB-02", "kind": "ready"}, {"id": "PB-03", "kind": "answered"}]}
WAITS = {"skill": "api-probe", "mode": "waiting", "reason": "build-planning waits for probes: PB-01, PB-02, PB-03: run their checks, then say so"}
GATE = {"skill": "architecture-design", "mode": "gate", "reason": "docs/architecture.md is Draft: answer its questions or approve it"}


def why(facts=FACTS, nxt=None, probes_run=(), approved=()):
    return [r for r, _ in readiness(facts, 1, "incremental", nxt, probes_run, approved)]


def sim_fallback(agent_msg):
    """sim_user when every call fails (the CLI exits 1 with no output): (its answer, the error log's lines)."""
    import driver
    saved, driver.CLAUDE_BIN = driver.CLAUDE_BIN, "false"
    log = pathlib.Path(tempfile.mkdtemp(prefix="sim-errors-")) / "sim_errors.jsonl"
    try:
        u = sim_user({"persona": "p", "projects": {"x": {"facts": []}}}, {"project": "x", "mode": "all_at_once"}, [],
                     None, "", agent_msg, "", [], errlog=log, turn=7)
    finally:
        driver.CLAUDE_BIN = saved
    return u, [json.loads(l) for l in log.read_text().splitlines()]


ASKED_U, ASKED_LOG = sim_fallback("Two questions before I write it.\n\n1. Which start date?\n2. Price only, or fundamentals too?")
DRAFT_U, _ = sim_fallback("The spec is ready for review: docs/spec.md (Draft).")


# A CLI that keeps the prompt it is given and answers with a structured reply.
ECHO_CLI = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, pathlib, sys
    pathlib.Path(__file__).with_name("prompt.txt").write_text(sys.argv[sys.argv.index("-p") + 1])
    print(json.dumps({"structured_output": {"action": "reply", "message": "No.", "ran": False, "approves": False}}))
    """)


def sim_prompt():
    """The prompt sim_user sends, with the rl scenario's facts."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="sim-prompt-"))
    (d / "claude").write_text(ECHO_CLI)
    (d / "claude").chmod(0o755)
    scn = json.loads((HERE / "scenarios.json").read_text())
    saved, driver.CLAUDE_BIN = driver.CLAUDE_BIN, str(d / "claude")
    try:
        sim_user(scn, {"project": "rl", "mode": "all_at_once"}, scn["projects"]["rl"]["stages"], None, "",
                 "Would matching the scripted fish count as passing?", "", [])
    finally:
        driver.CLAUDE_BIN = saved
    return (d / "prompt.txt").read_text()


SIM_PROMPT = sim_prompt()


# Iteration 10's sim user, in prose (H4): taken as the message, with `ran` and `approves` read off its words.
PROSE_RAN = sim_answer({"result": "No, I didn't intend the local address. I re-ran PB-01, PB-02 and the PB-03 compare "
                                  "step. Ran it."})
PROSE_OK = sim_answer({"result": "Approved. On the eqdata split, take your recommendation."})
PROSE_NOT = sim_answer({"result": "I don't approve this yet: the start date should be 2011."})
STRUCTURED = sim_answer({"structured_output": {"action": "finish", "message": "Done.", "ran": False, "approves": True},
                         "result": "ignored"})


def proxied_sharadar():
    """start_vendors on the quant scenario (driver.ENV restored after): Sharadar's record, the .env vendor_env gives
    a probe naming its key and base URL, and what a request to api.sharadar.com through the closed proxy (a user
    run's environment) gets, with the fake's log line for it."""
    project = dict(json.loads((HERE / "scenarios.json").read_text())["projects"]["quant"], id="quant")
    out = pathlib.Path(tempfile.mkdtemp(prefix="vendors-"))
    saved = dict(driver.ENV)
    try:
        vendors, servers = driver.start_vendors(out, project, "selftest")
        env = vendor_env(["SHARADAR_API_KEY", "SHARADAR_BASE_URL", "NDL_BASE_URL"], vendors)
        run_env = vendors["sharadar"]["run_env"]
        proxy_url = run_env["HTTPS_PROXY"]
        ctx = __import__("ssl").create_default_context(cafile=run_env["SSL_CERT_FILE"])
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"https": proxy_url}),
                                             urllib.request.HTTPSHandler(context=ctx))
        try:
            code = opener.open(f"https://api.sharadar.com/v1.0/data/tickers?ticker=AAPL&api_key={env.get('SHARADAR_API_KEY')}",
                               timeout=20).status
        except Exception as e:
            code = repr(e)
        log = [json.loads(l) for l in (out / "vendor_sharadar.jsonl").read_text().splitlines()] if (out / "vendor_sharadar.jsonl").exists() else []
        for server in servers:
            server.shutdown()
        return vendors["sharadar"], env, code, log, len(servers)
    finally:
        driver.ENV.clear()
        driver.ENV.update(saved)


SHARADAR, SHARADAR_ENV, SHARADAR_CODE, SHARADAR_LOG, N_SERVERS = proxied_sharadar()


# Iteration 11's Q1: the agent's paced Yahoo check ran inside its turn past the 1,800 s limit; the uncaught timeout
# killed both quant runs. A CLI that starts a Bash call (a child that would sleep for a minute) and hangs.
HANG_CLI = textwrap.dedent("""\
    #!/usr/bin/env python3
    import json, subprocess, sys, time
    print(json.dumps({"type": "system", "subtype": "init", "skills": []}), flush=True)
    print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash",
          "input": {"command": "uv run --script probes/PB-03-yahoo/public.py paced"}}]}}), flush=True)
    child = subprocess.Popen(["sleep", "60"])
    open("child.pid", "w").write(str(child.pid))
    time.sleep(60)
    """)


def hung_turn():
    """agent_turn on HANG_CLI with a 2 s limit: (its reply, usage, seconds, whether the stream kept both lines, whether
    the child still runs)."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="hang-"))
    cli = d / "claude"
    cli.write_text(HANG_CLI)
    cli.chmod(0o755)
    saved = driver.CLAUDE_BIN, driver.TURN_TIMEOUT
    driver.CLAUDE_BIN, driver.TURN_TIMEOUT = str(cli), 2
    try:
        reply, usage, _, _, secs, *_ = driver.agent_turn(d, "sid", "hi", True, d / "agent_stream.jsonl", d, [], turn=5)
    finally:
        driver.CLAUDE_BIN, driver.TURN_TIMEOUT = saved
    lines = (d / "agent_stream.jsonl").read_text().splitlines()
    pid = int((d / "child.pid").read_text()) if (d / "child.pid").exists() else None
    time.sleep(0.2)
    alive = pid is not None and subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True,
                                               text=True).stdout.strip() not in ("", "Z")
    return reply, usage, secs, len(lines) == 3 and '"driver_turn"' in lines[0], alive


HUNG_REPLY, HUNG_USAGE, HUNG_SECS, HUNG_STREAM, HUNG_CHILD = hung_turn()


# Smoke 14's PB-02 README (iteration 12): a paced keyless batch is the user's step, its time stated.
PACED_README = """## Who runs what

| Check | Runner | Command |
|---|---|---|
| C1 | agent (and you, as a second network) | `uv run probes/PB-02-yahoo-crosscheck/public.py sample` |
| C2 | agent | `uv run probes/PB-02-yahoo-crosscheck/public.py members` |
| C3 | user | `uv run probes/PB-02-yahoo-crosscheck/public.py pace` |

## What it spends

Nothing paid, no key. `pace` makes about 21 batched history requests for 210 symbols from your IP over
up to 30 minutes.

## Steps, in order

1. `uv run probes/PB-02-yahoo-crosscheck/public.py sample`: ~1 min. This is the agent's check, run again
   from your network: on 2026-10-19 the agent's network got odd answers from Yahoo.
2. `uv run probes/PB-02-yahoo-crosscheck/public.py pace`: ≤ 30 min (it's timed; that's the check).
3. `python3 probes/PB-02-yahoo-crosscheck/probe.py bulk`: an hour, paced
   over 2 hours on a slow network.
"""
# A step that starts a child and outlives its limit.
SLOW_STEP = textwrap.dedent("""\
    import subprocess, sys, time
    child = subprocess.Popen(["sleep", "60"])
    open(sys.argv[1], "w").write(str(child.pid))
    print("started", flush=True)
    time.sleep(60)
    """)


def slow_step():
    """run_step on SLOW_STEP with a 2 s limit: (rc, stdout, seconds, whether the child still runs)."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="slow-step-"))
    (d / "slow.py").write_text(SLOW_STEP)
    t0 = time.time()
    rc, so, _ = driver.run_step([sys.executable, "-B", "slow.py", str(d / "child.pid")], d,
                                {"PATH": os.environ.get("PATH", "")}, 2)
    secs = time.time() - t0
    pid = int((d / "child.pid").read_text()) if (d / "child.pid").exists() else None
    time.sleep(0.2)
    alive = pid is not None and subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True,
                                               text=True).stdout.strip() not in ("", "Z")
    return rc, so, secs, alive


SLOW_RC, SLOW_OUT, SLOW_SECS, SLOW_CHILD = slow_step()
PACED = {"probe": "PB-02", "script": "probes/PB-02-y/public.py", "args": ["pace"], "rc": "timeout", "seconds": 2312.4,
         "stated_s": 1800.0, "limit_s": 2310}


RUNS = [{"probe": "PB-01", "script": "probes/PB-01-x/public.py", "args": [], "rc": 0, "stdout_tail": "secret rows"},
        {"probe": "PB-01", "script": "probes/PB-01-x/probe.py", "args": ["bulk"], "rc": 1, "stderr_tail": "Traceback"},
        {"probe": "PB-02", "script": None, "rc": None, "error": "no folder PB-02"}]
# (what, got, expected)
DECISIONS = [
    ("a Ready probe dt says build-planning waits for, never run, must be run (flow-F3)",
     why(nxt=WAITS, approved={"docs/architecture.md"}), ["build-planning waits for Ready probes never run: PB-01, PB-02"]),
    ("a probe the user already ran isn't asked for again", why(nxt=WAITS, probes_run={"PB-01", "PB-02"},
                                                               approved={"docs/architecture.md"}), []),
    ("no probe clause when dt next names another skill", why(nxt=GATE, approved={"docs/architecture.md"}), []),
    ("a Draft the user's message doesn't approve is re-asked", why(), ["docs/architecture.md is Draft"]),
    ("a Draft at the gate the message approves isn't re-asked (flow-F1)",
     why(approved=approved_docs({"approves": True}, GATE, [])), []),
    ("a message that approves nothing approves no doc", approved_docs({"approves": False}, GATE, ["docs/spec.md"]), set()),
    ("an approving message covers the docs this turn changed", approved_docs({"approves": True}, {}, ["docs/brief.md"]),
     {"docs/brief.md"}),
    ("the run report gives each step's exit code and no output",
     run_report(RUNS), "PB-01 public.py: exit code 0; PB-01 probe.py bulk: exit code 1; PB-02 (no folder): no folder PB-02"),
    ("nothing Ready: the report says nothing ran", run_report([]), "nothing ran: no probe was Ready"),
    # Smoke 12: the sim user's rewrite named PB-02's step when only PB-01's had run; the driver says what ran.
    ("the user's message says what ran in the driver's words", (ran_said(run_report(RUNS[:2])), ran_said(run_report([]))),
     ("I ran them as the READMEs say: PB-01 public.py: exit code 0; PB-01 probe.py bulk: exit code 1.",
      "Nothing ran: no probe was Ready.")),
    ("a reply ending on a question asks; one ending on a statement doesn't",
     (asked("Which start date?\n"), asked("Approved and marked.")), (True, False)),
    ("a failed sim-user call is tried three times, each logged with its exit code and output (flow-F7)",
     [(e["turn"], e["attempt"], e["rc"]) for e in ASKED_LOG], [(7, 1, 1), (7, 2, 1), (7, 3, 1)]),
    ("the fallback never approves in place of answers: it asks for the questions again",
     (ASKED_U["message"], ASKED_U["approves"], ASKED_U.get("fallback")), (FALLBACK_ASKED, False, True)),
    ("with no question pending, the fallback approves and says nothing more",
     (DRAFT_U["message"], DRAFT_U["approves"]), (FALLBACK_APPROVE, True)),
    ("a prose answer is the message, a reply that ran (H4)",
     (PROSE_RAN["action"], PROSE_RAN["message"][:24], PROSE_RAN["ran"], PROSE_RAN["approves"], PROSE_RAN["prose"]),
     ("reply", "No, I didn't intend the ", True, False, True)),
    ("a prose approval approves; a refused one doesn't", (PROSE_OK["approves"], PROSE_OK["ran"], PROSE_NOT["approves"]),
     (True, False, False)),
    ("structured output wins over the result text", (STRUCTURED["action"], STRUCTURED["message"]), ("finish", "Done.")),
    ("a broken JSON object is no answer (retried, then the fallback)", sim_answer({"result": '{"action": "reply", '}), None),
    ("the sim user is told it can't change its environment (H4)", "unset or exported a variable" in driver.SIM_LIMITS, True),
    # Iteration 11's rl user: "Fish tank: matching the scripted baseline counts as passing."
    ("the sim user keeps its facts' success bars and constraints, even when asked to relax one",
     (driver.SIM_BARS in SIM_PROMPT, "never lower or relax one" in driver.SIM_BARS, "If it asks, say no and keep the fact"
      in driver.SIM_BARS, "beats a random and a simple scripted baseline" in SIM_PROMPT), (True, True, True, True)),
    ("the rl facts agree with the persona on a rented GPU",
     ("rent a cloud GPU for a few dollars" in SIM_PROMPT, "rented cloud GPU for a few dollars" in SIM_PROMPT,
      "no budget" in SIM_PROMPT), (True, True, False)),
    ("a user step's stated time is read off its own line: ~1 min, ≤ 30 min, the longest of a wrapped item, none",
     [stated_seconds(PACED_README, s, a) for s, a in (("public.py", ["sample"]), ("public.py", ["pace"]),
                                                      ("probe.py", ["bulk"]), ("public.py", ["members"]))],
     [60.0, 1800.0, 7200.0, None]),
    ("a user step's limit: its stated time plus a quarter and a minute, within the default and the ceiling",
     (step_limit(None), step_limit(60.0), step_limit(1800.0), step_limit(4 * 3600.0)),
     (driver.USER_STEP_TIMEOUT, driver.USER_STEP_TIMEOUT, 2310, driver.USER_STEP_MAX)),
    ("the default limit is 600 s and the ceiling two hours", (driver.USER_STEP_TIMEOUT, driver.USER_STEP_MAX), (600, 7200)),
    ("a user step past its limit is stopped, its output so far kept", (SLOW_RC, SLOW_OUT, SLOW_SECS < 20),
     ("timeout", "started\n", True)),
    ("what the stopped step started is stopped with it", SLOW_CHILD, False),
    ("a stopped step is reported with how long it ran and the time its README gives it",
     (run_report([PACED]), run_report([dict(PACED, stated_s=None, seconds=601)])),
     ("PB-02 public.py pace: still running after 39 minutes, so I stopped it (its README gives it 30 minutes)",
      "PB-02 public.py pace: still running after 10 minutes, so I stopped it (its README gives it no time)")),
    ("Sharadar is served on its real hosts only: no base URL, no 127.0.0.1 server (H1)",
     (SHARADAR["url"], SHARADAR["server"], N_SERVERS), (None, None, 2)),
    ("a user run's .env gets the canary key and no base URL", SHARADAR_ENV, {"SHARADAR_API_KEY": "sk-canary-selftest",
                                                                             "NASDAQ_DATA_LINK_API_KEY": "sk-canary-selftest"}),
    ("api.sharadar.com through the closed proxy reaches the fake, which takes the canary",
     (SHARADAR_CODE, [(e["path"], e["key_ok"]) for e in SHARADAR_LOG]), (200, [("/v1.0/data/tickers", True)])),
    ("a turn past the limit is killed, marked timed_out with the call it was in, and says so (Q1)",
     (HUNG_USAGE.get("timed_out"), (HUNG_USAGE.get("last_call") or {}).get("name"), HUNG_REPLY.startswith("[agent turn timed out"),
      HUNG_SECS < 20), (True, "Bash", True, True)),
    ("the killed turn's stream so far stays in the log, after its turn marker", HUNG_STREAM, True),
    ("what the killed turn started is killed with it", HUNG_CHILD, False),
    ("the next turn is told it was stopped, what it was running, and to carry on",
     timeout_note(1820, HUNG_USAGE.get("last_call")),
     'Your last turn was still running after 30 minutes, so it was stopped (the last thing it ran: Bash {"command": '
     '"uv run --script probes/PB-03-yahoo/public.py paced"}). Whatever it was running was killed and its output is '
     'lost. Please carry on from where you were.'),
    ("a turn's working skill: the last its calls show", working_skill(["api-probe", "pipeline-design"], ["probes/x"],
                                                                     "api-probe", "api-probe"), ("pipeline-design", "calls")),
    ("no skill in its calls: the owner of most of the files it changed",
     working_skill([], ["docs/packages/a/pipelines.md", "docs/explained/a.md", "docs/spec.md", "docs/roadmap.md"],
                   "api-probe", "api-probe"), ("pipeline-design", "files")),
    ("nothing changed and no call: carried within the session, else its opening skill",
     (working_skill([], ["docs/roadmap.md"], "test-planning", "api-probe"), working_skill(["null-hypothesis-testing"], [], None, "test-planning")),
     (("test-planning", "carried"), ("test-planning", "opening"))),
]


def run(verbose=True):
    """The cases that came out wrong (empty when all hold)."""
    wrong = [(what, got, want) for what, n, b, s, l, u, m, want in CASES if (got := session_step(n, b, s, l, u, m)) != want]
    wrong += [(what, got, want) for what, text, want, *script in STEPS if (got := user_steps(text, *script)) != want]
    wrong += [(what, got, want) for what, got, want in DECISIONS if got != want]
    n = len(CASES) + len(STEPS) + len(DECISIONS)
    if verbose:
        print(f"selftest/sessions.py: {n - len(wrong)}/{n} cases as expected")
        for what, got, want in wrong:
            print(f"  WRONG {what}: {got}, expected {want}")
    return wrong


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
