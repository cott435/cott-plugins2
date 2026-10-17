# Extend

New spec IDs or components arrived. Read `steps.md` before changing a step table or the planned layout, and `template.md` for a new pipeline's format. Ends at the Review Gate in `../SKILL.md`.

Take `uncovered_ids` and `components_unowned` from `dt status`. For each ID: an existing step covers it (add it to Covers), an existing step changes its In → Out (edit that row; check the contract still matches, else route to `architecture-design` Revise), or a new workflow or step is needed. Confirm new workflows as `../SKILL.md` (Asking about workflows) says, showing beside the candidate list the existing pipelines they sit beside. New pipelines get new IDs and their own entry sketch; existing IDs, rows and step names don't change. Append new PL IDs to the `Used by:` lines of the contract symbols they call.

**Layout.** A `## Planned layout (pre-build — removed by spine task)` section lives only while some pipeline in the doc is unbuilt; `dt lint` flags `prebuild-left` once every pipeline is built. So:
- **A new, unbuilt pipeline:** add its modules to the planned layout. If the spine already removed it, write a new one holding only the new modules, marked against the existing tree from `dt layout <pkg>`.
- **Only new steps on built pipelines:** write no planned layout. Name each new module at the gate (owner → `<owner>/<module>.py`); `build-planning` puts it in the task's `Writes:`.

Status back to Draft, then the Review Gate, highlighting only what changed.
