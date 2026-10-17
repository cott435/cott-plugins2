---
description: Plan a project skill by skill, each skill run in its own session in this folder, from idea to build setup
argument-hint: "<what you want to build or add>"
---

# Plan

You drive the planning; the skills do it. Each skill run gets its own child session, so every context stays small,
and the user answers questions and approves Drafts inside that child, in their own words. You never approve, relay
an approval, edit a planning doc or run a skill's work yourself. What runs next is `dt next`'s call, not yours.

`dt` is the `dt:` path in the dev-team summary at session start, else `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dt.py"`,
run from the project root.

## Each step

1. Run `dt next --json`: `{skill, mode, reason, waiting_on_user}`, plus `packages`.
2. `skill` is null (`done`): say planning is current and what `reason` suggests (build, or a new idea for
   idea-refine). Stop.
3. The current child's skill, in a `gate` or still working: it is waiting on the user. Say so in one line with a
   link to it, and stop until it ends another turn.
4. Otherwise start one child for it with `mcp__ccd_session__start_session`: `initiation` "user_asked" (the user
   asked for this by running `/dev-team:plan`), `context` "fresh", `use_worktree` false, `wake_when_done` true, a
   title naming the skill and mode, `prompt` starting `/dev-team:<skill>`, then the user's request (below) for the
   first child, and for later ones `dt next`'s `reason`. In `background` say this is one run
   of a dev-team planning sequence driven by `/dev-team:plan`: run the skill to its gate and stop there; the
   user approves in that session. One child at a time: never start one while another is working.
5. Tell the user which child is waiting on them and why (`reason`), with its link.

When a child ends its turn you are continued: go back to step 1. The same skill after its gate was approved
(`mode` no longer `gate`) gets a new child. A change a skill routed upstream comes back from `dt next` as the
owner's Revise or Extend; start it like any other. Test planning is optional: once the user declines it, pass
`--skip test-planning` to every `dt next`.

## Without session tools

If `mcp__ccd_session__start_session` isn't available (the CLI), say which skill `dt next` names and why, then run
that skill here (`/dev-team:<skill>`), the first with the user's request. After its gate, run `dt next` again.

## The user's request

$ARGUMENTS
