#!/usr/bin/env python3
"""Cases for the driver's own decisions: driver.session_step (when a turn resumes the current agent session and when
it opens a fresh one, and for which skill) and driver.user_steps (the probe.py steps a probe's README gives the user,
run in order on "ran it"). No dt, no model calls; the dry run runs this too.

Usage: sessions.py   prints one line per case; exit 1 if any case comes out wrong
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from driver import session_step, user_steps  # noqa: E402


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


def run(verbose=True):
    """The cases that came out wrong (empty when all hold)."""
    wrong = [(what, got, want) for what, n, b, s, a, want in CASES if (got := session_step(n, b, s, a)) != want]
    wrong += [(what, got, want) for what, text, want in STEPS if (got := user_steps(text)) != want]
    if verbose:
        print(f"selftest/sessions.py: {len(CASES) + len(STEPS) - len(wrong)}/{len(CASES) + len(STEPS)} cases as expected")
        for what, got, want in wrong:
            print(f"  WRONG {what}: {got}, expected {want}")
    return wrong


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
