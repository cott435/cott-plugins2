# Ideation Session Examples

These examples demonstrate what good ideation sessions look like across different kinds of ideas. Study the rhythm, tone, and structure — not just the content. The skill should feel equally at home with a vague startup concept, a feature for an existing product, or a process improvement.

---

## Example 1: Vague Early-Stage Concept (Full 3-Phase Session)

**User invokes:** `/ideate I want to help small local restaurants compete with the big delivery platforms`

### Phase 1: Understand & Expand

**Skill response:**

> **How might we** give independent restaurants the reach and convenience customers expect from delivery platforms, without forcing them into a model that erodes their margins and brand?

That's a big space. Let me sharpen it:

1. **Which part of "compete"?** Customer acquisition? Delivery logistics? Online ordering UX? Loyalty/retention? Margin pressure from platform fees?
2. **Who are you building for?** The restaurant owner? The diner? Both?
3. **What's the constraint?** Are you thinking software? A cooperative model? Something physical?

**User responds:** "Restaurant owners. The core pain is that they're paying 25-30% commission to delivery apps but feel they can't opt out because that's where the customers are. I'm thinking software but I'm open."

**Skill continues:**

So the problem isn't delivery logistics — it's **customer dependency**. The platforms own the customer relationship, and restaurants are renting access to their own customers at 30% of revenue. That's the leverage to break.

Here are 6 variations:

1. **Direct Channel Toolkit:** Give restaurants their own branded ordering — web, SMS, maybe a lightweight app — so they can move existing customers off-platform. The core bet: customers who *already know* a restaurant will order direct if it's easy enough. You don't need to compete with DoorDash for discovery, just for reordering.

2. **Inversion — Charge the Customer, Not the Restaurant:** What if the delivery fee model flipped? Customers pay a small premium for direct ordering, restaurants pay zero commission. Position it as "support your local spot." The bet: enough customers care about supporting local businesses to pay $1-2 more per order.

3. **Constraint Removal — What If Delivery Weren't Required?** The platforms bundle discovery + ordering + delivery, but most of their cost (and the restaurant's commission) is delivery. What if you only solved ordering and pickup? Pickup-first model. Restaurants keep 100% of revenue, customers save the delivery fee. Works best in dense neighborhoods.

4. **Combination — Restaurant Collective:** A co-op model where 20-50 local restaurants in an area share a platform, split costs, and cross-promote each other. Individual restaurants can't afford marketing — but a neighborhood collective can. Think "local food hall" but digital.

5. **Audience Shift — For Regular Customers:** Don't try to acquire new customers. Build exclusively for a restaurant's existing regulars — the people who come in weekly. A loyalty/reorder tool that's dead simple: "Your usual?" one-tap reorder. The 80/20 bet: 20% of customers drive 80% of revenue, and those people don't need DoorDash to discover the restaurant.

6. **Expert Lens — What Restaurant Owners Actually Do:** Most small restaurant owners aren't looking at dashboards. They're in the kitchen. Any tool that requires them to "manage" something will fail. The winning approach might be something that runs itself — auto-texts regulars when they haven't ordered in 2 weeks, auto-posts the daily special, auto-handles reorders. Zero restaurant-side effort.

Variation 5 and 6 together are interesting. Instead of trying to out-platform the platforms, you'd build something hyper-narrow: a reordering and retention tool for a restaurant's best existing customers. No discovery, no delivery, no marketplace. Just "keep your regulars ordering direct."

Which directions interest you?

---

### Phase 2: Evaluate & Converge

**User responds:** "I love the regulars angle (5 and 6). The direct channel toolkit (1) feels necessary but boring. The co-op idea (4) is interesting but complex. Let me focus on 1 + 5 + 6 combined."

**Skill response:**

Good instincts. That combination has a clear thesis: **own the relationship with your best customers, make reordering effortless, and require zero effort from the restaurant owner.** Let me stress-test it.

**Direction A: The "Regulars Engine" (Variations 5 + 6 fused)**
A tool focused entirely on a restaurant's existing repeat customers. Auto-reorder, auto-engagement, zero management.

- **Core bet:** A restaurant's top 20% of customers will shift to direct ordering if the experience is frictionless and personal. The restaurant doesn't need *new* customers — it needs to stop paying 30% on customers it already has.
- **User value:** High and immediate. Every direct reorder saves the restaurant 25-30% commission. If a regular orders $30/week, that's ~$400/year in saved fees per customer. 50 regulars = $20K/year. That's real money for a small restaurant.
- **Feasibility:** Medium. The ordering/payment tech is commodity. The hard parts: (a) how do you identify and onboard "regulars" without the restaurant doing manual work? (b) How do you handle the cold start — the first reorder needs an order history that lives on the delivery platform, not with you.
- **Differentiation:** High for the niche. Platforms optimize for marketplace dynamics (new customer discovery, driver logistics). Nobody is optimizing specifically for "keep your regulars ordering direct." It's too small for DoorDash to care about, which is exactly why it's a good wedge.
- **Hidden assumptions:**
  - Regulars will install/use yet another ordering method (assumption most likely to be wrong)
  - Restaurant owners will share customer contact info or let you access it
  - Direct ordering won't cannibalize dine-in revenue
- **What could kill it:** If customers simply won't switch channels. Habit is powerful — even if DoorDash costs more, it's already on their phone.

**Direction B: Direct Channel + Retention Hybrid (Variation 1 + 5)**
Branded ordering for the restaurant *plus* the retention automation. More complete but more complex.

- **Core bet:** Restaurants need both the channel (a way to accept orders) and the engine (a way to keep customers coming back through that channel).
- **User value:** Higher ceiling, but only if both parts work together. The ordering channel alone is a commodity (Square, Toast already do this). The retention layer alone has no channel to retain customers *on*.
- **Feasibility:** Lower. You're building two products and hoping they're better together.
- **Differentiation:** Medium. The combination is interesting, but each piece individually has competitors.
- **Hidden assumption:** That bundling these is better than partnering (e.g., retention layer on top of Square Online).
- **What could kill it:** Scope. Building two things well is exponentially harder than building one thing well.

**The honest read:** Direction A is the sharper bet. Direction B is safer but less differentiated. The biggest risk for A is the channel-switching problem — getting customers to order through a new method. If you can crack that (and variation 6's "zero effort" approach might help — an SMS-based reorder doesn't require a new app), the rest follows.

One thing I want to push back on: you said variation 1 feels "necessary but boring." That instinct to include the "necessary" thing is how products lose focus. If the regulars engine works, you can add a branded ordering channel later. But if you build the channel first, you're just another Square Online competitor.

---

### Phase 3: Write the Brief

**User picks Direction A.** The skill writes `docs/brief.md` as a Draft:

```markdown
# ReOrder

**Status:** Draft · **Last updated:** 2026-10-14

## The problem
Independent restaurants pay delivery apps 25-30% on every order, including orders from their most loyal customers. Those regulars would happily order direct, but there is no easy way for them to do it, so the restaurant pays a fee on relationships it already owns.

## Who it's for
Owners of independent restaurants with a steady base of repeat customers. Secondary: those regular customers.

## Goals
1. Regulars can reorder their usual meal directly in under 30 seconds.
2. Owners move their best customers off delivery apps without extra daily work.
3. Owners keep the full value of repeat orders.

## Constraints
- The owner is in the kitchen, not at a computer. Setup must take under 15 minutes.
- Pickup only at first. We have no delivery drivers.
- Must work for customers without installing an app.

## What success looks like
- 5 pilot restaurants, each with 20 regulars set up.
- At least 30% of those regulars reorder direct within 4 weeks.

## What we're betting on
- Regulars will order by text instead of their usual delivery app.
- Owners know who their regulars are and will share their contact details.
- Saving $8-10 per order is worth 15 minutes of setup.

## Not doing
- Delivery — expensive and not the core problem.
- Helping restaurants find new customers — that is the delivery apps' game.
- A branded app or website — Square and Toast already do this.
- Menu or till integration — "your usual" doesn't need a live menu yet.
- Reporting dashboards — owners get a weekly text summary instead.

## Open questions
- What rules apply to texting customers for marketing?
- How do we handle price changes on a saved "usual" order?
```

**Skill then says:** "The brief is at `docs/brief.md` (about 300 words). In short: restaurants pay platform fees on customers they already own; the top goal is a 30-second direct reorder; the biggest thing we're not doing is delivery. Read it and tell me to accept it or what to change — I'll write the spec once it's accepted." *(Turn ends.)*

---

## Example 2: Feature Idea Within an Existing Product (Extend Mode, Codebase-Aware)

**User invokes:** `/ideate adding real-time collaboration to our document editor`

### Phase 1: Understand & Expand

**Skill response:**

> **How might we** let multiple people work on the same document simultaneously in a way that feels natural, not chaotic?

I scanned your codebase and see you're using a block-based editor architecture with a REST API for persistence. No WebSocket infrastructure currently. That's important context. A few questions:

1. **What's the collaboration pattern?** Are people editing the same paragraph at the same time (Google Docs style)? Or working in different sections (Notion style)? Or reviewing/commenting while one person edits?
2. **How many simultaneous users?** 2-3 (pair editing)? 10+ (team workspace)?
3. **What's driving this now?** Customer requests? Competitive pressure? Internal need?

**User responds:** "2-5 people, usually working in different sections. Customers keep asking. We're losing deals to Notion because they assume any modern editor has this."

**Skill continues:**

The competitive pressure framing matters — this might be a checkbox feature (must-have to stay in the consideration set) rather than a differentiator. That changes how much you should invest.

I see your document model uses independent blocks with a flat ordering system (`src/models/document.ts:45`). That's actually favorable — block-level granularity means conflicts are rarer than character-level editing.

Here are 5 variations:

1. **Block-Level Locking (Simplest Path):** When someone starts editing a block, it's locked for others. They see a presence indicator ("Alex is editing...") but can edit any other block freely. No conflict resolution needed. Your existing block model supports this with minimal changes — add a `locked_by` field and a WebSocket layer for presence.

2. **Inversion — Async-First Collaboration:** Instead of real-time co-editing, lean into async. Inline suggestions, comments, and proposed edits that the document owner merges. Like suggestion mode, but as the *primary* collaboration model. Bet: for 2-5 people in different sections, async might actually be *better* than real-time.

3. **Simplification — Presence Without Co-Editing:** Show who's viewing the document and what section they're looking at (cursors, avatars in margins), but don't enable simultaneous editing. People coordinate verbally. Sounds primitive, but might be 80% of the value at 10% of the engineering cost.

4. **Combination — Collaboration + Version Branches:** Let people create "branches" of a document, edit independently, then merge. Each person gets their own space, no conflicts during editing, and you build a merge UI. Plays to your existing versioning system.

5. **10x Version — AI-Mediated Collaboration:** Multiple people describe what they want in a section, and AI synthesizes their inputs into a draft they all iterate on. Nobody directly edits the same text — they all influence it. Radical, possibly too early, but worth naming.

Given your architecture and the competitive context, I'd push you toward variation 1 or 3. You need to close deals, which means you need this shipped, which means you need the simplest version that checks the box. Variation 1 gives you real co-editing. Variation 3 is even cheaper but might not satisfy the "we need real-time" checkbox.

---

*Phase 2 would cluster into "minimum viable co-editing (1 or 3)" vs. "differentiated collaboration model (2 or 4)" — evaluating whether to check the competitive box quickly or invest in something that becomes a selling point.*

*Phase 2 clusters into "minimum viable co-editing (1 or 3)" vs. "differentiated collaboration model (2 or 4)". The user picks block-level locking.*

### Phase 3: Write the Idea File (Extend Mode)

The editor already has `docs/brief.md` and `docs/spec.md`, so this is extend mode. **Fit check:** the brief's users are small teams writing shared documents, and Goal 2 is "Teams can produce a finished document without emailing drafts around." Real-time editing serves Goal 2 directly, so **the brief does not change.** The skill writes `docs/ideas/shared-editing.md`:

```markdown
# Idea: Shared Editing

**Status:** Draft · **Last updated:** 2026-10-14 · **Brief:** [../brief.md](../brief.md)

## In one sentence
This lets 2-5 teammates edit the same document at the same time, so they stop waiting on each other or overwriting each other's work.

## The problem
Teams today take turns: one person edits while the others wait, or they edit copies and merge by hand. Customers ask for this every month, and sales has lost three deals this quarter to tools that already have it. For most buyers it's a box that must be ticked before they'll consider us.

## Who it's for
Small teams (2-5 people) working on one document, usually each in their own section.

## How it fits
- **Serves:** Goal 2 (finish documents without emailing drafts)
- **Touches:** EDIT-03 (only the owner can edit) must change; SAVE-01 (autosave) must handle several editors
- **Brief changes:** None

## Recommended direction
When someone starts editing a block, it's reserved for them. Everyone else sees who is in it ("Alex is editing") and can edit any other block freely. When they click away, the block is released.

This fits how teams already work, each in their own section, and avoids the hard problem of two people typing in the same sentence. Our documents are already made of separate blocks, which makes this much cheaper than full live co-typing.

## Alternatives considered
- Presence only, no co-editing — cheaper, but may not tick the box buyers are checking.
- Suggestion-only (async) — interesting, but doesn't answer the request we keep hearing.
- Branch and merge — powerful, but adds a merge step teams don't want.

## What success looks like
- Lost-deal notes stop citing missing collaboration.
- 30% of active teams have two or more people editing at once within two months.

## What we're betting on
- Teams rarely need to edit the same paragraph at the same moment.
- A "someone is editing this" label is enough. People won't feel blocked.

## Not doing
- Two people typing in the same block — complex, and rarely needed by small teams.
- Offline editing — not requested by 2-5 person teams.
- AI-merged drafts — premature.

## Open questions
- What happens if someone leaves a block reserved and walks away? Release it after a timeout?
- Can viewers (not editors) see live changes?
```

**Skill then says:** "The idea is at `docs/ideas/shared-editing.md`. The brief is unchanged: this serves Goal 2. Heads-up for the spec: it changes EDIT-03. Accept it or tell me what to change." *(Turn ends.)*

*If instead the idea had needed a new goal — say, "let clients outside the team comment" (a new user) — the fit check would flag it. Either the brief gains a goal and adds clients as a user, or it's a separate project.*

---

## Example 3: Process/Workflow Idea (Non-Product)

**User invokes:** `/ideate a better way to run our weekly team retrospectives — they've gotten stale and people dread them`

### Phase 1: Understand & Expand

**Skill response:**

> **How might we** make retrospectives genuinely useful — something the team looks forward to — instead of a recurring meeting people endure?

Before expanding:

1. **What's stale about them?** Same format every time? Same people talking? Action items that never get done? Topics feel repetitive?
2. **Team size and dynamic?** 5 people who all speak up, or 15 where 3 dominate?
3. **What does a *good* retro look like to you?** Have you had one that worked? What made it different?

**User responds:** "8 people, maybe 3-4 actually talk. Same 'what went well / what didn't / action items' format for a year. The action items pile up and nothing changes. People think it's theater."

**Skill continues:**

The action item problem is the real signal. If nothing changes after the retro, people rationally disengage. The meeting isn't stale — it's **broken at the output layer**. The format might be fine if the follow-through worked.

Here are 6 variations:

1. **Fix the Output, Not the Meeting:** Keep the retro format but completely change what happens after. One action item max per retro. Assigned an owner and a deadline during the meeting. Next retro starts with a 5-minute demo of the completed action. If it's not done, that *becomes* the retro topic. The constraint of one item forces prioritization.

2. **Inversion — Kill the Meeting:** Replace the synchronous retro with an async one. Everyone submits reflections in writing during the week. A rotating facilitator synthesizes themes and proposes one change. The "meeting" is a 15-minute standup to agree or disagree. Bet: writing produces more honest feedback than speaking in a group.

3. **Audience Shift — Retro for the Quiet Ones:** Design the format for the 4-5 people who don't talk. Anonymous submission of topics. Dot-voting to prioritize. Small-group breakouts (pairs) before full-group discussion. The loud voices still participate, but the structure prevents them from dominating.

4. **Simplification — The One Question Retro:** Each retro has exactly one question, and it changes every week. "What's one thing that slowed you down?" "What did you learn that the team should know?" "If you could change one thing about how we work, what?" The constraint forces depth over breadth.

5. **Combination — Retro + Experimentation:** Treat each retro output as a hypothesis. "We believe that [change] will improve [outcome]." Run it as a 2-week experiment. Next retro: did it work? Keep, modify, or kill. Turns the retro into a continuous improvement engine with built-in accountability.

6. **Expert Lens — What Facilitators Know:** Experienced facilitators say the #1 retro killer is lack of safety, not format. People won't say what's really wrong if they fear consequences. The fix might not be structural — it might be starting with an anonymous "team health check" score (1-5) each week. When safety is high, retros naturally improve.

The interesting tension: variations 1 and 5 fix the *output* problem (nothing changes). Variations 2, 3, and 4 fix the *input* problem (same voices, same topics). Variation 6 says both are symptoms of a deeper issue. Where do you think the real bottleneck is?

---

*Phase 2 would evaluate in terms of: effort to try (most are free — just change how you run the next meeting), risk (variation 2 is the biggest departure), and whether the team's real problem is output (action items die) or input (not enough honesty).*

*Phase 3 would produce a brief recommending starting with variation 1 (one action item, demo next week) as a zero-cost experiment, combined with variation 3's anonymous submission. "Not Doing" list: new tools, elaborate facilitation techniques, or anything requiring budget. The first fix should take 0 minutes of prep and $0.*

---

## What to Notice in These Examples

1. **The restatement changes the frame.** "Help restaurants compete" becomes "retain existing customers." "Add real-time collaboration" becomes "let people work simultaneously without chaos." "Fix stale retros" becomes "fix the output layer."

2. **Questions diagnose before prescribing.** Each question determines which *type* of problem this actually is. The retro example reveals the problem is action item follow-through, not meeting format — and that changes every variation.

3. **Variations have reasons.** Each one explains *why* it exists (what lens generated it), not just *what* it is. The label (Inversion, Simplification, etc.) teaches the user to think this way themselves.

4. **The skill has opinions.** "I'd push you toward 1 or 3." "Variation 6 is worth sitting with." It tells you what it thinks matters and why — not just neutral options.

5. **Phase 2 is honest.** Ideas get called out for low differentiation or high complexity. The skill pushes back: "That instinct to include the 'necessary' thing is how products lose focus."

6. **The brief is short and plain.** Anyone could read the ReOrder brief in two minutes. It says why the project exists and what we're betting on; it leaves requirements to the spec.

7. **The "Not Doing" list does real work.** It's specific and reasoned. Each item is something you might *want* to do but shouldn't yet.

8. **The skill adapts to context.** A codebase-aware example references actual architecture. A process idea generates zero-cost experiments instead of products. The framework stays the same but the output matches the domain.

9. **The brief waits for acceptance.** The turn ends after the Draft is saved. The spec is written only after the user accepts.

10. **Extend mode writes an idea file, not a bigger brief.** The shared-editing idea gets its own file with the context the spec needs: which goal it serves, which existing requirements it touches, and the alternatives that were rejected. The brief changes only when the fit check says the project's goals or constraints changed.
