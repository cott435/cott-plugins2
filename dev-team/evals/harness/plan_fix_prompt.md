You are fixing a finished set of planning documents before a solo developer starts building. A reviewer checked them against the developer's own messages and against each other, and listed the defects in `.review/review.json`. Apply them.

## What you have (paths relative to the folder you are in)
- `.review/review.json`: the defect list. Each defect has a `file`, an exact `quote`, `evidence` and a `fix`.
- `.review/user_messages.md`: every message the developer sent, in order. It is the ground truth when a fix is unclear; a later message overrides an earlier one.
- `docs/`, `tasks/`: the docs you edit. Context packets are generated from these docs, so a packet defect is fixed in the doc the packet reads (a task's **Read:** or **Writes:** line in `tasks/plan.md`, a section in a `contract.md`).
- The plan tool: `{DT} lint` checks every doc's IDs, references and formats; `{DT} context <task>` prints a task's packet as the builder will see it.

## Rules
- Edit only files under `docs/` and `tasks/`. Never touch `.review/`, `references/`, `tests/` or any code. Don't create CONSTRAINTS.md or other build-setup files.
- Keep every ID, heading, table column and field format exactly as it is. Don't renumber or retire IDs; add new IDs only where a fix needs a new requirement, case or task, using the next free number (`{DT} next-id <prefix>`).
- When a fact changes, change it everywhere it appears (brief, spec, architecture, pipelines, contract, tests, plan, roadmap), not only in the file the defect names. Grep for it.
- Prefer deleting stale or narrating text to rewording it. Don't add process notes ("fixed in review", "updated") anywhere.
- Each fix stays small and local. A fix that would need a redesign (a new package, a re-cut of milestones across the whole roadmap) is applied only as far as the docs can carry it now (the Outline, Exit, Depends, Skills, References lines; moving a task between milestones), and otherwise skipped with the reason.
- If a defect is wrong (the quote isn't there, the developer's messages say otherwise, or the fix would break something), skip it and say why.
- When you're done, run `{DT} lint` and fix every error your edits introduced (warnings that were already there can stay). Then run `{DT} context` on two or three tasks you changed and check the packet now holds what the fix added.

## Output
When everything is applied, reply with ONLY a JSON object, no other text:
{"applied": ["R01", ...], "skipped": [{"id": "R05", "reason": "..."}], "files_changed": ["docs/spec.md", ...], "lint": "<the last line of {DT} lint>"}
