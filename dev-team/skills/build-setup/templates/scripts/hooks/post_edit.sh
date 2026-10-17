#!/usr/bin/env bash
# PostToolUse hook (Edit|Write|MultiEdit): run the instant checks on the file just edited.
# ruff --fix and ruff format may rewrite the file; the agent re-reads it before the next edit.
# Exit 2 = show stderr to the agent so it fixes the problem right away. The edit already
# happened, so a broken input can only be reported (exit 1); the Stop gate still catches it.
source "$(dirname "$0")/project_root.sh"
cd "$root" || exit 1
if ! file=$(jq -r '.tool_input.file_path // empty' <<<"$input"); then
  echo "post_edit: could not read the hook input (is jq installed?)" >&2
  exit 1
fi
[ -z "$file" ] && exit 0
out=$(bash scripts/check.sh fast "$file" 2>&1) || {
  echo "$out" >&2
  exit 2
}
exit 0
