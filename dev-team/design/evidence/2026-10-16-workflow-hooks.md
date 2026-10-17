# Workflows × hooks × agent types: experiment, 2026-10-16

Claude Code 2.1.292, `claude -p` (sonnet/haiku), `--permission-mode bypassPermissions`. Throwaway repo: `<scratchpad of session 18953afe>/wfx`.
- **Trust:** I accepted the trust dialog once in the TUI (via `expect`), only for that path. Claude Code wrote `hasTrustDialogAccepted: true` for it in `~/.claude.json`, and I didn't edit that file by hand.
- **Evidence:** the condensed hook logs and the main workflow's return value are in `workflow-hook-experiment-evidence.txt` next to this file. The raw `*.jsonl` (stream, hook logs) and `*.debug` files are in the scratchpad. Workflow agent transcripts are under `~/.claude/projects/-private-tmp-…-scratchpad-wfx/<session>/subagents/workflows/`.

Setup:
- `.claude/settings.json`:
  - PreToolUse Edit|Write logs the hook JSON and denies `protected/**`.
  - SubagentStart and Stop log.
  - SubagentStop logs, then blocks once per `agent_id`.
- `.claude/agents/implementer.md`, frontmatter hooks:
  - PreToolUse denies `tests/intent/**` (exit 2).
  - Stop blocks once, with JSON.
- `--agents` JSON agent `jimpl` with the same hooks.
- `--plugin-dir miniplug`: hooks.json with logging PreToolUse and SubagentStop, plus a plugin agent `pimpl` whose frontmatter has a deny hook.
- Workflows:
  - 3 agents in parallel: default; `agentType: 'implementer'`; implementer with `isolation: 'worktree'`.
  - Then 2 in sequence: implementer; default with a worktree.
  - Then a `jimpl` agent and an implementer with `schema`.

## Results

| # | Question | Result | Evidence |
|---|---|---|---|
| 0 | Is the Workflow tool available in `claude -p`? | **FAIL by default.** Missing in 2.1.292 and 2.1.299. `CLAUDE_CODE_WORKFLOWS=1` turns it on. `-p` waits for the background workflow to finish before exiting | init `tools` list; binary gate (`CLAUDE_CODE_WORKFLOWS`, `settings.enableWorkflows`, `tengu_workflows_enabled`) |
| 1a | Do settings hooks fire for workflow agents? | **PASS.** PreToolUse, SubagentStart and SubagentStop fire for all 5 agents. The `protected/**` deny held for every agent, worktree ones included | wf1 log: settings-pre ×3 for each agent; `protected/` empty |
| 1b | Do plugin `hooks.json` hooks fire for workflow agents? | **PASS.** PreToolUse and SubagentStop fire | plug, plugagent logs |
| 1c | What does the hook JSON say about the agent? | Every subagent event carries `agent_id` and `agent_type`. Values seen: `workflow-subagent` (default agent()), `implementer`, `jimpl`, `general-purpose`, `miniplug:pimpl`. The main session has neither, except under `--agent X`, where it gets `agent_type: X` and no `agent_id`. Other fields: `cwd` (the worktree when isolated), `permission_mode`, `effort`, and `agent_transcript_path` on SubagentStop. Stop and SubagentStop also carry `background_tasks` (id, type, status, agent_type) | first PreToolUse and SubagentStop inputs in wf1.hooks.jsonl |
| 2a | Can agent() use a project agent type? | **PASS.** `agentType: 'implementer'` resolves `.claude/agents/implementer.md`; `meta.json` shows `agentType: implementer`. `--agents` JSON types (`jimpl`) and plugin types (`miniplug:pimpl`) resolve too | journal and meta.json files |
| 2b | Do project/`--agents` frontmatter hooks fire for those agents? | **PASS.** The PreToolUse deny on `tests/intent/**` held, in place and in a worktree. Stop arrives as SubagentStop and blocks | `tests/intent/` only has files from non-implementer agents |
| 2c | Do plugin agent frontmatter hooks fire? | **FAIL, as documented.** `miniplug:pimpl` wrote `tests/intent/w-pimpl.txt` without being stopped. Plugin hooks.json still sees `agent_type: miniplug:pimpl` | plugagent log |
| 3a | What cwd does a workflow agent get by default? | The session's cwd, i.e. the shared main checkout. Parallel agents wrote into the same `src/` | `pwd` in each agent and hook `cwd` = `wfx` |
| 3b | Is there an isolation option? | **Yes:** `agent(…, {isolation: 'worktree'})`. Each agent gets `.claude/worktrees/<wf_id>-<n>` on branch `worktree-<wf_id>-<n>`, cut from HEAD. A changed worktree is **kept, uncommitted and not merged**, and the script gets no path or branch back. In worktree agents, hook `cwd` is the worktree and `$CLAUDE_PROJECT_DIR` is the main checkout inside hooks. `$CLAUDE_PROJECT_DIR` is empty in the agent's Bash. A built-in check refused a chained `pwd; git …` Bash call ("git in a form too complex to verify that it stays inside the worktree"); the plain commands ran | `git worktree list`; agent s-wt-default result |
| 4a | Do Stop/SubagentStop hooks fire and block workflow agents? | **PASS.** Settings SubagentStop and frontmatter Stop both blocked. Each agent stopped twice: it was blocked, it complied (SS-ACK / FM-ACK), then it was allowed | wf1 log: 2× SubagentStop for each agent |
| 4b | Does the script see the gate? | **Only indirectly.** agent() returns the agent's last text, which after a block is its reply to the block reason. Twice that reply dropped the original report ("results unchanged … SS-ACK" / "OK SS-ACK"). There is no gate status, and hook output doesn't reach the script | `par[0]`, `s1`, plug result |
| 4c | Does a gate block an agent that has a `schema`? | **FAIL: the block is ignored.** The agent ends at StructuredOutput. SubagentStop fires once per hook and returns block (it shows as `hook_blocking_error` in the agent transcript), but the agent gets no more turns, and the script gets the object, which says "No stop-hook instructions received" | agentsjson: a323d… transcript tail |
| 4d | Main session Stop while a workflow runs | Workflow always launches in the background, so the main Stop fires as soon as the main turn ends, with `background_tasks: [{type: workflow, status: running}]`, and again after the result arrives | all workflow runs: 2× settings-stop |
| 5a | Do hooks fire for background Agent-tool subagents (`run_in_background`)? | **PASS.** The settings guard, frontmatter guard and SubagentStart all fire | bg log |
| 5b | Does SubagentStop block background subagents? | **PASS.** Both the settings and the frontmatter gate blocked once, then allowed | bg log: 2× SubagentStop each |
| 5c | Does the parent see the block? | **Only the post-block final text**, via the completion notification. The main session saw no hook messages, and bg-impl's report lost its per-write detail. The parent's Stop ran while both subagents were still running, with them listed in `background_tasks` | bg result |
| 6a | Do `--agents` JSON hooks apply in `claude -p`? | **PASS** in a trusted folder, both as an Agent-tool subagent and as a workflow `agentType` | agentsjson log (fm-pre / fm-stop for `jimpl`) |
| 6b | What about `--agent jimpl` as the main agent? | Hooks apply to the main session (Stop event, `agent_type: jimpl`). Its `tools` allowlist also removed Workflow, so a role-restricted main agent can't orchestrate | mainagent result |

Not tested here:
- Untrusted folders. The sibling note found frontmatter hooks skipped in untrusted `-p`; per the background, settings and plugin hooks still run.
- The interactive TUI.
- Whether a worktree agent loads `settings.json` from the worktree or from the main checkout. They were identical here.

## Recommendation for dev-team2's build phase

1. **Put role guards in dev-team2's plugin `hooks/hooks.json`, keyed on `agent_type` from the hook input**, not in project agent frontmatter.
   - It fires for workflow agents, foreground and background Agent-tool subagents, and worktree agents.
   - It doesn't depend on frontmatter loading, which fails for plugin agents and untrusted `-p`.
   - One guard script maps `tester` / `implementer` / `reviewer` (or `dev-team2:*` if shipped as plugin agents) to allowed and protected paths. Take the root from the input `cwd`.
   - Treat `workflow-subagent`, and any other non-role type, as deny on the protected list, so a script that forgets `agentType` fails closed.
   - Project agent files stay useful for prompts, tools and model. Frontmatter hooks become an optional duplicate, not the guard.
2. **Don't use a SubagentStop gate as the way the orchestrator learns the result.** It does force the fix loop, but the script only gets the agent's last words.
   - Have `stop_gate.sh` write a verdict file (for example `.dt/gates/<agent_id or task>.json`, with mode, pass/fail and tries).
   - Make the block reason say "fix, then restate your full report".
   - After every builder agent, the workflow runs a cheap `verify` agent (low effort, with `schema`) that runs `scripts/check.sh gate` plus the protected-path diff and returns `{passed, output}`. The script branches on that. The script can't exec, so this is its only deterministic signal.
3. **Never give tester or implementer agents a `schema`**, because it silently bypasses the Stop gate (4c). Use `schema` only for read-only roles (reviewer, verify).
4. **The main-session Stop gate must skip while `background_tasks` has running entries.** Otherwise it gates a half-built tree the moment the orchestrator's turn ends (4d, 5c).
5. **Parallel groups:** `isolation: 'worktree'` works, but nothing merges.
   - The agent prompt must say to commit on its branch and return the branch name.
   - A merge stage, an agent in the main checkout, then merges the `worktree-*` branches and runs the gate.
   - `.claude/worktrees/` is already in `gitignore.additions`.
   - Tell worktree agents to run git commands one at a time (the chained-git refusal in 3b).
6. **Running headless:** evals, CI or `claude -p` builds need `CLAUDE_CODE_WORKFLOWS=1`. The desktop app and the interactive CLI already have the tool.
