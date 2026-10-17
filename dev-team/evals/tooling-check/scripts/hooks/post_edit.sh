#!/usr/bin/env bash
# PostToolUse hook (Edit|Write): run the instant checks on the file just edited.
# Exit 2 = show stderr to the agent so it fixes the problem right away.
source "$(dirname "$0")/project_root.sh"
cd "$root" || exit 1
file=$(jq -r '.tool_input.file_path // empty' <<<"$input") || exit 1
[ -z "$file" ] && exit 0
out=$(bash scripts/check.sh fast "$file" 2>&1) || {
  echo "$out" >&2
  exit 2
}
exit 0
