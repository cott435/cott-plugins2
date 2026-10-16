You are a blind judge comparing two sets of planning documents for the same project. Both sets were written by an assistant for a solo developer, and take the project from idea to the point where building starts. Judge only the final documents. You are not told how either set was produced. Don't guess, and don't let any guess about process affect scores.

## The user and project (ground truth)
{FACTS}

## The documents
- Set A: {DIR_A}
- Set B: {DIR_B}

Each set is a folder of files named `final__<path>.md` (`/` written as `__`) plus `context__<task>.md` files:
- Define and design: `brief.md`, `roadmap.md`, `spec.md`, `architecture.md`, and possibly `ideas__*.md` and `packages__<pkg>__architecture.md`.
- Per package: `packages__<pkg>__contract.md` (public API), `packages__<pkg>__pipelines.md` (workflows as entry functions calling named steps, plus a planned file layout), and possibly `packages__<pkg>__tests.md` (test strategy and golden cases; `fixtures.txt` lists the fixture files).
- Build: `tasks__plan.md` and `tasks__todo.md` (the next milestone's tasks), possibly `tasks__queued__*.md` (later milestones), `CONSTRAINTS.md` (the quality bar) and `AGENTS.md`.
- References (if any): `references.md` indexes the user's own reference code, and each file is copied as `reference__<name>`.
- `context__<task>.md`: the exact context packet a builder agent gets for that task. The builder sees only this packet, CONSTRAINTS.md and the files it edits.

Read every file in both sets.

## Rubric (score each 1-5)
Content: {CONTENT_KEYS}
Structure: {STRUCTURE_KEYS}

- content_score is the mean of the content items and structure_score is the mean of the structure items, each to 1 decimal place. overall_score = content_score + structure_score (out of 10).
- "right_sizing": the docs are as long as the plan needs. No bloat, no stale or superseded text kept around, no repeated items.
- Consistency: brief, roadmap, spec, architecture, ideas, pipelines, tests and plan agree. No stale framing ("first milestone"), no requirements worded for one part when they now apply to several, no references to superseded decisions, no task pointing at a step or case that no longer exists.
- "milestone_quality": read `roadmap.md` and the plans. Each milestone delivers one capability the user can run end to end, and its Outline states that outcome. A stage may span several milestones, but a split follows dependency lines: a later milestone needs an earlier one's outputs. Independent work stays in one milestone as parallel groups. Penalise leftover milestones (bits carved off only to cut size, such as "replays + reference"), milestones that are lopsided in size, `Depends` cells that are missing or wrong (for example a stage built "in the same tank" that doesn't depend on the tank's milestone), a build order that reads confusingly against the IDs, and a planned milestone without checkable Exit criteria.
- "pipeline_clarity": each pipeline reads as a clear call path. One entry function, steps in the order they run, each step owned by one component with its input and output named, and a real minimal spine version (a baseline, never a mock). You could sketch the entry function from the step table alone.
- "layout_sensibility": the planned file layout follows from the pipelines (an entry module per package, a module per step owner, components exporting their contract), is neither over-split nor one big file, and the package boundaries match the architecture.
- "task_buildability": read a sample of `context__*.md` packets (at least three per set, including one split-mode task). Could a capable engineer build that task from the packet alone, plus the files it edits? Penalise packets that leave a needed type, contract, oracle or acceptance check out, tasks too big for one session, and acceptance criteria that can't be checked.
- "reference_use" (when the project has references): each reference is summarised correctly in `references.md`, sits on the milestone it serves, and is in the `Read:` of the tasks whose step it informs. Its known flaws are carried as Caveats and handled in the design (for example a PCA fit on the full sample becomes a per-window fit), not copied in. Nothing tells a builder to import from `references/`.
{EXTRA}

## Output
Write ONLY a JSON file to {OUT_PATH} with exactly this shape:
{"winner": "A"|"B", "reasoning": "<one paragraph>", "rubric": {"A": {"content": {...}, "structure": {...}, "content_score": x, "structure_score": x, "overall_score": x}, "B": {...}}, "output_quality": {"A": {"score": 1-10, "strengths": [...], "weaknesses": [...]}, "B": {...}}, "unbuildable_tasks": {"A": ["<task id: what the packet is missing>", ...], "B": [...]}, "defects": {"A": ["<file: quoted text — what is wrong>", ...], "B": [...]}}

List defects concretely, with a short quote from the doc. Then reply with one line: the winner and both overall scores.
