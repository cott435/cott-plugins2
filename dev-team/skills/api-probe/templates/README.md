# PB-NN: <the entry's title>

<One line: what this probe checks and which decision waits on it (AD-NN).> The spec and the
verdict are in `docs/probes.md`, PB-NN. The probe's code is reference for the build and is
never imported.

## Who runs what

| Check | Runner | Command |
|---|---|---|
| C1 | user (manual) | <where to look; what to report> |
| C2 | agent | `python3 probes/PB-NN-<slug>/public.py` |
| C3 | user | `python3 probes/PB-NN-<slug>/probe.py c3` |

## What it spends

<The entry's Spends line, in full: Items, paid calls, a subscription month, settings that can't
be changed later. Nothing runs until you have agreed to it.>

## Before you start

1. Copy `.env.example` to `.env` in this folder and fill in your values. Don't paste them
   anywhere else: the scripts read `.env` themselves, and they never print a key.
2. <Other prerequisites: an account, a plan, a file only you can write in `out/` such as
   `out/institutions.txt`.>
3. Check that git ignores your keys: `git check-ignore probes/PB-NN-<slug>/.env probes/PB-NN-<slug>/out/`
   prints both paths.

## Steps, in order

1. <Command> — <how long it takes>; <what it spends>. <What stops the run, such as C2 failing
   before C3 spends anything.>
2. <Command, a day later if a check needs a second run.>

When you've finished, say "ran it". Don't paste the output: the scripts write
`evidence/results.json`, and api-probe reads that.

## If a run stops

- `evidence NOT written: matched <pattern>`: the leak scan found something that looks like a
  secret or personal data. Open `out/evidence.rejected.json` yourself, and tell the agent only
  which pattern matched and which check it was in.
- `missing <NAME>`: that variable isn't in `.env` or the environment.
- An HTTP error prints the status and the vendor's error code, never the request headers.

## Files

- `probe.py` (yours to run), `public.py` (the agent's: it reads no environment at all),
  `probe_kit.py` (the shared helper, copied in).
- `evidence/` is committed. The scripts write it, and nothing else does.
- `out/` and `.env` are gitignored and owner-only. They hold your keys, raw responses and
  tokens. The agent never reads them.
