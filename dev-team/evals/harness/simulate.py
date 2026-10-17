#!/usr/bin/env python3
"""Replan and Advance simulation (design/planning-stage.md §13): apply a scripted state change to a copy of a
finished trajectory's project and assert the modes `dt status` reports. No model calls.

Replan:  edit a step of a pipeline the active milestone uses and put its pipelines.md back to Draft (what
         pipeline-design Revise does) → pipeline-design `revise`, build-planning `blocked` (waiting for approval);
         re-approve it with a later Last updated → build-planning `replan`, the doc in `changed_since_plan`;
         a task Blocked as well → `replan`, task listed; both files restored → back to the starting mode.
Advance: tick every todo item with `dt tick` → not yet `advance` (exit checkpoint open); tick the exit
         checkpoint → `advance`; `dt archive` → plan stubbed, milestone derived Done, lint clean.

Usage: simulate.py <project-dir> [<dt.py>]   prints one line per check; exit 1 if any fails
"""
import re, shutil, subprocess, sys, tempfile, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dtrun  # noqa: E402

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
        return R
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    res = simulate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    for r in res:
        print(("PASS " if r["passed"] else "FAIL ") + r["text"] + "  — " + r["evidence"][:200])
    sys.exit(0 if all(r["passed"] for r in res) else 1)
