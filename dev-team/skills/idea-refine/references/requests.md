# The user's words: `docs/requests.md`

Every planning skill follows this. The brief and the spec compress, and the next skill often runs in a fresh session that sees only the docs. `docs/requests.md` keeps what the user actually said, word for word, so the skill whose doc must honour it can. `dt request` writes every line; never edit the file by hand.

## What goes in

One request (`UR-NN`) per concrete statement you could check a doc against:

- facts about the domain, the data or the world ("the tank is circular"), numbers, limits, deadlines, budgets
- tools, libraries, vendors, protocols and data sources the user names ("stream prices over a WebSocket", "use yahooquery")
- choices: an option picked from yours ("Go with A"), and the answer to any question a skill asked
- a block acceptance ("assumptions 1–7 are fine"): one request, its `--about` listing what was accepted
- scope: what must be in, or left out

Not: approval of a whole doc ("approved", "looks good"), wishes with nothing to check ("make it nice"), your own proposals the user hasn't picked, or words already recorded (`dt request` lists them).

## Recording

As you hear it, before you write any doc:

```
dt request add <owner> "<their words>" --skill <this skill> [--about "<what it answers>"] [--replaces UR-NN]
```

- **Verbatim.** Quote the shortest span of their message that carries the fact. Never paraphrase, translate, correct or merge. A message stating three facts is three requests.
- **`--about`** whenever the words don't stand alone: "Go with A" → `--about "AD-22 price source: A = Sharadar, B = yfinance"`; "yes, 3" → what was asked. A bare letter means nothing to the next session, and the same words can pick opposite options in two rounds.
- **Owner** is the doc that must honour it: `brief` (who the user is, their time, budget or experience: context no later doc carries), `spec` (behaviour, numbers, scope the user can observe), `architecture` (tools, libraries, vendors, protocols, data sources, an option for a decision), `pipelines`, `tests`, `plan`, or `constraints` (the quality bar, tooling rules).
- **The user changes their mind:** record the new words with `--replaces` the old UR. A line is never edited or deleted.
- The request that started the run is the user's first message: record it too.

## Honouring

Before you write your doc, read `docs/requests.md` whole; `requests_open` in `dt status` lists the open requests your doc owns. For each:

- **Honour it:** write the requirement, decision, step, case or rule that does what the words say, then `dt request trace UR-NN <ID>…` with the IDs that do it (spec: requirement IDs; architecture: `AD-NN` or a contract ID; the others: their IDs). Honoured by a section with no ID (Out of scope, Assumptions, Constraints): trace its heading, `§Out of scope`.
- **Does what the words say** means the same shape, count, number, tool and goal, and for a named method or concept its mechanism, not its name: "self-play" is training against the opponent's past versions, not two learners at once. A number the words state must appear in the traced text (`request-number` warns).
- **Or change it, with the user's yes:** when it conflicts with another request or can't be met, say so at your gate with your alternative. Only after the user agrees, write the change into every ID it touches, the ones that honoured the old words included (a test case restating the old value too), then `dt request change UR-NN "<what instead>" --approved "<their words>" --skill <this skill> --into <those IDs>`. A doc that cites the request from another ID gets `request-cite`: bring it in line and add it with `dt request change UR-NN --into <ID>`. Never override a request silently, and never record an approval the user didn't give. Headless: leave it open under Open questions and the doc Draft.
- **A value from the user's words** (a golden case's expected output, a limit) cites the request as its Source: `**Source:** UR-04`. A number worked out from their words is not theirs; its Source says how it was derived (`request-source` warns).
- A request another doc owns waits for that doc's skill. Don't copy it into yours (the spec names no tools, even when a request does).

## At the gate

Before asking for approval, `dt request --open --owner <yours>` is empty, except requests whose change you are asking the user about. The summary lists them in one line:

> **Your words:** "circular tank" UR-01 → TANK-02 "the tank is a circle"; "use yahooquery" UR-03 → AD-04 "yahooquery"; change proposed: UR-05 one predator → two (yes?); open: none.

Quote the words and the traced text side by side, so the user sees whether one does the other.

Once the spec or architecture is Approved, `dt lint` fails it for every open request it owns, and `dt next` sends the run back to its skill.
