#!/usr/bin/env python3
"""Cases for the driver's own decisions: driver.session_step (when a turn resumes the current agent session and when
it opens a fresh one, and for which skill), driver.user_steps (the probe.py steps a probe's README gives the user,
run in order on "ran it"), driver.readiness's probe and approval clauses, and run_report (what the simulated user is
told after its run). No dt, no model calls; the dry run runs this too.

Usage: sessions.py   prints one line per case; exit 1 if any case comes out wrong
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from driver import approved_docs, readiness, run_report, session_step, user_steps  # noqa: E402


def sess(skill, *seen):
    return {"skill": skill, "seen": [skill, *seen]}


def nxt(skill, mode):
    return {"skill": skill, "mode": mode}


# (what, dt next now, dt next before the session's last message, session, user action, expected (fresh, skill))
CASES = [
    ("the first turn opens the run's first skill", nxt("idea-refine", "new"), {}, None, None, (True, "idea-refine")),
    ("a skill still asking, no Draft yet, resumes", nxt("idea-refine", "new"), nxt("idea-refine", "new"),
     sess("idea-refine"), "reply", (False, "idea-refine")),
    ("a Draft at the session's own gate resumes", nxt("spec-writing", "gate"), nxt("spec-writing", "new"),
     sess("spec-writing"), "reply", (False, "spec-writing")),
    ("an approved gate hands on to a fresh session", nxt("architecture-design", "new"), nxt("spec-writing", "gate"),
     sess("spec-writing"), "reply", (True, "architecture-design")),
    ("the same skill again after its gate opens a fresh session", nxt("pipeline-design", "extend"),
     nxt("pipeline-design", "gate"), sess("pipeline-design"), "reply", (True, "pipeline-design")),
    ("a skill the agent moved on to keeps the session through its gate", nxt("architecture-design", "gate"),
     nxt("spec-writing", "gate"), sess("spec-writing", "architecture-design"), "reply", (False, "architecture-design")),
    ("a Draft another session left opens a fresh session for its owner", nxt("pipeline-design", "gate"),
     nxt("test-planning", "new"), sess("test-planning"), "reply", (True, "pipeline-design")),
    ("a routed change opens its owner's Revise", nxt("architecture-design", "revise"), nxt("pipeline-design", "gate"),
     sess("pipeline-design"), "reply", (True, "architecture-design")),
    ("nothing left to plan: a new stage goes to idea-refine", {"skill": None, "mode": "done"},
     nxt("build-setup", "gate"), sess("build-setup"), "next_stage", (True, "idea-refine")),
    ("nothing left to plan: a reply stays", {"skill": None, "mode": "done"}, nxt("build-setup", "gate"),
     sess("build-setup"), "reply", (False, "build-setup")),
    ("no answer from dt next: the session stays", {}, nxt("spec-writing", "gate"), sess("spec-writing"), "reply",
     (False, "spec-writing")),
]


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
]


def run(verbose=True):
    """The cases that came out wrong (empty when all hold)."""
    wrong = [(what, got, want) for what, n, b, s, a, want in CASES if (got := session_step(n, b, s, a)) != want]
    wrong += [(what, got, want) for what, text, want in STEPS if (got := user_steps(text)) != want]
    wrong += [(what, got, want) for what, got, want in DECISIONS if got != want]
    n = len(CASES) + len(STEPS) + len(DECISIONS)
    if verbose:
        print(f"selftest/sessions.py: {n - len(wrong)}/{n} cases as expected")
        for what, got, want in wrong:
            print(f"  WRONG {what}: {got}, expected {want}")
    return wrong


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
