#!/usr/bin/env bash
# One entry point for every quality check. Hooks call it; so do the orchestrator's check agent and people.
# minilab's bar is build-setup's, reduced to the standard library and pytest (AD-01, AD-02): no uv, ruff or
# type checker, so a build eval measures planning and dispatch, not tool installs.
#
#   scripts/check.sh fast FILE...          per edit: the file compiles and fits CR-22
#   scripts/check.sh collect [--task ID]   tester's finish gate: intent tests collect; only tests/intent changed
#   scripts/check.sh gate [--task ID]      implementer's finish gate: all tests pass; floor; protected unchanged
#   scripts/check.sh full [--task ID]      checkpoints and milestone exit: gate, plus no stub left (--exit)
#   scripts/check.sh protected             print the protected-path globs (path_guard.sh deny --protected)
#   scripts/check.sh floor [--base REF]    the floor checks on the diff since REF (default refs/checks/base)
#
# Every collect/gate/full run appends a verdict to .dt/gates/<task>.json in the main checkout (worktrees
# write there too, so verdicts are never merged): {"task", "mode", "passed", "try", "failed", "time",
# "branch", "head"}. The task is --task, else $DT_TASK, else .claude/.check_task, else the M<n>-T<nn> prefix
# of the newest commit since the base, else "unknown".
set -u
cd "$(dirname "$0")/.." || exit 1
export NO_COLOR=1 PYTHONDONTWRITEBYTECODE=1

# The protected list (CONSTRAINTS.md, "Roles and protected paths"). Git pathspecs and path_guard globs.
PROTECTED=("tests/intent/**" "tests/fixtures/**" "tests/conftest.py" "pyproject.toml" "CONSTRAINTS.md"
           "scripts/**" ".claude/agents/**" ".claude/settings.json" "references/**" "tests/contracts/**")
SRC_DIRS=(packages/mdata/src packages/risk/src)
PY=${PYTHON:-python3}

mode="${1:-gate}"
shift || true
task="" base_arg="" exit_check=0 args=()
while [ $# -gt 0 ]; do
  case "$1" in
    --task) task="${2:-}"; shift 2 || shift ;;
    --base) base_arg="${2:-}"; shift 2 || shift ;;
    --exit) exit_check=1; shift ;;
    --pkg) shift 2 || shift ;;   # accepted for build-setup compatibility; every run covers both packages
    *) args+=("$1"); shift ;;
  esac
done

rc=0
failed=()
step() {
  echo "-> $*" >&2
  "$@" || { rc=1; failed+=("$*"); }
}

base_commit() {
  [ -n "$base_arg" ] && { git rev-parse -q --verify "$base_arg^{commit}"; return; }
  git rev-parse -q --verify refs/checks/base 2>/dev/null || git rev-parse -q --verify HEAD 2>/dev/null
}

# A contract folder is frozen once it exists at the base (CR-09); a folder new since the base belongs to the
# interface or contract task writing it.
frozen_contracts() {
  local base meta path
  base=$(base_commit) || return 0
  git ls-tree "$base" -- tests/contracts/ 2>/dev/null | while IFS=$'\t' read -r meta path; do
    case "$meta" in
      *" tree "*) echo "$path/**" ;;
      *) echo "$path" ;;
    esac
  done
}

protected_globs() {
  local g
  for g in "${PROTECTED[@]}"; do
    if [ "$g" = "tests/contracts/**" ]; then frozen_contracts; else echo "$g"; fi
  done
}

unchanged_since_base() {
  local label="$1" base new
  shift
  if ! base=$(base_commit); then
    echo "no commit to compare against: commit first" >&2
    rc=1; failed+=("$label: no commit"); return
  fi
  echo "-> $label unchanged since ${base:0:9}" >&2
  git --no-pager diff --exit-code --stat "$base" -- "$@" >&2 || { rc=1; failed+=("$label changed"); }
  new=$(git ls-files --others --exclude-standard -- "$@")
  if [ -n "$new" ]; then
    printf 'new untracked files in %s:\n%s\n' "$label" "$new" >&2
    rc=1; failed+=("$label changed")
  fi
}

# CR-01, CR-03, CR-08 on the diff since the base; CR-02 over the whole tree: a NotImplementedError stub must
# name an open task (ticked in tasks/todo.md = done), and with --exit no stub may be left at all.
floor() {
  local base diff ids id bad=0
  base=$(base_commit) || base=""
  if [ -n "$base" ]; then
    diff=$(git --no-pager diff -U0 "$base" -- . ':(exclude)scripts' ':(exclude)docs' ':(exclude)tasks' | grep '^+' || true)
    if grep -nE '# *noqa|type: *ignore|pragma: *no cover|pytest\.mark\.(skip|xfail)|pytest\.skip\(' <<<"$diff" >&2; then
      echo "floor: new suppression or skipped test (CR-01, CR-03)" >&2; bad=1
    fi
    if grep -nE '(^\+.*import +references|from +references|sys\.path.*references)' <<<"$diff" >&2; then
      echo "floor: imports from references/ (CR-08)" >&2; bad=1
    fi
  fi
  ids=$(grep -rhoE 'NotImplementedError\("M[0-9]+-T[0-9]+' "${SRC_DIRS[@]}" 2>/dev/null | grep -oE 'M[0-9]+-T[0-9]+' | sort -u)
  for id in $ids; do
    if [ "$exit_check" = 1 ] || grep -qE "^- \[x\] $id\b" tasks/todo.md 2>/dev/null; then
      echo "floor: a stub still names $id (CR-02)" >&2; bad=1
    fi
  done
  if grep -rnE 'raise NotImplementedError(\(\))?$' "${SRC_DIRS[@]}" >&2 2>/dev/null; then
    echo "floor: a stub that names no task (CR-02)" >&2; bad=1
  fi
  return $bad
}

sizes() {
  "$PY" - "$@" <<'EOF'
import ast, sys
bad = 0
for f in sys.argv[1:]:
    src = open(f, encoding="utf-8").read()
    if src.count("\n") > 500:
        print(f"{f}: over 500 lines (CR-22)"); bad = 1
    for node in ast.walk(ast.parse(src, f)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno - node.lineno + 1 > 60:
            print(f"{f}:{node.lineno} {node.name} over 60 lines (CR-22)"); bad = 1
sys.exit(bad)
EOF
}

src_files() { find "${SRC_DIRS[@]}" -name '*.py' 2>/dev/null; }

current_task() {
  local id="${task:-${DT_TASK:-}}"
  [ -z "$id" ] && [ -s .claude/.check_task ] && id=$(tr -cd 'A-Za-z0-9-' <.claude/.check_task)
  [ -z "$id" ] && id=$(git log --format=%s "$(base_commit)"..HEAD 2>/dev/null | grep -oE '^M[0-9]+-T[0-9]+' | head -1)
  [ -z "$id" ] && id=$(git log -1 --format=%s 2>/dev/null | grep -oE '^M[0-9]+-T[0-9]+')
  echo "${id:-unknown}"
}

# What gate runs: every test outside tests/intent, and the intent tests of the current task and of done
# tasks. An intent file belongs to the task whose commit added it (M<n>-T<nn> prefix). With testers merged
# ahead of their implementers (interface-first), other open tasks' intent tests are red by design.
test_targets() {
  local d
  for d in tests/contracts tests/unit tests/system; do [ -d "$d" ] && echo "$d"; done
  [ -d tests/intent ] || return 0
  "$PY" - "$(current_task)" <<'EOF'
import pathlib, re, subprocess, sys
current = sys.argv[1]
todo = pathlib.Path("tasks/todo.md")
done = set(re.findall(r"^- \[x\] (M\d+-T\d+)", todo.read_text(), re.M)) if todo.exists() else set()
for f in sorted(pathlib.Path("tests/intent").rglob("test_*.py")):
    log = subprocess.run(["git", "log", "--diff-filter=A", "--format=%s", "--", str(f)],
                         capture_output=True, text=True).stdout.splitlines()
    owners = [m.group(0) for m in (re.match(r"M\d+-T\d+", s) for s in log) if m]
    if not owners or owners[0] == current or owners[0] in done:
        print(f)
EOF
}

record() {
  [ "$mode" = fast ] || [ "$mode" = protected ] || [ "$mode" = floor ] && return 0
  local common main id
  id=$(current_task)
  common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || return 0
  main=$(dirname "$common")
  mkdir -p "$main/.dt/gates"
  "$PY" - "$main/.dt/gates/$id.json" "$id" "$mode" "$rc" "$(git branch --show-current)" \
    "$(git rev-parse -q --verify HEAD)" "${failed[@]+"${failed[@]}"}" <<'EOF'
import json, sys, time, pathlib
path, task, mode, rc, branch, head, *failed = sys.argv[1:]
p = pathlib.Path(path)
try:
    runs = json.loads(p.read_text())
except (OSError, ValueError):
    runs = []
runs.append({"task": task, "mode": mode, "passed": rc == "0", "try": 1 + sum(r.get("mode") == mode for r in runs),
             "failed": failed, "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "branch": branch, "head": head})
p.write_text(json.dumps(runs, indent=1) + "\n")
EOF
}

case "$mode" in
  fast)
    files=()
    for f in ${args[@]+"${args[@]}"}; do [[ $f == *.py ]] && [ -f "$f" ] && files+=("$f"); done
    [ ${#files[@]} -eq 0 ] && exit 0
    step "$PY" -m py_compile "${files[@]}"
    step sizes "${files[@]}"
    ;;
  collect)
    if [ ! -d tests/intent ]; then
      echo "tests/intent does not exist: write the intent tests there" >&2
      exit 1
    fi
    step "$PY" -m pytest tests/intent --collect-only -q
    step floor
    specs=(tests "${SRC_DIRS[@]}" "${PROTECTED[@]}")
    unchanged_since_base "files outside tests/intent" "${specs[@]}" ':(exclude)tests/intent'
    ;;
  gate | full)
    # shellcheck disable=SC2046  # one path per word, by construction
    step "$PY" -m pytest -q $(test_targets)
    # shellcheck disable=SC2046
    step sizes $(src_files)
    step floor
    protected=()
    while IFS= read -r g; do protected+=("$g"); done < <(protected_globs)
    unchanged_since_base "protected files" "${protected[@]}"
    ;;
  protected)
    protected_globs
    exit 0
    ;;
  floor)
    floor
    exit $?
    ;;
  *)
    echo "unknown mode: $mode (fast | collect | gate | full | protected | floor)" >&2
    exit 64
    ;;
esac
record
[ $rc -ne 0 ] && printf 'FAILED: %s\n' "${failed[@]}" >&2
exit $rc
