#!/usr/bin/env bash
# One entry point for every quality check. Hooks call this; so can you.
#
#   scripts/check.sh fast FILE...   per-edit, instant        (PostToolUse: tester, implementer)
#   scripts/check.sh collect        tester's end-of-work gate (Stop: tester)
#   scripts/check.sh gate           implementer's end gate    (Stop: implementer)
#   scripts/check.sh full           reviewer / CI             (reviewer runs it; CI)
#
# FILE paths are absolute or relative to the project root.
# Prints every failure (does not stop at the first), exits 1 if any check failed.
set -u
mode="${1:-gate}"
shift || true
cd "$(dirname "$0")/.." || exit 1   # hooks may run from another directory
export NO_COLOR=1                   # plain output for the agent reading it

# Implementer may not change these. Keep in sync with path_guard.sh's deny list.
PROTECTED=(tests/intent tests/fixtures tests/conftest.py pyproject.toml scripts .claude/agents)

rc=0
failed=()

# Run a tool from the project's locked environment, never whatever is first on PATH.
run() {
  echo "-> $*" >&2
  uv run --frozen --quiet "$@" || { rc=1; failed+=("$*"); }
}

# pytest exits 5 when it collects nothing. That is fine for gate/full on a project
# with no tests yet; collect calls pytest directly so an empty tests/intent fails.
run_tests() {
  echo "-> pytest $*" >&2
  uv run --frozen --quiet pytest "$@"
  local status=$?
  [ "$status" -eq 5 ] && { echo "(no tests collected)" >&2; return; }
  [ "$status" -eq 0 ] || { rc=1; failed+=("pytest $*"); }
}

# Protected files must match the commit the tester finished on, recorded by the
# orchestrator with `git update-ref refs/checks/base HEAD`. Without that ref this
# compares against HEAD, which misses changes the implementer has already committed.
protected_unchanged() {
  echo "-> protected files unchanged: ${PROTECTED[*]}" >&2
  local base new
  if ! base=$(git rev-parse -q --verify refs/checks/base || git rev-parse -q --verify HEAD); then
    echo "no commit to compare against: commit the tester's work first" >&2
    rc=1; failed+=("protected files: no commit"); return
  fi
  git diff --exit-code --stat "$base" -- "${PROTECTED[@]}" || { rc=1; failed+=("protected files changed"); }
  new=$(git ls-files --others --exclude-standard -- "${PROTECTED[@]}")
  if [ -n "$new" ]; then
    printf 'new untracked files in protected paths:\n%s\n' "$new" >&2
    rc=1; failed+=("protected files changed")
  fi
}

case "$mode" in
  fast)
    # Only Python files, only the file just edited.
    files=()
    for f in "$@"; do [[ $f == *.py ]] && files+=("$f"); done
    [ ${#files[@]} -eq 0 ] && exit 0
    run ruff check --fix --quiet "${files[@]}"
    run ruff format --quiet "${files[@]}"
    run typos "${files[@]}"
    run python scripts/check_size.py "${files[@]}"
    ;;
  collect)
    if [ ! -d tests/intent ]; then
      echo "tests/intent does not exist: write the intent tests there" >&2
      exit 1
    fi
    run ruff check tests/intent
    run ruff format --check tests/intent
    run typos tests/intent
    run pytest tests/intent --collect-only -q --no-cov
    ;;
  gate)
    run ruff check --ignore-noqa .   # exceptions go in per-file-ignores, which is protected
    run ruff format --check .
    run mypy
    run python scripts/check_size.py
    run deptry . --no-ansi
    run lint-imports --no-logo
    test_dirs=()
    for d in tests/intent tests/unit; do [ -d "$d" ] && test_dirs+=("$d"); done
    if [ ${#test_dirs[@]} -gt 0 ]; then
      run_tests "${test_dirs[@]}" --no-cov -q -x
    fi
    protected_unchanged
    ;;
  full)
    run ruff check --ignore-noqa .
    run ruff format --check .
    run mypy
    run pyright
    run python scripts/check_size.py
    run deptry . --no-ansi
    run lint-imports --no-logo
    run vulture
    run typos
    run pip-audit --skip-editable
    # Coverage threshold comes from [tool.coverage.report] fail_under.
    HYPOTHESIS_PROFILE=ci run_tests --cov -q
    ;;
  *)
    echo "unknown mode: $mode" >&2
    exit 64
    ;;
esac
[ $rc -ne 0 ] && printf 'FAILED: %s\n' "${failed[@]}" >&2
exit $rc
