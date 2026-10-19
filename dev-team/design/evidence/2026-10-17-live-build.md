# Live build of buildmini M1: 2026-10-17

Claude Code 2.1.296, `claude -p --model sonnet` in a never-trusted copy of `scripts/tests/fixtures/buildmini` made with `make_live.py`. The plugin came from `--plugin-dir dev-team` (plus `--add-dir dev-team` so the skill could read its references), the tester, implementer and reviewer agents from the rendered `.claude/agents/*.md` passed as `--agents` JSON with their frontmatter hooks, `--permission-mode acceptEdits`, and the rendered `.claude/settings.json` allow rules passed as `--allowedTools`. Prompt: build M1 with the go, stop before the merge. Five runs, $2.85 in total; each failed run's cause was fixed before the next.

## Runs

| Run | Result | Cause | Fix |
|---|---|---|---|
| 1 | Stopped in 13 s, no agent | The project's 15 allow rules were ignored: "this workspace has not been trusted". Reads of the skill's own reference files, outside the project, were denied | Pass the rules with `--allowedTools`; `--add-dir` the plugin folder |
| 2 | Interface landed after a correct `writes` reject and retry; stopped at the barrier review | The reviewer wrote its findings with a Bash heredoc (denied); the driver chained `dt` calls with `;` (denied) | Reviewer: Write tool only. Skill: one `dt` command per Bash call; a missing findings file → release and re-dispatch |
| 3 | Same stop | A worktree agent's **Write tool is refused outside its worktree** ("edit the worktree copy instead of the shared-checkout path"), so `.git/dt-build/reviews/` was unreachable | `dt build submit-review <checkpoint>.<pkg> FILE`: the reviewer writes in its worktree and dt copies the file |
| 4 | Same stop | **Write into `.claude/` is denied even inside the worktree** under acceptEdits | The findings file moves to a gitignored `.dt/review.md`. The reviewers also found a real fixture flaw: M1-T04 needs `--smoke`, which only the interface's `__main__.py` could add, so the interface task now freezes it |
| 5 | **Milestone built**: 4/4 tasks landed, interface and exit reviews recorded (12 findings, 0 Critical), stopped before the merge. 284 s, $1.11 | — | — |

## Run 5 timeline (`dt-build/log.jsonl`)

```
19:48:08 reserve M1-T01.solo   → claim → finished → land 19:48:53
19:48:54 reserve review M1-T01.mini → (first reviewer's heredoc denied, released) → reserve again
19:50:19 submit-review M1-T01.mini → review recorded 19:50:23        barrier passed
19:50:24 reserve M1-T02.solo + M1-T03.tester   (one dt ready, spawned together)
19:50:28 claim M1-T02.solo     19:50:29 claim M1-T03.tester          running in parallel
19:50:45 land M1-T03.tester (tests branch)     19:50:48 land M1-T02.solo
19:50:50 reserve M1-T03.implementer + M1-T04.solo                    in parallel again
19:51:11 land M1-T03.implementer
19:51:19 reject M1-T04.solo: integration    → reserve, claim, land 19:51:49
19:51:51 reserve review exit.mini → submit-review → review recorded 19:52:36
```

## Smoke tests 1–2 (build-phase.md §12)

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | A split task end to end, build branch never red | **PASS.** M1-T03's tester landed `cf96be3 M1-T03: tests` (`Dt-Landed: M1-T03 tester`) on `dt/M1-T03-tests` only. The implementer's claim merged it; its landing `f1148da` (`Dt-Landed: M1-T03 implementer`) is the first commit on `build/M1` that adds `tests/intent/` | `git log --first-parent --diff-filter=A build/M1 -- tests/intent` → `f1148da` |
| 2 | Two worktree agents in parallel, landed one after the other | **PASS.** M1-T02 and M1-T03's tester were claimed a second apart, overlapped for ~14 s, and landed 3 s apart under the lock; M1-T03's implementer and M1-T04 overlapped the same way | timeline above |
| — | The integration gate on the merged tree | **Caught a real integration error.** M1-T04's unit test asserted the spine's `mean=None`; it passed in M1-T04's worktree and failed on the merged tree after M1-T03's mean landed. The re-dispatched agent got the rejection from `dt claim` and fixed the test | `details/M1-T04.solo-1.txt` |
| — | Retry on a `writes` reject | Run 2: the interface agent wrote a unit test outside its `Writes:`; rejected, retried with the rejection in its claim output, landed | `details/M1-T01.solo-1.txt` (run 2) |
| — | Stop gate verdict reuse | Every landing reused the Stop gate's recorded verdict for the worktree's tree hash | details files: "reused the Stop gate's verdict" |
| — | The driver's context | One short status line per agent; the driver ran only `dt` commands, one per Bash call (after the run-2 fix) | stream |

## What this changes

- **Allow rules in a project's `settings.json` apply only once the folder is trusted.** Interactive use (the user opens the project) gets them; headless runs and evals pass them with `--allowedTools`.
- **A worktree agent can write only inside its worktree, and never into `.claude/`** (its own `.claude/` included). Files an agent hands to `dt` live in a gitignored `.dt/`, and `dt` (a process, which can write anywhere the sandbox allows) moves them. `dt claim` writing `.claude/packet.md` is fine: dt is a process, not the Write tool.
- **Agents reach for Bash heredocs and chained commands**, which allow rules don't match. Prompts that say "Write tool" and "one command per call" reduce it; the retry paths cover the rest (two reviewer re-dispatches, no task lost).
- **Leftovers:** a rejected half keeps its `worktree-agent-*` branch (four after this run) and `dt/<task>-tests` stays after its implementer lands. Exit should prune them.
- **Still open:** vulture fails `check.sh full` at the interface review because stubs and fields are unused until later tasks; both reviewers rated it Important.
