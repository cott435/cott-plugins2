# Extend mode: an idea file

`docs/brief.md` exists, so the new idea gets its own file and must earn its place in the project. Examples: `examples-extend.md`, `examples-ml.md`, `examples-quant.md` (stage skills and references).

**Read before asking anything:** `docs/brief.md`, `docs/spec.md`, `docs/roadmap.md` and open ideas in `docs/ideas/`. Their problem, goals, constraints, Not Doing list and requirements constrain the new idea. `Specced` ideas are frozen records; where one disagrees with the spec, the spec is current.

- A `Draft` brief: ask whether to finish reviewing it first.
- A `Draft`, `Accepted` or `Parked` idea covering the same ground: offer to refine it instead. A `Specced` one is frozen; a change starts a new file.

**Phases 1-2** per `ideation.md`. Before Phase 1, restate the new idea in terms of the existing project: "This adds [X] so that [existing user] can [outcome]." Note which existing features and requirement IDs it touches.

**Fit check (during Phase 2) — answer one of these out loud. It decides whether the brief changes:**

| Finding | Idea file | Brief |
|---|---|---|
| Serves an existing goal (including the next stage of the same project) | Write it | **No change.** This is the common case. |
| Needs a new goal, same problem and user | Write it | Only if the project's outcome itself widens; a new stage is not a new goal. Add it with the next number. If that makes more than five, ask the user which to merge. |
| Changes a constraint (deadline, budget, a rule) | Write it | Update Constraints. |
| Contradicts the Not Doing list | Write it only if the user reverses that decision | Remove the item, with the user's agreement. Otherwise park the idea. |
| Different problem or different user | Don't write it | Push back: this may be a separate project with its own brief. |

**Phase 3: write `docs/ideas/<idea-slug>.md`** (kebab-case slug, e.g. `shared-editing.md`):

```markdown
# Idea: [Name]

**Status:** Draft · **Last updated:** YYYY-MM-DD · **Brief:** [../brief.md](../brief.md)

## In one sentence
[This adds X so that Y can Z.]

## The problem
[The specific pain this solves. Who hit it, how often, and evidence — customer requests, support tickets, lost deals.]

## Who it's for
[Which of the brief's users. Name the specific situation they're in.]

## How it fits
- **Serves:** Goal 2 (and new Goal 4, if added)
- **Touches:** [existing features and spec IDs this changes or depends on, e.g. EDIT-03]
- **Brief changes:** [None — or the sections edited, in one line: "Goal 4 added; Not doing narrowed"]
- **Stage:** [New S3 (roadmap stage on acceptance) — or "joins S2", when the user puts it in a stage not yet being built]

## Recommended direction
[1-3 paragraphs on how it should work from the user's point of view, and why this direction over the others.]

## Data
[ML and data ideas only — omit otherwise. What data it needs, where it lives or could come from, how much history and labels exist, and how results will be evaluated (held-out data, baseline). If an installed skill owns the evaluation step, such as a hypothesis-testing skill, name it here.]

## Alternatives considered
- [Direction] — [why not, in one line]

## What success looks like
- [Observable signs it worked]

## What we're betting on
- [Assumptions specific to this idea]

## Not doing
- [Tempting part of this idea we're leaving out] — [reason]

## Open questions
- [Questions spec-writing must resolve or ask about]
```

**Writing rules for idea files:**

- **Plain English, still no requirements.** Describe what the user experiences and why; `spec-writing` turns that into requirement IDs and acceptance criteria.
- **More room than the brief, not unlimited.** Aim for 300-700 words. The extra space goes to *How it fits*, *Alternatives considered*, and *Open questions* — the context the spec needs.
- **One idea per file.** If the conversation produced two separable ideas, write two files (ask the user which to do first).
- **Write it as a record, in the brief's voice.** The file outlives the review. Notes to the user ("my proposed limit, for you to check") belong in the conversation. Questions belong under *Open questions*.
- **Tool preferences live here, not in the spec.** If the user names a library, dataset or service ("hand-write PPO, then compare with Stable-Baselines3"), record it under *Recommended direction* or *Data*. `spec-writing` writes the behavior without the name, and `architecture-design` reads the name from here.
- **Never paste the idea into the brief.** Brief edits are limited to the fit-check table above. Goal numbers stay stable; new goals take the next number. If a goal is dropped, tell the user which spec requirements referenced it.

**Review Gate** (`../SKILL.md`): also say whether the brief changed and which sections.

**Stage** per `roadmap.md`: one stage for the idea, Source `ideas/<slug>.md`. Skip it only when the idea's *Stage* line says it joins a stage not yet being built.

**Idea status lifecycle:** `Draft` → `Accepted` (user approved here) → `Specced` (set by `spec-writing` once the spec is approved). Parked ideas get `Parked` with a one-line reason, so they aren't re-proposed blindly. **A `Specced` idea is frozen.** It records why the feature was added, as it stood that day. `spec-writing` adds a one-line banner saying so, and nobody edits the file afterwards. The spec is the current description. When a new idea changes what a `Specced` one describes, such as a narrowed holdout or a merged stage, the new idea gets its own file and names the old one under *Touches*. The old file is not edited.
