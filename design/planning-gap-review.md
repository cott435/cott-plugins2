# Planning Stage — Gap Review vs agent-skills

**Status:** Review · **Last updated:** 2026-10-16 · **Reviews:** [planning-stage.md](planning-stage.md), [build-setup.md](build-setup.md)

`PS` = planning-stage.md, `BS` = build-setup.md. Paths without a prefix are in agent-skills. Line numbers are as of 2026-10-16. Build-execution questions already in [build-phase-notes.md](build-phase-notes.md) §4 aren't repeated here.

## Must

**M1 · No write matrix, so the design blocks its own steps.**
- **Pre-build sections:** the spine task must replace them (PS:234), but `dt lint` flags any edit to an Approved doc (PS:478).
- **Doc-sync tasks:** they are `solo` (PS:239) and run with the implementer's guards, which allow only `src/**` and `tests/unit/**` (BS:20, :121). No role can edit docs.
- **Review findings:** the reviewer has no Edit/Write (BS:55), yet findings go into `plan.md` (BS:179).
- **Archiving:** Advance archives the plan (PS:278), but `dt guard` denies `tasks/archive/**` (PS:487).
- **Read-only planning:** it's only an eval assertion (PS:600), not a skill rule. agent-skills states it in `planning-and-task-breakdown/SKILL.md:24-33` and `commands/plan.md:9`. The eval already saw approval turn into code (PS:118).
- **Fix → new §10 "Write matrix":**
  - one row per skill and role, with the paths each may write
  - planning skills never write or run `src/` code
  - mechanical edits go through `dt` (`dt prebuild-clear`, `dt archive`, `dt finding`), so they're exempt from the Draft reset and the archive deny

**M2 · Advance and kickoff run in an order that can't work.**
- **Extend runs too early:** the kickoff runs `build-setup` Extend (PS:284) before the next plan exists. Nothing is queued by default (PS:503), and flow H writes the plan after the kickoff (PS:398). But Extend reads "dependencies each milestone brings (plan)" (BS:34).
- **Ratchet order differs:** BS:30 has Ratchet after Extend; PS:287 has it before.
- **No turn boundaries:** Advance chains several gated steps without saying where the turn stops (`spec-driven-development/SKILL.md:170-174`).
- **Fix → §5.4 kickoff check, flow H and BS §2.** Each [gate] is its own turn:
  1. exit checkpoint
  2. Ratchet [gate]
  3. archive
  4. kickoff: status, Sync [gate if mismatches], queued-plan review
  5. next plan [gate]
  6. build-setup Extend [gate]
  7. `/build`

**M3 · Task size is a label with no definition.**
- **Gap:** XS–M is self-assigned, and only L fails lint (PS:575). There are no "split when" rules and no file cap.
- **agent-skills:**
  - sizes by file count, with four split triggers: more than one session, more than 3 acceptance bullets, two subsystems, "and" in the title (`planning-and-task-breakdown/SKILL.md:125-141`)
  - caps tasks at ~5 files (`:251`)
- **Fix → §5.4 template and §13 contract:** XS/S/M means 1 / 1–2 / 3–5 `Files likely`. Lint each task for:
  - ≤ 5 files
  - ≤ 3 acceptance bullets
  - one Package and one Step, or a reason
  - no "and" in the title

  Add the split triggers to step 5.

**M4 · Four docs the skills write have no template.**
- **The four:**
  - `plan.md` (only the task and checkpoint blocks exist)
  - `todo.md`
  - `tests.md`
  - `contract.md`
- **Task state:** nothing says which file holds it. PS:305 reads todo checkboxes; PS:576 reads "spine task checked".
- **agent-skills:** its plan template includes **Risks and Mitigations** and **Open Questions** (`planning-and-task-breakdown/SKILL.md:166-209`).
- **Fix:**
  - **§5.4, `plan.md`:**
    - header: Milestone, Status, Base, Skills
    - sections: Scope/Exit, Deferred, Phases, Checkpoints, Risks (Risk / Impact / Mitigation), Open questions, Replan notes
  - **§5.4, `todo.md`:** holds the task state. `dt lint` checks its ID set against `plan.md`.
  - **§5.3, `tests.md`:** strategy per PL, plus a TC index with source and tolerance.
  - **§5.1, `contract.md`:** one `### <pkg>.<symbol>` section per symbol, with signature, invariants and errors.

**M5 · Oracle values have no stated source.**
- **Gap:**
  - `input.json` is "validated against the contract types" (PS:196) before any parser or types exist.
  - Synthetic expected values such as `top_eigval: 2.31` have to be computed. If the planning agent computes them, the oracle is its own belief. That's the failure fixtures exist to catch (build-phase-notes:37), and it breaks PS:600.
- **agent-skills:** at least one check must be external (`constraint-driven-development/SKILL.md:218-224`).
- **Fix → §5.3 rules:**
  - every TC records a `Source:` (paper table, closed form, user file, or generator + seed) and a reason for its tolerance
  - synthetic cases are a generator plus a property ("top eigenvalue > MP edge"), not an agent-computed number
  - `input.json` is hand-transcribed; the parse test checks the parser reproduces it

**M6 · The anatomy sections have no content.**
- **Gap:** PS:578-583 requires description triggers, When to Use / Not for, Rationalizations, Red Flags and Verification. The design supplies none of them for the four new skills.
- **agent-skills:** see `docs/skill-anatomy.md:96-105` and `:154`. A description must not summarise the workflow (`:42`).
- **Fix:** add an "Anatomy" block to each of §5.2–5.4 and BS. Seeds:

| Skill | Rationalizations | Red flags | Verification |
|---|---|---|---|
| pipeline-design | "I can infer the workflows" → ask (PS:126) · "A registry keeps it extensible" → needs an AD · "The spine step can be a mock" → it must be a real baseline | A step with two owners · logic in the entry sketch · a layout module on no step | No uncovered IDs · every PL has an entry, trigger and spine column · user confirmed the workflows |
| test-planning | "A quick script gives the expected value" → circular (M5) · "No real data, no golden cases" → use known-answer cases | An expected value with no source · no parse layer · oracle approved by "sounds good" | A smoke test plus ≥ 1 golden case per PL · a source and tolerance reason per TC |
| build-planning | "The old plan is stale" (`planning-and-task-breakdown/SKILL.md:229`) · "I'll detail every milestone" → perishable (PS §7) · "No skill fits, I'll build without one" → flag it (PS:236) | A split task testing a missing symbol · parallel tasks sharing files | The §13 assertions plus `planning-and-task-breakdown/SKILL.md:246-253` |
| build-setup | Reuse `constraint-driven-development/SKILL.md:264-302` | Same | Same, plus `check.sh gate` passed once |

**M7 · Nothing stops agent-skills' own planner from taking over.**
- **Gap:**
  - `using-agent-skills/SKILL.md:23` routes "have a spec, need tasks" to `planning-and-task-breakdown`.
  - `/build auto` runs that skill when `tasks/plan.md` is missing (`commands/build.md:33`). That's exactly the state Advance leaves after archiving.
  - New mode (PS:275) doesn't handle a foreign or incomplete plan. agent-skills does (`planning-and-task-breakdown/SKILL.md:150-155`).
- **Fix → §5.4 modes and §9:**
  - a plan with no dev-team2 header and unchecked tasks: stop and ask
  - AGENTS.md says "plan with `build-planning`, not `/plan`"
  - `dt status` flags a foreign plan
  - Advance never leaves `plan.md` missing

## Should

**S1 · Assumptions and open questions.**
- **Gap:** pipeline-design invents names, triggers and types; build-planning invents order and sizes. Neither gate (PS:130, :243) lists them.
- **agent-skills:** `spec-driven-development/SKILL.md:71-82` and `context-engineering/SKILL.md:279-298`.
- **Fix:** each gate lists ASSUMPTIONS and open questions. Give `pipelines.md` and `tests.md` an Open questions section.

**S2 · How to interview, and what counts as approval.**
- **Gap:** PS:126 and :194 don't say how to ask. Nothing defines approval, which matters most for oracles (PS:205). Nothing covers runs with no user (eval harness, `/loop`).
- **agent-skills:**
  - ask one question at a time, with a guess (`interview-me/SKILL.md:53-77`)
  - hedges aren't a yes (`:113-122`, `commands/build.md:34`)
  - with no live user, flag the gap rather than guess (`constraint-driven-development/SKILL.md:36-38`)
- **Fix:** add a "Shared skill rules" preamble to §5.

**S3 · Dependency and parallel rules.**
- **Gap:**
  - no lint that `Depends on` resolves, is acyclic and points backward
  - no parallel-group field (PS:242)
  - no shared-file or shared-contract rule
  - no rule that a split task's symbol already exists (build-phase-notes Q4)
- **agent-skills:** contract first, shared state sequential (`planning-and-task-breakdown/SKILL.md:213-219`).
- **Fix → §5.4 and §13:**
  - add a `**Parallel:** G1` field
  - tasks that share files or a symbol can't be in the same group
  - symbols come from the spine or an earlier solo task

**S4 · Tasks don't leave the system working.**
- **agent-skills:** `planning-and-task-breakdown/SKILL.md:111`.
- **Fix:** after Phase 0, every `Verify:` includes its pipeline's smoke command, checked by lint.
- **Also:** add a `**Blocked:**` field, so a task paused by Revise (PS:185) shows in `dt status --summary` (`context-engineering/SKILL.md:123-137`).

**S5 · Commits at the gates.**
- **Gap:** nothing commits approved docs or fixtures. But BS:174 diffs against "the milestone's starting commit", and `/build auto` needs a clean tree (`commands/build.md:32`).
- **Fix:** commit on approval (or ask), and record `**Base:** <sha>` in the plan header at kickoff.

**S6 · The Definition of Done has no home.**
- **Gap:** PS:19 and :268 rely on it, but BS writes no DoD and CONSTRAINTS.md has no section for it.
- **agent-skills:** `references/definition-of-done.md:53-59`: tailor it once, check Correctness and Quality per task, the rest per feature.
- **Fix:** `build-setup` writes a `## Done` section, or cites the reference as-is. Map those levels to the task gate and to milestone exit.

**S7 · Inconsistencies.**
- PS:16 says `/build` works unchanged; split mode and build-phase-notes:72 say it doesn't.
- PS:44 and PS:60 name different owners for CONSTRAINTS.md.
- PS:506 says "Open: none", but BS:238 is open and tooling verification is pending.
- PS:565 puts the header on line 3, but the pipelines, roadmap and CONSTRAINTS templates use line 2. CONSTRAINTS also uses an unlisted key, `Last reviewed … by`.
- The `STAT-01–STAT-04` ranges (PS:147) aren't in the format contract.
- `### stats.estimate_cov` lacks the `: Title` that PS:568 requires.

## Nice
- **N1 · Trackers.** State that tasks stay in markdown (`dt` needs it), or that tracker items mirror the task IDs (`planning-and-task-breakdown/SKILL.md:157-164`).
- **N2 · `dt context` order.** Print the Read sections first and the task last (`context-engineering/SKILL.md:232-239`).
- **N3 · `source/` files are data.** Add one line to the §5.3 rules (`context-engineering/SKILL.md:98-103`).

## Deliberately different (keep)
- Per-milestone plans, with tasks only for the next milestone (PS §7: task lists go stale).
- Spine-first, then thicken. Each pipeline is still a vertical slice, so don't convert to feature slices.
- Task bodies in `plan.md` with ID headings and bold-key fields, read via `dt context`, not "Task N".
- The capability map comes from architecture packages plus the roadmap, not `spec-driven-development` Phase 0. The spec stays `docs/spec.md`.
- Checkpoints use a read-only reviewer agent; the human comes in at milestone exit, not at every checkpoint (`planning-and-task-breakdown/SKILL.md:122`).
- Size is capped at M (stricter than agent-skills' L).
- No review-plan file: CONSTRAINTS.md is a superset of agent-skills' format, with CR IDs.
- `dt.py` is stdlib Python at the plugin root, not bash at `skills/<name>/scripts/` (`docs/skill-anatomy.md:138-147`). Documented in PS §10.
- Three gated planning skills plus build-setup, not one planner.
- Additions agent-skills lacks: Deferred, repo-unique IDs, `Read:` packets, `Mode`, the oracle guard and the Replan drop list.
