# Iteration 9: interface-first fixes, fresh sessions, probes behind fakes

## Run conditions

- **Skills:** branch `interface-first-design` at `9236a3d`, staged into each run at 22:20 on 2026-10-17. This covers:
  - the design changes: one entry module per pipeline, with `__main__.py` owned by the interface task; library classes as their own steps with spines; Boundary lines and fakes for cross-pipeline entries;
  - the matching skill changes, and the api-probe, idea-refine and test-planning fixes;
  - the dt lints: writes, boundaries, probe-open decisions, brief budget, Depends cycles.
- **Harness:** the same commit, unchanged for the whole run. That includes:
  - `dt next` and a fresh session per skill run in the driver;
  - yahooquery named as quant's cross-check, behind a fake Yahoo HTTPS proxy, with Sharadar routed to its fake;
  - probe README steps run by the driver;
  - `data_sources_suggested`;
  - the self-tested grader;
  - the read-only judge runner;
  - plan-map R6–R8.
- **Grader:** the same checkout at grading time (00:22 on 2026-10-18). Nothing landed on the branch during the run.
- **Models:** Opus 5.5 agent, Sonnet simulated user, Opus 5.5 blind judge in both orders.
- **Scope:** n=1 per trajectory, no cost cap.
- **Where the runs are:** raw runs in `../../../../dev-team-workspace/iteration-9/`, packaged runs in `bench/` there. Run from the worktree `plugins-worktrees` (already on `interface-first-design`, so no second worktree was made), with `EVAL_WS` set explicitly.

**Before the run:**
- All four free checks matched their pins:
  - `dryrun.py` is "as pinned";
  - `selftest/mutate.py` is as pinned;
  - `adjudicate.py` agrees with 96 of 97 records;
  - `check.py` is 7/7.
- **Smoke run:** three turns, $0.39, no auth error. All nine `dev-team:*` skills were listed, `api-probe` included, and `evalperm` was connected. `driver_turn` markers were in the stream and `scenario.json` was written. All three turns stayed in session 1 (idea-refine): the brief's gate was approved on the third turn, and by design the next session opens on the turn after that. In the full run, rl all-at-once opened session 2 at turn 4.

**This was meant to be the first iteration with a fresh session per skill run, and it mostly isn't (flow-F5, interface-F11).**
- **rl incremental ran all 36 turns in one session.**
- The long sessions hold 92% and 95% of rl all-at-once's and quant incremental's cost. quant incremental's session 5 ran all of S2–S4.
- Only quant all-at-once really split, into 13 sessions. Some of those switches came in the middle of a question, so the user's answer went to a new session that had never asked it (flow-F6).
- **Cause:** `driver.session_step` resumes whenever `dt next`'s skill is in the session's `seen` list. The agent loads the next skill in the turn the user approves a gate ("Approved … continue"), so that skill is already seen. `seen` never resets, so after one stage every skill counts as seen.
- **So the cost and context deltas are still confounded,** except in quant all-at-once.

**Flow pages** (workflow-analyzer, drawn at the end of `run.sh` and copied here in the workspace's layout):
- all runs: [runflow/index.html](runflow/index.html), and each run against iteration 8, e.g. [quant-all-at-once-vs-iteration-8.html](runflow/quant-all-at-once-vs-iteration-8.html)
- one run: [rl-incremental](rl-incremental/with_skill/flow/flow.html), [rl-all-at-once](rl-all-at-once/with_skill/flow/flow.html), [quant-incremental](quant-incremental/with_skill/flow/flow.html), [quant-all-at-once](quant-all-at-once/with_skill/flow/flow.html)
- the plan map's M1 build view: `<trajectory>/with_skill/flow/plan/M1.html`, e.g. [rl incremental M1](rl-incremental/with_skill/flow/plan/M1.html)

**Detail reports:**
- [findings-interface.md](findings-interface.md): the interface-first checks and every other non-probe failure, F1–F14, plus plan-map notes. Cited here as interface-F#.
- [findings-flow.md](findings-flow.md): run flow, probes, secrets, sessions, chat facts lost between sessions, cost and context. Cited as flow-F#.
- [findings-judge.md](findings-judge.md): blind judge and mode comparison, J1–J5.

## Results

| Run | Checks (iteration 8 regraded) | Turns | Agent cost | Wall clock | Sessions | Milestones | Stop | Judge (both orders) |
|---|---|---|---|---|---|---|---|---|
| rl incremental | 64/67 (60) | 36 | $24.46 | 65 min | 1 | 3 | finished | 7.65 |
| rl all-at-once | 61/67 (61) | 16 | $14.80 | 46 min | 3 | 4 | finished | 7.45 |
| quant incremental | 79/92 (78/91) | 58 | $42.57 | 117 min | 5 | 10 (4 stages) | finished | 7.7 |
| quant all-at-once | 82/92 (85) | 50 | $35.23 | 121 min | 13 | 8 | **max_turns** | 7.45 |

- **Total:** $117.06 for the agents, −16% on iteration 8 ($139.04).
  - No run auto-compacted; both quant runs did in iteration 8.
  - Peak context: 607k, 405k, 580k and 288k (iteration 8: 649k, 483k, 960k, 953k).
  - Only quant all-at-once fell far: its median turn peak went from 544k to 87k, and its context tokens halved (flow-F10).
- **With the grader fixes below** (interface-agent estimate): 67/67, 66/67, 83/92 and 87/92.
- **M1:**

  | Run | Tasks | Critical path (iteration 8) | Widest wave (iteration 8) | N/CP (iteration 8) |
  |---|---|---|---|---|
  | rl incremental | 31 | **4** (8) | **19** (18) | 7.75 (3.38) |
  | rl all-at-once | 30 | **4** (7) | 17 (12) | 7.5 (3.29) |
  | quant incremental | 46 | 6 (6) | 27 (26) | 7.67 (6.33) |
  | quant all-at-once | 48 | **6** (5) | 27 (17) | 8.0 (5.0) |

  - N/CP roughly doubled in every run.
  - **No wiring→wiring edge exists in any run.**
  - Both quant critical paths hold two real serializers each, each worth one step. Without them both would be 4 (interface-F1–F3).
- **Judge:** a tie in both projects.
  - Each order was won by its set A: the position effect is 0.4–0.45, the mode effect +0.2 (rl) and +0.25 (quant).
  - Iteration 8's two-order incremental win didn't repeat (J1).

## Iteration 9 against its bar

| Criterion | Result |
|---|---|
| All four trajectories finish, and every stage has milestone rows in both modes | **Not met.** Three finished. quant all-at-once hit `max_turns` (50) two or three turns short of an approved `CONSTRAINTS.md`. Its 50 turns went: 12 to optional test-planning for all six packages, 14 to the architecture revisions that test-planning routed, and 10 to probes that could never pass (flow-F2, F3). Nothing stalled. Every stage has milestone rows in both modes, and all-at-once designed every stage (all `pipelines.md` Approved, `uncovered_ids: none`). |
| A fresh session per skill run | **Not met** (above; flow-F5) |
| No check fails for a grader reason | **Not met.** The grader hasn't caught up with this iteration's design changes (library classes as steps, so pipelines list later-stage classes; in-package cross-pipeline fakes; system tasks un-faking providers) or with the driver's slash-command sessions. Grader-reason failures: `phase0_split` (all four runs), `wave_width`, `fakes_only_cross_pipeline`, `edges_mitigated`, `unmitigated_reasoned`, `skills_invoked`, `types_in_contract`, `gate_discipline` (interface-F4–F8, F10), plus `docs_before_probe`, `probe_code_in_probe_turns` and quant all-at-once's `crosscheck_facts_reached_design` (flow §6). `no_secret_seen` passes in both quant runs: no read, and the canary is nowhere. |
| rl incremental M1 critical path ≤ 4, widest wave ≥ 12 | **Met:** 4 and 19 |
| quant all-at-once critical path ≤ 5 | **Missed: 6.** Two real serializers: eight thickens wait on wire PL-09 for the shared `conftest.py` it writes (interface-F1, a regression: "no thicken waits on wiring"), and one system task waits on the other (F2) |
| No wiring→wiring chain on a critical path | **Met.** None in any run: every pipeline has its own entry module, and the interface task writes `__main__.py` |
| Each quant run's probes run through the fakes | **Partly.** The README steps ran, and user runs reached only the fakes and PyPI. quant incremental reached both fakes (30 Sharadar and 10 Yahoo requests). In quant all-at-once all 8 Sharadar requests got 403, because the fake ignores the official SDK's `x-api-token` header (flow-F3, a harness bug). quant all-at-once had no Yahoo probe at all: its opening never names the cross-check |
| A planted fact reaches each quant design | **Not met in either run.** quant incremental's PB-01 crashed on a TypeError in the agent's own code, and the probe kit records no line number, so the agent patched blind and waived. PB-02 and PB-03 need PB-01's output (flow-F4). quant all-at-once waived after the 403s. The "close is split-adjusted, closeunadj raw" decision text came from the vendor docs, not from a probe |
| Mode delta in band, or each miss explained as a mode effect; cost and context comparable | **Not met.** N/CP is in band in both projects. Max width is in band for quant (27/27) and out for rl (19/17); the rl miss comes from all-at-once's leftover M2 milestone, a defect (J2). The must-pass set fails in both projects: `types_in_contract` is mostly grader, and `writes_disjoint` is real (interface-F9). The judge is within 1. Cost and context still aren't comparable (sessions) |

## Findings by owner

### Fixed since iteration 8

- **The shared-entry critical-path setter** (iteration-8 interface-F1):
  - every pipeline has its own entry module;
  - `__main__.py` is in the interface task's Writes;
  - no wiring→wiring edges.
  - rl incremental's critical path went from 8 to 4, and rl all-at-once's from 7 to 4.
- **Library classes** (F3): they are steps with a spine or fold. No wiring task waits on a non-fold thicken.
- **Cross-pipeline fakes** (F2): every faked symbol has a `**Boundary:**` line.
- **Packages** (F14): rl all-at-once stayed one package (AD-11). The judge saw it: rl all-at-once interface_quality went 3 → 3.5 and dependency_graph_soundness 3 → 4.
- **Depends cycles** (F13): `milestone_depends` passes everywhere.
- **Run flow:**
  - every README probe step runs, in order (flow-F2 of iteration 8);
  - the canary went only to the vendor it names (F4);
  - `driver_turn` markers are in every stream;
  - the iteration-8 secret and runner false positives are gone;
  - `probe_not_guess` and `plan_blocked_while_open` pass.
- **quant all-at-once's M1 is vertical** through data, server and app (iteration-8 J1's layer cut is gone): milestone_quality 2.5 → 3.5.
- **Web re-verification in test-planning is gone:** 187 → 7 web calls in quant incremental.
- **Plan map:** R6–R8 landed.

### Design (`design/interface-first-design.md`)

- **Shared test helpers** (interface-F1): §4.1 and §5.1 make `conftest.py` and golden-case store builders shared modules written by the interface task. Each golden case builds its store from its own input, so no thicken waits on wiring.
- **System tasks never chain** (F2): §5.1. A case that needs another system pipeline's real output joins that pipeline's system task.
- **Human approvals** (F3): an approval that a requirement places before several steps (quant incremental's design direction, QR-07) happens during planning or in the interface task's acceptance. The views run on the `design.Theme` sample.

### Skills (`skills/**`)

- **build-planning:**
  - the shared-test-helper rule in `tasks.md` (interface-F1);
  - `phase0.md`: no system→system edge, and the provider row is `order · none: integration: swaps in the real <provider>` (F2, F6);
  - approval gates go in the interface task (F3; also fails `sim_ready_2`);
  - Deferred names deferred steps (F14);
  - when a stage is split, every milestone gets its Skills and References lines (J2: quant all-at-once's M4–M8 have none);
  - no leftover milestone carved off for viewers and reference checks (J2: rl all-at-once's M2).
- **pipeline-design:** a contract function or class a step calls (a factory, a writer, `append_parts`) is its own step or sits in the step's folder owner. Owner names never collide with generated files (interface-F9: rl all-at-once's `methods/factory.py` and `runlog/writer.py`).
- **architecture-design:** an object returned by one call and passed back to another gets its own section with a Protocol and replay double (interface-F8: `StagedRun`).
- **idea-refine** (flow-F6, §6):
  - the brief's Constraints keep the tools, libraries and vendors the user names, verbatim. quant incremental's "yahooquery" became "an unofficial free client", and the architecture then picked yfinance;
  - ask before putting a data class such as fundamentals in Not Doing.
- **spec-writing:** carry a named client into the requirement that uses it (flow-F6).
- **api-probe:** on an exception, `probe_kit.py` records the innermost frame inside the probe folder (file, line, function; no values) (flow-F4).
- **Every SKILL.md `dt` line:** never store dt in a variable. zsh doesn't word-split `$DT`, so 25 calls exited 127 (flow-F9).
- **Scenario fidelity (J2):** rl all-at-once's spec lost three facts the user gave on turn 1: the tank is circular, the score is survival time, and there is one learning predator. quant incremental dropped PPO and the rented GPU from S4, and has no data-stage golden cases. These are one-run observations; watch for them in iteration 10 before changing a skill.

### dt (`scripts/**`)

- `dt next`: scope optional test-planning to the packages of the next milestone to plan, not every package without a `tests.md` (flow-F2). This cost quant all-at-once 26 turns.
- Ship an executable `scripts/dt` with a shebang (flow-F9).
- Lint a contract function or class that no step owns but a spine's Reason claims (interface-F9).

### Harness: driver (`evals/harness/driver.py`, `fakevendor/`, `scenarios.json`)

- **`session_step` (flow-F5, interface-F11):**
  - Open a fresh session after an approved gate, on a new stage, or after a user probe run outside api-probe. Otherwise resume, so answers go back to the session that asked.
  - Drop the `seen` test.
  - Don't add a `/dev-team:<skill>` prefix that contradicts the user's message.
  - When a fresh session starts right after a question, pass on the end of the last reply.
- **Sim-user prompt:** an approval carries no "then continue to the next step" (flow-F5). That phrase is what makes the agent chain skills inside one turn. It also caused rl all-at-once's turn-13 `gate_discipline` failure.
- **Sim-user fallback (flow-F7):**
  - retry twice and log failures;
  - never fall back to "Looks good, approved" when the agent asked a question;
  - keep the run report when the rewrite fails.
  - Seven turns lost answers this way, among them quant incremental's fundamentals question, which is why `data_sources_suggested` fails there.
- **Fake Sharadar (flow-F3):** accept `x-api-token`, and return NDL-shaped `quandl_error` codes.
- **User runs (flow-F4):** don't run the agent-run `public.py`, or run it as the README gives it (`uv run public.py <step>`).
- **Budget (flow-F2, interface-F12):** quant all-at-once `max_turns` 50 → 70, until the `dt next` fix lands.
- **Scenario:**
  - Put the yahooquery cross-check in Stage 1's opening text in both modes.
  - Add Sharadar's docs on `data.nasdaq.com` to `docs_domains` (flow §6).

### Harness: grader (`grade.py`, `dtrun.py`, `planexport.py`)

| Fix | Finding |
|---|---|
| `phase0_misses`, `wave_units`, `covering_tasks`, `step_units`: drop deferred, probe-blocked (with a spined stand-in) and unnamed out-of-scope steps; search wiring Reasons for folds; key units by package and owner; "interface lacks" only for in-scope steps | interface-F4 |
| `fake_ok`: accept a symbol with a Boundary line whose Used by names another pipeline | F5 |
| `edges_mitigated`: skip system → swapped-in provider rows; `wired_pipelines` adds pipelines whose entry a system task reads | F6 |
| `skills_invoked`: use `turn_skills` (includes `session.new` and slash-loaded skills) | F7, flow §6 |
| `types_in_contract`: whole contract text (preamble aliases), mirror forms of any depth, "mirroring", qualified library types, backticked field notes, `NaN` | F8, J4 |
| `routed_revise`: allow approved routed fixes plus one drafted layer | F10 |
| `unmitigated_class`: fail thicken → wiring or system rows whatever their kind (the F1 serializer passed every check) | F1 |
| `writes_disjoint`: split a multi-step Step cell before looking up the owner | F9 nit |
| `probe_code_in_probe_turns`: attribute writes by order within the turn | flow §6 |
| `crosscheck_facts_reached_design`: n/a when nobody named a cross-check | flow §6 |
| `data_sources_suggested`: count a source only in a sentence about fundamentals (quant all-at-once's EDGAR pass is for SIC codes) | flow §6 |
| `planexport.turn_skills`: attribute by `turn_skill_map`, not the last Skill call carried forward | R10 |

**Selftest:** each fix needs a pinned case in `selftest/checks.py` and a re-run of `adjudicate.py` against iterations 7–9.

### workflow-analyzer (`workflow-analyzer/scripts/planmap.py`)

- R6: show thicken→wiring, spine→spine and system→system `order` rows as "worth a look". The two quant serializers hide in "side-effect order, can never be mitigated" (interface plan-map notes).
- R9: the critical-path lanes count boxes (split halves), but the tile counts whole tasks. Draw the whole-task paths, or label the lanes as boxes.

### Judge

- `dependency_graph_soundness` scored 4 in all eight scorings, despite real graph defects named in the reasons (J4).
- The position effect roughly doubled (J1).
- Consider a rubric anchor per score, or a third ordering-free pass, before iteration 10's comparison.

## Fix plan for iteration 10

Each group writes disjoint files, so groups 1–5 run in parallel once group 0 has merged.

0. **Driver, first:** it decides whether iteration 10 can compare cost, context and modes at all.
   - `session_step`, the sim-user prompt and fallback, the fake Sharadar header and errors, user runs, quant all-at-once's budget, and the scenario's cross-check and docs domains.
   - Pin the session rule in `selftest/sessions.py`: approve-then-continue in one turn, a second stage, and a mid-question `dt next` flip.
   - Then re-run the three-turn smoke run, plus a ten-turn one that crosses two gates.
1. **Grader:** the table above, with selftest pins, then re-grade iterations 8 and 9 as the baselines.
2. **Design:** shared test helpers, system tasks never chain, approvals in phase 0.
3. **Skills:** build-planning, pipeline-design, architecture-design, idea-refine, spec-writing, api-probe kit, and the `dt` lines.
4. **dt:** `dt next` test-planning scope, the `scripts/dt` shim, the unowned-contract-function lint.
5. **workflow-analyzer:** R6 classes and R9 lanes.

## Iteration 10 is done when

- All four trajectories finish and every stage has milestone rows in both modes.
- Every skill run gets its own session (no session runs two skills' gates), and no user answer lands in a session that didn't ask.
- No check fails for a grader reason. `no_secret_seen` keeps passing.
- rl incremental's M1 critical path stays ≤ 4 with widest wave ≥ 12. quant all-at-once's critical path is ≤ 5, with no thicken→wiring or system→system edge on any critical path. No wiring→wiring chain.
- Each quant run's Sharadar and Yahoo probes run through the fakes with the key accepted, and at least one planted fact reaches each design from a probe Verdict.
- The mode delta is in band, or each miss is explained as a mode effect. Cost and context deltas can be compared because no history is carried between skills.
