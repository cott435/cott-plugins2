# Tooling Verification — python_tooling bundle

**Status:** Done · **Date:** 2026-10-16 · **Companion to:** [build-setup.md](build-setup.md)

I installed and ran the `python_tooling` bundle (`~/Downloads/python_tooling`, left unedited) on a sample project, fixed it until it passed on clean code, and then planted violations. I tested the hook scripts with simulated stdin and checked the hook claims against the current Claude Code docs.

- **Sample project:** [evals/tooling-check/](../evals/tooling-check/). The quant package `quantcheck` has `data` < `stats` < `portfolio`, one pipeline per subpackage, intent and unit tests, a Hypothesis property test and fixture `TC-01`. Its scripts and `pyproject.toml` are the fixed versions; the diffs are in §4.
- **Result:** `scripts/check.sh full` exits 0 on the sample. So do `fast`, `collect`, and `gate` in a git copy.
  - In place, `gate` fails only its protected-files step. That's because the sample is untracked in dev-team2, so the check is doing its job. It passes once the sample is committed.
- **Re-run:** `cd evals/tooling-check && uv sync && bash scripts/check.sh full`.

**Verdict:** the tool choice and the rule config hold up. The scripts had problems:
- Two blockers: the venv tools aren't on PATH, and there is no `[build-system]`.
- Five fail-open bugs in `path_guard.sh`.
- An integrity check that is easy to get around.
- A Stop hook whose block can silently become non-blocking.

All are fixed in the sample and listed below.

---

## 1. Versions

macOS 15 (Darwin 24.6), arm64 · uv 0.11.20 · CPython 3.11.10 (Homebrew, from `.python-version`) · jq 1.8.1 (`/usr/bin/jq` ships with macOS 15) · Node 24.14.1 (system, used by pyright) · Claude Code 2.1.292.

| Tool | Version | | Tool | Version |
|---|---|---|---|---|
| ruff | 0.17.1 | | deptry | 0.25.1 |
| mypy | 2.4.0 (compiled) | | import-linter / grimp | 2.15 / 3.17 |
| pyright | 1.1.414 | | vulture | 2.16 |
| pytest | 9.1.1 | | typos | 1.51.1 |
| pytest-cov / coverage | 7.1.0 / 7.16.2 | | pip-audit | 2.10.1 |
| hypothesis | 6.170.0 | | pandas-stubs | 3.0.5.260914 |
| numpy / pandas | 2.4.6 / 3.0.6 | | | |

## 2. Timings

Wall-clock times through `uv run --frozen` (about 30 ms overhead per call). The sample has 7 source files and 9 tests. "Cold" means the tool's own cache was deleted, but the venv's `.pyc` files and the OS cache were warm. Repeat runs varied by up to 40% under machine load.

| Step | Cold | Warm | Step | Cold | Warm |
|---|---|---|---|---|---|
| ruff check | 0.12 s | 0.03 s | pip-audit | 0.98 s | 0.87 s |
| ruff format --check | 0.04 | 0.03 | pytest --no-cov (dev, 20 ex.) | 1.61 | 1.40 |
| mypy strict | 1.75 | 0.16 | pytest --cov (dev) | 1.87 | 1.84 |
| pyright | 1.21 | 0.88 | pytest --cov (ci, 500 ex.) | 2.64 | 2.57 |
| check_size.py | 0.06 | 0.05 | **check.sh fast FILE** | 0.20 | 0.14–0.20 |
| deptry | 0.18 | 0.15 | **check.sh collect** | 1.44 | 1.5–2.2 |
| lint-imports | 0.24 | 0.20 | **check.sh gate** | 2.19 | 2.0–3.2 |
| vulture / typos | 0.07 / 0.07 | 0.07 / 0.04 | **check.sh full** | 5.36 | 5.2–8.9 |

First runs cost more:
- **gate in a fresh venv:** 13.7 s, of which pytest took 7.6 s compiling pandas and numpy `.pyc` files.
- **pip-audit:** 3.0 s on its first run (network and cache).
- **uv sync:** 6.2 s on a cold project.
- **pyright:** the PyPI wheel bundles the JS and uses the system `node`. With no Node installed it downloads one through `nodeenv` on first run. Use `pyright[nodejs]` to avoid that.

The design's default gate budget of 90 s has plenty of room.

## 3. What failed out of the box

| # | Problem | Evidence | Fix (in sample) |
|---|---|---|---|
| 1 | **check.sh calls bare `ruff`, `mypy`, `pytest`…** Hooks don't activate the venv. On this machine they resolved to Anaconda's ruff 0.12.0, mypy 1.17.1 and pytest 8.4.2; deptry, pyright and others were "command not found". | Shipped `gate` in a normal shell: mypy "Library stubs not installed", pytest `No module named 'hypothesis'`, `deptry: command not found`. Exit 1, and the version drift goes unnoticed | `run()` wraps every tool in `uv run --frozen --quiet` |
| 2 | **No `[build-system]` in the README pyproject.** uv treats the project as virtual and never installs `quantcheck`. | pytest `ModuleNotFoundError: No module named 'quantcheck'` (4 collection errors); lint-imports "Could not find package 'quantcheck'" | Add `uv_build` `[build-system]` |
| 3 | mypy strict with pandas needs stubs | `Library stubs not installed for "pandas" [import-untyped]` ×3 | `pandas-stubs` in the dev group |
| 4 | `PD901` was removed from Ruff | Every ruff run warns: "The following rules have been removed and ignoring them has no effect: PD901" | Drop it from `ignore` |
| 5 | **`lint.preview = true` changes Ruff's output to rule names** (`complex-structure`, not `C901`), in both `full` and `concise`. `noqa` and CONSTRAINTS.md cite codes. | `ruff check --show-settings` shows `output_prefer_rule_codes = false`; the docs for the setting say names are the default "when preview mode is enabled" | `output-prefer-rule-codes = true` under `[tool.ruff]` |
| 6 | `scripts/check_size.py` fails the bundle's own `ruff format --check` at line-length 100 | "1 file would be reformatted" | Reformatted |
| 7 | Placeholder import contract | `Missing layer 'quantcheck.cli': module quantcheck.cli does not exist.` | Generated contract `portfolio > stats > data` |
| 8 | Copying drops the exec bit; `post_edit`/`stop_gate` call `scripts/check.sh` directly | `bash: scripts/check.sh: Permission denied` (exit 126) | Hooks call `bash scripts/check.sh` |

Accepted as written:
- Every other Ruff option, and preview rules `PLR0914`, `PLR1702` and `PLR0904`, which are still preview in 0.17.1 (`PLR0917` is now stable).
- Every mypy, pyright, pytest, coverage, deptry, vulture and typos key.
- `--strict-config` raised no complaint.

## 4. Changes, before → after

### 4.1 `pyproject.toml` (diff against the README block with `yourpackage` → `quantcheck`)

```diff
 dependencies = [
-    # "pandas", "numpy", "pandera",
+    "numpy",
+    "pandas",
 ]
+[build-system]
+requires = ["uv_build>=0.11,<0.12"]
+build-backend = "uv_build"
 [dependency-groups]
 dev = [ …,
+    "pandas-stubs",
 ]
 [tool.ruff]
 src = ["src", "tests"]
+output-prefer-rule-codes = true # preview mode prints rule names; noqa and CONSTRAINTS.md use codes
 ignore = [
     "E501", "TRY003",
-    "PD901",    # "df" is a fine variable name
 ]
 [tool.coverage.report]
 exclude_also = [...]
+fail_under = 80                 # check.sh full reads this; keep in sync with CONSTRAINTS.md
 [[tool.importlinter.contracts]]
-name = "Layers: cli > services > core"
-layers = ["quantcheck.cli", "quantcheck.services", "quantcheck.core"]
+name = "Layers: portfolio > stats > data"
+layers = ["quantcheck.portfolio", "quantcheck.stats", "quantcheck.data"]
```

Left alone but worth knowing:
- `[[tool.mypy.overrides]] module = "tests.*"` is dead config, because `files = ["src"]` means mypy never sees tests.
- `pip-audit` with no arguments audits the whole venv, dev tools included.

### 4.2 `scripts/check.sh`

| Before | After | Why |
|---|---|---|
| `"$@" \|\| rc=1` | `uv run --frozen --quiet "$@" \|\| { rc=1; failed+=("$*"); }` | Locked tools, not PATH (§3 #1) |
| runs in the caller's cwd | `cd "$(dirname "$0")/.."` | Hooks can run from a subdirectory |
| — | `export NO_COLOR=1`, `deptry . --no-ansi`, `lint-imports --no-logo` | ANSI codes and a 12-line ASCII logo were filling the 60-line feedback tail |
| last line `exit $rc` | prints one `FAILED: <command>` line per failed step | The agent sees what failed even when `tail -60` cuts off the top |
| gate: `ruff check .` | `ruff check --ignore-noqa .` (gate and full) | A targeted, used `# noqa` otherwise passes (§5) |
| gate: no import-linter | `run lint-imports --no-logo` | The shipped gate passed a layer violation (exit 0); design CR-24 says gate; cost 0.2 s |
| `pytest tests/intent tests/unit` | only the dirs that exist; exit 5 ("no tests collected") counts as a pass in gate/full | Missing `tests/unit` → exit 4; empty dirs → exit 5 (§6.5) |
| collect: no dir check | `tests/intent does not exist: write the intent tests there` | Clear message instead of three tool errors |
| `git diff --exit-code --stat -- tests/intent` | `protected_unchanged`: diff against `refs/checks/base` (fallback HEAD) **plus** untracked files, over `PROTECTED=(tests/intent tests/fixtures tests/conftest.py pyproject.toml scripts .claude/agents)` | The shipped check misses staged, committed and new files, and every path outside tests/intent (§6.4) |
| full: `pytest --cov --cov-fail-under=80 -q` | `HYPOTHESIS_PROFILE=ci run_tests --cov -q`, threshold from `fail_under` | The full pass never selected the `ci` profile; a threshold buried in a script can't be checked against CONSTRAINTS.md |
| full: `pip-audit` | `pip-audit --skip-editable` | Drops the "quantcheck: not on PyPI" skip table |

### 4.3 Hook scripts

New `scripts/hooks/project_root.sh`, sourced by all three hooks:

```bash
input=$(cat)
root=$(jq -r '.cwd // empty' <<<"$input" 2>/dev/null)
root=${root:-${CLAUDE_PROJECT_DIR:-$PWD}}
while [ "$root" != / ] && [ ! -f "$root/scripts/check.sh" ]; do root=$(dirname "$root"); done
[ "$root" = / ] && root=${CLAUDE_PROJECT_DIR:-$PWD}
```

Why the input's `cwd` and not `$CLAUDE_PROJECT_DIR` or `$PWD`:
- The docs say `CLAUDE_PROJECT_DIR` "stays put" on the main checkout in a worktree, while the input's `cwd` "follows Claude" into worktrees and after `cd`.
- I tested a version that used `cd "$CLAUDE_PROJECT_DIR"`. Run from a worktree with a planted error, its stop gate checked the clean main checkout and let the agent stop.
- `$PWD` (shipped) breaks after `cd`.
- The walk-up also handles a project that isn't the git root, like this sample.

**`path_guard.sh`**
- `rel="${file#"$PWD"/}"` became `"$root"`.
- jq failure now blocks: it fails closed instead of open.
- `..` in the path blocks.
- `shopt -s nocasematch`.
- Deny also matches `*/GLOB` on the absolute path.

**`post_edit.sh`**
- Added `cd "$root"`.
- `bash scripts/check.sh` replaces `scripts/check.sh`.
- jq failure now gives exit 1 (a non-blocking notice) instead of a silent skip.

**`stop_gate.sh`**
- Blocks with `{"decision":"block","reason":…}` and exit 0, instead of exit 2 with stderr.
- When it gives up, it prints `{"systemMessage":…}` instead of writing stderr on exit 0, which nobody sees.
- Counter key is `agent_id // session_id`, not `agent_id // "main"`, so separate main sessions don't share a counter.
- Added `cd "$root"` and `bash scripts/check.sh`.

The reason for each is in §6.3.

---

## 5. Planted violations

Each plant went into a clean tree (`src/quantcheck/planted_*.py`, plus non-file plants) and was run through each mode. Each mode got a fresh copy, because `fast` auto-fixes in place.

| Violation | Caught by (code) | fast | gate | full |
|---|---|---|---|---|
| Complexity: 11 `if`/return branches | ruff `C901` (12 > 10), `PLR0911`, `PLR0912` | ✗ | ✗ | ✗ (+ coverage < 80) |
| Oversized function: 62-line literal, 1 statement | `check_size.py` `SIZE003` (PLR0915 can't see it) | ✗ | ✗ | ✗ |
| Unused dependency: `uv add six` | deptry `DEP002 'six' defined as a dependency but not used` | n/a | ✗ (+ protected: pyproject changed) | ✗ |
| Transitive import: `from dateutil import parser` | deptry `DEP003`; mypy (no stubs) | n/a | ✗ | ✗ |
| Layer violation: `data` imports `stats` | lint-imports `quantcheck.data is not allowed to import quantcheck.stats` | n/a | ✗ (**shipped gate: exit 0**) | ✗ |
| Blanket `# noqa` | `PGH004`, `RUF100` | ✗ (`--fix` deletes it) | ✗ | ✗ |
| Unused `# noqa: E501` | `RUF100` (non-enabled: E501) | ✓ (`--fix` deletes it) | ✗ | ✗ |
| **Used** `# noqa: C901, PLR0911, PLR0912` | only with `--ignore-noqa` | ✓ | ✗ (**shipped gate: exit 0**) | ✗ |
| Blanket `# type: ignore` | `PGH003` | ✗ | ✗ | ✗ (+ pyright `reportUnnecessaryTypeIgnoreComment`) |
| Unused `# type: ignore[arg-type]` | mypy `[unused-ignore]` (strict) | ✓ | ✗ | ✗ |
| **Used** `# type: ignore[return-value]` | **nothing** | ✓ | ✓ | ✓ |
| Untyped def `scale(values, factor)` | mypy `[no-untyped-def]` | ✓ (mypy isn't per-edit) | ✗ | ✗ |
| Typo `seperate` (identifier and docstring) | typos `` `seperate` should be `separate` `` | ✗ | ✓ (gate has no typos) | ✗ |
| Coverage drop | `Required test coverage of 80.0% not reached` (from config) | n/a | n/a | ✗ |

✗ = the check fails (good), ✓ = passes.

Remaining gaps:
- **A used `# type: ignore[code]` passes everything.** mypy can't be told to ignore its own ignores.
  - `enableTypeIgnoreComments = false` in pyright catches it in `full`: "Type "float" is not assignable to return type "int"" (verified).
  - But `# pyright: ignore[...]` still works under that setting, so a diff-scoped grep (`floor_guard.sh`) is the real control.
  - `pragma: no cover` was not tested; it is in the same position.
- **Dead functions.** At `min_confidence = 80`, vulture reports only unused imports (90%, already Ruff `F401`) and unreachable code (100%).
  - Unused functions and classes score 60% and go unreported.
  - At 60 the sample had no false positives, because `__all__` re-exports count as uses.
- Hypothesis profiles work: `dev` stops at `max_examples=20` and `ci` at 500, checked with `--hypothesis-show-statistics`.

## 6. Hook tests (simulated stdin)

### 6.1 `path_guard.sh`

| Case | Want | Shipped | Fixed |
|---|---|---|---|
| tester allow: `tests/intent/test_a.py`, `tests/intent/sub/test_b.py` | 0 | 0 | 0 |
| tester allow: `src/quantcheck/x.py`, `/etc/hosts` | 2 | 2 | 2 |
| tester allow: `tests/intent/../../src/x.py` | 2 | **0** | 2 |
| implementer deny: `tests/intent/test_a.py`, `tests/conftest.py`, `pyproject.toml` | 2 | 2 | 2 |
| implementer deny: `src/…`, `tests/unit/…` | 0 | 0 | 0 |
| implementer deny: `Tests/Intent/test_a.py` (APFS is case-insensitive; the file resolves) | 2 | **0** | 2 |
| implementer deny, after Claude `cd src` (cwd field and process cwd = `src/`) | 2 | **0** | 2 |
| implementer deny, root spelled differently (`/private` prefix) | 2 | **0** | 2 |
| implementer deny, jq not on PATH | 2 | **0** (`jq: command not found`, fails open) | 2 |
| tool call with no `file_path` | 0 | 0 | 0 |
| worktree: tester allow / implementer deny / deny src | 0 / 2 / 0 | 0 / 2 / 0 | 0 / 2 / 0 |

Caveats:
- I don't know whether Claude Code normalises `..` before the hook sees it. The docs only say `file_path` "is always absolute".
- In allow mode, a root mismatch blocks legitimate edits: it fails closed.

### 6.2 `post_edit.sh`

- **Clean file** → exit 0.
- **`ruff --fix` fixes everything** → it rewrites the file and exits 0.
  - In one run it removed 2 unused imports, and then `SIZE002` fired (module < 3 code lines). The min-lines rule does fire on new tiny files.
- **Unfixable problems** (`S307 eval`, `RET504`, typo `recieve`) → **exit 2** with the full ruff and typos output on stderr. This is the intended feedback path. PostToolUse exit 2 "Shows stderr to Claude".
- **Non-`.py` file** → exit 0.
- **Shipped, run from a subdirectory** → `scripts/check.sh: No such file or directory`, exit 2, so the agent gets a useless message. Fixed version: correct feedback.

### 6.3 `stop_gate.sh`

Shipped: the loop guard works as documented. With a lint plus mypy failure planted:
- Attempts 1–3 exit 2 with "attempt n/3" and a 34-line tail.
- Attempt 4 exits 0 and deletes the counter.
- Attempt 5 blocks again at 1/3.
- Separate `agent_id`s get separate counters; with no `agent_id` it falls back to `main`.

Two defects, from the docs:
1. **A block can turn non-blocking.** The docs: "`Stop`, `SubagentStop`, … when your hook exits 2 with nothing on stdout and its stderr says a file is missing, such as `No such file or directory`, Claude Code treats the run as a non-blocking error." I planted a test that reads a missing fixture. The shipped hook's stderr then contained `FileNotFoundError: [Errno 2] No such file or directory: 'tests/fixtures/…'`, so that block would be dropped. The fixed hook prints `{"decision":"block","reason":…}` on stdout and exits 0. Its output is verified as one valid JSON object.
2. **The give-up message is invisible.** It is written to stderr on exit 0, and for exit 0 "Claude Code writes stdout to the debug log and doesn't show it in the transcript". The fixed version prints `{"systemMessage": "Gate 'gate' still failing after 3 attempts; …"}`, shown to the user.

Fixed version, re-run: attempts 1–3 give `decision: block`, attempt 4 gives `systemMessage`, and a clean tree gives exit 0 with no output.

Worktree test: with a planted error in the worktree and a clean main checkout:
- The fixed hook blocks.
- The shipped hook blocks too (its process cwd is the worktree).
- A version using `cd "$CLAUDE_PROJECT_DIR"` let the agent stop.

Claude Code also has its own cap: "after stop hooks have continued the turn eight times in a row, Claude Code overrides the next block". The count resets on every tool call, so the 3-try guard is the real limit.

### 6.4 Integrity check (implementer changing protected files)

| Bypass | Shipped `git diff -- tests/intent` | Fixed `protected_unchanged` |
|---|---|---|
| Edit an intent test (unstaged) | caught | caught |
| Edit, then `git add` | **missed** | caught |
| Edit, then commit (base ref set) | **missed** | caught |
| Edit, then commit, no `refs/checks/base` (falls back to HEAD) | **missed** | **missed** |
| New untracked file in `tests/intent` | **missed** | caught |
| Delete an intent test | caught | caught |
| Edit oracle `tests/fixtures/…/expected.json` | **missed** (out of scope) | caught |

So the orchestrator has to record the base: `git update-ref refs/checks/base HEAD` after committing the tester's work. agent-skills `/build` commits as it goes.

### 6.5 Empty repo (skeleton `src/quantcheck/__init__.py`, numpy/pandas declared)

| State | Shipped | Fixed |
|---|---|---|
| No `tests/` dirs | pytest **exit 4** `file or directory not found: tests/intent` → gate fails | pytest skipped |
| Empty `tests/intent`, `tests/unit` | pytest **exit 5** → gate fails; `pytest --cov` also exits 5 | "(no tests collected)" → passes that step |
| `collect`, empty `tests/intent` | exit 5 → fails | still fails, on purpose (the tester wrote nothing) |
| `collect`, no `tests/intent` | 3 tool errors | `tests/intent does not exist: write the intent tests there` |
| deptry | `DEP002 'numpy'`, `DEP002 'pandas'` (declared, not imported) | same: **gate still fails** |
| lint-imports (fixed gate) | n/a | `Missing layer 'quantcheck.portfolio'` → fails. Optional layers `"(quantcheck.portfolio)"` pass while a layer is missing and are still enforced once it exists (verified) |
| git, no commits | `git diff` exits 0 (no HEAD needed); outside a repo it exits 129 | "no commit to compare against: commit the tester's work first" |

---

## 7. Claude Code doc claims

I fetched the raw page sources (`code.claude.com/docs/en/<page>.md`) on 2026-10-16 and grepped each quote myself.
- `/plugins-reference` is now titled "Plugin manifest reference".
- Plugin hooks and agents moved to `/docs/en/plugins/components`.

| Claim | Verdict | Doc text |
|---|---|---|
| (a) Plugin subagents ignore `hooks` frontmatter | **Confirmed** | sub-agents: "For security reasons, plugin subagents don't support the `hooks`, `mcpServers`, or `permissionMode` frontmatter fields. These fields are ignored when loading agents from a plugin. If you need them, copy the agent file into `.claude/agents/` or `~/.claude/agents/`." plugins/components adds: "**Ignored fields**: `permissionMode`, `hooks`, `mcpServers`, and `initialPrompt`." |
| (b) A frontmatter `Stop` hook becomes `SubagentStop` | **Confirmed** (only when run as a subagent) | sub-agents: "When the agent is invoked as a subagent, `Stop` hooks in frontmatter are automatically converted to `SubagentStop` events." hooks: "Claude Code converts a `Stop` hook here to `SubagentStop`, the event it fires when a subagent completes." |
| (c) `tool_input.file_path` | **Confirmed** | hooks › PreToolUse: "For the file tools `Write`, `Edit`, and `Read`, `tool_input.file_path` is always absolute". (PostToolUse's `tool_response` spells it `filePath`.) |
| (c) `stop_hook_active` | **Confirmed** | hooks › Stop: "Stop hooks receive `stop_hook_active`, `last_assistant_message`, `background_tasks`, and `session_crons`. The `stop_hook_active` field is `true` when Claude Code is already continuing as a result of a stop hook." |
| (c) `agent_id` | **Confirmed** | hooks › SubagentStop: "SubagentStop hooks receive `stop_hook_active`, `agent_id`, `agent_type`, `agent_transcript_path`, and `last_assistant_message`." Common fields: `agent_type` is "Present when the session uses `--agent` or the hook fires inside a subagent." |
| (d) `${CLAUDE_PLUGIN_ROOT}` in `hooks/hooks.json` | **Confirmed** | plugins-reference, "Where each variable resolves": "Hook commands \| Anywhere in `command` and `args` \| `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_PROJECT_DIR`, and `CLAUDE_PLUGIN_OPTION_<KEY>`". plugins/components example: `"command": "\"${CLAUDE_PLUGIN_ROOT}/scripts/format.sh\""` |
| (e) SessionStart fires for subagents | **Not stated; the docs imply no** | hooks lists it under "per session: `SessionStart` and `SessionEnd`" and says it "Runs when Claude Code starts a new session or resumes an existing session." sub-agents never mentions SessionStart. The subagent event is SubagentStart: "Runs when Claude spawns a subagent with the Agent tool, …" and "SubagentStart hooks can't block subagent creation, but they can inject context into the subagent." |
| (f) Plugin hooks fire on subagent tool calls | **Confirmed** | hooks: "Hooks from settings files, managed policy settings, and plugins also run inside subagents. When a subagent calls a tool, tool events such as `PreToolUse` and `PostToolUse` fire the same configured hooks as in the main conversation, and the input carries the `agent_id` and `agent_type` common input fields that identify the subagent." |
| (g) Project-dir variable | **`CLAUDE_PROJECT_DIR`**, with a worktree caveat | hooks: "`${CLAUDE_PROJECT_DIR}`: the project root where the session started." "**`${CLAUDE_PROJECT_DIR}` stays put** … **`cwd` follows Claude**: the `cwd` field in the hook's input JSON is the worktree root after Claude enters a worktree, and the new directory after Claude runs `cd`." Also: "Handlers run in the current directory with Claude Code's environment." |

Other doc facts the design relies on:
- **Exit 2:**
  - PreToolUse "Blocks the tool call".
  - PostToolUse "Shows stderr to Claude; the tool already ran".
  - Stop "Prevents Claude from stopping, continues the conversation".
  - SubagentStop "Prevents the subagent from stopping".
- **Matchers:** names made of letters, digits, `_`, `-`, spaces, `,` and `|` are exact lists, so `Edit|Write` is exact. `Stop` takes no matcher.
- **Timeout:** the default command-hook timeout is 600 s.
- **Workspace trust:** project subagent frontmatter hooks need it: "trusting a parent folder isn't enough, and a `-p` session doesn't count as trusted". "Hooks from user-level subagents in `~/.claude/agents/` and from definitions you pass with `--agents` run without this step."
- **Feedback to the parent:** "To inject context into the parent session after a subagent returns, use a PostToolUse hook on the `Agent` tool".
- **No snapshotting:** the docs say nothing about hooks being snapshotted at session start. Settings edits are picked up "automatically by the file watcher".

---

## 8. Changes needed in build-setup.md

1. **§3 file list:**
   - Add `scripts/hooks/project_root.sh`.
   - Templates are the fixed scripts in `evals/tooling-check/scripts/`, not the bundle's.
   - New mode must check `command -v uv jq` and stop with a clear message if either is missing. The hooks need jq and `check.sh` needs uv.
   - Add `.hypothesis/`, `.import_linter_cache/` and `.coverage` to the `.gitignore` line.
2. **§3 pyproject template:**
   - Always include a `[build-system]` (src layout).
   - Set `output-prefer-rule-codes = true` whenever `lint.preview = true`.
   - Remove `PD901`.
   - Add type stubs per stack, `pandas-stubs` for pandas (§8 Extend already says "type stubs"; make it New too).
3. **§4 CONSTRAINTS table:**
   - **CR-24** (import-linter at gate): the bundle ran it only in `full`; the template now runs it in `gate`.
   - **CR-27** `pytest -m repro` needs `repro` in `markers`, or `--strict-markers` rejects it. `gate` already runs every test, so say what `-m repro` adds or drop it.
   - **CR-40:** coverage threshold is config key `tool.coverage.report.fail_under`, not a `check.sh` flag. For the default "measure and hold", set it to the measured value and let Ratchet raise it.
4. **CR-01:**
   - Enforce Ruff suppressions with `ruff check --ignore-noqa` in gate and full, so exceptions live in `per-file-ignores` (protected config). The Exceptions table then maps one-to-one to `per-file-ignores` entries, and `dt status` can compare them.
   - A used `# type: ignore[code]` passes mypy and every other check. Keep `floor_guard.sh` as the control for `type: ignore`, `pyright: ignore` and `pragma: no cover`. Optionally add pyright `enableTypeIgnoreComments = false` for `full`.
5. **CR-41 (vulture):** at `min_confidence = 80` it reports only unused imports and unreachable code, so the metric will sit at 0. Use 60 plus a whitelist file, or drop the row.
6. **§6 hook commands:**
   - Agent frontmatter should run `bash "$CLAUDE_PROJECT_DIR"/scripts/hooks/<x>.sh`, not a relative path. A missing script is a non-blocking error, so a relative path that breaks after `cd` silently turns the guard off.
   - The scripts take the project root from the input's `cwd`, because `CLAUDE_PROJECT_DIR` stays on the main checkout in worktrees.
   - Still unverified: what `cwd` a subagent with `isolation: worktree` passes. Check it live (follow-up 1).
7. **§6 plugin hooks:**
   - **Plugin hooks fire inside subagents.** The oracle guard and `dt lint` will run on tester and implementer tool calls; that's intended, so state it.
   - **SessionStart doesn't reach subagents.** If `dt status --summary` should reach them, use `SubagentStart` with `additionalContext`.
8. **§6 "Two layers for every protection":**
   - The Stop-time check must diff against a recorded base ref (`refs/checks/base`), list untracked files, and cover every protected path, not just `tests/intent`.
   - The orchestrator (build-phase design) sets the ref when it commits the tester's work and at each task start.
   - Generate one protected-path list from the §4 role table and feed both the `path_guard.sh deny` globs and `check.sh`'s `PROTECTED`. The bundle's deny list was missing `tests/fixtures/**`, `scripts/`, `.claude/agents/` and `CONSTRAINTS.md`.
9. **§7 Task level ("3 tries, then hands to a human"):**
   - Stop hooks block with JSON `decision: "block"`, not exit 2.
   - The hand-off is a `systemMessage` to the user. The parent agent is **not** told. To tell the orchestrator, add a PostToolUse hook on the `Agent` tool, or have the orchestrator re-run `check.sh gate` after the subagent returns.
10. **§8 New mode, "run `check.sh gate` once to prove the config":** this fails on a fresh skeleton even with the fixed scripts:
    - deptry `DEP002` for declared but not-yet-imported dependencies.
    - `Missing layer` for components that don't exist yet.
    - No commit for the protected check.

    The fixes:
    - Generate contracts with optional layers `"(pkg.component)"` until the module exists. `dt status` flags parentheses on modules that now exist.
    - Make a commit before the proof run.
    - Decide how dependencies arrive (item 11).

    pytest exit 5 no longer fails gate or full; `collect` still fails on an empty `tests/intent`, by design.
11. **Dependencies (§8 Extend vs CR-07):**
    - The implementer can't edit `pyproject.toml` (path guard plus protected diff), so `uv add` mid-task fails the gate.
    - If Extend adds a milestone's dependencies at kickoff, deptry `DEP002` fails until code imports them.
    - Choose one: Extend adds dependencies together with a time-boxed `DEP002` exception for each, or the implementer may change `[project.dependencies]` only and the protected diff excludes those lines.
12. **§2 / §8 timing defaults:** the 90 s gate budget holds. gate takes 2–3 s warm and 13.7 s on a fresh venv's first run, on a 7-file package.
13. **§11 workspace trust:** frontmatter hooks need it, and `claude -p` doesn't count. Eval runs of `/build` through the headless harness won't exercise the agent hooks unless the agents are passed with `--agents` or are user-level.

**Follow-ups, not done here:**
1. A live smoke test inside a real Claude Code session: Stop JSON block, `systemMessage`, and `cwd` in a worktree subagent.
2. Turning the fixed scripts into `skills/build-setup/templates/`.
3. `floor_guard.sh`, which isn't in the bundle and is untested.
4. `check.sh --pkg`, which doesn't exist yet.
