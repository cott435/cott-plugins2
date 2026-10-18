#!/usr/bin/env python3
"""Test double for the `claude` CLI as judge_prompt.py's judge calls it (`-p <prompt> --output-format json`), for
selftest/judge.py. It counts its calls in FAKE_JUDGE_STATE and, run one call at a time, answers:

- calls 1 and 3: a malformed reply (call 1 has no JSON; call 3 is JSON with no rubric for Set B), so the runner retries;
- every other call: valid verdict number v (1, 2, ...), for repeat r = (v + 1) // 2. Set-1's content items all score
  r + 1, set-2's all score 3; Set A's structure items score 4 and Set B's 3 (a position effect of exactly 1).
- FAKE_JUDGE_FAIL=1: every call is malformed.

The rubric items are the prompt's own Content and Structure lines, so a filled prompt drives the shape.
"""
import json, os, pathlib, re, sys

args = sys.argv[1:]
prompt = args[args.index("-p") + 1]
state = pathlib.Path(os.environ["FAKE_JUDGE_STATE"])
calls = json.loads(state.read_text()) if state.exists() else {"calls": 0, "valid": 0}
calls["calls"] += 1
n = calls["calls"]


def reply(result):
    state.write_text(json.dumps(calls))
    print(json.dumps({"type": "result", "result": result}))
    sys.exit(0)


if os.environ.get("FAKE_JUDGE_FAIL") or n == 1:
    reply("I read both sets; Set A is better.")
if n == 3:
    reply(json.dumps({"winner": "A", "rubric": {"A": {}}}))
calls["valid"] += 1
rep = (calls["valid"] + 1) // 2
content = re.search(r"^Content: (.*)$", prompt, re.M).group(1).split(", ")
structure = re.search(r"^Structure: (.*)$", prompt, re.M).group(1).split(", ")
set_a_is_1 = re.search(r"^- Set A: (.*)$", prompt, re.M).group(1).endswith("set-1")


def block(c, s):
    cs, ss = float(c), float(s)
    return {"content": {k: c for k in content}, "structure": {k: s for k in structure},
            "content_score": cs, "structure_score": ss, "overall_score": cs + ss}


one, two = rep + 1, 3
a, b = (block(one, 4), block(two, 3)) if set_a_is_1 else (block(two, 4), block(one, 3))
winner = "A" if a["overall_score"] >= b["overall_score"] else "B"
reply("```json\n" + json.dumps({"winner": winner, "reasoning": "fake", "rubric": {"A": a, "B": b}}) + "\n```")
