# Writing rules

Read before writing or changing any architecture doc, every round. Decision rules are in `decisions.md`.

- **`PL-NN` IDs are permanent.** A retired system pipeline collapses to `- ~~PL-NN: title~~ Retired YYYY-MM-DD: reason`.
- **Describe the design as it is now, not how it got here.** No process notes ("no code was built before this change"), no struck-through risks, no per-stage blocks of risks or notes. Git keeps the rest.
- **The Changelog has one row per round, one line long.** IDs are the new decisions, as ranges (`AD-12–AD-15`). Don't repeat the spec row's ID list. The exception is a spec row with no source file: copy its IDs with their marks (`AD-16; QR-03 (changed)`). Source names the source files of the spec rows the round absorbs, as `spec_rows_pending` lists them: usually one idea file, sometimes `brief.md`. Use `spec.md` when those rows have none, as in a first architecture written from the initial spec alone. `dt status` matches this Source (or, for a row with no source file, those IDs) against the spec's Changelog to decide which spec changes the design has absorbed. A row that doesn't cite them leaves `changed_since` stuck on those requirements.
- **Risks and open questions is one consolidated list.** Each round merges into it: add new risks, rewrite ones that changed, and delete ones that are resolved. Record a resolution in a decision or the Changelog, not as a struck-through risk.
- **Size to the project.** A proof of concept with three modules doesn't need a Cross-cutting section longer than its Components table. Omit sections that would only say "N/A". Pin versions for the language and key libraries, not every transitive dependency.
- **No requirements restated.** Reference spec IDs; don't copy their text.
