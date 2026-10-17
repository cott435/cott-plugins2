# Purpose: `dev-team`

## Goal

A project goes from raw idea to working code: brief, spec, architecture, pipelines, test
plan, milestone plan and quality bar, each small, approved by the user and checked
by a tool; then each milestone is built by parallel agents held to the bar, so
what they build matches what was agreed.

## Who uses it, and when

A developer runs `/dev-team:plan` (one session per skill run) or the skills themselves,
and approves each planning Draft in their own words before the next skill starts, then
each milestone's build and merge. Between those the build runs unattended, stopping when
stuck. `dt` and the hooks act alone.

## What it does

- Turns an idea into an accepted brief and roadmap stages.
- Writes the spec, architecture (decisions, contracts, probes) and pipelines.
- Plans golden test cases whose expected outputs come from outside the agent.
- Cuts stages into milestones and plans the next one task by task, contract first.
- Sets and enforces the quality bar.
- Keeps every document addressable by ID through `dt`, and guards oracles and archives.
- Builds milestones: testers blind to code, implementers confined to their files,
  reviewers that land nothing. A task lands only when its checks pass.

## Non-goals

- Code outside a planned task: that is `/build`'s job. Probes (`probes/`) only check what an
  external API returns: never imported, and you run any needing your credentials.
- Planning more than the next milestone in task detail.
- Languages other than Python.

## Done well means

Every requirement has a home in the design, every stage reaches a milestone, and a builder's
whole context is one `dt context` packet. Incremental and up-front planning end at the same
bar. Golden cases pass with no oracle or intent test edited.
