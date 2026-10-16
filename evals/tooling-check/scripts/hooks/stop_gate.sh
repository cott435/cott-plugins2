#!/usr/bin/env bash
# Stop hook (becomes SubagentStop inside a subagent): block finishing until the gate passes.
#   stop_gate.sh collect|gate|full
# Blocks by printing {"decision": "block", "reason": ...} and exiting 0, not by exit 2:
# Claude Code treats an exit-2 Stop hook whose stderr mentions a missing file
# ("No such file or directory") as non-blocking, and test output often does.
# Loop guard: after MAX_TRIES failed attempts we let it stop and tell the user.
mode="${1:-gate}"
MAX_TRIES=3
source "$(dirname "$0")/project_root.sh"
cd "$root" || exit 1
id=$(jq -r '.agent_id // .session_id // "main"' <<<"$input")
counter=".claude/.stop_attempts_${id}"
mkdir -p .claude
tries=$(cat "$counter" 2>/dev/null || echo 0)

if out=$(bash scripts/check.sh "$mode" 2>&1); then
  rm -f "$counter"
  exit 0
fi

tries=$((tries + 1))
echo "$tries" > "$counter"
if [ "$tries" -gt "$MAX_TRIES" ]; then
  rm -f "$counter"
  # Exit 0 output is not shown anywhere unless it is a systemMessage.
  jq -n --arg msg "Gate '$mode' still failing after $MAX_TRIES attempts; stopping so a human can look." \
    '{systemMessage: $msg}'
  exit 0
fi

reason="Gate '$mode' failed (attempt $tries/$MAX_TRIES). Fix these before finishing:
$(echo "$out" | tail -60)"
jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
exit 0
