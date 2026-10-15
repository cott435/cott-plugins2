---
name: idea-refine
description: Refines raw ideas into a sharp direction through structured divergent and convergent thinking. For a new project it writes a one-page plain-English brief (docs/brief.md); for a new feature in an existing project it writes a focused idea file (docs/ideas/<idea>.md) and edits the brief only if the project's goals change. Use when an idea is still vague, when starting a new project, when adding a new feature idea to a project that already has a brief, or when assumptions need stress-testing before committing. Triggers on "ideate", "refine this idea", "write a brief", "I have a new idea for this project", or "stress-test my plan".
---

# Idea Refine

## Overview

Turns a raw idea into a focused direction and writes it down for the user to read and accept before anything is specified. What it writes depends on whether the project already exists:

| Mode | Writes | Purpose |
|---|---|---|
| **New project** | `docs/brief.md` | *Why the project exists* — a page or less, plain English, readable in two minutes |
| **Extend** (brief already exists) | `docs/ideas/<idea-slug>.md`, plus brief edits only if needed | *Why this feature, and how it fits* — focused on one idea, with the context `spec-writing` needs to add it to the spec |

The brief stays the stable "why" of the whole project. Ideas carry the detail for each addition. `spec-writing` reads whichever was produced. No spec is written until the user accepts.

## When to Use

- An idea is still vague and needs shaping before anything can be specified
- Starting a new project and no `docs/brief.md` exists yet
- Adding a new idea or feature to a project that already has `docs/brief.md` (writes an idea file)
- Picking up a `Draft` or `Parked` idea in `docs/ideas/` to refine it further
- Assumptions need stress-testing before committing to a direction
- Trigger phrases: "Help me refine this idea", "Ideate on [concept]", "Write a brief for…", "New idea for this project", "Stress-test my plan"

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

Run `bash skills/idea-refine/scripts/idea-refine.sh` (or check by hand). It reports whether `docs/brief.md` and `docs/spec.md` exist and lists the files in `docs/ideas/` with their status.

- **New mode** — no brief exists. Run the full process and write `docs/brief.md`.
- **Extend mode** — a brief exists. Read `docs/brief.md`, `docs/spec.md` (if present), and any open ideas in `docs/ideas/` *before* asking anything. The existing problem, goals, constraints, Not Doing list, and approved requirements are now constraints on the new idea. Follow [Extend Mode](#extend-mode-adding-an-idea-to-an-existing-project) for what to write.

If the brief is still `Draft`, ask whether to finish reviewing it first. If an existing idea file covers the same ground, offer to refine that one instead of starting another.

### Phase 1: Understand & Expand (Divergent)

**Goal:** Take the raw idea and open it up.

1. **Restate the idea** as a crisp "How Might We" problem statement. This forces clarity on what's actually being solved.

2. **Ask 3-5 sharpening questions** — no more. Focus on:
   - Who is this for, specifically?
   - What does success look like?
   - What are the real constraints (time, tech, budget, people, rules)?
   - What's been tried before?
   - Why now?

   Use the `AskUserQuestion` tool to gather this input. Do NOT proceed until you understand who this is for and what success looks like.

3. **Generate 5-8 idea variations** using these lenses:
   - **Inversion:** "What if we did the opposite?"
   - **Constraint removal:** "What if budget/time/tech weren't factors?"
   - **Audience shift:** "What if this were for [different user]?"
   - **Combination:** "What if we merged this with [adjacent idea]?"
   - **Simplification:** "What's the version that's 10x simpler?"
   - **10x version:** "What would this look like at massive scale?"
   - **Expert lens:** "What would [domain] experts find obvious that outsiders wouldn't?"

   Each variation gets a one-line reason it exists, not just a name.

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

### Phase 3: Write the Brief (New Mode)

In extend mode, skip to [Extend Mode](#extend-mode-adding-an-idea-to-an-existing-project) instead.

Write `docs/brief.md` (create `docs/` if needed) using the template below. The brief answers **why**, not **how** or **what exactly** — no requirements lists, no tech choices, no screens.

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
- **3-5 goals.** More than five means the project isn't focused yet — go back to Phase 2.
- **The Not Doing list is mandatory.** It is the most valuable part: it makes trade-offs explicit.

Check the word count (`wc -w docs/brief.md`) before presenting it.

### Phase 4: Review Gate (CRITICAL)

After saving the Draft (brief, or idea file plus any brief edits):

1. Tell the user what was written and where, with a three-line summary: the problem, the top goal (or the idea's recommended direction), and the biggest thing on the Not Doing list. In extend mode, also say whether the brief changed and list the edited sections.
2. Ask them to read it and either **accept** it or request changes.
3. **STOP YOUR TURN.** Do not start the spec in the same turn.

When the user requests changes, edit and repeat this gate. When the user accepts:

1. Change `**Status:** Draft` to `**Status:** Accepted` and update the date — on the brief, the idea file, or both, whichever were written or edited.
2. Hand off to `spec-writing` to write or update `docs/spec.md`.

## Extend Mode: Adding an Idea to an Existing Project

When `docs/brief.md` already exists, the new idea gets its own file and must earn its place in the project.

**Before Phase 1:** Read the brief, the spec, and open ideas. Restate the new idea in terms of the existing project: "This adds [X] so that [existing user] can [outcome]." Note which existing features and requirement IDs it touches.

**Fit check (during Phase 2) — answer one of these out loud. It decides whether the brief changes:**

| Finding | Idea file | Brief |
|---|---|---|
| Serves an existing goal | Write it | **No change.** This is the common case. |
| Needs a new goal, same problem and user | Write it | Add the goal with the next number. If that makes more than five, ask the user which to merge or drop. |
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
- **Brief changes:** [None — or the exact edits made]

## Recommended direction
[1-3 paragraphs on how it should work from the user's point of view, and why this direction over the others.]

## Data
[ML and data ideas only — omit otherwise. What data it needs, where it lives or could come from, how much history and labels exist, and how results will be evaluated (held-out data, baseline).]

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
- **Never paste the idea into the brief.** Brief edits are limited to the fit-check table above. Goal numbers stay stable; new goals take the next number. If a goal is dropped, tell the user which spec requirements referenced it.

**Idea status lifecycle:** `Draft` → `Accepted` (user approved here) → `Specced` (set by `spec-writing` once the spec is approved). Parked ideas get `Parked` with a one-line reason, so they aren't re-proposed blindly.

## Anti-patterns to Avoid

- **Don't generate 20+ ideas.** 5-8 well-considered variations beat 20 shallow ones.
- **Don't be a yes-machine.** Push back on weak ideas with specificity and kindness.
- **Don't skip "who is this for."** Every good idea starts with a person and their problem.
- **Don't put requirements in the brief or idea file.** "Users can export to CSV" is a spec line. The brief and idea file say why exporting matters.
- **Don't stretch the brief to hold a feature.** Feature detail goes in an idea file; the brief changes only when the project's goals or constraints do.
- **Don't write the brief before the user picks a direction.** Phase 2 ends with a decision.
- **Don't write the spec in the same turn as the brief or idea file.**
- **Don't ignore the codebase.** Existing architecture is a constraint and an opportunity.

## Tone

Direct, thoughtful, slightly provocative during ideation — a sharp thinking partner, not a facilitator reading from a script. Calm and plain when writing the brief or idea file: they are for readers, not for showing off the ideation.

Read `examples.md` in this skill directory for examples of full sessions, finished briefs (including a quant package), and extend-mode idea files (including an ML feature).

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| I'll generate 20+ ideas to cover all bases | 5-8 well-considered variations beat 20 shallow ones. |
| The user just needs encouragement, not critique | A yes-machine produces weak ideas. Push back with specificity and kindness. |
| Who this is for is obvious — no need to ask | Skipping it means designing for nobody. |
| The brief needs more detail to be useful | Detail belongs in the spec. A brief nobody finishes reading defines nothing. |
| The user said "go", so I'll write the brief and spec together | The gate exists so the *why* is agreed before the *what*. Stop after the brief or idea file. |
| I'll just add the new feature to the brief | The brief is the whole project's why. Feature detail belongs in an idea file; the brief changes only if goals or constraints do. |
| This feature is small, it doesn't need an idea file | Small ideas get short idea files. `spec-writing` still needs to know what it fits, what it touches, and what's out. |
| The new idea is clearly good, no need for a fit check | Good ideas that serve a different user or problem dilute the project. Check fit first. |

## Red Flags

- Generating 20+ shallow variations instead of 5-8 considered ones
- No assumptions surfaced before committing to a direction
- Brief over one page, or full of jargon, file paths, or tech choices
- Brief contains requirements or acceptance criteria
- Brief has no Not Doing list
- Goals that are features ("Add a dashboard") instead of outcomes ("Owners see weekly sales without logging in")
- Spec work started before the brief or idea file was marked Accepted
- Extend mode: feature detail written into the brief, existing goals renumbered, or the brief and spec not read first
- Extend mode: idea file missing *How it fits* (goals served, spec IDs touched, brief changes)

## Verification

Before handing off to `spec-writing`:

- [ ] A clear "How Might We" problem statement was agreed in conversation
- [ ] The target user and what success looks like are defined
- [ ] Multiple directions were explored and the user chose one
- [ ] The turn ended after the Draft was saved; acceptance came in a later turn
- [ ] Status reads `Accepted` only after the user said so

New mode:
- [ ] `docs/brief.md` follows the template and is under ~450 words
- [ ] Goals are numbered outcomes (3-5), not features
- [ ] The Not Doing list is present with a reason for each item

Extend mode:
- [ ] The fit check was answered and the user agreed with it
- [ ] `docs/ideas/<idea-slug>.md` follows the template, covers one idea, and contains no requirements
- [ ] *How it fits* names the goals served, spec IDs touched, and brief changes (or "None")
- [ ] The brief changed only as the fit check allowed, with goal numbers unchanged
