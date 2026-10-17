#!/usr/bin/env python3
"""Fill blind_judge_prompt.md for one pair of packaged runs (hand each prompt to a fresh agent session), and average
the two orders.

Usage:
  judge_prompt.py <project> <dir-1> <dir-2> <out-json> [--sets DIR] [--extra TEXT]
      Print one prompt with dir-1 as Set A. Shuffle the dirs yourself and keep the key.
  judge_prompt.py <project> <dir-1> <dir-2> <out-json> --both <prompt-dir> [--labels L1 L2] [--extra TEXT]
      Write <prompt-dir>/prompt-AB.md (dir-1 is A; the judge writes <out>.AB.json) and prompt-BA.md (dir-2 is A;
      <out>.BA.json), plus the key <out>.key.json. Labels (e.g. incremental all_at_once) go in the key only.
      The folder of <out-json> is created if it doesn't exist.
  judge_prompt.py average <out-json>
      Read <out>.AB.json, <out>.BA.json and the key; write <out-json> with each dir's scores averaged over the
      two orders (keyed by label), the winner per order, and the items whose two scores differ by more than 1.
  dir-1 / dir-2: packaged outputs dirs (bench/eval-*/<mode>/run-1/outputs from package.py).

Blinding: those paths name the mode, so the judge never sees them. Each dir is copied to a neutral folder, set-1
(dir-1) and set-2 (dir-2), in <prompt-dir> (without --both: --sets DIR, default <out-json minus .json>-sets/),
leaving out transcript.md and doc_evolution.md (older packaged runs kept them in outputs/). The prompt names only
those copies and <out-json>. If any of those paths, or any copied file name, contains a mode word, nothing is
written.
"""
import argparse, json, pathlib, re, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
COMMON_CONTENT = ["stage_completeness", "internal_consistency", "right_sizing", "milestone_quality", "pipeline_clarity",
                  "interface_quality", "dependency_graph_soundness", "task_buildability"]
CONTENT = {"quant": ["quant_soundness", "null_hypothesis_handoff", "reference_use"] + COMMON_CONTENT,
           "rl": ["rl_soundness"] + COMMON_CONTENT}
STRUCTURE = ["organization", "readability_for_solo_learner", "ease_of_finding_next_build_step", "layout_sensibility"]
PROCESS_FILES = ("transcript.md", "doc_evolution.md")  # they name the mode and the process: never in a judge's set
MODE_WORDS = re.compile(r"incremental|all[ _-]?at[ _-]?once|(?<![a-z])(inc|aao)(?![a-z])", re.I)


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


def mode_leaks(paths=(), sets=()):
    """Every given path, or file name inside a copied set, that contains a mode word."""
    bad = [str(p) for p in paths if MODE_WORDS.search(str(p))]
    bad += [str(f.relative_to(s.parent)) for s in sets for f in s.rglob("*") if MODE_WORDS.search(f.name)]
    return bad


def neutral_sets(dirs, root, prompt_paths):
    """Copy each packaged outputs dir to <root>/set-<n> without the process files; returns the copies. Exits,
    writing nothing more, when a path the prompt will name or a copied file name contains a mode word."""
    root = pathlib.Path(root).resolve()
    leaks = mode_leaks([root, *prompt_paths])
    if leaks:
        sys.exit(f"judge_prompt: a path the judge would see names the mode: {leaks}")
    sets = []
    for n, d in enumerate(dirs, 1):
        dst = root / f"set-{n}"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(pathlib.Path(d).resolve(), dst, ignore=shutil.ignore_patterns(*PROCESS_FILES))
        sets.append(dst)
    leaks = mode_leaks(sets=sets)
    if leaks:
        for s in sets:
            shutil.rmtree(s, ignore_errors=True)
        sys.exit(f"judge_prompt: copied file names name the mode: {leaks[:10]}")
    return sets


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
    ap.add_argument("--sets", metavar="DIR", help="without --both: where the neutral copies go (default <out>-sets/)")
    a = ap.parse_args()
    out = pathlib.Path(a.out).resolve()
    if not a.both:
        root = pathlib.Path(a.sets) if a.sets else out.with_name(f"{out.stem}-sets")
        s1, s2 = neutral_sets([a.dir_1, a.dir_2], root, [out])
        out.parent.mkdir(parents=True, exist_ok=True)
        print(fill(a.project, s1, s2, out, a.extra))
        return
    pdir = pathlib.Path(a.both).resolve()
    ab, ba = sibling(out, "AB"), sibling(out, "BA")
    s1, s2 = neutral_sets([a.dir_1, a.dir_2], pdir, [ab, ba])
    out.parent.mkdir(parents=True, exist_ok=True)
    (pdir / "prompt-AB.md").write_text(fill(a.project, s1, s2, ab, a.extra))
    (pdir / "prompt-BA.md").write_text(fill(a.project, s2, s1, ba, a.extra))
    key = {"dirs": {"1": str(pathlib.Path(a.dir_1).resolve()), "2": str(pathlib.Path(a.dir_2).resolve())},
           "sets": {"1": str(s1), "2": str(s2)},
           "labels": {"1": a.labels[0], "2": a.labels[1]}, "AB": {"A": "1", "B": "2"}, "BA": {"A": "2", "B": "1"}}
    sibling(out, "key").write_text(json.dumps(key, indent=1))
    print(pdir / "prompt-AB.md")
    print(pdir / "prompt-BA.md")


if __name__ == "__main__":
    main()
