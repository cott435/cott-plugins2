# Thickening, routing, modes, checkpoints, the graph, writing

Read when writing thicken tasks, the dependency graph and the files. Templates: `../examples.md`; graph example: `examples-phase0.md`; routing example: `examples-routing.md`.

## 5. Thicken

`**Kind:** thicken`, under Phase 2: one task per step upgrade, depending on its step's spine. Order in the file sets nothing: every thicken task can start once its spine lands. Risk orders tasks only when a later one must learn from an earlier one, as an `order` edge with its reason (step 9). In data and ML work, data loading, leak checks and the evaluation get thicken tasks of their own, never left until after the model.

**Split a task** when it needs more than one session, has more than 3 acceptance bullets, touches two packages or two steps, or has "and" in its title. Sizes count `Writes:` entries outside `tests/` (`task-size`; a folder glob counts as one): XS = 1, S = 1–2, M = 3–5. Nothing larger. Spine and thicken tasks are XS or S.

**Acceptance is test-backed.** Each bullet is checkable: a `TC-NN` passes, a Given/When/Then, a model criterion by ID, the smoke command. With no `tests.md`, write the criterion so a tester can encode it. A TC that runs the whole pipeline is the wiring or system task's acceptance (`phase0.md`), never a thicken's. A thicken's golden case builds its store from its own fixture (`input.json`) through a shared test helper, never through a wiring task's run, so no thicken waits on wiring.

## 6. Route skills and references

**Skills.** Start from `milestone_skills` (the milestone's `**Skills:**` line, else its stage's): each goes on the `**Skills:**` of every task it fits, and at least one. Then add others whose descriptions fit a task (project `.claude/skills/*/SKILL.md`, `skills_available`). The plan's Scope lists the milestone's skills. A task that needs a skill that isn't installed names it anyway (`dt status` reports it under `skills_missing`) and goes under Open questions. Never quietly plan the step without it.

**References.** Each `RF-NN` or `PB-NN` in `milestone_references` goes in the `Read:` of the tasks whose step it informs; an RF entry's *Use for* and *Key parts* say which, a PB entry's *Informs* and *Caveats*. Cite the ID, never the `references/` or `probes/` path. A probe's code goes to the step that calls the same API (`PB-01:probe.py:sync_all`); its redacted samples (`PB-01:samples`) go to the interface task (`phase0.md`) and, as raw-shaped test input, to that step's spine and thicken tasks. Over 300 lines, add a selector so the packet stays small: `RF-01:deseasonalize` (one function or class), `RF-01:outline`, or `RF-03:<heading>` for a doc. With no selector a long file prints as its outline and `dt lint` warns `ref-large`. Whether to reuse the code is the builder's call; don't write it into Acceptance. A decision whose Consequences adopt what a probe spent (Plaid Items it linked) gets its own task in the milestone that builds that step.

## 7. Build mode

- `split` (tester, then implementer) when the task adds or changes behavior with a checkable outcome: anything a TC case, Given/When/Then or model criterion covers.
- `solo` for interface, spine, wiring, system, refactor, glue and doc-sync tasks.

`mode_violations` flags a task that breaks the rule. An override needs `**Reason:** <one line>` on the task. **A split task tests symbols a frozen interface declares** (the interface task's types and signatures), so the tester never writes against a guess and starts right after the interface, beside the implementers. Its `Depends on` is the implementer half's; the tester half waits only on the interface.

## 8. Checkpoints

`### Checkpoint after M<n>-T<nn>` at the end of a wave, naming the wave's last task in plan order: usually once after the wiring and thicken wave, when every pipeline runs end to end. `### Checkpoint: milestone exit` last. Use the blocks in `../examples.md`. A separate read-only reviewer runs each one; the orchestrator records its findings with `dt finding`, not this skill.

## 9. Dependencies, Writes, the graph, Verify

- **`Depends on:`** resolves, points only backward (position counts, not ID number), is acyclic, and holds only edges nothing mitigates.
- **`Writes:`** is exact paths, or a folder glob the task owns, and is an exclusive claim: two tasks with no `Depends on` path between them never write the same path (`writes`). Shared files (`__init__.py`, `types.py`, `__main__.py`, and shared test helpers: `conftest.py`, a golden-case store builder) belong to the interface task; each pipeline's entry module to its wiring and system tasks (`phase0.md`). No `Writes:` under `tasks/`: builders never tick `todo.md` or record findings; the orchestrator does after each merge.
- **`## Dependency graph`**, after the last checkpoint: one row per edge between tasks, `| From | To | Kind | Mitigated by |`. From is the task that needs, To the one it needs; each cell starts with the task ID. Mitigated by names the interface and the task freezing it (`profile.Profile sample (M1-T01)`), or says `none: <reason>`.

| Kind | Meaning | Mitigation |
|---|---|---|
| `data` | One step's output feeds another's input | The type and its sample |
| `call` | A pipeline calls another pipeline or package | The fixture-backed fake |
| `file` | Two tasks must write one file | Move the shared part to the interface task; else serial. Two wiring tasks never share a file: each writes its own entry module. Two steps' thicken tasks on one module: the interface task's layout splits it (each step its own file, the old module re-exporting); never chain them |
| `code` | A task changes code another task wrote (a thicken after its step's spine or an earlier thicken of that step) | None: serial |
| `contract-change` | A task changes a frozen interface | None: serial, plus a new interface task |
| `order` | Integration (a wiring or system task runs the steps it wires: `none: integration: the smoke runs it`), or risk or learning ("do X first to learn Y"; never a human approval: `phase0.md` a) | None: reason required |

A spine never has an edge to another step's task: it builds against the interface's samples and doubles. A mitigated edge documents why two tasks run side by side and never appears in `Depends on`; an unmitigated one must (`edges`). Every `Depends on` has its row, except a dependency on the interface task, which every task has and needs none. The table is the reviewable argument for every serial step.
- **Width.** `dt status` gives `critical_path`, `waves`, `width` and `parallelism`; on the fresh plan `dt ready` lists only the interface task(s). Mostly width-1 waves mean an edge an interface could mitigate is ordering tasks.
- **`Verify:`** The interface task's runs the schema check over every sample; every other task's runs its focused tests and `scripts/check.sh gate` (`--pkg <pkg>` in multi-package), plus its pipeline's smoke command (tests.md Strategy, else the Trigger plus ` --smoke`) once its `Depends on` path reaches that pipeline's wiring task: wiring and system tasks always. A thicken task running beside the wiring is smoke-tested by the gate after each merge. Only the modes `fast`, `gate` and `full` exist.
- **`Read:`** lists the IDs (references as `RF-NN[:selector]`, probes as `PB-NN:<file>[:<symbol>]`, `PB-NN:outline` or `PB-NN:samples`) and paths a builder needs, and nothing else. A split task's names its step's function, so the tester knows the signature it tests. Check each packet with `dt context <task>`: it must resolve and stay under 2,000 lines.

## 10. Write

Task IDs start at `dt next-id M<n>-T` and count up, in phase order.
- **Next milestone only.** Later milestones stay as roadmap outlines. Write `tasks/queued/M<n>-<slug>.md` only when the user asks.
- `tasks/plan.md` with Status `Draft` and `**Base:** —` (pending). Never record a sha yourself: `build-setup` runs `dt base` after its bar is approved and committed.
- `tasks/todo.md`: one unchecked line per task, IDs matching the plan.
- Milestone rows and sections (`cut.md` step 2), the planned milestone's `**Exit:**` and `**Plan:**`, then `dt roadmap`.
