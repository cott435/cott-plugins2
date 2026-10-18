#!/usr/bin/env bash
# Stop hook (becomes SubagentStop inside a subagent): block finishing until the gate passes.
#   stop_gate.sh collect|gate|full [--warn]
# Blocks by printing {"decision": "block", "reason": ...} and exiting 0, not by exit 2:
# Claude Code treats an exit-2 Stop hook whose stderr mentions a missing file
# ("No such file or directory") as non-blocking, and test output often does.
# Loop guard: after MAX_TRIES failed attempts the agent may stop. Outside a dt build the last
# block tells it to start its report with "GATE FAILED", because that report is all the parent
# sees: a SubagentStop systemMessage doesn't reach the main view (checked live, Claude Code 2.1.292).
# --warn never blocks: a failing gate only leaves a systemMessage (CONSTRAINTS.md says when).
# For gate and full, .claude/.check_pkg (written by dt claim, optional) holds the task's package
# and becomes --pkg.
# In a dt build, .claude/.dt (written by dt claim) holds the path to dt.py: an agent whose claim
# has an escalation record (dt escalate) may stop without the gate, and every gate result is
# recorded with `dt build verdict`, which dt land reuses when the tree hasn't changed since.
mode=gate
warn=0
for a in "$@"; do
  case "$a" in
    --warn) warn=1 ;;
    *) mode="$a" ;;
  esac
done
MAX_TRIES=3
source "$(dirname "$0")/project_root.sh"

# Without jq there is no safe way to write the JSON answer: block the plain way (exit 2,
# fixed message) rather than let the agent stop on a gate nobody ran.
say_block() {
  if command -v jq >/dev/null 2>&1; then
    jq -n --arg reason "$1" '{decision: "block", reason: $reason}'
    exit 0
  fi
  echo "stop_gate: the gate failed and jq is not installed to report it; install jq, then run scripts/check.sh $mode" >&2
  exit 2
}
say_user() {
  command -v jq >/dev/null 2>&1 && jq -n --arg msg "$1" '{systemMessage: $msg}'
  exit 0
}

cd "$root" || say_block "stop_gate: cannot enter the project root $root"
id=$(jq -r '.agent_id // .session_id // "main"' <<<"$input" 2>/dev/null | tr -cd 'A-Za-z0-9_-')
counter=".claude/.stop_attempts_${id:-main}"
mkdir -p .claude

dt=""
[ -s .claude/.dt ] && dt=$(head -n 1 .claude/.dt)
if [ -n "$dt" ] && python3 "$dt" build escalated >/dev/null 2>&1; then
  rm -f "$counter"
  exit 0
fi

pkg_args=()
if [ "$mode" != collect ] && [ -s .claude/.check_pkg ]; then
  pkg_args=(--pkg "$(tr -cd 'A-Za-z0-9_.-' <.claude/.check_pkg)")
fi

out=$(bash scripts/check.sh "$mode" ${pkg_args[@]+"${pkg_args[@]}"} 2>&1)
rc=$?
[ -n "$dt" ] && python3 "$dt" build verdict --mode "$mode" --rc "$rc" >/dev/null 2>&1
if [ "$rc" -eq 0 ]; then
  rm -f "$counter"
  exit 0
fi

if [ "$warn" = 1 ]; then
  say_user "Gate '$mode' is failing (warn only, not blocking). Run scripts/check.sh $mode to see why."
fi

tries=$(cat "$counter" 2>/dev/null || echo 0)
[[ $tries =~ ^[0-9]+$ ]] || tries=0
tries=$((tries + 1))
echo "$tries" >"$counter"
if [ "$tries" -gt "$MAX_TRIES" ]; then
  rm -f "$counter"
  say_user "Gate '$mode' still failing after $MAX_TRIES attempts; the agent stopped so a human can look. Run scripts/check.sh $mode."
fi

last=""
if [ "$tries" -eq "$MAX_TRIES" ] && [ -n "$dt" ]; then
  last="
This was the last attempt. If you can't fix it now, finish anyway with your status line:
the failing verdict is recorded, and dt land rejects the task with it."
elif [ "$tries" -eq "$MAX_TRIES" ]; then
  last="
This was the last attempt. If you can't fix it now, finish anyway and start your report with
\"GATE FAILED: scripts/check.sh $mode\", then list what is still failing."
fi
say_block "Gate '$mode' failed (attempt $tries/$MAX_TRIES). Fix these before finishing:
$(echo "$out" | tail -60)$last"
