# Replan and Advance

Read when `dt status --skill build-planning` reports `replan` or `advance`. Examples: `examples-advance-replan.md`.

## Replan

Something learned during the build, or a major bug (after `pipeline-design` or `architecture-design` Revise, if a step or decision changed).
1. Take `blocked_tasks`, the docs under `changed_since_plan` and their revised sections (`dt section <ID>`). Until those docs are re-approved, `dt status` says `blocked`: wait. Reorder, split or add; new IDs from `dt next-id M<n>-T`. Never renumber or reuse an ID.
2. **Never drop an unchecked task silently.** List each drop with its reason for approval. On approval, remove it from plan and todo and keep a retired line under Replan notes: `- ~~M2-T05: Title~~ Retired YYYY-MM-DD: reason`.
3. Remove a `**Blocked:**` line only when the change resolves it. A major bug's regression case becomes an acceptance bullet.
4. Add one dated line to `## Replan notes`, set Status to Draft and update `Last updated` (the plan is then newer than the revised docs, which clears `changed_since_plan`), run the Review Gate. Never touch a checked task.

## Advance

Each gate ends a turn. Re-run `dt status` at the start of each turn to see where you are.

1. **Exit checkpoint.** Every finding under every checkpoint has a disposition (`dt lint` shows no `finding-disposition`), and Critical ones are fixed. Ask the user to approve the milestone. [gate] On approval set Status `Done`.
2. **Ratchet.** Route to `build-setup` Ratchet. [gate, run by build-setup] When you're back with Status `Done`, continue only if `dt status --skill build-setup` no longer says `ratchet` (its CONSTRAINTS.md header reads `**Ratcheted:** M<n>`).
3. **Archive.** Run `dt archive`. It moves the plan to `tasks/archive/`, writes the stub plan and empty todo, and adds `**Outcome:** Done <date>` to the roadmap. Append the outcome in one line (what changed versus the plan), then `dt roadmap`.
4. **Kickoff check.** Run `dt status --skill build-planning`. `drift` (entry calls ≠ step table) routes to `pipeline-design` Sync and `stale_contracts` to `architecture-design` Sync; `dt layout <pkg>` gives the detail. [gate if either is non-empty] Then check a queued plan against what changed: `dt lint tasks/queued/`, the Replan notes, and the Outcome.
5. **Next plan.** Run the Grow check, then Extend: promote the queued plan (move it to `tasks/plan.md`, update it, write the todo) or write a new one. `Base` stays `—` until build-setup sets it. Run the Review Gate. [gate]
6. **build-setup Extend** for new packages, dependencies or Grow; it sets `Base` with `dt base` once approved and committed. [gate, run by build-setup]
7. Build. Not this skill.

No next milestone: if the next stage is designed (`stage_to_cut`), cut it (`cut.md` step 2) and plan its first milestone. Otherwise leave the stub, say so, and name the skill that comes next (`idea-refine` for a new stage, or the first upstream skill whose doc isn't Approved).
