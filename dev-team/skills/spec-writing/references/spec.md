# The spec: template, writing rules, hygiene check

Read before writing or extending `docs/spec.md`, and again for the hygiene check at the Review Gate.

## Template

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
**Stage:** S2
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
- **QR-01** [Measurable non-functional requirement: speed, reliability, accessibility, privacy, security, cost, licence.]
  - [How it's checked.]

## Assumptions
- [Assumptions the user confirmed]

## Open questions
- [Unresolved items, each with who can answer it. Omit if none. A question about what an external source really returns is "answered by a probe during architecture".]

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
- **Every feature names one stage.** Its `**Stage:**` line holds only the ID of the roadmap stage that first builds it. `dt lint` fails a feature with no stage, or one naming no stage row.
- **Requirement IDs are permanent.** `CODE-NN`, numbered within the feature, never reused or renumbered.
- **Quality requirements only when measurable.** Leave out generic wishes ("should be secure"); keep checkable ones ("passwords are never shown in full"). Cost, licence, budget and run-time limits are `QR-` items, each with how it is measured ("data costs ≤ $50 a month"; "the full study runs in ≤ 1 hour", timed on the user's machine), never `DATA-` or feature requirements.
- **One decision, one home.** A limit, pass bar, count or schedule is stated in the one requirement that owns it. The Summary, Behavior, Assumptions, edge cases and other requirements name its ID ("within QR-02's limit") and never restate it. The spec owns the bar ("higher at a 5% level after correcting for the 6 comparisons"); which test and which correction is `architecture-design`'s, so no requirement names one (a t-test, Bonferroni, Holm). An assumption the spec turns into a requirement leaves Assumptions.
- **No tech stack, libraries, vendors, schemas, endpoints, or file structure, even when the user names them.** Write the behavior the name stands for. The name itself belongs to `architecture-design`, which reads it in `docs/requests.md`.
- **Describe the product as it is now, not how it got here.** Requirement text, scope lists and assumptions carry no change notes, provenance tags ("from the field-photo idea", "UR-03") or process notes ("numbers chosen for review"). History goes in one Changelog row per round, and in git; which requirement honours which request goes in `docs/requests.md` (`dt request trace`).
- **The user's words win over the brief's.** Where a `spec` request is more specific than the brief or idea file ("circular tank", "one predator"), the requirement says what the request says, or the user approves the change.

**Data and ML projects — extra rules:**

- **Specify the data, not the source.** `DATA-NN` requirements say what the data must contain and guarantee ("hourly readings for every meter in the service area, including decommissioned ones, since 2015"; "every record is stamped with the date it became known"). Which API, vendor, or dataset meets them is an architecture decision, made by checking candidates against these requirements. Name a source only when the brief makes it a fixed constraint (our own database, a required benchmark).
- **Write data guarantees as testable criteria.** Leakage, look-ahead, selection bias, and coverage gaps are requirements, not hopes: "Given a forecast issued at time T, when the model requests weather, then no value published after T is returned."
- **Model quality is a requirement with a baseline.** Acceptance criteria name the metric, the held-out data, the threshold, and the baseline to beat: "Given the most recent 6 months of plates (never trained on), when ranked, then reviewing the top 20% catches ≥ 90% of scientist-failed plates, and beats ranking by Z′ alone." Never "the model is accurate".
- **No model types or libraries.** "Gradient boosting" or "PyTorch" are architecture decisions; the spec says what the model must achieve.
- **Learning projects: "build it by hand, then compare with a library" is a valid requirement. Write it without the names.** "The hand-written CNN reaches ≥ 90% of the accuracy of an established reference implementation on the same dataset." "The logistic regression is written from basic array operations; a reference library is used only to check its output." The architecture picks the reference.

## Hygiene check

Run on everything above the Changelog before presenting a Draft.

- **The user's words.** `dt request --open --owner spec` is empty, or each one left is a change you ask the user about.

- **Stated twice.** For each number and pass bar in a requirement, search the rest of the spec. A repeat elsewhere becomes the ID. Where two wordings disagree (an assumption that the agent "may only tie" a baseline EVAL-04 says it beats), ask the user which holds and delete the other.

- **Implementation names.** Search for library, framework, vendor, dataset, file-format, database and model-type names, file and function names (a reference's included), including names the user, the brief or the idea file used. Rewrite each one as the behavior or guarantee it stands for: "within 10% of torchvision's ResNet-18" becomes "within 10% of an established reference implementation", and "NumPy only" becomes "written from basic array operations". The only exception is a source the brief makes a fixed constraint.
