# Example: an ML feature in an existing product

Extend mode for an ML idea: the Data section and a baseline.

## ML Feature in an Existing Product (Extend Mode)

**User invokes:** `/ideate use ML to flag bad assay plates automatically in our lab results app`

The app already has `docs/brief.md` (Goal 2: *Bad data is caught before it reaches analysis*) and `docs/spec.md`, so this is **extend mode**. The skill reads both, plus the `qc` module in the codebase.

### Phase 1: Understand & Expand

> **How might we** catch failed plates before they reach analysis, without scientists reviewing every plate by hand?

Questions:

1. **How are plates checked today, and how long does it take?**
2. **What history exists?** How many plates, and is there a record of which ones were failed and why?
3. **What's worse: a bad plate getting through, or a good plate being re-run?**

**User responds:** "Scientists eyeball every plate — about 6 hours a week. We have 3 years of plate reads, roughly 40,000 plates, and about 2% were marked failed in the app. Missing a bad plate is much worse; a re-run costs a day."

**Skill continues:**

Before any ML: assay QC already has a standard rule, the **Z′-factor** (plates under 0.5 are suspect). Your `qc` module computes it but nobody acts on it. That's the baseline any model has to beat. If the rule alone catches most failures, you may not need ML at all.

Variations:

1. **Simplification — Just Use the Rule:** Auto-flag plates with Z′ < 0.5 and stop there. Zero ML.
2. **Ranked Review Queue:** A model scores every plate. Scientists review the riskiest first and stop when the scores get low. Humans still decide.
3. **Inversion — Auto-Pass the Obvious:** Instead of finding bad plates, confidently clear the clearly-good ones, and scientists review the rest.
4. **Anomaly Detection:** No labels needed. Flag plates that look unlike typical ones. Useful if past "failed" labels turn out to be unreliable.
5. **Expert Lens — Layout Patterns:** Many failures show up as spatial patterns (edge effects, a dead column). Features built from plate layout may beat a generic model.

### Phase 2: Evaluate & Converge (summary)

**Data check:** 40,000 plates with 800 failures is enough to try a supervised model, *if* the labels are consistent. That's the biggest bet. Different scientists may fail plates for different reasons. **Baseline:** the Z′ rule. **Cost asymmetry:** missing a bad plate is far worse, so measure recall at a fixed review budget, not accuracy (98% accuracy is free by passing everything).

The user picks **2 (ranked queue), with 1 as the baseline it must beat**. **Fit check:** it serves existing Goal 2 and the same users, so **the brief does not change.**

### Phase 3: Write the Idea File

`docs/ideas/plate-qc-ranking.md`:

```markdown
# Idea: Plate QC Ranking

**Status:** Draft · **Last updated:** 2026-10-14 · **Brief:** [../brief.md](../brief.md)

## In one sentence
This ranks every new assay plate by how likely it is to fail QC, so scientists review the riskiest plates first instead of checking all of them.

## The problem
Scientists check every plate by eye, about 6 hours a week. Failures are rare (about 2%) but costly: a bad plate that slips through corrupts downstream analysis. A good plate failed by mistake costs a day to re-run. The app already computes a standard quality score (Z′) but nothing acts on it.

## Who it's for
Lab scientists doing plate QC, during their weekly review.

## How it fits
- **Serves:** Goal 2 (bad data caught before analysis)
- **Touches:** QC-01 (Z′ is calculated per plate), QC-03 (scientist marks pass/fail)
- **Brief changes:** None
- **Stage:** New S3 (roadmap stage on acceptance)

## Recommended direction
Each new plate gets a risk score from a model trained on three years of past pass/fail decisions. The review screen sorts plates riskiest first. Scientists still make every pass/fail call; the model only sets the order.

The Z′ rule is the baseline. If the model doesn't clearly beat "sort by Z′", we ship the rule alone and stop.

## Data
- About 40,000 plates over 3 years, with raw reads, Z′, and the scientist's pass/fail decision (about 800 failures).
- All in our own database. No outside data needed.
- Evaluate on the most recent 6 months, never trained on, to mimic real use.

## Alternatives considered
- Rule only (Z′ < 0.5) — kept as the baseline, and the fallback if the model doesn't beat it.
- Anomaly detection — only if past labels turn out to be unreliable.
- Auto-passing obvious plates — revisit once the ranking has earned trust.

## What success looks like
- Reviewing the top 20% of plates catches at least 90% of the plates scientists would fail.
- Clearly better than sorting by Z′ alone on the same 6 months.
- Weekly review time drops from about 6 hours to under 2.

## What we're betting on
- Past pass/fail decisions are consistent enough to learn from.
- New plates look like past plates (same instruments and assays).

## Not doing
- Automatically failing or passing plates — a scientist always decides.
- Image-based models of the plate.
- Plates from other sites or instruments.

## Open questions
- How often do two scientists agree on the same plate? Measure before training.
- How often should the model be retrained, and who signs off?
```

**Skill then says:** "The idea is at `docs/ideas/plate-qc-ranking.md`. The brief is unchanged: this serves Goal 2. The biggest risk is label consistency. I'd measure scientist agreement on ~100 plates before anyone trains anything. Accept it or tell me what to change." *(Turn ends.)*

*An idea file for an ML feature adds a **Data** section. It names the data, where it lives, and how it will be evaluated. It still says nothing about model type or libraries; those are decided in the architecture.*
