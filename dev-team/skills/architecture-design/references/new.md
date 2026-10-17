# New

Read when `dt status --skill architecture-design` reports New: there is no `docs/architecture.md`. It ends at the Review Gate in `../SKILL.md`. Examples: `examples-new.md` (a single-package proof of concept), `examples-new-multi.md` (a multi-package platform).

```
READ ─→ SHAPE ─→ COMPONENTS ─→ CONTRACTS ─→ DECISIONS ─→ WRITE ─→ [user approves] ─→ pipeline-design
```

**1. Shape.** Read `shape.md`, propose single or multi-package with a one-line reason, and record it in the header. Multi-package: first propose the package ids, dependency direction and cross-package flows.

**2. Components** as `components.md` says.

**3. Contracts.** Write each package's `contract.md` as `contracts.md` says.

**4. Decisions.** Make each significant open choice as `decisions.md` says.

**5. Write** from `templates.md`, following `writing-rules.md`.
