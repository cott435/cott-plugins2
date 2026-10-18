"""Claim a reserved task half inside the agent's worktree and write its packet to .claude/packet.md.

build-phase.md §6.2.
Run by the agent as its first action, in its own linked worktree. It turns the reservation into a claim,
refuses a stale base (a landing the half needs isn't in HEAD's todo.md), merges the task's tests branch for an
implementer, writes `.claude/.task_writes` (the role's share of Writes:), `.claude/.check_pkg` (the package),
`.claude/.dt` (this dt.py, for the project's hook scripts), sets `refs/worktree/checks-base` to HEAD, links the
project's worktree links, and writes the packet to `.claude/packet.md`.

Worktree links: CONSTRAINTS.md may hold one line `**Worktree links:** data/raw, models/cache` naming gitignored
inputs (paths relative to the project root, comma-separated, `—` for none). Each that exists in the main checkout
and not in the worktree becomes a symlink to the main checkout's copy. `.env` files are never linked.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from .. import buildstate as bs
from .. import dispatch, graph, md
from . import context as ctx

LINKS_RE = re.compile(r"\*\*Worktree links:\*\*\s*(.*)$")
TAIL = 12          # lines of the previous rejection's detail file shown


def add_arguments(parser):
    parser.add_argument("task", help="task ID, e.g. M1-T03")
    parser.add_argument("--role", required=True, choices=bs.ROLES, help="the half this agent builds")


def done_condition(task: str, role: str) -> str:
    check = "scripts/check.sh collect" if role == "tester" else "scripts/check.sh gate"
    what = ("your intent tests lint clean, collect, and are red for the right reason" if role == "tester"
            else "the gate passes on your Writes")
    return (f"Done when `{check}` passes ({what}); the Stop hook runs it. End with one line: `DONE {task} {role}`. "
            f"If you can't finish: `python3 {bs.DT_PY} escalate <TEST-WRONG|NEEDS-DEP> \"<why>\"`, or "
            f"`python3 {bs.DT_PY} escalate CONTRACT-CHANGE \"<why>\" --type <the contract symbol>`, "
            f"then end with one line: `STOPPED {task} {role}: see dt escalate`.")


def worktree_links(repo) -> list[str]:
    doc = repo.constraints
    for line in doc.lines if doc else []:
        m = LINKS_RE.search(line)
        if m:
            return [p.strip().strip("`").strip("/") for p in md.split_list(m.group(1))
                    if p.strip().strip("`") not in ("", "—", "-", "none")]
    return []


def link(main: Path, wt: Path, rel: str) -> str:
    if Path(rel).name.startswith(".env") or rel.startswith(("/", "..")) or "/../" in rel:
        return f"{rel}: never linked"
    src, dst = main / rel, wt / rel
    if not src.exists():
        return f"{rel}: not in the main checkout"
    if dst.exists() or dst.is_symlink():
        return f"{rel}: already present"
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(src, dst)
    return f"{rel}: linked"


def refuse(msg: str) -> int:
    print(f"dt claim: {msg}", file=sys.stderr)
    return 1


def run(args, repo) -> int:
    task_id, role = args.task.upper(), args.role
    try:
        root = bs.toplevel(repo.root)
        state = bs.State(root)
        if bs.is_main_checkout(root):
            return refuse("run me inside the agent's own worktree, not the main checkout")
    except bs.GitError as e:
        return refuse(f"needs a git worktree: {e}")
    build = dispatch.Build(repo, state)
    task = build.by_id.get(task_id)
    if task is None:
        return refuse(f"{task_id} is not a task of this worktree's tasks/plan.md")
    if role not in graph.roles(task):
        return refuse(f"{task_id} is Mode {task.mode or '—'}: its halves are {', '.join(graph.roles(task))}")
    cid = dispatch.half_id(task_id, role)
    claim = state.read("claims", cid)
    if claim and bs.real(claim["worktree"]) != bs.real(root):
        return refuse(f"{cid} is already claimed in {claim['worktree']}")
    if claim is None:
        if state.read("reserved", cid) is None:
            return refuse(f"{cid} is not reserved: the driver reserves it with `dt ready --reserve`")
        # The base must hold every landing the half needs: a stale base fails here, not at merge.
        need = ([a for a in graph.ancestors(build.tasks, task_id) if build.by_id[a].kind == "interface"]
                if role == "tester" else [d for d in task.depends_on if d in build.by_id])
        missing = [d for d in need if d not in build.done]
        if missing:
            return refuse(f"stale base: HEAD's tasks/todo.md lacks the landing of {', '.join(missing)}; "
                          "the worktree must branch from the build branch's head")
        if role == "implementer":
            branch = bs.tests_branch(task_id)
            if not bs.ref_exists(root, f"refs/heads/{branch}"):
                return refuse(f"{branch} doesn't exist: the tester half hasn't landed")
            merged = bs.git(root, "merge", "--no-edit", "-q", branch, check=False)
            if merged.returncode != 0:
                bs.git(root, "merge", "--abort", check=False)
                return refuse(f"merging {branch} failed: {(merged.stderr or merged.stdout).strip()}")

    writes = bs.role_writes(task, role)
    claude = root / ".claude"
    claude.mkdir(exist_ok=True)
    (claude / ".task_writes").write_text("".join(f"{w}\n" for w in writes), encoding="utf-8")
    (claude / ".check_pkg").write_text(f"{task.package}\n", encoding="utf-8")
    (claude / ".dt").write_text(f"{bs.DT_PY}\n", encoding="utf-8")
    links = worktree_links(repo)
    state.exclude(["# dt build: files dt claim writes into a worktree"] + [f"/{p}" for p in bs.CLAIM_FILES]
                  + [f"/{p}" for p in links])
    linked = [link(bs.main_checkout(root), root, p) for p in links]

    if claim is None:
        bs.git(root, "update-ref", "refs/worktree/checks-base", "HEAD")
        claim = {"id": cid, "task": task_id, "role": role, "agent_type": dispatch.agent_type(role),
                 "pkg": task.package, "worktree": str(root), "branch": bs.current_branch(root),
                 "base": bs.head(root), "time": bs.now(), "finished": False}
        state.write("claims", cid, claim)
        state.remove("reserved", cid)
        state.log("claim", claim=cid, task=task_id, role=role, worktree=str(root), branch=claim.get("branch"),
                  base=claim["base"])

    p = ctx.packet(repo, task, writes=writes, tester=role == "tester")
    head = (f"# Packet: {task_id} {role}\n"
            f"You are the {role} for {task_id}. Your edit boundary is your Writes below (`.claude/.task_writes`); "
            "the guard blocks everything else.\n\n"
            f"{done_condition(task_id, role)}\n\n")
    text = head + p["text"]
    (claude / "packet.md").write_text(text, encoding="utf-8")

    lines = [f"packet: {claude / 'packet.md'} ({text.count(chr(10))} lines; read it in full)",
             f"task: {task_id} {task.title} · role {role} · package {task.package or '—'} · kind {task.kind or '—'}",
             f"writes: {', '.join(writes) or 'none'}",
             f"done: {done_condition(task_id, role)}"]
    if p["problems"]:
        lines.append("packet problems: " + "; ".join(p["problems"]))
    if linked:
        lines.append("links: " + "; ".join(linked))
    decided = state.read("resolved", task_id) or {}
    if decided.get("test_stands") and role == "implementer":
        lines.append("the user decided the intent tests stand: make them pass, don't escalate them again"
                     + (f" ({decided['note']})" if decided.get("note") else ""))
    last = (state.read("rejects", cid) or {}).get("last")
    if last:
        lines.append(f"previous rejection: {last.get('reject')}"
                     + (f" ({last['kind']})" if last.get("kind") else "") + f", details in {last.get('detail_file')}")
        try:
            detail = Path(last["detail_file"]).read_text(encoding="utf-8").splitlines()
            lines += [f"  {x}" for x in detail[:TAIL]]
        except (OSError, KeyError):
            pass
    print("\n".join(lines))
    return 0

