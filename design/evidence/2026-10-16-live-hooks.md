# Live verification of dev-team2 hooks: Claude Code 2.1.292, 2026-10-16

Ran in a throwaway copy of scripts/tests/fixtures/quant in the scratchpad, using haiku for the hook runs. Nothing was committed.

## 1. Plugin hooks (hooks/hooks.json): all pass
- SessionStart: `dt status --summary` is injected, and the model quoted it back.
- Oracle edit (tests/fixtures/quant/TC-01/expected.json): guard returns `ask`. Interactive (pty TUI, acceptEdits on) shows "Do you want to make this edit to expected.json?" and Esc rejects it. With `-p --permission-prompts none` it is auto-denied. With `bypassPermissions --permission-prompt-tool mcp__evalperm__approve` it is routed to evalperm, which allows it and logs one line.
- tasks/archive/x.md: denied with "Archived plan: … written only by `dt archive`".
- Duplicate `## PL-02` heading: PostToolUse returns `decision: block` with dup-id, pipeline-fields and approved-edit, and the agent sees them.
- Stop: a `systemMessage` with the 3 problems, shown as a notice ("Stop says: …"). It does not block.

## 2. build-setup implementer frontmatter hooks
- path_guard: deny on tests/intent passes (exit 2, BLOCKED message), both in place and in a worktree.
- `$CLAUDE_PROJECT_DIR` resolves to the main checkout, including inside a worktree subagent.
- Worktree subagent: hook `cwd` and `$PWD` are `<proj>/.claude/worktrees/agent-<id>`. project_root.sh picks the worktree and the gate runs there.
- stop_gate: arrives as SubagentStop with agent_id. It blocks with JSON 3 times, then sends a systemMessage, and the counter file is removed. Passes.
- `..` in file_path is normalised by Claude Code before the hook sees it.
- FAIL, fixed: the SubagentStop systemMessage isn't shown in the TUI main view (only "Agent … finished"), and the parent isn't told. Fix: the third block now tells the agent to start its report with "GATE FAILED: scripts/check.sh <mode>". Verified live: the parent's agent result starts with that line.
- FAIL, fixed: worktrees under .claude/worktrees/ aren't gitignored, so the main checkout's gate linted, formatted and deptry-scanned the worktree copies, which added DEP004 failures. Added `.claude/worktrees/` to gitignore.additions.
- Confirmed: `claude -p` in a never-trusted folder skips frontmatter hooks silently, and the implementer wrote tests/intent unblocked. In a trusted folder they fire under -p too.
- Note: the Agent tool backgrounds subagents by default, and the parent's Stop hook can run before the subagent finishes.

## 3. Eval smoke
- `MAX_TURNS=1 driver.py rl-all-at-once …` (opus, $0.34): plugin loaded, all 7 dev-team2:* skills in session_init, evalperm connected, idea-refine invoked.
- FAIL, fixed: the driver didn't pass `--include-hook-events`, so hook_events counted only SessionStart. Added the flag. The fake-CLI loop and a haiku smoke still work.
- Full run (not launched): `evals/harness/run.sh iteration-5`

## Files changed (uncommitted)
skills/build-setup/templates/scripts/hooks/stop_gate.sh, templates/gitignore.additions, tests/test_scripts.py (33/33 pass), references/tools/hooks.md, design/build-setup.md, evals/harness/driver.py, evals/README.md
