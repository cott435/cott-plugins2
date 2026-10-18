#!/usr/bin/env python3
"""Replan and Advance simulation (design/planning-stage.md §13): apply a scripted state change to a copy of a
finished trajectory's project and assert the modes `dt status` reports. No model calls.

Replan:  edit a step of a pipeline the active milestone uses and put its pipelines.md back to Draft (what
         pipeline-design Revise does) → pipeline-design `revise`, build-planning `blocked` (waiting for approval);
         re-approve it with a later Last updated → build-planning `replan`, the doc in `changed_since_plan`;
         a task Blocked as well → `replan`, task listed; both files restored → back to the starting mode.
Advance: tick every todo item with `dt tick` → not yet `advance` (exit checkpoint open); tick the exit
         checkpoint → `advance`; `dt archive` → plan stubbed, milestone derived Done, lint clean.
Ready (interface-first plans, design/interface-first-design.md §9.1): on a fresh plan `dt ready` lists only the
         interface task; once it is ticked, every spine and every split task's tester half; a pipeline's wiring task
         isn't ready until all its spines are ticked.
Contract change: edit a type the interface task froze and re-approve the contract → build-planning `replan`, with
         the tasks that read the type listed.
Probe gate (design/probes.md §3.3, `simulate_probes`): with the active plan set aside, a probe whose Milestones
         name that milestone set back to Ready → build-planning `blocked` with it in `probes_blocking`; the same
         probe Answered → no longer blocking. Not applicable without a probe, or with a dt that has no
         `probes_blocking` yet.

Usage: simulate.py <project-dir> [<dt.py>]   prints one line per check; exit 1 if any fails
"""
import json, re, shutil, subprocess, sys, tempfile, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dtrun, probefacts  # noqa: E402

GIT = ["git", "-c", "user.email=e@e", "-c", "user.name=sim"]


def git(proj, *a):
    return subprocess.run([*GIT, *a], cwd=proj, capture_output=True, text=True)


def copy_project(src, dest):
    shutil.copytree(src, dest, symlinks=True,
                    ignore=shutil.ignore_patterns(".venv", "__pycache__", ".ruff_cache", ".mypy_cache", ".pytest_cache"))
    if not (dest / ".git").exists():
        git(dest, "init", "-q")
    git(dest, "add", "-A")
    git(dest, "commit", "-q", "--no-verify", "-m", "sim base")  # `revise` compares the working copy with HEAD
    return dest


def bp(proj, dt):
    return dtrun.run_json(proj, "status", "--skill", "build-planning", dt=dt)


def pd(proj, dt):
    return dtrun.run_json(proj, "status", "--skill", "pipeline-design", dt=dt)


def section_bounds(lines, heading_re):
    """(start, end) of the first `##`/`###` section whose heading matches; end is the next heading at the same or higher level."""
    for i, l in enumerate(lines):
        m = re.match(r"^(#{2,3}) ", l)
        if m and re.match(heading_re, l):
            lvl = len(m.group(1))
            for j in range(i + 1, len(lines)):
                h = re.match(r"^(#{1,6}) ", lines[j])
                if h and len(h.group(1)) <= lvl:
                    return i, j
            return i, len(lines)
    return None


def set_status(path, old, new):
    lines = path.read_text().splitlines(keepends=True)
    for i, l in enumerate(lines):
        if "**Status:**" in l:
            lines[i] = re.sub(rf"(\*\*Status:\*\*\s*){old}\b", rf"\g<1>{new}", l, count=1)
            break
    path.write_text("".join(lines))


def edit_first_step(path, pid):
    """Rewrite the Spine version cell (else the last-but-one cell) of the pipeline's first step row."""
    lines = path.read_text().splitlines(keepends=True)
    b = section_bounds([l.rstrip("\n") for l in lines], rf"^#{{2,3}} {re.escape(pid)}:")
    if not b:
        return None
    head = None
    for i in range(*b):
        if not lines[i].lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if head is None:
            head = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        col = next((k for k, h in enumerate(head) if h.lower().startswith("spine")), len(cells) - 2)
        cells[col] = cells[col] + " (revised: shrink before cleaning)"
        lines[i] = "| " + " | ".join(cells) + " |\n"
        path.write_text("".join(lines))
        return cells[1].strip("`") if len(cells) > 1 else "?"
    return None


def set_last_updated(path, date):
    lines = path.read_text().splitlines(keepends=True)
    for i, l in enumerate(lines):
        if "**Last updated:**" in l:
            lines[i] = re.sub(r"(\*\*Last updated:\*\*\s*)\d{4}-\d{2}-\d{2}", rf"\g<1>{date}", l, count=1)
            break
    path.write_text("".join(lines))


def add_blocked(path, task_id, reason):
    lines = path.read_text().splitlines(keepends=True)
    for i, l in enumerate(lines):
        if re.match(rf"^#{{2,4}} {re.escape(task_id)}:", l):
            lines.insert(i + 2, f"**Blocked:** {reason}\n")  # after the heading and its first field line
            path.write_text("".join(lines))
            return True
    return False


def tick_exit(path):
    lines = path.read_text().splitlines()
    b = section_bounds(lines, r"^#{2,3} Checkpoint.*exit")
    if not b:
        return False
    for i in range(*b):
        lines[i] = re.sub(r"^(\s*[-*] )\[ \]", r"\1[x]", lines[i])
    path.write_text("\n".join(lines) + "\n")
    return True


def set_todo(proj, done):
    """Rewrite tasks/todo.md so exactly the tasks in `done` are checked."""
    path = proj / "tasks" / "todo.md"
    lines = path.read_text().splitlines()
    for i, l in enumerate(lines):
        m = re.match(r"^(\s*[-*] \[)[ xX](\] (M\d+-T\d{2,})\b.*)$", l)
        if m:
            lines[i] = m.group(1) + ("x" if m.group(3) in done else " ") + m.group(2)
    path.write_text("\n".join(lines) + "\n")


def ready(proj, dt):
    """(task IDs `dt ready --json` lists, raw entries), or (None, why) when dt has no ready command."""
    rc, out, err = dtrun.run(proj, "ready", "--json", dt=dt)
    try:
        d = json.loads(out)
    except Exception:
        return None, f"dt ready: rc={rc} {(err or out).strip()[-160:]}"
    items = d if isinstance(d, list) else d.get("ready") or d.get("tasks") or []
    return [x.get("id") if isinstance(x, dict) else str(x) for x in items], items


def task_ids_in(d, skip=("next_task", "progress", "milestone", "next ids", "next_ids")):
    """Every task ID anywhere in a dt JSON answer, apart from the fields that always name one."""
    if isinstance(d, dict):
        return set().union(set(), *(task_ids_in(v) for k, v in d.items() if k not in skip))
    if isinstance(d, list):
        return set().union(set(), *(task_ids_in(v) for v in d))
    return set(re.findall(r"M\d+-T\d{2,}", d)) if isinstance(d, str) else set()


def interface_first(src, dt, tmp, plan, check):
    """The four `dt ready` / contract-change replays, on a plan whose tasks carry Kind (else one failing check)."""
    tasks = plan["tasks"]
    iface = [t["id"] for t in tasks if t.get("kind") == "interface"]
    if not iface:
        check("Ready simulation: the active plan has an interface task (`**Kind:** interface`)", False,
              f"kinds: {sorted({t.get('kind') or '—' for t in tasks})}")
        return
    proj = copy_project(src, tmp / "ready")
    declared = set(plan.get("interface_symbols", []))
    spines = [t["id"] for t in tasks if t.get("kind") == "spine"]
    testers = [t["id"] for t in tasks if t["mode"] == "split" and t.get("read_symbols")
               and set(t["read_symbols"]) <= declared]
    set_todo(proj, set())
    got, raw = ready(proj, dt)
    check("Ready simulation: on a fresh plan `dt ready` lists only the interface task",
          got is not None and sorted(got) == sorted(iface), f"ready={got if got is not None else raw}; interface={iface}")
    set_todo(proj, set(iface))
    got, raw = ready(proj, dt)
    missing = [i for i in spines + testers if got is None or i not in got]
    check("Ready simulation: after the interface task, `dt ready` lists every spine and every split task's tester half",
          got is not None and spines and not missing,
          f"spines {spines}; tester halves {testers}; missing: {missing}; ready={got if got is not None else raw}")
    # Wiring: everything ticked except one pipeline's wiring, its last spine, and whatever follows them.
    by_id = {t["id"]: t for t in tasks}
    wiring = next((t for t in tasks if t.get("kind") == "wiring"
                   and [s for s in spines if by_id[s]["step"].split(".")[0] == t["step"].split(".")[0]]), None)
    if not wiring:
        check("Ready simulation: a pipeline's wiring task waits for all its spines", False, "no wiring task with spines on its pipeline")
    else:
        own = [s for s in spines if by_id[s]["step"].split(".")[0] == wiring["step"].split(".")[0]]
        held = {wiring["id"], own[-1]}
        anc = dtrun.ancestors(tasks)
        later = {t["id"] for t in tasks if held & anc[t["id"]]}
        set_todo(proj, {t["id"] for t in tasks} - held - later)
        before, raw = ready(proj, dt)
        set_todo(proj, {t["id"] for t in tasks} - {wiring["id"]} - later)
        after, _ = ready(proj, dt)
        check(f"Ready simulation: {wiring['id']} (wiring {wiring['step']}) isn't ready until its spines {own} are ticked",
              before is not None and wiring["id"] not in before and wiring["id"] in (after or []),
              f"with {own[-1]} open: {before if before is not None else raw}; with it ticked: {after}")
    # Contract change: a frozen type edited and the contract re-approved after the plan.
    proj = copy_project(src, tmp / "contract")
    facts = dtrun.probe(proj, dt)
    readers = {}
    for t in tasks:
        for sym in t.get("read_symbols", []):
            readers.setdefault(sym, []).append(t["id"])
    typ = next((s for s in facts.get("symbols", []) if s["is_type"] and s["id"] in declared and readers.get(s["id"])), None)
    if not typ:
        check("Contract-change simulation: a frozen type that tasks read exists", False, f"declared: {sorted(declared)[:8]}")
        return
    doc = proj / typ["doc"]
    lines = doc.read_text().splitlines(keepends=True)
    b = section_bounds([l.rstrip("\n") for l in lines], rf"^### {re.escape(typ['id'])}:")
    lines.insert(b[1] if b else len(lines), "- **Invariants:** (revised) one more field the interface lacked\n")
    doc.write_text("".join(lines))
    set_last_updated(doc, "2099-01-01")
    s_bp = bp(proj, dt)
    listed = task_ids_in(s_bp)
    rc, out, _ = dtrun.run(proj, "plan", "--json", dt=dt)
    try:
        cc = [e for e in json.loads(out).get("edges", []) if e.get("kind") == "contract-change"]
    except Exception:
        cc = []
    want = [i for i in readers[typ["id"]] if i not in iface]
    check(f"Contract-change simulation: editing frozen {typ['id']} → build-planning Replan with its readers {want} listed",
          s_bp.get("mode") == "replan" and (set(want) <= listed or bool(cc)),
          f"mode={s_bp.get('mode')} changed_since_plan={s_bp.get('changed_since_plan')} tasks listed={sorted(listed)[:10]} "
          f"contract-change edges={cc[:3]}")


def set_probe_status(path, pid, status):
    """Rewrite one PB entry's header-line Status (a value may itself hold `·`: `Answered · pass · <date>`)."""
    lines = path.read_text().splitlines(keepends=True)
    for i, l in enumerate(lines):
        if re.match(rf"^#{{2,3}} {re.escape(pid)}:", l):
            for j in range(i + 1, min(i + 4, len(lines))):
                if "**Status:**" in lines[j]:
                    lines[j] = re.sub(r"(\*\*Status:\*\*\s*).*?(?=\s*·\s*\*\*[A-Z][\w ]*:\*\*|\s*$)",
                                      lambda m: m.group(1) + status, lines[j], count=1)
                    path.write_text("".join(lines))
                    return True
    return False


def simulate_probes(src, dt=None):
    """One record for plan_blocked_while_open: {text, passed, evidence}, or {text, na: True, evidence: why}."""
    dt = dt or dtrun.REPO_DT
    src = pathlib.Path(src).resolve()
    text = "Probe simulation: with the plan set aside, the probes on its milestone Ready → build-planning blocked on them; Answered → not"
    pb = src / "docs" / "probes.md"
    entries = probefacts.parse_probes(pb.read_text(errors="ignore"))["entries"] if pb.exists() else []
    if not entries:
        return {"text": text, "na": True, "evidence": "no probes in docs/probes.md"}
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dt-sim-probe-"))
    try:
        proj = copy_project(src, tmp / "probe")
        facts = dtrun.probe(proj, dt)
        plan = next((p for p in facts["plans"] if p["kind"] == "plan" and p["dev_team"] and p["milestone"]), None)
        ms = plan["milestone"] if plan else (facts["roadmap"][0]["id"] if facts["roadmap"] else "")
        stage = next((r.get("stage") for r in facts["roadmap"] if r["id"] == ms), "")
        es = [e for e in entries if ms in e["milestones"] or (stage and stage in e["milestones"])] or entries[:1]
        ids = [e["id"] for e in es]
        for rel in ("tasks/plan.md", "tasks/todo.md"):
            if (proj / rel).exists():
                (proj / rel).unlink()
        shutil.rmtree(proj / "tasks" / "queued", ignore_errors=True)  # a queued plan would put dt in extend, not New
        pb = proj / "docs" / "probes.md"
        for pid in ids:
            set_probe_status(pb, pid, "Ready")
        open_ = bp(proj, dt)
        if "probes_blocking" not in open_:
            return {"text": text, "na": True, "evidence": f"dt has no probes_blocking yet (build-planning mode={open_.get('mode')} "
                                                           f"{open_.get('_error', '')})"}
        for pid in ids:
            set_probe_status(pb, pid, "Answered · pass · 2099-01-01")
        done = bp(proj, dt)
        blocked = open_.get("mode") == "blocked" and all(pid in json.dumps(open_.get("probes_blocking")) for pid in ids)
        freed = done.get("mode") != "blocked" and not any(pid in json.dumps(done.get("probes_blocking")) for pid in ids)
        return {"text": text.replace("the probes", ", ".join(ids)).replace("its milestone", ms or "the first milestone"),
                "passed": blocked and freed,
                "evidence": f"{ms} plan set aside; {', '.join(ids)} Ready → mode={open_.get('mode')} probes_blocking={open_.get('probes_blocking')}; "
                            f"Answered → mode={done.get('mode')} probes_blocking={done.get('probes_blocking')}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def simulate(src, dt=None):
    """[{text, passed, evidence}] for the Replan and Advance checks, run on copies of <src>."""
    dt = dt or dtrun.REPO_DT
    src = pathlib.Path(src).resolve()
    R = []

    def check(text, passed, evidence):
        R.append({"text": text, "passed": bool(passed), "evidence": str(evidence)[:600]})

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dt-sim-"))
    try:
        # ---- Replan
        proj = copy_project(src, tmp / "replan")
        facts = dtrun.probe(proj, dt)
        plan = next((p for p in facts["plans"] if p["kind"] == "plan" and p["dev_team"] and p["milestone"]), None)
        if not plan:
            check("Replan/Advance simulation: an active milestone plan exists to simulate on", False,
                  f"plans: {[(p['doc'], p['status']) for p in facts['plans']]}")
            return R
        row = next((r for r in facts["roadmap"] if r["id"] == plan["milestone"]), {"pipelines": []})
        todo = {t["id"] for t in plan["tasks"]}
        start_mode = bp(proj, dt).get("mode")
        pls = [p for p in facts["pipelines"] if p["id"] in row["pipelines"] and not p["system"]
               and p["doc"].endswith("pipelines.md") and p["doc_status"] == "Approved"]
        # Prefer a pipeline with a task still to build, so a Blocked task is realistic.
        steps_of = lambda pid: [t for t in plan["tasks"] if t["step"].startswith(pid + ".")]
        pls.sort(key=lambda p: not steps_of(p["id"]))
        if not pls:
            check("Replan simulation: the active milestone has an Approved package pipeline to revise", False,
                  f"milestone {plan['milestone']} pipelines {row['pipelines']}")
        else:
            p = pls[0]
            doc = proj / p["doc"]
            step = edit_first_step(doc, p["id"])
            set_status(doc, "Approved", "Draft")
            s_pd, s_bp = pd(proj, dt), bp(proj, dt)
            pkg_mode = (s_pd.get("packages") or {}).get(p["package"] or "", s_pd.get("mode"))
            check(f"Replan simulation: editing {p['id']} step `{step}` (pipelines.md back to Draft) → pipeline-design Revise",
                  s_pd.get("mode") == "revise" and pkg_mode == "revise",
                  f"mode={s_pd.get('mode')} packages={s_pd.get('packages')} {s_pd.get('_error', '')}")
            check(f"Replan simulation: while {p['id']} is Draft → build-planning blocked (waiting for approval)",
                  s_bp.get("mode") == "blocked", f"mode={s_bp.get('mode')} draft_pipelines={s_bp.get('draft_pipelines')} {s_bp.get('_error', '')}")
            # Re-approved after the plan was written: the plan must catch up.
            set_status(doc, "Draft", "Approved")
            set_last_updated(doc, "2099-01-01")
            s_bp = bp(proj, dt)
            changed = s_bp.get("changed_since_plan") or []
            check(f"Replan simulation: {p['id']} re-approved after the plan → build-planning Replan, doc listed",
                  s_bp.get("mode") == "replan" and any(p["doc"] in str(x) for x in changed),
                  f"mode={s_bp.get('mode')} changed_since_plan={changed}")
            # A task on the changed step is paused as well.
            task = next((t["id"] for t in steps_of(p["id"])), None) or next(iter(sorted(todo)), None)
            add_blocked(proj / plan["doc"], task, f"{p['id']} step revised")
            s_bp = bp(proj, dt)
            check(f"Replan simulation: {task} Blocked → build-planning Replan, task listed",
                  s_bp.get("mode") == "replan" and any(str(x).startswith(str(task)) for x in s_bp.get("blocked_tasks", [])),
                  f"mode={s_bp.get('mode')} blocked_tasks={s_bp.get('blocked_tasks')}")
            git(proj, "checkout", "HEAD", "--", plan["doc"], p["doc"])
            s_bp = bp(proj, dt)
            check(f"Replan simulation: both files restored → build-planning back to `{start_mode}`", s_bp.get("mode") == start_mode,
                  f"mode={s_bp.get('mode')}")

        # ---- Advance
        proj = copy_project(src, tmp / "advance")
        items = [t["id"] for t in plan["tasks"]]
        bad = [i for i in items if dtrun.run(proj, "tick", i, dt=dt)[0] != 0]
        s_bp = bp(proj, dt)
        check("Advance simulation: every todo item ticked, exit checkpoint open → not yet Advance",
              not bad and s_bp.get("mode") != "advance" and s_bp.get("progress", "").split("/")[0] == s_bp.get("progress", "/").split("/")[-1],
              f"tick failures={bad} mode={s_bp.get('mode')} progress={s_bp.get('progress')}")
        ticked = tick_exit(proj / "tasks" / "plan.md")
        s_bp = bp(proj, dt)
        check("Advance simulation: exit checkpoint ticked too → build-planning Advance",
              ticked and s_bp.get("mode") == "advance", f"exit checkpoint found={ticked} mode={s_bp.get('mode')}")
        rc, out, err = dtrun.run(proj, "archive", "--date", "2026-12-01", dt=dt)
        after = dtrun.probe(proj, dt)
        ms = next((r for r in after["roadmap"] if r["id"] == plan["milestone"]), {})
        stub = (proj / "tasks" / "plan.md").read_text() if (proj / "tasks" / "plan.md").exists() else ""
        lint = dtrun.run_json(proj, "lint", dt=dt)
        s_bp = bp(proj, dt)
        check("Advance simulation: `dt archive` stubs the plan, the milestone derives Done, lint stays clean",
              rc == 0 and "Between milestones" in stub and ms.get("derived") == "Done" and lint.get("errors") == 0,
              f"archive rc={rc} {(out or err).strip()[:160]} · {plan['milestone']}={ms.get('derived')} · "
              f"lint errors={lint.get('errors')} · next build-planning mode={s_bp.get('mode')}")

        # ---- Ready and contract change (interface-first)
        interface_first(src, dt, tmp, plan, check)
        return R
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    res = simulate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    res.append(simulate_probes(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
    for r in res:
        print(("N/A  " if r.get("na") else "PASS " if r["passed"] else "FAIL ") + r["text"] + "  — " + r["evidence"][:200])
    sys.exit(0 if all(r.get("na") or r["passed"] for r in res) else 1)
