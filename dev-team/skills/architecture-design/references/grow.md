# Grow: single package to multi-package

Read when `dt status --skill architecture-design` reports Grow (a trigger in `shape.md` fires) or the user wants a split. It ends at the Review Gate in `../SKILL.md`, following `writing-rules.md`. Example: `examples-grow.md`; the multi-package result looks like `examples-new-multi.md`.

1. Write a decision (`AD-NN`, scope `system`, as `decisions.md` says) explaining why now: the trigger, and the new boundary, owner, runtime, or release need.
2. Propose the package list and dependency rules. Component ids become package ids where possible, so Covers entries and contract IDs (`profile.fit_seasonality`) carry over unchanged.
3. Move each package's detail from `docs/architecture.md` into `docs/packages/<pkg>/architecture.md`, and each `## <component>` group of the old contract into `docs/packages/<pkg>/contract.md` (`contracts.md`). Rewrite the root as the system map (the multi-package templates in `templates.md`).
4. Add System pipelines for the flows that now cross packages, each with a new ID from `dt next-id PL`. A package pipeline whose flow now crosses keeps its own `PL-NN` ID: it stays the segment of the package that owns its entry, and `pipeline-design` Grow marks it `**Part of:**` the new system pipeline. Name that source pipeline at the gate. Never give a system pipeline an ID a package pipeline already holds.
5. Change the header to `**Shape:** Multi-package`, add a Changelog row, and run the Review Gate. After approval, point to `pipeline-design` (Grow mode).
