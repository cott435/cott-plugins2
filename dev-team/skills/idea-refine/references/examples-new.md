# Example: a new project

A vague early-stage concept through all three phases to a Draft brief.

## Vague Early-Stage Concept (Full 3-Phase Session)

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

- **Core bet:** Restaurants need both the channel and the engine that keeps customers on it.
- **User value / feasibility:** Higher ceiling, but two products; the channel alone is a commodity (Square, Toast).
- **Hidden assumption:** Bundling beats partnering (a retention layer on top of Square Online).
- **What could kill it:** Scope.

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
