#!/usr/bin/env python3
"""Size and history-residue stats for one run's final planning docs, as JSON.

Measures what eval iteration 1 found growing in incremental runs: total words, struck
(removed) requirements and how long they stay, "(changed ...)" markers, superseded
decisions kept in full, Risks size, and the size of the docs past the architecture (pipelines, test plans,
contracts, build plans, CONSTRAINTS.md) against their per-unit line budgets: the ones `dt lint` applies to contracts
(per symbol, types included), pipelines (per pipeline, plus the pre-build layout) and test plans (per case), and the
grader's per-task budget for build plans (grade.py `doc_budgets`).

Usage: docstats.py <docs-dir>   (a project's docs/, or a dir of final__*.md files from package.py)
"""
import json, re, sys, pathlib

d = pathlib.Path(sys.argv[1])


def load(name):
    """Text of docs/<name>, or of final__<name with / as __> in a packaged outputs dir."""
    for p in (d / name, d / ("final__" + name.replace("/", "__"))):
        if p.exists():
            return p.read_text()
    return ""


def globbed(sub):
    hits = sorted((d / sub).glob("*.md")) if (d / sub).is_dir() else sorted(d.glob(f"final__{sub}__*.md"))
    return [p.read_text() for p in hits]


def matching(docs_glob, final_glob, root=None):
    """(name, text) of docs matching a glob under docs/ (or root), or the packaged final__ equivalent."""
    hits = sorted((root or d).glob(docs_glob)) or sorted(d.glob(final_glob))
    return [(p.name if p.name.startswith("final__") else str(p.relative_to(root or d)), p.read_text()) for p in hits]


def words(t):
    return len(t.split())


def id_count(text):
    """IDs named in text, counting a range like AB-01–AB-05 as five."""
    return sum(int(b[-2:]) - int(a[-2:]) + 1 if b else 1
               for a, b in re.findall(r"\b([A-Z][A-Z0-9]*-\d{2,})(?:\s*[–-]\s*([A-Z][A-Z0-9]*-\d{2,}))?", text))


def section(t, heading):
    m = re.search(rf"^## {heading}.*?$(.*?)(?=^## |\Z)", t, re.S | re.M)
    return m.group(1) if m else ""


brief, spec, arch = load("brief.md"), load("spec.md"), load("architecture.md")
pkgs = globbed("architecture") + [t for _, t in matching("packages/*/architecture.md", "final__packages__*__architecture.md")]
ideas = globbed("ideas")
# Per-unit line budgets: (lines per unit, allowance, unit heading pattern). Contracts, pipelines and test plans as
# `dt lint` budgets them; plans per task plus one line per dependency-graph row, as grade.py's doc_budgets does.
UNIT_BUDGETS = {"contract": (8, 12, r"^### [a-z][\w-]*(?:\.\w+)+:"), "pipelines": (35, 10, r"^## PL-\d{2,}:(?!.*~~)"),
                "tests": (10, 15, r"^### TC-\d{2,}:(?!.*~~)"), "plan": (12, 40, r"^### M\d+-T\d{2,}:")}


def budget(kind, text):
    per, allowance, unit = UNIT_BUDGETS[kind]
    n = len(re.findall(unit, text, re.M))
    extra = 0
    if kind == "pipelines":  # pre-build sections (planned layout, entry sketches) are extra
        extra = sum(len(m.group(0).splitlines()) for m in re.finditer(r"^##+ [^\n]*pre-build.*?(?=^## |\Z)", text, re.S | re.M))
    if kind == "plan":
        extra = len(re.findall(r"^\|\s*M\d+-T\d{2,}", section(text, "Dependency graph"), re.M))
    return per * n + allowance + extra
later = {k: matching(f"packages/*/{k}.md", f"final__packages__*__{k}.md") for k in ("contract", "pipelines", "tests")}
later["plan"] = matching("tasks/plan.md", "final__tasks__plan.md", d.parent) + matching("tasks/queued/*.md", "final__tasks__queued__*.md", d.parent)
constraints = matching("CONSTRAINTS.md", "final__CONSTRAINTS.md", d.parent)
arch_all = "\n".join([arch] + pkgs)

# Each requirement block runs from its "- **ID**" line to the next one (or next heading).
blocks = re.findall(r"^\s*- \*\*([A-Z][A-Z0-9]*-\d{2,})\*\*(.*?)(?=^\s*- \*\*[A-Z][A-Z0-9]*-\d{2,}\*\*|^#|\Z)",
                    spec, re.S | re.M)
removed = [(rid, body) for rid, body in blocks if "~~" in body.split("\n")[0]]

# Each decision block runs from its "### AD-NN" heading to the next heading.
decisions = re.findall(r"^### (AD-\d{2,})(.*?)(?=^##|\Z)", arch, re.S | re.M)
superseded = [(i, b) for i, b in decisions if re.search(r"Superseded by", b)]

risks = section(arch, "Risks")
out = {
    "words": {"brief": words(brief), "spec": words(spec), "architecture": words(arch_all),
              "ideas": sum(words(t) for t in ideas), "total": words(brief) + words(spec) + words(arch_all) + sum(words(t) for t in ideas)},
    "spec": {"requirements": len(blocks), "removed": len(removed),
             "removed_avg_words": round(sum(words(b) for _, b in removed) / len(removed), 1) if removed else 0,
             "changed_markers": len(re.findall(r"\(changed\b", spec)),
             "changed_markers_above_changelog": len(re.findall(r"\(changed\b", re.split(r"^## Changelog", spec, flags=re.M)[0])),
             "changed_markers_off_id_lines": sum(1 for l in re.split(r"^## Changelog", spec, flags=re.M)[0].splitlines()
                                                 if "(changed" in l and not re.search(r"\*\*[A-Z][A-Z0-9]*-\d{2,}\*\*", l)),
             "changelog_rows": len(re.findall(r"^\|\s*\d{4}-\d{2}-\d{2}", section(spec, "Changelog"), re.M))},
    "architecture": {"decisions": len(decisions), "superseded": len(superseded),
                     "superseded_avg_words": round(sum(words(b) for _, b in superseded) / len(superseded), 1) if superseded else 0,
                     "risks_words": words(risks), "risks_subheadings": len(re.findall(r"^###", risks, re.M)),
                     "struck_risks": len(re.findall(r"^\s*- ~~", risks, re.M)),
                     "package_docs": len(pkgs),
                     # An odd count leaves a code block open, so the rest of the doc renders as code.
                     "code_fences_unbalanced": len(re.findall(r"^\s*```", arch, re.M)) % 2 == 1,
                     "changelog_rows": len(re.findall(r"^\|\s*\d{4}-\d{2}-\d{2}", section(arch, "Changelog"), re.M)),
                     # Spec IDs copied into the architecture Changelog (its last column, minus AD- ranges).
                     "changelog_spec_ids": sum(id_count(re.sub(r"AD-\d{2,}(\s*[–-]\s*AD-\d{2,})?", "", r.rstrip(" |").split("|")[-1]))
                                               for r in re.findall(r"^\|\s*\d{4}-\d{2}-\d{2}.*$", section(arch, "Changelog"), re.M))},
    "ideas": {"count": len(ideas),
              "specced_without_banner": sum(1 for t in ideas if re.search(r"\*\*Status:\*\*\s*Specced", t)
                                            and not re.search(r"^> Record of why", t, re.M)),
              "specced_with_open_questions": sum(1 for t in ideas if re.search(r"\*\*Status:\*\*\s*Specced", t)
                                                 and re.search(r"^## Open questions\n+\s*- ", t, re.M))},
    "planning": {k: {"docs": len(v), "lines": [len(t.splitlines()) for _, t in v], "budgets": [budget(k, t) for _, t in v],
                     "over_budget": [n for n, t in v if len(t.splitlines()) > budget(k, t)]} for k, v in later.items()}
                | {"constraints_lines": sum(len(t.splitlines()) for _, t in constraints),
                   "tasks": sum(len(re.findall(r"^### M\d+-T\d{2,}:", t, re.M)) for _, t in later["plan"])},
}
print(json.dumps(out, indent=1))
