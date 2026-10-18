"""The user's own words (`docs/requests.md`, design/requests.md): one `UR-NN` line per concrete statement, written
only by `dt request`. A line's words never change; its trace after `→` names the IDs that honour it, a change the
user approved, or the later request that replaced it. Used by `dt request`, `dt status`, `dt next` and lint."""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field

from . import edit, md
from .repo import Doc, Repo

PATH = "docs/requests.md"
ID = r"UR-\d{2,}"
# Owner (the doc that must honour a request) → the skill that writes that doc.
OWNERS = {"brief": "idea-refine", "spec": "spec-writing", "architecture": "architecture-design", "pipelines": "pipeline-design",
          "tests": "test-planning", "plan": "build-planning", "constraints": "build-setup"}
# The doc kinds whose live IDs, or sections (`§Out of scope`), can honour an owner's request.
HONOUR_KINDS = {"brief": ("brief", "idea"), "spec": ("spec",), "architecture": ("architecture", "package-architecture", "contract"),
                "pipelines": ("pipelines",), "tests": ("tests",), "plan": ("plan", "queued-plan"),
                "constraints": ("constraints",)}
# Owners whose open requests fail `dt lint` once their doc is Approved, and send `dt next` back to their skill.
DUE_WHEN_APPROVED = {"spec": "docs/spec.md", "architecture": "docs/architecture.md"}

LEAD = re.compile(rf"^\s*[-*]\s+\*\*({ID})\*\*")
LINE = re.compile(rf'^\s*[-*]\s+\*\*(?P<id>{ID})\*\*\s+(?P<owner>[a-z]+)\s+·\s+"(?P<words>.*?)"'
                  r"(?:\s+\[(?P<about>[^\]]*)\])?\s+·\s+(?P<skill>[a-z-]+)\s+(?P<date>\d{4}-\d{2}-\d{2})"
                  r"(?:\s+→\s+(?P<trace>.*?))?\s*$")
CHANGED = re.compile(r'^changed:\s*(?P<what>.+?)\s+\(approved\s+"(?P<words>.+)",\s+(?P<skill>[a-z-]+)\s+'
                     r"(?P<date>\d{4}-\d{2}-\d{2})(?:;\s*in\s+(?P<into>[^()]+?))?\)$")
SUPERSEDED = re.compile(rf"^superseded by (?P<by>{ID})$")


@dataclass
class Request:
    id: str
    line: int             # 0-based
    owner: str
    words: str
    about: str
    skill: str
    date: str
    trace: str            # the text after `→`, "" when untraced
    honoured_by: list[str]
    changed: str          # what was done instead, when the user approved a change
    approval: str         # the user's words approving it
    superseded_by: str
    into: list[str] = field(default_factory=list)   # the IDs a change was written into
    changed_by: tuple[str, str] = ("", "")             # the skill and date of the approval

    @property
    def fixed(self) -> tuple[str, str, str, str]:
        """What never changes once written: the words, the context, who heard them and when."""
        return self.words, self.about, self.skill, self.date

    @property
    def state(self) -> str:
        if self.superseded_by:
            return "superseded"
        if self.changed:
            return "changed"
        return "traced" if self.honoured_by else "open"


@dataclass
class Bad:
    line: int
    id: str
    message: str


def parse(doc: Doc | None) -> tuple[list[Request], list[Bad]]:
    """The doc's UR lines, and the ones that don't parse."""
    out: list[Request] = []
    bad: list[Bad] = []
    if doc is None:
        return out, bad
    for i, text in enumerate(doc.lines):
        lead = LEAD.match(text)
        if doc.mask[i] or not lead:
            continue
        m = LINE.match(text)
        if not m:
            bad.append(Bad(i, lead.group(1), 'not `- **UR-NN** <owner> · "<words>" [<context>] · <skill> <date>'
                                             ' → <trace>`'))
            continue
        if m["owner"] not in OWNERS:
            bad.append(Bad(i, m["id"], f"owner {m['owner']!r} is not one of {', '.join(OWNERS)}"))
            continue
        trace = (m["trace"] or "").strip()
        honoured, changed, approval, by, into, changed_by = [], "", "", "", [], ("", "")
        if trace:
            c, s = CHANGED.match(trace), SUPERSEDED.match(trace)
            if c:
                changed, approval, changed_by = c["what"].strip(), c["words"], (c["skill"], c["date"])
                into = [md.strip_md(x) for x in md.split_list(c["into"])] if c["into"] else []
            elif s:
                by = s["by"]
            else:
                items = [md.strip_md(x) for x in md.split_list(trace)]
                if trace.startswith("changed") or not all(re.fullmatch(md.HEADING_ID, x) or is_section(x)
                                                          for x in items):
                    bad.append(Bad(i, m["id"], 'trace is not IDs, `changed: <what> (approved "<words>", <skill> '
                                               '<date>)` or `superseded by UR-NN`'))
                    continue
                honoured = items
        out.append(Request(m["id"], i, m["owner"], m["words"], (m["about"] or "").strip(), m["skill"], m["date"],
                           trace, honoured, changed, approval, by, into, changed_by))
    return out, bad


def is_section(item: str) -> bool:
    """A trace item naming a section of the owner's doc by its heading: `§Out of scope`."""
    return item.startswith("§") and bool(item[1:].strip())


def section_docs(repo: Repo, owner: str, item: str) -> list[Doc]:
    """The owner's docs with a heading whose text is the item's (case and markup ignored)."""
    want = md.strip_md(item[1:]).strip().lower()
    return [d for d in repo.docs(*HONOUR_KINDS[owner])
            if any(md.strip_md(h.text).strip().lower() == want for h in d.headings)]


def resolves(repo: Repo, owner: str, item: str) -> bool:
    if is_section(item):
        return bool(section_docs(repo, owner, item))
    return repo.lookup(item, archive=False) is not None


def all_requests(repo: Repo) -> list[Request]:
    return parse(repo.doc(PATH))[0]


def honouring(repo: Repo, r: Request) -> list[str]:
    """The trace items that are live definitions, or sections, in a doc its owner writes."""
    kinds = HONOUR_KINDS[r.owner]
    out = []
    for id_ in r.honoured_by:
        if is_section(id_):
            if section_docs(repo, r.owner, id_):
                out.append(id_)
            continue
        d = repo.lookup(id_, archive=False)
        if d is not None and not d.retired and d.doc.kind in kinds:
            out.append(id_)
    return out


def is_open(repo: Repo, r: Request) -> bool:
    """Neither honoured by a live ID of its owner's docs, nor changed with approval, nor replaced."""
    return r.state not in ("changed", "superseded") and not honouring(repo, r)


def open_requests(repo: Repo, owner: str | None = None) -> list[Request]:
    return [r for r in all_requests(repo) if (owner is None or r.owner == owner) and is_open(repo, r)]


def due(repo: Repo, owner: str) -> list[Request]:
    """Open requests of an owner whose doc is Approved: `dt lint` fails them and `dt next` routes them."""
    rel = DUE_WHEN_APPROVED.get(owner)
    doc = repo.doc(rel) if rel else None
    if doc is None or not (doc.status or "").startswith("Approved"):
        return []
    return open_requests(repo, owner)


def owner_of(skill: str) -> str | None:
    return next((o for o, s in OWNERS.items() if s == skill), None)


def label(r: Request) -> str:
    return f'{r.id} "{r.words}"' + (f" [{r.about}]" if r.about else "")


def open_for(repo: Repo, skill: str) -> list[str]:
    """The skill's open requests, `UR-NN "<words>" [<context>]`, for `dt status`."""
    owner = owner_of(skill)
    return [label(r) for r in open_requests(repo, owner)] if owner else []


# ---- writing (dt request) ---------------------------------------------------------------------------

INTRO = ("The user's words, verbatim: one line per fact, constraint, tool, choice or answer, with the skill that "
         "heard it and the date. The words never change; only the trace after → does. Written with `dt request`.\n")


def render(r: Request) -> str:
    about = f" [{r.about}]" if r.about else ""
    trace = f" → {r.trace}" if r.trace else ""
    return f'- **{r.id}** {r.owner} · "{r.words}"{about} · {r.skill} {r.date}{trace}'


def _today() -> str:
    return datetime.date.today().isoformat()


def _write(repo: Repo, lines: list[str]) -> None:
    doc = repo.doc(PATH)
    if doc is not None and doc.header_line is not None:
        lines[doc.header_line] = re.sub(r"(\*\*Last updated:\*\*\s*)\d{4}-\d{2}-\d{2}", rf"\g<1>{_today()}",
                                        lines[doc.header_line])
    edit.write_lines(repo.root / PATH, lines)
    repo.reload(PATH)


def add(repo: Repo, owner: str, words: str, skill: str, about: str = "") -> Request:
    """Append a request (creating the doc on first use); returns it."""
    path = repo.root / PATH
    r = Request(repo.next_id("UR"), 0, owner, words, about, skill, _today(), "", [], "", "", "")
    if path.is_file():
        lines = edit.ensure_eol(edit.read_lines(path))
        lines.append(render(r) + edit.eol(lines))
        _write(repo, lines)
    else:
        brief = repo.doc("docs/brief.md")
        name = re.sub(r"\s*—\s*Brief$", "", brief.title or "") if brief else ""
        title = f"# {name} — User requests" if name else "# User requests"
        edit.write_text(path, f"{title}\n\n**Last updated:** {_today()}\n\n{INTRO}\n{render(r)}\n")
        repo.reload(PATH)
    return r


def set_trace(repo: Repo, r: Request, trace: str) -> None:
    lines = edit.read_lines(repo.root / PATH)
    ending = lines[r.line][len(lines[r.line].rstrip("\r\n")):]
    r.trace = trace
    lines[r.line] = render(r) + ending
    _write(repo, lines)


def changed_trace(what: str, approval: str, skill: str, into: list[str], date: str = "") -> str:
    return f'changed: {what} (approved "{approval}", {skill} {date or _today()}; in {", ".join(into)})'


# ---- numbers (request-number, request-source) ------------------------------------------------------

WORDS = {w: float(n) for n, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve "
                                           "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"
                                           .split())} | {"thirty": 30.0, "forty": 40.0, "fifty": 50.0,
                                                         "hundred": 100.0, "thousand": 1000.0, "dozen": 12.0}
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
MARKER = re.compile(r"(?:^|(?<=\s))\d+[.)](?=\s)")
NUMBER = re.compile(r"(?<![\w.\-])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?![\w-]*\d)\s*(%|k\b|hours?\b|hrs?\b|h\b|"
                    r"minutes?\b|mins?\b)?", re.I)
NUMBER_WORD = re.compile(r"\b(" + "|".join(WORDS) + r")\b(?:\s+(hours?|minutes?))?", re.I)


def numbers(text: str) -> list[tuple[str, set[float], str]]:
    """Each number stated in the text, as written, with the values it may appear as elsewhere (an hour is also 60
    minutes, 5% is also 0.05, 2k is 2000) and its kind: "time" for hours and minutes, else "". IDs (AD-03, S2),
    dates and list markers are not numbers."""
    text = MARKER.sub(" ", DATE.sub(" ", text))
    out = []
    for m in NUMBER.finditer(text):
        unit = (m.group(2) or "").lower()
        out.append((m.group(0).strip(), _values(float(m.group(1).replace(",", "")), unit), _kind(unit)))
    for m in NUMBER_WORD.finditer(text):
        unit = (m.group(2) or "").lower()
        out.append((m.group(0), _values(WORDS[m.group(1).lower()], unit), _kind(unit)))
    return out


def _kind(unit: str) -> str:
    return "time" if unit[:1] in ("h", "m") else ""


def _values(v: float, unit: str) -> set[float]:
    if unit == "%":
        return {v, v / 100}
    if unit == "k":
        return {v * 1000}
    if unit.startswith("h"):
        return {v, v * 60}
    if unit.startswith("m"):
        return {v, v / 60}
    return {v}


def unstated(text: str, sources: list[str]) -> list[str]:
    """The numbers in the text that none of the sources states. A time (an hour, 90 minutes) matches only a time."""
    have = [(vals, kind) for src in sources for _, vals, kind in numbers(src)]
    return [shown for shown, vals, kind in numbers(text)
            if not any((not kind or k == kind) and any(abs(v - h) < 1e-9 for v in vals for h in hv)
                       for hv, k in have)]


def definition_text(repo: Repo, id_: str) -> str:
    d = repo.lookup(id_, archive=False)
    return "" if d is None or d.retired else "\n".join(d.doc.lines[d.start:d.end])


def stated(repo: Repo, r: "Request") -> str:
    """What a request asks for now: its words, or what the user approved instead, or its replacement's."""
    seen = set()
    while r.superseded_by and r.id not in seen:
        seen.add(r.id)
        r = next((x for x in all_requests(repo) if x.id == r.superseded_by), r)
    return r.changed or r.words
