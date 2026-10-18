# The User's Words — Design

**Status:** Built · **Last updated:** 2026-10-18 · **Companion to:** [planning-stage.md](planning-stage.md), [references.md](references.md)

A verbatim record of what the user asked for, `docs/requests.md`, so that the facts, tools and choices they state survive the brief's compression and the session boundary between skills.

---

## 1. Why

Iteration 9 ran a fresh agent session per skill, as a user who clears context would. The blind judge scored plans 7.45–7.7/10, and about 30% of its cited defects were things the user said that a doc lost or overrode. All but one were said during idea-refine. The brief is capped at 500 words and five goals, so it compressed them away; spec-writing's hygiene rule kept tool names out of the spec, telling architecture-design to find them in "the idea file and the conversation", and in a fresh session there is no conversation.

**What a correct record would have held.** Each user message in the four runs' `turns.json`, split into the requests §2 admits, and checked against the final docs (spec and architecture are Approved in all four). Whole-doc approvals, bare "take your default" replies and the simulated user's fallback "Looks good, approved. Please continue." hold no request.

| Run | Requests | Spec / arch | Honoured by ID | By a section (no ID) | Changed with the user's yes | Lost | `request-open` would fail |
|---|---|---|---|---|---|---|---|
| quant all-at-once | 72 | 53 | 43 | 4 | 2 | 4 | spec.md (UR-13); architecture.md (UR-06, UR-33, UR-51) |
| quant incremental | 111 | 91 | 80 | 4 | 3 | 4 | architecture.md (UR-06, UR-14, UR-18, UR-20) |
| rl all-at-once | 45 | 35 | 25 | 5 | 2 | 3 | spec.md (UR-04, UR-05, UR-10) |
| rl incremental | 75 | 63 | 56 | 3 | 3 | 0 | passes |

The lost requests, all heard in idea-refine except UR-51:

| Run | UR | Turn | The user's words | What the Approved doc says |
|---|---|---|---|---|
| quant all-at-once | UR-06, UR-33 | 1, 2 | "(HTTP and WebSocket)"; "over WebSocket", repeated after the agent pushed back | AD-07, AD-09: live runs over SSE; WebSocket only a rejected alternative. 0 mentions in brief or spec |
| quant all-at-once | UR-13 | 1 | "test them with ML for information gain over the residual (market-removed) returns" | SIG-02 tests per-feature rank correlation; no ML model in the stage |
| quant all-at-once | UR-51 | 15 | "Go with A." (A: each Source declares its own expected member range) | AD-22 fixes the 495–510 bounds and lists A as an Alternative; the api-probe session that heard it replied "What was 'A'?" |
| quant incremental | UR-06, UR-18, UR-20 | 1, 2 | "(HTTP and WebSocket)"; "The WebSocket is for live progress of download/validation runs." | AD-07: Server-Sent Events. The gate summary named SSE without saying it overrode the user |
| quant incremental | UR-14 | 2 | "I want yahooquery (free, unofficial Yahoo client)" | The brief: "Yahoo, via an unofficial free client"; AD-03: `yfinance`, which then failed probe PB-03 |
| rl all-at-once | UR-04 | 1 | "a circular tank with a ball bouncing around inside it" | FISH-01: "The tank is a square with walls" |
| rl all-at-once | UR-05 | 1 | "swim away from the ball and survive as long as possible" | FISH-04: hits per fish per episode, a hit fish respawns |
| rl all-at-once | UR-10 | 1 | "a learning predator hunts them" | PREY-01: "6 prey, 2 predators" |

rl incremental, the one run that stayed in a single session, kept every fact rl all-at-once lost. quant incremental's dropped PPO agents and rented GPU aren't losses: the user deferred both (turns 47–48), so they are approved changes.

What the dry run changed in the design:
- **Bare choices need their question.** "Go with A" appears twice in quant all-at-once, at turns 15 and 17, picking opposite options; and block acceptances ("Assumptions 1-7 are fine") carry real choices. Hence `[context]`, required whenever the words don't stand alone.
- **Some requests are honoured by a section with no ID:** Out of scope, Assumptions, Edge cases, Constraints (3–5 per run). Hence section traces, `§Out of scope`.
- **Some facts belong only in the brief** ("evenings/weekends, a few weeks per env", "new to RL"). Hence the `brief` owner, reported to idea-refine and not linted.
- **A recorded change can still leave the doc stale:** quant all-at-once's approved PANEL-02 exception lives only in AD-08, and PANEL-02 still contradicts it. The rule says the change is written into every requirement or decision it touches; `dt` can't check that (§6).
- **The skill that heard it** is not always the one whose question was answered: a reply arrives in the next session, so `--skill` names the session's skill and `--about` names the question.

Two fixes were weighed: one session shared by idea-refine and spec-writing, or a separate record. One session only moves the boundary (architecture-design still starts fresh, which is where quant's WebSocket and yahooquery were lost) and doesn't survive a user clearing context. A record carries the words to every later skill, and `dt` can check each one reached a doc.

---

## 2. Decisions

1. **One file, `docs/requests.md`, one line per request `UR-NN`:** the user's words verbatim in quotes, the skill that heard them and the date. Turn numbers aren't kept: they restart in every session, so the date and skill place a request.
2. **Only concrete, checkable statements:** facts, numbers, constraints, tools, libraries, vendors, protocols, data sources, scope, an option picked ("Go with A"), and the answer to any skill's question. Not doc approvals, vague wishes or the agent's own proposals.
3. **Each request has an owner,** the doc that must honour it: `brief`, `spec`, `architecture`, `pipelines`, `tests`, `plan` or `constraints`. The skill that hears it picks the owner; a tool or vendor is `architecture` even when idea-refine hears it.
4. **Traced in place.** The text after `→` names the IDs (or, for a section with none, its heading: `§Out of scope`) that honour it, a change the user approved (with the approval's words), or the later request that replaced it. The spec cites no UR IDs in requirement text (its no-provenance rule); traces live in requests.md, and an architecture decision's Context may cite the request it follows.
5. **Not budgeted, append-only except the trace.** A line's words, context, skill and date never change and a line is never deleted (`request-edit`); the user changing their mind is a new request that replaces the old one.
6. **`dt request` writes every line,** like `dt route`: it assigns the ID, quotes the words, dates them and keeps the format, so a skill spends one command per statement.
7. **The rule lives once,** in idea-refine's `references/requests.md`; every planning skill's SKILL.md names it in one line, and spec-writing and architecture-design add the honouring step to their own references.
8. **Checked where it matters most:** once the spec or architecture is Approved, any open request it owns fails `dt lint` at that doc and sends `dt next` back to its skill. Brief, pipelines, tests, plan and constraints requests are reported by `dt status` (`requests_open`) only, for now.

---

## 3. The record

```markdown
# Quant Lab — User requests

**Last updated:** 2026-10-18

The user's words, verbatim: one line per fact, constraint, tool, choice or answer, with the skill that heard it and the date. The words never change; only the trace after → does. Written with `dt request`.

- **UR-01** architecture · "live prices over a WebSocket" · idea-refine 2026-10-18 → AD-05
- **UR-02** architecture · "use yahooquery for the free data" · idea-refine 2026-10-18 → AD-03
- **UR-03** spec · "the tank is circular" · idea-refine 2026-10-18 → TANK-02
- **UR-08** spec · "no live trading" · idea-refine 2026-10-18 → §Out of scope
- **UR-04** spec · "one predator" · idea-refine 2026-10-18 → changed: two predators from S3 (approved "two is fine, keep it hard", spec-writing 2026-10-19)
- **UR-05** architecture · "Go with A" [AD-22 price source: A = Sharadar, B = yfinance] · architecture-design 2026-10-19 → AD-22
- **UR-06** pipelines · "rebalance monthly" · pipeline-design 2026-10-20 → superseded by UR-07
- **UR-07** pipelines · "actually weekly" [rebalance cadence] · pipeline-design 2026-10-20 → PL-03
```

- **Line form:** `- **UR-NN** <owner> · "<words>" [<context>] · <skill> <date> → <trace>`. The `[context]` says what bare words answer ("Go with A", "yes, 3"); it is the agent's note, never part of the quote.
- **Trace forms:** IDs and sections (`TANK-02, §Out of scope`: `§` and a heading's text, case ignored); `changed: <what instead> (approved "<the user's words>", <skill> <date>)`; `superseded by UR-NN`. No trace: open.
- **Open** means not changed, not superseded, and no traced item is a live definition in, or a heading of, a doc the owner writes (brief: brief.md and idea files; spec: spec.md; architecture: architecture docs and contracts; the others: their own docs). A trace to a retired ID is `retired-ref`, and the request is open again.
- **The header** has no Status: the record is never Draft or Approved, only appended to.
- **`UR` is reserved:** a spec requirement can't use it (`ref-prefix`).

---

## 4. Who writes and reads it

| Skill | Records | Honours |
|---|---|---|
| idea-refine | The first message, each sharpening answer, each direction picked (Phases 1–2) | `brief` requests only; the brief is otherwise free to compress, because the record doesn't |
| spec-writing | Each answer to its clarifying questions | `spec` requests: a requirement says what the request says, or the user approves the change; `dt request trace`. Its gate's summary has a **Your words** line |
| architecture-design | Each answer, each option picked | `architecture` requests: the user's named tool or picked option is the decision, its Context cites the UR; Revise mode when an Approved architecture has one open. **Your words** line at its gate |
| pipeline-design, test-planning, build-planning, build-setup | Each answer | Their own requests, by the same rule, reported in `requests_open` |

The full rule (what counts, verbatim, owner, `--about`, replacing, honouring, changing with approval, the gate line) is `skills/idea-refine/references/requests.md`.

---

## 5. `dt`

| Area | Change |
|---|---|
| Parser | Doc kind `requests` (`docs/requests.md`); each `- **UR-NN**` line defines its ID (`dt section UR-03`, `dt next-id UR`) |
| `dt request` | `add <owner> "<words>" --skill S [--about] [--replaces UR-NN]`, `trace UR-NN <ID>…`, `change UR-NN "<what>" --approved "<words>" --skill S`, `list [--open] [--owner] [--json]` |
| `dt status` | `requests_open` for each owning skill; architecture-design is `revise` when its Approved doc has one open |
| `dt next` | After routed changes: an Approved spec, then architecture, with an open request of its own → spec-writing (extend), architecture-design (revise) |
| `--summary` | `requests: N not honoured → <skills>` |
| `dt lint` | `request-format`, `request-trace`, `request-open` (at the Approved spec.md or architecture.md header), `request-edit` (words changed or line deleted since HEAD), `request-ref` (a UR named anywhere that isn't defined); `ref-prefix` covers `UR` |

---

## 6. Limits and next steps

- `dt` can't tell whether an ID really honours a request, only that the owner's doc defines it, nor whether an approved change reached every requirement it touches. The gate's **Your words** line puts each trace in front of the user, and the eval's judge reads them.
- A skill that doesn't record what it hears loses it as before. The eval can check this directly: each scenario fact the simulated user states should appear as a UR line in the run's `docs/requests.md`.
- Brief, pipelines, tests, plan and constraints requests aren't linted yet; add them to `DUE_WHEN_APPROVED` once a run shows they're used.
