# Workflow-arm runtime smoke tests: 2026-10-18

Before building `dt build workflow` (the A3-WF eval arm, build-phase.md §5): can a headless build session run a
Workflow script whose agents use the project's agent types, in worktrees, under its allow rules?

Claude Code 2.1.302, `claude -p --model claude-opus-5-5`, env `CLAUDE_CODE_WORKFLOWS=1`, with the flags
`build_driver.py` builds: `--plugin-dir`/`--add-dir` the staged plugin, `--agents` from the rendered
`.claude/agents/*.md` (`build_driver.agents_json`), `--allowedTools` the rendered allow rules
(`build_driver.allow_rules`) plus `git add`, `git commit` and `Workflow`, `--permission-mode acceptEdits`,
`--disallowedTools AskUserQuestion`, `--setting-sources project,local`, stream-json. Project: a live minilab
(`build_driver.setup`, which runs `make_live.py`) under `/private/tmp/wf-smoke/project`. Three runs, **$0.76** in total.

- **Run 1** (on `main`, $0.335, 32 s wall): the main prompt passes a script inline. Agent 1:
  `agent(…, {agentType: 'reviewer', isolation: 'worktree'})` runs `pwd`, `git rev-parse --git-dir`,
  `git rev-parse --git-common-dir`, `scripts/check.sh protected` and `python3 -c 'print(42)'` (no allow rule), and
  quotes its system prompt. Agent 2: `agent(…, {schema: {ok: boolean}, effort: 'low'})`.
- **Run 2** (on `build/M1`, one commit ahead of `main`, $0.173, 33 s): one `reviewer` agent in a worktree with a
  schema returns `git rev-parse HEAD`, `git branch --show-current`, `--git-dir`, and writes an untracked
  `notes/probe.txt`.
- **Run 3** ($0.249, 26 s): the main session runs a script file in the project's gitignored `.dt/` by
  `scriptPath` (how the A3-WF arm runs `dt build workflow`'s output); one low-effort schema agent returns the branch.

| Question | Result | Evidence |
|---|---|---|
| Is Workflow available under `-p`? | **Yes.** `Workflow` is in the init `tools`; the call returned at once ("Workflow launched in background", a task id, the transcript dir and the saved script path) | stream: `tool_result`, `task_started` (`task_type: local_workflow`) |
| Can it run a project file? | **Yes**: `Workflow({scriptPath: '<project>/.dt/hello.workflow.js'})` ran and returned `{branch: 'build/M1'}` | run 3 |
| Does `-p` wait for it? | **Yes**, as for background agents: the first main turn ended ("still running"), the `task_notification` started a second turn with the return value. Two `result` events; read the last. It waits at most `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` (600 s by default), then kills the workflow: the build driver sets it to the turn timeout | stream `result_index` 0, 1; the second has `origin.kind: task-notification` |
| Do `--agents` types resolve in `agent()`? | **Yes.** `agentType: 'reviewer'` ran as `reviewer` (meta `agentType`, the progress record) with the rendered body in its system prompt (`You review one slice…` in its transcript). The agent's own quote of its first sentence was the SDK preamble, so the files are the evidence | `subagents/workflows/<run>/agent-*.meta.json`, `workflows/<run>.json` |
| Does `agentType` compose with `schema`? | **Yes** (run 2): the reviewer returned the schema object | run 2 result |
| Does `isolation: 'worktree'` work? | **Yes.** cwd `.claude/worktrees/wf_<run>-<n>`; `--git-dir` `.git/worktrees/wf_<run>-<n>` ≠ `--git-common-dir` `.git` | run 1 |
| Where does the worktree start? | **The main checkout's HEAD**: `build/M1`'s head, not `main`. Branch `worktree-wf_<run>-<n>` | run 2: `head` = `build/M1` |
| Is an unchanged worktree removed, a changed one kept? | **Yes, both**: run 1's (no changes) is gone with its branch; run 2's (an untracked file) is kept, branch and all | `git worktree list` after each run |
| Do allow rules reach workflow agents? | **Yes.** The allowed `git rev-parse` and `scripts/check.sh protected` ran; `python3 -c` (no rule) was **denied, not asked**, and appears in the main result's `permission_denials` with the agent's id | `permission_denied` event, `agent_id` = the reviewer's |
| Do hooks fire? | SubagentStop fired for each workflow agent (the rendered settings' hook) | stream `hook_started` |
| Cost accounting | `total_cost_usd` and `modelUsage` **include the workflow agents** (output 2,124 tokens ≈ main 1,160 + agents 994, from the transcripts); `subagent_stats` counts none of them (`spawned: 0`) | result events vs the agents' transcripts |
| Odd one | A workflow agent's text return containing `.claude/settings.json` came back prefixed `[harness: subagent output matched instruction-shaped pattern(s): settings-json…]`. A schema return had no prefix | run 1 journal |

Timings (run 1): workflow launched 04:04:47.3, reviewer 04:04:47.5–04:05:00.2 (12.7 s, 5 Bash calls), schema agent
04:05:00.5–04:05:03.1, workflow done 04:05:03.2 (15.9 s); the main turns took 9.5 s and 9.9 s.

Not tested: an agent-file frontmatter hook (the Stop gate) on a workflow agent; a `dt land` from a workflow agent;
more than two agents at once (the per-workflow cap is min(16, CPUs − 2) = 10 here).

## What this changes

- The A3-WF arm can run headless with the build arms' flags plus `CLAUDE_CODE_WORKFLOWS=1` and `Workflow` allowed.
- Builders and reviewers can be spawned by `agentType` from the script, each in a worktree from the build
  branch's head, so `dt claim`'s stale-base check holds as in A3.
- Every command a workflow agent runs needs an allow rule, as for background agents (2026-10-17); a denial is
  silent apart from `permission_denials`.
- The land and dispatch agents should return through a `schema`, so no harness prefix lands in the script's data.
- Session cost from the last `result` event covers the workflow's agents; per-agent counts need the workflow
  transcripts, not `subagent_stats`.
