# New: a probe is written

`probes_unwritten` lists a probe a decision cites with no entry yet (`PB-01 (AD-04)`), or the user asks a question about a service ("does the weather API return hourly history back to 2015?"). Use the shape in `entry.md` and the rules in `safety.md`. `../examples.md` shows the whole round for FinTrack's Plaid probe.

## 1. Read what the probe serves

- The decision and its Risks line (`dt section AD-04`), the requirements it rests on, and the contract types whose fields depend on the source. A user's direct question informs the decision being made. With no decision yet, ask which requirement it serves; a probe that informs nothing isn't written.
- The vendor's **official docs**: one page per question (the pricing or plan page, the endpoint reference, the error and rate-limit pages, the sandbox page), never a homepage or a third-party summary. Note each with the date read. A page that refuses a fetch is named under Open questions, not guessed at.

## 2. Sort every claim the decision rests on

| The claim | Goes to |
|---|---|
| The docs settle it | Docs read, cited; no check |
| The docs are silent, vague ("up to 24 months"), or contradict the design | A check |
| It depends on the user's account, plan, institutions or data | A user check |

A contradiction between the docs and the decision (the weather API's timestamps are UTC, and the decision says local time) goes to the gate summary at once, as a hand-off to architecture-design, before anything runs.

## 3. Write the entry

Draft, with the checks table. Each check's Pass comes from the requirement it informs, with the ID in the cell ("≥ 12 months where the bank keeps it (DATA-01)"). Order the checks so the cheap ones come first and a failure stops the run before anything is spent. Spends names everything a run uses up.

## 4. Write the folder

1. Copy `templates/probe_kit.py` unchanged, and `templates/README.md` and `templates/.env.example`; fill both in.
2. Write `public.py` for the agent's checks, if any, and `probe.py` for the user's. Each check is one function ending in `record()`. Allow-list every field that reaches evidence.
3. Add the `.gitignore` lines from `safety.md` that are missing.
4. `dt probes --stamp PB-NN` writes the Hash.

## 5. Run the agent's checks

`env -i PATH="$PATH" python3 probes/PB-NN-<slug>/public.py`, then fill those rows' Result. A scan hit means the allow-list is wrong: fix the script and run again, without opening `out/`. Never run `probe.py`, not even with a dry-run flag.

## 6. Gate

Besides SKILL.md's gate, show:
- **Settled by the docs:** each claim and its page, in one line each.
- **Contradictions** found in step 2, first.
- **Spends**, in full, and the question whether the user agrees to it.
- **Your steps:** the README's order, the exact commands, how long each takes and what each spends.
- **The agent's results so far.**

On an unambiguous yes, to the checks and to the spend: set `Ready`. **Stop.** The user runs their steps when they can. Meanwhile pipeline-design and test-planning can go on; build-planning waits for this probe.
