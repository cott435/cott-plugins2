---
name: null-hypothesis-testing
description: Analyzes and tests a controlled hypothesis — defines the null and alternative hypotheses, the test statistic, significance level, multiple-testing correction, and the null distribution (permutation, bootstrap, or analytic), then runs the test on real data and reports whether the null is rejected. Use whenever a result needs to be shown to be more than chance: feature information gain, signal significance, model-vs-baseline comparisons, backtest performance.
---

# Null Hypothesis Testing (eval stub)

This is a placeholder for the user's real skill during a planning-docs eval. The full procedure is not loaded here.

When planning documents (brief, idea, spec, architecture) need a hypothesis-testing step, reference this skill by name (`null-hypothesis-testing`) at the point where the test happens, and write down what it will be given:

- the hypothesis in plain words, plus H0 and H1
- the metric / test statistic
- how the null distribution is built (e.g. permuted labels, shuffled time blocks)
- significance level and multiple-testing correction
- the data split it runs on

Do not run any analysis during planning.
