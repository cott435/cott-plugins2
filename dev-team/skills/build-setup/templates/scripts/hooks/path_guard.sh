#!/usr/bin/env bash
# PreToolUse hook: restrict which files an agent may touch.
#   path_guard.sh deny  GLOB...        block files matching any GLOB
#   path_guard.sh deny  --protected    block the protected list (scripts/check.sh protected)
#   path_guard.sh allow GLOB...        block files NOT matching any GLOB
#   path_guard.sh writes               block files outside the task's Writes: list, which the
#                                      orchestrator puts in .claude/.task_writes (one path or glob a
#                                      line; a trailing / means the folder). No file: no limit
# GLOBs are relative to the project root; * also matches across /.
# Reads the hook JSON on stdin. Exit 2 = block the tool call; stderr goes to the agent.
# Fails closed: if the input or the protected list can't be read, the call is blocked.
mode="${1:-}"; shift
if [ "$mode" != deny ] && [ "$mode" != allow ] && [ "$mode" != writes ]; then
  cat >/dev/null
  echo "BLOCKED: path_guard mode must be allow, deny or writes (got: '$mode')" >&2
  exit 2
fi
source "$(dirname "$0")/project_root.sh"
if ! file=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' <<<"$input"); then
  echo "BLOCKED: path_guard could not read the hook input (is jq installed?)" >&2
  exit 2
fi
[ -z "$file" ] && exit 0
if [[ $file == */../* || $file == */.. || $file == ../* ]]; then
  echo "BLOCKED: use a path without '..' (tried: $file)" >&2
  exit 2
fi

globs=()
scope="this agent"
if [ "$mode" = writes ]; then
  [ -s "$root/.claude/.task_writes" ] || exit 0
  while IFS= read -r line; do
    line="${line%%[[:space:]]}"
    [ -z "$line" ] && continue
    [[ $line == */ ]] && line="${line}**"
    globs+=("$line")
  done <"$root/.claude/.task_writes"
  mode=allow
  scope="this task's Writes: (.claude/.task_writes)"
  set --
fi
for g in "$@"; do
  if [ "$g" = --protected ]; then
    if ! list=$(bash "$root/scripts/check.sh" protected) || [ -z "$list" ]; then
      echo "BLOCKED: path_guard could not read the protected list from scripts/check.sh" >&2
      exit 2
    fi
    while IFS= read -r line; do [ -n "$line" ] && globs+=("$line"); done <<<"$list"
  else
    globs+=("$g")
  fi
done

# Path relative to the root, trying the root as given and with symlinks resolved
# (/tmp vs /private/tmp). The file may not exist yet; its directory usually does.
rel="${file#"$root"/}"
if [ "$rel" = "$file" ]; then
  root_p=$(cd "$root" 2>/dev/null && pwd -P)
  dir_p=$(cd "$(dirname "$file")" 2>/dev/null && pwd -P)
  [ -n "$root_p" ] && [ -n "$dir_p" ] && rel="${dir_p}/$(basename "$file")" && rel="${rel#"$root_p"/}"
fi

shopt -s nocasematch   # macOS file systems are case-insensitive: Tests/ is tests/
match=0
for g in ${globs[@]+"${globs[@]}"}; do
  # shellcheck disable=SC2053  # unquoted on purpose: glob match
  [[ $rel == $g ]] && match=1
  # Deny also matches the absolute path, in case the root is spelled differently.
  # Over-blocking is the safe direction.
  [[ $mode == deny && $file == */$g ]] && match=1
done

if [ "$mode" = deny ] && [ $match = 1 ]; then
  if [[ $rel == tests/contracts/* ]]; then
    echo "BLOCKED: $rel is a frozen boundary contract (CR-09). It changes only through architecture-design Revise; stop and report it." >&2
  else
    echo "BLOCKED: $rel is protected from this agent (CONSTRAINTS.md, Roles and protected paths)." >&2
  fi
  exit 2
fi
if [ "$mode" = allow ] && [ $match = 0 ]; then
  echo "BLOCKED: $scope may only edit: ${globs[*]}  (tried: $rel)" >&2
  exit 2
fi
exit 0
