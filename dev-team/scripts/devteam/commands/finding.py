"""Record a review finding under a checkpoint in tasks/plan.md; --from records a reviewer's whole file.

Each finding gets the next free M<n>-R ID. With --from: every finding line of a reviewer's file, committed on the
current branch, with the review's outcome in dt-build/reviews/."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .. import buildstate as bs
from .. import dispatch, edit, md, model

SEVERITIES = ("Critical", "Important", "Suggestion", "Nit")   # agent-skills code-review-and-quality
# A reviewer's finding line (reviewer.md): `<Severity> · <CR-NN or axis> · <where> <what> → <fix>`, optionally
# as a list item. Any other line in the file (headings, the checklist) is ignored.
LINE = re.compile(rf"^\s*(?:[-*]\s+)?\**({'|'.join(SEVERITIES)})\**\s*·\s*(.+?)\s*$", re.IGNORECASE)


def add_arguments(parser):
    parser.add_argument("checkpoint", nargs="?",
                        help="task ID the checkpoint follows (M1-T04), or `exit` for the milestone exit")
    parser.add_argument("severity", nargs="?", help="Critical, Important, Suggestion or Nit")
    parser.add_argument("text", nargs="?", help="the finding, e.g. 'CR-21 · `rmt.py::clean_eigen` complexity 14'")
    parser.add_argument("--disposition", default="", help="fix task or reason, appended as `→ <disposition>`")
    parser.add_argument("--from", dest="from_file", metavar="FILE",
                        help="record every finding line in FILE (a reviewer's `<checkpoint>.<pkg>.md`), commit "
                             "tasks/plan.md, and write the review's outcome to dt-build/reviews/<checkpoint>.<pkg>.json")
    parser.add_argument("--checkpoint", dest="cp_opt", help="with --from: the checkpoint (default: from FILE's name)")
    parser.add_argument("--pkg", help="with --from: the package reviewed (default: from FILE's name)")


def _checkpoint(plan, which: str) -> model.Checkpoint | None:
    for cp in model.checkpoints(plan):
        if (which == "exit" and "exit" in cp.title.lower()) or (which != "exit" and cp.after == which):
            return cp
    return None


def _which(raw: str) -> str | None:
    which = raw if raw.lower() == "exit" else raw.upper()
    which = "exit" if which.lower() == "exit" else which
    return which if which == "exit" or re.fullmatch(md.TASK_ID, which) else None


def _write_checkpoint(repo, plan, cp: model.Checkpoint):
    """Write a barrier dt added (dispatch.added_barriers) into the plan as its heading, where the interface task's
    section ends; the task's text is unchanged. Returns the reloaded plan."""
    lines = edit.read_lines(plan.path)
    nl = edit.eol(lines)
    head = [f"### {cp.title}" + nl, nl]
    if cp.start and lines[cp.start - 1].strip():
        head.insert(0, nl)
    lines[cp.start:cp.start] = head
    edit.write_lines(plan.path, lines)
    repo.reload(plan.rel)
    return repo.plan


def record(repo, which: str, severity: str, text: str, disposition: str = "") -> tuple[int, str]:
    """Append one finding under the checkpoint: (0, new ID) or (exit code, message)."""
    plan = repo.plan
    milestone = model.milestone_of(plan) if plan else None
    if not plan or not milestone:
        return 1, "tasks/plan.md has no active milestone"
    cp = _checkpoint(plan, which)
    added = next((c for c in dispatch.added_barriers(plan, model.tasks(plan)) if c.after == which), None)
    if cp is None and added is not None:
        plan = _write_checkpoint(repo, plan, added)
        cp = _checkpoint(plan, which)
    if cp is None:
        return 1, f"tasks/plan.md has no {'milestone exit checkpoint' if which == 'exit' else f'checkpoint after {which}'}"
    fid = repo.next_id(f"{milestone}-R")
    lines = edit.read_lines(plan.path)
    nl = edit.eol(lines)
    item = f"- {fid} {severity} · {text}" + (f" → {disposition}" if disposition else "") + nl

    f_line = md.field_line(plan.lines, cp.start + 1, cp.end, "Findings")
    if f_line is not None:
        at = f_line + 1           # after the label and any findings already listed under it
        while at < cp.end and re.match(r"^\s*[-*]\s+", plan.lines[at]):
            at += 1
        new = [item]
    else:
        at = cp.end               # after the checkpoint's last non-blank line
        while at > cp.start + 1 and not plan.lines[at - 1].strip():
            at -= 1
        new = ["**Findings:**" + nl, item]
    lines = edit.ensure_eol(lines) if at >= len(lines) else lines
    lines[at:at] = new
    edit.write_lines(plan.path, lines)
    repo.reload(plan.rel)
    return 0, fid


def parse_lines(text: str) -> list[tuple[str, str]]:
    """(Severity, rest of the line) for each finding line, in file order."""
    out = []
    for line in text.splitlines():
        m = LINE.match(line)
        if m:
            sev = next(s for s in SEVERITIES if s.lower() == m.group(1).lower())
            out.append((sev, " ".join(m.group(2).split())))
    return out


def _fail(msg: str, code: int = 1) -> int:
    print(json.dumps({"error": msg}))
    return code


def run_from(args, repo) -> int:
    path = Path(args.from_file)
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return _fail(f"dt finding: cannot read {path}: {e}")
    stem = path.name.removesuffix(".md")
    cp_guess, _, pkg_guess = stem.partition(".")
    which = _which(args.cp_opt or cp_guess)
    pkg = args.pkg or pkg_guess
    if which is None or not pkg:
        return _fail(f"dt finding: name the checkpoint and package (--checkpoint, --pkg; or a file named "
                     f"<checkpoint>.<pkg>.md), got {path.name!r}", 2)
    rid = f"{which}.{pkg}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    try:
        state = bs.State(repo.root)
    except bs.GitError as e:
        return _fail(f"dt finding: --from needs git: {e}")
    prev = state.read("reviews", rid)
    if prev and prev.get("file_sha256") == digest:
        print(json.dumps({**prev, "already_recorded": True}, indent=2))
        return 0

    found = parse_lines(raw)
    ids, critical = [], []
    for sev, text in found:
        code, fid = record(repo, which, sev, text)
        if code:
            return _fail(f"dt finding: {fid}")
        ids.append(fid)
        if sev == "Critical":
            critical.append(fid)
    committed = None
    if ids:
        bs.git(repo.root, "add", "--", "tasks/plan.md")
        n_crit = f", {len(critical)} Critical" if critical else ""
        msg = f"{which} review, {pkg}: {len(ids)} findings{n_crit}\n"
        bs.git(repo.root, "commit", "-q", "-F", "-", "--", "tasks/plan.md", input=msg)
        committed = bs.head(repo.root)

    reservation = state.read("reserved", f"{rid}.reviewer")
    tasks = (reservation or {}).get("tasks")
    if tasks is None:
        build = dispatch.Build(repo, state)
        ph = next((p for p in build.phases if p.key == which), None)
        tasks = [t.id for t in ph.tasks if t.package == pkg] if ph else []
    if prev:
        tasks = list(dict.fromkeys(prev.get("tasks", []) + tasks))
    result = {"checkpoint": which, "pkg": pkg, "outcome": "critical" if critical else "passed",
              "findings": (prev or {}).get("findings", []) + ids,
              "critical": (prev or {}).get("critical", []) + critical,
              "counts": {s: sum(1 for sev, _ in found if sev == s) for s in SEVERITIES},
              "tasks": tasks, "file": str(path), "file_sha256": digest, "commit": committed, "time": bs.now()}
    state.write("reviews", rid, result)
    state.remove("reserved", f"{rid}.reviewer")
    state.log("review", review=rid, outcome=result["outcome"], findings=ids, critical=critical)
    print(json.dumps(result, indent=2))
    return 0


def run(args, repo) -> int:
    if args.from_file:
        return run_from(args, repo)
    if not (args.checkpoint and args.severity and args.text is not None):
        print("dt finding: give <checkpoint> <severity> <text>, or --from FILE")
        return 2
    severity = next((s for s in SEVERITIES if s.lower() == args.severity.lower()), None)
    if severity is None:
        print(f"dt finding: severity must be one of {', '.join(SEVERITIES)}")
        return 2
    which = _which(args.checkpoint)
    if which is None:
        print(f"dt finding: checkpoint must be a task ID (M1-T04) or `exit`, not {args.checkpoint!r}")
        return 2
    text, disposition = " ".join(args.text.split()), " ".join(args.disposition.split())
    if not text:
        print("dt finding: empty finding text")
        return 2
    code, msg = record(repo, which, severity, text, disposition)
    print(msg if code == 0 else f"dt finding: {msg}")
    return code
