#!/usr/bin/env python3
"""Test double for the `claude` CLI, so driver.py's loop can be exercised with no model calls.

- `claude plugin validate <dir>` → ok.
- Agent turn (`-p … --output-format stream-json`): replays dt's sample project (scripts/tests/fixtures/quant)
  into the cwd one planning layer per turn (dryrun.LAYERS, minus the build), and prints stream-json with a
  Skill call (plus one Agent call per reference file on the reference-intake layer) and a cumulative
  total_cost_usd, like the real CLI.
- Simulated user (`-p … --output-format json`): always answers {"action": "finish", "message": "Approved."}.
- FAKE_MODE=build (build_driver.py): each agent turn replays one checkpoint segment of a good build of the
  target fixture into the cwd (dryrun_build.Replayer, arm from BUILD_ARM): worktree-* branches, merges, gate
  files and ticks, as the arm's orchestrator would. The stream shows one Workflow call per segment for
  parallel arms and one Agent call per builder job.

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
    """One orchestrator turn of a build: the next checkpoint segment, replayed."""
    from dryrun_build import Replayer  # noqa: E402
    arm = os.environ.get("BUILD_ARM", "A3")
    rp = Replayer(pathlib.Path(".").resolve(), arm)
    res = rp.run_segment()
    state = rp.state()
    jobs = [e for e in res["events"]]
    print(json.dumps({"type": "system", "subtype": "init", "skills": [], "agents": ["tester", "implementer", "reviewer", "check", "merge"],
                      "mcp_servers": [{"name": "evalperm", "status": "connected"}], "session_id": "00000000-0000-4000-8000-000000000000"}))
    content = []
    if rp.arm["dispatch"] == "parallel" and jobs:
        content.append({"type": "tool_use", "name": "Workflow", "input": {"script": f"// fake: segment {res['segment'] + 1}\n" + "\n".join(jobs)}})
    for e in jobs:
        branch = e.split()[0]
        content.append({"type": "tool_use", "name": "Agent", "input": {
            "subagent_type": "implementer" if "tester" not in branch else "tester", "description": e,
            "isolation": "worktree" if branch.startswith("worktree-") else None, "prompt": f"(fake) {e}"}})
    print(json.dumps({"type": "assistant", "message": {"content": content}}))
    done = "Milestone exit checkpoint reached; every task is ticked." if res["done"] else "Checkpoint reached; approve to continue?"
    print(json.dumps({"type": "result", "result": f"(fake) segment {res['segment'] + 1}/{res['segments']}: "
                      f"{len(jobs)} jobs ({'; '.join(jobs[:6])}{' …' if len(jobs) > 6 else ''}). {done}",
                      "total_cost_usd": 0.5 * state.get("segment", 1), "duration_ms": 1, "num_turns": 1,
                      "usage": {"output_tokens": 100}}))


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
