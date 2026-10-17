"""Print a task's whole builder context packet: its Read: sections and files, the package layout, the frozen
interfaces its steps cross, its Writes: (or Files likely), then the task."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .. import code, md, model
from .. import outline as ol
from .. import probes as pb
from .. import references as refs
from .layout import tree_lines

BUDGET = 2000          # lines; agent-skills context-engineering target for one builder
PLAN_KINDS = ("plan", "queued-plan")
LANGS = {".py": "python", ".md": "markdown", ".json": "json", ".toml": "toml", ".yaml": "yaml", ".yml": "yaml",
         ".sh": "bash", ".csv": "csv", ".sql": "sql", ".js": "javascript", ".ts": "typescript", ".txt": "text"}


def add_arguments(parser):
    parser.add_argument("task", help="task ID, e.g. M2-T03")
    parser.add_argument("--json", action="store_true", help="print one JSON object (the packet is under `text`)")


def _find_task(repo, task_id: str):
    for doc in repo.docs(*PLAN_KINDS):
        for t in model.tasks(doc):
            if t.id == task_id:
                return t
    return None


def _ref(raw: str) -> str:
    """A `Read:` item without backticks or a trailing `(reason)`."""
    return re.sub(r"\s*\(.*\)\s*$", "", raw).strip().strip("`").strip()


def _looks_like_path(repo, ref: str) -> bool:
    """A repo path rather than an ID: has a folder, exists, or ends in a file extension."""
    suffix = ("." + ref.rsplit(".", 1)[1].lower()) if "." in ref else ""
    return "/" in ref or (repo.root / ref).exists() or suffix in LANGS or suffix in (".cfg", ".ini", ".lock")


def _fence(text: str) -> str:
    longest = max((len(m) for m in re.findall(r"`{3,}", text)), default=0)
    return "`" * max(3, longest + 1)


def _file_block(repo, rel: str) -> tuple[str, bool]:
    """`### <path>` and the file in a fence; a one-line note if it can't be read."""
    path = repo.root / rel
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return f"### {rel}\n(missing: not in the repo yet)\n", False
    fence = _fence(text)
    lang = LANGS.get(path.suffix.lower(), "")
    body = text if text.endswith("\n") or not text else text + "\n"
    return f"### {rel}\n{fence}{lang}\n{body}{fence}\n", True


BANNER = ("> Reference, not part of the project. Reuse what fits the contract and step table as is, adapt it, "
          "or ignore it: your call.\n"
          "> Never import from references/. Anything you bring over meets the same bar as the rest of the code.\n")


def _reference_block(repo, entry: model.Reference, selector: str) -> tuple[str, dict, str | None]:
    """The banner and the reference file (whole, one selected part, or its outline): (block, read info,
    problem). A selector that names nothing in the file is a problem; a missing file is only noted."""
    rel = entry.file
    head = f"### Reference {entry.id}: {rel or '(no File)'}\n{BANNER}"
    if entry.caveats:
        head += f"> Caveats: {entry.caveats}\n"
    info = {"file": rel, "selector": selector, "shown": "missing"}
    path = repo.root / rel if rel else None
    text = ol.read(path) if path is not None and path.is_file() else None
    if text is None:
        return head + "(missing: the entry's file isn't in references/; run reference-intake)\n", info, None
    n = len(text.splitlines())
    if selector.lower() == "outline" or (not selector and n > refs.LARGE_LINES):
        o = ol.outline(path, text)
        why = "outline" if selector else f"{n} lines, so outline only; name a part: {entry.id}:<symbol or heading>"
        info["shown"] = "outline"
        return head + f"({why})\n" + _fenced("\n".join(o.items) + "\n", ""), info, None
    if not selector:
        info["shown"] = "whole"
        return head + _fenced(text, LANGS.get(path.suffix.lower(), "")), info, None
    span = ol.select(path, text, selector)
    if span is None:
        return "", info, f"Read: {entry.id}:{selector} names nothing in {rel} (a def, class or heading)"
    a, b = span
    info["shown"] = "part"
    part = "\n".join(text.splitlines()[a - 1:b]) + "\n"
    return head + f"({selector} · lines {a}–{b} of {n})\n" + _fenced(part, LANGS.get(path.suffix.lower(), "")), \
        info, None


PROBE_BANNER = ("> Reference, not part of the project. Reuse what fits the contract and step table as is, adapt it, "
                "or ignore it: your call.\n"
                "> Never import from probes/. Anything you bring over meets the same bar as the rest of the code.\n"
                "> Probe code: written to answer {id}'s checks, not to production standard. "
                "Its Verdict and Caveats follow.\n")


def _probe_block(repo, entry: model.Probe, selector: str) -> tuple[str, dict, str | None]:
    """The probe banner, then (design/probes.md §4.6): its files (no selector), every code file's outline
    (`outline`), its redacted samples (`samples`), or one file, whole or outlined (`<file>`), or one part of it
    (`<file>:<symbol or heading>`). `out/` and `.env` files are never shown."""
    folder = pb.folder_of(repo, entry)
    rel = entry.folder
    verdict = md.strip_md(entry.fields.get("Verdict", "")) or "—"
    head = PROBE_BANNER.format(id=entry.id) + f"> Verdict: {verdict}\n"
    if entry.caveats:
        head += f"> Caveats: {entry.caveats}\n"
    info = {"file": rel, "selector": selector, "shown": "missing"}
    if folder is None or not folder.is_dir():
        return (f"### Reference {entry.id}: {rel or '(no Folder)'}\n{head}"
                "(missing: the probe's folder isn't there; run api-probe)\n"), info, None
    code = pb.code_files(folder)
    if not selector:
        info["shown"] = "files"
        listing = [f"{f} ({pb.line_count(folder / f)} lines)" for f in code]
        listing += [f"{f} (sample)" for f in pb.samples(folder)]
        return (f"### Reference {entry.id}: {rel}/\n{head}(files; name a part: {entry.id}:<file>, "
                f"{entry.id}:<file>:<symbol>, {entry.id}:samples, {entry.id}:outline)\n"
                + _fenced("\n".join(listing) + "\n", "")), info, None
    if selector.lower() == "outline":
        info["shown"] = "outline"
        parts = []
        for f in code:
            if f.endswith(pb.SOURCE_SUFFIXES):
                text = ol.read(folder / f)
                if text is not None:
                    parts.append("\n".join(ol.outline(folder / f, text).items))
        return (f"### Reference {entry.id}: {rel}/\n{head}(outline)\n"
                + _fenced("\n\n".join(parts) + "\n", "")), info, None
    if selector.lower() == "samples":
        files = pb.samples(folder)
        if not files:
            return (f"### Reference {entry.id}: {rel}/evidence/samples/\n{head}"
                    "(missing: no samples yet; the probe writes them when it runs)\n"), info, None
        info["shown"] = "samples"
        body = "".join(f"#### {rel}/{f}\n" + _fenced(ol.read(folder / f) or "", LANGS.get(Path(f).suffix, ""))
                       for f in files)
        return f"### Reference {entry.id}: {rel}/evidence/samples/\n{head}" + body, info, None
    name, _, part = selector.partition(":")
    name = name.strip()
    if name.startswith(("/", "../", "out/")) or "/../" in name or Path(name).name.startswith(".env"):
        return "", info, f"Read: {entry.id}:{selector} is never shown (out/ and .env stay with the user)"
    path = folder / name
    text = ol.read(path) if path.is_file() else None
    if text is None:
        return "", info, f"Read: {entry.id}:{selector} names no file in {rel}/"
    lang = LANGS.get(path.suffix.lower(), "")
    n = len(text.splitlines())
    title = f"### Reference {entry.id}: {rel}/{name}\n{head}"
    if not part and n > refs.LARGE_LINES:
        info["shown"] = "outline"
        return title + f"({n} lines, so outline only; name a part: {entry.id}:{name}:<symbol>)\n" + \
            _fenced("\n".join(ol.outline(path, text).items) + "\n", ""), info, None
    if not part:
        info["shown"] = "whole"
        return title + _fenced(text, lang), info, None
    span = ol.select(path, text, part.strip())
    if span is None:
        return "", info, f"Read: {entry.id}:{selector} names nothing in {rel}/{name} (a def, class or heading)"
    a, b = span
    info["shown"] = "part"
    return title + f"({part.strip()} · lines {a}–{b} of {n})\n" + \
        _fenced("\n".join(text.splitlines()[a - 1:b]) + "\n", lang), info, None


def _fenced(body: str, lang: str) -> str:
    fence = _fence(body)
    return f"{fence}{lang}\n{body}{fence}\n"


def _layout_block(repo, pkg: str) -> str:
    """The package's real tree (as `dt layout`), since built pipelines point there instead of a planned layout."""
    if not pkg:
        return ""
    folder = code.source_folder(repo, pkg)
    root = repo.root / folder
    if not root.is_dir():
        return ""
    return f"## Layout (`dt layout {pkg}`)\n{folder}/\n" + "".join(tree_lines(code.source_tree(root)))


def _task_steps(repo, task: model.Task) -> list[model.Step]:
    """The steps a task touches: `PL-02.pca` → that step; `PL-02` (wiring, system) → every step of PL-02."""
    pipelines = {p.id: p for p in model.all_pipelines(repo)}
    out = []
    for m in re.finditer(r"(PL-\d{2,})(?:\.(\w+))?", task.step):
        p = pipelines.get(m.group(1))
        if p is not None:
            out += [s for s in p.steps if m.group(2) in (None, s.name)]
    return out


def interfaces(repo, task: model.Task, shown: set[str]) -> list[model.Symbol]:
    """The frozen interfaces the task's steps cross and that its `Read:` doesn't already show: the contract types
    their `In → Out` cells name, and the contract symbols with a step's name (its signature)."""
    types = model.contract_types(repo)
    steps = _task_steps(repo, task)
    out: dict[str, model.Symbol] = {}
    for s in steps:
        for name in s.in_types + s.out_types:
            ty = model.resolve_type(types, name)
            if ty is not None:
                out.setdefault(ty.id, ty)
    names = {s.name for s in steps}
    for sym in model.all_symbols(repo):
        if not sym.is_type and sym.name in names:
            out.setdefault(sym.id, sym)
    return [sym for i, sym in out.items() if i not in shown]


def _interfaces_block(repo, syms: list[model.Symbol]) -> str:
    parts = []
    for sym in syms:
        part = f"<!-- {sym.doc.rel}:{sym.start + 1} -->\n{sym.text}"
        if sym.sample:
            part += f"Sample: {sym.sample} ({'exists' if (repo.root / sym.sample).exists() else 'not written yet'})\n"
        parts.append(part)
    return "## Interfaces (frozen: build against these, never change them)\n" + "\n".join(parts)


def _writes(repo, task: model.Task) -> list[dict]:
    out = []
    for w in task.writes:
        folder = w.endswith(("/", "/*", "/**"))
        out.append({"path": w, "exists": (repo.root / w.rstrip("*").rstrip("/")).exists(), "folder": folder})
    return out


def run(args, repo) -> int:
    task = _find_task(repo, args.task)
    if task is None:
        print(f"dt context: task {args.task} not found in tasks/plan.md or tasks/queued/", file=sys.stderr)
        return 1

    blocks: list[str] = []
    reads: list[dict] = []
    problems: list[str] = []
    entries = {e.id: e for e in model.all_references(repo) + model.all_probes(repo)}
    shown: set[str] = set()
    for raw in task.read:
        ref = _ref(raw)
        rid, selector = model.split_ref(ref)
        if rid in entries:
            entry = entries[rid]
            render = _probe_block if isinstance(entry, model.Probe) else _reference_block
            block, info, problem = render(repo, entry, selector)
            if problem:
                problems.append(problem)
                continue
            where = f"{entry.doc.rel}:{entry.start + 1}"
            reads.append({"ref": ref, "kind": "reference", "where": where, **info})
            blocks.append(block if rid in shown else f"<!-- {where} -->\n{entry.text}\n{block}")
            shown.add(rid)
            continue
        d = repo.lookup(rid if selector else ref, archive=False)
        if d is not None:
            if d.retired:
                problems.append(f"Read: {ref} is retired ({d.retired_note}) at {d.where}")
            reads.append({"ref": ref, "kind": "id", "where": d.where, "retired": d.retired})
            blocks.append(f"<!-- {d.where} -->\n{d.text}")
        elif _looks_like_path(repo, ref):
            block, exists = _file_block(repo, ref)
            reads.append({"ref": ref, "kind": "file", "exists": exists})
            blocks.append(block)
        else:
            problems.append(f"Read: {ref} is not defined in any doc")
    if problems:
        for p in problems:
            print(f"dt context: {task.id}: {p}", file=sys.stderr)
        return 1

    layout = _layout_block(repo, task.package)
    if layout:
        blocks.append(layout)
    shown_ids = {r["ref"] for r in reads if r["kind"] == "id"}
    syms = interfaces(repo, task, shown_ids)
    if syms:
        blocks.append(_interfaces_block(repo, syms))
    files = [{"path": f, "exists": (repo.root / f).exists()} for f in task.files_likely]
    writes = _writes(repo, task) if "Writes" in task.fields else []
    if writes:
        blocks.append("## Writes (edit only these files; the plan gives every other file to another task)\n" + "".join(
            f"- {w['path']} ({'folder' if w['folder'] else 'exists' if w['exists'] else 'new'})\n" for w in writes))
    elif files:
        blocks.append("## Files likely\n" + "".join(
            f"- {f['path']} ({'exists' if f['exists'] else 'new'})\n" for f in files))
    blocks.append(f"<!-- {task.doc.rel}:{task.start + 1} -->\n{task.text}")

    kind = f" · kind {task.kind}" if task.kind else ""
    preamble = (f"# Context for {task.id}: package {task.package or '—'} · mode {task.mode or '—'}{kind}\n"
                "Read only what is below, plus CONSTRAINTS.md and the files you edit. "
                "Your task is the last section.\n")
    text = "\n".join([preamble] + blocks)
    lines = text.count("\n")
    if lines > BUDGET:
        print(f"dt context: {task.id} packet is {lines} lines (budget {BUDGET}); split the task or trim its Read:",
              file=sys.stderr)

    if args.json:
        print(json.dumps({"task": task.id, "package": task.package, "mode": task.mode, "kind": task.kind,
                          "lines": lines, "read": reads,
                          "interfaces": [{"id": s.id, "where": f"{s.doc.rel}:{s.start + 1}", "type": s.is_type,
                                          "sample": s.sample} for s in syms],
                          "writes": writes, "files_likely": files, "text": text}, indent=2))
    else:
        print(text, end="")
    return 0
