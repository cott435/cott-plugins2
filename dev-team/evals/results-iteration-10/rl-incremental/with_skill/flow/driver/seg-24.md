# Driver segment 24 · `/dev-team:idea-refine From the previous session:
<<<
at M3's first task fixes up front, not on the tank training code being finished. My rough longest chain is about 9 tasks: interface → TankEnv → PGAgent's four rungs → PPO tuning → system check. The limit is 15, and the rule is that a stage that fits in one milestone gets one.
- **Depends on M2, not just M1.** M3 reuses M2's compare and replay entry points. Also, TC-37's snapshot of saved Snake runs has to be made by the accepted S1 build, before any S2 code lands (UR-72).
- **Grow check:** no triggers. The tank adds only NumPy, which is already a dependency. AD-01, UR-34 and UR-65 record the decision to keep a single package.
- Skills `null-hypothesis-testing` and `dataviz` come from the S2 stage, so nothing is left unrouted. No references.

## Open questions
- **Recommendation:** keep the one-milestone cut, unless you'd rather mirror S1's train / compare-and-replay split as M3 + M4.
- **M1's plan needs a Replan next.** Its contract changed after the plan was committed (the AD-11, AD-15 and TANK-10 updates for the tank), and `dt status` now flags most of M1's fixed interfaces as changed (`interfaces_changed`): core.Env, core.Agent, core.Learner, store.RunSettings and others. That's the next build-planning run, before `build-setup`.
- `dataviz` still isn't installed.

## Uncovered
These S2 spec IDs still show as uncovered, all targeting M3 until its plan is written: TANK-01–TANK-13, PG-01–PG-04, PG-06–PG-08, BASE-04–BASE-07 and RUN-09.

Do you approve the cut, or want changes?
>>>

Approved, keep the one-milestone cut. Next idea: Environment 3 is predator-prey foraging. Prey fish forage for food pellets while a learning predator hunts them, and both sides learn at the same time, so it's multi-agent and non-stationary. The concept is co-evolution / self-play: how each side's learning changes what the other has to learn.`

- **Steps:** D650–D674 · **definition:** `/Users/connorott/plugins/dev-team-workspace/iteration-10/rl-incremental/with_skill/plugin/dev-team/skills/idea-refine/SKILL.md`
- **Units spawned here:** none

## Steps

- `D650` **USER TYPED** `/dev-team:idea-refine From the previous session:
<<<
at M3's first task fixes up front, not on the tank training code being finished. My rough longest chain is about 9 tasks: interface → TankEnv → PGAgent's four rungs → PPO tuning → system check. The limit is 15, and the rule is that a stage that fits in one milestone gets one.
- **Depends on M2, not just M1.** M3 reuses M2's compare and replay entry points. Also, TC-37's snapshot of saved Snake runs has to be made by the accepted S1 build, before any S2 code lands (UR-72).
- **Grow check:** no triggers. The tank adds only NumPy, which is already a dependency. AD-01, UR-34 and UR-65 record the decision to keep a single package.
- Skills `null-hypothesis-testing` and `dataviz` come from the S2 stage, so nothing is left unrouted. No references.

## Open questions
- **Recommendation:** keep the one-milestone cut, unless you'd rather mirror S1's train / compare-and-replay split as M3 + M4.
- **M1's plan needs a Replan next.** Its contract changed after the plan was committed (the AD-11, AD-15 and TANK-10 updates for the tank), and `dt status` now flags most of M1's fixed interfaces as changed (`interfaces_changed`): core.Env, core.Agent, core.Learner, store.RunSettings and others. That's the next build-planning run, before `build-setup`.
- `dataviz` still isn't installed.

## Uncovered
These S2 spec IDs still show as uncovered, all targeting M3 until its plan is written: TANK-01–TANK-13, PG-01–PG-04, PG-06–PG-08, BASE-04–BASE-07 and RUN-09.

Do you approve the cut, or want changes?
>>>

Approved, keep the one-milestone cut. Next idea: Environment 3 is predator-prey foraging. Prey fish forage for food pellets while a learning predator hunts them, and both sides learn at the same time, so it's multi-agent and non-stationary. The concept is co-evolution / self-play: how each side's learning changes what the other has to learn.`
- `D651` skill loaded from `/Users/connorott/plugins/dev-team-workspace/iteration-10/rl-incremental/with_skill/plugin/dev-team/skills/idea-refine`
- `D652` **Bash** python3 ../plugin/dev-team/scripts/dt.py status --skill idea-refine 2>&1 | head -80; ls docs docs/ideas; cat /Users/connorott/plugins/dev-team-workspace/iteration-10/rl-incremental/with_skill/plugin/dev-team/skills/idea-refine/references/extend.md
      ↳ …[6192 chars] dea is frozen.** It records why the feature was added, as it stood that day. `spec-writing` adds a one-line banner saying so, and nobody edits the file afterwards. The spec is the current description. When a new idea changes what a `Specced` one describes, such as a narrowed holdout or a merged stage, the new idea gets its own file and names the old one under *Touches*. The old file is not edited.
- `D653` **Bash** cat docs/brief.md docs/roadmap.md docs/ideas/fish-tank.md; cat ../plugin/dev-team/skills/idea-refine/references/ideation.md ../plugin/dev-team/skills/idea-refine/references/requests.md ../plugin/dev-team/skills/idea-refine/references/roadmap.md 2>&1 | head -300
      ↳ …[19662 chars]  S1: [Name] ⏎ **Outline:** [What the user can do when this stage is done, in one sentence.] ⏎ **Skills:** [skill names routed to this stage, comma-separated, or —] ⏎ ``` ⏎ Add stages; never renumber, reorder or edit existing ones. A roadmap from before stages has only a milestone table (with a Source column): add the stage table above it for the first new stage, and leave the old rows as they are.
- `D654` **Bash** grep -n -i "cut" ../plugin/dev-team/skills/build-planning/SKILL.md | head -30; python3 ../plugin/dev-team/scripts/dt.py request list 2>&1 | tail -25; git log --oneline -3 -- docs/roadmap.md; git show --stat HEAD | head
      ↳ …[9198 chars] ] · architecture → AD-15, pg.UpdateLog, pg.discounted_returns, pg.move_weights, pg.gaussian_log_prob, pg.ppo_objective, pg.minibatch_plan ⏎ 38b252a turn 52 ⏎ 95be172 turn 40 ⏎ a461b38 turn 35 ⏎ commit 38b252a3b4a129493158ff9cb0b8de4fd1f343ab ⏎ Author: eval <e@e> ⏎ Date:   Sun Oct 18 16:43:34 2026 -0400 ⏎     turn 52 ⏎  docs/roadmap.md | 9 ++++++++- ⏎  1 file changed, 8 insertions(+), 1 deletion(-)
- `D655` **Bash** D="python3 ../plugin/dev-team/scripts/dt.py"; 
python3 ../plugin/dev-team/scripts/dt.py request add plan "Approved, keep the one-milestone cut." --skill idea-refine --about "S2 cut: one milestone M3 Fish tank (vs mirroring S1 as M3 train + M4 compare-and-replay)" &&
python3 ../plugin/dev-team/scripts/dt.py request add spec "Environment 3 is predator-prey foraging." --skill idea-refine &&
python3 ../plugin/dev-team/scripts/dt.py request add spec "Prey fish forage for food pellets while a learning …[+711 chars]
      ↳ …[417 chars] ⏎ examples-data.md ⏎ examples-extend.md ⏎ examples-ml.md ⏎ examples-new.md ⏎ examples-process.md ⏎ extend.md ⏎ frameworks.md ⏎ ideation.md ⏎ new.md ⏎ refinement-criteria.md ⏎ requests.md ⏎ roadmap.md ⏎ 28:- A ball that speeds up, more than one ball, or a ball that learns to hunt. ⏎ 184:- **RUN-08** Training, testing, saving evidence and replay work for a second environment without changes to them.
- `D656` _said:_ I recorded the M3 cut approval as UR-74. The M3 row was already written, so nothing else in the roadmap changes. M1 still needs its Replan before `build-setup`, and this idea doesn't hold that up. ⏎ Your new idea is recorded word for word as UR-75 to UR-79. ⏎ ## Environment 3: predator-prey foraging ⏎ **In project terms:** this adds a third environment where prey fish forage for pellets while a predator hunts them, with both sides learning. You'd see and measure how one side's learning changes the problem the other side has to solve. ⏎ **How might we** make an arms race between two learners so …[+3576 chars]
- `D657` HOOK Stop said: {"systemMessage": "dt lint: 2 problems\ndocs/requests.md:24: request-number UR-18 says '7', which TAB-01, DQN-02, DQN-03, DQN-04, BASE-02, SHAPE-01 doesn't state: honour the number, or change it with the user's yes\ndocs/requests.md:51: request-number UR-45 says 'four', which CR-23, CR-40, CR-41, CR-42 doesn't state: honour the number, or change it with the user's yes"}
- `D658` HOOK SessionStart:resume said: milestone: M1 Train a run · plan Approved ⏎ progress: 0/20 · next: M1-T01 M1 interface ⏎ blocked: none ⏎ requests: 5 not honoured → spec-writing ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-10/rl-incremental/with_skill/plugin/dev-team/scripts/dt
- `D659` **USER:** 1. (c), the ladder 1 → 2 → 3 with variation 4 as the control. ⏎ 2. Yes, same tank, moves and PPO, learning predator replaces the ball. ⏎ 3. As stated: 1 predator, 5 prey, shared prey brain, separate predator brain, pellets respawn elsewhere. ⏎ 4. Both of those. ⏎ 5. Same short view for everyone.
- `D660` **Bash** python3 ../plugin/dev-team/scripts/dt.py request add spec "1. (c), the ladder 1 → 2 → 3 with variation 4 as the control." --skill idea-refine --about "Environment 3 mechanism: (a) both learn at once only, (b) past-versions self-play only, (c) ladder 1 both learn at once -> 2 take turns (freeze one side, swap every N updates) -> 3 train against a pool of the opponent's past versions, with 4 (one side learns vs a scripted opponent) as the control" &&
python3 ../plugin/dev-team/scripts/dt.py reques …[+1171 chars]
      ↳ UR-80 spec: "1. (c), the ladder 1 → 2 → 3 with variation 4 as the control." ⏎ UR-81 spec: "2. Yes, same tank, moves and PPO, learning predator replaces the ball." ⏎ UR-82 spec: "3. As stated: 1 predator, 5 prey, shared prey brain, separate predator brain, pellets respawn elsewhere." ⏎ UR-83 spec: "4. Both of those." ⏎ UR-84 spec: "5. Same short view for everyone."
- `D661` **Write** /Users/connorott/plugins/dev-team-workspace/iteration-10/rl-incremental/with_skill/project/docs/ideas/predator-prey.md (78 lines)
- `D662` _said:_ I've written the idea as a Draft in `docs/ideas/predator-prey.md`. Your answers are recorded as UR-80 to UR-84. ⏎ - **Problem:** with two learners, each side's opponent changes while it learns. One learner on a world with fixed rules never shows this. ⏎ - **Direction:** five prey forage while one predator hunts, in the S2 tank with PPO. The ladder is: both learn at once → take turns → train against the other side's past versions. A run with one side learning against a scripted opponent is the control. ⏎ - **Biggest Not Doing:** no cooperative hunting with several predators, and no evolutionary …[+1371 chars]
- `D663` HOOK Stop said: {"systemMessage": "dt lint: 2 problems\ndocs/requests.md:24: request-number UR-18 says '7', which TAB-01, DQN-02, DQN-03, DQN-04, BASE-02, SHAPE-01 doesn't state: honour the number, or change it with the user's yes\ndocs/requests.md:51: request-number UR-45 says 'four', which CR-23, CR-40, CR-41, CR-42 doesn't state: honour the number, or change it with the user's yes"}
- `D664` HOOK SessionStart:resume said: milestone: M1 Train a run · plan Approved ⏎ progress: 0/20 · next: M1-T01 M1 interface ⏎ blocked: none ⏎ draft (waiting for approval): docs/ideas/predator-prey.md ⏎ requests: 10 not honoured → spec-writing ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-10/rl-incremental/with_skill/plugin/dev-team/scripts/dt
- `D665` **USER:** Accepted. Yes, route null-hypothesis-testing and dataviz to S3. Run the control in both directions, 25 runs.
- `D666` **Bash** python3 ../plugin/dev-team/scripts/dt.py request add plan "Yes, route null-hypothesis-testing and dataviz to S3." --skill idea-refine --about "S3: Predator and prey, Source ideas/predator-prey.md, Skills: null-hypothesis-testing, dataviz, no references" &&
python3 ../plugin/dev-team/scripts/dt.py request add spec "Run the control in both directions, 25 runs." --skill idea-refine --about "predator-prey control: learning predator vs scripted forager AND learning prey vs scripted chaser; 3 ladder r …[+93 chars]
      ↳ UR-85 plan: "Yes, route null-hypothesis-testing and dataviz to S3." ⏎ UR-86 spec: "Run the control in both directions, 25 runs." ⏎ S3
- `D667` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-10/rl-incremental/with_skill/project/docs/ideas/predator-prey.md | old: '**The control.** One side learns against a scripted opponent, which measures wha' | new: '**The control, run in both directions.** A learning predator against the scripte'
- `D668` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-10/rl-incremental/with_skill/project/docs/ideas/predator-prey.md | old: '- The control: run it in both directions (learning predator against the scripted' | new: ''
- `D669` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-10/rl-incremental/with_skill/project/docs/ideas/predator-prey.md | old: '**Status:** Draft · **Last updated:** 2026-10-18' | new: '**Status:** Accepted · **Last updated:** 2026-10-18'
- `D670` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-10/rl-incremental/with_skill/project/docs/roadmap.md | old: '| S2 | Fish tank | ideas/fish-tank.md | Split |' | new: '| S2 | Fish tank | ideas/fish-tank.md | Split | ⏎ | S3 | Predator and prey | ide'
- `D671` **Bash** cat >> docs/roadmap.md <<'EOF'

## S3: Predator and prey
**Outline:** Train a predator and five foraging prey that learn together in the tank, up a ladder from both learning at once to taking turns to training against past versions, with a scripted-opponent control for each side; compare each side with random and scripted bots, chart predator versions against prey versions, and watch any game as a replay.
**Skills:** null-hypothesis-testing, dataviz
EOF
python3 ../plugin/dev-team/scripts/dt.py r …[+102 chars]
      ↳ …[2544 chars] s ⏎ docs/spec.md:3: request-open UR-86 "Run the control in both directions, 25 runs." [predator-prey control: learning predator vs scripted forager AND learning prey vs scripted chaser; 3 ladder rungs + 2 controls = 5 setups x 5 seeds] is neither honoured nor changed with the user's approval: `dt request trace UR-86 <ID>`, or `dt request change UR-86` once the user approves ⏎ 11 errors, 9 warnings
- `D672` _said:_ The idea and S3 are both accepted, with the control running in both directions. ⏎ - **`docs/ideas/predator-prey.md`** is now **Accepted**. It describes the control as a learning predator against the scripted forager, and learning prey against the scripted chaser. That gives 3 rungs plus 2 controls, so 5 setups × 5 seeds = 25 runs. I removed this from the open questions. ⏎ - **`docs/roadmap.md`** has a new stage, **S3: Predator and prey**, with Source `ideas/predator-prey.md` and Skills `null-hypothesis-testing, dataviz`. Its status was set to `Idea`. No references were assigned. ⏎ - **`docs/re …[+756 chars]
- `D673` HOOK Stop said: {"systemMessage": "dt lint: 7 problems\ndocs/requests.md:24: request-number UR-18 says '7', which TAB-01, DQN-02, DQN-03, DQN-04, BASE-02, SHAPE-01 doesn't state: honour the number, or change it with the user's yes\ndocs/requests.md:51: request-number UR-45 says 'four', which CR-23, CR-40, CR-41, CR-42 doesn't state: honour the number, or change it with the user's yes\ndocs/roadmap.md:21: roadmap-skill S1 Skills names dataviz: not installed (.claude/skills or the plugin)\ndocs/roadmap.md:32: roadmap-skill M2 Skills names dataviz: not installed (.claude/skills or the plugin)\ndocs/roadmap.md:38: roadmap-skill S2 Skills names dataviz: not installed (.claude/skills or the plugin)\ndocs/roadmap.md:42: roadmap-skill M3 Skills names dataviz: not installed (.claude/skills or the plugin)\ndocs/roa …[+97 chars]
- `D674` HOOK SessionStart:startup said: milestone: M1 Train a run · plan Approved ⏎ progress: 0/20 · next: M1-T01 M1 interface ⏎ blocked: none ⏎ requests: 11 not honoured → spec-writing ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-10/rl-incremental/with_skill/plugin/dev-team/scripts/dt
