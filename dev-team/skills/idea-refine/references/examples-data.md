# Example: a demand-forecasting package

A data-dependent New project with its first roadmap stages, then a later idea routing stage skills and references.

## GridLoad (New Project, Data-Dependent)

**User invokes:** `/ideate a Python package for forecasting our utility's electricity demand — I keep rewriting the same notebook code`

### Phase 1: Understand & Expand

**Skill response:**

> **How might we** get from a forecast idea to an evaluation we can actually trust, without rebuilding the data and scoring plumbing every time?

Before expanding:

1. **Who uses it?** Just you, or a small team that needs to compare each other's results?
2. **What horizon and resolution?** Day-ahead? Hourly? By region?
3. **What data do you have today, and what's the budget?** Free sources, an existing subscription, or room to pay?
4. **Research only, or does this end up feeding operations?**

**User responds:** "Me and two analysts. Hourly by region, day-ahead is what matters. We have the utility's meter export and pull weather from a free public weather API. Budget maybe $100/month. Research only for now."

**Skill continues:**

"Rewriting notebook code" is the symptom. The expensive problem is **not trusting the results**. One-off notebooks are where look-ahead and missing history creep in, and a forecast that only scores well because of a bug is worse than no forecast.

Here are 5 variations:

1. **Model Engine First:** A clean training and scoring loop. Forecasts plug in. Data is the user's problem.
2. **Data Layer First (Inversion):** Start from trustworthy data, not the engine: a local store of readings and weather as known at any time, with one interface. Any simple model is fine once the data is right.
3. **Simplification — Tabular Only:** No sequence models. A forecast is a function from a region-by-hour feature table to predictions. Fast and enough for day-ahead.
4. **Combination — Notebook Kit:** Keep notebooks, but ship the pieces as a library: data loader, scoring function, standard error report.
5. **10x — Full Platform:** Scheduled data pulls, experiment tracking, and a model registry. Clearly too much for three people.

### Phase 2: Evaluate & Converge

**Data feasibility decides this one.** Today's readings are easy: they are the utility's own export. **Meter history including decommissioned meters** is not: the export lists today's registry, so every regional total quietly drops removed meters and past load looks wrong. Scoring with weather actuals where only the forecast was known has the same effect on errors. That's the dealbreaker to check first: can both be had within $100/month?

**Direction (2 + 3): Trustworthy data layer + tabular forecasts.** It attacks the real problem (trust). It fits day-ahead hourly forecasts. Hiding the weather source behind one interface keeps the provider decision open.

**Direction (1): Model engine.** More flexible training, but none of your forecasts need it yet. Pushing back: this is where these projects usually sink months.

The user picks (2 + 3).

### Phase 3: Write the Brief

```markdown
# GridLoad

**Status:** Draft · **Last updated:** 2026-10-14

## The problem
Testing a forecast idea takes about a week of one-off notebook code: pulling readings and weather, cleaning them, and writing the scoring from scratch. Results can't be compared across ideas. Worse, subtle mistakes, like using weather that wasn't known at forecast time, make forecasts look better than they are.

## Who it's for
A small forecasting team (1-3 people) testing day-ahead hourly demand forecasts for one utility's service area.

## Goals
1. Go from a forecast idea to an evaluation report in under a day.
2. Trust the results: no peeking at weather that wasn't forecast yet, and no silently dropping meters that were decommissioned.
3. Compare any two forecasts side by side on the same data and held-out weeks.
4. Change weather providers without rewriting forecasts.

## Constraints
- Python, running on a laptop.
- Hourly readings by region, one service area only.
- Data budget: free sources to start, under $100/month at most.

## What success looks like
- Three of our past notebook forecasts re-run in the package, with matching results or explained differences.
- A new forecast takes under a day from idea to report.

## What we're betting on
- Hourly regional data is enough for the forecasts we care about.
- Affordable weather data is good enough for research (not for operations).
- We can get history that includes decommissioned meters, and weather forecasts as issued, within budget. If not, Goal 2 needs rethinking.

## Not doing
- Feeding the operational forecast — research only.
- Sub-hourly data, single-customer forecasts, or prices.
- A model engine — day-ahead tabular forecasts don't need one yet.
- A user interface — notebooks and a command line are enough.

## Open questions
- Which weather provider? (Decided in the architecture, against the data requirements in the spec.)
```

*Notice what's **not** in the brief: a weather API. The brief records data **needs** (hourly, by region, includes decommissioned meters, forecasts as issued, under budget) as constraints and bets. `spec-writing` turns them into data requirements, and the provider is chosen in the architecture against those requirements.*

**On acceptance.** In Phase 2 the user agreed to build in two stages: the trustworthy data layer first, then tabular forecasts. The stages are not goals: Goals 1-4 hold whichever stage is being built. The skill sets the brief to Accepted, creates `docs/roadmap.md` with a stage row per stage (IDs from `dt next-id S`), and runs `dt roadmap` to fill Status:

```markdown
| Stage | Name | Source | Status* |
|---|---|---|---|
| S1 | As-of data | brief | Idea |
| S2 | Tabular forecasts | brief | Idea |

## S1: As-of data
**Outline:** Load hourly readings and weather as they were known at any time, including meters that were later decommissioned.
**Skills:** —

## S2: Tabular forecasts
**Outline:** Turn a region-by-hour feature table into a scored day-ahead forecast report, comparable across forecasts.
**Skills:** —
```

The project has no skills installed yet, so the gate asked "No installed skill fits either stage, so both get `Skills: —`. OK?" and the user said yes.

Neither stage is sized. S1 may need one milestone or three; that is `build-planning`'s call once S1's pipelines are approved, when it cuts S1 into milestone rows (`M1`, `M2`, …) under a milestone table of its own.

## Stage Skills and References (GridLoad, Extend Mode)

**State:** A GridLoad roadmap split differently: stage S1 Ingest & clean, cut into milestone M1. The project has two skills, `profile-report` and `significance-check`. `docs/references.md` indexes RF-01 (seasonal profile, `Milestones: S2`, assigned during intake while S2's row was being drafted) and RF-02, RF-03 (holiday calendar and boosting windows, `Milestones: —`).

```
$ python3 ../../scripts/dt.py status --skill idea-refine
…
references_unindexed: none
references_changed: none
references_missing: none
references_unassigned: RF-02, RF-03
```

Nothing is waiting for intake. **The idea** is the seasonality-and-baselines stage. The idea file's *Recommended direction* cites RF-01 as prior art ("the daily and weekly profile removal in RF-01, fitted per window"), never the path.

**Gate message (end):**

> On acceptance I'll add stage **S2: Seasonality & baselines** to the roadmap with `**Skills:** profile-report, significance-check`: profile-report for the seasonal decomposition and load profiles, significance-check for the "the profile is real" claims. Route those two? [yes / edit]. RF-02 and RF-03 (boosting) don't serve this stage, so they stay unassigned.

*(Turn ends.)* **User:** "Accepted, yes." Set the idea file to Accepted and add the stage row and section:

```markdown
## S2: Seasonality & baselines
**Outline:** Daily and weekly Fourier profile removed; seasonal-naive forecast and equal reserve split as baselines, scored on held-out weeks.
**Skills:** profile-report, significance-check
```

**Months later, S3 Features & boosting.** `references_unassigned` still lists RF-02 and RF-03. The gate adds "RF-02 (holiday calendar) and RF-03 (boosting windows) look like they serve S3. Assign them? [yes / edit]". On a yes, both entries' `**Milestones:** —` becomes `**Milestones:** S3`. The index keeps its Status: the user's yes at this gate is the confirmation.
