#!/usr/bin/env python3
"""A final plan-review pass on a copy of a finished run: a read-only reviewer lists defects against the user's own
messages (plan_review_prompt.md), then a fixer applies them to the copy's docs and plan (plan_fix_prompt.md).

Usage: plan_review.py <run-copy> [prepare|review|fix|all]   (default all)
  <run-copy> is a with_skill folder laid out like a driver run (project/, plugin/, turns.json), never the original.
  prepare (part of review) writes project/.review/: user_messages.md (each turn's user message from turns.json),
  packets/context__<task>.md (`dt context` for every task) and lint.txt (`dt lint`).
  review runs the reviewer (`claude -p`, REVIEW_MODEL, default claude-opus-5-5, Read/Glob/Grep only) from project/
  and saves its JSON to <run-copy>/review/review.json and project/.review/review.json.
  prepare alone writes project/.review/ without running the reviewer, so fix can run on a review.json put there
  by hand (an earlier run's list, to test the fixer alone).
  fix runs the fixer (Read/Edit/Glob/Grep, Bash only for the run's dt) from project/, saves its reply to
  <run-copy>/review/fix.json, removes project/.review/ and commits the edits to docs/, tasks/ and
  tests/fixtures/ (the expected.json values the fixer may change) in the copy as "plan review fixes".
  The fixer runs without the plugin, so dt guard's prompt on expected.json writes never fires. Instead, before
  the commit, oracle_check diffs every changed expected.json against its committed version and checks each new
  or changed value against the developer's turn that fix.json's oracle_edits cites for that file (see
  value_in_turn for the notations it accepts). A value that fails is reverted and then deleted. Its case is
  routed to test-planning the way the fixer routes a computed value: `dt route`, tests.md Status Draft, an
  Open questions bullet, and a short model pass that takes the value out of the case's wording. Results go to
  fix.json's oracle_check and cost.json's oracle_revert.
  Each step's cost, turns and seconds go to <run-copy>/review/cost.json.
"""
import json, os, pathlib, re, shutil, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver, dtrun  # noqa: E402  (driver: the isolated environment the eval's own sessions get)

MODEL = os.environ.get("REVIEW_MODEL", "claude-opus-5-5")


def prepare(run):
    proj, dt = run / "project", dtrun.dt_path(run)
    rv = proj / ".review"
    if rv.exists():
        shutil.rmtree(rv)
    (rv / "packets").mkdir(parents=True)
    turns = json.loads((run / "turns.json").read_text())
    (rv / "user_messages.md").write_text("# The developer's messages, in order\n\n" + "\n".join(
        f"## Turn {t['turn']}\n\n{t['user'].strip()}\n" for t in turns))
    n = 0
    for plan in dtrun.probe(proj, dt)["plans"]:
        for t in plan["tasks"]:
            rc, packet, err = dtrun.run(proj, "context", t["id"], dt=dt)
            (rv / "packets" / f"context__{t['id']}.md").write_text(packet if rc == 0 else f"(dt context failed: {err.strip()})\n")
            n += 1
    rc, out, err = dtrun.run(proj, "lint", dt=dt)
    (rv / "lint.txt").write_text(out + err)
    return n


def claude(prompt, cwd, tools, allowed):
    cmd = [driver.CLAUDE_BIN, "-p", prompt, "--model", MODEL, "--tools", tools, "--allowedTools", *allowed,
           "--strict-mcp-config", "--output-format", "json", "--no-session-persistence", *driver.ISOLATE]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd, env=driver.ENV, capture_output=True, text=True, timeout=7200)
    try:
        res = json.loads(r.stdout)
        reply = json.loads(re.search(r"\{.*\}", res["result"], re.S).group(0))
    except (ValueError, KeyError, TypeError, AttributeError):
        raise SystemExit(f"plan_review: no JSON reply (rc {r.returncode}): {(r.stdout or r.stderr)[-800:]}")
    cost = {"cost_usd": res.get("total_cost_usd"), "turns": res.get("num_turns"), "seconds": round(time.time() - t0),
            "usage": res.get("usage")}
    return reply, cost


def record(run, step, cost):
    f = run / "review" / "cost.json"
    data = json.loads(f.read_text()) if f.exists() else {}
    data[step] = cost
    f.write_text(json.dumps(data, indent=1))


def review(run):
    n = prepare(run)
    proj = run / "project"
    reply, cost = claude((HERE / "plan_review_prompt.md").read_text(), proj, "Read,Glob,Grep", ["Read", "Glob", "Grep"])
    (run / "review").mkdir(exist_ok=True)
    for f in (run / "review" / "review.json", proj / ".review" / "review.json"):
        f.write_text(json.dumps(reply, indent=1))
    record(run, "review", {**cost, "packets": n})
    print(run.parent.name, "review:", len(reply.get("defects", [])), "defects", f"${cost['cost_usd']:.2f}")


NUMBER_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty".split())} | {"thirty": 30, "forty": 40, "fifty": 50, "hundred": 100,
                                                      "dozen": 12, "half": 0.5, "single": 1, "once": 1, "twice": 2}
STOP = set("this that with from have will each when then than them they into only also what which their there "
           "about after before every other some more most less such where while true false none null".split())


def leaves(obj, path=()):
    """Every leaf of a JSON value as {path: value}. A list counts as one leaf."""
    if isinstance(obj, dict):
        return {k: v for key, val in obj.items() for k, v in leaves(val, path + (key,)).items()}
    return {path: obj}


def tokens(path, value):
    """The numbers and content words a leaf carries, its key included."""
    text = " ".join(map(str, path)) + " " + json.dumps(value)
    nums = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]
    words = [w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP]
    return nums, words


def strip_markers(text):
    """The message without numbered-list markers: a 1–2 digit number with "." or ")" before a capital letter."""
    return re.sub(r"(?:^|(?<=[\s(]))\d{1,2}[.)]\s+(?=[A-Z])", " ", text, flags=re.M)


def turn_numbers(text):
    """Numbers a developer's message states, in every notation the check accepts: digits (1,000 and 1000),
    number words (one … twenty, thirty, forty, fifty, hundred, dozen, half, single, once, twice), a percent as
    both 5 and 0.05, 'N k' as N·1000, and hours as minutes (N hour → N·60) and back. List markers ("3. Use",
    "3) Use") are not numbers the developer stated."""
    low = strip_markers(text).lower()
    out = set()
    for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*(%|k\b|hours?|hrs?|h\b|minutes?|mins?)?", low):
        n, unit = float(m.group(1).replace(",", "")), (m.group(2) or "")
        out.add(n)
        if unit == "%":
            out.add(n / 100)
        elif unit == "k":
            out.add(n * 1000)
        elif unit.startswith("h"):
            out.add(n * 60)
        elif unit.startswith("m"):
            out.add(n / 60)
    for w, n in NUMBER_WORDS.items():
        if re.search(rf"\b{w}\b", low):
            out.add(float(n))
            if re.search(rf"\b{w}\s+hours?\b", low):
                out.add(float(n) * 60)
    if re.search(r"\b(an?)\s+hour\b", low):
        out.add(60.0)
    return out


def value_in_turn(old, new, path, text):
    """Does the developer's message contain this new value? Only what the edit added is checked:
    - every number in the new value and not in the old one must be in the message, in any notation turn_numbers
      accepts; 1 also passes when the message says "a" or "an" within two words before a word sharing the first
      four letters of a word in the leaf ("a learning predator" for "predators": 1);
    - a value with no new number passes when a content word it added shares its first four letters with a word
      in the message (circle / circular);
    - a value that only lost items (a shorter list or string, nothing added) is a deletion, the route the fixer
      takes for a computed value, and isn't checked.
    Returns (ok, why)."""
    low = strip_markers(text).lower()
    msg_words = {w[:4] for w in re.findall(r"[a-z]{4,}", low)}
    on, ow = tokens(path, old) if old is not None else ([], [])
    nn, nw = tokens(path, new)
    added_nums = list(nn)
    for n in on:
        if n in added_nums:
            added_nums.remove(n)
    stated = turn_numbers(text)
    for n in added_nums:
        if any(abs(n - s) < 1e-9 for s in stated):
            continue
        if n == 1 and any(re.search(rf"\b(an?)\s+(?:\w+\s+){{0,2}}{w[:4]}", low) for w in nw):
            continue
        return False, f"{n:g} is not in the turn"
    if added_nums:
        return True, "numbers " + ", ".join(f"{n:g}" for n in added_nums)
    added_words = [w for w in nw if w not in ow]
    if added_words:
        hit = [w for w in added_words if w[:4] in msg_words]
        return (True, "word " + hit[0]) if hit else (False, "no added word is in the turn: " + ", ".join(added_words[:6]))
    return True, "deletion: nothing added"


def git_json(proj, rev, rel):
    r = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=proj, capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def oracle_check(run, reply, base="HEAD", write=True):
    """Check every expected.json the fixer changed against the turn it cites (value_in_turn). With write, a failing
    value is reverted and deleted and its case routed to test-planning. Returns the per-file results."""
    proj = run / "project"
    turns = {t["turn"]: t["user"] for t in json.loads((run / "turns.json").read_text())}
    cited = {}
    for e in reply.get("oracle_edits", []):
        if e.get("turn") in turns:
            cited.setdefault(e.get("file", ""), set()).add(e["turn"])
    changed = subprocess.run(["git", "diff", "--name-only", base, "--", "tests/fixtures"], cwd=proj,
                             capture_output=True, text=True).stdout.split()
    if write:
        changed += subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "tests/fixtures"], cwd=proj,
                                  capture_output=True, text=True).stdout.split()
    results = []
    for rel in sorted(set(f for f in changed if f.endswith("expected.json"))):
        f = proj / rel
        if not f.exists():
            results.append({"file": rel, "status": "deleted file"})
            continue
        before = leaves(git_json(proj, base, rel) or {})
        cur_obj = json.loads(f.read_text()) if write else git_json(proj, "HEAD", rel)
        after = leaves(cur_obj)
        checks, failed = [], []
        for path, val in after.items():
            if path in before and before[path] == val:
                continue
            old = before.get(path)
            if old is not None and value_in_turn(old, val, path, "")[1].startswith("deletion"):
                checks.append({"key": ".".join(map(str, path)), "old": old, "new": val, "ok": True,
                               "why": "deletion: nothing added"})
                continue
            ok, why = False, "no turn cited for this file"
            for n in sorted(cited.get(rel, ())):
                ok, why = value_in_turn(old, val, path, turns[n])
                if ok:
                    why = f"turn {n}: {why}"
                    break
            checks.append({"key": ".".join(map(str, path)), "old": old, "new": val, "ok": ok, "why": why})
            if not ok:
                failed.append(path)
        if not checks:
            continue
        res = {"file": rel, "turns": sorted(cited.get(rel, ())), "checks": checks,
               "status": "reverted" if failed else "passed"}
        results.append(res)
        if failed and write:
            for path in failed:  # revert to the committed value, then delete it: the case is re-derived
                node = cur_obj
                for k in path[:-1]:
                    node = node[k]
                node.pop(path[-1], None)
            orig = (subprocess.run(["git", "show", f"{base}:{rel}"], cwd=proj, capture_output=True, text=True).stdout
                    or f.read_text())
            f.write_text((json.dumps(cur_obj, indent=2) if "\n" in orig.strip() else json.dumps(cur_obj)) + "\n")
    return results


def route_reverted(run, results, dt):
    """Route each reverted case the way the fixer routes a computed value, then have a short model pass take the
    deleted values out of the case's wording in tests.md."""
    proj = run / "project"
    cases = []
    for r in results:
        if r["status"] != "reverted":
            continue
        m = re.match(r"tests/fixtures/([^/]+)/(TC-\d+)/expected\.json", r["file"])
        if not m:
            continue
        pkg, tc = m.groups()
        keys = [c["key"] for c in r["checks"] if not c["ok"]]
        why = "; ".join(f"{c['key']}: {c['why']}" for c in r["checks"] if not c["ok"])
        dtrun.run(proj, "route", "test-planning", f"{tc}: re-derive {', '.join(keys)} in expected.json "
                  f"(the value the review wrote is not in the developer's words)", "--from", "plan-review", dt=dt)
        tests = proj / "docs" / "packages" / pkg / "tests.md"
        if tests.exists():
            text = re.sub(r"(\*\*Status:\*\*\s*)\w+", r"\1Draft", tests.read_text(), count=1)
            bullet = (f"- {tc}: re-derive {', '.join(keys)} in `expected.json` with test-planning; the value a review "
                      f"wrote was not in the developer's words.\n")
            if "## Open questions" in text:
                text = re.sub(r"(## Open questions\n(?:\n)?)", lambda mm: mm.group(1) + bullet, text, count=1)
            else:
                text = text.rstrip("\n") + "\n\n## Open questions\n" + bullet
            tests.write_text(text)
        cases.append({"case": tc, "tests": str(tests.relative_to(proj)), "keys": keys, "why": why,
                      "values": [c["new"] for c in r["checks"] if not c["ok"]]})
    if not cases:
        return None
    prompt = ("You are cleaning up after a plan review. Each case below had expected values written that the "
              "developer never stated, so they were deleted from the case's expected.json and the case was routed "
              "to test-planning (an Open questions bullet now says so). In each case's section of its tests.md, "
              "remove those values from the **Expected:** and **Tolerance:** wording (and the title, if it states "
              "them), leaving the rest of the sentence readable, and say the value is to be re-derived. Change "
              "nothing else: no other case, no IDs, no other file. Cases:\n" + json.dumps(cases, indent=1) +
              '\nReply with ONLY a JSON object: {"edited": ["TC-NN", ...]}')
    reply, cost = claude(prompt, proj, "Read,Edit,Grep", ["Read", "Edit", "Grep"])
    return {"cases": cases, "edited": reply.get("edited", []), **cost}


def fix(run):
    proj, dt = run / "project", dtrun.dt_path(run).resolve()
    dtcmd = f"python3 {dt} --root {proj.resolve()}"
    prompt = (HERE / "plan_fix_prompt.md").read_text().replace("{DT}", dtcmd)
    reply, cost = claude(prompt, proj, "Read,Edit,Glob,Grep,Bash",
                         ["Read", "Edit", "Glob", "Grep", f"Bash(python3 {dt}:*)"])
    record(run, "fix", cost)
    reply["oracle_check"] = oracle_check(run, reply)
    rev = route_reverted(run, reply["oracle_check"], dt)
    if rev:
        record(run, "oracle_revert", rev)
    (run / "review" / "fix.json").write_text(json.dumps(reply, indent=1))
    shutil.rmtree(proj / ".review", ignore_errors=True)
    subprocess.run(["git", "add", "-A", "docs", "tasks", *(["tests/fixtures"] if (proj / "tests/fixtures").exists() else [])],
                   cwd=proj, check=True)
    subprocess.run(["git", "commit", "-qm", "plan review fixes"], cwd=proj)
    print(run.parent.name, "fix:", len(reply.get("applied", [])), "applied,", len(reply.get("skipped", [])), "skipped",
          f"${cost['cost_usd']:.2f};", "oracle values:",
          sum(1 for r in reply["oracle_check"] for c in r.get("checks", []) if c["ok"]), "passed,",
          sum(1 for r in reply["oracle_check"] for c in r.get("checks", []) if not c["ok"]), "reverted")


if __name__ == "__main__":
    run = pathlib.Path(sys.argv[1]).resolve()
    if re.search(r"/iteration-\d+/", str(run)):
        sys.exit(f"plan_review: {run} is an original run; review a copy")
    step = sys.argv[2] if len(sys.argv) > 2 else "all"
    if step == "prepare":
        print(run.parent.name, "prepared:", prepare(run), "packets")
    if step in ("review", "all"):
        review(run)
    if step in ("fix", "all"):
        fix(run)
