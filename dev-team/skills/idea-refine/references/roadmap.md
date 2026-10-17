# Roadmap stages

Read when proposing stages at the Review Gate and when adding them on acceptance; the mode file says which stages to propose. An example: `examples-data.md`.

Stages live in `docs/roadmap.md`. A stage is an outcome the user agreed: what they can do when it's done, such as "Data + stats" or "See my spending". It is coarse and unsized. **Don't size it:** no task estimates, no pipeline counts, no splitting a stage because it looks big. Two stages differ by outcome, never by size. Once a stage's pipelines are approved, `build-planning` cuts it into build-sized milestones (`M<n>`), each a vertical slice it can run end to end, and owns those rows.

**Add stages only when the user accepts** (Phase 4). Each stage takes its ID from `dt next-id S` (`dt` as defined in `../SKILL.md`), a short name, and its Source. Leave the Status* cell empty, then run `dt roadmap`, which fills it. Under the tables, add a `## S<n>: <Name>` section with one plain-English `**Outline:**` line (what the user can do when the stage is done) and one `**Skills:**` line.

**Stage skills and references.** The `**Skills:**` line is the one record of which skills serve a stage; later skills start from it and `build-planning` checks each one lands on a milestone and then a task. Propose the skills whose descriptions fit the stage (project `.claude/skills/*/SKILL.md` and the installed skills in your context), and ask once: "Route profile-report and significance-check to S2? [yes / edit]". None fit → `**Skills:** —`. Also offer each `references_unassigned` entry that serves the stage ("RF-02 and RF-03 (boosting) → S3? [yes / edit]"). On acceptance, write the line and set `**Milestones:**` on each RF entry the user assigned to the stage ID (`—` becomes `S3`; otherwise append). Those two fields are all you write in the roadmap sections and `docs/references.md`.

If `docs/roadmap.md` doesn't exist, create it:

```markdown
# [Project Name] — Roadmap

**Last updated:** YYYY-MM-DD

| Stage | Name | Source | Status* |
|---|---|---|---|
| S1 | [Name] | brief | |

*Written by `dt roadmap` from doc statuses and todo checkboxes; never hand-edited.

## S1: [Name]
**Outline:** [What the user can do when this stage is done, in one sentence.]
**Skills:** [skill names routed to this stage, comma-separated, or —]
```

Add stages; never renumber, reorder or edit existing ones. A roadmap from before stages has only a milestone table (with a Source column): add the stage table above it for the first new stage, and leave the old rows as they are.
