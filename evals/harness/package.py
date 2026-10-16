#!/usr/bin/env python3
"""Arrange finished trajectory runs into the skill-creator benchmark layout:
bench/eval-<project>/<mode>/run-1/{outputs/, grading.json, timing.json}

Usage: package.py [iteration-dir]  (relative to $EVAL_WS, default: a dev-team2-workspace next to the repo)
"""
import json, os, shutil, subprocess, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
WS = pathlib.Path(os.environ.get("EVAL_WS", HERE.parents[2] / "dev-team2-workspace"))
it = WS / sys.argv[1] if len(sys.argv) > 1 else WS / "iteration-1"
bench = it / "bench"
scn = json.loads((HERE / "scenarios.json").read_text())

for i, project in enumerate(["rl", "quant"]):
    ev = bench / f"eval-{i}-{project}"
    ev.mkdir(parents=True, exist_ok=True)
    stages = scn["projects"][project]["stages"]
    (ev / "eval_metadata.json").write_text(json.dumps({
        "eval_id": i, "eval_name": f"{project}-planning-trajectory",
        "prompt": f"{project.upper()} project planned with dev-team2 skills. INCREMENTAL = user reveals one stage at a time "
                  f"({' → '.join(s['name'] for s in stages)}), each going brief/idea → spec → architecture. "
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
        docs = src / "project" / "docs"
        for p in sorted(docs.rglob("*.md")):
            shutil.copy(p, out / ("final__" + str(p.relative_to(docs)).replace("/", "__")))
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
