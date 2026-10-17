# Revise

Read when `dt status --skill architecture-design` reports Revise: a technical change with no spec change, or probe results to fold in. It ends at the Review Gate in `../SKILL.md`, following `writing-rules.md`. Example: `examples-revise.md`.

1. Write a new decision whose Context explains what was learned ("the simulator is 40× too slow for QR-02 at 1M steps"). Then supersede the old decision if the new one reverses it, or revise it in place if the new one changes only part of it (`decisions.md`).
2. Update every section and contract the change touches (tech stack, components, Overview; contracts per `contracts.md`), and run the Review Gate.
3. If a contract changes, list its consumers (its **Used by**): their pipelines and tasks need revisiting. Record the pipelines' share for `pipeline-design`: `dt route pipeline-design "<change> (PL-02, PL-03)" --from architecture-design`. A frozen interface's type, samples and fake change with it, in a new interface task Replan adds (a `contract-change` edge).

## Probe results

For each probe in `probes_answered` or `probes_failed`, read its entry with `dt section PB-NN` (its Verdict, each check's Result, its Caveats), never `probes/`. Then, for each decision it informs:

| Result | Change |
|---|---|
| Every check passed | Cite the finding in the decision's Context ("PB-01, 2026-10-20: 6 of 6 institutions link; history 13–24 months") and delete its Risks line. It becomes Accepted at approval |
| Waived | Cite the waiver and the user's reason in Context; keep the Risks line. It becomes Accepted at approval |
| A check failed, and another option still meets the requirements | Steps 1–3: revise the decision in place, or supersede it |
| A check failed, and no affordable option meets a requirement | Name the requirement and the finding at the gate. Only the user can change it, through `spec-writing` |
| Observed fields differ from a contract type | The type's fields and invariants follow the evidence ("`merchant_entity_id` is None on 38% of rows"); its **Cases** may name the probe's samples (`contracts.md`) |
