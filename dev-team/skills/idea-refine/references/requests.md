# The user's words: `docs/requests.md`

Every planning skill follows this. The brief and the spec compress, and the next skill often runs in a fresh session that sees only the docs. `docs/requests.md` keeps what the user actually said, word for word, so the skill whose doc must honour it can. `dt request` writes every line; never edit the file by hand.

## What goes in

One request (`UR-NN`) per concrete statement you could check a doc against:

- facts about the domain, the data or the world ("the tank is circular"), numbers, limits, deadlines, budgets
- tools, libraries, vendors, protocols and data sources the user names ("stream prices over a WebSocket", "use yahooquery")
- choices: an option picked from yours ("Go with A"), and the answer to any question a skill asked
- scope: what must be in, or left out

Not: approval of a whole doc ("approved", "looks good"), wishes with nothing to check ("make it nice"), your own proposals the user hasn't picked, or words already recorded (`dt request` lists them).

## Recording

As you hear it, before you write any doc:

```
dt request add <owner> "<their words>" --skill <this skill> [--about "<what it answers>"] [--replaces UR-NN]
```

- **Verbatim.** Quote the shortest span of their message that carries the fact. Never paraphrase, translate, correct or merge. A message stating three facts is three requests.
- **`--about`** when the words don't stand alone: "Go with A" → `--about "AD-22 price source: A = Sharadar, B = yfinance"`; "yes, 3" → what was asked.
- **Owner** is the doc that must honour it: `spec` (behaviour, numbers, scope the user can observe), `architecture` (tools, libraries, vendors, protocols, data sources, an option for a decision), `pipelines`, `tests`, `plan`, or `constraints` (the quality bar, tooling rules).
- **The user changes their mind:** record the new words with `--replaces` the old UR. A line is never edited or deleted.
- The request that started the run is the user's first message: record it too.

## Honouring

Before you write your doc, read `docs/requests.md` whole; `requests_open` in `dt status` lists the open requests your doc owns. For each:

- **Honour it:** write the requirement, decision, step, case or rule that does what the words say, then `dt request trace UR-NN <ID>…` with the IDs that do it (spec: requirement IDs; architecture: `AD-NN` or a contract ID; the others: their IDs).
- **Or change it, with the user's yes:** when it conflicts with another request or can't be met, say so at your gate with your alternative. Only after the user agrees: `dt request change UR-NN "<what instead>" --approved "<their words>" --skill <this skill>`. Never override a request silently, and never record an approval the user didn't give. Headless: leave it open under Open questions and the doc Draft.
- A request another doc owns waits for that doc's skill. Don't copy it into yours (the spec names no tools, even when a request does).

## At the gate

Before asking for approval, `dt request --open --owner <yours>` is empty, except requests whose change you are asking the user about. The summary lists them in one line:

> **Your words:** honoured UR-01 (TANK-02), UR-03 (AD-04); change proposed: UR-05 one predator → two (yes?); open: none.

Once the spec or architecture is Approved, `dt lint` fails it for every open request it owns, and `dt next` sends the run back to its skill.
