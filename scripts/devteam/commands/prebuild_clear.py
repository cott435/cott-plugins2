"""Replace a pipeline's pre-build entry sketch with a `dt layout` pointer (and the planned layout once all are built)."""
from __future__ import annotations

import re

from .. import edit, model

LAYOUT_RE = re.compile(r"^Layout:\s*`dt layout ")


def add_arguments(parser):
    parser.add_argument("pipeline", help="pipeline ID, e.g. PL-02")


def _layout_pkg(pipeline: model.Pipeline) -> str:
    """Package for the pointer: the doc's package, else (system pipeline) the folder after `src/` in Entry."""
    if pipeline.package:
        return pipeline.package
    parts = pipeline.entry_file.split("/")
    return parts[1] if len(parts) > 2 and parts[0] == "src" else (parts[0] if parts[0] else "<pkg>")


def _content_end(lines: list[str], start: int, end: int) -> int:
    """End of [start, end) with trailing blank lines left out."""
    while end > start and not lines[end - 1].strip():
        end -= 1
    return end


def run(args, repo) -> int:
    pid = args.pipeline
    if not re.fullmatch(r"PL-\d{2,}", pid):
        print(f"dt prebuild-clear: bad pipeline ID {pid!r}")
        return 2
    found = [(d, p) for d in repo.docs("pipelines", "architecture") for p in model.pipelines(d) if p.id == pid]
    if not found:
        print(f"dt prebuild-clear: {pid} not found")
        return 1
    doc, pipeline = found[0]
    lines = edit.read_lines(doc.path)
    nl = edit.eol(lines)
    heading = doc.heading(pid)
    under = doc.headings_under(heading)
    sketch = next((h for h in under if "entry sketch" in h.text.lower() and "(pre-build" in h.text), None)

    # Edits run bottom-up so earlier line numbers stay valid.
    edits: list[tuple[int, int, list[str]]] = []
    done: list[str] = []
    if sketch:
        has_pointer = any(LAYOUT_RE.match(doc.lines[i]) for i in range(heading.line, heading.end)
                          if not sketch.line <= i < sketch.end)
        if has_pointer:     # drop the sketch and its trailing blank lines
            edits.append((sketch.line, sketch.end, []))
        else:               # the pointer takes the sketch's place; the blank lines after it stay
            pointer = f"Layout: `dt layout {_layout_pkg(pipeline)}`{nl}"
            edits.append((sketch.line, _content_end(doc.lines, sketch.line, sketch.end), [pointer]))
        done.append(f"removed {pid} entry sketch")

    spine = model.spine_done(repo)
    live = model.pipelines(doc)
    planned = next((h for h in doc.headings if h.level == 2 and "planned layout" in h.text.lower()
                    and "(pre-build" in h.text), None)
    if planned and all(model.pipeline_built(repo, p, spine) for p in live):
        edits.append((planned.line, planned.end, []))   # its trailing blank lines go too
        done.append("removed Planned layout (every pipeline built)")
    elif planned:
        waiting = [p.id for p in live if not model.pipeline_built(repo, p, spine)]
        done.append(f"kept Planned layout (not built: {', '.join(waiting)})")

    if not edits:
        print(f"{pid}: nothing to clear" + (f"; {done[-1]}" if done else ""))
        return 0
    for start, end, new in sorted(edits, reverse=True):
        lines[start:end] = new
    edit.write_lines(doc.path, lines)
    repo.reload(doc.rel)
    print(f"{doc.rel}: " + "; ".join(done))
    return 0
