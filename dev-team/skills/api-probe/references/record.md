# Record: results come back

`probes_results` lists a probe whose `evidence/results.json` is newer than its Last run, or the user says "ran it". Use the shape in `entry.md` and the rules in `safety.md`.

1. **No new evidence.** Every run writes `results.json`, a failed one too, so a "ran it" that leaves `probes_results` empty means no script ran, or the leak scan stopped the write. Say so, give the README's next step with its exact command and its `evidence NOT written` advice, and stop. On the second such "ran it", or the second run with the same `error`, don't patch, re-stamp or re-read anything: say the runs left nothing new, and offer at once to waive the probe (their words) or pause it (stays Ready; build-planning waits, pipeline-design and test-planning go on).
2. **Scan.** `dt probes --scan`. On a hit, stop: name the file and the pattern, and ask the user to look at it themselves. The fix is a narrower allow-list (Revise) and a re-run. Don't open the matched value.
3. **Check the code.** `script_hash` in `results.json` must equal the entry's Hash. If it doesn't, the results are for other code (`probes_stale`): go to Revise and ask for a re-run. Record nothing.
4. **A failed run.** `results.json` has an `error`, or a `base_url` other than the script's default host (a local address: a base-URL variable was set where it ran): copy `run_at` to Last run, fill no Result, keep `Ready`, and give the fix at the gate. A wrong host gets one Caveats line, `<run_at>: ran against <base_url>, rejected`, and the variable to unset, said once; a later run on that host is reported in one line with step 1's waive-or-pause offer, never explained or asked about again. A paused probe isn't raised until a run reaches the real host. `usage`: the README command, with its step. `missing`: the key names to put in `.env`. `exception`: the step, class and `frame`; read that line before proposing a fix; a missing file from another probe's `out/` means that probe runs first, and its README order goes in through Revise, as any code fix does.
5. **Read `results.json` only.** Never `out/`, never the raw responses, never the terminal output the user ran. A check ID in the file that isn't in the table is an error to report, not to record.
6. **Fill the entry.** Each check's Result from its record, `pass` or `fail` with the observed value in a few words; a check with no record stays `—`. `Last run` is `run_at`, copied verbatim. Verdict: `pass` when every check passed, else the failed checks and why, in one line. A `null` pass is a measurement: judge it against the row's Pass cell yourself and say so at the gate. A measure-only check that met its threshold by its requirement's own terms passes, with the note (a card opened 3 months ago).
7. **Manual checks.** A `user (manual)` row's Result is what the user reported in chat. Ask for any that is missing, one at a time.
8. **Not all run yet** (a day-2 check is still waiting): fill what came back, leave the rest `—`, keep `Ready`, and say at the gate which checks are left and when. The probe is Answered only when every row has a Result.

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

On an unambiguous yes: set `Answered · pass|fail · <date>`, and commit as the Review Gate says. **Stop.** Next is architecture-design Revise.
