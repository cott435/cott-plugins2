#!/usr/bin/env python3
"""Test double for the `claude` CLI, so driver.py's loop can be exercised with no model calls.

- `claude plugin validate <dir>` → ok.
- Agent turn (`-p … --output-format stream-json`): replays dt's sample project (scripts/tests/fixtures/quant)
  into the cwd one planning layer per turn (dryrun.LAYERS, minus the build), and prints stream-json with a
  Skill call (plus one Agent call per reference file on the reference-intake layer) and a cumulative
  total_cost_usd, like the real CLI.
- Simulated user (`-p … --output-format json`): always answers {"action": "finish", "message": "Approved."}.

Usage: CLAUDE_BIN=evals/harness/fake_claude.py python3 evals/harness/driver.py quant-all-at-once <out>
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dryrun import FIXTURE, LAYERS, copy_layer, intake_agents  # noqa: E402

args = sys.argv[1:]
if args[:2] == ["plugin", "validate"]:
    print("✔ Validation passed")
    sys.exit(0)
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
