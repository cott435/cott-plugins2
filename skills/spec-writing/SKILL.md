---
name: spec-writing
description: Writes the project specification (docs/spec.md) — requirements, acceptance criteria, scope boundaries, and expected behavior — from an accepted brief, and adds accepted feature ideas (docs/ideas/*.md) to an existing spec without breaking what is already approved. Use when docs/brief.md has been accepted and no spec exists yet, when an idea in docs/ideas/ is accepted and needs adding to the spec, or when the user asks to write, update, or extend the spec.
---

# Spec Writing

## Overview

The brief (`docs/brief.md`) says **why** the project exists; idea files (`docs/ideas/*.md`) say why each later feature is worth adding and how it fits. The spec (`docs/spec.md`) says **what** is being built: every requirement, how we'll know it works, and where the edges are. It is a product spec, not a technical design — it describes behavior the user can observe, not frameworks, schemas, or file layouts. Those decisions come next, in `architecture-design` (`docs/architecture.md`).

## When to Use

- `docs/brief.md` is marked `Accepted` and `docs/spec.md` does not exist
- An idea in `docs/ideas/` is `Accepted` and needs adding to the spec
- The user asks to write, update, or extend the spec

**Not for:**
- Ideas that are still vague, or projects with no brief (use `idea-refine` first)
- Technical design or architecture (use `architecture-design` after the spec is approved), or task breakdown (a planning skill)
- One-line fixes where the expected behavior is obvious

## Preconditions

Run `bash skills/spec-writing/scripts/spec-status.sh` first. It reports the mode, brief and spec status, which ideas are `Accepted` and waiting to be specced, and the next free requirement ID for each prefix — use those IDs rather than counting by hand.

1. Read `docs/brief.md`. If it doesn't exist, stop and route to `idea-refine`.
2. Decide the mode:
   - **New mode** — `docs/spec.md` does not exist. The brief is the input.
   - **Extend mode** — `docs/spec.md` exists. The input is an idea file in `docs/ideas/`. Read the spec fully, then see [Extend Mode](#extend-mode-adding-an-idea-to-an-existing-spec).
3. Check the input's Status. If it is `Draft`, ask the user whether they accept it; proceed only once they do (and set it to `Accepted`). In extend mode, also check the brief: if the idea edited it, the brief must be `Accepted` too.
4. Extend mode with no idea file (the user just describes a feature): route to `idea-refine` first — unless the change is small and fully clear, in which case confirm with the user and add it directly, noting "no idea file" in the Changelog row.
5. If inside a codebase, scan for existing behavior the spec must respect (current features, data, integrations). Ground requirements in what exists.

## The Process

```
READ BRIEF ─→ SURFACE ASSUMPTIONS ─→ CLARIFY ─→ WRITE SPEC ─→ [user approves] ─→ architecture-design
```

### Step 1: Map Goals to Features

In new mode, start from the brief's numbered goals. (In extend mode, start from the idea file — see below.) Propose the features needed to achieve them. Show the user a short mapping before writing:

```
Goal 1 (regulars reorder in < 30s)   → Saved orders, Text reorder
Goal 2 (no extra daily work for owner) → Regulars setup, Order notifications
Goal 3 (owner keeps full value)        → Direct payment
```

Every feature must serve at least one goal. A feature that serves no goal is either missing from the brief (go back to `idea-refine`) or shouldn't be built. Every goal must have at least one feature.

Give each feature a short, stable **feature code** — 2-5 capital letters (`SAVE`, `TEXT`, `PAY`). Codes are chosen once and never renamed; requirement IDs depend on them.

### Step 2: Surface Assumptions

Before writing requirements, list what you're assuming and let the user correct it:

```
ASSUMPTIONS I'M MAKING:
1. A customer has exactly one "usual" order per restaurant
2. Payment happens before the restaurant is notified
3. If the restaurant doesn't confirm within 10 minutes, the customer is told
→ Correct me now or I'll proceed with these.
```

Don't silently fill gaps. Assumptions are where specs most often go wrong.

### Step 3: Clarify

Ask only the questions whose answers change requirements — use `AskUserQuestion`, at most 3-5 at a time. Good targets: edge cases (what happens when it fails?), limits (how many? how fast?), permissions (who can do this?), and anything the brief leaves open.

**Turn vague goals into testable conditions.** If the brief says "fast", propose a number and ask:

```
"Reorder in under 30 seconds" →
- From opening the text to order confirmed takes ≤ 2 taps
- Confirmation text arrives within 10 seconds of payment
→ Are these the right targets?
```

### Step 4: Write the Spec

Write `docs/spec.md` with this template:

```markdown
# [Project Name] — Spec

**Status:** Draft · **Last updated:** YYYY-MM-DD · **Brief:** [brief.md](brief.md)

## Summary
[2-3 sentences: what is being built. Link to the brief for why — don't repeat it.]

## Users
| User | What they need to do |
|---|---|
| [Primary user] | [...] |

## Scope
**In scope:** [features, by name]
**Out of scope:** [what we're not building — include everything on the brief's Not Doing list, plus anything decided during clarification]

## Features

### [Feature name] (`CODE`)
**Serves:** Goal 1, Goal 3
**Source:** [ideas/<slug>.md](ideas/<slug>.md) *(extend mode only — omit for features from the original brief)*
**Behavior:** [2-4 sentences or a short numbered flow describing what the user experiences.]

**Requirements**
- **CODE-01** [One testable statement of what the system does.]
  - Given [context], when [action], then [observable result].
  - Given [...], when [...], then [...].
- **CODE-02** [...]
  - Given [...], when [...], then [...].

**Edge cases & errors**
- [Situation] → [expected behavior]

## Data requirements
*(Data and ML projects only — omit otherwise.)*
- **DATA-01** [What data the system needs: content, coverage, history, frequency, freshness — not which vendor.]
  - Given [...], when [...], then [...].

## Quality requirements
- **QR-01** [Measurable non-functional requirement: speed, reliability, accessibility, privacy, security.]
  - [How it's checked.]

## Assumptions
- [Assumptions the user confirmed in Step 2]

## Open questions
- [Unresolved items, each with who can answer it. Omit if none.]

## Changelog
| Date | Change | Source | IDs |
|---|---|---|---|
| YYYY-MM-DD | Initial spec | brief.md | all |
```

**Writing rules:**

- **One requirement, one behavior.** If a requirement contains "and", it's probably two.
- **Every requirement has at least one acceptance criterion** in Given/When/Then form. If you can't write one, the requirement isn't clear yet.
- **Describe behavior, not implementation.** "The customer sees their usual order" — not "the app queries the orders table."
- **Use exact numbers.** "≤ 2 seconds", "up to 50 regulars", never "fast" or "many".
- **Requirement IDs are permanent.** `CODE-NN`, numbered within the feature, never reused or renumbered.
- **Quality requirements only when measurable.** Leave out generic wishes ("should be secure"); keep checkable ones ("passwords are never shown in full").
- **No tech stack, schemas, endpoints, or file structure.** Those belong to `architecture-design`.

**Data and ML projects — extra rules:**

- **Specify the data, not the source.** `DATA-NN` requirements say what the data must contain and guarantee ("daily prices for all US stocks, including delisted ones, since 2010"; "every record is stamped with the date it became known"). Which API, vendor, or dataset meets them is an architecture decision, made by checking candidates against these requirements. Name a source only when the brief makes it a fixed constraint (our own database, a required benchmark).
- **Write data guarantees as testable criteria.** Leakage, look-ahead, survivorship bias, and coverage gaps are requirements, not hopes: "Given a backtest date D, when the strategy requests data, then no value published after D is returned."
- **Model quality is a requirement with a baseline.** Acceptance criteria name the metric, the held-out data, the threshold, and the baseline to beat: "Given the most recent 6 months of plates (never trained on), when ranked, then reviewing the top 20% catches ≥ 90% of scientist-failed plates, and beats ranking by Z′ alone." Never "the model is accurate".
- **No model types or libraries.** "Gradient boosting" or "PyTorch" are architecture decisions; the spec says what the model must achieve.

### Step 5: Review Gate (CRITICAL)

After saving the Draft:

1. Summarize: number of features and requirements, the goal → feature mapping, and the Open Questions.
2. Ask the user to approve the spec or request changes.
3. **STOP YOUR TURN.** Do not start the architecture or code in the same turn.

On changes, edit and repeat the gate. On approval, set `**Status:** Approved`, update the date, mark the idea file `Specced` (extend mode), and point the user to the next step (`architecture-design`).

## Extend Mode: Adding an Idea to an Existing Spec

The idea file is the main input. Its sections map onto the spec like this:

| Idea file section | Used for |
|---|---|
| How it fits → Serves | `Serves:` line of each new feature |
| How it fits → Touches | Which existing requirements to check, change, or extend |
| Recommended direction | Feature Behavior and the requirements |
| Not doing | Out of scope |
| What success looks like | Quality requirements, where measurable |
| Open questions | Questions to ask in Step 3 — resolve them, or carry them into the spec's Open questions |

Run Steps 1-5 for the idea only, with these rules:

1. **Check for conflicts first.** Start with the IDs under *Touches*, then search the rest of the spec for anything else the idea contradicts. List conflicts for the user before writing — "Shared editing changes **EDIT-03** (only the owner can edit). Proposed: owner *or invited editors* can edit."
2. **Add, don't rewrite.**
   - New feature → new `### Feature (CODE)` section with a new code and IDs starting at `-01`.
   - New behavior in an existing feature → next unused number in that feature (if `SAVE-04` is the highest, add `SAVE-05`, even if `SAVE-02` was removed). `spec-status.sh` reports it.
   - Changed requirement → edit it in place, keep its ID, and append `*(changed YYYY-MM-DD)*`.
   - Removed requirement → replace its text with `~~[old text]~~ *Removed YYYY-MM-DD: [reason]*`. Never delete the line — the ID stays retired.
3. **Link back to the idea.** Add `**Source:** [ideas/<slug>.md](ideas/<slug>.md)` under the `Serves:` line of each new feature section, so readers can find the full why.
4. **Update everything it touches:** Summary, Users, Scope (both lists), Serves lines, Open questions.
5. **Add one Changelog row** naming the idea file as the source and listing every added, changed, and removed ID.
6. **Set the spec Status back to Draft** and run the Review Gate, highlighting the changed IDs so the user reviews only what's new.

**After the spec is approved,** close the loop on the idea file: set its Status to `Specced` and add a line under the header — `**Spec:** CODE-01–CODE-04, EDIT-03 (changed)`. Don't otherwise edit the idea; it's the record of why the feature was added.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The brief is clear enough — I'll skip the acceptance check" | The gate exists so *why* is agreed before *what*. Ask. |
| "Acceptance criteria are obvious from the requirement" | If they're obvious, they take ten seconds to write. If they're not, you just found a gap. |
| "I'll add the tech stack so the architecture goes faster" | Mixing design into requirements locks in decisions before anyone reviewed them. Keep the spec about behavior. |
| "Renumbering makes the spec tidier" | Plans, tests, and PRs reference IDs. Renumbering silently breaks every one of them. |
| "The idea file covers it, I don't need to read the existing spec" | The idea lists what it *thinks* it touches. Conflicts it missed are found by reading the spec. |
| "It's just one new feature — I'll rewrite the spec cleanly" | Rewriting hides what changed and re-opens approved decisions. Add, mark, and log. |
| "This edge case is unlikely" | Unlikely edge cases are where users lose data. Write the expected behavior, even if it's "show an error and keep the draft". |

## Red Flags

- Writing a spec with no accepted brief, or adding a feature from an idea file still in Draft
- A feature with no `Serves:` goal, or a brief goal with no feature
- Requirements with no Given/When/Then criteria
- Vague words in requirements: "fast", "easy", "intuitive", "robust", "etc."
- Tech stack, database tables, API routes, or file paths in the spec
- Data or ML project with no `DATA-` requirements, a specific vendor chosen without the brief requiring it, or model criteria with no baseline or held-out data
- Out of scope missing items from the brief's Not Doing list
- Extend mode: IDs renumbered, removed requirements deleted, no Changelog row, or conflicts with existing requirements not raised
- Extend mode: new feature with no `Source:` link, or the idea file left `Accepted` after the spec was approved
- Architecture or code started in the same turn the spec was written

## Verification

Before handing off to `architecture-design`:

- [ ] `docs/brief.md` is `Accepted` and linked from the spec header (and, in extend mode, the idea file is `Accepted`)
- [ ] Every brief goal maps to at least one feature; every feature lists the goals it serves
- [ ] Every requirement has a permanent ID and at least one Given/When/Then criterion
- [ ] Edge cases and error behavior are written for each feature
- [ ] Out of scope includes everything on the brief's Not Doing list
- [ ] No implementation details (stack, schema, endpoints, files, vendors, model types)
- [ ] Data/ML projects: data needs are `DATA-` requirements with testable guarantees; model criteria name metric, held-out data, threshold, and baseline
- [ ] Assumptions were confirmed by the user; open questions are listed
- [ ] The turn ended after the Draft was saved; approval came in a later turn
- [ ] Extend mode: no IDs renumbered or reused, changes marked in place, Changelog row added, conflicts raised with the user
- [ ] Extend mode: new features link to their idea file; the idea's Open questions are resolved or carried over; after approval the idea is `Specced` with its spec IDs listed
