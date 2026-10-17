"""Spec ↔ architecture bookkeeping, ported from architecture-design's `arch-status.py`.

- `changelog`: a doc's Changelog rows with the source files they cite and their marked IDs
- `pending_rows`: spec Changelog rows the architecture hasn't caught up with
- `broken_fences`: code fences that never close or swallow a heading

A spec Changelog row is pending if it is dated after the architecture's Last updated date. Rows dated that
same day are told apart by order: they are pending if they come after the last spec row that the
architecture's Changelog acknowledges. An architecture row acknowledges a spec row by citing its source file
(ideas/<slug>.md or brief.md) in Source or, for a spec row with no source file, by listing all of its IDs with
the same marks. Spec rows are matched in order and each citation is used once, so a second spec row from the
same idea file stays pending until a later architecture row cites that file again.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


def refs(text: str) -> set[str]:
    """IDs referenced in text, expanding ranges like ENV-01–ENV-04 or ENV-01–04 (arch-status semantics)."""
    out = set()
    for m in re.finditer(r"\b([A-Z][A-Z0-9]*)-(\d{2,})(?:\s*[–-]\s*(?:\1-)?(\d{2,}))?", text):
        pre, a, b = m.group(1), int(m.group(2)), m.group(3)
        width = len(m.group(2))
        for n in range(a, (int(b) if b else a) + 1):
            out.add(f"{pre}-{n:0{width}d}")
    return out


def marked_ids(cell: str) -> dict[str, str]:
    """{ID: added|changed|removed} for a Changelog IDs cell. A "(changed)" or "(removed)" mark covers the
    unmarked IDs before it in its ;-separated group: "TANK-01–TANK-12; QR-03, CORE-04 (changed)"."""
    out: dict[str, str] = {}
    for group in re.split(r";(?![^()]*\))", cell):
        run: set[str] = set()
        for item in re.split(r",(?![^()]*\))", group):
            run |= refs(re.sub(r"\([^)]*\)", "", item))
            mark = re.search(r"\((changed|removed)\b", item, re.I)
            if mark:
                out.update(dict.fromkeys(run, mark.group(1).lower()))
                run = set()
        for r in run:
            out.setdefault(r, "added")
    return out


@dataclass
class ChangelogRow:
    date: str
    change: str
    source: str
    files: set[str] = field(default_factory=set)     # .md files the Source cell cites, minus spec/architecture
    ids: dict[str, str] = field(default_factory=dict)
    all_ids: bool = False                            # the IDs cell reads `all` (an initial spec)

    def label(self) -> str:
        return f"{self.date} | {self.change} | {self.source}"


def changelog(text: str | None) -> list[ChangelogRow]:
    """Rows of a doc's `## Changelog` table."""
    m = re.search(r"^## Changelog[^\n]*$(.*?)(?=^## |\Z)", text or "", re.S | re.M)
    rows = []
    for line in (m.group(1) if m else "").splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if len(cells) < 4 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
            continue
        cited = {re.sub(r"^(\.\./|docs/)+", "", f) for f in re.findall(r"[\w./-]+\.md", cells[-2])}
        rows.append(ChangelogRow(cells[0], " | ".join(cells[1:-2]), cells[-2],
                                 cited - {"spec.md", "architecture.md"}, marked_ids(cells[-1]),
                                 bool(re.fullmatch(r"all\b.*", cells[-1].strip(), re.I))))
    return rows


def pending_rows(spec_rows: list[ChangelogRow], arch_rows: list[ChangelogRow],
                 updated: str | None) -> list[ChangelogRow]:
    """Spec Changelog rows with IDs that the architecture hasn't caught up with."""
    cites = [(set(a.files), {i: m for i, m in a.ids.items() if not i.startswith("AD-")}) for a in arch_rows]
    j, last = 0, -1   # j: architecture row of the previous acknowledgment; last: index of that spec row
    for n, row in enumerate(spec_rows):
        if not row.ids:
            continue
        for k in range(j, len(cites)):
            files, ids = cites[k]
            if (row.files & files) if row.files else (row.ids.items() <= ids.items()):
                files -= row.files
                for i in row.ids:
                    ids.pop(i, None)
                j, last = k, n
                break

    def pending(n: int, row: ChangelogRow) -> bool:
        if updated and row.date != updated:
            return row.date > updated
        return n > last
    return [r for n, r in enumerate(spec_rows) if r.ids and pending(n, r)]


def broken_fences(lines: list[str]) -> list[int]:
    """1-based line numbers of code fences that never close, or that open a block holding a ##–#### heading
    (a block tagged markdown may hold headings)."""
    out, start, fence, is_md, held = [], None, "", False, False
    for n, line in enumerate(lines, 1):
        m = re.match(r"\s*(`{3,}|~{3,})(.*)", line)
        if start is None:
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                start, fence, held = n, m.group(1), False
                is_md = bool(re.match(r"\s*(markdown|md)\b", m.group(2), re.I))
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
            out += [start] if held else []
            start = None
        elif not is_md and re.match(r"#{2,4} \S", line):
            held = True
    return out + ([start] if start else [])
