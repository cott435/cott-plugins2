# New mode: the brief

No `docs/brief.md` yet. Examples: `examples-new.md` (all phases), `examples-process.md` (a non-product idea), `examples-quant.md` (a data-dependent brief).

1. **Phases 1-2** per `ideation.md`.
2. **Phase 3: write the brief** from the template below. Check the word count (`wc -w docs/brief.md`) before presenting it.
3. **Stages** per `roadmap.md`: one per outcome the user agreed in conversation, Source `brief`. If only the first is known, add just that one.

## The brief

Write `docs/brief.md` (create `docs/` if needed) from this template. The brief answers **why**, not **how** or **what exactly** — no requirements lists, no tech choices, no screens.

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
- **3-5 goals, project-level and stage-neutral.** A goal is an outcome of the whole project ("Honest estimates of risk"), never a stage ("Stage 2: PCA works"). If the user describes the project in stages, the stages become roadmap stage rows (`roadmap.md`), and every goal stays true whichever stage is being built. More than five goals means the project isn't focused yet — go back to Phase 2.
- **The Not Doing list is mandatory.** It is the most valuable part: it makes trade-offs explicit.
