#!/usr/bin/env python3
"""Good and bad cases for the grader's structural rules (dtrun.py), one pair or more per check that iteration 7's
findings changed. The good cases are the forms the iteration-7 plans used that the old grader flagged by mistake;
the bad cases are the defects each check must still catch. No dt, no model calls; the dry run runs this too.

Usage: checks.py   prints one line per case; exit 1 if any case comes out wrong
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import dtrun as d  # noqa: E402


def task(id_, kind, step="", writes=(), mode="solo", reads=(), read_symbols=(), acceptance=(), reason="", title=""):
    return {"id": id_, "kind": kind, "step": step, "writes": list(writes), "mode": mode, "reads": list(reads),
            "read_symbols": list(read_symbols), "acceptance": list(acceptance), "reason": reason, "title": title or id_}


def step(name, owner, io="", spine=""):
    i, _, o = io.partition("→")
    return {"name": name, "owner": owner, "in_type": i.strip(), "out_type": o.strip(), "spine": spine}


def pipe(id_, steps, package="quant", entry="", system=False):
    return {"id": id_, "package": package, "entry_file": entry, "system": system, "steps": steps}


def row(a, b, kind, reason="", mitigated=""):
    return {"from": a, "to": b, "kind": kind, "reason": reason, "mitigated_by": mitigated}


CASES = []  # (check id, good|bad, what, got the expected answer)


def case(cid, good, what, ok):
    CASES.append((cid, "good" if good else "bad", what, bool(ok)))


# ---- unmitigated_reasoned (interface F3): integration, file, same module, contract change, order; by structure
pl1 = pipe("PL-01", [step("read_raw", "data.read", "Universe → RawPrices"), step("apply_universe", "data.universe", "RawPrices → Prices")],
           entry="src/quant/data/pipeline.py")
pl2 = pipe("PL-02", [step("estimate_cov", "stats.cov", "Returns → Cov"), step("clean_eigen", "stats.rmt", "Cov → Cov")],
           entry="src/quant/stats/pipeline.py")
info = {f"{p['id']}.{s['name']}": s for p in (pl1, pl2) for s in p["steps"]}
T = {t["id"]: t for t in [
    task("T02", "spine", "PL-01.read_raw", ["src/quant/data/read.py", "tests/unit/test_read.py"]),
    task("T03", "spine", "PL-01.apply_universe", ["src/quant/data/universe.py"]),
    task("T04", "spine", "PL-02.estimate_cov", ["src/quant/stats/cov.py"]),
    task("T05", "spine", "PL-02.clean_eigen", ["src/quant/stats/rmt.py"]),
    task("T08", "wiring", "PL-01", ["src/quant/data/pipeline.py", "tests/unit/test_pl01.py"]),
    task("T09", "wiring", "PL-02", ["src/quant/stats/pipeline.py", "tests/unit/test_pl02.py"]),
    task("T10", "thicken", "PL-01.apply_universe", ["src/quant/data/universe.py"], mode="split"),
    task("T12", "thicken", "PL-02.estimate_cov", ["src/quant/stats/cov_shrink.py"], mode="split"),
    task("T14", "system", "PL-02", ["src/quant/stats/pipeline.py"], reads=["PL-01", "PL-02"]),
]}
for r_, want in [(row("T08", "T02", "code", "the smoke runs it"), "integration"),
                 (row("T09", "T04", "order", "integration: the smoke runs the real steps"), "order"),
                 (d.integration_row(row("T09", "T05", "code", mitigated="integration: the smoke runs it")), "integration"),
                 (row("T10", "T03", "file", "both write universe.py"), "file"),
                 (row("T12", "T04", "code", "extends it"), "same module"),
                 (row("T14", "T08", "code", "the real chain runs them"), "integration"),
                 (row("T04", "T03", "contract-change", "new interface task"), "contract change")]:
    got, _ = d.unmitigated_class(r_, T, info)
    case("unmitigated_reasoned", True, f"{r_['from']}→{r_['to']} {r_['kind']} '{r_['reason']}' is {want}", got == want)
for r_, why in [(row("T05", "T04", "code", "clean_eigen needs a real estimate"), "code edge between two steps' tasks"),
                (row("T12", "T05", "data", "it's simpler"), "no allowed structure"),
                (row("T08", "T02", "code", ""), "no reason"),
                (row("T99", "T02", "data", "same module"), "names a task outside the plan"),
                (row("T08", "T04", "code", "the smoke runs it"), "no allowed structure")]:  # wiring of PL-01 → PL-02's spine
    got, w = d.unmitigated_class(r_, T, info)
    case("unmitigated_reasoned", False, f"{r_['from']}→{r_['to']} {r_['kind']} '{r_['reason']}' flagged ({why})", not got and w == why)
pl3 = pipe("PL-03", [step("load_config", "catalog.config", "name → RunConfig", "PL-01 as built"), step("train_ref", "reference.sb3", "RunConfig → RunDir")])
plc = pipe("PL-01", [step("load_config", "catalog.config", "name → RunConfig")])
info3 = {"PL-01.load_config": plc["steps"][0], "PL-03.train_ref": pl3["steps"][1]}
T3 = {"T02": task("T02", "spine", "PL-01.load_config"), "T23": task("T23", "wiring", "PL-03"),
      "T37": task("T37", "system", "PL-04", reads=["PL-04"]), "T38": task("T38", "system", "PL-05", reads=["PL-04", "PL-05"])}
case("unmitigated_reasoned", True, "wiring PL-03 waits on the spine of a step it shares with PL-01: integration",
     d.unmitigated_class(row("T23", "T02", "code", "the smoke runs it"), T3, info3, {"PL-01": plc, "PL-03": pl3})[0] == "integration")
case("unmitigated_reasoned", True, "a system task waits on the system task of a pipeline it swaps in: integration",
     d.unmitigated_class(row("T38", "T37", "code", "serves the version it built"), T3, info3, {})[0] == "integration")
case("unmitigated_reasoned", False, "an interface task waiting on another interface task",
     not d.unmitigated_class(row("T04", "T03", "code", "generates its types from T03's schema"),
                             {"T04": task("T04", "interface", "contract", ["web/src/api/types.ts"]), "T03": task("T03", "interface", "contract", ["server/**"])}, {})[0])
case("unmitigated_reasoned", True, "a mitigated row stays mitigated", d.integration_row(row("T09", "T08", "call", mitigated="data.load_prices fake"))["mitigated_by"])

# ---- writes_disjoint (interface F6): owner → path, package-local tests, one folder glob
for writes, owner, pkgs in [(["src/gridlab/experiments/build.py", "tests/unit/test_build.py"], "experiments.build", ()),
                            (["packages/web/src/views/stock.tsx", "packages/web/tests/stock.test.tsx"], "web.views.stock", ("web", "server")),
                            (["src/gridlab/viewer/draw/**", "tests/unit/test_draw.py"], "viewer.draw", ()),
                            (["src/quant/data/read.py", "tests/unit/quant/test_read.py"], "data", ())]:
    case("writes_disjoint", True, f"spine of {owner} writing {writes}", not d.spine_writes_problem(writes, owner, pkgs))
for writes, owner, why in [(["src/gridlab/train/loop.py", "src/gridlab/train/checkpoints.py"], "train.loop", "a helper module beside the owner"),
                           (["src/gridlab/experiments/build.py", "tests/intent/test_build.py"], "experiments.build", "an intent test"),
                           (["src/gridlab/viewer/*.py"], "viewer", "a file glob"),
                           (["src/gridlab/research/eda.py"], "server.routes", "another module")]:
    case("writes_disjoint", False, f"spine of {owner} writing {writes} ({why})", d.spine_writes_problem(writes, owner, ()))

# ---- phase0_split (interface F7): shared owner modules, system pipelines, package-local smoke tests, folds
src = pipe("PL-05", [step("fetch_bars", "data.source", "Universe → Bars"), step("fetch_actions", "data.source", "Universe → Actions"),
                     step("validate", "data.validate", "Bars → Report")], package="data", entry="packages/data/src/data/pipeline.py")
sysp = pipe("PL-01", [], package=None, system=True)
good_tasks = [task("T01", "interface", "contract", ["packages/data/src/data/**", "tests/contracts/**"]),
              task("T05", "spine", "PL-05.fetch_bars", ["packages/data/src/data/source.py"]),
              task("T06", "thicken", "PL-05.validate", ["packages/data/src/data/validate.py"], mode="split", reason="fold: whole behavior is its spine, golden case"),
              task("T07", "wiring", "PL-05", ["packages/data/src/data/pipeline.py", "packages/data/e2e/pl05.spec.ts"]),
              task("T33", "system", "PL-01", ["tests/system/test_e2e.py"], reads=["PL-01"])]
names = {"Universe", "Bars", "Actions", "Report"}
miss = d.phase0_misses([src, sysp], good_tasks, {"T01"}, names, ("data", "web"))
case("phase0_split", True, "steps sharing data.source share one spine; a fold Reason; an e2e smoke spec; a system task", not miss)
bad_tasks = [t for t in good_tasks if t["id"] not in ("T06", "T33")] + [
    task("T06", "thicken", "PL-05.validate", ["packages/data/src/data/validate.py"], mode="split", reason="it's small")]
bad_tasks = [t if t["id"] != "T07" else task("T07", "wiring", "PL-05", ["packages/data/src/data/pipeline.py"]) for t in bad_tasks]
miss = d.phase0_misses([src, sysp], bad_tasks, {"T01"}, names, ("data", "web"))
case("phase0_split", False, "an unrecorded fold", any("PL-05.validate: 0 spine" in m for m in miss))
case("phase0_split", False, "a wiring task with no smoke test", any("PL-05: 1 wiring tasks, 0 writing" in m for m in miss))
case("phase0_split", False, "a system pipeline no system task names", any("PL-01: system pipeline" in m for m in miss))
two = pipe("PL-06", [step("a", "data.one", "X → Y"), step("b", "data.two", "Y → Z")], package="data", entry="packages/data/src/data/p6.py")
miss = d.phase0_misses([two], [task("T01", "interface"), task("T02", "spine", "PL-06.a"),
                                task("T03", "wiring", "PL-06", ["packages/data/src/data/p6.py", "packages/data/tests/test_p6.py"])],
                       {"T01"}, {"X", "Y", "Z"}, ("data",))
case("phase0_split", False, "two owner modules, one spine task", miss == ["PL-06.b: 0 spine tasks"])

# ---- interface_coverage (interface F8): Out → In boundaries; a named case the interface task writes
rl = pipe("PL-02", [step("make_agent", "core.agents", "AgentSpec → Agent"), step("create_run", "runstore.writer", "RunConfig → RunWriter"),
                    step("train", "train.loop", "Agent, RunWriter → RunDir")])
b = [(x["name"], y["name"], t) for x, y, t in d.boundaries(rl)]
case("interface_coverage", True, "boundaries are Out → In matches, not adjacent rows",
     b == [("make_agent", "train", ["Agent"]), ("create_run", "train", ["RunWriter"])])
iface = [task("T01", "interface", "contract", ["src/gridlab/core/**", "tests/contracts/**"])]
case("interface_coverage", True, "a named case the interface task writes", d.named_case({"Cases": "one replayed episode"}) and d.sample_written("core.Agent", iface))
case("interface_coverage", True, "a Sample field whose folder exists", d.named_case({"Sample": "tests/contracts/core.Env/"}) and d.sample_written("core.Env", [], on_disk=True))
case("interface_coverage", True, "Cases and Fixtures written on the Boundary line",
     "3 dates around" in d.named_case({"Boundary": "research, server · Fixtures: tests/contracts/data.Membership/ · Cases: 3 dates around an index change"}))
case("interface_coverage", True, "an interface task writing `tests/contracts/data.*/**`",
     d.sample_written("data.Membership", [task("T01", "interface", "contract", ["packages/data/src/data/**", "tests/contracts/data.*/**"])]))
case("interface_coverage", False, "`tests/contracts/data.*/**` doesn't cover a server type",
     not d.sample_written("server.App", [task("T01", "interface", "contract", ["tests/contracts/data.*/**"])]))
case("interface_coverage", False, "no case named", not d.named_case({"Invariants": "N×N", "Cases": "—"}))
case("interface_coverage", False, "a Boundary line with no case", not d.named_case({"Boundary": "server · Used by: PL-09"}))
case("interface_coverage", False, "a case no interface task writes", not d.sample_written("core.Agent", [task("T01", "interface", "contract", ["src/gridlab/core/**"])]))
case("interface_coverage", False, "an untyped cross-owner pair",
     d.boundaries(pipe("PL-03", [step("load", "data.io", "path → frame"), step("fit", "model.fit", "frame → fitted")])) != [])

# ---- tester_starts_early (interface F9): methods, the interface's own signatures, the task's own step
decl = {"data.Loader", "stats.Cov"}
case("tester_starts_early", True, "a method of a declared class", d.tester_early(task("T20", "thicken", mode="split", read_symbols=["data.Loader.search"]), decl))
inf = {"PL-02.clean_eigen": {"name": "clean_eigen"}}
case("tester_starts_early", True, "its own step's function", d.tester_early(task("T21", "thicken", "PL-02.clean_eigen", mode="split", read_symbols=["stats.clean_eigen", "stats.Cov"]), decl, inf))
syms = [{"id": "baselines.make_baseline", "is_type": False, "doc": "docs/packages/gridlab/contract.md"},
        {"id": "server.get_run", "is_type": False, "doc": "docs/packages/server/contract.md"},
        {"id": "core.Env", "is_type": True, "doc": "docs/packages/gridlab/contract.md"}]
iface = [task("T01", "interface", "contract", ["src/gridlab/**", "tests/contracts/**"],
              acceptance=["Every M1 step and contract function exists with its signature"])]
got = d.interface_writes_symbols(iface, syms)
case("tester_starts_early", True, "an interface writing every contract function declares its package's functions", got == {"baselines.make_baseline"})
case("tester_starts_early", False, "an undeclared symbol", not d.tester_early(task("T22", "thicken", mode="split", read_symbols=["stats.shrink_target"]), decl))
case("tester_starts_early", False, "a split task reading no symbol", not d.tester_early(task("T31", "thicken", "PL-02.clean_eigen", mode="split"), decl, inf))
case("tester_starts_early", False, "an interface that writes only types declares no function",
     not d.interface_writes_symbols([task("T01", "interface", "contract", ["src/gridlab/**"], acceptance=["Every type is a dataclass"])], syms))
case("tester_starts_early", False, "a solo task has no tester half", not d.tester_early(task("T23", "thicken", read_symbols=["stats.Cov"]), decl))

# ---- fakes_only_cross_pipeline (interface F1, F10): cross-package calls; a replay double is a sample
pl4 = pipe("PL-04", [step("trading_days", "data.calendar", "dates → Days", "data.trading_days(start, today)"),
                     step("build", "builder.build", "Days → Tables")], package="builder")
case("fakes_only_cross_pipeline", True, "a step owned by another package is a call", d.call_step(pl4, pl4["steps"][0], ("data", "builder")))
case("fakes_only_cross_pipeline", True, "a step whose spine names another pipeline is a call", d.call_step(pl2, step("load", "data", "", "PL-01 as built")))
case("fakes_only_cross_pipeline", True, "Cases naming a replay double", d.is_double({"Cases": "a fixture-backed fake replaying a recorded 5-step episode"}))
case("fakes_only_cross_pipeline", False, "a step of the pipeline's own package is no call", not d.call_step(pl4, pl4["steps"][1], ("data", "builder")))
case("fakes_only_cross_pipeline", False, "a sample payload is no double", not d.is_double({"Sample": "tests/contracts/stats.Cov/sample.json"}))

# ---- wave_width (interface F11): spine units by owner module; spines and tester halves only
m = [pipe("PL-09", [step("a", "data.validate", "X → Y"), step("b", "data.validate", "Y → Y"), step("c", "data.flags", "Y → Z"),
                    step("d", "core", "Z → W"), step("e", "core", "W → V")])]
case("wave_width", True, "steps sharing data.validate are one unit; a bare owner counts per step", len(d.wave_units(m)) == 4)
ts = [task("T01", "interface"), task("T02", "spine", "PL-09.a"), task("T03", "spine", "PL-09.c"),
      task("T04", "thicken", "PL-09.b", mode="split", read_symbols=["data.Y"]),
      task("T05", "thicken", "PL-09.d"), task("T06", "wiring", "PL-09")]
deps = {"T01": [], "T02": ["T01"], "T03": ["T01"], "T04": ["T02"], "T05": ["T01"], "T06": ["T01"]}
spines, testers = d.wave_ready(ts, {"T01"}, deps, {"data.Y"})
case("wave_width", True, "spines and tester halves count", spines == ["T02", "T03"] and testers == ["T04"])
case("wave_width", False, "a solo thicken and a wiring task ready after the interface don't count", "T05" not in spines + testers and "T06" not in spines + testers)
case("wave_width", False, "3 ready against 4 units is under 0.8", len(spines + testers) < 0.8 * len(d.wave_units(m)))

# ---- no_edge_to_code_when_interface (interface F13): file edges skipped; wiring → a frozen other component
srv = pipe("PL-13", [step("open_loader", "data.Loader", "Path → Loader"), step("mount_dataset_routes", "server.routes", "Loader → App")],
           package="server", entry="packages/server/src/server/app.py")
inf13 = {f"PL-13.{s['name']}": s for s in srv["steps"]} | {"PL-02.estimate_cov": pl2["steps"][0]}
w26 = task("T26", "wiring", "PL-13", ["packages/server/src/server/app.py"])
PK = ("data", "server", "web")
case("no_edge_to_code_when_interface", False, "wiring PL-13 (server) waits on the data.Loader spine although T01 fakes data.Loader",
     d.wiring_crosses_frozen(w26, task("T10", "spine", "PL-13.open_loader"), {"PL-13": srv}, inf13, {"data.Loader"}, PK))
lib = pipe("PL-04", [step("estimate_cov", "stats.cov", "Returns → Cov")], entry="src/quant/stats/pipeline.py")
uses = pipe("PL-03", [step("estimate_cov", "stats.cov", "Returns → Cov", "PL-04 as built"), step("min_variance", "portfolio.minvar", "Cov → Weights")],
            entry="src/quant/portfolio/pipeline.py")
case("no_edge_to_code_when_interface", False, "wiring PL-03 waits on PL-04's spine although the plan fakes stats.estimate_cov",
     d.wiring_crosses_frozen(task("T30", "wiring", "PL-03"), task("T31", "spine", "PL-04.estimate_cov"), {"PL-03": uses, "PL-04": lib},
                             {"PL-04.estimate_cov": lib["steps"][0]}, {"stats.estimate_cov"}))
case("no_edge_to_code_when_interface", True, "the same call with no fake declared for it (a signature isn't a fake)",
     not d.wiring_crosses_frozen(w26, task("T10", "spine", "PL-13.open_loader"), {"PL-13": srv}, inf13, set(), PK))
case("no_edge_to_code_when_interface", True, "wiring waits on its own pipeline's spine owned by another component of its package",
     not d.wiring_crosses_frozen(task("T27", "wiring", "PL-02"), T["T04"], {"PL-02": pl2}, info, {"stats.Cov", "stats.cov"}))
case("no_edge_to_code_when_interface", True, "two thickens writing one module are a file edge (reported, not a violation)",
     d.writes_overlap(task("T31", "thicken", writes=["packages/data/src/data/validate.py"]), task("T30", "thicken", writes=["packages/data/src/data/validate.py"])))

# ---- first_planned_rest_designed (flow F4): stages with no rows; dt's Cut is now Split, both read as cut
st = [{"id": "S1", "name": "data", "derived": "Planned"}, {"id": "S2", "name": "structure", "derived": "Cut"},
      {"id": "S3", "name": "features", "derived": "Split"}, {"id": "S4", "name": "agents", "derived": "Building"}]
case("first_planned_rest_designed", True, "Planned, Cut, Split and Building stages all have rows", not d.stages_uncut(st))
st2 = st + [{"id": "S5", "name": "fish", "derived": "Designed"}, {"id": "S6", "name": "foraging", "derived": "Specced"}]
case("first_planned_rest_designed", False, "a Designed and a Specced stage have no rows", d.stages_uncut(st2) == ["S5 fish=Designed", "S6 foraging=Specced"])

# ---- milestone_depends (interface F12): the skill's `M1 (what it needs)` form
case("milestone_depends", True, "`M1 (PL-01 output, runstore.RunDir)` depends on M1",
     d.depends_cell("M1 (PL-01 output, runstore.RunDir)") == (["M1"], {"M1": "PL-01 output, runstore.RunDir"}))
case("milestone_depends", True, "`M1, M2 (stats.Cov)`", d.depends_cell("M1, M2 (stats.Cov)") == (["M1", "M2"], {"M2": "stats.Cov"}))
case("milestone_depends", False, "a Depends cell naming no milestone", d.depends_cell("PL-01 output")[0] == [])
case("milestone_depends", False, "`—` names no milestone", d.depends_cell("—")[0] == [])

# ---- gate_discipline (flow F6, F7e): a routed two-turn Revise; skills attributed by dt status and reference reads
prev = {"status": "docs/packages/quant/pipelines.md: Draft (2026-10-17)\ndocs/architecture.md: Approved (2026-10-17)",
        "assistant": "The steps need two contract types. May I run the architecture revision to add them?"}
changed = ["docs/architecture.md", "docs/packages/quant/contract.md", "docs/packages/quant/pipelines.md"]
case("gate_discipline", True, "arch + pipelines after a turn that left pipelines Draft and asked for the Revise",
     d.routed_revise({"arch", "pipelines"}, prev, changed))
case("gate_discipline", True, "arch + tests the same way",
     d.routed_revise({"arch", "tests"}, {**prev, "status": "docs/packages/quant/tests.md: Draft (x)"}, ["docs/packages/quant/tests.md", "docs/architecture.md"]))
case("gate_discipline", False, "the single-turn case: pipelines were Approved before",
     not d.routed_revise({"arch", "pipelines"}, {**prev, "status": "docs/packages/quant/pipelines.md: Approved (x)"}, changed))
case("gate_discipline", False, "the turn before drafted the architecture and pipelines itself (it didn't stop at its gate)",
     not d.routed_revise({"arch", "pipelines"}, prev, changed, prev_layers={"arch", "pipelines"}))
case("gate_discipline", True, "the turn before drafted only the pipelines", d.routed_revise({"arch", "pipelines"}, prev, changed, prev_layers={"pipelines"}))
case("gate_discipline", False, "no Revise asked for", not d.routed_revise({"arch", "pipelines"}, {**prev, "assistant": "Pipelines drafted."}, changed))
case("gate_discipline", False, "arch + plan is never a routed Revise", not d.routed_revise({"arch", "plan"}, prev, changed + ["tasks/plan.md"]))
turns = [{"turn": 10, "skills": ["dev-team:pipeline-design"]}, {"turn": 11, "skills": []}, {"turn": 12, "skills": []}]
calls = [{"turn": 11, "input": {"command": "python3 skills/../scripts/dt.py status --skill pipeline-design --json"}},
         {"turn": 12, "input": {"file_path": "/x/plugin/dev-team/skills/architecture-design/references/revise.md"}}]
sk = d.turn_skill_map(turns, calls)
case("gate_discipline", True, "a turn running `dt status --skill pipeline-design` is pipeline-design's", sk[11] == {"pipeline-design"})
case("gate_discipline", True, "a turn reading architecture-design's references is architecture-design's", sk[12] == {"architecture-design"})
case("gate_discipline", False, "a turn with no Skill call, dt status or skill read is no skill's",
     d.turn_skill_map([{"turn": 13, "skills": []}], [{"turn": 13, "input": {"command": "git status"}}])[13] == set())

# ---- intake_subagent_per_file (flow F7e): intake turns without a Skill call
tt = [{"turn": 41, "skills": [], "agents": [{"description": "Summarize tft_model.py"}, {"description": "Summarize tft_targets.py"}]},
      {"turn": 42, "skills": [], "agents": [{"description": "Explore the repo layout"}]},
      {"turn": 43, "skills": [], "agents": [{"description": "Read the new file"}]}]
got = [t["turn"] for t in d.intake_turns(tt, {41: set(), 42: set(), 43: set()}, refs_changed={43})]
case("intake_subagent_per_file", True, "Agents named `Summarize <file>.py`, no Skill call: an intake turn", 41 in got)
case("intake_subagent_per_file", True, "a docs/references.md change with Agent launches: an intake turn", 43 in got)
case("intake_subagent_per_file", False, "an unrelated Agent launch is no intake turn", 42 not in got)

# ---- spec_ml_beats_classical (flow F7c): the bar against S2's named benchmark
case("spec_ml_beats_classical", True, "the agent scored against S2's best strategy",
     d.ML_BEATS_CLASSICAL.search("AGENT-05: the PPO agent's portfolio is scored against S2's benchmark out of sample"))
case("spec_ml_beats_classical", True, "the old wording still matches", d.ML_BEATS_CLASSICAL.search("The PPO portfolio beats minimum-variance"))
case("spec_ml_beats_classical", False, "no comparison at all", not d.ML_BEATS_CLASSICAL.search("The agent trains for one hour on CPU."))

# ---- types_in_contract (judge H3): the types a type section's fields use
text = "### core.RunConfig: type\n`class RunConfig: world: WorldSettings; learners: dict[str, LearnerSettings | PolicyRef]; seed: int`\n- **Cases:** one config"
contract = text + "\n### core.PolicyRef: type\n`class PolicyRef: path: Path`\n"
undefined = [n for n in d.field_types(text) if not d.defined_in(n, contract)]
case("types_in_contract", False, "WorldSettings and LearnerSettings are defined nowhere", undefined == ["WorldSettings", "LearnerSettings"])
ok_text = "`class Prices: frame: DataFrame  # dates × tickers; def returns(self) -> Returns`\n- **Invariants:** a Snake episode: T×N"
case("types_in_contract", True, "library types, comments and prose are left out", d.field_types(ok_text) == [])
case("types_in_contract", True, "a type defined inline resolves", d.defined_in("CovMethod", "`CovMethod = Literal['sample', 'shrink']`"))


# ---- data_sources_suggested (iteration-8 follow-up): the agent's own sources beyond Sharadar prices and yahooquery
f, fund = d.data_sources({"docs/architecture.md": "- **Alternatives:** Tiingo (raw closes); SEC EDGAR company facts "
                          "(XBRL) for fundamentals, deferred to S3."})
case("data_sources_suggested", True, "a fundamentals source among the alternatives counts", fund == ["SEC EDGAR / XBRL"] and "Tiingo" in f)
f, fund = d.data_sources({"docs/architecture.md": "Fundamentals from Sharadar's SF1 table, on the same subscription."})
case("data_sources_suggested", True, "Sharadar SF1, named as the fundamentals source, counts", fund == ["Sharadar SF1"])
f, fund = d.data_sources({"docs/architecture.md": "Prices from Sharadar SEP; cross-checked against Yahoo via yahooquery, "
                          "with EODHD and Polygon considered for prices."})
case("data_sources_suggested", False, "price sources alone, and Sharadar without SF1, don't count", not fund and sorted(f) == ["EODHD", "Polygon"])
f, fund = d.data_sources({"docs/brief.md": "- Intraday data, fundamentals or live streaming — daily prices first."})
case("data_sources_suggested", False, "fundamentals ruled out, no source named", not f and not fund)


def run(verbose=True):
    """The cases that came out wrong (empty when all hold)."""
    wrong = [c for c in CASES if not c[3]]
    if verbose:
        ids = sorted({c[0] for c in CASES})
        lacking = [i for i in ids if {"good", "bad"} - {c[1] for c in CASES if c[0] == i}]
        print(f"selftest/checks.py: {len(CASES) - len(wrong)}/{len(CASES)} cases as expected over {len(ids)} checks"
              + (f"; checks without both a good and a bad case: {lacking}" if lacking else ""))
        for c in wrong:
            print(f"  WRONG [{c[0]}] {c[1]}: {c[2]}")
        wrong += [("checks.py", "pair", f"{i} lacks a good or a bad case", False) for i in lacking]
    return wrong


if __name__ == "__main__":
    for c in CASES:
        print(("ok    " if c[3] else "WRONG ") + f"[{c[0]}] {c[1]}: {c[2]}")
    sys.exit(1 if run() else 0)
