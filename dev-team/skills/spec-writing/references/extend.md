# Extend mode: adding an idea to an existing spec

Read when `dt status` reports `mode: extend`: `docs/spec.md` exists and an accepted idea file (`ideas_ready`) is the input. Read the spec fully, then `references/spec.md`.

- A brief the idea edited must be `Accepted` too, like the idea itself.
- **No idea file** (the user just describes a feature): route to `idea-refine`, unless the change is small and fully clear; then confirm and add it, noting "no idea file" in the Changelog row.

The idea file is the main input. Its sections map onto the spec like this:

| Idea file section | Used for |
|---|---|
| How it fits → Serves | `Serves:` line of each new feature |
| How it fits → Touches | Which existing requirements to check, change, or extend |
| Recommended direction | Feature Behavior and the requirements |
| Not doing | Out of scope |
| What success looks like | Quality requirements, where measurable |
| Open questions | Questions to ask in Step 3 — resolve them, or carry them into the spec's Open questions |

## Steps

Run these for the idea only:

1. **Check for conflicts first.** Start with the IDs under *Touches*, then search the rest of the spec for anything else the idea contradicts. List conflicts for the user before writing — "Shared editing changes **EDIT-03** (only the owner can edit). Proposed: owner *or invited editors* can edit."
2. **Map the idea to features** and show the goal → feature mapping before writing.
3. **Surface assumptions, then clarify** (SKILL.md's Asking section).
4. **Write the change** following `references/spec.md` and the rules below.
5. **Set the spec Status back to Draft** and run the Review Gate (SKILL.md, plus the gate steps below), highlighting the changed IDs so the user reviews only what's new.

## Writing rules

1. **Keep IDs stable, keep the text current.** IDs are never renumbered or reused. Old text does not stay in the spec once it stops being true; git keeps it.
   - New feature → new `### Feature (CODE)` section with a new code and IDs starting at `-01`.
   - New behavior in an existing feature → next unused number in that feature (if `SAVE-04` is the highest, add `SAVE-05`, even if `SAVE-02` was removed). `dt status` reports it under `prefixes`.
   - **Widen, don't bolt on.** If an existing requirement already covers this concern for an earlier part of the project, rewrite it to cover the new part too, instead of adding a near-duplicate. A training-time limit written for the first game becomes a limit for every game. A summary that says "the first milestone" is rewritten.
   - Changed requirement → rewrite it in place and keep its ID. Put no marker on it. Instead, list it as `(changed)` in this round's Changelog row, with the reason in the row's Change text. `architecture-design` reads those Changelog marks (through `dt status`) to find what the architecture must revisit, so list every changed ID.
   - Removed requirement → collapse it to one struck line and delete its criteria and edge cases: `- **CODE-03** ~~[short name]~~ *Removed YYYY-MM-DD: [reason, or "replaced by CODE-07"].*` Never delete the ID line; the ID stays retired.
2. **Link back to the idea.** Add `**Source:** [ideas/<slug>.md](ideas/<slug>.md)` under the `Serves:` line of each new feature section, so readers can find the full why.
3. **Update everything it touches, and consolidate.** Summary (rewritten for the whole spec, not appended to), Users, Serves lines. Scope stays one deduplicated list per side: merge new out-of-scope items into it, and drop or narrow anything the new features bring into scope (the gate's *Out of scope* step). Remove assumptions and open questions that are answered or no longer apply.
4. **Add one Changelog row**, one line: the idea file as the source, a short description of the change, and the IDs as ranges in up to three `;`-separated groups: added, then changed, then removed (`TANK-01–TANK-12; QR-03, CORE-04 (changed); SNAKE-04 (removed)`). A `(changed)` or `(removed)` mark covers every ID in its group.

## Gate steps

Run the hygiene check on the whole spec, not just the new section, and add:

- **Out of scope.** Read every out-of-scope line against the features this round added. Drop a line the new features bring into scope. Narrow a line that is now only partly true to the part still excluded, and name the stage it applies to. Once a neural-network stage exists, "deep learning" is no longer out of scope. Once a trading stage uses return forecasts, "no return forecasts — the portfolio stage is variance-only" becomes "the variance-only portfolios use no return forecasts". Then merge duplicates.
- **Leftovers.** The Summary describes the whole spec as it now stands. No requirement is still worded for one stage when it now covers several. Removed requirements are one line each. No `(changed …)` marker or other change note appears above the Changelog.

## On approval: close and freeze the idea

A `Specced` idea is the record of why the feature was added, as it stood that day. The spec is the current description.

1. Set its Status to `Specced` and add two lines under the header: `**Spec:** CODE-01–CODE-04, EDIT-03 (changed)` and the banner `> Record of why, frozen when specced. The spec is current: [spec.md](../spec.md)`.
2. Delete the open questions the spec answered. If none are left, the section becomes one line: `Resolved in the spec.`
3. Delete wording that only served the review: notes to the user ("my proposed limit, for you to check") and instructions to this skill ("this line must be removed from the spec").

After that, don't edit the file again, even when a later round changes what it describes, such as a narrowed holdout or a merged stage. That change goes in the spec, and the later idea file names this one under *Touches*.
