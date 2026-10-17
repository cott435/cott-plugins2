---
name: idea-refine
description: Refines a raw idea into a sharp direction through divergent and convergent thinking. For a new project it writes a one-page brief (docs/brief.md); for a new feature, an idea file (docs/ideas/{idea}.md). Each accepted stage becomes an unsized row in docs/roadmap.md. Use when an idea is vague, when starting a project, when adding a feature idea, or to stress-test assumptions. Triggers on "ideate", "refine this idea", "write a brief" or "stress-test my plan".
---

# Idea Refine

Turns a raw idea into a focused direction and writes it down for the user to accept before anything is specified.

- **New project:** `docs/brief.md`, *why the project exists*: a page or less, plain English. On acceptance, a roadmap stage per agreed stage.
- **Extend** (a brief exists): `docs/ideas/<idea-slug>.md`, *why this feature and how it fits*, with the context `spec-writing` needs; brief edits only if needed. On acceptance, a roadmap stage.

The brief stays the stable "why"; ideas carry each addition's detail; stages live in `docs/roadmap.md`, never as brief goals.

**Not for:** a user unsure what they want at all (`interview-me` if available); an accepted brief or idea that needs requirements (`spec-writing`); bug fixes or small changes with obvious requirements.

`dt` means `python3 ../../scripts/dt.py`, relative to this skill's folder, run from the project root. Examples: `examples.md` (a new project, all phases) and `references/examples-*.md`.

## Workflow

```
MODE CHECK ─→ UNDERSTAND & EXPAND ─→ EVALUATE & CONVERGE ─→ WRITE BRIEF or IDEA ─→ [user accepts] ─→ spec-writing
```

Each arrow waits on the user. Everything is written as **Draft** and becomes **Accepted** only when the user says so.

### Phase 0: Mode check

Run `dt status --skill idea-refine`: the mode, doc statuses, `brief_words`, `brief_goals`, `ideas`, `roadmap_rows`, and references waiting or unassigned. If references are waiting, offer `reference-intake` first (default: run it, then come back).

- **New** (no brief): the full process, writing `docs/brief.md`.
- **Extend** (a brief exists): read `docs/brief.md`, `docs/spec.md`, `docs/roadmap.md` and open ideas in `docs/ideas/` *before* asking anything; their problem, goals, constraints, Not Doing list and requirements constrain the new idea. Read `references/extend.md`.

A `Draft` brief: ask whether to finish reviewing it first. A `Draft`, `Accepted` or `Parked` idea covering the same ground: offer to refine it instead. A `Specced` one is frozen; a change starts a new file.

### Phase 1: Understand & expand

1. **Restate the idea** as a "How Might We" problem statement.
2. **Ask 3-5 sharpening questions**, no more, with `AskUserQuestion`: who it's for, what success looks like, real constraints, what's been tried, why now. Don't proceed until you know who it's for and what success looks like.
3. **Generate 5-8 variations**, each with a one-line reason it exists. Lenses: inversion, constraint removal, audience shift, combination, simplification, 10x version, expert lens. `frameworks.md` has more; pick what fits.

In a codebase, ground variations in what exists and cite files. Read `docs/references.md` too; an idea cites a reference as prior art by `RF-NN`, never its path.

### Phase 2: Evaluate & converge

1. **Cluster** what resonated into 2-3 meaningfully different directions.
2. **Stress-test** each: user value (painkiller or vitamin?), feasibility (cost, hardest part), differentiation (would someone switch?), and for ML and data projects, data: does usable data exist, can we use it, what's the non-ML baseline? "No usable data" is a feasibility failure, not an open question. Rubric: `refinement-criteria.md`.
3. **Surface hidden assumptions:** what you're betting is true, what could kill it, what you're ignoring for now.
4. **Get a decision** on a direction before writing anything.

Be honest, not supportive: say kindly when an idea is weak and push back on complexity. Sharp while ideating; calm and plain when writing.

### Phase 3: Write

New mode: read `references/brief.md` and write the brief; check `wc -w docs/brief.md`. Extend mode: write the idea file per `references/extend.md`. Read `references/roadmap.md` for the stages you'll propose.

### Phase 4: Review Gate (CRITICAL)

1. Say what was written and where, in three lines: the problem, the top goal (or the idea's direction), the biggest Not Doing item. In Extend, say whether the brief changed and which sections. Propose the roadmap stage(s) to add on acceptance (`S3: Classical portfolios`), each with its skills and references, as one question with your proposal as the default.
2. Ask the user to **accept** or request changes.
3. **STOP YOUR TURN.** Never start the spec in the same turn, and never edit the brief or idea and draft the spec in one turn.

**No live user** (headless): don't invent confirmations. Write the Draft, put what the user must confirm (direction, goals, stages) under Open questions, leave Draft, add no roadmap stage, and stop.

| The user says | Do | Then |
|---|---|---|
| Accepted, nothing to change | Set `**Status:** Accepted` and the date on whichever of the brief and idea were written or edited. Add the roadmap stage(s) with their Skills lines, and the stage on each assigned reference. Offer to commit; commit only on a yes | Hand off to `spec-writing` |
| Accepted, with a change | Make exactly that edit. Fully specified: set Accepted and add the stage(s). Needs your judgment: keep Draft | **Stop.** List what you changed; the spec starts next turn |
| Changes requested | Edit, keep Draft | Repeat this gate |
