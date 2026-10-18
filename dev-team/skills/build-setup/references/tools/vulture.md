# vulture: dead code

| | |
|---|---|
| **What it does** | Finds functions, classes, variables and imports that nothing uses |
| **Speed** | Fast: a few seconds |
| **Config** | `[tool.vulture]` |
| **Hook tier** | Reviewer and CI. It guesses (with a confidence score), so keep it out of hard per-edit gates |

> **Verified** in `design/tooling-verification.md` (2026-10-16): vulture 2.16. At 60 the sample had no false positives.

## What it catches

```python
def _old_helper():      # vulture: unused function '_old_helper' (60% confidence)
    ...
```
```text
src/signals.py:12: unused function '_old_helper' (60% confidence)
src/signals.py:40: unused variable 'tmp' (60% confidence)
```
Why: agents rewrite code and leave the old version behind. Ruff's `F401`/`F841` find unused imports and locals, but not an unused function or class.

## False positives

Vulture can't see dynamic use: framework entry points, plugin hooks, anything called by string name, and public functions used only by tests.

At `min_confidence = 80` it reports only unused imports (90%, already Ruff `F401`) and unreachable code (100%); unused functions and classes score 60% and vanish (verified). So the template uses 60 plus a whitelist of today's findings:

```toml
[tool.vulture]
paths = ["src", "scripts/vulture_whitelist.py"]
min_confidence = 60
```

- New mode writes the whitelist from today's findings (`uv run vulture --make-whitelist`, appended under the file's header comment), so `full` passes and any *new* dead code fails. That is CR-41's "must not grow". It fails only `full --exit` (the milestone exit): mid-milestone, `full` prints the findings and passes, because the interface task's stub parameters and type fields are unused until later tasks use them.
- Ratchet regenerates it; a shorter whitelist is the tightening.
- The whitelist lives in `scripts/`, so it is protected, and Ruff excludes it (it isn't real code).
- `__all__` re-exports count as uses.

Run: `vulture` (reads `paths` from config). It runs in `full` only.
