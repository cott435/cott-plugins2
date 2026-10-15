#!/usr/bin/env python3
"""Report what architecture-design needs before it starts, as JSON.

- mode: blocked | new | extend | current
- spec status, architecture status and shape
- uncovered: live spec requirement IDs not referenced by any architecture doc
- changed_since: spec IDs marked "(changed YYYY-MM-DD)" after the architecture's Last updated date
- stale: IDs the architecture references that are removed from, or missing in, the spec
- next_decision: next free AD-NN
- package_docs / packages_found: documented packages vs package manifests found in the repo (for Sync and Grow)
- skills: other skills installed in this project (.claude/skills), which may own steps the design must route to

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

spec = read(spec_p)
if spec is None:
    print("No docs/spec.md — run spec-writing first.", file=sys.stderr)
    print(json.dumps({"mode": "blocked", "reason": "no spec"}))
    sys.exit(0)

live, removed, changed = set(), set(), {}
for line in spec.splitlines():
    m = re.search(r"\*\*(%s)\*\*" % ID, line)
    if not m:
        continue
    rid = m.group(1)
    if "~~" in line:
        removed.add(rid)
    else:
        live.add(rid)
        c = re.search(r"\(changed (\d{4}-\d{2}-\d{2})\)", line)
        if c:
            changed[rid] = c.group(1)

arch = read(arch_p)
pkg_docs = sorted(f for f in os.listdir(pkg_dir) if f.endswith(".md")) if os.path.isdir(pkg_dir) else []
arch_texts = ([arch] if arch else []) + [read(os.path.join(pkg_dir, f)) or "" for f in pkg_docs]
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
changed_since = sorted(r for r, d in changed.items() if updated and d > updated)
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
    "stale": stale,
    "next_decision": f"AD-{(max(nums) + 1) if nums else 1:02d}",
    "package_docs": pkg_docs,
    "packages_found": sorted(found),
    "skills": skills,
}
print(f"Mode: {mode} (spec: {report['spec']['status']}, architecture: {report['architecture']['status']}, "
      f"uncovered: {len(uncovered)})", file=sys.stderr)
print(json.dumps(report, indent=2))
