#!/usr/bin/env bash
# PreToolUse hook: restrict which files an agent may edit.
#   path_guard.sh deny  GLOB...   block edits to files matching any GLOB
#   path_guard.sh allow GLOB...   block edits to files NOT matching any GLOB
# GLOBs are relative to the project root; * also matches across /.
# Reads the hook JSON on stdin. Exit 2 = block the tool call; stderr goes to the agent.
# Fails closed: if the input can't be read, the edit is blocked.
mode="$1"; shift
source "$(dirname "$0")/project_root.sh"
if ! file=$(jq -r '.tool_input.file_path // empty' <<<"$input"); then
  echo "BLOCKED: path_guard could not read the hook input (is jq installed?)" >&2
  exit 2
fi
[ -z "$file" ] && exit 0
if [[ $file == */../* || $file == */.. ]]; then
  echo "BLOCKED: use a path without '..' (tried: $file)" >&2
  exit 2
fi
rel="${file#"$root"/}"

shopt -s nocasematch   # macOS file systems are case-insensitive: Tests/ is tests/
match=0
for g in "$@"; do
  # shellcheck disable=SC2053  # unquoted on purpose: glob match
  [[ $rel == $g ]] && match=1
  # Deny also matches the absolute path, in case the root is spelled differently
  # (symlink, /tmp vs /private/tmp). Over-blocking is the safe direction.
  [[ $mode == deny && $file == */$g ]] && match=1
done

if [ "$mode" = deny ] && [ $match = 1 ]; then
  echo "BLOCKED: $rel is protected and cannot be edited by this agent." >&2
  exit 2
fi
if [ "$mode" = allow ] && [ $match = 0 ]; then
  echo "BLOCKED: this agent may only edit: $*  (tried: $rel)" >&2
  exit 2
fi
exit 0
