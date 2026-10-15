# dev-team2

Skills for taking a project from a raw idea to a written spec and architecture. This README covers the project documents those skills produce and how they change over time.

## The documents

| Document | Answers | Written by | Length |
|---|---|---|---|
| `docs/brief.md` | **Why** the project exists: problem, users, goals, constraints, what we're not doing | `idea-refine` | One page or less, plain English |
| `docs/ideas/<idea>.md` | **Why** a new feature is worth adding and how it fits the project | `idea-refine` | 300-700 words |
| `docs/spec.md` | **What** is being built: requirements, acceptance criteria, scope, behavior | `spec-writing` | As long as it needs to be |
| `docs/architecture.md` | **How** it will be built: components, dependencies, interfaces, technical decisions | `architecture-design` | 1-3 pages (single package); a system map plus `docs/architecture/<package>.md` per package (multi-package) |

The **brief** is the stable foundation. It rarely changes. **Idea files** carry the detail for each addition, so the brief doesn't grow. The **spec** is the single source of truth for what gets built. Every requirement traces back to a brief goal, and features added later also link to their idea file. The **architecture** gives every spec requirement a home in a component and records each technical choice as a numbered decision (`AD-NN`).

A proof of concept gets one short architecture file. A monorepo gets a system map (packages, dependency rules, contracts between packages) plus one doc per package.

## Statuses

| Document | Lifecycle |
|---|---|
| Brief | `Draft` → `Accepted` |
| Idea | `Draft` → `Accepted` → `Specced` (or `Parked`) |
| Spec | `Draft` → `Approved` |
| Architecture | `Draft` → `Approved`; each decision `Proposed` → `Accepted` → `Superseded by AD-NN` |

Nothing moves forward until you accept it. Every skill stops after writing a Draft and waits for your review.

## Lifecycles

### New project

```
idea-refine → docs/brief.md (Draft) → you accept
            → spec-writing → docs/spec.md (Draft) → you approve
            → architecture-design → docs/architecture.md (Draft) → you approve
```

### Adding a feature

```
idea-refine → docs/ideas/<idea>.md (+ brief edits, if needed) → you accept
            → spec-writing → adds to docs/spec.md → you approve → idea marked Specced
            → architecture-design → places the new requirements in the design → you approve
```

`idea-refine` runs a fit check first. Most features serve an existing goal and **leave the brief untouched**. The brief is edited only if the feature adds a goal, changes a constraint, or reverses something on the Not Doing list. If the feature serves a different problem or user, it's pushed back as a possible separate project.

### Changing something that already exists

| Change | Go to | Result |
|---|---|---|
| Small, clear tweak to existing behavior | `spec-writing` | Requirement edited in place (same ID, marked changed), changelog row |
| Rethinking how a feature works | `idea-refine` | New idea file describing the change, then `spec-writing` updates the spec |
| Project direction (goals, users, constraints) | `idea-refine` | Brief edited and set back to Draft. Once you re-accept it, `spec-writing` brings the spec in line |
| Technical change (library, data source, performance fix) with no spec change | `architecture-design` | New decision that supersedes the old one; affected sections updated |
| Project outgrows one package | `architecture-design` | Split into packages: root becomes a system map, one doc per package |
| Code has drifted from the design | `architecture-design` | Mismatches listed; you decide whether the doc or the code changes |

Spec and architecture changes never renumber or delete IDs. Changed requirements keep their ID, and removed ones are struck through and retired. Each change gets a changelog row.

## Data and ML projects

Data decisions are spread across the stages on purpose:

| Stage | Decides | Example |
|---|---|---|
| Brief / idea (`idea-refine`) | Whether usable data **exists** and is affordable and legal. The non-ML baseline. | "Need daily US prices including delisted companies, under $100/month" |
| Spec (`spec-writing`) | What the data must **contain and guarantee** (`DATA-` requirements). Model targets against a baseline. | "No value published after date D is visible to a backtest on D" |
| Architecture (`architecture-design`) | **Which** API, vendor, or dataset, and which model type, each recorded as a decision | Candidates are checked against the `DATA-` requirements and the brief's budget |

A data source is named earlier only when it's a fixed constraint, such as your own database or a required benchmark.

## Skills

| Skill | Phase | Produces |
|---|---|---|
| [`idea-refine`](skills/idea-refine/SKILL.md) | Define | `docs/brief.md`, `docs/ideas/*.md` |
| [`spec-writing`](skills/spec-writing/SKILL.md) | Define | `docs/spec.md` |
| [`architecture-design`](skills/architecture-design/SKILL.md) | Design | `docs/architecture.md`, `docs/architecture/*.md` |
