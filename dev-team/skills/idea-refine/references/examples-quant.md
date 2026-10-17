# Example: a quant research package

A data-dependent New project with its first roadmap stages, then a later idea routing stage skills and references.

## Quant Research Package (New Project, Data-Dependent)

**User invokes:** `/ideate a Python package for researching and backtesting equity strategies — I keep rewriting the same notebook code`

### Phase 1: Understand & Expand

**Skill response:**

> **How might we** get from a strategy idea to a backtest we can actually trust, without rebuilding the data and backtest plumbing every time?

Before expanding:

1. **Who uses it?** Just you, or a small team that needs to compare each other's results?
2. **What markets and frequency?** US equities? Daily bars, or intraday?
3. **What data do you have today, and what's the budget?** Free sources, an existing subscription, or room to pay?
4. **Research only, or does this end in live trading?**

**User responds:** "Me and two collaborators. US equities, daily is fine — we rebalance weekly to monthly. We've been using a free end-of-day price API. Budget maybe $100/month. Research only for now."

**Skill continues:**

"Rewriting notebook code" is the symptom. The expensive problem is **not trusting the results**. One-off notebooks are where look-ahead bias and survivorship bias creep in, and a strategy that only works because of a bug is worse than no strategy.

Here are 5 variations:

1. **Backtest Engine First:** A clean event loop with costs and slippage. Strategies plug in. Data is the user's problem.
2. **Data Layer First (Inversion):** Start from trustworthy data, not the engine: a local, point-in-time store with one interface. Any simple backtester is fine once the data is right.
3. **Simplification — Vectorized Only:** No event loop. Strategies are functions from a date-by-stock signal table to weights. Fast and easy for weekly/monthly rebalancing.
4. **Combination — Research Notebook Kit:** Keep notebooks, but ship the pieces as a library: data loader, backtest function, standard tear-sheet.
5. **10x — Full Platform:** Scheduled data pulls, experiment tracking, and a strategy registry. Clearly too much for three people.

### Phase 2: Evaluate & Converge

**Data feasibility decides this one.** Price data is easy to get. **Historical index membership including delisted companies** is not, and without it every backtest quietly drops the stocks that went bust, so results look better than reality. That's the dealbreaker to check first: can it be had within $100/month?

**Direction (2 + 3): Trustworthy data layer + vectorized backtests.** It attacks the real problem (trust). It fits daily/monthly strategies. Hiding the data source behind one interface keeps the vendor decision open.

**Direction (1): Event-driven engine.** More realistic order modeling, but none of your strategies need it yet. Pushing back: this is where these projects usually sink months.

The user picks (2 + 3).

### Phase 3: Write the Brief

```markdown
# Factor Lab

**Status:** Draft · **Last updated:** 2026-10-14

## The problem
Testing a strategy idea takes about a week of one-off notebook code: pulling data, cleaning it, and writing a backtest from scratch. Results can't be compared across ideas. Worse, subtle mistakes, like using information that wasn't available at the time, make strategies look better than they are.

## Who it's for
A small research team (1-3 people) testing US stock strategies that trade weekly to monthly.

## Goals
1. Go from a strategy idea to a backtest report in under a day.
2. Trust the results: no peeking at future data, and no silently dropping companies that failed.
3. Compare any two strategies side by side on the same data and assumptions.
4. Change data providers without rewriting strategies.

## Constraints
- Python, running on a laptop.
- Daily US stock data only.
- Data budget: free sources to start, under $100/month at most.

## What success looks like
- Three of our past notebook strategies re-run in the package, with matching results or explained differences.
- A new strategy takes under a day from idea to report.

## What we're betting on
- Daily data is enough for the strategies we care about.
- Affordable data is good enough for research (not for live trading).
- We can get history that includes companies that were delisted, within budget. If not, Goal 2 needs rethinking.

## Not doing
- Live trading or placing orders — research only.
- Intraday data, options, futures, or crypto.
- An event-driven engine — weekly/monthly strategies don't need one yet.
- A user interface — notebooks and a command line are enough.

## Open questions
- Which data provider? (Decided in the architecture, against the data requirements in the spec.)
```

*Notice what's **not** in the brief: a data API. The brief records data **needs** (daily, US, includes delisted companies, under budget) as constraints and bets. `spec-writing` turns them into data requirements, and the provider is chosen in the architecture against those requirements.*

**On acceptance.** In Phase 2 the user agreed to build in two stages: the trustworthy data layer first, then vectorized backtests. The stages are not goals: Goals 1-4 hold whichever stage is being built. The skill sets the brief to Accepted, creates `docs/roadmap.md` with a stage row per stage (IDs from `dt next-id S`), and runs `dt roadmap` to fill Status:

```markdown
| Stage | Name | Source | Status* |
|---|---|---|---|
| S1 | Point-in-time data | brief | Idea |
| S2 | Vectorized backtests | brief | Idea |

## S1: Point-in-time data
**Outline:** Load daily US prices as they were known on any date, including companies that later failed.
**Skills:** —

## S2: Vectorized backtests
**Outline:** Turn a date-by-stock signal table into a backtest report with costs, comparable across strategies.
**Skills:** —
```

The project has no skills installed yet, so the gate asked "No installed skill fits either stage, so both get `Skills: —`. OK?" and the user said yes.

Neither stage is sized. S1 may need one milestone or three; that is `build-planning`'s call once S1's pipelines are approved, when it cuts S1 into milestone rows (`M1`, `M2`, …) under a milestone table of its own.

## Stage Skills and References (Quant, Extend Mode)

**State:** Quant Lab has stage S1 Data + stats, cut into milestone M1. The project has two skills, `data-analysis` and `null-hypothesis-testing`. `docs/references.md` indexes RF-01 (market decomposition, `Milestones: S2`, assigned during intake while S2's row was being drafted) and RF-02, RF-03 (TFT targets and dataset, `Milestones: —`).

```
$ python3 ../../scripts/dt.py status --skill idea-refine
…
references_unindexed: none
references_changed: none
references_missing: none
references_unassigned: RF-02, RF-03
```

Nothing is waiting for intake. **The idea** is the structure-and-portfolios stage. The idea file's *Recommended direction* cites RF-01 as prior art ("the market-mode removal in RF-01, fitted per window"), never the path.

**Gate message (end):**

> On acceptance I'll add stage **S2: Structure + classical portfolios** to the roadmap with `**Skills:** data-analysis, null-hypothesis-testing`: data-analysis for the covariance and PCA work, null-hypothesis-testing for the "the structure is real" claims. Route those two? [yes / edit]. RF-02 and RF-03 (TFT) don't serve this stage, so they stay unassigned.

*(Turn ends.)* **User:** "Accepted, yes." Set the idea file to Accepted and add the stage row and section:

```markdown
## S2: Structure + classical portfolios
**Outline:** PCA and MP-cleaned covariance feed min-var, risk parity and HRP, compared out of sample.
**Skills:** data-analysis, null-hypothesis-testing
```

**Months later, S4 Forecasting & agents.** `references_unassigned` still lists RF-02 and RF-03. The gate adds "RF-02 (TFT targets) and RF-03 (TFT dataset) look like they serve S4. Assign them? [yes / edit]". On a yes, both entries' `**Milestones:** —` becomes `**Milestones:** S4`. The index keeps its Status: the user's yes at this gate is the confirmation.
