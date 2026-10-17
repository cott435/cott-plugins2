# Extend mode: adding an idea to an existing spec

Read when `docs/spec.md` exists and an accepted idea file is the input.

The idea file is the main input. Its sections map onto the spec like this:

| Idea file section | Used for |
|---|---|
| How it fits → Serves | `Serves:` line of each new feature |
| How it fits → Touches | Which existing requirements to check, change, or extend |
| Recommended direction | Feature Behavior and the requirements |
| Not doing | Out of scope |
| What success looks like | Quality requirements, where measurable |
| Open questions | Questions to ask in Step 3 — resolve them, or carry them into the spec's Open questions |

Run Steps 1-5 for the idea only, with these rules:

1. **Check for conflicts first.** Start with the IDs under *Touches*, then search the rest of the spec for anything else the idea contradicts. List conflicts for the user before writing — "Shared editing changes **EDIT-03** (only the owner can edit). Proposed: owner *or invited editors* can edit."
2. **Keep IDs stable, keep the text current.** IDs are never renumbered or reused. Old text does not stay in the spec once it stops being true; git keeps it.
   - New feature → new `### Feature (CODE)` section with a new code and IDs starting at `-01`.
   - New behavior in an existing feature → next unused number in that feature (if `SAVE-04` is the highest, add `SAVE-05`, even if `SAVE-02` was removed). `dt status` reports it under `prefixes`.
   - **Widen, don't bolt on.** If an existing requirement already covers this concern for an earlier part of the project, rewrite it to cover the new part too, instead of adding a near-duplicate. A training-time limit written for the first game becomes a limit for every game. A summary that says "the first milestone" is rewritten.
   - Changed requirement → rewrite it in place and keep its ID. Put no marker on it. Instead, list it as `(changed)` in this round's Changelog row, with the reason in the row's Change text. `architecture-design` reads those Changelog marks (through `dt status`) to find what the architecture must revisit, so list every changed ID.
   - Removed requirement → collapse it to one struck line and delete its criteria and edge cases: `- **CODE-03** ~~[short name]~~ *Removed YYYY-MM-DD: [reason, or "replaced by CODE-07"].*` Never delete the ID line; the ID stays retired.
3. **Link back to the idea.** Add `**Source:** [ideas/<slug>.md](ideas/<slug>.md)` under the `Serves:` line of each new feature section, so readers can find the full why.
4. **Update everything it touches, and consolidate.** Summary (rewritten for the whole spec, not appended to), Users, Serves lines. Scope stays one deduplicated list per side: merge new out-of-scope items into it, and drop or narrow anything the new features bring into scope (the hygiene check's *Out of scope* item). Remove assumptions and open questions that are answered or no longer apply.
5. **Add one Changelog row**, one line: the idea file as the source, a short description of the change, and the IDs as ranges in up to three `;`-separated groups: added, then changed, then removed (`TANK-01–TANK-12; QR-03, CORE-04 (changed); SNAKE-04 (removed)`). A `(changed)` or `(removed)` mark covers every ID in its group.
6. **Set the spec Status back to Draft** and run the Review Gate, highlighting the changed IDs so the user reviews only what's new.

**After the spec is approved,** close the loop on the idea file, then freeze it. A `Specced` idea is the record of why the feature was added, as it stood that day. The spec is the current description.

1. Set its Status to `Specced` and add two lines under the header: `**Spec:** CODE-01–CODE-04, EDIT-03 (changed)` and the banner `> Record of why, frozen when specced. The spec is current: [spec.md](../spec.md)`.
2. Delete the open questions the spec answered. If none are left, the section becomes one line: `Resolved in the spec.`
3. Delete wording that only served the review: notes to the user ("my proposed limit, for you to check") and instructions to this skill ("this line must be removed from the spec").

After that, don't edit the file again, even when a later round changes what it describes, such as a narrowed holdout or a merged stage. That change goes in the spec, and the later idea file names this one under *Touches*.
