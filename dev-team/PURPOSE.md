# Purpose: `dev-team`

## Goal

A project goes from a raw idea to a build plan that an agent can follow without guessing:
brief, spec, architecture, pipelines, test plan, milestone plan and quality bar, each small,
approved by the user and checked by a tool rather than by memory. Builders get small,
correct inputs, so what they build matches what was agreed.

## Who uses it, and when

A developer starting a Python project, adding a stage to one, or finishing a milestone. They
run a planning skill, review the Draft it writes, and approve it in their own words before
the next skill starts. The `dt` tool and the hooks act on their own.

## What it does

- Turns an idea into an accepted brief and roadmap stages.
- Writes the spec, the architecture with its decisions and contracts, and the pipelines,
  each stopping for the user's approval.
- Plans golden test cases whose expected outputs come from outside the agent.
- Cuts each designed stage into milestones and plans the next one task by task, contract
  first.
- Sets the project's quality bar and its enforcement.
- Keeps every document addressable by ID through `dt`, and guards oracles and archives.

## Non-goals

- Writing or running the project's code: building is `/build`'s job.
- Planning more than the next milestone in task detail.
- Projects in languages other than Python.

## Done well means

Every requirement has a home in the design, every stage reaches a milestone, and a builder's
whole context is one `dt context` packet. Incremental and up-front planning end at the same
bar.
