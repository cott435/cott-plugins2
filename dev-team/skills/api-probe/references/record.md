# Record: results come back

`probes_results` lists a probe whose `evidence/results.json` is newer than its Last run. The user has said "ran it", or a session started after they ran it. Use the shape in `entry.md` and the rules in `safety.md`.

1. **Scan.** `dt probes --scan`. On a hit, stop: name the file and the pattern, and ask the user to look at it themselves. The fix is a narrower allow-list (Revise) and a re-run. Don't open the matched value.
2. **Check the code.** `script_hash` in `results.json` must equal the entry's Hash. If it doesn't, the results are for other code (`probes_stale`): go to Revise and ask for a re-run. Record nothing.
3. **Read `results.json` only.** Never `out/`, never the raw responses, never the terminal output the user ran. A check ID in the file that isn't in the table is an error to report, not to record.
4. **Fill the entry.** Each check's Result from its record, `pass` or `fail` with the observed value in a few words; a check with no record stays `—`. `Last run` is the `run_at` date. Verdict: `pass` when every check passed, else the failed checks and why, in one line. A measure-only check that met its threshold by its requirement's own terms passes, with the note (a card opened 3 months ago).
5. **Manual checks.** A `user (manual)` row's Result is what the user reported in chat. Ask for any that is missing, one at a time.
6. **Not all run yet** (a day-2 check is still waiting): fill what came back, leave the rest `—`, keep `Ready`, and say at the gate which checks are left and when. The probe is Answered only when every row has a Result.

## Gate

Besides SKILL.md's gate, show:
- **Free text** that reached evidence (masked merchant descriptions), every line, for the user to approve before it is committed. Lines they reject are removed by fixing the script's filter and re-running, never by editing evidence.
- **Hand-offs**, one line each, by result:

| Result | Goes to |
|---|---|
| Every check passes | architecture-design Revise: cite the finding in the decision's Context ("PB-01, 2026-10-20: 6 of 6 institutions link; 13–24 months"), set it Accepted, delete the Risks line |
| A check fails, and an option still meets the requirements | architecture-design Revise: revise or supersede the decision |
| A check fails, and no affordable option meets a requirement | spec-writing, on the user's word: name the requirement and the finding. Never edit the spec |
| Observed fields differ from a contract type | architecture-design Revise: the type's fields and invariants follow the evidence; `**Cases:**` can name the samples |
| Spent resources must be kept (Items, tokens) | architecture-design Revise: the decision's Consequences say the build adopts them |

On an unambiguous yes: set `Answered · pass|fail · <date>`, and offer to commit `docs/probes.md` and the probe folder. **Stop.** Next is architecture-design Revise.
