#!/usr/bin/env python3
"""Report what architecture-design needs before it starts, as JSON.

- mode: blocked | new | extend | current
- spec status, architecture status and shape
- uncovered: live spec requirement IDs not referenced by any architecture doc
- changed_since: requirements the architecture already places that a pending spec Changelog row marks "(changed)"
- spec_rows_pending: spec Changelog rows the architecture hasn't caught up with (see below)
- stale: IDs the architecture references that are removed from, or missing in, the spec
- next_decision: next free AD-NN
- package_docs / packages_found: documented packages vs package manifests found in the repo (for Sync and Grow)
- skills: other skills installed in this project (.claude/skills), which may own steps the design must route to
- broken_fences: doc:line of each code fence that leaves doc text inside a code block: one whose block holds a
  heading (a stray fence, often closing lines added below a block's real closing fence) or one that never closes

A spec Changelog row is pending if it is dated after the architecture's Last updated date. Rows dated
that same day are told apart by order: they are pending if they come after the last spec row that the
architecture's Changelog acknowledges. An architecture row acknowledges a spec row by citing its source
file (ideas/<slug>.md or brief.md) in Source or, for a spec row with no source file, by listing all of its
IDs with the same marks. Spec rows are matched in order and each citation is used once, so a second spec
row from the same idea file stays pending until a later architecture row cites that file again.

Usage: python3 skills/architecture-design/scripts/arch-status.py [docs_dir] [repo_root]
"""
import json, os, re, sys

docs = sys.argv[1] if len(sys.argv) > 1 else "docs"
root = sys.argv[2] if len(sys.argv) > 2 else "."
spec_p = os.path.join(docs, "spec.md")
arch_p = os.path.join(docs, "architecture.md")
pkg_dir = os.path.join(docs, "architecture")

ID = r"[A-Z][A-Z0-9]*-\d{2,}"

def read(p):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None

def field(text, name):
    m = re.search(r"\*\*%s:\*\*\s*([^·\n]+)" % re.escape(name), text or "")
    return m.group(1).strip() if m else None

def refs(text):
    """IDs referenced in text, expanding ranges like ENV-01–ENV-04 or ENV-01–04."""
    out = set()
    for m in re.finditer(r"\b([A-Z][A-Z0-9]*)-(\d{2,})(?:\s*[–-]\s*(?:\1-)?(\d{2,}))?", text):
        pre, a, b = m.group(1), int(m.group(2)), m.group(3)
        width = len(m.group(2))
        for n in range(a, (int(b) if b else a) + 1):
            out.add(f"{pre}-{n:0{width}d}")
    return out

def marked_ids(cell):
    """{ID: added|changed|removed} for a Changelog IDs cell. A "(changed)" or "(removed)" mark covers the
    unmarked IDs before it in its ;-separated group: "TANK-01–TANK-12; QR-03, CORE-04 (changed)"."""
    out = {}
    for group in re.split(r";(?![^()]*\))", cell):
        run = set()
        for item in re.split(r",(?![^()]*\))", group):
            run |= refs(re.sub(r"\([^)]*\)", "", item))
            mark = re.search(r"\((changed|removed)\b", item, re.I)
            if mark:
                out.update(dict.fromkeys(run, mark.group(1).lower()))
                run = set()
        for r in run:
            out.setdefault(r, "added")
    return out

def changelog(text):
    """Rows of a doc's Changelog table: date, change, source, the .md files the source cites, and marked IDs."""
    m = re.search(r"^## Changelog[^\n]*$(.*?)(?=^## |\Z)", text or "", re.S | re.M)
    rows = []
    for line in (m.group(1) if m else "").splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if len(cells) < 4 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
            continue
        cited = {re.sub(r"^(\.\./|docs/)+", "", f) for f in re.findall(r"[\w./-]+\.md", cells[-2])}
        rows.append({"date": cells[0], "change": " | ".join(cells[1:-2]), "source": cells[-2],
                     "files": cited - {"spec.md", "architecture.md"}, "ids": marked_ids(cells[-1])})
    return rows

def broken_fences(text):
    """Line numbers of code fences that never close, or that open a block holding a ##–#### heading
    (a block tagged markdown may hold headings)."""
    out, start, fence, md, held = [], None, "", False, False
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r"\s*(`{3,}|~{3,})(.*)", line)
        if start is None:
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                start, fence, held = n, m.group(1), False
                md = bool(re.match(r"\s*(markdown|md)\b", m.group(2), re.I))
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
            out += [start] if held else []
            start = None
        elif not md and re.match(r"#{2,4} \S", line):
            held = True
    return out + ([start] if start else [])

def pending_rows(spec_rows, arch_rows, updated):
    """Spec Changelog rows with IDs that the architecture hasn't caught up with."""
    cites = [(a["files"], {i: m for i, m in a["ids"].items() if not i.startswith("AD-")}) for a in arch_rows]
    j, last = 0, -1  # j: architecture row of the previous acknowledgment; last: index of that spec row
    for n, row in enumerate(spec_rows):
        if not row["ids"]:
            continue
        for k in range(j, len(cites)):
            files, ids = cites[k]
            if (row["files"] & files) if row["files"] else (row["ids"].items() <= ids.items()):
                files -= row["files"]
                for i in row["ids"]:
                    ids.pop(i, None)
                j, last = k, n
                break

    def pending(n, row):
        if updated and row["date"] != updated:
            return row["date"] > updated
        return n > last
    return [r for n, r in enumerate(spec_rows) if r["ids"] and pending(n, r)]

spec = read(spec_p)
if spec is None:
    print("No docs/spec.md — run spec-writing first.", file=sys.stderr)
    print(json.dumps({"mode": "blocked", "reason": "no spec"}))
    sys.exit(0)

live, removed = set(), set()
for line in spec.splitlines():
    m = re.search(r"\*\*(%s)\*\*" % ID, line)
    if m:
        (removed if "~~" in line else live).add(m.group(1))

arch = read(arch_p)
pkg_docs = sorted(f for f in os.listdir(pkg_dir) if f.endswith(".md")) if os.path.isdir(pkg_dir) else []
arch_docs = ([(arch_p, arch)] if arch else []) + [(p, read(p) or "") for p in (os.path.join(pkg_dir, f) for f in pkg_docs)]
arch_texts = [t for _, t in arch_docs]
referenced = set().union(*(refs(t) for t in arch_texts)) if arch_texts else set()
decisions = {r for r in referenced if r.startswith("AD-")}
referenced -= decisions

ignore = {"node_modules", ".venv", "venv", ".git", "dist", "build", "__pycache__", ".tox"}
manifests = {"pyproject.toml", "setup.py", "package.json", "Cargo.toml", "go.mod"}
found = []
for d, subdirs, files in os.walk(root):
    subdirs[:] = [s for s in subdirs if s not in ignore and not s.startswith(".")]
    if d.count(os.sep) - root.count(os.sep) > 4:
        subdirs[:] = []
    if manifests & set(files):
        found.append(os.path.relpath(d, root))

skills_dir = os.path.join(root, ".claude", "skills")
own = {"idea-refine", "spec-writing", "architecture-design"}
skills = sorted(s for s in os.listdir(skills_dir)
                if s not in own and os.path.isfile(os.path.join(skills_dir, s, "SKILL.md"))) if os.path.isdir(skills_dir) else []

updated = field(arch, "Last updated") if arch else None
uncovered = sorted(live - referenced)
pending = pending_rows(changelog(spec), changelog(arch), updated)
changed = {i for r in pending for i, m in r["ids"].items() if m == "changed"}
changed_since = sorted(changed & live & referenced)
prefixes = {r.split("-")[0] for r in live | removed}
stale = sorted(r for r in referenced if r.split("-")[0] in prefixes and r not in live)
nums = [int(r.split("-")[1]) for r in decisions]

if arch is None:
    mode = "new"
elif uncovered or changed_since:
    mode = "extend"
else:
    mode = "current"

report = {
    "mode": mode,
    "spec": {"path": spec_p, "status": field(spec, "Status"), "live_requirements": len(live)},
    "architecture": {"path": arch_p, "exists": arch is not None,
                     "status": field(arch, "Status"), "shape": field(arch, "Shape"), "last_updated": updated},
    "uncovered": uncovered,
    "changed_since": changed_since,
    "spec_rows_pending": [f"{r['date']} | {r['change']} | {r['source']}" for r in pending],
    "stale": stale,
    "next_decision": f"AD-{(max(nums) + 1) if nums else 1:02d}",
    "package_docs": pkg_docs,
    "packages_found": sorted(found),
    "skills": skills,
    "broken_fences": [f"{p}:{n}" for p, t in arch_docs for n in broken_fences(t)],
}
print(f"Mode: {mode} (spec: {report['spec']['status']}, architecture: {report['architecture']['status']}, "
      f"uncovered: {len(uncovered)}, broken fences: {len(report['broken_fences'])})", file=sys.stderr)
print(json.dumps(report, indent=2))
