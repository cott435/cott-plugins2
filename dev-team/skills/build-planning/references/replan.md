# Replan

`dt status` says `replan`: something learned during the build, or a major bug (after `pipeline-design` or `architecture-design` Revise, if a step or decision changed). Example: `examples-replan.md`.

1. Take `blocked_tasks`, the docs under `changed_since_plan` and their revised sections (`dt section <ID>`). Until those docs are re-approved, `dt status` says `blocked`: wait. Reorder, split or add; new IDs from `dt next-id M<n>-T`. Never renumber or reuse an ID. A new or split task meets `tasks.md`; a step a revised pipeline adds gets a task or a Deferred entry by name (`cut.md` step 3). Each changed `Depends on` changes its `## Dependency graph` row; a frozen interface that must change is a `contract-change`: a new interface task before every task that needs it (`phase0.md`, Frozen means frozen).
2. **Never drop an unchecked task silently.** List each drop with its reason for approval. On approval, remove it from plan, graph and todo and keep a retired line under Replan notes: `- ~~M2-T05: Title~~ Retired YYYY-MM-DD: reason`.
3. Remove a `**Blocked:**` line only when the change resolves it. A major bug's regression case becomes an acceptance bullet.
4. Add one dated line to `## Replan notes`, set Status to Draft and update `Last updated` (the plan is then newer than the revised docs, which clears `changed_since_plan`), run the Review Gate. Never touch a checked task.
