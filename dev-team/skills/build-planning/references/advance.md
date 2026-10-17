# Advance

`dt status` says `advance`: every todo item and the exit checkpoint are ticked. Each gate ends a turn. Re-run `dt status` at the start of each turn to see where you are. Example: `examples-advance.md`.

1. **Exit checkpoint.** Every finding under every checkpoint has a disposition (`dt lint` shows no `finding-disposition`), and Critical ones are fixed. Ask the user to approve the milestone. [gate] On approval set Status `Done`.
2. **Ratchet.** Route to `build-setup` Ratchet. [gate, run by build-setup] When you're back with Status `Done`, continue only if `dt status --skill build-setup` no longer says `ratchet` (its CONSTRAINTS.md header reads `**Ratcheted:** M<n>`).
3. **Archive.** Run `dt archive`. It moves the plan to `tasks/archive/`, writes the stub plan and empty todo, and adds `**Outcome:** Done <date>` to the roadmap. Append the outcome in one line (what changed versus the plan), then `dt roadmap`.
4. **Kickoff check.** Run `dt status --skill build-planning`. `drift` (entry calls ≠ step table) routes to `pipeline-design` Sync and `stale_contracts` to `architecture-design` Sync; `dt layout <pkg>` gives the detail. [gate if either is non-empty] Then check a queued plan against what changed: `dt lint tasks/queued/`, the Replan notes, and the Outcome.
5. **Next plan.** Run the Grow check (`cut.md` step 1). Then promote the queued plan (move it to `tasks/plan.md`, update it, write the todo) or write a new one: scope it (`cut.md` step 3), shape it (`phase0.md`), write its tasks and files (`tasks.md`). `Base` stays `—` until build-setup sets it. Run the Review Gate. [gate]
6. **build-setup Extend** for new packages, dependencies or Grow; it sets `Base` with `dt base` once approved and committed. [gate, run by build-setup]
7. Build. Not this skill.

Whenever `dt status` names a `stage_to_cut`, cut it, rows only (`extend.md` step 1). No next milestone: plan the first milestone of the stage just cut; with no stage to cut, leave the stub, say so, and name the skill that comes next (`idea-refine` for a new stage, or the first upstream skill whose doc isn't Approved).
