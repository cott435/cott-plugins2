#!/usr/bin/env python3
"""Fill blind_judge_prompt.md for one pair of packaged runs (hand each prompt to a fresh agent session), and average
the two orders.

Usage:
  judge_prompt.py <project> <dir-1> <dir-2> <out-json> [--extra TEXT]
      Print one prompt with dir-1 as Set A. Shuffle the dirs yourself and keep the key.
  judge_prompt.py <project> <dir-1> <dir-2> <out-json> --both <prompt-dir> [--labels L1 L2] [--extra TEXT]
      Write <prompt-dir>/prompt-AB.md (dir-1 is A; the judge writes <out>.AB.json) and prompt-BA.md (dir-2 is A;
      <out>.BA.json), plus the key <out>.key.json. Labels (e.g. incremental all_at_once) go in the key only.
  judge_prompt.py average <out-json>
      Read <out>.AB.json, <out>.BA.json and the key; write <out-json> with each dir's scores averaged over the
      two orders (keyed by label), the winner per order, and the items whose two scores differ by more than 1.
  dir-1 / dir-2: packaged outputs dirs (bench/eval-*/<mode>/run-1/outputs from package.py).
"""
import argparse, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
COMMON_CONTENT = ["stage_completeness", "internal_consistency", "right_sizing", "milestone_quality", "pipeline_clarity",
                  "interface_quality", "dependency_graph_soundness", "task_buildability"]
CONTENT = {"quant": ["quant_soundness", "null_hypothesis_handoff", "reference_use"] + COMMON_CONTENT,
           "rl": ["rl_soundness"] + COMMON_CONTENT}
STRUCTURE = ["organization", "readability_for_solo_learner", "ease_of_finding_next_build_step", "layout_sensibility"]


def fill(project, dir_a, dir_b, out, extra):
    facts = json.loads((HERE / "scenarios.json").read_text())["projects"][project]
    values = {"FACTS": "\n".join(f"- {f}" for f in facts["facts"]) + "\n\nStages, in order:\n" +
                       "\n".join(f"- {s['reveal']}" for s in facts["stages"]),
              "DIR_A": str(pathlib.Path(dir_a).resolve()), "DIR_B": str(pathlib.Path(dir_b).resolve()),
              "CONTENT_KEYS": ", ".join(CONTENT[project]), "STRUCTURE_KEYS": ", ".join(STRUCTURE),
              "EXTRA": extra, "OUT_PATH": str(pathlib.Path(out).resolve())}
    text = (HERE / "blind_judge_prompt.md").read_text()
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    return text


def sibling(out, tag):
    out = pathlib.Path(out)
    return out.with_name(f"{out.stem}.{tag}.json")


def average(out):
    key = json.loads(sibling(out, "key").read_text())
    runs = {o: json.loads(sibling(out, o).read_text()) for o in ("AB", "BA")}
    per = {"1": [], "2": []}  # each dir's rubric block, once per order
    for o, d in runs.items():
        for letter, which in key[o].items():
            per[which].append(d["rubric"][letter])
    scores, split = {}, []
    for which, blocks in per.items():
        label = key["labels"][which]
        sc = {}
        for part in ("content", "structure"):
            items = sorted({k for b in blocks for k in (b.get(part) or {})})
            sc[part] = {k: round(sum((b.get(part) or {}).get(k, 0) for b in blocks) / len(blocks), 2) for k in items}
            split += [f"{label} {k}: {[(b.get(part) or {}).get(k) for b in blocks]}" for k in items
                      if len({(b.get(part) or {}).get(k) for b in blocks}) > 1
                      and max((b.get(part) or {}).get(k, 0) for b in blocks) - min((b.get(part) or {}).get(k, 0) for b in blocks) > 1]
        for s in ("content_score", "structure_score", "overall_score"):
            sc[s] = round(sum(b.get(s, 0) for b in blocks) / len(blocks), 2)
        scores[label] = sc
    winners = {o: key["labels"][key[o][d.get("winner", "")]] if d.get("winner") in key[o] else None for o, d in runs.items()}
    res = {"labels": key["labels"], "dirs": {key["labels"][k]: key["dirs"][k] for k in ("1", "2")}, "orders": 2,
           "scores": scores, "winner_by_order": winners, "order_disagreements": split}
    pathlib.Path(out).write_text(json.dumps(res, indent=1))
    return res


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "average":
        if len(sys.argv) != 3:
            sys.exit("usage: judge_prompt.py average <out-json>")
        res = average(sys.argv[2])
        print(json.dumps({k: v["overall_score"] for k, v in res["scores"].items()}), res["winner_by_order"])
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("project", choices=sorted(CONTENT))
    ap.add_argument("dir_1")
    ap.add_argument("dir_2")
    ap.add_argument("out")
    ap.add_argument("--extra", default="")
    ap.add_argument("--both", metavar="PROMPT_DIR", help="write both orders' prompts and the key")
    ap.add_argument("--labels", nargs=2, default=["1", "2"], help="names for dir-1 and dir-2, kept in the key only")
    a = ap.parse_args()
    if not a.both:
        print(fill(a.project, a.dir_1, a.dir_2, a.out, a.extra))
        return
    pdir = pathlib.Path(a.both)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "prompt-AB.md").write_text(fill(a.project, a.dir_1, a.dir_2, sibling(a.out, "AB"), a.extra))
    (pdir / "prompt-BA.md").write_text(fill(a.project, a.dir_2, a.dir_1, sibling(a.out, "BA"), a.extra))
    key = {"dirs": {"1": str(pathlib.Path(a.dir_1).resolve()), "2": str(pathlib.Path(a.dir_2).resolve())},
           "labels": {"1": a.labels[0], "2": a.labels[1]}, "AB": {"A": "1", "B": "2"}, "BA": {"A": "2", "B": "1"}}
    sibling(a.out, "key").write_text(json.dumps(key, indent=1))
    print(pdir / "prompt-AB.md")
    print(pdir / "prompt-BA.md")


if __name__ == "__main__":
    main()
