# mini — Contract

**Package:** mini · **Status:** Approved · **Last updated:** 2026-10-17 · **Architecture:** [../../architecture.md](../../architecture.md)

## core

### core.Numbers: type
`@dataclass(frozen=True) class Numbers: values: tuple[float, ...]`
- **Invariants:** at least one value
- **Boundary:** core · **Fixtures:** tests/contracts/core.Numbers/ · **Cases:** three numbers
- **Used by:** PL-01

### core.Summary: type
`@dataclass(frozen=True) class Summary: count: int; total: float; mean: float | None`
- **Invariants:** `count` = number of values; `total` = their sum; `mean` = total ÷ count, or None
- **Boundary:** core · **Fixtures:** tests/contracts/core.Summary/ · **Cases:** a summary of three numbers
- **Used by:** PL-01

### core.summarize: Summarize numbers
`def summarize(numbers: Numbers) -> Summary`
- **Invariants:** never changes its input
- **Used by:** PL-01
