#!/usr/bin/env python3
"""Good and bad cases for the grader's structural rules (dtrun.py, probefacts.py, probegrade.py, planexport.py), one
pair or more per check that iteration 7's, 8's and 9's findings changed. The good cases are the forms those plans used that the old grader flagged by mistake;
the bad cases are the defects each check must still catch. No dt, no model calls; the dry run runs this too.

Usage: checks.py   prints one line per case; exit 1 if any case comes out wrong
"""
import json, pathlib, re, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import dtrun as d  # noqa: E402
import probefacts as pf  # noqa: E402


def task(id_, kind, step="", writes=(), mode="solo", reads=(), read_symbols=(), acceptance=(), reason="", title=""):
    return {"id": id_, "kind": kind, "step": step, "writes": list(writes), "mode": mode, "reads": list(reads),
            "read_symbols": list(read_symbols), "acceptance": list(acceptance), "reason": reason, "title": title or id_}


def step(name, owner, io="", spine="", covers=()):
    i, _, o = io.partition("→")
    return {"name": name, "owner": owner, "in_type": i.strip(), "out_type": o.strip(), "spine": spine, "covers": list(covers)}


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
# Iteration 8's F3: wiring waits on spines and folds only; two thickens of one Step aren't one module by that alone.
T8 = {**T, "T11": task("T11", "thicken", "PL-01.read_raw", ["src/quant/data/views.py"], mode="split", reason="library module behind read_raw"),
      "T13": task("T13", "thicken", "PL-01.read_raw", ["src/quant/data/rules.py"], mode="split"),
      "T15": task("T15", "thicken", "PL-02.pca", ["src/quant/stats/pca.py"], mode="split", reason="spine folded into the thicken: TC-03 checks it")}
case("unmitigated_reasoned", True, "wiring waits on a step whose only task is a recorded fold: integration",
     d.unmitigated_class(row("T09", "T15", "order", "integration: the smoke runs it"), T8, info | {"PL-02.pca": step("pca", "stats.pca")})[0] == "order")
for r_, why in [(row("T08", "T11", "order", "integration: the smoke builds the views"), "wiring waits on a thicken task that isn't a fold"),
                (row("T08", "T10", "code", "the smoke runs it"), "wiring waits on a thicken task that isn't a fold"),
                (row("T13", "T11", "data", "the rules need real views"), "no allowed structure")]:
    got, w = d.unmitigated_class(r_, T8, info)
    case("unmitigated_reasoned", False, f"{r_['from']}→{r_['to']} {r_['kind']} '{r_['reason']}' flagged ({why})", not got and w == why)

# ---- writes_disjoint (interface F6): owner → path, package-local tests, one folder glob
for writes, owner, pkgs in [(["src/gridlab/experiments/build.py", "tests/unit/test_build.py"], "experiments.build", ()),
                            (["packages/web/src/views/stock.tsx", "packages/web/tests/stock.test.tsx"], "web.views.stock", ("web", "server")),
                            (["src/gridlab/viewer/draw/**", "tests/unit/test_draw.py"], "viewer.draw", ()),
                            (["src/quant/data/read.py", "tests/unit/quant/test_read.py"], "data", ()),
                            # it8 quant inc F11: two files inside the owner's folder are the owner
                            (["packages/cockpit/src/api/client.ts", "packages/cockpit/src/api/validate.ts",
                              "tests/unit/cockpit/client.test.ts"], "api", ("cockpit",))]:
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
# Iteration 8's F4: bare owners name modules; a spine's Reason or Writes says which steps it builds; call steps stay.
cli = pipe("PL-16", [step("read_settings", "cli", "argv → Settings"), step("judge", "cli", "Settings → Verdicts"),
                     step("train_seeds", "lab.runs", "Settings → Runs", "PL-01 as built"), step("report_runs", "lab.runs", "Runs → Report"),
                     step("fetch", "api", "Route → Dto")], package="lab", entry="packages/lab/src/lab/pl16.py")
wire16 = task("T09", "wiring", "PL-16", ["packages/lab/src/lab/pl16.py", "packages/lab/tests/test_pl16.py"])
t16 = [task("T01", "interface"), task("T02", "spine", "PL-16.read_settings", reason="`read_settings` and `judge` share cli.py"),
       task("T03", "spine", "PL-16.train_seeds"), task("T04", "spine", "PL-01.other", ["packages/lab/src/lab/api.ts"]), wire16]
names16 = {"Settings", "Verdicts", "Runs", "Report", "Dto", "Route"}
case("phase0_split", True, "a step named in a spine's Reason, a call step's unit, a spine writing the owner module",
     not d.phase0_misses([cli], t16, {"T01"}, names16, ("lab",)))
case("wave_width", True, "a Reason-shared bare owner is one unit; a call step's module counts once",
     len(d.wave_units([cli], t16, ("lab",))) == 3)
miss = d.phase0_misses([cli], [x for x in t16 if x["id"] != "T02"] + [task("T02", "spine", "PL-16.read_settings")], {"T01"}, names16, ("lab",))
case("phase0_split", False, "a bare-owner step no spine names or owns", miss == ["PL-16.judge: 0 spine tasks"])
case("phase0_split", True, "a fold recorded anywhere in the Reason",
     not d.phase0_misses([two], [task("T01", "interface"), task("T02", "spine", "PL-06.a"),
                                 task("T04", "thicken", "PL-06.b", mode="split", reason="spine folded into the thicken: TC-28 checks it"),
                                 task("T03", "wiring", "PL-06", ["packages/data/src/data/p6.py", "packages/data/tests/test_p6.py"])],
                         {"T01"}, {"X", "Y", "Z"}, ("data",)))

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
iface_cls = [task("T01", "interface", "contract", ["src/gridlab/**", "tests/contracts/**"],
                  acceptance=["Every M1 step and contract class imports with its contract signature"])]
cls_syms = syms + [{"id": "core.Corridor", "is_type": True, "title": "Corridor test environment", "doc": "docs/packages/gridlab/contract.md"},
                   {"id": "core.LADDER", "is_type": True, "title": "The ladder rungs", "doc": "docs/packages/gridlab/contract.md"}]
cls_syms[2] = dict(cls_syms[2], title="type")
case("tester_starts_early", True, "an interface writing every contract class declares the class sections too (it8 rl inc F5)",
     d.interface_writes_symbols(iface_cls, cls_syms) == {"baselines.make_baseline", "core.Corridor"})
case("tester_starts_early", False, "...but not the boundary types or constants, which its Read declares (it8 rl inc F12: CrossPlay)",
     not {"core.Env", "core.LADDER"} & d.interface_writes_symbols(iface_cls, cls_syms))
case("tester_starts_early", False, "an interface writing every step signature declares no class",
     "core.Corridor" not in d.interface_writes_symbols(iface, cls_syms))
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
case("fakes_only_cross_pipeline", True, "'PL-19's estimator step for the name, as built' is a call",
     d.call_step(pl2, step("estimate", "stats", "", "the PL-19 estimator step for the requested name, as built")))
case("fakes_only_cross_pipeline", False, "'as in PL-06' reuses that function in its own module, no call (it8 quant inc F7)",
     not d.call_step(pl2, step("read_tables", "snapshots.read", "", "as in PL-06")))
case("fakes_only_cross_pipeline", False, "a PL-NN named for its output is data, no call",
     not d.call_step(pl2, step("load_windows", "data", "", "PL-36's saved windows")))
case("fakes_only_cross_pipeline", True, "a fake glob stands for the contract symbols it matches (it8 quant aao F8)",
     d.expand_globs(["data.load_*", "data.security_info"], ["data.load_prices", "data.load_universe", "data.security_info", "stats.load_x"])
     == ["data.load_prices", "data.load_universe", "data.security_info"])
case("fakes_only_cross_pipeline", False, "a glob matching no contract symbol stays, to be reported",
     d.expand_globs(["data.fetch_*"], ["data.load_prices"]) == ["data.fetch_*"])
case("fakes_only_cross_pipeline", True, "Cases naming a replay double", d.is_double({"Cases": "a fixture-backed fake replaying a recorded 5-step episode"}))
case("fakes_only_cross_pipeline", False, "a step of the pipeline's own package is no call", not d.call_step(pl4, pl4["steps"][1], ("data", "builder")))
case("fakes_only_cross_pipeline", False, "a sample payload is no double", not d.is_double({"Sample": "tests/contracts/stats.Cov/sample.json"}))

# ---- wave_width (interface F11): spine units by owner module; spines and tester halves only
m = [pipe("PL-09", [step("a", "data.validate", "X → Y"), step("b", "data.validate", "Y → Y"), step("c", "data.flags", "Y → Z"),
                    step("d", "core", "Z → W"), step("e", "core", "W → V")])]
case("wave_width", True, "steps sharing data.validate are one unit; a bare owner counts per step", len(d.wave_units(m)) == 4)
ts = [task("T01", "interface"), task("T02", "spine", "PL-09.a"), task("T03", "spine", "PL-09.c"),
      task("T04", "thicken", "PL-09.e", mode="split", read_symbols=["data.Y"], reason="fold: spine folded into the thicken"),
      task("T05", "thicken", "PL-09.d"), task("T06", "wiring", "PL-09"),
      task("T07", "thicken", "PL-09.b", mode="split", read_symbols=["data.Y"])]
deps = {"T01": [], "T02": ["T01"], "T03": ["T01"], "T04": ["T02"], "T05": ["T01"], "T06": ["T01"], "T07": ["T02"]}
spines, testers = d.wave_ready(ts, {"T01"}, deps, {"data.Y"})
case("wave_width", True, "spines and a fold's tester half count", spines == ["T02", "T03"] and testers == ["T04"])
case("wave_width", False, "a solo thicken and a wiring task ready after the interface don't count", "T05" not in spines + testers and "T06" not in spines + testers)
case("wave_width", False, "a library thicken's tester half doesn't count (it7 rl inc F11)", "T07" not in testers)
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
case("no_edge_to_code_when_interface", True, "...and so are they for the wiring rule",
     not d.wiring_shared_file(task("T31", "thicken", writes=["packages/data/src/data/validate.py"]), task("T30", "thicken", writes=["packages/data/src/data/validate.py"])))
case("no_edge_to_code_when_interface", False, "two wiring tasks chained on a shared __main__.py (it8 F1)",
     d.wiring_shared_file(task("T09", "wiring", "PL-02", ["src/quant/__main__.py", "src/quant/stats/pipeline.py"]),
                          task("T08", "wiring", "PL-01", ["src/quant/__main__.py", "src/quant/data/pipeline.py"])))

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
# One `claude -p` call (turn 2) prints four inits, as background agents finish: turn 3's calls stay turn 3's.
INIT, RESULT = {"type": "system", "subtype": "init"}, {"type": "result"}
def use(cmd):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}
lines = [INIT, use("ls"), RESULT, INIT, use("git log"), INIT, INIT, INIT, use("git diff"), RESULT, RESULT, RESULT, RESULT,
         INIT, use("python3 dt.py status --skill pipeline-design"), RESULT]
turns = [{"turn": 1, "tools": ["Bash"], "skills": []}, {"turn": 2, "tools": ["Bash", "Bash"], "skills": []},
         {"turn": 3, "tools": ["Bash"], "skills": []}]
with tempfile.TemporaryDirectory() as tmp:
    stream = pathlib.Path(tmp) / "agent_stream.jsonl"
    stream.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    by_init = [c["turn"] for c in pf.tool_calls(stream)]
    (stream.parent / "turns.json").write_text(json.dumps(turns))
    sk = d.turn_skill_map(turns, pf.tool_calls(stream))
case("gate_discipline", True, "a turn after a call that printed four inits keeps its own calls (turns.json counts)",
     sk[3] == {"pipeline-design"})
case("gate_discipline", False, "the four-init call's turn gets no later turn's skill", sk[2] == set())
case("gate_discipline", True, "with no turns.json, inits still split the stream", by_init == [1, 2, 5, 6])

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
ctor = ("`team: dict[str, LearnerEntry | FixedEntry]`, where `LearnerEntry(kind: Literal[\"qtable\", \"dqn\"], settings)` "
        "and `FixedEntry(spec: str)`")
case("types_in_contract", True, "a constructor with every parameter typed defines its type (it8 rl aao F10)", d.defined_in("FixedEntry", ctor))
case("types_in_contract", False, "a constructor with an untyped parameter doesn't", not d.defined_in("LearnerEntry", ctor))
mirror = ("- **Invariants:** mirrors `qdata.Security`; `TickerSpanDto`, `SpellDto` and `ExitDto` mirror their `qdata` types "
          "field for field\n- **Invariants:** `ActionDto` mirrors `qdata.CorporateAction`")
case("types_in_contract", True, "a type that mirrors another, alone or in a list (it8 quant inc F10)",
     all(d.defined_in(n, mirror) for n in ("ActionDto", "SpellDto", "ExitDto", "TickerSpanDto")))
case("types_in_contract", False, "a type only named beside a mirror defines nothing", not d.defined_in("FlagDto", mirror + "; `FlagDto` rows"))


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


# ---- crosscheck_facts_reached_design (the fake Yahoo's planted facts reach the design)
import fakevendor  # noqa: E402
Y = fakevendor.VENDORS["yahoo"].PLANTED
def y_entry(kind="answered", verdict=""):
    return {"id": "PB-02", "kind": kind, "verdict": verdict, "caveats": "", "checks": [{"result": ""}]}
lost = "LEH, BSC, CFC, MER, SGP, WYE and EK return no data."
ok, _ = d.crosscheck_facts([y_entry(verdict=lost + " BUD, DNA and WB now belong to AB InBev, Ginkgo and Weibo.")],
                           "AD-05: Yahoo's close is split-adjusted; no raw close, so raw prices stay Sharadar's.", Y)
case("crosscheck_facts_reached_design", True, "answered, lost names and ticker reuse in the Verdict, no raw close in the decision", ok)
ok, m = d.crosscheck_facts([y_entry(verdict="LEH and MER return no data.")], "AD-05: cross-check closes against Yahoo.", Y)
case("crosscheck_facts_reached_design", False, "names missing from the Verdict, nothing on raw closes or reuse",
     not ok and "BSC" in m["missing_not_named"] and not m["adjusted_only"])
ok, _ = d.crosscheck_facts([y_entry("ready", lost + " DNA is Ginkgo now.")], "Yahoo has no raw close.", Y)
case("crosscheck_facts_reached_design", False, "the facts guessed before the probe is Answered", not ok)


# ---- no_secret_seen, runner_split (iteration-8 flow F5, F6): reading verbs on .env and out/, not text that names them
def bash(cmd):
    return {"name": "Bash", "input": {"command": cmd}}


for cmd, why in [("cat > probes/PB-01/.env.example <<'EOF'\n# Copy to .env in this folder\nKEY=\nEOF", "a heredoc writing .env.example"),
                 ("printf '.env\\n!.env.example\\nprobes/*/out/\\n' >> .gitignore", "ignore patterns into .gitignore"),
                 ("git check-ignore probes/$d/.env probes/$d/out/", "git check-ignore"),
                 ('test -e probes/x/.env && echo "env file present"', "an existence test"), ("grep -n .env .gitignore", "a grep pattern")]:
    case("no_secret_seen", True, f"{why} reads no secret", not pf.secret_reads([bash(cmd)]))
for cmd, why in [("grep -n KEY probes/x/.env", "grep on .env"), (". ./.env", "sourcing .env"), ("done < .env", "an input redirect"),
                 ("python3 - <<'EOF'\nprint(open('.env').read())\nEOF", "python run on a heredoc that opens .env"),
                 ("head -5 probes/PB-01/out/members.json", "head on out/")]:
    case("no_secret_seen", False, f"{why} is a read", pf.secret_reads([bash(cmd)]))
case("runner_split", True, "'python3 probe.py' inside a heredoc's string literal is no run",
     not pf.runs_user_script(bash("python3 - <<'EOF'\nsys.exit(\"usage: python3 probe.py bulk|checks\")\nEOF")))
case("runner_split", True, "a syntax check is no run", not pf.runs_user_script(bash("python3 -m py_compile probes/x/probe.py")))
case("runner_split", False, "probe.py run in its folder", pf.runs_user_script(bash("cd probes/PB-01 && python3 probe.py bulk")))
case("runner_split", False, "probe.py run by a shell heredoc", pf.runs_user_script(bash("bash <<EOF\npython3 probe.py\nEOF")))


# ---- requests_captured, requests_append_only (design/requests.md): the facts iteration 9 lost at session boundaries
SCN = json.loads((pathlib.Path(__file__).resolve().parents[1] / "scenarios.json").read_text())
for pid, p in SCN["projects"].items():
    said = " ".join(p["facts"] + [s["reveal"] for s in p["stages"]])
    unmatched = [f["id"] for f in p.get("stated_facts", []) if not re.search(f["pattern"], said, re.I)]
    case("requests_captured", True, f"{pid}: every stated_facts pattern matches the scenario text it stands for",
         p.get("stated_facts") and not unmatched)
RL = SCN["projects"]["rl"]["stated_facts"]
said = [{"turn": 1, "user": "Environment 2: a circular tank with a ball bouncing around; fish survive as long as possible."},
        {"turn": 4, "user": "Approved. Environment 3: prey forage while a learning predator hunts them."}]
st = d.facts_stated(RL, said)
case("requests_captured", True, "the facts the user said, by turn; an unsaid one isn't counted",
     st == {"circular_tank": [1], "survive": [1], "one_predator": [4]})
case("requests_captured", True, "quoted words with the user's casing capture each stated fact",
     not d.requests_missed(RL, st, ["a circular tank with a ball bouncing around", "fish Survive as long as possible",
                                    "a learning predator hunts them"]))
case("requests_captured", False, "the it9 rl losses: a square tank, a hit count, two predators",
     d.requests_missed(RL, st, ["the tank is a square with walls", "count hits per fish", "2 predators"])
     == ["circular_tank", "survive", "one_predator"])
case("requests_captured", False, "a paraphrase (`Web Socket`) is no verbatim capture",
     d.requests_missed(SCN["projects"]["quant"]["stated_facts"],
                       {"websocket": [1]}, ["live progress over a Web Socket"]) == ["websocket"])
w1 = {"UR-01": "live progress over a WebSocket", "UR-02": "I want yahooquery"}
case("requests_append_only", True, "lines appended, the file first committed at turn 2",
     not d.requests_rewritten([(1, None, []), (2, w1, []), (3, {**w1, "UR-03": "a circular tank"}, [])]))
case("requests_append_only", False, "words reworded at turn 3",
     d.requests_rewritten([(2, w1, []), (3, {**w1, "UR-02": "use a free Yahoo client"}, [])])
     == ['turn 3: UR-02 "I want yahooquery" became "use a free Yahoo client"'])
case("requests_append_only", False, "a line deleted, then the whole file: each line reported once",
     d.requests_rewritten([(2, w1, []), (3, {"UR-01": w1["UR-01"]}, []), (4, None, []), (5, None, [])])
     == ['turn 3: UR-02 "I want yahooquery" vanished', 'turn 4: UR-01 "live progress over a WebSocket" vanished'])
case("requests_append_only", False, "a line that stops parsing counts once",
     d.requests_rewritten([(2, w1, []), (3, {"UR-01": w1["UR-01"]}, ["UR-02"]), (4, {"UR-01": w1["UR-01"]}, ["UR-02"])])
     == ['turn 3: UR-02 "I want yahooquery" no longer parses'])


# ==== iteration 9 (results-iteration-9/findings.md, "Harness: grader") ===========================================

# ---- phase0_split, wave_width (it9 interface F4): only the steps this milestone builds
lab = pipe("PL-01", [step("make_env", "lab.build", "Settings → Env", covers=["CORE-01"]),
                     step("Snake", "envs.snake", "Rewards → Env", covers=["SNAKE-01"]),
                     step("FishTank", "envs.tank", "Rewards → Env", covers=["FISH-01", "FISH-02"]),       # Deferred to M2
                     step("PPOAgent", "agents.ppo", "Params → Agent", covers=["PG-01", "AGENT-06"]),       # PG-01 Deferred
                     step("OpponentPool", "selfplay.pool", "Agent → Pool", covers=["SELF-03"]),            # Deferred: its type too
                     step("DQNAgent", "agents.dqn", "Params → Agent", covers=["AGENT-06"])],
           package="rllab", entry="src/rllab/lab/pipelines/pl01_train.py")
ev = pipe("PL-03", [step("evaluate", "evaluate.protocol", "Agent → ScoreSet", covers=["EVAL-02"]),
                    step("print_scores", "lab.printing", "ScoreSet → ScoreSet", covers=["EVAL-01"])],
          package="rllab", entry="src/rllab/lab/pipelines/pl03_eval.py")
t9 = [task("T01", "interface"), task("T02", "spine", "PL-01.make_env"), task("T03", "spine", "PL-01.Snake"),
      task("T05", "spine", "PL-01.DQNAgent"), task("T06", "spine", "PL-03.evaluate"),
      task("T21", "wiring", "PL-01", ["src/rllab/lab/pipelines/pl01_train.py", "tests/unit/test_pl01.py"]),
      task("T23", "wiring", "PL-03", ["src/rllab/lab/pipelines/pl03_eval.py", "tests/unit/test_pl03.py"],
           reason="`print_scores` is trivial, so this task builds it (fold)")]
names9 = {"Settings", "Env", "Rewards", "Params", "Agent", "ScoreSet"}  # no Pool: OpponentPool is M3's
DEFER = ["FISH-01", "FISH-02", "PG-01", "SELF-03"]
out9 = d.outside_milestone([lab, ev], t9, DEFER, names9, ("rllab",))
case("phase0_split", True, "it9 rl inc: FishTank, PPOAgent and OpponentPool are Deferred (PPO's AGENT-06 is DQN's too)",
     sorted(out9) == ["PL-01.FishTank", "PL-01.OpponentPool", "PL-01.PPOAgent"])
miss = d.phase0_misses([lab, ev], t9, {"T01"}, names9, ("rllab",), out9)
case("phase0_split", True, "...so neither their spines nor OpponentPool's type are missing; a fold named in the wiring's Reason",
     not miss)
case("wave_width", True, "deferred steps and a step the wiring builds are no spine units (it9 rl inc 28 → 18)",
     d.wave_units([lab, ev], t9, ("rllab",), out9) == ["task T02", "task T03", "task T05", "task T06"])
case("phase0_split", False, "with nothing Deferred, the same steps miss their spines and the interface lacks Pool",
     {"PL-01.FishTank: 0 spine tasks", "PL-01: interface lacks ['Pool']"}
     <= set(d.phase0_misses([lab, ev], t9, {"T01"}, names9, ("rllab",), d.outside_milestone([lab, ev], t9, [], names9 | {"FishTank", "PPOAgent", "OpponentPool"}, ("rllab",)))))
own_req = pipe("PL-04", [step("load", "data.load", "Path → Frame", covers=["DATA-01"]),
                         step("clean", "data.clean", "Frame → Frame", covers=["DATA-02", "DATA-09"])], package="data", entry="data/p4.py")
t4 = [task("T01", "interface"), task("T02", "spine", "PL-04.load"), task("T03", "wiring", "PL-04", ["data/p4.py", "tests/test_p4.py"])]
case("phase0_split", False, "a step one of whose Covers is Deferred, but with a requirement only it covers, is still missing",
     d.phase0_misses([own_req], t4, {"T01"}, {"Path", "Frame"}, ("data",), d.outside_milestone([own_req], t4, ["DATA-09"], set(), ("data",)))
     == ["PL-04.clean: 0 spine tasks"])
src9 = pipe("PL-09", [step("SyntheticSource", "vendors_synthetic", "seed → Source", covers=["DATA-01", "DATA-07"]),
                      step("EdgarSicSource", "vendors.edgar", "user agent → Source", "SIC from each header (waits on PB-02)", covers=["DATA-07"]),
                      step("SharadarBars", "vendors.sharadar", "api key → Bars", "get_table per table (waits on PB-01)", covers=["DATA-08"])],
            package="data", entry="data/p9.py")
ts9 = [task("T01", "interface"), task("T04", "spine", "PL-09.SyntheticSource"), task("T05", "wiring", "PL-09", ["data/p9.py", "tests/test_p9.py"])]
o9 = d.outside_milestone([src9], ts9, [], {"Source", "Bars"} | {"EdgarSicSource", "SharadarBars"}, ("data",))
case("phase0_split", True, "it9 quant aao: EdgarSicSource waits on PB-02 and a built stand-in has its Out type", "PL-09.EdgarSicSource" in o9)
case("phase0_split", False, "a probe-blocked step whose Out type no built step has is still missing", "PL-09.SharadarBars" not in o9)
rl2 = pipe("PL-02", [step("DQN", "methods.dqn", "Config → Learner", covers=["CHECK-01", "TRAIN-01"]),
                     step("PPO", "methods.ppo", "Config → Learner", covers=["CHECK-01"])], package="rllab", entry="p2.py")
t2 = [task("T01", "interface"), task("T08", "spine", "PL-02.DQN"), task("T20", "wiring", "PL-02", ["p2.py", "tests/test_p2.py"])]
case("phase0_split", True, "it9 rl aao's PPO: undeclared, named by no task, its one Cover built by DQN",
     "PL-02.PPO" in d.outside_milestone([rl2], t2, [], {"Config", "Learner"}, ("rllab",)))
case("phase0_split", False, "...but declared by the interface it is this milestone's, and missing",
     d.phase0_misses([rl2], t2, {"T01"}, {"Config", "Learner", "PPO"}, ("rllab",),
                     d.outside_milestone([rl2], t2, [], {"Config", "Learner", "PPO"}, ("rllab",))) == ["PL-02.PPO: 0 spine tasks"])
case("phase0_split", False, "a step with no Covers is never outside (the it8 bare-owner case stays a miss)",
     not d.outside_milestone([cli], [x for x in t16 if x["id"] != "T02"] + [task("T02", "spine", "PL-16.read_settings")], [], names16, ("lab",)))
api_s = pipe("PL-11", [step("export_openapi", "api.schema", "App → Doc"), step("write_schema", "api.schema", "Doc → Doc")], package="qserver", entry="s/p11.py")
api_e = pipe("PL-15", [step("readSchema", "api.schema", "path → Doc"), step("generateTypes", "api.schema", "Doc → Schema")], package="explorer", entry="e/p15.ts")
ta = [task("T01", "interface"), task("T24", "spine", "PL-11.export_openapi", reason="also builds write_schema, same module"),
      task("T36", "spine", "PL-15.generateTypes", reason="also builds readSchema: one module"),
      task("T41", "wiring", "PL-11", ["s/p11.py", "tests/test_p11.py"]), task("T44", "wiring", "PL-15", ["e/p15.ts", "tests/p15.test.ts"])]
case("phase0_split", True, "it9 quant inc: qserver's api.schema and explorer's api.schema are two modules, one spine each",
     not d.phase0_misses([api_s, api_e], ta, {"T01"}, {"App", "Doc", "Schema"}, ("qserver", "explorer")))
case("phase0_split", False, "two spines for one package's module are still two",
     d.phase0_misses([api_s], ta + [task("T25", "spine", "PL-11.write_schema")], {"T01"}, {"App", "Doc"}, ("qserver",))
     == ["PL-11.export_openapi: 2 spine tasks", "PL-11.write_schema: 2 spine tasks"])
case("phase0_split", False, "a wiring task that names nothing builds no step",
     d.phase0_misses([ev], [x for x in t9 if x["id"] != "T23"] + [task("T23", "wiring", "PL-03", ["src/rllab/lab/pipelines/pl03_eval.py", "tests/unit/test_pl03.py"])],
                     {"T01"}, names9, ("rllab",)) == ["PL-03.print_scores: 0 spine tasks"])
sv = pipe("PL-10", [step("create_app", "api.app", "Store → App"), step("mount_static", "api.static", "App → App")], package="qserver", entry="s/pl10.py")
tw = [task("T01", "interface"), task("T20", "spine", "PL-10.create_app"),
      task("T40", "wiring", "PL-10", ["s/pl10.py", "s/api/static.py", "tests/test_pl10.py"])]
case("wave_width", True, "it9 quant inc: a step the wiring writes the module of is no spine unit", d.wave_units([sv], tw, ("qserver",)) == ["task T20"])
case("wave_width", False, "...but a step nothing builds still is", d.wave_units([sv], tw[:2], ("qserver",)) == ["qserver:api.static", "task T20"])

# ---- fakes_only_cross_pipeline (it9 interface F5): an in-package fake across pipelines, by its Boundary line
ev_sec = {"id": "evaluate.evaluate", "fields": {"Boundary": "train, reference, lab", "Used by": "train, reference, lab; PL-01, PL-02, PL-03"}}
pls5 = [pipe("PL-01", [step("train", "train.loop")], package="rllab"), pipe("PL-03", [step("evaluate", "evaluate.protocol")], package="rllab")]
case("fakes_only_cross_pipeline", True, "it9 rl inc: evaluate.evaluate has a Boundary line and PL-01 uses PL-03's step",
     d.boundary_fake_ok("evaluate.evaluate", ev_sec, pls5, "PL-01", ("rllab",)))
rt_sec = {"id": "train.run_train", "fields": {"Boundary": "PL-03", "Used by": "train.run_batch; PL-02, PL-03"}}
pls5e = [{"id": "PL-02", "package": "rllab", "entry": "src/rllab/train/pipelines/pl02_train.py::run_train", "steps": []},
         {"id": "PL-03", "package": "rllab", "entry": "src/rllab/train/pipelines/pl03_batch.py::run_batch", "steps": [step("run_parallel", "train.batch")]}]
case("fakes_only_cross_pipeline", True, "it9 rl aao: PL-02's entry train.run_train, faked for PL-03",
     d.boundary_fake_ok("train.run_train", rt_sec, pls5e, "PL-03", ("rllab",)))
case("fakes_only_cross_pipeline", False, "...but not for a consumer its Used by doesn't name",
     not d.boundary_fake_ok("train.run_train", rt_sec, pls5e, "PL-07", ("rllab",)))
case("fakes_only_cross_pipeline", False, "no Boundary line: a within-package helper stays a type and a sample",
     not d.boundary_fake_ok("evaluate.evaluate", {"id": "evaluate.evaluate", "fields": {"Used by": "PL-01, PL-03"}}, pls5, "PL-01", ("rllab",)))
case("fakes_only_cross_pipeline", False, "a Used by naming only the owner's pipeline is no cross-pipeline call",
     not d.boundary_fake_ok("evaluate.evaluate", {"id": "evaluate.evaluate", "fields": {"Boundary": "lab", "Used by": "PL-03"}}, pls5, "PL-03", ("rllab",)))

# ---- edges_mitigated, unmitigated_reasoned (it9 interface F6): a system task swaps in the real provider
pls6 = {"PL-11": {"id": "PL-11", "package": "data", "entry": "packages/data/src/qrp_data/pipelines/pl11_returns_panel.py::returns_panel", "steps": []},
        "PL-12": {"id": "PL-12", "package": "data", "entry": "packages/data/src/qrp_data/pipelines/pl12_membership.py::membership_as_of", "steps": []},
        "PL-13": {"id": "PL-13", "package": "data", "entry": "packages/data/src/qrp_data/pipelines/pl13_x.py::other", "steps": []}}
s47 = dict(task("T47", "system", "PL-01", reads=["PL-01", "PL-10", "data.returns_panel"], read_symbols=["data.returns_panel"]),
           verify=["uv run pytest tests/intent/data/test_pl12_smoke.py -q"])
w31 = task("T31", "wiring", "PL-11", ["packages/data/src/qrp_data/pipelines/pl11_returns_panel.py", "tests/intent/data/test_pl11_smoke.py"])
w32 = task("T32", "wiring", "PL-12", ["packages/data/src/qrp_data/pipelines/pl12_membership.py", "tests/intent/data/test_pl12_smoke.py"])
w33 = task("T33", "wiring", "PL-13", ["packages/data/src/qrp_data/pipelines/pl13_x.py", "tests/intent/data/test_pl13_smoke.py"])
case("edges_mitigated", True, "it9 quant aao: T47 reads data.returns_panel, PL-11's entry, so its row to wire PL-11 swaps it in",
     d.swaps_in(s47, w31, pls6) and "PL-11" in d.wired_pipelines(s47, pls6))
case("edges_mitigated", True, "...and its Verify runs PL-12's smoke test", d.swaps_in(s47, w32, pls6))
case("edges_mitigated", False, "a pipeline it neither reads nor runs is no swap", not d.swaps_in(s47, w33, pls6))
case("edges_mitigated", False, "wiring → wiring is never a swap", not d.swaps_in(w31, w32, pls6))
T6 = {"T47": s47, "T31": w31, "T33": w33}
case("unmitigated_reasoned", True, "the swap row `call · none: system task swaps in the real provider` is integration",
     d.unmitigated_class(row("T47", "T31", "call", "system task swaps in the real provider"), T6, {}, pls6)[0] == "integration")
case("unmitigated_reasoned", False, "...a call row to a pipeline it doesn't run has no allowed structure",
     d.unmitigated_class(row("T47", "T33", "call", "system task swaps in the real provider"), T6, {}, pls6) == ("", "no allowed structure"))

# ---- unmitigated_reasoned (it9 interface F1): no thicken waits on wiring or system, whatever the row's kind
T1 = {**T, "T29": task("T29", "wiring", "PL-01", ["src/quant/data/pipeline.py", "tests/intent/conftest.py"]),
      "T37": task("T37", "thicken", "PL-01.apply_universe", ["src/quant/data/universe_rules.py"], mode="split")}
for r_, k in [(row("T37", "T29", "order", "TC-23's store is built by the real download (conftest.py)"), "wiring"),
              (row("T37", "T14", "order", "golden cases need the real chain"), "system"),
              (row("T37", "T29", "file", "both write conftest.py"), "wiring")]:
    case("unmitigated_reasoned", False, f"it9 quant aao F1: thicken → {k} `{r_['kind']}` '{r_['reason']}'",
         d.unmitigated_class(r_, T1, info) == ("", f"a thicken task waits on a {k} task"))
case("unmitigated_reasoned", True, "a thicken waiting on its own step's spine is still same module",
     d.unmitigated_class(row("T37", "T03", "code", "extends it"), T1, info)[0] == "same module")

# ---- skills_invoked, test_planning_invoked (it9 interface F7): the driver's `/dev-team:<skill>` sessions
st9 = [{"turn": 1, "user": "/dev-team:idea-refine I want an RL lab", "skills": [], "session": {"new": True, "skill": "idea-refine"}},
       {"turn": 2, "user": "Approved.", "skills": [], "session": {"new": False, "skill": "idea-refine"}},
       {"turn": 3, "user": "/dev-team:spec-writing From the previous session: …", "skills": [], "session": {"new": True, "skill": "spec-writing"}},
       {"turn": 4, "user": "Approved.", "skills": [], "session": {"new": True, "skill": "test-planning", "slash": False}}]
sm = d.turn_skill_map(st9)
case("skills_invoked", True, "a session opened with /dev-team:<skill> worked in that skill, with no Skill call",
     sm[1] == {"idea-refine"} and sm[3] == {"spec-writing"})
case("skills_invoked", False, "a turn with no slash opening, Skill call, dt status or skill read is no skill's", sm[2] == set())
case("skills_invoked", False, "a new session the driver opened without the slash prefix loads nothing by itself", sm[4] == set())
seq = d.turn_skill_seq([{"turn": 5, "user": "/dev-team:api-probe go", "skills": ["dev-team:pipeline-design"]}],
                       [{"turn": 5, "name": "Bash", "input": {"command": "python3 dt.py status --skill api-probe"}},
                        {"turn": 5, "name": "Skill", "input": {"skill": "dev-team:pipeline-design"}}])
case("skills_invoked", True, "the per-turn order: the slash skill, then each call's", seq[5] == ["api-probe", "api-probe", "pipeline-design"])

# ---- types_in_contract (it9 interface F8, J4): whole contract text, mirror forms, qualified library types, notes
with tempfile.TemporaryDirectory() as tmp:
    (pathlib.Path(tmp) / "docs").mkdir()
    (pathlib.Path(tmp) / "docs" / "contract.md").write_text('# Contract\n\n`Direction = Literal["higher", "lower"]`, `Settings = Mapping[str, float]` are used throughout.\n\n## core\n')
    ctext = d.contract_text(tmp, [{"id": "core.TeamSpec", "doc": "docs/contract.md", "text": "`class TeamSpec: direction: Direction`"}])
case("types_in_contract", True, "it9 rl aao: an alias in the contract's preamble resolves", d.defined_in("Direction", ctext) and d.defined_in("Settings", ctext))
case("types_in_contract", False, "...a type the preamble doesn't define doesn't", not d.defined_in("Budget", ctext))
mq = ("- **Invariants:** `CompanyMsg` mirrors `qdata.query.Company`; `ActionMsg` mirrors one `qdata.query.Actions` row\n"
      "- **Invariants:** mirrors `qdata.xcheck.Comparison`, `DayDiffMsg` mirroring `DayDiff` (EXPL-06)\n"
      "- `CheckCountsMsg` mirrors `CheckCounts` plus `check: str`; `ScoreMsg` mirrors `Scorecard`\n"
      "- **Invariants:** `DayDiff(day: date, primary: float, action: str | None)` per day")
case("types_in_contract", True, "it9 quant inc: deep mirror paths, 'mirrors one … row', 'mirroring', a bare name with a section or inline",
     all(d.defined_in(n, mq, {"CheckCounts"}) for n in ("CompanyMsg", "ActionMsg", "DayDiffMsg", "CheckCountsMsg")))
case("types_in_contract", False, "a bare mirror target with no section and no inline definition defines nothing",
     not d.defined_in("ScoreMsg", mq, {"CheckCounts"}))
mods = d.contract_modules(("qdata", "explorer"), [{"id": "pages.RouteView"}, {"id": "store.VersionedStore"}])
ft = d.field_types("`type RouteView = { title: string; element: JSX.Element }`\n"
                   "`def open(self, version: VersionId | None) -> duckdb.DuckDBPyConnection`\n"
                   "`def company(self) -> qdata.query.Company`\n`class Bar: value: float | NaN; staged: StagedRun`", mods)
case("types_in_contract", True, "it9 quant inc/aao: JSX.Element, duckdb.DuckDBPyConnection and NaN aren't contract types",
     not {"Element", "DuckDBPyConnection", "NaN"} & set(ft))
case("types_in_contract", False, "...but a contract-qualified type and an undefined one stay to resolve (StagedRun is real)",
     {"Company", "StagedRun", "VersionId"} <= set(ft))
note = ("- `BarSchema`: index `date`; `open, high, close, ret: float64` (NaN where missing). `ActionSchema`: `date, kind: Literal[\"split\"], value: float`\n"
        "- `VendorRowSchema`: `table: str; key: str; values: str  # JSON`\n- `FlagRow`: `ticker, date`")
case("types_in_contract", True, "it9 quant aao: a backticked note with typed fields defines its type",
     all(d.defined_in(n, note) for n in ("BarSchema", "ActionSchema", "VendorRowSchema")))
case("types_in_contract", False, "a backticked note listing bare field names defines nothing", not d.defined_in("FlagRow", note))

# ---- gate_discipline (it9 interface F10): routed fixes the user approved, then one drafted layer
p12 = {"assistant": "The two routed fixes would then come before build-planning: the TRAIN-03 count in the spec, and AD-09's corridor in the architecture."}
u13 = "Approved. Set the plan to Approved. Then make the two routed fixes (the TRAIN-03 count and AD-09's corridor) and continue."
case("gate_discipline", True, "it9 rl aao turn 13: 16 architecture lines of approved routed fixes, then the M1 plan",
     d.routed_fixes({"arch", "plan"}, {"arch": 16, "plan": 432}, p12, u13))
case("gate_discipline", False, "an architecture change over 25 lines is a redesign, not a routed fix",
     not d.routed_fixes({"arch", "plan"}, {"arch": 60, "plan": 432}, p12, u13))
case("gate_discipline", False, "no user message telling the agent to make them",
     not d.routed_fixes({"arch", "plan"}, {"arch": 16, "plan": 432}, p12, "Approved. Continue to the next planning step."))
case("gate_discipline", False, "the turn before named no routed fix",
     not d.routed_fixes({"arch", "plan"}, {"arch": 16, "plan": 432}, {"assistant": "Plan drafted."}, u13))
case("gate_discipline", False, "three layers are never one routed fix",
     not d.routed_fixes({"arch", "spec", "plan"}, {"arch": 16, "spec": 14, "plan": 432}, p12, u13))

# ---- writes_disjoint (it9 interface F9 nit): a Step cell naming two steps
case("writes_disjoint", True, "it9 quant aao T02: `PL-09.open_run, PL-09.close_run` names both steps",
     d.step_ids("PL-09.open_run, PL-09.close_run") == ["PL-09.open_run", "PL-09.close_run"])
case("writes_disjoint", False, "...and its owner's spine writing runs/events.py beside runs/record.py is still flagged",
     d.spine_writes_problem(["packages/data/src/qrp_data/runs/record.py", "packages/data/src/qrp_data/runs/events.py",
                             "tests/unit/data/test_runs.py"], "runs.record", ("data",)))

# ---- probe_code_in_probe_turns (it9 flow §6): writes before the turn leaves api-probe stay api-probe's
import probegrade  # noqa: E402
t8 = [{"name": "Write", "input": {"file_path": "/w/project/probes/PB-03-yahoo/yahoo_http.py"}},
      {"name": "Bash", "input": {"command": "cd probes/PB-03-yahoo && python3 - <<'EOF'\np=pathlib.Path(\"public.py\")\nEOF"}},
      {"name": "Skill", "input": {"skill": "dev-team:pipeline-design"}},
      {"name": "Bash", "input": {"command": "python3 dt.py status --skill pipeline-design"}}]
case("probe_code_in_probe_turns", True, "it9 quant inc turn 8: the approved PB-03 Revise, then pipeline-design",
     probegrade.written_before_switch(t8, "probes/PB-03-yahoo/yahoo_http.py") and probegrade.written_before_switch(t8, "probes/PB-03-yahoo/public.py"))
case("probe_code_in_probe_turns", False, "a probe file written after the turn moved to pipeline-design",
     not probegrade.written_before_switch(t8 + [{"name": "Edit", "input": {"file_path": "/w/project/probes/PB-03-yahoo/probe.py"}}],
                                          "probes/PB-03-yahoo/probe.py"))
case("probe_code_in_probe_turns", False, "a probe file no call names can't be placed", not probegrade.written_before_switch(t8, "probes/PB-03-yahoo/other.py"))

# ---- crosscheck_facts_reached_design (it9 flow §6): n/a when nobody named the cross-check
case("crosscheck_facts_reached_design", True, "it9 quant aao: no user message or doc names Yahoo (EXCH calendar 'cross-checked' is no source)",
     not d.crosscheck_named(["Plan my quant lab on Sharadar."], ["| Trading calendar | exchange_calendars, cross-checked with SEP dates |"]))
case("crosscheck_facts_reached_design", False, "a user who names yahooquery makes the check apply",
     d.crosscheck_named(["I cross-check against Yahoo with yahooquery."], []))

# ---- data_sources_suggested (it9 flow §6): a fundamentals source only in a sentence about fundamentals
f, fund = d.data_sources({"docs/architecture.md": "AD-05: sector history from SEC EDGAR annual-report headers (SIC codes). "
                          "Fundamentals stay out of scope (spec.md Out of scope)."})
case("data_sources_suggested", False, "it9 quant aao: EDGAR for SIC codes is no fundamentals source", "SEC EDGAR / XBRL" in f and not fund)
f, fund = d.data_sources({"docs/architecture.md": "| Fundamentals | SEC EDGAR company facts, later | AD-09 |"})
case("data_sources_suggested", True, "EDGAR in a table row about fundamentals counts", fund == ["SEC EDGAR / XBRL"])

# ---- planexport.turn_skills (it9 R10): the skill at the end of each turn, not the last Skill call carried forward
import planexport  # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    rdir = pathlib.Path(tmp)
    tt = [{"turn": 1, "user": "/dev-team:idea-refine go", "skills": [], "tools": [], "session": {"id": "s1", "new": True, "skill": "idea-refine"}},
          {"turn": 2, "user": "Approved.", "skills": [], "tools": ["Bash"], "session": {"id": "s1"}},
          {"turn": 3, "user": "Approved.", "skills": [], "tools": [], "session": {"id": "s1"}},
          {"turn": 4, "user": "Approved.", "skills": [], "tools": [], "session": {"id": "s2", "new": True, "skill": "build-planning", "slash": False}}]
    (rdir / "turns.json").write_text(json.dumps(tt))
    (rdir / "agent_stream.jsonl").write_text("\n".join(json.dumps(x) for x in [
        {"type": "driver_turn", "turn": 1}, {"type": "driver_turn", "turn": 2},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "python3 dt.py status --skill build-planning"}}]}},
        {"type": "driver_turn", "turn": 3}, {"type": "driver_turn", "turn": 4}]) + "\n")
    ps = planexport.turn_skills(rdir)
case("planexport_turn_skills", True, "it9 R10: a long session's turn running `dt status --skill build-planning` is build-planning's",
     ps[1] == "idea-refine" and ps[2] == "build-planning" and ps[3] == "build-planning")
case("planexport_turn_skills", False, "a new session that shows no skill doesn't inherit the last session's", ps[4] == "")


# ==== iteration 10 (results-iteration-10/findings.md, "Harness: grader") ==========================================

# ---- spec_classical (it10 G1): "risk-parity" is risk parity
case("spec_classical", True, "it10 quant inc: 'minimum-variance' and 'The risk-parity rule' (PORT-11)",
     d.spec_classical("PORT-10 The minimum-variance rule … PORT-11 The risk-parity rule picks the weights …"))
case("spec_classical", True, "the spaced form still matches", d.spec_classical("min variance and risk parity portfolios"))
case("spec_classical", False, "min-variance alone is not both", not d.spec_classical("PORT-10 The minimum-variance rule; PORT-12 HRP"))

# ---- probe_not_guess (it10 G2): a suggestion for a later stage is no data-source decision of this stage
ad11 = {"title": "Suggested fundamentals source for a later stage: Sharadar Core US Fundamentals",
        "text": "### AD-11: Suggested fundamentals source for a later stage: Sharadar Core US Fundamentals\n"
                "**Status:** Accepted · **Date:** 2026-10-18 · **Scope:** later stage\n- **Decision:** Suggest SF1."}
case("probe_not_guess", True, "it10 quant inc AD-11: '**Scope:** later stage' and its heading say later stage", d.later_stage_decision(ad11))
case("probe_not_guess", True, "the Scope line alone is enough",
     d.later_stage_decision({"title": "Sharadar SF1 for fundamentals", "text": "**Status:** Accepted · **Scope:** a later stage (S3)"}))
case("probe_not_guess", False, "the stage's own source decision still counts, so it must cite a probe",
     not d.later_stage_decision({"title": "Sharadar SEP is the price source", "text": "**Status:** Proposed · **Scope:** `eqdata`\n"
                                 "- **Consequences:** a later stage can add fundamentals from the same vendor."}))

# ---- sim_ready_3 (it10 G3): the wiring replay holds a spine its wiring waits on, never a call step's
import simulate  # noqa: E402
lab_pl = pipe("PL-01", [step("fit_learner", "lab.fit", "Config → Agent"), step("train_dqn", "dqn.train_dqn", "Config → Agent")],
              package="lab", entry="packages/lab/src/rllab/lab/pipeline.py")
t10 = [task("M1-T01", "interface"), task("M1-T05", "spine", "PL-01.fit_learner"), task("M1-T14", "spine", "PL-01.train_dqn"),
       task("M1-T19", "wiring", "PL-01", ["packages/lab/src/rllab/lab/pipeline.py", "tests/unit/lab/test_pl01_smoke.py"])]
w, own = simulate.wiring_spines(t10, [lab_pl], ("lab", "dqn"))
case("sim_ready_3", True, "it10 rl aao: M1-T14 builds PL-01.train_dqn in package dqn, which lab's wiring M1-T19 fakes: not held",
     w and w["id"] == "M1-T19" and own == ["M1-T05"])
w, own = simulate.wiring_spines(t10, [pipe("PL-01", lab_pl["steps"], package="lab")], ("lab",))
case("sim_ready_3", False, "a step of the pipeline's own package is still one the wiring waits on", own == ["M1-T05", "M1-T14"])

# ---- phase0_split, wave_width (it10 G4): steps the Deferred list names by ID
cell = ("SYNC-04 (to M2), PL-07.raise_finding (to M2: findings land with validation), PL-09.useReport, PL-09.ReportView "
        "(to M3: runs and the report), PL-07.latest_day (to M4: only the study calls it).")
case("phase0_split", True, "it10 quant inc: named steps read from the Deferred cell, the sentence's full stop left off",
     d.named_steps(cell) == ["PL-07.raise_finding", "PL-09.useReport", "PL-09.ReportView", "PL-07.latest_day"])
pl07 = pipe("PL-07", [step("total_returns", "returns.series", "Universe → Returns", covers=["RET-01", "RET-07"]),
                      step("raise_finding", "findings", "Returns → Finding", covers=["RET-07"]),
                      step("latest_day", "returns.latest", "Store → TradingDay", covers=["DATA-05"]),
                      step("daily_bars", "returns.bars", "Ids → BarFrame", covers=["DATA-05"])],
            package="eqdata", entry="e/pl07.py")
pl09 = pipe("PL-09", [step("useStock", "api.queries", "Id → Stock", covers=["VIEW-01"]),
                      step("useReport", "api.queries", "Id → Report", covers=["VIEW-09"])], package="web", entry="w/pl09.ts")
tq = [task("M1-T01", "interface"), task("M1-T11", "spine", "PL-07.total_returns"), task("M1-T19", "spine", "PL-09.useStock"),
      task("M1-T26", "wiring", "PL-07", ["e/pl07.py", "tests/unit/test_pl07.py"]), task("M1-T27", "wiring", "PL-09", ["w/pl09.ts", "tests/pl09.test.ts"])]
dq = ["SYNC-04"] + d.named_steps(cell)
names10 = {"Universe", "Returns", "Store", "Ids", "Id", "Stock"}
o10 = d.outside_milestone([pl07, pl09], tq, dq, names10, ("eqdata", "web"))
case("phase0_split", True, "it10 quant inc: PL-07.raise_finding, PL-07.latest_day and PL-09.useReport are Deferred by name",
     {k for k, v in o10.items() if v == "Deferred by name"} == {"PL-07.raise_finding", "PL-07.latest_day", "PL-09.useReport"})
m10 = d.phase0_misses([pl07, pl09], tq, {"M1-T01"}, names10, ("eqdata", "web"), o10)
case("phase0_split", True, "...so useReport's Report and raise_finding's Finding aren't asked of the interface, though api.queries is built",
     not any("Report" in m or "Finding" in m or "raise_finding" in m or "latest_day" in m for m in m10))
case("phase0_split", False, "PL-07.daily_bars, neither spined nor Deferred, is still missing with its BarFrame",
     m10 == ["PL-07: interface lacks ['BarFrame']", "PL-07.daily_bars: 0 spine tasks"])
case("phase0_split", False, "with dt's pipeline-ID reading of the cell (`PL-07`), the old misses come back",
     "PL-09: interface lacks ['Report']" in d.phase0_misses([pl07, pl09], tq, {"M1-T01"}, names10, ("eqdata", "web"),
                                                            d.outside_milestone([pl07, pl09], tq, ["SYNC-04", "PL-07", "PL-09"], names10, ("eqdata", "web"))))
case("phase0_split", False, "a step Deferred by name that a task's Step cell names is this milestone's",
     "PL-07.latest_day" not in d.outside_milestone([pl07], tq + [task("M1-T12", "spine", "PL-07.latest_day")], dq, names10, ("eqdata",)))

# ---- runner_split (it10 G5, kept): the agent runs no probe.py, not even a copy against its own fake (api-probe new.md §5)
case("runner_split", False, "it10 quant aao turn 9: a scratchpad copy of PB-03's probe.py run against the agent's fake with a dummy key",
     pf.runs_user_script(bash("S=/private/tmp/x/scratchpad; cd $S/t/PB-03-sharadar-sp500 && export SHARADAR_BASE_URL=http://127.0.0.1:8765/v1.0 "
                              "SHARADAR_API_KEY=k3y-for-tests; python3 probe.py sp500")))
case("runner_split", True, "the agent's own public.py, run with an empty environment, is allowed",
     not pf.runs_user_script(bash('env -i PATH="$PATH" uv run -q probes/PB-02-yahoo-crosscheck/public.py public')))

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
