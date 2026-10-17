#!/usr/bin/env python3
"""Stdio MCP server whose one tool answers Claude Code permission prompts during a headless run.

The plugin's PreToolUse guard answers "ask" for tests/fixtures/**/expected.json (oracle files need the user's
yes). A headless `claude -p` has nobody to ask, so the driver passes `--permission-prompt-tool
mcp__evalperm__approve`: the simulated user approves expected outputs at test-planning's review gate, and this
stands in for the matching click. Every prompt is logged (EVALPERM_LOG, JSON lines) so the grader can count them.
Requests the guard denies outright (tasks/archive/**) never reach it.

Stdlib only; newline-delimited JSON-RPC 2.0 on stdin/stdout.
"""
import json, os, sys, time

LOG = os.environ.get("EVALPERM_LOG")
TOOL = {"name": "approve", "description": "Answer a permission prompt for the evaluation's simulated user (always allows; logged).",
        "inputSchema": {"type": "object", "properties": {"tool_name": {"type": "string"}, "input": {"type": "object"},
                                                         "tool_use_id": {"type": "string"}}, "required": ["tool_name", "input"]}}


def handle(req):
    method, params = req.get("method"), req.get("params") or {}
    if method == "initialize":
        return {"protocolVersion": params.get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}},
                "serverInfo": {"name": "evalperm", "version": "1"}}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": [TOOL]}
    if method == "tools/call":
        args = params.get("arguments") or {}
        if LOG:
            with open(LOG, "a") as f:
                f.write(json.dumps({"time": time.time(), "tool_name": args.get("tool_name"),
                                    "path": (args.get("input") or {}).get("file_path")}) + "\n")
        decision = {"behavior": "allow", "updatedInput": args.get("input") or {}}
        return {"content": [{"type": "text", "text": json.dumps(decision)}]}
    raise KeyError(method)


for line in sys.stdin:
    try:
        req = json.loads(line)
    except ValueError:
        continue
    if "id" not in req:
        continue  # a notification (e.g. notifications/initialized)
    try:
        resp = {"jsonrpc": "2.0", "id": req["id"], "result": handle(req)}
    except KeyError:
        resp = {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": f"unknown method {req.get('method')}"}}
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()
