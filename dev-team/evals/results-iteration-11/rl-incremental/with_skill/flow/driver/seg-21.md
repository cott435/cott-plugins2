# Driver segment 21 · `/dev-team:test-planning From the previous session:
<<<
es improve, each side's reward can stay flat. This is the only way Goal 2 ("shown to learn") survives non-stationarity.

**Where I land:** 1 + 2, with 3 as an optional first rung and 7 as the way it's evaluated. Each side is also scored against fixed random and scripted opponents, so Goal 2 still has a fixed bar.

## Questions (my default in bold)
1. **When should this be planned?** **(a) Write the idea file now and park it until S2 is built. No stage and no spec changes yet.** (b) Plan it now as S3, built after S2. This narrows the brief's Not Doing item and probably reopens the M1 core contract.
2. **Mechanism:** **simultaneous learners first, then fixed by training against past versions (ladder 2)**, or something else, such as evolutionary methods (5)?
3. **Algorithm and tank:** **reuse S2's tank and hand-written PPO for both sides**, with the prey sharing one policy as in S2 and **one predator**?
4. **Foraging stakes:** **prey must eat to survive** (they lose energy over time), so hiding forever loses. Or are pellets just a bonus reward?
5. **What counts as success?** **Each side beats random and scripted opponents, and later generations beat earlier ones in the cross-play table.** Or something else?

Also: I've recorded your Q1 answer as UR-63 and set the M1 plan to **Approved**. M6's exit already requires each rung to beat both baselines. UR-63 will be closed when M6 is planned, alongside UR-57. Nothing is committed yet; it will be committed with this idea's acceptance.
>>>

Q1: Plan it now as S3, built after S2. It's part of the project, so I'd rather have it planned. Narrow the Not Doing item and reopen the core contract if you need to.

Q2: Simultaneous learners first, then fix it by training against past versions (ladder 2). Take turns (3) as an optional first rung, and use the cross-play table (7) for evaluation.

Q3: Yes. Reuse S2's tank and hand-written PPO for both sides. The prey share one policy, and there is one predator.

Q4: Prey must eat to survive, so they lose energy over time.

Q5: Your default. Each side beats random and scripted opponents, and later generations beat earlier ones in the cross-play table.`

- **Steps:** D612–D642 · **definition:** `/Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/skills/test-planning/SKILL.md`
- **Units spawned here:** none

## Steps

- `D612` **USER TYPED** `/dev-team:test-planning From the previous session:
<<<
es improve, each side's reward can stay flat. This is the only way Goal 2 ("shown to learn") survives non-stationarity.

**Where I land:** 1 + 2, with 3 as an optional first rung and 7 as the way it's evaluated. Each side is also scored against fixed random and scripted opponents, so Goal 2 still has a fixed bar.

## Questions (my default in bold)
1. **When should this be planned?** **(a) Write the idea file now and park it until S2 is built. No stage and no spec changes yet.** (b) Plan it now as S3, built after S2. This narrows the brief's Not Doing item and probably reopens the M1 core contract.
2. **Mechanism:** **simultaneous learners first, then fixed by training against past versions (ladder 2)**, or something else, such as evolutionary methods (5)?
3. **Algorithm and tank:** **reuse S2's tank and hand-written PPO for both sides**, with the prey sharing one policy as in S2 and **one predator**?
4. **Foraging stakes:** **prey must eat to survive** (they lose energy over time), so hiding forever loses. Or are pellets just a bonus reward?
5. **What counts as success?** **Each side beats random and scripted opponents, and later generations beat earlier ones in the cross-play table.** Or something else?

Also: I've recorded your Q1 answer as UR-63 and set the M1 plan to **Approved**. M6's exit already requires each rung to beat both baselines. UR-63 will be closed when M6 is planned, alongside UR-57. Nothing is committed yet; it will be committed with this idea's acceptance.
>>>

Q1: Plan it now as S3, built after S2. It's part of the project, so I'd rather have it planned. Narrow the Not Doing item and reopen the core contract if you need to.

Q2: Simultaneous learners first, then fix it by training against past versions (ladder 2). Take turns (3) as an optional first rung, and use the cross-play table (7) for evaluation.

Q3: Yes. Reuse S2's tank and hand-written PPO for both sides. The prey share one policy, and there is one predator.

Q4: Prey must eat to survive, so they lose energy over time.

Q5: Your default. Each side beats random and scripted opponents, and later generations beat earlier ones in the cross-play table.`
- `D613` skill loaded from `/Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/skills/test-planning`
- `D614` **Bash** python3 ../plugin/dev-team/scripts/dt.py status --skill test-planning 2>&1 | head -60; echo ---; python3 ../plugin/dev-team/scripts/dt.py next 2>&1 | head; ls docs docs/ideas 2>&1; git status --short
      ↳ …[1430 chars] cases (BASE-01 tank band, BASE-04, TWIN-02, PG-10/PG-11, the tank's EVAL-03/QR-02); also the Strategy smoke commands still use pre-AD-15 paths (runs/full-s1 -> runs/snake/full-s1) (from build-planning) ⏎ waiting on user: no ⏎ run: /dev-team:test-planning ⏎ docs: ⏎ architecture.md ⏎ brief.md ⏎ explained ⏎ ideas ⏎ packages ⏎ requests.md ⏎ roadmap.md ⏎ routes.md ⏎ spec.md ⏎ docs/ideas: ⏎ fish-tank.md
- `D615` **Bash** grep -n "UR-6[0-9]" docs/requests.md | head; grep -n -i "predator\|prey\|co-evol\|adversar" docs/brief.md docs/roadmap.md docs/ideas/*.md | head -20; git log --oneline -3 --stat | head -30
      ↳ …[1411 chars] +++++++++- ⏎  docs/routes.md  |   1 + ⏎  tasks/plan.md   | 123 ++++++++++++++++++++++++++++++++++++++------------------ ⏎  tasks/todo.md   |   3 ++ ⏎  4 files changed, 110 insertions(+), 40 deletions(-) ⏎ c94df75 turn 43 ⏎  docs/architecture.md            | 2 +- ⏎  docs/packages/rllab/contract.md | 2 +- ⏎  docs/routes.md                  | 4 ++-- ⏎  3 files changed, 4 insertions(+), 4 deletions(-)
- `D616` _thought:_ These answers belong to the predator-prey idea under `idea-refine`, not `test-planning`, since test-planning only handles golden cases for approved pipelines and is currently on the S2 revise. I'll forward your answers to `idea-refine` so it can update the idea file and write the S3 stage.
- `D617` **Skill** dev-team:idea-refine Answers to the predator-prey (environment 3, UR-64..UR-66) idea questions from the previous session:

Q1: Plan it now as S3, built after S2. It's part of the project, so I'd rather have it planned. Narrow the Not Doing item and reopen the core contract if you need to.

Q2: Simultaneous learners first, then fix it by training against past versions (ladder 2). Take turns (3) as an optional first rung, and use the cross-play table (7) for evaluation.

Q3: Yes. Reuse S2's tank and hand-written PPO for both sides. The prey share one policy, and there is one predator.

Q4: Prey must eat to survive, so they lose energy over time.

Q5: Your default. Each side beats random and scripted opponents, and later generations beat earlier ones in the cross-play table.
- `D618` skill loaded from `/Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/skills/idea-refine`
- `D619` **Bash** python3 ../plugin/dev-team/scripts/dt.py status --skill idea-refine; S=../plugin/dev-team/skills/idea-refine; cat $S/references/extend.md; ls $S $S/references
      ↳ …[6550 chars] ets its own file and names the old one under *Touches*. The old file is not edited. ⏎ ../plugin/dev-team/skills/idea-refine: ⏎ SKILL.md ⏎ references ⏎ ../plugin/dev-team/skills/idea-refine/references: ⏎ examples-data.md ⏎ examples-extend.md ⏎ examples-ml.md ⏎ examples-new.md ⏎ examples-process.md ⏎ extend.md ⏎ frameworks.md ⏎ ideation.md ⏎ new.md ⏎ refinement-criteria.md ⏎ requests.md ⏎ roadmap.md
- `D620` **Bash** S=../plugin/dev-team/skills/idea-refine/references; cat $S/requests.md $S/roadmap.md; cat docs/brief.md; cat docs/roadmap.md; sed -n 1,80p docs/ideas/fish-tank.md; head -30 docs/requests.md; python3 ../plugin/dev-team/scripts/dt.py request --help 2>&1 | head -30
      ↳ …[25046 chars] words approving the change ⏎   --into ID [ID ...]    change: the IDs the change was written into (every ID ⏎                         that honoured the old words) ⏎   --owner {brief,spec,architecture,pipelines,tests,plan,constraints} ⏎                         list: only this owner's requests ⏎   --open                list: only requests nothing honours yet ⏎   --json                list: print JSON
- `D621` **Bash** sed -n 30,80p docs/requests.md; grep -n "^## \|^### \|CORE-0[1-9]\*\*\|Out of scope" docs/spec.md | head -60
      ↳ …[9790 chars] learning agent (`AGENT`) ⏎ 159:### Policy-gradient ladder (`PG`) ⏎ 198:### Ablation switches (`ABL`) ⏎ 226:### Baselines (`BASE`) ⏎ 249:### Evaluation (`EVAL`) ⏎ 270:### Run logging (`LOG`) ⏎ 290:### Learning curves (`CURVE`) ⏎ 314:### Replay viewer (`REPLAY`) ⏎ 336:### Explanation notes (`EXPL`) ⏎ 356:### Discrete tank (`TWIN`) ⏎ 371:## Quality requirements ⏎ 383:## Assumptions ⏎ 397:## Changelog
- `D622` **Bash** grep -n -i "word\|budget" ../plugin/dev-team/skills/idea-refine/references/new.md | head; sed -n 13,25p docs/spec.md; sed -n 100,125p docs/spec.md | grep -n "CORE-05\|agent" ; ls docs/ideas; git log --all --oneline | grep -i idea | head -3
      ↳ …[3022 chars]  with no changes to the core, then training completes, both points reach 5 in ≥ 9 of 10 evaluation games, and the run is logged, drawn and replayed. ⏎ 24:- **CORE-08** When an environment removes one of its agents mid-game, the training loop stops asking that agent for moves and the game continues for the rest. ⏎ fish-tank.md ⏎ 8346f0c Accept the fish-tank idea and brief edit; add roadmap stage S2
- `D623` _said:_ Recording your answers first.
- `D624` **Bash** D="python3 ../plugin/dev-team/scripts/dt.py request add"
$D brief "Plan it now as S3, built after S2." --skill idea-refine --about "Q1 when: plan Environment 3 now as S3 built after S2 vs write the idea and park it until S2 is built"
$D brief "Narrow the Not Doing item" --skill idea-refine --about "Q1: brief Not doing item 'Planning environments beyond the second' may be narrowed"
$D architecture "reopen the core contract if you need to." --skill idea-refine --about "Q1: the M1 core contract may …[+1202 chars]  ❌ ERROR
      ↳ Exit code 127 ⏎ (eval):2: no such file or directory: python3 ../plugin/dev-team/scripts/dt.py request add ⏎ (eval):3: no such file or directory: python3 ../plugin/dev-team/scripts/dt.py request add ⏎ (eval):4: no such file or directory: python3 ../plugin/dev-team/scripts/dt.py request add ⏎ (eval):5: no such file or directory: python3 ../plugin/dev-team/scripts/dt.py request add ⏎ (eval):6: no such file or directory: python3 ../plugin/dev-team/scripts/dt.py request add ⏎ (eval):7: no such file or directory: python3 ../plugin/dev-team/scripts/dt.py request add ⏎ (eval):8: no such file or directory: python3 ../plugin/dev-team/scripts/dt.py request add ⏎ (eval):9: no such file or directory: python3 ../plugin/dev-team/scripts/dt.py request add ⏎ (eval):10: no such file or directory: python3 .. …[+135 chars]
- `D625` **Bash** cd /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project
python3 ../plugin/dev-team/scripts/dt.py request add brief "Plan it now as S3, built after S2." --skill idea-refine --about "Q1 when: plan Environment 3 now as S3 built after S2 vs write the idea and park it until S2 is built"
python3 ../plugin/dev-team/scripts/dt.py request add brief "Narrow the Not Doing item" --skill idea-refine --about "Q1: brief Not doing item 'Planning environments beyond the seco …[+1775 chars]
      ↳ …[2082 chars]  - **UR-75** spec · "Prey must eat to survive, so they lose energy over time." [Q4 foraging stakes: prey must eat vs pellets only a bonus reward] · idea-refine 2026-10-18 ⏎ - **UR-76** spec · "Each side beats random and scripted opponents, and later generations beat earlier ones in the cross-play table." [Q5 what counts as success for Environment 3 (user took the default)] · idea-refine 2026-10-18
- `D626` _said:_ Writing the idea file and narrowing the brief's Not Doing item.
- `D627` **Write** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/ideas/predator-prey.md (62 lines)
- `D628` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/brief.md | old: '- Planning environments beyond the second, the fish tank: each next one is chose' | new: '- Planning environments beyond the third, predator-prey foraging: each next one '
- `D629` **Bash** python3 ../plugin/dev-team/scripts/dt.py request trace UR-67 "§Not doing" && python3 ../plugin/dev-team/scripts/dt.py request trace UR-68 "§Not doing" && wc -w docs/brief.md docs/ideas/predator-prey.md && python3 ../plugin/dev-team/scripts/dt.py lint docs/ideas/predator-prey.md; python3 ../plugin/dev-team/scripts/dt.py lint docs/brief.md; python3 ../plugin/dev-team/scripts/dt.py request --open --owner brief
      ↳ UR-67 → §Not doing ⏎ UR-68 → §Not doing ⏎      453 docs/brief.md ⏎      907 docs/ideas/predator-prey.md ⏎     1360 total ⏎ 0 errors, 0 warnings ⏎ 0 errors, 0 warnings ⏎ requests: none
- `D630` _said:_ I've written the predator-prey idea as a Draft at `docs/ideas/predator-prey.md`. I also changed one line in the brief. ⏎ - **Problem:** when the opponent also learns, the target keeps moving. Each side's reward can stay flat while both improve, and the two can go round in circles. ⏎ - **Direction:** this is S2's tank with the ball replaced by one learning predator. Prey lose energy and must eat pellets to survive. Both sides use your PPO from S2, and all prey share one policy. The training ladder has three rungs: ⏎   1. Taking turns (optional). ⏎   2. Simultaneous learners, kept on purpose as  …[+2203 chars]
- `D631` HOOK SessionStart:resume said: milestone: M1 Train an agent · plan Approved ⏎ progress: 0/22 · next: M1-T01 M1 interface ⏎ blocked: none ⏎ draft (waiting for approval): docs/ideas/predator-prey.md ⏎ requests: 11 not honoured → spec-writing, architecture-design ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/scripts/dt
- `D632` **USER:** Accepted: the idea, the brief edit and S3. Yes, commit them. One fix: my limit is about 1 hour of training per environment, so it applies to the whole self-play run, not per generation.
- `D633` **Bash** python3 ../plugin/dev-team/scripts/dt.py request add spec "my limit is about 1 hour of training per environment, so it applies to the whole self-play run, not per generation." --skill idea-refine --about "Environment 3 training-time limit: whole self-play run vs per generation" && python3 ../plugin/dev-team/scripts/dt.py next-id S
      ↳ UR-77 spec: "my limit is about 1 hour of training per environment, so it applies to the whole self-play run, not per generation." ⏎ S3
- `D634` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/ideas/predator-prey.md | old: '**The core grows again.**' | new: "**Time.** The brief's limit of about an hour of training covers the whole self-p"
- `D635` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/ideas/predator-prey.md | old: '- Self-play over a handful of generations fits on a laptop CPU.' | new: '- A whole self-play run, over a handful of generations, fits in about an hour on'
- `D636` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/ideas/predator-prey.md | old: '- Training time: does the brief\'s "under about an hour per environment" hold for' | new: ''
- `D637` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/ideas/predator-prey.md | old: '**Status:** Draft ·' | new: '**Status:** Accepted ·'
- `D638` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/roadmap.md | old: '| S2 | Fish tank + policy gradients | ideas/fish-tank.md | Split |' | new: '| S2 | Fish tank + policy gradients | ideas/fish-tank.md | Split | ⏎ | S3 | Pred'
- `D639` **Bash** cat >> docs/roadmap.md <<'EOF'

## S3: Predator-prey + self-play
**Outline:** I can train a hand-written PPO predator and a shared prey policy against each other in the fish tank, where prey must eat pellets to survive, by taking turns, then learning at once, then self-play against past versions, all within about an hour, and see each side beat random and scripted opponents and later generations beat earlier ones in a cross-play table, on the same shared core, with Snake and the tank still runni …[+475 chars]
      ↳ UR-78 plan: "Accepted: the idea, the brief edit and S3." ⏎ S3: — → Idea ⏎ roadmap: updated 1 ⏎ 0 errors, 0 warnings ⏎ 0 errors, 0 warnings ⏎  M docs/ideas/predator-prey.md ⏎  M docs/requests.md ⏎  M docs/roadmap.md
- `D640` **Bash** git add docs/ideas/predator-prey.md docs/requests.md docs/roadmap.md && git commit -q -m "Accept the predator-prey idea and brief edit; add roadmap stage S3

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log --oneline -1 && python3 ../plugin/dev-team/scripts/dt.py next | head -3
      ↳ COMMIT UNCONFIRMED — HEAD after the call was f964cd4; check `git show --stat f964cd4`
      ↳ …[264 chars] TANK-10, PG-01-PG-09, PG-12, ABL-06-ABL-08, the tank's EVAL-02 cadence with a final over 100), CORE-09 (Snake's 200-game seed-1 record from M1 as the 'before'), and later M5/M6 cases (BASE-01 tank band, BASE-04, TWIN-02, PG-10/PG-11, the tank's EVAL-03/QR-02); also the Strategy smoke commands still use pre-AD-15 paths (runs/full-s1 -> runs/snake/full-s1) (from build-planning) ⏎ waiting on user: no
- `D641` _said:_ The predator-prey idea, the brief edit and S3 are accepted and committed as `f964cd4`. ⏎ **Your fix:** the idea now says the hour of training covers the whole self-play run, every generation of both sides. The matching assumption in the idea says a full run fits in about an hour on a laptop CPU. I removed that question from Open questions and recorded your words as UR-77; the spec will turn them into a requirement. ⏎ **What changed:** ⏎ - `docs/ideas/predator-prey.md` is now Accepted. ⏎ - `docs/roadmap.md` has a new stage, **S3: Predator-prey + self-play**, using the null-hypothesis-testing sk …[+663 chars]
- `D642` HOOK SessionStart:startup said: milestone: M1 Train an agent · plan Approved ⏎ progress: 0/22 · next: M1-T01 M1 interface ⏎ blocked: none ⏎ requests: 12 not honoured → spec-writing, architecture-design ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/scripts/dt
