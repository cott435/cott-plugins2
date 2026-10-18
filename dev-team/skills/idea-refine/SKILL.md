---
name: idea-refine
description: Refines a raw idea into a sharp direction through divergent and convergent thinking. For a new project it writes a one-page brief (docs/brief.md); for a new feature, an idea file (docs/ideas/{idea}.md). Each accepted stage becomes an unsized row in docs/roadmap.md. Use when an idea is vague, when starting a project, when adding a feature idea, or to stress-test assumptions. Triggers on "ideate", "refine this idea", "write a brief" or "stress-test my plan".
---

# Idea Refine

Turns a raw idea into a focused direction and writes it down for the user to accept before anything is specified. idea-refine makes and edits the brief, writes an idea file for each addition, and is in charge of the first stage split: it starts `docs/roadmap.md` and adds every stage after.

## What it owns

- **`docs/brief.md`**, *why the project exists*: a page or less, plain English, the stable "why".
- **`docs/ideas/<idea-slug>.md`**, *why this feature and how it fits*, with the context `spec-writing` needs. Ideas carry each addition's detail, so the brief doesn't grow.
- **Roadmap stages** (`S<n>`, from `dt next-id S`): the stage rows and each `## S<n>` section's `**Outline:**` and `**Skills:**` lines. Stages live in `docs/roadmap.md`, never as brief goals.
- **`docs/references.md`**: only the `**Milestones:**` field of entries the user assigns to a stage.
- **`docs/requests.md`**, *what the user said*, verbatim: idea-refine starts it, recording each fact, constraint, tool, choice and answer as the user gives it, with `dt request add`. `references/requests.md` holds its rules; every planning skill follows them, because the brief compresses and later skills often run in a fresh session.

**Never:** sizes or cuts a stage, or writes milestone rows and `## M<n>` sections (`build-planning`); writes a Status* cell (`dt roadmap`); writes requirements (`spec-writing`) or picks tools, APIs or datasets (`architecture-design`).

**Not for:** a user unsure what they want at all (`interview-me` if available); an accepted brief or idea that needs requirements (`spec-writing`); bug fixes or small changes with obvious requirements.

`dt` means `python3 ../../scripts/dt.py`, relative to this skill's folder, run from the project root; write it out each call, never as a shell variable.

## Picking a mode

Run `dt status --skill idea-refine`: the mode, doc statuses, `brief_words`, `brief_goals`, `ideas`, `roadmap_rows`, and references waiting or unassigned. If references are waiting, offer `reference-intake` first (default: run it, then come back).

## Modes

| Mode | When | Read |
|---|---|---|
| New | No brief | `references/new.md`: writes `docs/brief.md` and the first stages |
| Extend | A brief exists | `references/extend.md`: writes an idea file, edits the brief only if the fit check says so |

```
MODE CHECK ─→ 1 UNDERSTAND & EXPAND ─→ 2 EVALUATE & CONVERGE ─→ 3 WRITE BRIEF or IDEA ─→ 4 REVIEW GATE ─→ [user accepts] ─→ spec-writing
```

## Asking and tone

Each arrow waits on the user. Everything is written as **Draft** and becomes **Accepted** only when the user says so. Be honest, not supportive: say kindly when an idea is weak and push back on complexity. Sharp while ideating; calm and plain when writing.

## Review Gate (CRITICAL)

1. Say what was written and where, in three lines: the problem, the top goal (or the idea's direction), the biggest Not Doing item. Propose the roadmap stage(s) to add on acceptance (`S3: Features & boosting`), each with its skills and references, as one question with your proposal as the default.
2. Ask the user to **accept** or request changes.
3. **STOP YOUR TURN.** Never start the spec in the same turn, and never edit the brief or idea and draft the spec in one turn.

**No live user** (headless): don't invent confirmations. Write the Draft, put what the user must confirm (direction, goals, stages) under Open questions, leave Draft, add no roadmap stage, and stop.

| The user says | Do | Then |
|---|---|---|
| Accepted, nothing to change | Set `**Status:** Accepted` and the date on whichever of the brief and idea were written or edited. Add the roadmap stage(s) with their Skills lines, and the stage on each assigned reference. Offer to commit; commit only on a yes | Hand off to `spec-writing` |
| Accepted, with a change | Make exactly that edit. Fully specified: set Accepted and add the stage(s). Needs your judgment: keep Draft | **Stop.** List what you changed; the spec starts next turn |
| Changes requested | Edit, keep Draft | Repeat this gate |
