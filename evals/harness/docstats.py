#!/usr/bin/env python3
"""Size and history-residue stats for one run's final planning docs, as JSON.

Measures what eval iteration 1 found growing in incremental runs: total words, struck
(removed) requirements and how long they stay, "(changed ...)" markers, superseded
decisions kept in full, Risks size, and docs written past the architecture (plan.md).

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
pkgs, ideas = globbed("architecture"), globbed("ideas")
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
    "past_architecture": sorted(p.name for p in [d / "plan.md", d / "final__plan.md"] if p.exists())
                         + (["tasks/"] if (d.parent / "tasks").is_dir() else []),
}
print(json.dumps(out, indent=1))
