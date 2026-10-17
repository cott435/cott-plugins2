---
name: spec-writing
description: Writes the project specification (docs/spec.md) — requirements, acceptance criteria, scope boundaries, and expected behavior — from an accepted brief, and adds accepted feature ideas (docs/ideas/*.md) to an existing spec without breaking what is already approved. Use when docs/brief.md has been accepted and no spec exists yet, when an idea in docs/ideas/ is accepted and needs adding to the spec, or when the user asks to write, update, or extend the spec.
---

# Spec Writing

The brief (`docs/brief.md`) says **why** the project exists; idea files (`docs/ideas/*.md`) say why each later feature is worth adding. The spec (`docs/spec.md`) says **what** is built: every requirement, how we'll know it works, and where the edges are. It describes observable behavior, never frameworks, schemas or file layouts (`architecture-design`'s).

**Not for:** vague ideas or projects with no brief (`idea-refine` first); technical design, pipelines or tasks; one-line fixes with obvious behavior.

## Preconditions

Run `python3 ../../scripts/dt.py status --skill spec-writing` first (path relative to this skill's folder, run from the project root). It reports the mode, brief and spec status, `ideas_ready` (Accepted ideas waiting), `skills`, and `prefixes` (the next free requirement ID per prefix; use those, never count by hand).

1. Read `docs/brief.md`; if there is none, route to `idea-refine`.
2. **New mode:** no `docs/spec.md`; the brief is the input. **Extend mode:** the spec exists and an idea file is the input; read the spec fully, then `references/extend.md`.
3. A `Draft` input: ask whether the user accepts it, and proceed only once they do (set it `Accepted`). In Extend, a brief the idea edited must be `Accepted` too.
4. Extend with no idea file (the user just describes a feature): route to `idea-refine`, unless the change is small and fully clear; then confirm and add it, noting "no idea file" in the Changelog row.
5. In a codebase, ground requirements in existing behavior. Read `docs/references.md` summaries for behavior worth requiring (references waiting: `reference-intake` first); the spec states the behavior, never the reference, its file or its functions.
6. In every round, check the installed skills (`dt status`'s `skills`, plus those in your context). A step one owns (a hypothesis test, a security review, a data workflow) names the skill in its requirement, with what it's given and what counts as a pass: "Each candidate feature is tested with the `<skill name>` skill on held-out residual returns; it passes only if the null is rejected at 5% after correction." Never write your own version of its procedure.

## Process

```
READ BRIEF ─→ SURFACE ASSUMPTIONS ─→ CLARIFY ─→ WRITE SPEC ─→ [user approves] ─→ architecture-design
```

### Step 1: Map goals to features

From the brief's numbered goals (Extend: from the idea file), propose features and show the mapping before writing:

```
Goal 1 (regulars reorder in < 30s)     → Saved orders, Text reorder
Goal 2 (no extra daily work for owner) → Regulars setup, Order notifications
```

Every feature serves a goal (else it's missing from the brief or shouldn't be built); every goal has a feature. **Every stage the brief and roadmap list is specced in full** in a New round: features, requirements, criteria and edge cases for all of them, never "S1 in full, the rest outlined". Later skills design only what the spec holds.

Each feature gets a stable **feature code** of 2-5 capitals (`SAVE`, `TEXT`), chosen once and never renamed. `RF` is reserved for references.

### Step 2: Surface assumptions

List what you're assuming and let the user correct it ("ASSUMPTIONS I'M MAKING: 1. … → Correct me now or I'll proceed with these."). Never fill gaps silently.

### Step 3: Clarify

Ask only what changes requirements (edge cases, limits, permissions, gaps in the brief), with `AskUserQuestion`, 3-5 at a time at most. Turn vague goals into testable conditions by proposing a number: "Reorder in under 30 seconds" → "≤ 2 taps from opening the text to confirmed; confirmation within 10 seconds of payment. Right targets?"

### Step 4: Write the spec

Read `references/spec.md` and write `docs/spec.md` from its template, following its writing rules (and its data and ML rules where they apply).

### Step 5: Review Gate (CRITICAL)

Run the hygiene check in `references/spec.md` (implementation names; in Extend also out-of-scope lines and leftovers). Then:

1. Summarize: feature and requirement counts, the goal → feature mapping, Open questions.
2. Ask the user to approve or request changes.
3. **STOP YOUR TURN.** Never start the architecture or code in the same turn, and never edit the spec and draft the architecture in one turn.

**No live user** (headless): don't invent confirmations. Write the spec, put unconfirmed assumptions and questions under Open questions, leave Draft, and stop.

| The user says | Do | Then |
|---|---|---|
| Approved, nothing to change | Set `**Status:** Approved` and the date; in Extend, mark the idea `Specced` and freeze it (`references/extend.md`). Offer to commit the spec and idea; commit only on a yes | Hand off to `architecture-design` |
| Approved, with a change ("make QR-02 ≤ 5 minutes") | Make exactly that edit. Fully specified: set Approved. Needs your judgment: keep Draft | **Stop.** List what you changed; the architecture starts next turn |
| Changes requested | Edit, keep Draft | Repeat this gate |
