# Claude Code hooks: how the project's checks are wired

Loaded when build-setup writes or changes `.claude/agents/*.md`, `.claude/settings.json` or `scripts/hooks/*`. Doc claims checked against the Claude Code docs on 2026-10-16 (`design/tooling-verification.md` §7); the scripts are tested by `skills/build-setup/tests/`.

## The contract

1. Claude Code runs the command with **JSON on stdin**: `tool_name`, `tool_input` (`file_path` is always absolute for Edit, Write and Read), `cwd`, and `agent_id` / `agent_type` inside a subagent. Stop and SubagentStop also get `stop_hook_active`.
2. **Exit 0** = fine. **Exit 2** = blocking: PreToolUse blocks the call; PostToolUse shows stderr to the agent (the tool already ran). Any other non-zero exit is a non-blocking error, and the action goes ahead.
3. **Stop blocks with JSON**, not exit 2: print `{"decision": "block", "reason": "…"}` and exit 0. An exit-2 Stop hook whose stderr mentions a missing file ("No such file or directory") is treated as non-blocking, and test output often does.
4. Exit-0 output is not shown to anyone unless it is a `{"systemMessage": "…"}`, and a SubagentStop `systemMessage` doesn't reach the main view either (checked live, Claude Code 2.1.292).
5. Matchers made of letters, digits, `_`, `-`, spaces, `,` and `|` are exact lists: `Edit|Write|MultiEdit|NotebookEdit`. Stop takes no matcher. The default timeout is 600 s; don't set a short one, because a timed-out hook doesn't block.

## Who owns which hook

| Source | Fires | Hooks |
|---|---|---|
| Plugin `hooks/hooks.json` (dev-team2) | every session, **including tool calls inside subagents** | SessionStart `dt status --summary` (doesn't reach subagents), PreToolUse `dt guard` (oracle files → ask), PostToolUse `dt lint` on docs, SubagentStop `dt build mark-finished` (the claim in the agent's worktree, its `cwd`) |
| Project `.claude/agents/*.md` frontmatter | only while that agent runs, only in a trusted workspace | the role hooks below. A frontmatter `Stop` becomes `SubagentStop` |
| Project `.claude/settings.json` | main session and **every worktree agent** (the main checkout's copy on disk, never the worktree's) | no hooks; `acceptEdits` and the allow rules background agents need, since an un-allowed command is denied, not asked |

- **Plugin subagents ignore `hooks` frontmatter.** That is why the agents are copied into the project's `.claude/agents/`.
- **Workspace trust:** project frontmatter hooks need the trust dialog accepted. `claude -p` in a folder never trusted skips them silently (checked live: the implementer wrote `tests/intent/` unblocked); in a trusted folder they fire under `-p` too. Headless eval runs only exercise them with `--agents`, user-level agents, or a folder trusted beforehand.
- **Commands are absolute:** `bash "$CLAUDE_PROJECT_DIR"/scripts/hooks/<x>.sh`. A missing script is a non-blocking error, so a relative path that breaks after `cd` would silently turn the guard off.
- **The root comes from the input's `cwd`** (`project_root.sh`), walking up to the folder holding `scripts/check.sh`. `CLAUDE_PROJECT_DIR` stays on the main checkout in a worktree; `cwd` follows Claude into worktrees and after `cd`.

## Role hooks

| Agent | PreToolUse | PostToolUse | Stop |
|---|---|---|---|
| tester | `path_guard.sh allow "tests/intent/**"` and `path_guard.sh writes` on edits; `path_guard.sh deny <source globs>` on Read | `post_edit.sh` | `stop_gate.sh collect` |
| implementer (and solo) | `path_guard.sh deny --protected` and `path_guard.sh writes` | `post_edit.sh` | `stop_gate.sh gate` |
| reviewer | none: `tools: Read, Grep, Glob, Bash`, no Edit or Write | — | — |

`--protected` reads the list from `scripts/check.sh protected`, so the guard and the Stop-time diff can't drift apart. That output narrows `tests/contracts/**` to the contract folders at the worktree's base (CR-09): an interface task may write the folder it creates, or a frozen one its `.claude/.task_writes` names; the next task's base freezes it. `writes` reads `.claude/.task_writes` at the root (one `Writes:` path or folder glob a line, a trailing `/` meaning the folder), so a parallel builder edits only what its task claims; with no file it blocks the `tester` and `implementer` agent types (`agent_type` in the input) and allows any other caller.

## Two layers

Every protection has two layers:
1. **PreToolUse guard** stops the normal route (Edit, Write).
2. **Stop-time diff** catches Bash writes (`sed -i`, `echo >`): `check.sh gate` diffs the whole protected list against the base and lists untracked files; `check.sh collect` does the same for everything outside `tests/intent`.

The base is `refs/worktree/checks-base`, a per-worktree ref: `dt claim` sets it to HEAD in the builder's worktree, `dt land` in the main checkout before its merged gate. Without it the diff falls back to HEAD, which misses changes the agent already committed. `dt claim` also writes the task's package to `.claude/.check_pkg`, which `stop_gate.sh` passes on as `--pkg`, the role's `Writes:` to `.claude/.task_writes`, and the path to `dt.py` to `.claude/.dt`.

## The scripts

| Script | Event | Does | Fails |
|---|---|---|---|
| `path_guard.sh` | PreToolUse | `allow`/`deny` globs relative to the root, or `writes` from `.claude/.task_writes`; `*` crosses `/`; case-insensitive; deny also matches the absolute path; blocks `..` | closed: bad input, no jq or no protected list → exit 2 |
| `post_edit.sh` | PostToolUse | `check.sh fast <file>`: ruff `--fix`, format, typos, size; exit 2 with the output | bad input → exit 1 (reported; the Stop gate still runs) |
| `stop_gate.sh` | Stop / SubagentStop | `check.sh <mode>`; blocks with JSON and the last 60 lines; `--warn` never blocks. With `.claude/.dt`: lets the agent stop when `dt build escalated` exits 0, and records each result with `dt build verdict --mode <m> --rc <rc>` | closed: bad input still runs the gate on the fallback root; no jq → exit 2 with a fixed message |
| `project_root.sh` | sourced | sets `$input` and `$root` | falls back to `CLAUDE_PROJECT_DIR`, then `$PWD` |

**Loop guard.** After 3 failed attempts `stop_gate.sh` lets the agent stop and prints a `systemMessage`. In a dt build the third block tells the agent to finish on its status line, since the failing verdict is recorded and `dt land` rejects with it; elsewhere, to start its report with `GATE FAILED: scripts/check.sh <mode>`, the only signal the parent gets, because the `systemMessage` isn't shown in the main view. The counter is `.claude/.stop_attempts_<agent_id or session_id>` (gitignored) and resets on a pass. `dt land` re-runs the gate unless a recorded verdict matches the worktree's tree. Claude Code's own cap (8 continued Stop blocks in a row) resets on every tool call, so the 3-try guard is the real limit.

## Testing a hook by hand

```bash
echo '{"cwd":"'$PWD'","tool_input":{"file_path":"'$PWD'/tests/intent/test_a.py"}}' \
  | bash scripts/hooks/path_guard.sh deny --protected; echo "exit $?"     # 2 = blocked
echo '{"cwd":"'$PWD'","agent_id":"t1"}' | bash scripts/hooks/stop_gate.sh gate  # JSON, or nothing on a pass
```

## Verified live (Claude Code 2.1.292, 2026-10-16)

- The implementer's frontmatter hooks fire in a trusted workspace, interactive and `-p`: `path_guard.sh` blocks `tests/intent/**` (exit 2), `post_edit.sh` feeds `check.sh fast` back, and the frontmatter `Stop` arrives as `SubagentStop` with `agent_id`.
- `$CLAUDE_PROJECT_DIR` resolves in frontmatter commands. In an `isolation: worktree` subagent it stays on the main checkout, while `cwd` and `$PWD` are the worktree (`.claude/worktrees/agent-<id>`). `project_root.sh` picks the worktree, and the gate runs there.
- Stop JSON blocks 3 times, then the agent may stop; the counter file is removed.
- Claude Code normalises `..` in `file_path` before the hook sees it.
- Worktrees live under `.claude/worktrees/` inside the checkout, so `gitignore.additions` ignores that folder; otherwise the main checkout's ruff, format and deptry scan the worktree copies.
- The Agent tool backgrounds subagents by default, so the parent may finish its own turn (and its Stop hook) before the subagent's gate runs.
