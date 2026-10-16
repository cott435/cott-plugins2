#!/usr/bin/env bash
# Floor checks on the diff (CONSTRAINTS.md Floor, CR-01 to CR-04, CR-07, CR-08): new suppression
# comments, stubs, weakened or assertion-free tests, secrets, a loosened tool config, and
# imports from references/ or references/ put on an import path.
# Diff-scoped, so code that was already there is not judged again.
#
#   scripts/floor_guard.sh                default base: refs/checks/base, else HEAD
#   scripts/floor_guard.sh --base REF     e.g. the milestone's Base sha, or origin/main in CI
#
# Exit 0 clean · 1 at least one violation · 2 could not run (never read a 2 as clean).
# Adapted from agent-skills constraint-driven-development references/floor-guard.md.
set -u
cd "$(dirname "$0")/.." || exit 2

base_ref=""
while [ $# -gt 0 ]; do
  case "$1" in
    --base) base_ref="${2:-}"; shift 2 || shift ;;
    *) echo "usage: scripts/floor_guard.sh [--base REF]" >&2; exit 2 ;;
  esac
done

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "floor_guard: not inside a git work tree" >&2
  exit 2
fi
if [ -n "$base_ref" ]; then
  base=$(git rev-parse -q --verify "${base_ref}^{commit}") || {
    echo "floor_guard: no such commit: $base_ref" >&2
    exit 2
  }
else
  base=$(git rev-parse -q --verify refs/checks/base || git rev-parse -q --verify HEAD) || {
    echo "floor_guard: no commit to compare against: commit first" >&2
    exit 2
  }
fi

tmp=$(mktemp -d) || exit 2
trap 'rm -rf "$tmp"' EXIT
# The project may sit below the git root: --relative limits the diff to it and names files
# relative to it, as `git ls-files` does from here.
git -c core.quotepath=off diff --relative --unified=0 --no-color --no-ext-diff "$base" -- . >"$tmp/diff" || exit 2
git -c core.quotepath=off ls-files --others --exclude-standard -- . >"$tmp/untracked" || exit 2
git show "$base:./pyproject.toml" >"$tmp/pyproject.base.toml" 2>/dev/null || : >"$tmp/pyproject.base.toml"

uv run --frozen --quiet python scripts/floor_guard.py \
  --diff "$tmp/diff" --untracked "$tmp/untracked" --old-pyproject "$tmp/pyproject.base.toml"
status=$?
# Anything but a clean 0 or a findings 1 means the guard itself broke.
[ $status -le 1 ] || status=2
exit $status
