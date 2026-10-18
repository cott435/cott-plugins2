#!/usr/bin/env python3
"""Test double for the `claude` CLI, so driver.py's loop can be exercised with no model calls.

- `claude plugin validate <dir>` → ok.
- Agent turn (`-p … --output-format stream-json`): replays dt's sample project (scripts/tests/fixtures/quant)
  into the cwd one planning layer per turn (dryrun.LAYERS, minus the build), and prints stream-json with a
  Skill call (plus one Agent call per reference file on the reference-intake layer) and a cumulative
  total_cost_usd, like the real CLI.
- Simulated user (`-p … --output-format json`): always answers {"action": "finish", "message": "Approved."}.
- FAKE_MODE=build (build_driver.py): each agent turn replays a good build of the target fixture in the cwd up to
  its next stop (dryrun_build.Replay, arm from BUILD_ARM, through the run's staged dt): reservations, worktrees,
  claims, landings and reviews, as the build skill's driver and its agents would. The stream shows the build
  skill and one Agent call per half.

Usage: CLAUDE_BIN=evals/harness/fake_claude.py python3 evals/harness/driver.py quant-all-at-once <out>
       CLAUDE_BIN=evals/harness/fake_claude.py FAKE_MODE=build python3 evals/harness/build_driver.py minilab A3 <out>
"""
import json, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

args = sys.argv[1:]
if args[:2] == ["plugin", "validate"]:
    print("✔ Validation passed")
    sys.exit(0)
if args[:1] == ["--version"]:
    print("0.0.0 (fake_claude)")
    sys.exit(0)


def build_turn():
    """One driver turn of a build: dryrun_build.Replay up to its next stop, through the run's staged dt."""
    from dryrun_build import Replay  # noqa: E402
    proj = pathlib.Path(".").resolve()
    staged = proj.parent / "plugin" / "dev-team" / "scripts" / "dt.py"
    rp = Replay(proj.parent, os.environ.get("BUILD_ARM", "A3"), **({"dt": staged} if staged.exists() else {}))
    stop = rp.turn()
    sid = "00000000-0000-4000-8000-000000000000"
    print(json.dumps({"type": "system", "subtype": "init", "skills": ["dev-team:build"], "session_id": sid,
                      "agents": ["tester", "implementer", "reviewer"], "claude_code_version": "0.0.0 (fake)"}))
    content = [{"type": "tool_use", "name": "Skill", "input": {"skill": "dev-team:build"}}]
    for e in rp.events:
        task, role = (e.split(":")[0].split() + ["", ""])[:2]
        if role in ("tester", "implementer", "solo"):
            content.append({"type": "tool_use", "name": "Agent", "input": {
                "subagent_type": "tester" if role == "tester" else "implementer", "description": f"{task} {role}",
                "isolation": "worktree", "run_in_background": True, "prompt": f"(fake) {e}"}})
    print(json.dumps({"type": "assistant", "message": {"content": content}}))
    text = {"contract-change": "Build M1 stopped: a CONTRACT-CHANGE escalation needs your decision. Change the contract?",
            "exit": "M1 is built: every task landed and the exit review is recorded. Merge build/M1?",
            }.get(stop, f"Build M1 stopped ({stop}).")
    if rp.problems:
        text += " Problems: " + "; ".join(x.splitlines()[0] for x in rp.problems[:4])
    print(json.dumps({"type": "result", "result": f"(fake) {len(rp.events)} events. {text}", "session_id": sid,
                      "total_cost_usd": 0.5, "duration_ms": 1, "num_turns": 1, "usage": {"output_tokens": 100},
                      "permission_denials": []}))


fmt0 = args[args.index("--output-format") + 1] if "--output-format" in args else "text"
if os.environ.get("FAKE_MODE") == "build" and fmt0 == "stream-json":
    build_turn()
    sys.exit(0)

from dryrun import FIXTURE, LAYERS, copy_layer, intake_agents  # noqa: E402
fmt = args[args.index("--output-format") + 1] if "--output-format" in args else "text"
if fmt == "json":
    print(json.dumps({"type": "result", "result": json.dumps({"action": "finish", "message": "Approved."})}))
    sys.exit(0)

state = pathlib.Path(".git/fake_turn")
n = int(state.read_text()) if state.exists() else 0
layers = [l for l in LAYERS if l[0]]  # planning layers only: a planning run never builds
skill, paths = layers[min(n, len(layers) - 1)]
if n < len(layers):
    copy_layer(FIXTURE, pathlib.Path("."), paths)
state.write_text(str(n + 1))
agents = intake_agents(pathlib.Path(".")) if skill == "reference-intake" else []
print(json.dumps({"type": "system", "subtype": "init", "skills": [f"dev-team:{l[0]}" for l in layers],
                  "mcp_servers": [{"name": "evalperm", "status": "connected"}]}))
print(json.dumps({"type": "system", "subtype": "hook_response", "hook_event_name": "SessionStart"}))
print(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "tool_use", "name": "Skill", "input": {"skill": f"dev-team:{skill}"}},
    {"type": "tool_use", "name": "Write", "input": {}},
    *({"type": "tool_use", "name": "Agent", "input": a} for a in agents)]}}))
# A subagent's own tool calls carry parent_tool_use_id; the driver must not count them as launches.
for a in agents:
    print(json.dumps({"type": "assistant", "parent_tool_use_id": "toolu_fake", "message": {"content": [
        {"type": "tool_use", "name": "Read", "input": {}}]}}))
print(json.dumps({"type": "result", "result": f"(fake) wrote the {skill} layer: {', '.join(paths)}. Approve?",
                  "total_cost_usd": 0.1 * (n + 1), "duration_ms": 1, "num_turns": 1, "usage": {"output_tokens": 10}}))
