# dev-team2

Skills for taking a project from a raw idea to a written spec. This README covers the project documents those skills produce and how they change over time.

## The documents

| Document | Answers | Written by | Length |
|---|---|---|---|
| `docs/brief.md` | **Why** the project exists: problem, users, goals, constraints, what we're not doing | `idea-refine` | One page or less, plain English |
| `docs/ideas/<idea>.md` | **Why** a new feature is worth adding and how it fits the project | `idea-refine` | 300-700 words |
| `docs/spec.md` | **What** is being built: requirements, acceptance criteria, scope, behavior | `spec-writing` | As long as it needs to be |

The **brief** is the stable foundation. It rarely changes. **Idea files** carry the detail for each addition, so the brief doesn't grow. The **spec** is the single source of truth for what gets built. Every requirement traces back to a brief goal, and features added later also link to their idea file.

## Statuses

| Document | Lifecycle |
|---|---|
| Brief | `Draft` → `Accepted` |
| Idea | `Draft` → `Accepted` → `Specced` (or `Parked`) |
| Spec | `Draft` → `Approved` |

Nothing moves forward until you accept it. Every skill stops after writing a Draft and waits for your review.

## Lifecycles

### New project

```
idea-refine → docs/brief.md (Draft) → you accept → spec-writing → docs/spec.md (Draft) → you approve
```

### Adding a feature

```
idea-refine → docs/ideas/<idea>.md (+ brief edits, if needed) → you accept
            → spec-writing → adds to docs/spec.md → you approve → idea marked Specced
```

`idea-refine` runs a fit check first. Most features serve an existing goal and **leave the brief untouched**. The brief is edited only if the feature adds a goal, changes a constraint, or reverses something on the Not Doing list. If the feature serves a different problem or user, it's pushed back as a possible separate project.

### Changing something that already exists

| Change | Go to | Result |
|---|---|---|
| Small, clear tweak to existing behavior | `spec-writing` | Requirement edited in place (same ID, marked changed), changelog row |
| Rethinking how a feature works | `idea-refine` | New idea file describing the change, then `spec-writing` updates the spec |
| Project direction (goals, users, constraints) | `idea-refine` | Brief edited and set back to Draft. Once you re-accept it, `spec-writing` brings the spec in line |

Spec changes never renumber or delete requirement IDs. Changed requirements keep their ID, and removed ones are struck through and retired. Each change gets a changelog row.

## Skills

| Skill | Phase | Produces |
|---|---|---|
| [`idea-refine`](skills/idea-refine/SKILL.md) | Define | `docs/brief.md`, `docs/ideas/*.md` |
| [`spec-writing`](skills/spec-writing/SKILL.md) | Define | `docs/spec.md` |
