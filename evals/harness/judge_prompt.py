#!/usr/bin/env python3
"""Fill blind_judge_prompt.md for one pair of packaged runs and print it (hand it to a fresh agent session).

Usage: judge_prompt.py <project> <dir-A> <dir-B> <out-json> [--extra TEXT]
  dir-A / dir-B: packaged outputs dirs (bench/eval-*/<mode>/run-1/outputs from package.py). Shuffle A and B
  yourself and keep the key; the judge must not know which is which.
"""
import argparse, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
COMMON_CONTENT = ["stage_completeness", "internal_consistency", "right_sizing", "pipeline_clarity", "task_buildability"]
CONTENT = {"quant": ["quant_soundness", "null_hypothesis_handoff", "reference_use"] + COMMON_CONTENT,
           "rl": ["rl_soundness"] + COMMON_CONTENT}
STRUCTURE = ["organization", "readability_for_solo_learner", "ease_of_finding_next_build_step", "layout_sensibility"]

ap = argparse.ArgumentParser()
ap.add_argument("project", choices=sorted(CONTENT))
ap.add_argument("dir_a")
ap.add_argument("dir_b")
ap.add_argument("out")
ap.add_argument("--extra", default="")
a = ap.parse_args()
facts = json.loads((HERE / "scenarios.json").read_text())["projects"][a.project]
fill = {"FACTS": "\n".join(f"- {f}" for f in facts["facts"]) + "\n\nStages, in order:\n" +
                 "\n".join(f"- {s['reveal']}" for s in facts["stages"]),
        "DIR_A": str(pathlib.Path(a.dir_a).resolve()), "DIR_B": str(pathlib.Path(a.dir_b).resolve()),
        "CONTENT_KEYS": ", ".join(CONTENT[a.project]), "STRUCTURE_KEYS": ", ".join(STRUCTURE),
        "EXTRA": a.extra, "OUT_PATH": str(pathlib.Path(a.out).resolve())}
text = (HERE / "blind_judge_prompt.md").read_text()
for k, v in fill.items():
    text = text.replace("{" + k + "}", v)
print(text)
