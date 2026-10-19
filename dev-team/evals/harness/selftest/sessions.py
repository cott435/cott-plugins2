#!/usr/bin/env python3
"""Cases for the driver's own decisions: driver.session_step (when a turn resumes the current agent session and when
it opens a fresh one, for which skill, and whether with `/dev-team:<skill>`), driver.user_steps (the probe.py and
public.py steps a probe's README gives the user, run in order on "ran it"), driver.readiness's probe and approval
clauses, run_report (what the simulated user is told after its run), sim_user's fallback when every call fails and
sim_answer's when it answers in prose, working_skill (the skill a turn worked in), and start_vendors' proxied Sharadar
(no base URL; the closed proxy serves api.sharadar.com with the canary key). No dt, no model calls; the dry run runs
this too.

Usage: sessions.py   prints one line per case; exit 1 if any case comes out wrong
"""
import json, pathlib, sys, tempfile, urllib.request

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import driver  # noqa: E402
from driver import (FALLBACK_APPROVE, FALLBACK_ASKED, approved_docs, asked, readiness, run_report,  # noqa: E402
                    ran_said, session_step, sim_answer, sim_user, user_steps, vendor_env, working_skill)


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
    ("Sharadar is served on its real hosts only: no base URL, no 127.0.0.1 server (H1)",
     (SHARADAR["url"], SHARADAR["server"], N_SERVERS), (None, None, 2)),
    ("a user run's .env gets the canary key and no base URL", SHARADAR_ENV, {"SHARADAR_API_KEY": "sk-canary-selftest",
                                                                             "NASDAQ_DATA_LINK_API_KEY": "sk-canary-selftest"}),
    ("api.sharadar.com through the closed proxy reaches the fake, which takes the canary",
     (SHARADAR_CODE, [(e["path"], e["key_ok"]) for e in SHARADAR_LOG]), (200, [("/v1.0/data/tickers", True)])),
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
