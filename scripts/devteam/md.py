"""Low-level markdown reading: fences, headings, header lines, bold-key fields, tables and ID references.

Everything here works on a list of lines and knows nothing about which doc it is reading.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ID forms (planning-stage.md §13). Requirement IDs (spec) are any PREFIX-NN.
REQ_ID = r"[A-Z][A-Z0-9]*-\d{2,}"
TASK_ID = r"M\d+-T\d{2,}"
FINDING_ID = r"M\d+-R\d{2,}"
MILESTONE_ID = r"M\d+"
SYMBOL_ID = r"[a-z][a-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+"
HEADING_ID = rf"(?:{TASK_ID}|{FINDING_ID}|{MILESTONE_ID}|{REQ_ID}|{SYMBOL_ID})"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
ID_HEADING_RE = re.compile(rf"^({HEADING_ID}):\s*(.*)$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
BOLD_LEAD_RE = re.compile(rf"^\s*(?:[-*]\s+)?\*\*({REQ_ID})\*\*")
RETIRED_RE = re.compile(
    rf"^\s*[-*]\s+~~\s*({HEADING_ID})\s*:?\s*(.*?)~~\s*Retired\s+(\d{{4}}-\d{{2}}-\d{{2}})\s*:?\s*(.*)$")
FIELD_RE = re.compile(r"\*\*([A-Za-z][A-Za-z ]*?):\*\*\s*")


def code_mask(lines: list[str]) -> list[bool]:
    """True for each line that is inside a fenced code block (fence lines included)."""
    mask, fence = [], None
    for line in lines:
        m = FENCE_RE.match(line)
        if fence is None:
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = m.group(1)
                mask.append(True)
                continue
            mask.append(False)
        else:
            mask.append(True)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
                fence = None
    return mask


@dataclass
class Heading:
    line: int          # 0-based index of the heading line
    level: int
    text: str          # heading text without the hashes
    id: str | None = None
    title: str = ""    # text after "<ID>:" for ID headings, else the whole text
    end: int = 0       # exclusive end of the section (next heading of same or higher level)


def headings(lines: list[str], mask: list[bool] | None = None) -> list[Heading]:
    """All headings outside code fences, each with its section end filled in."""
    mask = mask if mask is not None else code_mask(lines)
    out: list[Heading] = []
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        level, text = len(m.group(1)), m.group(2).strip()
        h = Heading(line=i, level=level, text=text, title=text)
        idm = ID_HEADING_RE.match(text)
        if idm and level in (2, 3):
            h.id, h.title = idm.group(1), idm.group(2).strip()
        out.append(h)
    for n, h in enumerate(out):
        h.end = len(lines)
        for later in out[n + 1:]:
            if later.level <= h.level:
                h.end = later.line
                break
    return out


def split_fields(line: str) -> dict[str, str]:
    """`**Key:** value · **Key2:** value2` → {"Key": "value", ...}. Empty dict if the line has no bold key."""
    out: dict[str, str] = {}
    matches = list(FIELD_RE.finditer(line))
    for n, m in enumerate(matches):
        end = matches[n + 1].start() if n + 1 < len(matches) else len(line)
        value = line[m.end():end].strip()
        value = re.sub(r"\s*·\s*$", "", value).strip()
        out[m.group(1).strip()] = value
    return out


def header(lines: list[str]) -> tuple[dict[str, str], int | None, str | None, int | None]:
    """(fields, header line index, H1 title, H1 line index).

    The header is the first non-blank line after the H1 that holds `**Key:** value` pairs.
    """
    title = title_line = None
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == 1:
            title, title_line = m.group(2).strip(), i
            break
    if title_line is None:
        return {}, None, None, None
    for i in range(title_line + 1, len(lines)):
        if not lines[i].strip():
            continue
        fields = split_fields(lines[i])
        return (fields, i, title, title_line) if fields else ({}, None, title, title_line)
    return {}, None, title, title_line


def fields_in(lines: list[str], start: int, end: int) -> dict[str, str]:
    """Bold-key fields on every line of [start, end) that starts with `**Key:**`. Later lines don't override."""
    out: dict[str, str] = {}
    for line in lines[start:end]:
        if line.lstrip().startswith("**"):
            for k, v in split_fields(line).items():
                out.setdefault(k, v)
    return out


def field_line(lines: list[str], start: int, end: int, key: str) -> int | None:
    """Index of the line in [start, end) that holds `**key:**`."""
    pat = f"**{key}:**"
    for i in range(start, end):
        if pat in lines[i]:
            return i
    return None


def table_cells(line: str) -> list[str] | None:
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [c.strip() for c in re.split(r"(?<!\\)\|", s.strip("|"))]


def tables(lines: list[str], start: int = 0, end: int | None = None,
           mask: list[bool] | None = None) -> list[tuple[int, list[str], list[tuple[int, list[str]]]]]:
    """Tables in [start, end): (header line, header cells, [(row line, cells)])."""
    end = len(lines) if end is None else end
    mask = mask if mask is not None else code_mask(lines)
    out = []
    i = start
    while i < end - 1:
        head = table_cells(lines[i]) if not mask[i] else None
        sep = table_cells(lines[i + 1]) if head else None
        if head and sep and all(re.fullmatch(r":?-{2,}:?", c) for c in sep if c):
            rows, j = [], i + 2
            while j < end and not mask[j] and (cells := table_cells(lines[j])) is not None:
                rows.append((j, cells))
                j += 1
            out.append((i, head, rows))
            i = j
        else:
            i += 1
    return out


def table_dicts(head: list[str], rows: list[tuple[int, list[str]]]) -> list[tuple[int, dict[str, str]]]:
    return [(n, {h: (cells[k] if k < len(cells) else "") for k, h in enumerate(head)}) for n, cells in rows]


def expand_refs(text: str) -> list[str]:
    """Requirement-style IDs in text, expanding ranges `STAT-01–STAT-04` and `STAT-01–04`. Order kept, no repeats."""
    out: list[str] = []
    for m in re.finditer(r"\b([A-Z][A-Z0-9]*)-(\d{2,})(?:\s*[–-]\s*(?:\1-)?(\d{2,})\b)?", text):
        pre, a, b = m.group(1), int(m.group(2)), m.group(3)
        width = len(m.group(2))
        hi = int(b) if b else a
        if hi - a > 500:
            hi = a
        for n in range(a, hi + 1):
            rid = f"{pre}-{n:0{width}d}"
            if rid not in out:
                out.append(rid)
    return out


def task_refs(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(rf"\b{TASK_ID}\b", text)))


def split_list(value: str) -> list[str]:
    """Comma-separated field value → items, with backticks and trailing reasons in parens kept."""
    return [s.strip().strip("`") for s in re.split(r",(?![^()]*\))", value) if s.strip()]


def strip_md(value: str) -> str:
    return re.sub(r"[`*]", "", value).strip()


@dataclass
class Checkbox:
    line: int
    checked: bool
    text: str


def checkboxes(lines: list[str], start: int, end: int) -> list[Checkbox]:
    out = []
    for i in range(start, end):
        m = re.match(r"^\s*[-*]\s+\[([ xX])\]\s*(.*)$", lines[i])
        if m:
            out.append(Checkbox(i, m.group(1) in "xX", m.group(2).strip()))
    return out


@dataclass
class Retired:
    id: str
    title: str
    date: str
    reason: str
    line: int


def retired_lines(lines: list[str], mask: list[bool]) -> list[Retired]:
    out = []
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        m = RETIRED_RE.match(line)
        if m:
            out.append(Retired(m.group(1), m.group(2).strip(), m.group(3), m.group(4).strip(), i))
    return out


@dataclass
class BoldLead:
    id: str
    line: int
    end: int           # exclusive: the line plus its indented continuation lines
    removed: bool      # struck through (`~~`) on the line


def bold_leads(lines: list[str], mask: list[bool]) -> list[BoldLead]:
    """Spec-style requirement lines `- **CODE-01** text` with their indented sub-bullets."""
    out = []
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        m = BOLD_LEAD_RE.match(line)
        if not m:
            continue
        indent = len(line) - len(line.lstrip())
        j = i + 1
        while j < len(lines) and lines[j].strip() and (len(lines[j]) - len(lines[j].lstrip())) > indent \
                and not BOLD_LEAD_RE.match(lines[j]):
            j += 1
        out.append(BoldLead(m.group(1), i, j, "~~" in line))
    return out


@dataclass
class Fence:
    start: int
    end: int           # line of the closing fence (or last line if unclosed)
    info: str


def fences(lines: list[str]) -> list[Fence]:
    out, start, fence, info = [], None, "", ""
    for i, line in enumerate(lines):
        m = FENCE_RE.match(line)
        if start is None:
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                start, fence, info = i, m.group(1), m.group(2).strip()
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
            out.append(Fence(start, i, info))
            start = None
    if start is not None:
        out.append(Fence(start, len(lines) - 1, info))
    return out

