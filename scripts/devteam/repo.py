"""A project's planning docs: which files they are, what kind each is, and every ID they define.

`Repo(root)` reads the doc map once. Commands ask it for docs by kind and for ID definitions; they never
glob or open docs themselves, so every command sees the same IDs, statuses and sections.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from . import md

# Doc kinds by repo-relative path. First match wins.
KINDS = [
    (r"docs/brief\.md", "brief"),
    (r"docs/ideas/[^/]+\.md", "idea"),
    (r"docs/roadmap\.md", "roadmap"),
    (r"docs/spec\.md", "spec"),
    (r"docs/architecture\.md", "architecture"),
    (r"docs/packages/[^/]+/architecture\.md", "package-architecture"),
    (r"docs/architecture/[^/]+\.md", "package-architecture"),   # legacy layout, before §5.1
    (r"docs/packages/[^/]+/contract\.md", "contract"),
    (r"docs/packages/[^/]+/pipelines\.md", "pipelines"),
    (r"docs/packages/[^/]+/tests\.md", "tests"),
    (r"docs/references\.md", "references"),
    (r"CONSTRAINTS\.md", "constraints"),
    (r"(AGENTS|CLAUDE)\.md", "agents"),
    (r"tasks/plan\.md", "plan"),
    (r"tasks/todo\.md", "todo"),
    (r"tasks/queued/[^/]+\.md", "queued-plan"),
    (r"tasks/archive/[^/]+\.md", "archived-plan"),
]

# Doc kinds whose IDs are part of the live doc map. Archived plans are read only for next-id and lookups.
ARCHIVE_KINDS = {"archived-plan"}


def kind_of(rel: str) -> str | None:
    rel = rel.replace(os.sep, "/")
    for pat, kind in KINDS:
        if re.fullmatch(pat, rel):
            return kind
    return None


def package_of(rel: str) -> str | None:
    m = re.match(r"docs/packages/([^/]+)/", rel) or re.match(r"docs/architecture/([^/]+)\.md$", rel)
    return m.group(1) if m else None


@dataclass
class Definition:
    """Where an ID is defined: a heading section, a bold-led requirement line, a table row or a retired line."""
    id: str
    doc: "Doc"
    start: int            # 0-based first line
    end: int              # exclusive
    how: str              # heading | requirement | table | retired | finding
    title: str = ""
    retired: bool = False
    retired_note: str = ""   # "Retired 2026-11-02: reason" or "Superseded by AD-07 · …"

    @property
    def text(self) -> str:
        return "\n".join(self.doc.lines[self.start:self.end]).rstrip() + "\n"

    @property
    def where(self) -> str:
        return f"{self.doc.rel}:{self.start + 1}"


class Doc:
    def __init__(self, root: Path, rel: str, text: str | None = None):
        self.root = root
        self.rel = rel.replace(os.sep, "/")
        self.path = root / rel
        self.kind = kind_of(self.rel)
        self.package = package_of(self.rel)
        self.text = text if text is not None else self.path.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()
        self.mask = md.code_mask(self.lines)
        self.header, self.header_line, self.title, self.title_line = md.header(self.lines)
        self.headings = md.headings(self.lines, self.mask)

    def __repr__(self) -> str:
        return f"Doc({self.rel!r}, kind={self.kind!r})"

    @property
    def status(self) -> str | None:
        return self.header.get("Status")

    @property
    def last_updated(self) -> str | None:
        return self.header.get("Last updated")

    def heading(self, id_or_text: str) -> md.Heading | None:
        for h in self.headings:
            if h.id == id_or_text or h.text == id_or_text:
                return h
        return None

    def section_text(self, h: md.Heading) -> str:
        return "\n".join(self.lines[h.line:h.end]).rstrip() + "\n"

    def headings_under(self, parent: md.Heading) -> list[md.Heading]:
        return [h for h in self.headings if parent.line < h.line < parent.end]

    def prebuild_sections(self) -> list[md.Heading]:
        return [h for h in self.headings if "(pre-build" in h.text]

    def tables(self, start: int = 0, end: int | None = None):
        return md.tables(self.lines, start, end, self.mask)

    def definitions(self) -> list[Definition]:
        """Every ID this doc defines, in line order."""
        out: list[Definition] = []
        for h in self.headings:
            if not h.id:
                continue
            d = Definition(h.id, self, h.line, h.end, "heading", h.title)
            # Superseded decisions: `### AD-02: ~~Old title~~` + `**Status:** Superseded by AD-07 · …`
            if "~~" in h.title:
                d.retired = True
                status = md.fields_in(self.lines, h.line + 1, min(h.end, h.line + 3)).get("Status", "")
                d.retired_note = status or "struck"
            out.append(d)
        for r in md.retired_lines(self.lines, self.mask):
            out.append(Definition(r.id, self, r.line, r.line + 1, "retired", r.title, True,
                                  f"Retired {r.date}: {r.reason}"))
        if self.kind == "spec":
            for b in md.bold_leads(self.lines, self.mask):
                out.append(Definition(b.id, self, b.line, b.end, "requirement",
                                      retired=b.removed, retired_note="removed" if b.removed else ""))
        if self.kind == "constraints":
            for b in md.bold_leads(self.lines, self.mask):
                if b.id.startswith("CR-"):
                    out.append(Definition(b.id, self, b.line, b.end, "requirement"))
            for _, head, rows in self.tables():
                for n, cells in rows:
                    if cells and re.fullmatch(r"CR-\d{2,}", cells[0]):
                        out.append(Definition(cells[0], self, n, n + 1, "table"))
        if self.kind in ("plan", "queued-plan", "archived-plan"):
            for i, line in enumerate(self.lines):
                m = re.match(rf"^\s*[-*]\s+({md.FINDING_ID})\b\s*(.*)$", line)
                if m and not self.mask[i]:
                    out.append(Definition(m.group(1), self, i, i + 1, "finding", m.group(2)))
        out.sort(key=lambda d: d.start)
        return out


IGNORE_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", "dist", "build"}


class Repo:
    def __init__(self, root: str | Path = "."):
        self.root = Path(root).resolve()
        self._docs: dict[str, Doc] = {}
        self.unreadable: list[str] = []      # doc-map paths that couldn't be read as UTF-8 text
        for rel in self._doc_paths():
            try:
                self._docs[rel] = Doc(self.root, rel)
            except (OSError, UnicodeDecodeError):
                self.unreadable.append(rel)

    def _doc_paths(self) -> list[str]:
        out = []
        for top in ("docs", "tasks"):
            base = self.root / top
            if not base.is_dir():
                continue
            for d, subdirs, files in os.walk(base):
                subdirs[:] = sorted(s for s in subdirs if s not in IGNORE_DIRS)
                for f in sorted(files):
                    if f.endswith(".md"):
                        rel = os.path.relpath(os.path.join(d, f), self.root).replace(os.sep, "/")
                        if kind_of(rel):
                            out.append(rel)
        for f in ("CONSTRAINTS.md", "AGENTS.md", "CLAUDE.md"):
            if (self.root / f).is_file():
                out.append(f)
        return out

    # ---- docs -------------------------------------------------------------------------------

    def doc(self, rel: str) -> Doc | None:
        return self._docs.get(rel)

    def docs(self, *kinds: str, archive: bool = False) -> list[Doc]:
        """Docs of the given kinds (all kinds if none), archive excluded unless asked for."""
        return [d for d in self._docs.values()
                if (not kinds or d.kind in kinds) and (archive or d.kind not in ARCHIVE_KINDS)]

    def reload(self, rel: str) -> Doc | None:
        """Re-read one doc after a mechanical edit."""
        self.__dict__.pop("index", None)
        self.__dict__.pop("all_definitions", None)
        if (self.root / rel).is_file():
            self._docs[rel] = Doc(self.root, rel)
        else:
            self._docs.pop(rel, None)
        return self._docs.get(rel)

    @property
    def spec(self) -> Doc | None:
        return self.doc("docs/spec.md")

    @property
    def architecture(self) -> Doc | None:
        return self.doc("docs/architecture.md")

    @property
    def roadmap(self) -> Doc | None:
        return self.doc("docs/roadmap.md")

    @property
    def references(self) -> Doc | None:
        return self.doc("docs/references.md")

    @property
    def plan(self) -> Doc | None:
        return self.doc("tasks/plan.md")

    @property
    def todo(self) -> Doc | None:
        return self.doc("tasks/todo.md")

    @property
    def constraints(self) -> Doc | None:
        return self.doc("CONSTRAINTS.md")

    def packages(self) -> list[str]:
        """Package ids that have a docs/packages/<pkg>/ folder."""
        base = self.root / "docs" / "packages"
        return sorted(p.name for p in base.iterdir() if p.is_dir()) if base.is_dir() else []

    def package_doc(self, pkg: str, name: str) -> Doc | None:
        return self.doc(f"docs/packages/{pkg}/{name}.md")

    # ---- IDs --------------------------------------------------------------------------------

    @cached_property
    def all_definitions(self) -> list[Definition]:
        """Every definition in every doc, archive included."""
        out = []
        for d in self._docs.values():
            out.extend(d.definitions())
        return out

    @cached_property
    def index(self) -> dict[str, list[Definition]]:
        """ID → its definitions in live docs (more than one live, non-retired definition is a duplicate)."""
        out: dict[str, list[Definition]] = {}
        for d in self.all_definitions:
            if d.doc.kind not in ARCHIVE_KINDS:
                out.setdefault(d.id, []).append(d)
        return out

    def lookup(self, id_: str, archive: bool = True) -> Definition | None:
        """The live definition of an ID; a retired line if that's all there is; the archive as a fallback."""
        defs = self.index.get(id_, [])
        live = [d for d in defs if not d.retired]
        if live:
            return live[0]
        if defs:
            return defs[0]
        if archive:
            for d in self.all_definitions:
                if d.id == id_:
                    return d
        return None

    def is_retired(self, id_: str) -> bool:
        defs = self.index.get(id_, [])
        return bool(defs) and all(d.retired for d in defs)

    def ids_with_prefix(self, prefix: str, archive: bool = True) -> list[str]:
        """Every ID ever defined with this prefix (`PL`, `TC`, `AD`, `M2-T`, `M2-R`, `M`), retired included."""
        defs = self.all_definitions if archive else [d for v in self.index.values() for d in v]
        if prefix == "M":
            pat = re.compile(r"M(\d+)$")
        elif re.fullmatch(r"M\d+-[TR]", prefix):
            pat = re.compile(re.escape(prefix) + r"(\d{2,})$")
        else:
            pat = re.compile(re.escape(prefix) + r"-(\d{2,})$")
        found = {d.id for d in defs if pat.match(d.id)}
        # Roadmap rows and todo lines name milestones and tasks that may not have sections yet.
        if prefix == "M" or re.fullmatch(r"M\d+-T", prefix):
            for doc in self.docs("roadmap", "todo") + self.docs("archived-plan", archive=True):
                for tok in re.findall(r"\b(M\d+(?:-T\d{2,})?)\b", doc.text):
                    if pat.match(tok):
                        found.add(tok)
        return sorted(found, key=lambda s: int(pat.match(s).group(1)))

    def next_id(self, prefix: str) -> str:
        ids = self.ids_with_prefix(prefix)
        pat = re.compile(r"(\d+)$")
        n = max((int(pat.search(i).group(1)) for i in ids), default=0) + 1
        if prefix == "M":
            return f"M{n}"
        if re.fullmatch(r"M\d+-[TR]", prefix):
            return f"{prefix}{n:02d}"
        return f"{prefix}-{n:02d}"

    # ---- git --------------------------------------------------------------------------------

    @cached_property
    def is_git(self) -> bool:
        return (self.root / ".git").exists()
