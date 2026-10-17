#!/usr/bin/env python3
"""Dry run of the harness with no model calls: stage and check the plugin, then fake a trajectory from dt's
sample project (scripts/tests/fixtures/quant, a valid single-package project mid-M1) and grade it.

The fixture is replayed one planning layer per turn (brief → spec → architecture → pipelines → tests → plan →
build setup, with reference intake before the M2 idea), then the M1 code it already contains lands as a final "build" turn. So most assertions should
pass; the expected failures are the ones the fixture can't meet (it isn't a finished four-stage quant run).

Usage: dryrun.py [out-dir]   (default: a fresh temp dir; printed at the end)
"""
import json, shutil, subprocess, sys, tempfile, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver, dtrun, plugin  # noqa: E402

FIXTURE = HERE.parents[1] / "scripts" / "tests" / "fixtures" / "quant"
# (skill, paths) per turn, in planning order; the user approves each.
LAYERS = [
    ("idea-refine", ["docs/brief.md", "docs/roadmap.md"]),
    ("spec-writing", ["docs/spec.md"]),
    ("architecture-design", ["docs/architecture.md", "docs/packages/quant/contract.md"]),
    ("reference-intake", ["references", "docs/references.md"]),  # M2's reference arrives with the M2 idea
    ("idea-refine", ["docs/ideas"]),
    ("pipeline-design", ["docs/packages/quant/pipelines.md"]),
    ("test-planning", ["docs/packages/quant/tests.md", "tests/fixtures"]),
    ("build-planning", ["tasks", "AGENTS.md"]),
    ("build-setup", ["CONSTRAINTS.md", ".claude"]),
    (None, ["src"]),  # M1-T01 already built: the fixture is mid-M1
]


def copy_layer(fixture, proj, paths):
    """Copy a layer's paths from the fixture; a path the fixture doesn't have (yet) is skipped."""
    for p in paths:
        src, dst = fixture / p, proj / p
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy(src, dst)


def intake_agents(proj):
    """What reference-intake's stream would show: one read-only subagent per reference file."""
    refs = sorted(p for p in (proj / "references").rglob("*") if p.is_file()) if (proj / "references").is_dir() else []
    return [{"subagent_type": "general-purpose", "description": f"Summarize {p.name}",
             "prompt": f"Read {p.relative_to(proj)} and draft its reference entry."} for p in refs]


def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="dt-dryrun-")).resolve()
    run = out / "quant-incremental" / "with_skill"
    if run.exists():
        shutil.rmtree(run)
    run.mkdir(parents=True)

    root = plugin.stage(run / "plugin")
    probs = plugin.check(root)
    print(f"plugin staged at {root}: {'ok' if not probs else probs}")
    for s in plugin.skills_missing(root):
        print(f"  warning: skills/{s} has no SKILL.md yet")
    dt = root / "scripts" / "dt.py"

    proj = run / "project"
    proj.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=proj)
    driver.commit(proj, "turn 0")
    turns = []
    stage = "data"
    for n, (skill, paths) in enumerate(LAYERS, 1):
        copy_layer(FIXTURE, proj, paths)
        driver.commit(proj, f"turn {n}")
        _, status = driver.snapshot(proj, dt)
        stage = "structure_portfolios" if skill == "reference-intake" else stage
        turns.append({"turn": n, "user": "Approved." if n > 1 else "Plan my quant lab.", "assistant": "(replayed)",
                      "skills": [f"dev-team:{skill}"] if skill else [], "tools": [], "seconds": 0,
                      "usage": {}, "docs_changed": "", "status": status, "stage": stage,
                      "agents": intake_agents(proj) if skill == "reference-intake" else []})
    (run / "turns.json").write_text(json.dumps(turns, indent=1))
    (run / "summary.json").write_text(json.dumps({"trajectory": "quant-incremental (dry run)", "turns": len(turns),
                                                  "stages_reached": 2, "finished": True, "stop_reason": "dry run",
                                                  "references": [p.name for p in sorted((proj / "references").glob("*"))]}))
    r = subprocess.run([sys.executable, str(HERE / "grade.py"), str(run)], capture_output=True, text=True)
    print(r.stdout + r.stderr)
    print(f"run dir: {run}")
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
