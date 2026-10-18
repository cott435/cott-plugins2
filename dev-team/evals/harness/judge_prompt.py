#!/usr/bin/env python3
"""Fill blind_judge_prompt.md for one pair of packaged runs, run each order as a read-only judge, and average the two
orders.

Usage:
  judge_prompt.py <project> <dir-1> <dir-2> <out-json> [--sets DIR] [--extra TEXT]
      Print one prompt with dir-1 as Set A. Shuffle the dirs yourself and keep the key.
  judge_prompt.py <project> <dir-1> <dir-2> <out-json> --both <prompt-dir> [--labels L1 L2] [--extra TEXT]
      Write <prompt-dir>/prompt-AB.md (dir-1 is A; its verdict goes to <out>.AB.json) and prompt-BA.md (dir-2 is
      A; <out>.BA.json), plus the key <out>.key.json. Labels (e.g. incremental all_at_once) go in the key only. The
      folder of <out-json> is created if it doesn't exist; it must lie outside <prompt-dir>.
  judge_prompt.py run <prompt-dir> <out-json> [--repeats N] [--workers W] [--resume]
      Judge the pair N times (default 1), each in both orders: 2N calls, W at a time (default min(2N, 6)), each its
      own `claude -p` (JUDGE_MODEL, default claude-opus-5-5) from <prompt-dir> with only Read, Glob and Grep, no
      CLAUDE.md files, no MCP servers and no host settings. Repeat 1's verdicts are <out>.AB.json and <out>.BA.json,
      repeat r's <out>.AB.r.json and <out>.BA.r.json. A reply with no valid verdict (no JSON, or not the rubric's
      shape) is retried, up to 3 attempts, each logged to <out>.log and stderr, the latest bad reply kept
      as <out>.<order>.malformed.txt. Saved verdicts are removed first;
      --resume keeps those of repeats 1..N and runs only the missing ones. A judge can't write, and a read
      outside <prompt-dir> asks for a permission that a headless run in the default permission mode denies, so the
      key stays out of reach.
  judge_prompt.py average <out-json>
      Read every repeat with both orders saved, and the key; write <out-json> with each dir's scores (keyed by label)
      averaged over all repeats and orders, plus per-repeat mean, SD and min-max per item and overall (`stats`), the
      margin of dir-1 over dir-2 and the Set A position effect with the same stats, each repeat's overall and winners
      (`runs`), the winner per order (a label; a list of labels, one per repeat, when N > 1), and the items whose two
      orders differ by more than 1.
  dir-1 / dir-2: packaged outputs dirs (bench/eval-*/<mode>/run-1/outputs from package.py).

Blinding: those paths name the mode, so the judge never sees them. Each dir is copied to a neutral folder, set-1
(dir-1) and set-2 (dir-2), in <prompt-dir> (without --both: --sets DIR, default <out-json minus .json>-sets/),
leaving out transcript.md and doc_evolution.md (older packaged runs kept them in outputs/). The prompt names only
those copies; the judge replies with its verdict. If any of those paths, or any copied file name, contains a mode
word, nothing is written.
"""
import argparse, datetime, json, os, pathlib, re, shutil, statistics, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
COMMON_CONTENT = ["stage_completeness", "internal_consistency", "right_sizing", "milestone_quality", "pipeline_clarity",
                  "interface_quality", "dependency_graph_soundness", "task_buildability"]
CONTENT = {"quant": ["quant_soundness", "null_hypothesis_handoff", "reference_use"] + COMMON_CONTENT,
           "rl": ["rl_soundness"] + COMMON_CONTENT}
STRUCTURE = ["organization", "readability_for_solo_learner", "ease_of_finding_next_build_step", "layout_sensibility"]
PROCESS_FILES = ("transcript.md", "doc_evolution.md")  # they name the mode and the process: never in a judge's set
MODE_WORDS = re.compile(r"incremental|all[ _-]?at[ _-]?once|(?<![a-z])(inc|aao)(?![a-z])", re.I)
ORDERS = ("AB", "BA")
SCORES = ("content_score", "structure_score", "overall_score")
ATTEMPTS = 3  # about 1 reply in 4 comes back malformed (iteration 9)


def fill(project, dir_a, dir_b, out, extra):
    facts = json.loads((HERE / "scenarios.json").read_text())["projects"][project]
    values = {"FACTS": "\n".join(f"- {f}" for f in facts["facts"]) + "\n\nStages, in order:\n" +
                       "\n".join(f"- {s['reveal']}" for s in facts["stages"]),
              "DIR_A": str(pathlib.Path(dir_a).resolve()), "DIR_B": str(pathlib.Path(dir_b).resolve()),
              "CONTENT_KEYS": ", ".join(CONTENT[project]), "STRUCTURE_KEYS": ", ".join(STRUCTURE),
              "EXTRA": extra}
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


def verdict_tag(order, rep):
    return order if rep == 1 else f"{order}.{rep}"


def verdicts(out):
    """{repeat: {order: path}} for the verdicts saved beside <out-json>."""
    out = pathlib.Path(out)
    pat = re.compile(rf"^{re.escape(out.stem)}\.(AB|BA)(?:\.(\d+))?\.json$")
    reps = {}
    for f in out.parent.iterdir():
        m = pat.match(f.name)
        if m:
            reps.setdefault(int(m.group(2) or 1), {})[m.group(1)] = f
    return dict(sorted(reps.items()))


def stat(xs):
    """Mean, sample SD (None for one value) and min-max of per-repeat values."""
    return {"mean": round(statistics.mean(xs), 3), "sd": round(statistics.stdev(xs), 3) if len(xs) > 1 else None,
            "min": min(xs), "max": max(xs), "n": len(xs)}


def pair_scores(runs, key):
    """One repeat: each dir's scores averaged over its two orders, the order disagreements and the winners."""
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
        for s in SCORES:
            sc[s] = round(sum(b.get(s, 0) for b in blocks) / len(blocks), 2)
        scores[label] = sc
    winners = {o: key["labels"][key[o][d.get("winner", "")]] if d.get("winner") in key[o] else None for o, d in runs.items()}
    # dir-1's margin over dir-2 in each order; half their difference is what being Set A is worth
    m = {o: d["rubric"][a1]["overall_score"] - d["rubric"][a2]["overall_score"] for o, d in runs.items()
         for a1, a2 in [sorted(key[o], key=lambda letter: key[o][letter])]}
    return scores, split, winners, round((m["AB"] - m["BA"]) / 2, 3)


def average(out):
    key = json.loads(sibling(out, "key").read_text())
    reps = {r: {o: json.loads(f.read_text()) for o, f in fs.items()} for r, fs in verdicts(out).items() if len(fs) == 2}
    if not reps:
        sys.exit(f"judge_prompt: no repeat of {out} has both orders saved")
    labels = [key["labels"]["1"], key["labels"]["2"]]
    pairs = {r: pair_scores({o: runs[o] for o in ORDERS}, key) for r, runs in reps.items()}
    scores, stats = {}, {}
    for label in labels:
        per = [p[0][label] for p in pairs.values()]
        sc, st = {}, {}
        for part in ("content", "structure"):
            items = sorted({k for s in per for k in s[part]})
            vals = {k: [s[part].get(k, 0) for s in per] for k in items}
            sc[part] = {k: round(statistics.mean(v), 2) for k, v in vals.items()}
            st[part] = {k: stat(v) for k, v in vals.items()}
        for s in SCORES:
            sc[s] = round(statistics.mean(p[s] for p in per), 2)
            st[s] = stat([p[s] for p in per])
        scores[label], stats[label] = sc, st
    n = len(pairs)
    tag = (lambda r: f"r{r} ") if n > 1 else (lambda r: "")
    winners = {o: [p[2][o] for p in pairs.values()] for o in ORDERS}
    res = {"labels": key["labels"], "dirs": {key["labels"][k]: key["dirs"][k] for k in ("1", "2")}, "orders": 2,
           "repeats": n, "scores": scores,
           "winner_by_order": {o: w[0] for o, w in winners.items()} if n == 1 else winners,
           "order_disagreements": [tag(r) + d for r, p in pairs.items() for d in p[1]],
           "stats": stats,
           "margin": stat([p[0][labels[0]]["overall_score"] - p[0][labels[1]]["overall_score"] for p in pairs.values()]),
           "position_effect": stat([p[3] for p in pairs.values()]),
           "runs": [{"repeat": r, "overall": {lb: p[0][lb]["overall_score"] for lb in labels},
                     "winner_by_order": p[2]} for r, p in pairs.items()]}
    pathlib.Path(out).write_text(json.dumps(res, indent=1))
    return res


def verdict_problem(v):
    """Why a parsed reply isn't a verdict in the rubric's shape, or None."""
    if not isinstance(v, dict) or v.get("winner") not in ("A", "B"):
        return "winner is not A or B"
    for letter in "AB":
        r = (v.get("rubric") or {}).get(letter)
        if not isinstance(r, dict):
            return f"no rubric for {letter}"
        for part in ("content", "structure"):
            items = r.get(part)
            if not isinstance(items, dict) or not items:
                return f"rubric {letter} has no {part} scores"
            bad = [k for k, x in items.items() if not isinstance(x, (int, float)) or not 1 <= x <= 5]
            if bad:
                return f"rubric {letter} {part} scores outside 1-5: {bad}"
        if not all(isinstance(r.get(s), (int, float)) for s in SCORES):
            return f"rubric {letter} lacks a numeric {'/'.join(SCORES)}"
    return None


def judge(prompt_dir, order, out, rep=1):
    """One order's verdict: the prompt run as a read-only `claude -p` from the prompt folder, its JSON saved."""
    sys.path.insert(0, str(HERE))
    import driver  # the isolated environment the eval's own sessions get
    text = (pathlib.Path(prompt_dir) / f"prompt-{order}.md").read_text()
    cmd = [driver.CLAUDE_BIN, "-p", text, "--model", os.environ.get("JUDGE_MODEL", "claude-opus-5-5"),
           "--tools", "Read,Glob,Grep", "--allowedTools", "Read,Glob,Grep", "--strict-mcp-config",
           "--output-format", "json", "--no-session-persistence", *driver.ISOLATE]
    r = subprocess.run(cmd, cwd=prompt_dir, env=driver.ENV, capture_output=True, text=True, timeout=7200)
    tag = verdict_tag(order, rep)
    try:
        reply = json.loads(r.stdout)["result"]
    except (ValueError, KeyError, TypeError):
        reply = None
    verdict = first_json_object(reply) if isinstance(reply, str) else None
    problem = "no JSON object in the reply" if verdict is None else verdict_problem(verdict)
    if problem:
        raw = pathlib.Path(out).with_name(f"{pathlib.Path(out).stem}.{tag}.malformed.txt")
        raw.write_text(reply if isinstance(reply, str) else (r.stdout or r.stderr))
        raise SystemExit(f"judge_prompt: the {order} judge gave no valid verdict (rc {r.returncode}): {problem}; "
                         f"reply saved to {raw.name}")
    sibling(out, tag).write_text(json.dumps(verdict, indent=1))
    return order, verdict.get("winner")


def first_json_object(text):
    """The first JSON object in a reply that decodes whole, wherever it starts; prose or fences around it are fine."""
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj = dec.raw_decode(text, m.start())[0]
        except ValueError:
            continue
        if isinstance(obj, dict) and "rubric" in obj:
            return obj
    return None


def log_line(out, *parts):
    line = " ".join([datetime.datetime.now().isoformat(timespec="seconds"), *map(str, parts)])
    print(line, file=sys.stderr, flush=True)
    with pathlib.Path(out).with_suffix(".log").open("a") as f:
        f.write(line + "\n")


def judge_retrying(prompt_dir, order, out, rep):
    """One order of one repeat, retried on a reply with no valid verdict; the winner, or None after ATTEMPTS."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            winner = judge(prompt_dir, order, out, rep)[1]
            log_line(out, f"r{rep}", order, "ok", f"attempt {attempt}")
            return winner
        except (SystemExit, subprocess.TimeoutExpired) as e:
            log_line(out, f"r{rep}", order, "malformed" if isinstance(e, SystemExit) else "timeout",
                     f"attempt {attempt}", str(e).replace("\n", " ")[:300])
    return None


def run(prompt_dir, out, repeats=1, workers=None, resume=False):
    """2 x repeats judge calls; returns {"r<rep> <order>": winner or None}. First removes the saved verdicts this run
    replaces (with `resume`, only those above `repeats`), so a failed call never leaves an older verdict standing."""
    for r, fs in verdicts(out).items():
        if r > repeats or not resume:
            for f in fs.values():
                f.unlink()
    jobs = [(o, r) for r in range(1, repeats + 1) for o in ORDERS
            if not (resume and sibling(out, verdict_tag(o, r)).exists())]
    log_line(out, f"run: {len(jobs)} judge calls ({repeats} repeat(s) x 2 orders"
                  + (", saved ones kept)" if resume else ")"))
    if not jobs:
        return {}
    with ThreadPoolExecutor(max_workers=workers or min(len(jobs), 6)) as pool:
        got = pool.map(lambda j: (f"r{j[1]} {j[0]}", judge_retrying(prompt_dir, j[0], out, j[1])), jobs)
        return dict(got)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        ap = argparse.ArgumentParser(prog="judge_prompt.py run")
        ap.add_argument("prompt_dir")
        ap.add_argument("out")
        ap.add_argument("--repeats", type=int, default=1, help="judge the pair this many times, each in both orders")
        ap.add_argument("--workers", type=int, help="judge calls at a time (default min(2 x repeats, 6))")
        ap.add_argument("--resume", action="store_true", help="keep verdicts already saved; run only the missing")
        a = ap.parse_args(sys.argv[2:])
        pdir, out = pathlib.Path(a.prompt_dir).resolve(), pathlib.Path(a.out).resolve()
        if pdir in sibling(out, "key").parents:
            sys.exit(f"judge_prompt: the key {sibling(out, 'key')} is inside {pdir}, where the judge reads")
        if a.repeats < 1:
            sys.exit("judge_prompt: --repeats must be at least 1")
        res = run(pdir, out, a.repeats, a.workers, a.resume)
        print(res)
        failed = [k for k, w in res.items() if w is None]
        if failed:
            sys.exit(f"judge_prompt: no valid verdict after {ATTEMPTS} attempts: {failed}; rerun with --resume")
        return
    if len(sys.argv) > 1 and sys.argv[1] == "average":
        if len(sys.argv) != 3:
            sys.exit("usage: judge_prompt.py average <out-json>")
        res = average(sys.argv[2])
        for label, st in res["stats"].items():
            o = st["overall_score"]
            sd = f" ± {o['sd']:.2f}" if o["sd"] is not None else ""
            print(f"{label}: {o['mean']:.2f}{sd} ({o['min']}–{o['max']}, {o['n']} repeat(s))")
        m, p = res["margin"], res["position_effect"]
        fmt = lambda s: f"{s['mean']:+.2f}" + (f" ± {s['sd']:.2f}" if s["sd"] is not None else "")
        print(f"margin {res['labels']['1']} − {res['labels']['2']}: {fmt(m)}; Set A position effect: {fmt(p)}; "
              f"winners {res['winner_by_order']}")
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
    if pdir in sibling(out, "key").parents:
        sys.exit(f"judge_prompt: put <out-json> outside {pdir}: the key must stay out of the judge's folder")
    s1, s2 = neutral_sets([a.dir_1, a.dir_2], pdir, [])
    out.parent.mkdir(parents=True, exist_ok=True)
    (pdir / "prompt-AB.md").write_text(fill(a.project, s1, s2, sibling(out, "AB"), a.extra))
    (pdir / "prompt-BA.md").write_text(fill(a.project, s2, s1, sibling(out, "BA"), a.extra))
    key = {"dirs": {"1": str(pathlib.Path(a.dir_1).resolve()), "2": str(pathlib.Path(a.dir_2).resolve())},
           "sets": {"1": str(s1), "2": str(s2)},
           "labels": {"1": a.labels[0], "2": a.labels[1]}, "AB": {"A": "1", "B": "2"}, "BA": {"A": "2", "B": "1"}}
    sibling(out, "key").write_text(json.dumps(key, indent=1))
    print(pdir / "prompt-AB.md")
    print(pdir / "prompt-BA.md")


if __name__ == "__main__":
    main()
