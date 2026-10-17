# Thickening, routing, modes, checkpoints, order, writing

Read when writing Phase 1 and the files. Templates: `../examples.md`; routing example: `examples-phase0.md`.

## 5. Thicken

`## Phase 1: Thicken`: one task per step upgrade, **riskiest first**. In data and ML work that means data loading, leak checks and the evaluation before any model. **Contract changes come first**, then the tasks that use them.

**Split a task** when it needs more than one session, has more than 3 acceptance bullets, touches two packages or two steps, or has "and" in its title. Sizes (lint-enforced by `Files likely` count): XS = 1 file, S = 1–2, M = 3–5. Nothing larger.

**Acceptance is test-backed.** Each bullet is checkable: a `TC-NN` passes, a Given/When/Then, a model criterion by ID, the smoke command. With no `tests.md`, write the criterion so a tester can encode it.

## 6. Route skills and references

**Skills.** Start from `milestone_skills` (the milestone's `**Skills:**` line, else its stage's): each goes on the `**Skills:**` of every task it fits, and at least one. Then add others whose descriptions fit a task (project `.claude/skills/*/SKILL.md`, `skills_available`). The plan's Scope lists the milestone's skills. A task that needs a skill that isn't installed names it anyway (`dt status` reports it under `skills_missing`) and goes under Open questions. Never quietly plan the step without it.

**References.** Each `RF-NN` in `milestone_references` goes in the `Read:` of the tasks whose step it informs; its entry's *Use for* and *Key parts* say which. Cite the ID, never the `references/` path. Over 300 lines, add a selector so the packet stays small: `RF-01:residualize` (one function or class), `RF-01:outline`, or `RF-03:<heading>` for a doc. With no selector a long file prints as its outline and `dt lint` warns `ref-large`. Whether to reuse the code is the builder's call; don't write it into Acceptance.

## 7. Build mode

- `split` (tester, then implementer) when the task adds or changes behavior with a checkable outcome: anything a TC case, Given/When/Then or model criterion covers.
- `solo` for contract, spine, refactor, glue and doc-sync tasks.

`mode_violations` flags a task that breaks the rule. An override needs `**Reason:** <one line>` on the task. **A split task only tests symbols that already exist** (from the spine or an earlier solo task), so the tester never writes against a guess.

## 8. Checkpoints

`### Checkpoint after M<n>-T<nn>` every 2–3 tasks, and `### Checkpoint: milestone exit` last. Use the block in `../examples.md`. A separate read-only reviewer runs each one; its findings are recorded under the block with `dt finding`, not by this skill.

## 9. Order, dependencies, parallel groups, Verify

- `**Depends on:**` resolves, points only backward (to a task earlier in the plan; position counts, not ID number) and is acyclic.
- Package spines of different packages, and after Phase 0 independent tasks, get `**Parallel:** G<n>`. Tasks that share a `Files likely` path or a `Read:` contract symbol never share a group, except a symbol the contract task froze.
- The contract task's `Verify:` runs the schema check over every fixture. **Every `Verify:` after Phase 0 includes its pipeline's smoke command** (tests.md Strategy, else the Trigger plus ` --smoke`), so each task leaves the system working. Add the focused tests and `scripts/check.sh gate` (`--pkg <pkg>` in multi-package). Only the modes `fast`, `gate` and `full` exist.
- `**Read:**` lists the IDs (references as `RF-NN[:selector]`) and paths a builder needs, and nothing else. Check each packet with `dt context <task>`: it must resolve and stay under 2,000 lines.

## 10. Write

Task IDs start at `dt next-id M<n>-T` and count up.
- **Next milestone only.** Later milestones stay as roadmap outlines. Write `tasks/queued/M<n>-<slug>.md` only when the user asks.
- `tasks/plan.md` with Status `Draft` and `**Base:** —` (pending). Never record a sha yourself: `build-setup` runs `dt base` after its bar is approved and committed.
- `tasks/todo.md`: one unchecked line per task, IDs matching the plan.
- Milestone rows and sections (`cut.md` step 2), the planned milestone's `**Exit:**` and `**Plan:**`, then `dt roadmap`.
- **New only:** the AGENTS.md doc map (`## Docs` and `## Project skills`, ≤ 25 lines). If only `CLAUDE.md` exists, write it there. Leave every other section alone.
