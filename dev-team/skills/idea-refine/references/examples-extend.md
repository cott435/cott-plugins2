# Example: a feature idea in an existing product

Extend mode in a codebase: an idea file, and a fit check that leaves the brief unchanged.

## Feature Idea Within an Existing Product (Extend Mode, Codebase-Aware)

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
- **Stage:** New S4 (roadmap stage on acceptance)

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
