You are a blind judge comparing two sets of planning documents for the same project. Both sets were written by an assistant for a solo developer. Judge only the final documents. You are not told how either set was produced. Don't guess, and don't let any guess about process affect scores.

## The user and project (ground truth)
{FACTS}

## The documents
- Set A: {DIR_A}
- Set B: {DIR_B}

Each set has `brief.md`, `spec.md`, `architecture.md`, and possibly `architecture/*.md` and `ideas/*.md`. Read every file in both sets.

## Rubric (score each 1-5)
Content: {CONTENT_KEYS}
Structure: {STRUCTURE_KEYS}

- content_score is the mean of the content items and structure_score is the mean of the structure items, each to 1 decimal place. overall_score = content_score + structure_score (out of 10).
- "right_sizing": the docs are as long as the plan needs. No bloat, no stale or superseded text kept around, no repeated items.
- Consistency: brief, spec, architecture and ideas agree. No stale framing ("first milestone"), no requirements worded for one part when they now apply to several, no references to superseded decisions.
{EXTRA}

## Output
Write ONLY a JSON file to {OUT_PATH} with exactly this shape:
{"winner": "A"|"B", "reasoning": "<one paragraph>", "rubric": {"A": {"content": {...}, "structure": {...}, "content_score": x, "structure_score": x, "overall_score": x}, "B": {...}}, "output_quality": {"A": {"score": 1-10, "strengths": [...], "weaknesses": [...]}, "B": {...}}, "defects": {"A": ["<file: quoted text — what is wrong>", ...], "B": [...]}}

List defects concretely, with a short quote from the doc. Then reply with one line: the winner and both overall scores.
