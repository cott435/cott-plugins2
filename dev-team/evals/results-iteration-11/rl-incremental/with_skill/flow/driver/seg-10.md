# Driver segment 10 · `/dev-team:test-planning From the previous session:
<<<
The architecture and the `rllab` contract are now **Approved** (2026-10-18).

- **AD-10** (the notes page is yours: the code checks it and never writes it) is now **Accepted**. There's no probe file, so no decision is waiting on a probe.
- The pipeline-design request to add the notes check to the architecture is closed.
- `dt lint docs/` shows 0 errors and 0 warnings.

Three files are uncommitted: `docs/architecture.md`, `docs/packages/rllab/contract.md` and `docs/routes.md`. Want me to commit them?

**Next:** `/dev-team:test-planning` (extend mode). It plans the tests and golden cases for PL-06, the only pipeline without tests yet. This step is optional.
>>>

Approved, looks good. Yes, commit them.`

- **Steps:** D240–D274 · **definition:** `/Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/skills/test-planning/SKILL.md`
- **Units spawned here:** none

## Steps

- `D240` **USER TYPED** `/dev-team:test-planning From the previous session:
<<<
The architecture and the `rllab` contract are now **Approved** (2026-10-18).

- **AD-10** (the notes page is yours: the code checks it and never writes it) is now **Accepted**. There's no probe file, so no decision is waiting on a probe.
- The pipeline-design request to add the notes check to the architecture is closed.
- `dt lint docs/` shows 0 errors and 0 warnings.

Three files are uncommitted: `docs/architecture.md`, `docs/packages/rllab/contract.md` and `docs/routes.md`. Want me to commit them?

**Next:** `/dev-team:test-planning` (extend mode). It plans the tests and golden cases for PL-06, the only pipeline without tests yet. This step is optional.
>>>

Approved, looks good. Yes, commit them.`
- `D241` skill loaded from `/Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/skills/test-planning`
- `D242` **Bash** git status --short && git add docs/architecture.md docs/packages/rllab/contract.md docs/routes.md && git commit -q -m "Approve architecture and rllab contract; accept AD-10

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log --oneline -1 && python3 ../plugin/dev-team/skills/test-planning/../../scripts/dt.py status --skill test-planning  ❌ ERROR
      ↳ Exit code 1 ⏎ On branch master ⏎ nothing to commit, working tree clean
- `D243` **Bash** git show --stat HEAD | head -20; ls ../plugin/dev-team/scripts/ 2>/dev/null | head
      ↳ commit 07cf02040bd771c33900810e98c918a172666373 ⏎ Author: eval <e@e> ⏎ Date:   Sun Oct 18 22:51:02 2026 -0400 ⏎     turn 24 ⏎  docs/architecture.md            | 4 ++-- ⏎  docs/packages/rllab/contract.md | 2 +- ⏎  docs/routes.md                  | 2 +- ⏎  3 files changed, 4 insertions(+), 4 deletions(-) ⏎ README.md ⏎ devteam ⏎ dt ⏎ dt.py
- `D244` _said:_ The three files were already committed in `07cf020`. Moving on to test planning.
- `D245` **Bash** python3 ../plugin/dev-team/scripts/dt.py status --skill test-planning
      ↳ …[165 chars]  constraints missing ⏎ next ids: AD-11 PL-07 TC-13 S2 M1 ⏎ references_unindexed: none ⏎ references_changed: none ⏎ references_missing: none ⏎ packages: rllab=extend ⏎ pipelines_no_smoke: PL-06 ⏎ pipelines_no_golden: PL-06 ⏎ cases_no_source: none ⏎ cases_no_tolerance: none ⏎ fixtures_missing: none ⏎ fixtures_orphan: none ⏎ skills: null-hypothesis-testing ⏎ routed_changes: none ⏎ requests_open: none
- `D246` **Bash** cd /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/skills/test-planning && cat references/extend.md; echo ======; cat examples.md  ❌ ERROR
      ↳ Exit code 1 ⏎ # Extend: add cases ⏎ A new pipeline, new user pairs, or a bug found in a golden path. Read `cases.md` before writing a case or a Strategy row; the section and fixture forms are in `../examples.md`. ⏎ - New pipelines get a Strategy row and cases. ⏎ - New user pairs become new cases. ⏎ - A bug found in a golden path gets a `regression` case whose expected output comes from the user or the reference that showed the bug, never from the fixed code. ⏎ Existing cases stay untouched. **Rebuild** reuses existing cases unchanged: they're what proves the new implementation matches the old. ⏎ Then the Review Gate, showing the cases this round added. ⏎ (eval):1: ===== not found
- `D247` **Bash** cd /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/skills/test-planning && cat references/cases.md; echo; echo ----------; cat examples.md
      ↳ …[9108 chars] es(days=2000, regions=50, k=20)` on seeds 12–31; same H0, statistic and null as TC-20 ⏎ **Expected:** no feature rejects H0 after Holm correction · **Tolerance:** at most 1 of the 20 seeds may reject, since the family-wise error rate is α = 0.05 ⏎ **Skills:** significance-check ⏎ ``` ⏎ Shell cwd was reset to /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project
- `D248` **Bash** cat docs/packages/rllab/tests.md; echo ---------; cat docs/packages/rllab/pipelines.md
      ↳ …[23418 chars] ons ⏎ - Re-running the study when its run folders already exist: `create_run` refuses each one, so they come back as missing. (assumed: no resume; delete `runs/` entries to re-run) ⏎ - The study scoring baselines when `rllab baselines` already wrote `runs/baseline-*`. (assumed: `score_baselines` reads an existing finished record back with `load_record`, since scoring is deterministic) ⏎ ## Retired
- `D249` **Bash** D=../plugin/dev-team/scripts/dt.py; python3 $D section EXPL-01; python3 $D section EXPL-02; python3 $D section EXPL-03; grep -n -i -A25 "NotesCheck\|check_notes" docs/packages/rllab/contract.md | head -80; grep -n "AD-10" -A12 docs/architecture.md | head -30; ls tests/fixtures/rllab/TC-12 tests/fixtures/rllab/TC-09; cat tests/fixtures/rllab/TC-09/*.json
      ↳ …[6901 chars] ence", "no-frozen": "no detectable difference", "no-decay": "no detectable difference"}, "incomplete": [], "report_states_no_switch_hurt": true, "report_switch_sections": 3, "raises": false, "tol": 0} ⏎ {"generator": "planted_study_records", "env": "snake", "seeds": [1, 2, 3, 4, 5], "seed": 9, "ablations": "copy of full agent's evaluation scores", "baselines": ["random", "scripted"], "failed": []}
- `D250` **Bash** python3 ../plugin/dev-team/scripts/dt.py next-id TC; ls .claude/skills 2>/dev/null; cat tests/fixtures/rllab/TC-12/input.json; ls -R tests/contracts 2>/dev/null | head
      ↳ TC-13 ⏎ null-hypothesis-testing ⏎ {"run": {"env": "corridor", "seed": 1, "n_games": 200}, "replays": [{"agent": "<run folder>", "env": "corridor", "seed": 1000000, "times": 2}, {"agent": "scripted", "env": "snake", "seed": 42, "times": 2}]}
- `D251` _said:_ The commit was already done. I'm now writing PL-06's golden cases (TC-13 to TC-15) and their fixtures.
- `D252` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/packages/rllab/tests.md | old: '| PL-05 | `python -m rllab replay runs/full-s1 --env snake --seed 42 --smoke` | ' | new: '| PL-05 | `python -m rllab replay runs/full-s1 --env snake --seed 42 --smoke` | '
- `D253` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/packages/rllab/tests.md | old: "**Expected:** each pair has identical frames and score; the corridor replay's sc" | new: "**Expected:** each pair has identical frames and score; the corridor replay's sc"
      ⛔ HOOK PostToolUse:Edit blocked: dt lint found problems in docs/packages/rllab/tests.md: ⏎ docs/packages/rllab/tests.md:3: approved-edit Approved doc changed since HEAD without going back to Draft (or the approval isn't committed) ⏎ docs/packages/rllab/tests.md:79: fixture-size TC-13 Fixture folder tests/fixtures/rllab/TC-13/ doesn't exist ⏎ 1 error, 1 warning
- `D254` _said:_ Setting the status back to Draft, then writing the TC-13 fixture.
- `D255` **Bash** sed -i '' 's/\*\*Status:\*\* Approved · \*\*Last updated:\*\* 2026-10-18/**Status:** Draft · **Last updated:** 2026-10-18/' docs/packages/rllab/tests.md && head -3 docs/packages/rllab/tests.md
F=tests/fixtures/rllab/TC-13; mkdir -p $F/notes $F/runs/study-snake
cat > $F/notes/snake.md <<'EOF'
# Snake notes

My notes on the Snake study.

## Why It Learns

The agent sees 11 facts about danger, direction and food, so a small network can map them to good moves.

## Ablations

### no-memory

Without r …[+647 chars]
      ↳ # rllab — Tests ⏎ **Package:** rllab · **Status:** Draft · **Last updated:** 2026-10-18 · **Pipelines:** [pipelines.md](pipelines.md) ⏎ input.json ⏎ notes ⏎ runs ⏎ tests/fixtures/rllab/TC-13/notes: ⏎ snake.md ⏎ tests/fixtures/rllab/TC-13/runs: ⏎ study-snake ⏎ tests/fixtures/rllab/TC-13/runs/study-snake: ⏎ curves.png ⏎ report.md
- `D256` **Write** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/tests/fixtures/rllab/TC-13/expected.json (1 lines)
- `D257` **Bash** python3 ../plugin/dev-team/scripts/dt.py next-id TC
      ↳ TC-14
- `D258` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/packages/rllab/tests.md | old: '**Expected:** `exists` true; `missing_sections`, `empty_sections` and `broken_li' | new: '**Expected:** `exists` true; `missing_sections`, `empty_sections` and `broken_li'
      ⛔ HOOK PostToolUse:Edit blocked: dt lint found problems in docs/packages/rllab/tests.md: ⏎ docs/packages/rllab/tests.md:84: fixture-size TC-14 Fixture folder tests/fixtures/rllab/TC-14/ doesn't exist ⏎ 1 error, 0 warnings
- `D259` **Bash** F=tests/fixtures/rllab/TC-14; mkdir -p $F
cat > $F/input.json <<'EOF'
{"env": "snake", "notes_root": "<empty temporary folder>", "runs_root": "<empty temporary folder>"}
EOF
ls $F
      ↳ input.json
- `D260` **Write** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/tests/fixtures/rllab/TC-14/expected.json (1 lines)
- `D261` **Bash** python3 ../plugin/dev-team/scripts/dt.py next-id TC
      ↳ TC-15
- `D262` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/packages/rllab/tests.md | old: 'each link entry matched by the file name it contains, since the contract fixes n' | new: 'each link entry matched by the file name it contains, since the contract fixes n'
      ⛔ HOOK PostToolUse:Edit blocked: dt lint found problems in docs/packages/rllab/tests.md: ⏎ docs/packages/rllab/tests.md:89: fixture-size TC-15 Fixture folder tests/fixtures/rllab/TC-15/ doesn't exist ⏎ 1 error, 0 warnings
- `D263` **Bash** F=tests/fixtures/rllab/TC-15; mkdir -p $F/notes $F/runs/study-snake
cat > $F/notes/snake.md <<'EOF'
# Snake notes

## Why it learns



## No-Memory

Without replay memory, scores stayed low and noisy.

## NO-FROZEN

Without the frozen copy, learning wobbled but still rose.

## Results

The full study is in the [report](../runs/study-snake/report.md).

![Learning curves](../runs/study-snake/curve.png)
EOF
cat > $F/runs/study-snake/report.md <<'EOF'
# Snake study

Placeholder report for TC-15; che …[+220 chars]
      ↳ input.json ⏎ notes ⏎ runs ⏎ tests/fixtures/rllab/TC-15/notes: ⏎ snake.md ⏎ tests/fixtures/rllab/TC-15/runs: ⏎ study-snake ⏎ tests/fixtures/rllab/TC-15/runs/study-snake: ⏎ curves.png ⏎ report.md
- `D264` _said:_ Writing the last oracle file (TC-15), then I'll update the Strategy row and run lint.
- `D265` **Write** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/tests/fixtures/rllab/TC-15/expected.json (1 lines)
- `D266` **Bash** sed -i '' 's/| TC-13 (env name, notes root, runs root → check_notes → NotesCheck) |/| TC-13, TC-14, TC-15 (env name, notes root, runs root → check_notes → NotesCheck) |/' docs/packages/rllab/tests.md && grep -n "^| PL-06" docs/packages/rllab/tests.md
D=../plugin/dev-team/scripts/dt.py; python3 $D lint docs/packages/rllab/tests.md; python3 $D status --skill test-planning | grep -E "pipelines_no|cases_no|fixtures|routed|requests"
      ↳ …[118 chars] tion), cli.args (`notes` command); boundary tests on study.check_notes, study.NotesCheck | TC-13, TC-14, TC-15 (env name, notes root, runs root → check_notes → NotesCheck) | — | ⏎ 0 errors, 0 warnings ⏎ pipelines_no_smoke: none ⏎ pipelines_no_golden: none ⏎ cases_no_source: none ⏎ cases_no_tolerance: none ⏎ fixtures_missing: none ⏎ fixtures_orphan: none ⏎ routed_changes: none ⏎ requests_open: none
- `D267` **Edit** /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/project/docs/packages/rllab/tests.md | old: '## Open questions' | new: "## Open questions ⏎ - PL-06's cases use hand-built pages. A draft of your own `n"
- `D268` **Bash** python3 ../plugin/dev-team/scripts/dt.py lint docs/packages/rllab/tests.md; git status --short
      ↳ 0 errors, 0 warnings ⏎  M docs/packages/rllab/tests.md ⏎ ?? tests/fixtures/rllab/TC-13/ ⏎ ?? tests/fixtures/rllab/TC-14/ ⏎ ?? tests/fixtures/rllab/TC-15/
- `D269` _said:_ The three files were already committed in `07cf020` ("turn 24"), so there was nothing new to commit. ⏎ I've added three golden cases for PL-06 (Check the notes page) to `docs/packages/rllab/tests.md`, along with their fixtures. The doc is back in Draft until you approve. `dt lint` shows 0 errors and 0 warnings, and every gap in `dt status` is now empty. ⏎ ## What was written ⏎ **Strategy row added** ⏎ | Pipeline | Smoke | Step unit tests | Golden cases | Model eval | ⏎ |---|---|---|---|---| ⏎ | PL-06 | `python -m rllab notes --env snake --smoke` | study.notes (heading match, empty-section rule …[+3459 chars]
- `D270` HOOK SessionStart:resume said: milestone: none (no tasks/plan.md) ⏎ draft (waiting for approval): docs/packages/rllab/tests.md ⏎ roadmap: Status* column stale (run dt roadmap) ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/scripts/dt
- `D271` **USER:** Approved. I don't have a draft notes/snake.md yet, so keep the synthetic pages. Yes, commit tests.md and the three fixture folders.
- `D272` **Bash** sed -i '' -e 's/\*\*Status:\*\* Draft · \*\*Last updated:\*\* 2026-10-18/**Status:** Approved · **Last updated:** 2026-10-18/' -e '/^- PL-06.s cases use hand-built pages/d' docs/packages/rllab/tests.md
D=../plugin/dev-team/scripts/dt.py; head -3 docs/packages/rllab/tests.md; sed -n '/## Open questions/,/## Retired/p' docs/packages/rllab/tests.md; python3 $D lint docs/packages/rllab/tests.md
git add docs/packages/rllab/tests.md tests/fixtures/rllab/TC-13 tests/fixtures/rllab/TC-14 tests/fixtures/ …[+205 chars]
      ↳ COMMIT UNCONFIRMED — HEAD after the call was 879fc30; check `git show --stat 879fc30`
      ↳ …[11 chars] ests ⏎ **Package:** rllab · **Status:** Approved · **Last updated:** 2026-10-18 · **Pipelines:** [pipelines.md](pipelines.md) ⏎ ## Open questions ⏎ ## Retired ⏎ 0 errors, 0 warnings ⏎ 879fc30 Approve PL-06 golden cases TC-13–TC-15 and fixtures ⏎ next: build-planning (new) ⏎ reason: build-planning reports new: stage_to_cut S1 Snake + shared core ⏎ waiting on user: no ⏎ run: /dev-team:build-planning
- `D273` _said:_ `docs/packages/rllab/tests.md` is now **Approved** (2026-10-18). I committed it with the fixture folders for TC-13, TC-14 and TC-15 in `879fc30`, and the working tree is clean. `dt lint` shows 0 errors and 0 warnings. ⏎ - **Synthetic pages kept:** since you don't have a draft notes page yet, TC-13 to TC-15 keep the hand-built pages. I removed that question from tests.md. When you write `notes/snake.md`, it can become a real example case in a later extend round. ⏎ - **Coverage:** every pipeline from PL-01 to PL-06 now has a smoke test and golden cases. ⏎ **Next:** `/dev-team:build-planning` (ne …[+92 chars]
- `D274` HOOK SessionStart:startup said: milestone: none (no tasks/plan.md) ⏎ roadmap: Status* column stale (run dt roadmap) ⏎ dt: /Users/connorott/plugins/dev-team-workspace/iteration-11/rl-incremental/with_skill/plugin/dev-team/scripts/dt
