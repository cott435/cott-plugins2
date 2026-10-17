# Build-phase runtime smoke tests: 2026-10-17

Claude Code 2.1.296, `claude -p --model sonnet`, agents passed with `--agents` (one `prober` type, sonnet), `--output-format stream-json --verbose --include-hook-events`. Throwaway repo in this session's scratchpad (`smoke/repo`), never trusted, so only settings hooks were used. Four runs, $0.97 in total. Settings hooks logged every SubagentStart, SubagentStop, PreToolUse (Write|Edit) and Stop input; a second PreToolUse hook returned `ask` for any path under `oracle/`.

Setup:
- `main` has one commit; `build/M1` adds a second (`BUILD_MARKER`) and is checked out.
- `.claude/settings.json` is committed with hooks tagged `committed`; the main checkout's copy is modified, uncommitted, with the same hooks tagged `maindisk`. A worktree checks out the committed copy, so the tag shows which file a worktree agent's hooks come from.
- A fake `dt claim` (`tools/fakedt.py`, run by absolute path) writes a 2,100-line `.claude/packet.md` with a token on line 2050, and a claim record under `$(git rev-parse --git-common-dir)/dt-build/claims/`.
- The main prompt launches two `prober` agents in one message, both `isolation: "worktree"` and `run_in_background: true`. **A**: `pwd`, `git rev-parse HEAD`, `git branch --show-current`, `git rev-parse --git-common-dir`, the fake claim; read the whole packet and report the token; write a new untracked `tests/intent/test_new.py`; try to write `oracle/expected.json`; commit nothing. **B**: two read-only commands, no changes.

| Run | Permission mode | Allow rules |
|---|---|---|
| 1 | `bypassPermissions` | — |
| 2 | `default` | `Agent`, `Bash(pwd)`, `Bash(git rev-parse:*)`, `Bash(git branch:*)` |
| 3 | `acceptEdits` | run 2's plus `Bash(python3 <abs>/fakedt.py:*)` |
| 4 | `acceptEdits`, `--settings '{"sandbox":{"enabled":true,"autoAllowBashIfSandboxed":true}}'` | `Agent` only |

## Results

| # | Question (build-phase.md §12) | Result | Evidence |
|---|---|---|---|
| 3 | Which `settings.json` does a worktree agent load? | **The main checkout's file on disk**, not the worktree's committed copy. Every hook event, from both worktree agents, was tagged `maindisk` | `hooks.jsonl`: `maindisk-substart`, `maindisk-pre`, `maindisk-substop` for both agent ids; no `committed` tag |
| 4 | Do Agent-tool worktrees branch from the main checkout's HEAD? | **PASS.** Both worktrees started at `fb16712`, `build/M1`'s head, not `main` (`266b6c7`). Branch `worktree-agent-<id>`, path `.claude/worktrees/agent-<id>` | A's `git rev-parse HEAD`, `git worktree list` |
| 5 | Does a worktree holding only new, untracked files survive clean-up? | **PASS.** A's worktree (only `?? tests/`, plus the gitignored packet) was kept; B's, unchanged, was removed with its branch | `git worktree list` after each run |
| — | What does the parent get back? | The agent's last text, plus, **for a kept worktree, `<worktree><worktreePath>…</worktreePath><worktreeBranch>…</worktreeBranch></worktree>`**. B's result had none | run 1 and 3 final results |
| 6 | Can a subagent run `dt` by absolute path and read a 2,100-line packet? | **PASS.** The fake claim ran from its absolute path; A reported line 2050's token exactly (`TOKEN-2050-fdff6529` = the claim record's) | run 1 result vs `claims/M1-T01.json` |
| 7a | Background agents' permissions in `-p`, default mode | **A command with no allow rule is denied, not asked.** `--allowedTools` rules reach subagents: the allowed `git` commands ran, the fake claim was denied, and A stopped and reported it | run 2 `permission_denials`: the `python3 …fakedt.py` call |
| 7b | `acceptEdits` in a worktree | **Writes inside the worktree are accepted** (`tests/intent/test_new.py` written, no denial) | run 3 |
| 7c | A guard's `ask` in a background agent, `-p` | **Denied**, and listed in the result's `permission_denials`; the agent reported `oracle=refused`. (Interactive: not tested) | runs 1, 3, 4 |
| 8 | Can a worktree agent write under the git common dir with the sandbox on? | **PASS.** With the sandbox on, Bash ran with no allow rule (so the sandbox was active; run 2 shows that command is otherwise denied), and the claim record was written to `repo/.git/dt-build/`. The session's cwd was the repo root, which contains both `.git` and `.claude/worktrees/`. Caveat: the repo sat under `/private/tmp` | run 4 claim file |
| 9 | Can a SubagentStop hook find the agent's claim? | **PASS.** SubagentStart and SubagentStop both carry `agent_type`, `agent_id` and `cwd` = the agent's worktree, so a hook can map agent to claim by `cwd` | `hooks.jsonl` |
| 10 | Venv per worktree, with torch | **0.35–0.9 s** for `uv sync --frozen` from a warm uv cache (a clone of the rl iteration-8 project, then a worktree of it); `.venv` 1.0 GB apparent, cloned rather than copied on APFS. First `import torch` through `uv run`: 6.2 s | `time` output |
| 11 | Does `claude -p` wait for background agents and resume the main agent? | **PASS.** `-p` stayed alive until both finished; each completion started a new main turn. The stream has **one `result` event per main turn** (3 per run), so a harness must read the last | `*.stream.jsonl` |
| — | Main-session Stop while agents run | Fired after each main turn, with `background_tasks` listing the running agents (as on 2026-10-16) | `maindisk-stop … bg` |

Not tested: smoke tests 1–2 (a split task end to end, parallel landing), which need `dt claim` and `dt land`; how a background agent's permission prompt or `ask` surfaces in the interactive app; a trusted folder with agent-file frontmatter hooks (covered 2026-10-16).

## What this changes in the design

- **Hooks and allow rules come from the main checkout's `.claude/settings.json`**, read from disk, for every worktree agent. A change to that file mid-build changes every agent at once, and a worktree's copy is never consulted; the guard that matters is the one protecting the main checkout's file.
- **Background agents need allow rules** for everything they run (`uv run`, `git`, `scripts/check.sh`, the `dt` path), or `acceptEdits` plus those rules: an un-allowed command is a denial the agent can only report. build-setup writes them.
- **`dt guard`'s `ask` becomes a denial** for a background agent in `-p`. A tester or implementer must never need an oracle edit; when it does, it escalates.
- **The Agent result names a kept worktree's path and branch**, so the driver could land from it; the claim record stays the source of truth, since an unchanged worktree returns nothing and a compaction can drop the message.
- **Liveness by `cwd` works**: SubagentStop's `cwd` is the worktree that holds the claim.
- **Per-worktree venvs are cheap** with a warm uv cache; a cold torch import (~6 s) is the larger cost per first test run.
- **Eval harness:** read the last `result` event of a `-p` stream, not the first.
