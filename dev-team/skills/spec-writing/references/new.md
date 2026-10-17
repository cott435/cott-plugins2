# New mode: writing the spec from the brief

Read when `dt status` reports `mode: new`: there is no `docs/spec.md`, and the accepted brief is the input.

```
READ BRIEF ─→ SURFACE ASSUMPTIONS ─→ CLARIFY ─→ WRITE SPEC ─→ [user approves] ─→ architecture-design
```

## Step 1: Map goals to features

From the brief's numbered goals, propose features and show the mapping before writing:

```
Goal 1 (regulars reorder in < 30s)     → Saved orders (S1), Text reorder (S2)
Goal 2 (no extra daily work for owner) → Regulars setup (S1), Order notifications (S2)
```

Every goal has a feature, and every feature names its roadmap stage (`references/spec.md`). **Every stage the brief and roadmap list is specced in full**: features, requirements, criteria and edge cases for all of them, never "S1 in full, the rest outlined". Later skills design only what the spec holds.

## Steps 2-3: Surface assumptions, then clarify

As SKILL.md's Asking section says.

## Step 4: Write the spec

Read `references/spec.md` and write `docs/spec.md` from its template, following its writing rules (and its data and ML rules where they apply).

## Step 5: Review Gate

SKILL.md's Review Gate. This mode adds no gate steps and no on-approval step.
