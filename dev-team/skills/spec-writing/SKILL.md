---
name: spec-writing
description: Writes the project specification (docs/spec.md) — requirements, acceptance criteria, scope boundaries, and expected behavior — from an accepted brief, and adds accepted feature ideas (docs/ideas/*.md) to an existing spec without breaking what is already approved. Use when docs/brief.md has been accepted and no spec exists yet, when an idea in docs/ideas/ is accepted and needs adding to the spec, or when the user asks to write, update, or extend the spec.
---

# Spec Writing

The brief (`docs/brief.md`) says **why** the project exists; idea files (`docs/ideas/*.md`) say why each later feature is worth adding. The spec (`docs/spec.md`) says **what** is built: every requirement, how we'll know it works, and where the edges are. It describes observable behavior, never frameworks, schemas or file layouts (`architecture-design`'s).

**Writes:** `docs/spec.md`, and the Status line of the brief or idea file it takes as input.

**IDs:** each feature gets a stable **feature code** of 2-5 capitals (`SAVE`, `TEXT`), chosen once and never renamed; `RF` (references) and `PB` (probes) are reserved. Requirements are numbered under their code (`SAVE-01`), plus `DATA-NN` and `QR-NN`. Every feature serves a goal (else it's missing from the brief or shouldn't be built).

**Not for:** vague ideas or projects with no brief (`idea-refine` first); technical design, pipelines or tasks; one-line fixes with obvious behavior.

## Preconditions

Run `python3 ../../scripts/dt.py status --skill spec-writing` first (path relative to this skill's folder, run from the project root; write it out each call, never as a shell variable). It reports the mode, brief and spec status, `ideas_ready` (Accepted ideas waiting), `skills`, and `prefixes` (the next free requirement ID per prefix; use those, never count by hand).

1. Read `docs/brief.md`.
2. A `Draft` input: ask whether the user accepts it, and proceed only once they do (set it `Accepted`).
3. Read `docs/requests.md`, the user's own words. `requests_open` lists the ones the spec must honour; follow `../idea-refine/references/requests.md` for them and for every answer you get.
4. In a codebase, ground requirements in existing behavior. Read `docs/references.md` summaries for behavior worth requiring (references waiting: `reference-intake` first); the spec states the behavior, never the reference, its file or its functions.
5. In every round, check the installed skills (`dt status`'s `skills`, plus those in your context). A step one owns (a hypothesis test, a security review, a data workflow) names the skill in its requirement, with what it's given and what counts as a pass: "Each candidate feature is tested with the `<skill name>` skill on held-out weeks; it passes only if its lift is significant at 5% after correction." Never write your own version of its procedure.

## Modes

| Mode | When | Read |
|---|---|---|
| Blocked | No `docs/brief.md` | Stop; start what `dt next` names, this turn |
| New | No `docs/spec.md`; the brief is the input | `references/new.md` |
| Extend | The spec exists; an idea file, or a change another skill routed here (`routed_changes`), is the input | `references/extend.md` |

`references/spec.md` holds the template, writing rules and hygiene check; the mode file says when to read it.

## Asking

- **Surface assumptions.** List what you're assuming and let the user correct it ("ASSUMPTIONS I'M MAKING: 1. … → Correct me now or I'll proceed with these."). Never fill gaps silently.
- **Clarify.** Ask only what changes requirements (edge cases, limits, permissions, gaps in the brief), with `AskUserQuestion`, 3-5 at a time at most. Turn vague goals into testable conditions by proposing a number: "Reorder in under 30 seconds" → "≤ 2 taps from opening the text to confirmed; confirmation within 10 seconds of payment. Right targets?"

## Review Gate (CRITICAL)

Run the hygiene check in `references/spec.md`, and the gate steps your mode file adds. Then:

1. Summarize: feature and requirement counts, the goal → feature and stage → feature mappings, the **Your words** line (requests honoured and changed), Open questions.
2. Ask the user to approve (a yes also commits) or request changes.
3. **STOP YOUR TURN.** Never start the architecture or code in the same turn, and never edit the spec and draft the architecture in one turn.

**No live user** (headless): don't invent confirmations. Write the spec, put unconfirmed assumptions and questions under Open questions, leave Draft, and stop.

| The user says | Do | Then |
|---|---|---|
| Approved, nothing to change | Set `**Status:** Approved` and the date, do the on-approval step your mode file names, and `python3 ../../scripts/dt.py route --done spec-writing` if `routed_changes` listed any. Commit the spec and idea if `git status` lists them | **Stop.** Next is `architecture-design`: say so; never ask whether to start it |
| Approved, with a change ("make QR-02 ≤ 5 minutes") | Make exactly that edit. Fully specified: set Approved. Needs your judgment: keep Draft | **Stop.** List what you changed; the architecture starts next turn |
| Changes requested | Edit, keep Draft | Repeat this gate |
