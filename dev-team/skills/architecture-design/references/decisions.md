# Decisions

Read when making a technical decision, or when one changes or retires an Accepted decision.

## Making a decision

For each significant open choice (language, libraries, storage, deployment, data sources, model approach): 2-3 real options checked against the requirements that constrain them (`DATA-`; model criteria and baseline), and a recommendation. Ask about expensive-to-reverse ones. Record each as `AD-NN`, citing an informing reference by `RF-NN`, never its path. Small reversible choices go only in the tech stack table. A repo with its own ADRs keeps that convention.

## When it touches older decisions

Find every Accepted decision a new one touches: search the doc for the components, data, counts and names it changes.

- It reverses an old choice → supersede the old decision, which collapses to its superseded line.
- It changes part of an old choice → revise the old decision in place (*Accepted decisions stay true*). Examples: a third holdout added to a decision that set up two, or a new caller of an interface that a decision said only one study uses.
- It only adds a member to a set a shared decision governs (another claim family, another run folder) → add the member where the set is listed and cite the shared decision. Don't revise it (*Shared decisions state a rule*).

## Rules

- **Decision IDs are permanent; superseded decisions shrink.** `AD-NN` IDs are never reused or renumbered, and the heading is never deleted. A reversed decision collapses to its heading with the title struck, plus one status line: `**Status:** Superseded by AD-NN · date — reason`. Delete its Context, Decision, Alternatives and Consequences. The new decision's Context says what the old one chose and why that no longer holds. Then update every section that cited the old decision (tech stack, contracts, code comments, layout, risks) so that only the superseded line, the new decision and the Changelog mention it.
- **Accepted decisions stay true.** When a new decision changes only part of an Accepted one, revise the old one instead of superseding it. Rewrite the sentences that are no longer true, in its Context as well as its Decision and Consequences, and point to the new decision for the part it now owns. "Two holdouts, one per study" becomes "one holdout per study; AD-26 sets the ranges". The old decision stays Accepted. Supersede only when its choice is reversed as a whole. Readers take an Accepted decision as current, so a stale count in one is a defect.
- **Shared decisions state a rule, not a roster.** A decision that later stages build on (where claims go, which modules may import a library, where runs are stored) is worded to stay true as stages join: "every module that makes a significance claim writes a `Claim`", not "`eda` and `backtest` write claims". Its Context cites the requirements that set the rule, not each one that uses it. The members and their per-stage details (claim families, importers, run folders, time budgets) are listed once, where they live: a component's row and Covers, a contract section, the storage layout, or that stage's own decision. A new stage adds its members there and cites the shared decision. Revise the shared decision only when its rule changes. If one already lists members, move them out the next time a round touches it.
