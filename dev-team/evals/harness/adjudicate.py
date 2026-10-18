#!/usr/bin/env python3
"""The grader against its adjudicated corpus: regrade the archived runs of past iterations and compare each check
an analyst ruled on with the ruling. No model calls.

selftest/adjudicated/iteration-<N>.json holds one record per (trajectory, check) that a findings analysis ruled on
(results-iteration-<N>/findings-interface.md and findings-flow.md):
- `expect`: "pass" or "fail", what a correct grader gives this run;
- `verdict`: "grader" (a false fail), "false-pass" (a defect the check let through), "real" (a correct fail) or
  "mixed" (a correct fail whose evidence also lists items the analyst ruled false);
- `must_match` / `must_not_match`: regexes the check's evidence or `metrics` must (not) contain: the real items a
  mixed fail must keep and the false items it must drop. Evidence is cut to 600 characters; `metrics.items` holds
  the full lists;
- `finding`, `reason`; `basis` is "analyst" when the findings name this run and check, "derived" when they name
  the defect and the record applies it to a check the analyst filed under another finding.

Each run is copied from the workspace (iteration-<N>/<trajectory>/with_skill) into a scratch dir without its
virtualenv, node_modules, caches, flow/ and grading.json, and graded there; the workspace is only read.

Usage: adjudicate.py [--workspace DIR] [--out DIR] [--iteration N ...] [--trajectory T ...] [--reuse] [--json FILE]
  --reuse grades only the copies that have no grading.json yet. Exit 1 if any record disagrees with the grader.
"""
import argparse, json, pathlib, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
CORPUS = HERE / "selftest" / "adjudicated"
WORKSPACE = pathlib.Path("/Users/connorott/plugins/dev-team-workspace")
SKIP = shutil.ignore_patterns(".venv", "node_modules", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
                              "flow", "grading.json")


def load(iterations=None):
    recs = []
    for p in sorted(CORPUS.glob("iteration-*.json")):
        it = int(p.stem.split("-")[1])
        if iterations and it not in iterations:
            continue
        recs += [{"iteration": it, **r} for r in json.loads(p.read_text())]
    return recs


def regrade(src, dst, reuse=False):
    """Copy one archived run and grade the copy; return its checks by id."""
    if not (reuse and (dst / "grading.json").exists()):
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=SKIP, symlinks=True)
        r = subprocess.run([sys.executable, str(HERE / "grade.py"), str(dst)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"adjudicate: grade.py failed on {dst}:\n{r.stderr[-2000:]}")
    return {c["id"]: c for c in json.loads((dst / "grading.json").read_text())["expectations"]}


def compare(rec, c):
    """The ways the grader's check disagrees with the record (empty when it agrees)."""
    if c is None:
        return ["check missing from grading.json"]
    if c.get("na"):
        return [f"n/a: {c['evidence'][:160]}"]
    got = "pass" if c["passed"] else "fail"
    if got != rec["expect"]:
        return [f"{'passes' if c['passed'] else 'fails'}, ruled {rec['expect']}"]
    ev = c["evidence"] + " " + json.dumps(c.get("metrics", {}))
    out = [f"evidence lacks /{p}/ (a real item)" for p in rec.get("must_match", []) if not re.search(p, ev, re.M)]
    out += [f"evidence still lists /{p}/ (ruled false)" for p in rec.get("must_not_match", []) if re.search(p, ev, re.M)]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workspace", type=pathlib.Path, default=WORKSPACE)
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--iteration", type=int, action="append")
    ap.add_argument("--trajectory", action="append")
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--json", type=pathlib.Path)
    a = ap.parse_args()
    ws = a.workspace.resolve()
    out = (a.out or pathlib.Path(tempfile.mkdtemp(prefix="dt-adjudicate-"))).resolve()
    if out == ws or ws in out.parents:
        raise SystemExit(f"adjudicate: --out {out} is inside the workspace; grading writes there")
    recs = [r for r in load(a.iteration) if not a.trajectory or r["trajectory"] in a.trajectory]
    runs = sorted({(r["iteration"], r["trajectory"]) for r in recs})
    for it, t in runs:
        if not (ws / f"iteration-{it}" / t / "with_skill").is_dir():
            raise SystemExit(f"adjudicate: no run at {ws / f'iteration-{it}' / t / 'with_skill'}")

    def job(key):
        it, t = key
        return key, regrade(ws / f"iteration-{it}" / t / "with_skill", out / f"iteration-{it}" / t / "with_skill", a.reuse)
    with ThreadPoolExecutor(max_workers=4) as pool:
        graded = dict(pool.map(job, runs))

    rows, ruled = [], set()
    for r in recs:
        ruled.add((r["iteration"], r["trajectory"], r["check"]))
        problems = compare(r, graded[(r["iteration"], r["trajectory"])].get(r["check"]))
        rows.append({**r, "ok": not problems, "problems": problems})
    bad = [x for x in rows if not x["ok"]]
    unruled = [(it, t, cid, c["evidence"][:140]) for (it, t), res in graded.items() for cid, c in res.items()
               if c.get("passed") is False and (it, t, cid) not in ruled]

    print(f"{len(rows)} adjudicated records over {len(runs)} runs; the grader agrees with {len(rows) - len(bad)}, "
          f"disagrees with {len(bad)}")
    for kind, title in (("grader", "still a false fail"), ("false-pass", "still a false pass"),
                        ("mixed", "mixed: wrong outcome or wrong items"), ("real", "a real failure the grader no longer sees")):
        group = [x for x in bad if x["verdict"] == kind]
        if group:
            print(f"\n{title} ({len(group)}):")
        for x in group:
            print(f"  it{x['iteration']} {x['trajectory']:<18} {x['check']:<32} {'; '.join(x['problems'])}  "
                  f"[{x['finding']}{', derived' if x['basis'] == 'derived' else ''}]")
    if unruled:
        print(f"\nfailing checks no record rules on ({len(unruled)}, not counted):")
        for it, t, cid, ev in unruled:
            print(f"  it{it} {t:<18} {cid:<32} {ev}")
    print(f"\nregraded copies: {out}")
    if a.json:
        a.json.write_text(json.dumps({"records": rows, "unruled": unruled}, indent=1))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
