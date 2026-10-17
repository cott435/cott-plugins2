# Sourced by the hook scripts. Sets $input (the hook JSON) and $root (the project to check).
# The input's `cwd` is where Claude is working: it follows worktrees and `cd`, while
# CLAUDE_PROJECT_DIR stays on the checkout the session started in. Walk up from `cwd`
# to the directory that holds scripts/check.sh.
input=$(cat)
root=$(jq -r '.cwd // empty' <<<"$input" 2>/dev/null)
root=${root:-${CLAUDE_PROJECT_DIR:-$PWD}}
while [ "$root" != / ] && [ ! -f "$root/scripts/check.sh" ]; do root=$(dirname "$root"); done
[ "$root" = / ] && root=${CLAUDE_PROJECT_DIR:-$PWD}
