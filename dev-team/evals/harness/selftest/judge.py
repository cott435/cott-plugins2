#!/usr/bin/env python3
"""Cases for the blind judge's runner, with no model calls: judge_prompt.py builds both orders' prompts from neutral
copies (rubric anchors in, placeholders filled, no mode word), `average` reproduces iteration 9's committed judge-*.json
from its saved verdicts, and `run --repeats 3` against selftest/fake_judge.py retries malformed replies, logs them,
and `average` reports the per-repeat mean, SD and min-max that the fake's scores imply (modecmp reads the result).

Usage: judge.py   prints one line per case; exit 1 if any case comes out wrong
"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile

HARNESS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS))
import judge_prompt as jp  # noqa: E402
from modecmp import judge_scores  # noqa: E402

IT9 = HARNESS.parent / "results-iteration-9"
ANCHORED = ["dependency_graph_soundness", "layout_sensibility", "organization", "ease_of_finding_next_build_step"]
FAILS = []


def case(name, ok, detail=""):
    print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f": {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def cli(*args, env=None):
    return subprocess.run([sys.executable, str(HARNESS / "judge_prompt.py"), *map(str, args)], capture_output=True,
                          text=True, env={**os.environ, **(env or {})})


def synthetic_runs(root):
    """Two packaged-outputs dirs with a process file each, under names that carry no mode."""
    dirs = []
    for name, extra in (("first", "one"), ("second", "two")):
        d = root / "runs" / name / "outputs"
        d.mkdir(parents=True)
        (d / "final__brief.md").write_text(f"# Brief {extra}\n")
        (d / "plan_snapshot.json").write_text("{}")
        (d / "transcript.md").write_text("process\n")
        dirs.append(d)
    return dirs


def check_prompts(root):
    d1, d2 = synthetic_runs(root)
    pdir, out = root / "prompts", root / "verdicts" / "judge-rl.json"
    r = cli("rl", d1, d2, out, "--both", pdir, "--labels", "incremental", "all_at_once")
    case("prompts: --both writes both orders and the key", r.returncode == 0, r.stderr[-300:])
    if r.returncode:
        return None, None
    ab, ba = (pdir / "prompt-AB.md").read_text(), (pdir / "prompt-BA.md").read_text()
    set_a = lambda t: re.search(r"^- Set A: (.*)$", t, re.M).group(1)
    case("prompts: AB has set-1 as Set A, BA has set-2", set_a(ab).endswith("set-1") and set_a(ba).endswith("set-2"))
    case("prompts: every placeholder filled", not re.search(r"\{[A-Z_]+\}", ab + ba), re.findall(r"\{[A-Z_]+\}", ab))
    case("prompts: no mode word anywhere", not jp.MODE_WORDS.search(ab + ba), jp.MODE_WORDS.findall(ab + ba))
    case("prompts: process files left out of the sets", not list(pdir.rglob("transcript.md")))
    case("prompts: the shared scale is in", "5 = you checked it and found no defect" in ab)
    for item in ANCHORED:
        line = next((ln for ln in ab.splitlines() if ln.startswith(f'- "{item}"')), "")
        case(f"prompts: {item} has anchors for 4, 3 and 2", all(f" {s}: " in line for s in (4, 3, 2)))
    words = len(ab.split())
    case("prompts: length stays reasonable (under 2000 words)", words < 2000, words)
    return pdir, out


def check_iteration_9(root):
    """average over iteration 9's saved verdicts gives its committed file, field for field."""
    for project in ("rl", "quant"):
        dst = root / "it9" / project
        dst.mkdir(parents=True)
        for tag in ("AB", "BA", "key"):
            shutil.copy(IT9 / f"judge-{project}.{tag}.json", dst)
        res = jp.average(str(dst / f"judge-{project}.json"))
        want = json.loads((IT9 / f"judge-{project}.json").read_text())
        same = {k: res[k] == want[k] for k in want}
        case(f"iteration 9 {project}: one repeat reproduces the committed judge file", all(same.values()),
             [k for k, v in same.items() if not v])
        case(f"iteration 9 {project}: no SD from one repeat",
             res["repeats"] == 1 and res["stats"]["incremental"]["overall_score"]["sd"] is None)


def check_repeats(pdir, out, root):
    state = root / "fake-state.json"
    env = {"CLAUDE_BIN": str(HARNESS / "selftest" / "fake_judge.py"), "FAKE_JUDGE_STATE": str(state)}
    stale = jp.sibling(out, "AB.4")
    stale.write_text("{}")
    r = cli("run", pdir, out, "--repeats", "3", "--workers", "1", env=env)
    case("run --repeats 3: all six verdicts saved", r.returncode == 0 and all(
        jp.sibling(out, jp.verdict_tag(o, n)).exists() for n in (1, 2, 3) for o in jp.ORDERS), r.stderr[-400:])
    case("run: a stale verdict of a higher repeat is removed", not stale.exists())
    log = out.with_suffix(".log").read_text()
    case("run: two malformed replies retried and logged, six ok",
         log.count(" malformed attempt 1") == 2 and log.count(" ok ") == 6, log)
    case("run: eight judge calls", json.loads(state.read_text())["calls"] == 8)

    res = jp.average(str(out))
    s1, s2 = res["stats"]["incremental"], res["stats"]["all_at_once"]
    # set-1 overall per repeat: (r + 1) + mean(4, 3) = 5.5, 6.5, 7.5; set-2: 3 + 3.5 = 6.5 every time
    case("average: per-repeat overall mean, SD and min-max",
         (s1["overall_score"]["mean"], s1["overall_score"]["sd"], s1["overall_score"]["min"], s1["overall_score"]["max"])
         == (6.5, 1.0, 5.5, 7.5) and s2["overall_score"]["sd"] == 0.0, (s1["overall_score"], s2["overall_score"]))
    case("average: per-item stats (content 2, 3, 4)",
         s1["content"]["dependency_graph_soundness"] == {"mean": 3, "sd": 1.0, "min": 2.0, "max": 4.0, "n": 3},
         s1["content"]["dependency_graph_soundness"])
    case("average: structure item shows the position effect only", s1["structure"]["organization"]["mean"] == 3.5
         and s1["structure"]["organization"]["sd"] == 0.0)
    case("average: margin and Set A position effect",
         (res["margin"]["mean"], res["margin"]["sd"], res["position_effect"]["mean"], res["position_effect"]["sd"])
         == (0, 1.0, 1, 0.0), (res["margin"], res["position_effect"]))
    case("average: scores keep today's shape, as means",
         res["scores"]["incremental"]["overall_score"] == 6.5
         and res["scores"]["incremental"]["content"]["dependency_graph_soundness"] == 3
         and res["repeats"] == 3 and res["orders"] == 2 and len(res["runs"]) == 3)
    case("average: winners per order, one per repeat", all(len(v) == 3 for v in res["winner_by_order"].values()))
    js = judge_scores(out)
    case("modecmp reads the averaged file", js["incremental"]["dependency_graph_soundness"] == 3
         and js["all_at_once"]["overall_score"] == 6.5, js)

    jp.sibling(out, "BA.2").unlink()
    r = cli("run", pdir, out, "--repeats", "3", "--workers", "1", "--resume", env=env)
    case("run --resume: only the missing verdict is judged", r.returncode == 0
         and json.loads(state.read_text())["calls"] == 9 and jp.sibling(out, "BA.2").exists(), r.stderr[-300:])

    bad = out.with_name("judge-bad.json")
    shutil.copy(jp.sibling(out, "key"), jp.sibling(bad, "key"))
    r = cli("run", pdir, bad, env={**env, "FAKE_JUDGE_FAIL": "1"})
    log = bad.with_suffix(".log").read_text()
    case("run: gives up after three malformed replies per order, exit 1",
         r.returncode == 1 and log.count(" malformed attempt ") == 6 and "rerun with --resume" in r.stderr, r.stderr[-300:])
    raw = bad.with_name("judge-bad.AB.malformed.txt")
    case("run: the last malformed reply is saved for reading", raw.exists() and "Set A is better" in raw.read_text())
    case("parse: the verdict object found among prose, fences and stray braces",
         jp.first_json_object('Read {both}. ```json\n{"winner": "B", "rubric": {"A": {}}}\n``` see {"x": }')
         == {"winner": "B", "rubric": {"A": {}}})
    case("parse: an object that doesn't decode is no verdict",
         jp.first_json_object('{"winner": "A", "rubric": {"A": "a "quoted" word"}}') is None)


def main():
    root = pathlib.Path(tempfile.mkdtemp(prefix="judge-selftest-"))
    try:
        pdir, out = check_prompts(root)
        check_iteration_9(root)
        if pdir:
            check_repeats(pdir, out, root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print(f"{len(FAILS)} failed" if FAILS else "all judge cases ok")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
