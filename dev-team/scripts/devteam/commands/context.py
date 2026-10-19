"""Print a task's whole builder context packet: its Read: sections and files, the package layout, the frozen
interfaces its steps cross, for a system task the fakes whose cases it runs on the real providers, its Writes: (or
Files likely), then the task."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .. import code, graph, md, model
from .. import packet as pk
from .. import outline as ol
from .. import probes as pb
from .. import references as refs
from .layout import tree_lines

BUDGET = 2000          # lines; agent-skills context-engineering target for one builder
PLAN_KINDS = ("plan", "queued-plan")
LANGS = pk.LANGS


def add_arguments(parser):
    parser.add_argument("task", help="task ID, e.g. M2-T03")
    parser.add_argument("--json", action="store_true", help="print one JSON object (the packet is under `text`)")


def _find_task(repo, task_id: str):
    for doc in repo.docs(*PLAN_KINDS):
        for t in model.tasks(doc):
            if t.id == task_id:
                return t
    return None


def _fence(text: str) -> str:
    longest = max((len(m) for m in re.findall(r"`{3,}", text)), default=0)
    return "`" * max(3, longest + 1)


def _file_block(repo, rel: str, task: model.Task) -> tuple[str, bool]:
    """`### <path>` and the file in a fence; a one-line note if it can't be read: the task that writes it first
    (an interface stub, a seam), or "missing" when none does (`dt lint` `read-unwritten`)."""
    path = repo.root / rel
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        by = pk.writers_before(repo, task, rel)
        if by:
            verb = "writes" if len(by) == 1 else "write"
            return f"### {rel}\n(not in the repo yet: {', '.join(by)} {verb} it before this task starts)\n", False
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


LONG_TABLE = 12        # step rows; past this, a task building some of a pipeline's steps sees only their rows


def _section(task: model.Task, d) -> tuple[str, str | None]:
    """A `Read:` section's text, and `k of n` when its step table was cut. A pipeline whose step table is over
    `LONG_TABLE` rows keeps its header and the rows of the steps the task's `Step:` names (`PL-01.train_run`); a task
    building the whole pipeline (`Step: PL-01`: wiring, system) or none of its steps gets every row."""
    if d.how != "heading" or not re.fullmatch(r"PL-\d{2,}", d.id):
        return d.text, None
    p = next((x for x in model.pipelines(d.doc) if x.id == d.id), None)
    if p is None or len(p.steps) <= LONG_TABLE:
        return d.text, None
    named = [m.group(1) for m in re.finditer(rf"{re.escape(p.id)}(?:\.(\w+))?\b", task.step)]
    keep = {s.line for s in p.steps if s.name in named}
    if not keep or None in named:
        return d.text, None
    rows = {s.line for s in p.steps}
    last = max(rows)
    out = []
    for i in range(d.start, d.end):
        if i not in rows or i in keep:
            out.append(d.doc.lines[i])
        if i == last:
            out.append(f"({len(keep)} of {len(rows)} step rows: the ones {task.id} builds; the rest are other "
                       f"tasks')")
    return "\n".join(out).rstrip() + "\n", f"{len(keep)} of {len(rows)}"


def interfaces(repo, task: model.Task, shown: set[str]) -> list[pk.Shown]:
    """The frozen interfaces the packet adds to what `Read:` shows: the contract types the task's steps' `In → Out`
    cells name, the contract symbols with a step's name (its signature), and every contract section those and the
    Read symbols' signatures name, until closed (`packet.contract`)."""
    return [s for s in pk.contract(repo, task, sorted(shown)) if s.symbol.id not in shown]


def _interfaces_block(repo, shown: list[pk.Shown]) -> str:
    parts = []
    for s in shown:
        sym = s.symbol
        why = f" · {s.why}" if s.why.startswith("named by") else ""
        part = f"<!-- {sym.doc.rel}:{sym.start + 1}{why} -->\n{sym.text}"
        if sym.sample:
            part += f"Sample: {sym.sample} ({'exists' if (repo.root / sym.sample).exists() else 'not written yet'})\n"
        parts.append(part)
    return "## Interfaces (frozen: build against these, never change them)\n" + "\n".join(parts)


def conformance(repo, task: model.Task, syms: list[pk.Shown]) -> list[tuple[str, list[str]]]:
    """For a system task, which runs real providers where fakes stood: each contract symbol it reads or crosses
    whose `tests/contracts/<id>/` folder holds a fake, with that folder's files. Their cases run on the real one."""
    if task.kind != "system":
        return []
    ids = dict.fromkeys([pk.read_ref(r) for r in task.read] + [s.symbol.id for s in syms])
    out = []
    for sid in ids:
        folder = repo.root / "tests" / "contracts" / sid
        if re.fullmatch(md.SYMBOL_ID, sid) and any(folder.glob("fake*.py")):
            out.append((sid, sorted(f.name for f in folder.iterdir() if f.is_file())))
    return out


def _conformance_block(found: list[tuple[str, list[str]]]) -> str:
    rows = "".join(f"- {sid}: tests/contracts/{sid}/ ({', '.join(files)})\n" for sid, files in found)
    return ("## Conformance (each fake's contract cases, run on the real provider)\n"
            "Run every case a folder's contract tests give its fake on the real provider too, in a test your "
            "Writes: name. A case the real one fails: fix it if your Writes: hold the code, else "
            "`dt escalate CONTRACT-CHANGE \"<the case, fake vs real>\" --type <symbol>`.\n" + rows)


def _writes(repo, task: model.Task) -> list[dict]:
    """Each Writes path: exists, a folder, and `from` — the tasks upstream of this one (`Depends on`, directly or
    not) whose Writes name that exact path, so a builder extends their file instead of starting a new one (a
    folder claim upstream, such as the interface task's stubs, doesn't count)."""
    plan = model.tasks(task.doc)
    up = graph.ancestors(plan, task.id)
    out = []
    for w in task.writes:
        folder = w.endswith(("/", "/*", "/**"))
        prior = [t.id for t in plan if t.id in up and not folder
                 and model.norm_write(w)[0] in {model.norm_write(v)[0] for v in t.writes}]
        out.append({"path": w, "exists": (repo.root / w.rstrip("*").rstrip("/")).exists(), "folder": folder,
                    "from": prior})
    return out


def _write_state(w: dict) -> str:
    if w["folder"]:
        return "folder"
    if w["exists"]:
        return "exists"
    return f"from {', '.join(w['from'])}" if w["from"] else "new"


SOURCE_PREFIXES = ("src/",)


def is_source(rel: str) -> bool:
    """A path under a source folder (`src/`, `packages/<pkg>/src/`): never shown to a tester."""
    rel = rel.removeprefix("./")
    return rel.startswith(SOURCE_PREFIXES) or bool(re.match(r"packages/[^/]+/src/", rel))


def packet(repo, task, writes: list[str] | None = None, tester: bool = False) -> dict:
    """The task's packet: `{text, lines, reads, interfaces, writes, files_likely, problems}`. `writes` narrows the
    Writes block to a half's share; `tester` leaves out source files and the package layout (build-phase.md
    §3.4: a tester never sees `src/`)."""
    blocks: list[str] = []
    reads: list[dict] = []
    problems: list[str] = []
    entries = {e.id: e for e in model.all_references(repo) + model.all_probes(repo)}
    shown: set[str] = set()
    for raw in task.read:
        ref = pk.read_ref(raw)
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
            text, rows = _section(task, d)
            reads.append({"ref": ref, "kind": "id", "where": d.where, "retired": d.retired,
                          **({"rows": rows} if rows else {})})
            blocks.append(f"<!-- {d.where} -->\n{text}")
        elif pk.looks_like_path(repo, ref):
            if tester and is_source(ref):
                reads.append({"ref": ref, "kind": "file", "exists": (repo.root / ref).exists(), "shown": "withheld"})
                continue
            block, exists = _file_block(repo, ref, task)
            reads.append({"ref": ref, "kind": "file", "exists": exists})
            blocks.append(block)
        else:
            problems.append(f"Read: {ref} is not defined in any doc")

    layout = "" if tester else _layout_block(repo, task.package)
    if layout:
        blocks.append(layout)
    shown_ids = {r["ref"] for r in reads if r["kind"] == "id"}
    syms = interfaces(repo, task, shown_ids)
    if syms:
        blocks.append(_interfaces_block(repo, syms))
    found = [] if tester else conformance(repo, task, syms)
    if found:
        blocks.append(_conformance_block(found))
    files = [{"path": f, "exists": (repo.root / f).exists()} for f in task.files_likely]
    out_writes = _writes(repo, task) if "Writes" in task.fields else []
    if writes is not None:
        out_writes = [w for w in out_writes if w["path"] in writes]
    if out_writes:
        blocks.append("## Writes (edit only these files; the plan gives every other file to another task)\n" + "".join(
            f"- {w['path']} ({_write_state(w)})\n" for w in out_writes))
    elif files:
        blocks.append("## Files likely\n" + "".join(
            f"- {f['path']} ({'exists' if f['exists'] else 'new'})\n" for f in files))
    blocks.append(f"<!-- {task.doc.rel}:{task.start + 1} -->\n{task.text}")

    kind = f" · kind {task.kind}" if task.kind else ""
    preamble = (f"# Context for {task.id}: package {task.package or '—'} · mode {task.mode or '—'}{kind}\n"
                "Read only what is below, plus CONSTRAINTS.md and the files you edit. "
                "Your task is the last section.\n")
    text = "\n".join([preamble] + blocks)
    return {"text": text, "lines": text.count("\n"), "reads": reads, "interfaces": syms, "writes": out_writes,
            "files_likely": files, "problems": problems}


def run(args, repo) -> int:
    task = _find_task(repo, args.task)
    if task is None:
        print(f"dt context: task {args.task} not found in tasks/plan.md or tasks/queued/", file=sys.stderr)
        return 1
    p = packet(repo, task)
    if p["problems"]:
        for problem in p["problems"]:
            print(f"dt context: {task.id}: {problem}", file=sys.stderr)
        return 1
    text, lines, syms = p["text"], p["lines"], p["interfaces"]
    if lines > BUDGET:
        print(f"dt context: {task.id} packet is {lines} lines (budget {BUDGET}); split the task or trim its Read:",
              file=sys.stderr)

    if args.json:
        print(json.dumps({"task": task.id, "package": task.package, "mode": task.mode, "kind": task.kind,
                          "lines": lines, "read": p["reads"],
                          "interfaces": [{"id": s.symbol.id, "where": f"{s.symbol.doc.rel}:{s.symbol.start + 1}",
                                          "type": s.symbol.is_type, "sample": s.symbol.sample,
                                          "named_by": s.why.removeprefix("named by ") if s.why != "step" else None}
                                         for s in syms],
                          "writes": p["writes"], "files_likely": p["files_likely"], "text": text}, indent=2))
    else:
        print(text, end="")
    return 0
