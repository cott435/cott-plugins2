# Revise: a probe changes

`probes_stale` lists a probe whose code no longer matches the `script_hash` its results were made with, or the user changes a check, the Spends or the steps. Use the shape in `entry.md` and the rules in `safety.md`.

| Trigger | Do |
|---|---|
| Code changed after a run (`probes_stale`) | Say what changed (`git diff probes/PB-NN-*/`). If the change was intended, `dt probes --stamp PB-NN`, clear the Result cells the change affects, and ask the user to re-run those checks. If it wasn't, ask before restoring the code with `git checkout` |
| The user changes a check, a threshold or a runner | Edit the row and the function behind it; the Pass still cites its requirement. A check moved to `agent` must meet `safety.md`'s agent rule and move into `public.py` |
| A new unknown turns up (from a Record, or mid-build) | Add a row, `C<next>`, and its function. Never renumber or reuse a check ID: a dropped check is struck through in its row with the reason |
| The decision it informs changed (superseded, a new vendor) | Update Informs. A probe whose question no longer matters is retired (`entry.md`); a new vendor is a new probe, through New |
| A setting that spends changed (a new `days_requested`, more institutions) | Rewrite Spends in full and ask again: the user's earlier agreement doesn't cover it |

Then:
1. Status back to `Draft`, whatever it was. A probe that was Answered is Answered again only after Record.
2. `dt probes --stamp PB-NN` after any code edit.
3. Run the agent's checks again if `public.py` changed, as in `new.md` step 5.

## Gate

Besides SKILL.md's gate, show the old and new row side by side for every changed check, the new Spends if it changed, and the steps the user must run again. If the decision was already Accepted on this probe's earlier result, hand off to architecture-design Revise: the decision goes back to Proposed until the probe is Answered again.

On an unambiguous yes: set `Ready`. **Stop.**
