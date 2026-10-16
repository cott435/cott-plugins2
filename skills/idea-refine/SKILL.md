---
name: idea-refine
description: Refines raw ideas into a sharp direction through structured divergent and convergent thinking. For a new project it writes a one-page plain-English brief (docs/brief.md); for a new feature in an existing project it writes a focused idea file (docs/ideas/<idea>.md) and edits the brief only if the project's goals change. Each accepted stage becomes a row in docs/roadmap.md. Use when an idea is still vague, when starting a new project, when adding a new feature idea to a project that already has a brief, or when assumptions need stress-testing before committing. Triggers on "ideate", "refine this idea", "write a brief", "I have a new idea for this project", or "stress-test my plan".
---

# Idea Refine

## Overview

Turns a raw idea into a focused direction and writes it down for the user to read and accept before anything is specified. What it writes depends on whether the project already exists:

| Mode | Writes | Purpose |
|---|---|---|
| **New project** | `docs/brief.md`; on acceptance, a roadmap row per agreed stage | *Why the project exists* — a page or less, plain English, readable in two minutes |
| **Extend** (brief already exists) | `docs/ideas/<idea-slug>.md`, plus brief edits only if needed; on acceptance, a roadmap row | *Why this feature, and how it fits* — focused on one idea, with the context `spec-writing` needs to add it to the spec |

The brief stays the stable "why" of the whole project. Ideas carry the detail for each addition. Stages live in `docs/roadmap.md`, never as brief goals, so the brief doesn't have to re-aim at each stage. `spec-writing` reads whichever was produced. No spec is written until the user accepts.

## When to Use

- An idea is still vague and needs shaping before anything can be specified
- Starting a new project and no `docs/brief.md` exists yet
- Adding a new idea or feature to a project that already has `docs/brief.md` (writes an idea file)
- Picking up a `Draft` or `Parked` idea in `docs/ideas/` to refine it further
- Assumptions need stress-testing before committing to a direction

**Not for:**
- A user who is unsure what they want at all (use `interview-me` if available)
- An accepted brief or idea that just needs requirements written (use `spec-writing`)
- Bug fixes or small changes with obvious requirements

## The Gated Workflow

```
MODE CHECK ─→ UNDERSTAND & EXPAND ─→ EVALUATE & CONVERGE ─→ WRITE BRIEF or IDEA ─→ [user accepts] ─→ spec-writing
```

Each arrow waits on the user. Everything is written as a **Draft**; it only becomes **Accepted** when the user says so.

### Phase 0: Mode Check

Run `python3 ../../scripts/dt.py status --skill idea-refine`. The path is relative to this skill's folder: resolve it from where this SKILL.md lives, and run the command from the project root. It reports the mode, the brief and spec status, the brief's word and goal counts (`brief_words`, `brief_goals`), each idea file with its status (`ideas`), and the existing roadmap rows (`roadmap_rows`).

- **New mode** — no brief exists. Run the full process and write `docs/brief.md`.
- **Extend mode** — a brief exists. Read `docs/brief.md`, `docs/spec.md` (if present), `docs/roadmap.md` (if present), and any open ideas in `docs/ideas/` *before* asking anything. The existing problem, goals, constraints, Not Doing list, and approved requirements are now constraints on the new idea. Follow [Extend Mode](#extend-mode-adding-an-idea-to-an-existing-project) for what to write.

If the brief is still `Draft`, ask whether to finish reviewing it first. If a `Draft`, `Accepted` or `Parked` idea file covers the same ground, offer to refine that one instead of starting another. A `Specced` one is frozen; a change to it starts a new file.

### Phase 1: Understand & Expand (Divergent)

**Goal:** Take the raw idea and open it up.

1. **Restate the idea** as a crisp "How Might We" problem statement. This forces clarity on what's actually being solved.

2. **Ask 3-5 sharpening questions** — no more: who is this for, specifically; what does success look like; the real constraints (time, tech, budget, people, rules); what's been tried before; why now. Use the `AskUserQuestion` tool to gather this input. Do NOT proceed until you understand who this is for and what success looks like.

3. **Generate 5-8 idea variations**, each with a one-line reason it exists, not just a name. Lenses: **inversion** (do the opposite), **constraint removal** (no budget, time or tech limits), **audience shift** (a different user), **combination** (merge with an adjacent idea), **simplification** (10x simpler), **10x version** (massive scale), **expert lens** (what domain experts find obvious that outsiders don't).

**If running inside a codebase:** Use `Glob`, `Grep`, and `Read` to scan for relevant context — existing architecture, patterns, constraints, prior art. Ground your variations in what actually exists and reference specific files when relevant.

Read `frameworks.md` in this skill directory for additional ideation frameworks. Pick the lens that fits; don't run every framework mechanically.

### Phase 2: Evaluate & Converge

After the user reacts to Phase 1, shift to convergent mode:

1. **Cluster** the ideas that resonated into 2-3 meaningfully different directions.

2. **Stress-test** each direction:
   - **User value:** Who benefits and how much? Painkiller or vitamin?
   - **Feasibility:** What's the cost? What's the hardest part?
   - **Differentiation:** Would someone switch from what they do today?
   - **Data (ML and data projects):** Does usable data exist, can we use it, and what's the non-ML baseline? Treat "no usable data" as a feasibility failure, not an open question.

   Read `refinement-criteria.md` in this skill directory for the full rubric, including the Data & ML feasibility checks.

3. **Surface hidden assumptions.** For each direction, name what you're betting is true, what could kill it, and what you're choosing to ignore for now.

4. **Get a decision.** Ask the user to pick a direction (or confirm your recommendation) before writing anything.

**Be honest, not supportive.** If an idea is weak, say so with kindness. Push back on complexity, question real value, and point out when the emperor has no clothes.

**Tone:** direct, thoughtful, slightly provocative during ideation — a sharp thinking partner, not a facilitator reading from a script. Calm and plain when writing the brief or idea file: they are for readers, not for showing off the ideation.

### Phase 3: Write the Brief (New Mode)

In extend mode, skip to [Extend Mode](#extend-mode-adding-an-idea-to-an-existing-project). Write `docs/brief.md` (create `docs/` if needed) using the template below. The brief answers **why**, not **how** or **what exactly** — no requirements lists, no tech choices, no screens.

```markdown
# [Project Name]

**Status:** Draft · **Last updated:** YYYY-MM-DD

## The problem
[2-4 sentences. Who has the problem, what it costs them today, and why it matters now.]

## Who it's for
[The specific people this serves. Name a primary user; mention a secondary one only if it matters.]

## Goals
1. [An outcome for the user, not a feature — "Regulars can reorder in under 30 seconds"]
2. [...]
3. [...]

## Constraints
- [Real limits: deadline, budget, team, existing systems, rules or regulations]

## What success looks like
- [Observable signs it worked — numbers where you have them]

## What we're betting on
- [The 2-3 assumptions that must be true, in plain words]

## Not doing
- [Tempting thing we're deliberately leaving out] — [one-line reason]

## Open questions
- [Only questions that could change the direction. Omit the section if none.]
```

**Writing rules — the brief must pass all of these:**

- **One page or less.** Aim for 250-450 words. If it's longer, cut — don't shrink the font.
- **Plain English.** Write for a smart person outside the team. No acronyms without a definition, no jargon, no code, no file paths.
- **Short sentences, short bullets.** One idea per bullet. No bullet longer than two lines.
- **Data needs, not data vendors.** For ML and data projects, say what data the project depends on in plain terms ("10+ years of daily US stock prices, including companies that no longer exist") as a constraint or a bet. Name a specific source only if it's fixed (our own data, a required benchmark). Choosing APIs and datasets happens in the architecture, after the spec.
- **Goals are numbered** so `spec-writing` can trace requirements back to them ("serves Goal 2").
- **3-5 goals, project-level and stage-neutral.** A goal is an outcome of the whole project ("Honest estimates of risk"), never a stage ("Stage 2: PCA works"). If the user describes the project in stages, the stages become roadmap rows (see [Roadmap Rows](#roadmap-rows)), and every goal stays true whichever stage is being built. More than five goals means the project isn't focused yet — go back to Phase 2.
- **The Not Doing list is mandatory.** It is the most valuable part: it makes trade-offs explicit.

Check the word count (`wc -w docs/brief.md`) before presenting it.

### Phase 4: Review Gate (CRITICAL)

After saving the Draft (brief, or idea file plus any brief edits):

1. Tell the user what was written and where, with a three-line summary: the problem, the top goal (or the idea's recommended direction), and the biggest thing on the Not Doing list. In extend mode, also say whether the brief changed and list the edited sections. Name the roadmap row(s) you'll add on acceptance (`M3: Classical portfolios`).
2. Ask them to read it and either **accept** it or request changes.
3. **STOP YOUR TURN.** Do not start the spec in the same turn.

**No live user** (a headless run): don't invent confirmations. Write the Draft, put what the user must confirm (the direction, goals, stages) under Open questions, leave it Draft, add no roadmap row, and stop.

**Handling the reply.** Requested edits are the whole turn. Never edit the brief or idea file and draft the spec in the same turn.

| The user says | Do | Then |
|---|---|---|
| Accepted, nothing to change | Change `**Status:** Draft` to `**Status:** Accepted` and update the date, on whichever of the brief and idea file were written or edited. Add the roadmap row(s). Offer to commit them; commit only on a yes | Hand off to `spec-writing` to write or update `docs/spec.md` |
| Accepted, with a change ("accepted, but drop the leaderboard") | Make exactly that edit. If the user fully specified it, set Accepted and add the roadmap row(s). If it needs your judgment, keep Draft. | **Stop.** List what you changed. The spec starts next turn, after the user has seen the edit. |
| Changes requested | Edit, keep Draft | Repeat this gate |

## Extend Mode: Adding an Idea to an Existing Project

When `docs/brief.md` already exists, the new idea gets its own file and must earn its place in the project.

**Before Phase 1:** Read the brief, the spec, the roadmap, and open ideas (`Draft`, `Accepted`, `Parked`). `Specced` ideas are frozen records: where one disagrees with the spec, the spec is current. Restate the new idea in terms of the existing project: "This adds [X] so that [existing user] can [outcome]." Note which existing features and requirement IDs it touches.

**Fit check (during Phase 2) — answer one of these out loud. It decides whether the brief changes:**

| Finding | Idea file | Brief |
|---|---|---|
| Serves an existing goal (including the next stage of the same project) | Write it | **No change.** This is the common case. |
| Needs a new goal, same problem and user | Write it | Only if the project's outcome itself widens; a new stage is not a new goal. Add it with the next number. If that makes more than five, ask the user which to merge. |
| Changes a constraint (deadline, budget, a rule) | Write it | Update Constraints. |
| Contradicts the Not Doing list | Write it only if the user reverses that decision | Remove the item, with the user's agreement. Otherwise park the idea. |
| Different problem or different user | Don't write it | Push back: this may be a separate project with its own brief. |

**Write `docs/ideas/<idea-slug>.md`** (kebab-case slug, e.g. `shared-editing.md`):

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
- **Milestone:** [New M3 (roadmap row on acceptance) — or "joins M2", when the user puts it in a stage not yet planned]

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

**Idea status lifecycle:** `Draft` → `Accepted` (user approved here) → `Specced` (set by `spec-writing` once the spec is approved). Parked ideas get `Parked` with a one-line reason, so they aren't re-proposed blindly. **A `Specced` idea is frozen.** It records why the feature was added, as it stood that day. `spec-writing` adds a one-line banner saying so, and nobody edits the file afterwards. The spec is the current description. When a new idea changes what a `Specced` one describes, such as a narrowed holdout or a merged stage, the new idea gets its own file and names the old one under *Touches*. The old file is not edited.

## Roadmap Rows

Stages live in `docs/roadmap.md`. A stage (milestone) delivers one working capability the user can run end to end, such as "Data + stats" or "Classical portfolios". `build-planning` later fills in its packages, pipelines and exit criteria.

**Add rows only when the user accepts** (Phase 4):
- **New mode:** one row per stage the user agreed in conversation, Source `brief`. If only the first stage is known, add just that one.
- **Extend mode:** one row for the idea, Source `ideas/<slug>.md`. Skip it only when the idea's *Milestone* line says it joins a stage not yet planned.

Each row takes its ID from `python3 ../../scripts/dt.py next-id M`, a short name, and its Source. Packages, Pipelines and Depends get `—`, even when you can guess them: `build-planning` fills them, from the pipelines `dt` infers from the Source's spec IDs. Leave the Status* cell empty, then run `python3 ../../scripts/dt.py roadmap`, which fills it. Under the table, add a `## M<n>: <Name>` section with one plain-English `**Outline:**` line: what the user can do when the stage is done.

If `docs/roadmap.md` doesn't exist, create it:

```markdown
# [Project Name] — Roadmap

**Last updated:** YYYY-MM-DD

| Milestone | Name | Source | Packages | Pipelines | Depends | Status* |
|---|---|---|---|---|---|---|
| M1 | [Name] | brief | — | — | — | |

*Written by `dt roadmap` from doc statuses and todo checkboxes; never hand-edited.

## M1: [Name]
**Outline:** [What the user can do when this stage is done, in one sentence.]
```

Add rows; never renumber, reorder or edit existing ones. Status* belongs to `dt roadmap`, and the other columns to `build-planning`.

Read `examples.md` in this skill directory for examples of full sessions, finished briefs (including a quant package with its first roadmap rows), and extend-mode idea files (including an ML feature).

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| I'll generate 20+ ideas to cover all bases | 5-8 well-considered variations beat 20 shallow ones. |
| The user just needs encouragement, not critique | A yes-machine produces weak ideas. Push back with specificity and kindness. |
| Who this is for is obvious — no need to ask | Skipping it means designing for nobody. |
| The brief needs more detail to be useful | Detail belongs in the spec. A brief nobody finishes reading defines nothing. |
| The user said "go", so I'll write the brief and spec together | The gate exists so the *why* is agreed before the *what*. Stop after the brief or idea file. |
| This stage needs its own brief goal | Stages are roadmap rows. A goal per stage is how briefs grew to six or seven goals and stopped describing the project. |
| I'll just add the new feature to the brief | The brief is the whole project's why. Feature detail belongs in an idea file; the brief changes only if goals or constraints do. |
| This feature is small, it doesn't need an idea file | Small ideas get short idea files. `spec-writing` still needs to know what it fits, what it touches, and what's out. |
| The new idea is clearly good, no need for a fit check | Good ideas that serve a different user or problem dilute the project. Check fit first. |

## Red Flags

- Generating 20+ shallow variations instead of 5-8 considered ones
- No assumptions surfaced before committing to a direction
- Brief over one page, full of jargon, file paths or tech choices, containing requirements, or with no Not Doing list
- Goals that are features ("Add a dashboard") instead of outcomes ("Owners see weekly sales without logging in"), that name a stage, more than five of them, or one added per stage
- A roadmap row added before acceptance, a Status* cell typed by hand, or an existing row edited
- Spec work started before the brief or idea file was marked Accepted
- Extend mode: feature detail written into the brief, existing goals renumbered, or the brief and spec not read first
- Extend mode: idea file missing *How it fits*, a `Specced` idea file edited, or notes to the user left in an idea file
- The spec drafted in the same turn as edits to the brief or idea file

## Verification

Before handing off to `spec-writing`:

- [ ] A clear "How Might We" problem statement was agreed in conversation
- [ ] The target user and what success looks like are defined
- [ ] Multiple directions were explored and the user chose one
- [ ] The turn ended after the Draft was saved; acceptance came in a later turn, and Status reads `Accepted` only after the user said so (headless: left Draft)
- [ ] On acceptance, each accepted stage has a roadmap row (ID from `dt next-id M`, Packages/Pipelines/Depends `—`, Status* filled by `dt roadmap`); a commit only on the user's yes
- [ ] New mode: `docs/brief.md` follows the template, is under ~450 words, has 3-5 numbered outcome goals (not features or stages) and a Not Doing list with a reason per item
- [ ] Extend mode: the fit check was answered and the user agreed with it
- [ ] Extend mode: the idea file follows the template, covers one idea, has no requirements, and its *How it fits* names the goals served, spec IDs touched, and brief changes (or "None")
- [ ] Extend mode: the brief changed only as the fit check allowed (goal numbers unchanged, still 5 or fewer); no `Specced` idea file was edited
