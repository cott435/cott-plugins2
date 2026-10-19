# Driver segment 30 · `/dev-team:pipeline-design From the previous session:
<<<
The architecture and the rllab contract are now Approved, and AD-25 (the random agent is built for one side) is Accepted. AD-25 doesn't depend on any external probe. I also marked the change test-planning sent here as done.

Three files have uncommitted changes: `docs/architecture.md`, `docs/packages/rllab/contract.md` and `docs/routes.md`. Want me to commit them?

The next step is `/dev-team:pipeline-design`, which has two changes waiting:
- **Random agent's step:** update it to take the `Side` (PL-01, PL-02, PL-05).
- **Cross-play tables (from test-planning):** PL-04 should also build them for unfinished runs that saved at least one generation per side, and list them as incomplete (TC-57).
>>>

Approved, looks good. Yes, commit them.`

- **Steps:** D975–D991 · **definition:** `/Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/skills/pipeline-design/SKILL.md`
- **Units spawned here:** none

## Steps

- `D975` **USER TYPED** `/dev-team:pipeline-design From the previous session:
<<<
The architecture and the rllab contract are now Approved, and AD-25 (the random agent is built for one side) is Accepted. AD-25 doesn't depend on any external probe. I also marked the change test-planning sent here as done.

Three files have uncommitted changes: `docs/architecture.md`, `docs/packages/rllab/contract.md` and `docs/routes.md`. Want me to commit them?

The next step is `/dev-team:pipeline-design`, which has two changes waiting:
- **Random agent's step:** update it to take the `Side` (PL-01, PL-02, PL-05).
- **Cross-play tables (from test-planning):** PL-04 should also build them for unfinished runs that saved at least one generation per side, and list them as incomplete (TC-57).
>>>

Approved, looks good. Yes, commit them.`
- `D976` skill loaded from `/Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/skills/pipeline-design`
- `D977` **Bash** git status --short && git add docs/architecture.md docs/packages/rllab/contract.md docs/routes.md && git commit -q -m "Approve architecture and rllab contract; accept AD-25 (random agent built for one side)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log --oneline -1; python3 ../plugin/dev-team/scripts/dt.py status --skill pipeline-design
      ↳ COMMIT UNCONFIRMED — HEAD after the call was (sha not shown); check `git show --stat (sha not shown)`
      ↳ …[796 chars] e generation per side, so write_tables lists them as incomplete (TC-57) (from test-planning), baselines.RandomAgent now takes the Side it plays (AD-25): its step's In is Side → Agent, not name → Agent, and it draws from that side's moves rather than 'the side of the id asked'; load_agent's random branch builds RandomAgent(side) (PL-01, PL-02, PL-05) (from architecture-design) ⏎ requests_open: none
- `D978` **Bash** git show --stat HEAD | head -20; cat ../plugin/dev-team/skills/pipeline-design/references/revise.md
      ↳ …[3498 chars]  ask which changes: ⏎ - **The doc changes** when the code found a better order or a real extra step. Edit the table (as Revise), Status to Draft. ⏎ - **The code changes** when it broke a rule: logic in the entry, a step owned by two components, a registry with no AD. Leave the doc, and list the fix for `build-planning` Replan. ⏎ Never rewrite the table to match code that breaks a readability rule.
- `D979` **Bash** cat ../plugin/dev-team/skills/pipeline-design/references/steps.md | sed -n '/Changing a step table/,/^## [^C]/p'; grep -n "PL-0[1245]\|RandomAgent\|random\|play_tables\|write_tables\|incomplete\|Status\|^##\|^| " docs/packages/rllab/pipelines.md | head -150
      ↳ …[25323 chars] ⏎ 222:## Planned layout (pre-build — removed by spine task) ⏎ 226:  __main__.py   CLI: train → PL-01, baselines → PL-02, curves → PL-03, study → PL-04, replay → PL-05, notes → PL-06, crossplay → PL-07 ⏎ 244:  replay/     __init__.py  pipeline.py (PL-05 entry)  specs.py  record.py  window.py ⏎ 247:  cli/        __init__.py  pipeline.py (PL-01 entry)  args.py ⏎ 251:## Open questions ⏎ 253:## Retired
- `D980` **Bash** grep -n "RandomAgent\|incomplete\|class CrossTable\|build_table\|play_tables" docs/packages/rllab/contract.md | head -30; grep -n "AD-25" -A6 docs/architecture.md | head -20; python3 ../plugin/dev-team/scripts/dt.py section CROSS-02 2>/dev/null | head -20; grep -rn "Step:.*PL-0[1245]\.\(RandomAgent\|load_agent\|play_tables\|write_tables\)\|Read:.*PL-04" tasks/plan.md tasks/todo.md 2>/dev/null | head
      ↳ …[8007 chars] d | AD-25 | ⏎ <!-- docs/spec.md:295 --> ⏎ - **CROSS-02** The table is shown with predator generations as rows and prey generations as columns, one table per rung averaged over its 5 training seeds, built from saved generations only, never by training again. ⏎   - Given the 5 seeds of the self-play rung, when its table is shown, then each cell holds both sides' mean scores over the 5 seeds' tables.
- `D981` **Bash** sed -n 714,726p docs/packages/rllab/contract.md; grep -n "CROSS" docs/spec.md | grep -i "edge\|fewer\|incomplete"; grep -n "Step:\|Read:" tasks/todo.md tasks/plan.md | grep -i "RandomAgent\|load_agent\|play_tables\|write_tables\|make_run\|PL-04\b" | head
      ↳ …[1375 chars] oundary:** study, cli · **Fixtures:** tests/contracts/crossplay.build_table/ · **Cases:** a finished 20-game chase run with 2 generations per side; a run with no generations (refused) ⏎ - **Used by:** study, cli; PL-04, PL-07 ⏎ 303:- A run has fewer than 10 generations saved → its table covers the saved ones, is marked incomplete, and the run is left out of the CROSS-03 comparison, which names it.
- `D982` _said:_ Those three files were already committed in `c5faac8` and the tree is clean. Now I'm revising the step tables for the two routed changes.
- `D983` **Bash** python3 - <<'EOF'
p='docs/packages/rllab/pipelines.md'
s=open(p).read()
old1="| 22 | `load_agent` | registry.agents | agent spec, Env, side → Agent | `random` → `RandomAgent`;"
new1="| 22 | `load_agent` | registry.agents | agent spec, Env, side → Agent | `random` → `RandomAgent(side)` (AD-25);"
old2="| 23 | `RandomAgent` | baselines.uniform | name → Agent | uniform over `range(n)` for Choices, each control uniform within its limits for Controls, reading the side of the id asked; generator reseed …[+2393 chars]
      ↳ 3 ⏎ 11:- **Used by:** snake, corridor, tank, agent, baselines, evaluate, registry ⏎ - **Used by:** registry; PL-01, PL-02, PL-05 ⏎ 655-- **Used by:** study, cli; PL-01, PL-04 ⏎ 662-- **Used by:** replay, study, crossplay, cli; PL-01, PL-02, PL-04, PL-05, PL-07
- `D984` **Bash** D="python3 ../plugin/dev-team/scripts/dt.py"; $D status --skill pipeline-design | grep -E "mode|uncovered|unowned|retired|drift|routed"; $D explain --write 2>&1 | tail -3; grep -nE "PL-0[1245]\.(RandomAgent|load_agent|make_run|play_tables|write_tables)|Read:.*PL-0[1245]" tasks/todo.md tasks/plan.md | head -20
      ↳ …[3006 chars]  registry.make_agent ⏎ tasks/plan.md:206:**Read:** PL-01, AGENT-04, ABL-01, agent.DQNAgent, agent.AgentConfig, core.Transition, src/rllab/agent/dqn/memory.py ⏎ tasks/plan.md:216:**Read:** PL-01, AGENT-05, ABL-02, agent.DQNAgent, agent.AgentConfig, src/rllab/agent/dqn/targets.py ⏎ tasks/plan.md:226:**Read:** PL-01, AGENT-02, ABL-03, agent.DQNAgent, agent.AgentConfig, src/rllab/agent/dqn/schedule.py
- `D985` **Bash** python3 ../plugin/dev-team/scripts/dt.py status --skill pipeline-design | grep -E "mode|uncovered|unowned|retired|drift|routed"; python3 ../plugin/dev-team/scripts/dt.py explain --write 2>&1 | tail -3; grep -nE "RandomAgent|load_agent|make_run|play_tables|write_tables|PL-0[245]" tasks/plan.md tasks/todo.md | head
      ↳ …[674 chars] ndomAgent(side) (PL-01, PL-02, PL-05) (from architecture-design) ⏎ docs/explained/rllab.md ⏎ tasks/plan.md:323:- `boundaries_unfrozen` lists the tank, line, pg, baselines, `registry.load_agent`, curves, replay and study symbols, and the tank/line cases of core types: none is on an M1 step, so M2–M6's interface tasks freeze them (M4 adds the seeded tank and line cases to the core contract folders).
- `D986` _said:_ I've made both changes to `docs/packages/rllab/pipelines.md` and set it back to **Draft** until you approve. ⏎ **Commit:** there was nothing to commit. `docs/architecture.md`, `contract.md` and `routes.md` were already committed in `c5faac8`, and the working tree was clean. ⏎ ## 1. What was written ⏎ - **PL-01, Train an agent:** ⏎   - The `RandomAgent` step now takes the `Side` it plays. It picks only from that side's moves, and its `kind` follows them (AD-25). It no longer works out the side from the id it's asked about. ⏎   - In `load_agent`, `random` now builds `RandomAgent(side)`. ⏎   - `m …[+2070 chars]
- `D987` HOOK SessionStart:resume said: milestone: M1 Train an agent · plan Approved ⏎ progress: 0/22 · next: M1-T01 M1 interface ⏎ blocked: none ⏎ draft (waiting for approval): docs/packages/rllab/pipelines.md ⏎ roadmap: Status* column stale (run dt roadmap) ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/scripts/dt
- `D988` **USER:** Approved, looks good.
- `D989` **Bash** sed -i '' 's/\*\*Status:\*\* Draft · \*\*Last updated:\*\* 2026-10-19/**Status:** Approved · **Last updated:** 2026-10-19/' docs/packages/rllab/pipelines.md && head -3 docs/packages/rllab/pipelines.md | tail -1; python3 ../plugin/dev-team/scripts/dt.py route --done pipeline-design; python3 ../plugin/dev-team/scripts/dt.py status --skill pipeline-design | grep -E "mode|routed"; python3 ../plugin/dev-team/scripts/dt.py next; git status --short
      ↳ …[1635 chars] runs.LossPoint (M1-T11), runs.RunConfig (M1-T02, M1-T08, M1-T10, M1-T11, M1-T22, M1-T14, M1-T19), runs.RunRecord (M1-T08, M1-T11, M1-T14, M1-T19), runs.RunWriter (M1-T08, M1-T10, M1-T11, M1-T14, M1-T19), runs.load_record (M1-T10), snake.SnakeEnv (M1-T04), train.train_run (M1-T08, M1-T14) ⏎ waiting on user: no ⏎ run: /dev-team:build-planning ⏎  M docs/packages/rllab/pipelines.md ⏎  M docs/routes.md
- `D990` _said:_ `docs/packages/rllab/pipelines.md` is now **Approved** (2026-10-19). The two waiting changes, the random agent taking its `Side` and the cross-play tables for unfinished runs, are marked done, so nothing is left waiting for pipeline-design. ⏎ Two files have uncommitted changes: `docs/packages/rllab/pipelines.md` and `docs/routes.md`. Want me to commit them? ⏎ The next step is `/dev-team:build-planning`, to replan. It has two jobs: ⏎ - **Cut S3 (predator-prey and self-play) into milestones.** ⏎ - **Re-check the M1 plan** against the changed pipelines, tests and contract. A long list of M1 tasks …[+95 chars]
- `D991` HOOK SessionStart:startup said: milestone: M1 Train an agent · plan Approved ⏎ progress: 0/22 · next: M1-T01 M1 interface ⏎ blocked: none ⏎ roadmap: Status* column stale (run dt roadmap) ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/scripts/dt
