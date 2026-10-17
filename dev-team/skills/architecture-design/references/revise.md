# Revise

Read when `dt status --skill architecture-design` reports Revise: a technical change with no spec change. It ends at the Review Gate in `../SKILL.md`, following `writing-rules.md`. Example: `examples-revise.md`.

1. Write a new decision whose Context explains what was learned ("the simulator is 40× too slow for QR-02 at 1M steps"). Then supersede the old decision if the new one reverses it, or revise it in place if the new one changes only part of it (`decisions.md`).
2. Update every section and contract the change touches (tech stack, components, Overview; contracts per `contracts.md`), and run the Review Gate.
3. If a contract changes, list its consumers (its **Used by**): their pipelines and tasks need revisiting. A frozen interface's type, samples and fake change with it, in a new interface task Replan adds (a `contract-change` edge).
