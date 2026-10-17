#!/usr/bin/env python3
"""Arrange finished trajectory runs into the skill-creator benchmark layout:
bench/eval-<project>/<mode>/run-1/{outputs/, grading.json, timing.json}

outputs/ holds every final planning doc as final__<path with / as __> (docs/**, tasks/**, CONSTRAINTS.md,
AGENTS.md), a fixtures listing, one context__<task>.md per task (its `dt context` packet, which the blind judge
reads to decide whether the task is buildable from it alone), plan_snapshot.json (the final plan as one graph:
`dt plan --json`, else planexport's build from dtprobe facts, with nothing that names the mode), the transcript
and the doc-evolution table.

Usage: package.py [iteration-dir]  (relative to $EVAL_WS, default: a dev-team-workspace next to the marketplace repo)
"""
import json, os, shutil, subprocess, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dtrun, planexport  # noqa: E402
WS = pathlib.Path(os.environ.get("EVAL_WS", HERE.parents[3] / "dev-team-workspace"))
it = WS / sys.argv[1] if len(sys.argv) > 1 else WS / "iteration-1"
bench = it / "bench"
scn = json.loads((HERE / "scenarios.json").read_text())

for i, project in enumerate(["rl", "quant"]):
    ev = bench / f"eval-{i}-{project}"
    ev.mkdir(parents=True, exist_ok=True)
    stages = scn["projects"][project]["stages"]
    (ev / "eval_metadata.json").write_text(json.dumps({
        "eval_id": i, "eval_name": f"{project}-planning-trajectory",
        "prompt": f"{project.upper()} project planned with dev-team skills. INCREMENTAL = user reveals one stage at a time "
                  f"({' → '.join(s['name'] for s in stages)}), each going brief/idea → spec → architecture → pipelines → "
                  f"test plan (optional) → build plan, with build setup before the first build. "
                  f"ALL_AT_ONCE = user states every stage in the first message.",
        "assertions": []}, indent=1))
    for mode in ["incremental", "all_at_once"]:
        src = it / f"{project}-{mode.replace('_', '-')}" / "with_skill"
        if not (src / "grading.json").exists():
            continue
        run = ev / mode / "run-1"
        if run.exists():
            shutil.rmtree(run)
        out = run / "outputs"
        out.mkdir(parents=True)
        proj = src / "project"
        docs = proj / "docs"
        for p in sorted(docs.rglob("*.md")):
            shutil.copy(p, out / ("final__" + str(p.relative_to(docs)).replace("/", "__")))
        for p in sorted([*proj.glob("tasks/**/*.md"), *proj.glob("CONSTRAINTS.md"), *proj.glob("AGENTS.md")]):
            shutil.copy(p, out / ("final__" + str(p.relative_to(proj)).replace("/", "__")))
        for p in sorted(proj.glob("references/**/*")):
            if p.is_file():
                shutil.copy(p, out / ("reference__" + str(p.relative_to(proj / "references")).replace("/", "__")))
        fx = sorted(str(p.relative_to(proj)) for p in proj.glob("tests/fixtures/**/*") if p.is_file())
        (out / "fixtures.txt").write_text("\n".join(fx) + "\n")
        dt = dtrun.dt_path(src)
        facts = dtrun.probe(proj, dt)
        for plan in facts["plans"]:
            for t in plan["tasks"]:
                rc, packet, err = dtrun.run(proj, "context", t["id"], dt=dt)
                (out / f"context__{t['id']}.md").write_text(packet if rc == 0 else f"(dt context failed: {err.strip()})\n")
        snap = planexport.snapshot_body(proj, dt, facts)
        snap.pop("source", None)
        (out / "plan_snapshot.json").write_text(json.dumps({"schema": planexport.SCHEMA, **snap}, indent=1))
        turns = json.loads((src / "turns.json").read_text())
        md = [f"# Transcript — {project} / {mode}\n"]
        for t in turns:
            md.append(f"## Turn {t['turn']} · stage `{t['stage']}` · skills {t['skills']} · {t['seconds']}s\n")
            md.append(f"**User:**\n\n{t['user']}\n\n**Assistant:**\n\n{t['assistant']}\n\n**Docs after turn:**\n```\n{t['status']}\n```\n")
        (out / "transcript.md").write_text("\n".join(md))
        evo = ["| Turn | Stage | Skills | Docs changed | Statuses after |", "|---|---|---|---|---|"]
        for t in turns:
            ch = (t["docs_changed"].splitlines() or ["-"])
            files = ", ".join(l.split("|")[0].strip().replace("docs/", "") for l in ch if "|" in l) or "-"
            evo.append(f"| {t['turn']} | {t['stage']} | {', '.join(t['skills']) or '-'} | {files} | {t['status'].replace(chr(10), '<br>')} |")
        (out / "doc_evolution.md").write_text("# How the docs evolved\n\n" + "\n".join(evo) + "\n")
        g = json.loads((src / "grading.json").read_text())
        shutil.copy(src / "grading.json", run / "grading.json")
        (run / "timing.json").write_text(json.dumps({
            "total_tokens": g["extra"]["output_tokens"], "duration_ms": g["extra"]["agent_seconds"] * 1000,
            "total_duration_seconds": g["extra"]["agent_seconds"], "cost_usd": g["extra"]["cost_usd"]}, indent=1))
        (run / "transcript.md").write_text((out / "transcript.md").read_text())
        print("packaged", run)
