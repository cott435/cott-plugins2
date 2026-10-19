"""User requests (design/requests.md): the docs/requests.md parser, `dt request`, the request lint checks,
`requests_open` in `dt status`, `dt next` routing and the SessionStart line, on copies of fixtures/quant (whose
spec and architecture are Approved)."""
from __future__ import annotations

import datetime
import json
import unittest

from dt_helpers import HAS_GIT, QUANT, FixtureCopy, Project, run_dt

from devteam import requests as rq  # noqa: E402
from devteam.commands import lint  # noqa: E402
from devteam.repo import Doc, Repo  # noqa: E402

PATH = "docs/requests.md"
TODAY = datetime.date.today().isoformat()
DOC = """# Quant Lab — User requests

**Last updated:** 2026-10-18

Intro.

- **UR-01** spec · "delisted names stay in until they delist" · idea-refine 2026-10-18 → DATA-02
- **UR-02** architecture · "use Parquet, not CSV" · idea-refine 2026-10-18 → AD-03
- **UR-03** architecture · "Go with A" [storage: A = Parquet, B = SQLite] · architecture-design 2026-10-18
- **UR-04** spec · "one predator" · idea-refine 2026-10-18 → changed: two predators (approved "two is fine (harder)", spec-writing 2026-10-19)
- **UR-05** pipelines · "rebalance monthly" · idea-refine 2026-10-18 → superseded by UR-06
- **UR-06** pipelines · "rebalance weekly" · spec-writing 2026-10-19
"""


def codes(problems, code):
    return [p for p in problems if p.code == code]


class ParserTest(unittest.TestCase):
    def doc(self, text: str = DOC) -> Doc:
        return Doc(QUANT, PATH, text)

    def test_lines(self):
        reqs, bad = rq.parse(self.doc())
        self.assertEqual(bad, [])
        self.assertEqual([r.id for r in reqs], ["UR-01", "UR-02", "UR-03", "UR-04", "UR-05", "UR-06"])
        r1, _, r3, r4, r5, r6 = reqs
        self.assertEqual((r1.owner, r1.words, r1.skill, r1.date, r1.honoured_by, r1.state),
                         ("spec", "delisted names stay in until they delist", "idea-refine", "2026-10-18",
                          ["DATA-02"], "traced"))
        self.assertEqual((r3.about, r3.state), ("storage: A = Parquet, B = SQLite", "open"))
        self.assertEqual((r4.changed, r4.approval, r4.state), ("two predators", "two is fine (harder)", "changed"))
        self.assertEqual((r5.superseded_by, r5.state), ("UR-06", "superseded"))
        self.assertEqual(r6.state, "open")

    def test_words_keep_quotes_and_separators(self):
        text = '- **UR-01** spec · "say "hi" · then stop" · idea-refine 2026-10-18 → DATA-01\n'
        (r,), bad = rq.parse(self.doc(text))
        self.assertEqual((r.words, r.honoured_by, bad), ('say "hi" · then stop', ["DATA-01"], []))

    def test_bad_lines(self):
        text = ('- **UR-01** spec "no separators" idea-refine 2026-10-18\n'
                '- **UR-02** vibes · "x" · idea-refine 2026-10-18\n'
                '- **UR-03** spec · "x" · idea-refine 2026-10-18 → changed: y (no approval)\n'
                '- **UR-04** spec · "x" · idea-refine 2026-10-18 → honoured somewhere\n'
                '```\n- **UR-05** not parsed in a fence\n```\n')
        reqs, bad = rq.parse(self.doc(text))
        self.assertEqual(reqs, [])
        self.assertEqual([b.id for b in bad], ["UR-01", "UR-02", "UR-03", "UR-04"])
        self.assertIn("owner 'vibes'", bad[1].message)

    def test_change_into(self):
        text = ('- **UR-01** spec · "one predator" · idea-refine 2026-10-18 → changed: two predators (approved '
                '"two is fine", spec-writing 2026-10-19; in DATA-01, TC-01)\n')
        (r,), bad = rq.parse(self.doc(text))
        self.assertEqual((bad, r.state, r.changed, r.into, r.changed_by),
                         ([], "changed", "two predators", ["DATA-01", "TC-01"], ("spec-writing", "2026-10-19")))

    def test_numbers(self):
        self.assertEqual([n for n, _, _ in rq.numbers("6 prey, 2 predators and ten pellets; AD-03, S2, 2026-10-18")],
                         ["6", "2", "ten"])
        self.assertEqual(rq.numbers("1) Build the core"), [])
        self.assertEqual(rq.unstated("within 90 minutes", ["under ~1 hour"]), ["90 minutes"])
        self.assertEqual(rq.unstated("under ~1 hour", ["5 runs of one world within 90 minutes"]), ["1 hour"])
        self.assertEqual(rq.unstated("≤ 60 minutes, 5% of 2k", ["under ~1 hour", "0.05 of 2000"]), [])

    def test_definitions(self):
        defs = [d for d in self.doc().definitions()]
        self.assertEqual([(d.id, d.how) for d in defs][:2], [("UR-01", "request"), ("UR-02", "request")])
        self.assertEqual(defs[0].end - defs[0].start, 1)


class Base(FixtureCopy):
    def status(self, skill: str) -> dict:
        return json.loads(self.dt("status", "--json", "--skill", skill)[1])

    def problems(self, code: str):
        return codes(lint.lint(Repo(self.root)), code)

    def requests(self) -> dict:
        return {r.id: r for r in rq.all_requests(Repo(self.root))}


class CommandTest(Base):
    def test_add_creates_the_doc(self):
        code, out, _ = self.dt("request", "add", "spec", '"the tank is circular"', "--skill", "idea-refine")
        self.assertEqual((code, out.strip()), (0, 'UR-01 spec: "the tank is circular"'))
        text = self.read(PATH)
        self.assertTrue(text.startswith(f"# Quant Lab — User requests\n\n**Last updated:** {TODAY}\n"))
        self.assertIn(f'- **UR-01** spec · "the tank is circular" · idea-refine {TODAY}\n', text)
        self.assertEqual(self.dt("next-id", "UR")[1].strip(), "UR-02")
        self.assertEqual(lint.lint(Repo(self.root), {PATH}), [])

    def test_add_appends_with_context(self):
        self.write(PATH, DOC)
        code, out, _ = self.dt("request", "add", "architecture", "Go with B", "--about", "storage [AD-03]",
                               "--skill", "architecture-design")
        self.assertEqual(code, 0)
        r = self.requests()["UR-07"]
        self.assertEqual((r.words, r.about, r.date), ("Go with B", "storage (AD-03)", TODAY))
        self.assertIn(f"**Last updated:** {TODAY}", self.read(PATH))
        self.assertTrue(self.read(PATH).startswith(DOC.split("**Last")[0]))

    def test_add_replaces(self):
        self.write(PATH, DOC)
        code, out, _ = self.dt("request", "add", "pipelines", "rebalance daily", "--skill", "pipeline-design",
                               "--replaces", "UR-06")
        self.assertEqual((code, out.strip()), (0, 'UR-07 pipelines: "rebalance daily" (replaces UR-06)'))
        self.assertEqual(self.requests()["UR-06"].superseded_by, "UR-07")

    def test_add_refuses(self):
        self.write(PATH, DOC)
        self.assertEqual(self.dt("request", "add", "vibes", "x", "--skill", "idea-refine")[0], 2)
        self.assertEqual(self.dt("request", "add", "spec", "x")[0], 2)
        self.assertEqual(self.dt("request", "add", "spec", '""', "--skill", "idea-refine")[0], 2)
        self.assertEqual(self.dt("request", "add", "spec", "x", "--skill", "Idea Refine")[0], 2)
        self.assertEqual(self.dt("request", "add", "spec", "x", "--skill", "s", "--replaces", "UR-99")[0], 2)
        self.assertEqual(self.read(PATH), DOC)

    def test_trace(self):
        self.write(PATH, DOC)
        code, out, _ = self.dt("request", "trace", "UR-03", "AD-01", "AD-03")
        self.assertEqual((code, out.strip()), (0, "UR-03 → AD-01, AD-03"))
        self.assertEqual(self.dt("request", "trace", "UR-01", "DATA-01")[1].strip(), "UR-01 → DATA-02, DATA-01")
        self.assertEqual(self.requests()["UR-03"].words, "Go with A")

    def test_trace_refuses(self):
        self.write(PATH, DOC)
        self.assertEqual(self.dt("request", "trace", "UR-03", "AD-99")[0], 2)          # not defined
        self.assertEqual(self.dt("request", "trace", "UR-03", "DATA-01")[0], 2)        # a spec ID for architecture
        self.assertEqual(self.dt("request", "trace", "UR-04", "DATA-01")[0], 2)        # changed: its record stays
        self.assertEqual(self.dt("request", "trace", "UR-05", "DATA-01")[0], 2)        # superseded
        self.assertEqual(self.read(PATH), DOC)

    def test_trace_to_a_section(self):
        self.write(PATH, DOC + '- **UR-07** spec · "no live trading" · idea-refine 2026-10-19\n'
                   '- **UR-08** brief · "evenings and weekends only" · idea-refine 2026-10-19\n')
        self.assertEqual(self.dt("request", "trace", "UR-07", "§Quality")[1].strip(), "UR-07 → §Quality")
        self.assertEqual(self.dt("request", "trace", "UR-08", "§constraints")[1].strip(), "UR-08 → §constraints")
        self.assertEqual(self.dt("request", "trace", "UR-07", "§Nowhere")[0], 2)
        self.assertEqual(self.dt("request", "trace", "UR-03", "§Quality")[0], 2)      # a spec heading, not architecture
        reqs = self.requests()
        self.assertEqual([rq.is_open(Repo(self.root), reqs[i]) for i in ("UR-07", "UR-08")], [False, False])
        self.assertEqual([p.message.split(" ")[0] for p in self.problems("request-open")], ["UR-03"])

    def test_trace_drops_retired_ids(self):
        self.write(PATH, DOC.replace("→ AD-03", "→ AD-02"))
        self.assertEqual(self.dt("request", "trace", "UR-02", "AD-03")[1].strip(), "UR-02 → AD-03")

    def test_change(self):
        self.write(PATH, DOC)
        code, out, _ = self.dt("request", "change", "UR-03", "SQLite (option B)", "--approved", 'ok, "B" then',
                               "--skill", "architecture-design", "--into", "AD-03")
        self.assertEqual(code, 0)
        r = self.requests()["UR-03"]
        self.assertEqual((r.state, r.changed, r.approval, r.into), ("changed", "SQLite (option B)", 'ok, "B" then',
                                                                    ["AD-03"]))
        self.assertEqual(r.trace, f'changed: SQLite (option B) (approved "ok, "B" then", architecture-design {TODAY}; '
                                  "in AD-03)")
        self.assertEqual(self.dt("request", "change", "UR-03", "x", "--skill", "s", "--into", "AD-03")[0], 2)
        self.assertEqual(self.dt("request", "change", "UR-05", "x", "--approved", "y", "--skill", "s",
                                 "--into", "DATA-01")[0], 2)

    def test_change_needs_into(self):
        self.write(PATH, DOC)
        args = ("request", "change", "UR-03", "SQLite", "--approved", "B", "--skill", "architecture-design")
        self.assertEqual(self.dt(*args)[0], 2)                                    # no --into
        self.assertEqual(self.dt(*args, "--into", "DATA-01")[0], 2)               # no architecture ID
        self.assertEqual(self.dt(*args, "--into", "AD-99")[0], 2)                 # not defined
        self.assertEqual(self.read(PATH), DOC)

    def test_change_covers_what_honoured_it(self):
        self.write(PATH, DOC)
        args = ("request", "change", "UR-02", "CSV", "--approved", "fine, CSV", "--skill", "architecture-design")
        code, _, err = self.dt(*args, "--into", "AD-01")
        self.assertEqual(code, 2)
        self.assertIn("AD-03 honoured the old words", err)
        self.assertEqual(self.dt(*args, "--into", "AD-01", "AD-03")[0], 0)
        self.assertEqual(self.requests()["UR-02"].into, ["AD-01", "AD-03"])

    def test_change_adds_ids(self):
        self.write(PATH, DOC)
        self.dt("request", "change", "UR-03", "SQLite", "--approved", "B", "--skill", "architecture-design",
                "--into", "AD-03")
        self.assertEqual(self.dt("request", "change", "UR-03", "--into", "TC-01")[0], 0)
        r = self.requests()["UR-03"]
        self.assertEqual((r.into, r.approval, r.changed_by), (["AD-03", "TC-01"], "B", ("architecture-design", TODAY)))
        self.assertEqual(self.dt("request", "change", "UR-06", "--into", "TC-01")[0], 2)  # nothing changed yet

    def test_list(self):
        self.write(PATH, DOC)
        out = self.dt("request")[1]
        self.assertIn('UR-03 "Go with A" [storage: A = Parquet, B = SQLite] · architecture · open\n', out)
        self.assertIn('UR-01 "delisted names stay in until they delist" · spec → DATA-02\n', out)
        rows = json.loads(self.dt("request", "--open", "--json")[1])
        self.assertEqual([r["id"] for r in rows], ["UR-03", "UR-06"])
        rows = json.loads(self.dt("request", "--owner", "spec", "--json")[1])
        self.assertEqual([(r["id"], r["state"]) for r in rows], [("UR-01", "traced"), ("UR-04", "changed")])
        self.assertEqual(self.dt("request", "list", "x")[0], 2)


class LintTest(Base):
    def test_clean(self):
        self.write(PATH, DOC.replace(" · architecture-design 2026-10-18\n", " · architecture-design 2026-10-18 → AD-03\n"))
        self.assertEqual([p for p in lint.lint(Repo(self.root)) if p.code.startswith("request")], [])

    def test_open_fails_the_approved_owner_doc(self):
        self.write(PATH, DOC + '- **UR-07** spec · "show the eigenvalues" · spec-writing 2026-10-19\n')
        got = sorted((p.path, p.line, p.message.split(" ")[0]) for p in self.problems("request-open"))
        self.assertEqual(got, [("docs/architecture.md", 3, "UR-03"), ("docs/spec.md", 3, "UR-07")])
        # Pipelines, tests and plan requests are reported by status only; a Draft owner doc is at its gate.
        self.replace("docs/spec.md", "**Status:** Approved", "**Status:** Draft")
        self.assertEqual([p.path for p in self.problems("request-open")], ["docs/architecture.md"])
        self.assertEqual(lint.lint(Repo(self.root), {PATH}), [])

    def test_trace_to_the_wrong_kind_is_open(self):
        self.write(PATH, DOC.replace("→ AD-03", "→ DATA-01"))
        self.assertEqual([p.message for p in self.problems("request-trace")],
                         ["UR-02 (architecture) is traced to no ID defined in architecture, "
                          "package-architecture, contract"])
        self.assertIn("UR-02", " ".join(p.message for p in self.problems("request-open")))

    def test_trace_to_undefined_or_retired(self):
        self.write(PATH, DOC.replace("→ AD-03", "→ AD-99").replace("→ DATA-02", "→ DATA-03")
                   .replace("superseded by UR-06", "superseded by UR-42"))
        msgs = [p.message for p in self.problems("request-trace")]
        self.assertEqual(msgs, ["UR-02 → AD-99: AD-99 is not defined", "UR-05 is superseded by UR-42: no such later request"])
        self.assertEqual([p.line for p in self.problems("retired-ref") if p.path == PATH], [7])  # DATA-03 removed
        self.assertEqual(sorted(p.message.split(" ")[0] for p in self.problems("request-open")),
                         ["UR-01", "UR-02", "UR-03"])

    def test_plan_trace_survives_archive(self):
        # iteration 10 D3: `dt archive` moves the plan's task IDs to tasks/archive/; a trace to them still holds.
        self.write(PATH, DOC.replace(" · architecture-design 2026-10-18\n", " · architecture-design 2026-10-18 → AD-03\n")
                   + '- **UR-07** plan · "build the loader first" · build-planning 2026-10-19 → M1-T01\n')
        self.assertEqual(self.problems("request-trace"), [])
        self.write("tasks/archive/M1-data-stats.md", self.read("tasks/plan.md"))
        self.write("tasks/plan.md", "# Between milestones\n\n**Status:** Between milestones · **Last updated:** "
                   "2026-11-02\n")
        self.assertEqual(self.problems("request-trace"), [])
        self.assertEqual([r.id for r in rq.open_requests(Repo(self.root), "plan")], [])
        self.assertEqual(self.dt("request", "trace", "UR-07", "M1-T02")[0], 0)
        self.assertEqual(self.requests()["UR-07"].honoured_by, ["M1-T01", "M1-T02"])

    def test_trace_to_a_missing_section(self):
        self.write(PATH, DOC.replace("→ DATA-02", "→ §Out of scope"))
        self.assertEqual([p.message for p in self.problems("request-trace")],
                         ["UR-01 → §Out of scope: no such heading in spec"])
        self.assertIn("UR-01", " ".join(p.message for p in self.problems("request-open")))

    def test_format(self):
        self.write(PATH, DOC + '- **UR-07** spec · "x" · idea-refine 2026-10-19 → somewhere\n')
        (p,) = self.problems("request-format")
        self.assertEqual((p.path, p.line), (PATH, 13))

    def test_header_needs_no_status(self):
        self.write(PATH, DOC)
        self.assertEqual([p for p in self.problems("header") if p.path == PATH], [])
        self.write(PATH, DOC.replace("**Last updated:** 2026-10-18\n", ""))
        self.assertEqual([p.path for p in self.problems("header")], [PATH])

    def test_ref(self):
        self.write(PATH, DOC)
        self.replace("docs/architecture.md", "### AD-03: Parquet on local disk\n",
                     "### AD-03: Parquet on local disk\nThe user chose it (UR-03; see also UR-31).\n")
        self.assertEqual([p.message for p in self.problems("request-ref")], [f"UR-31 is not in {PATH}"])

    def test_prefix_reserved(self):
        self.replace("docs/spec.md", "- **STAT-01**", "- **UR-01**")
        self.assertEqual([p.message for p in self.problems("ref-prefix")],
                         [f"UR-01: the UR prefix is reserved for {PATH}"])
        self.assertIn("UR", self.status("spec-writing")["reserved_prefixes"])

    def test_trace_into_undefined(self):
        self.write(PATH, DOC.replace('spec-writing 2026-10-19)', 'spec-writing 2026-10-19; in DATA-01, DATA-09)'))
        self.assertEqual([p.message for p in self.problems("request-trace")],
                         ["UR-04 was changed in DATA-09: DATA-09 is not defined"])

    def test_number(self):
        self.write(PATH, DOC + '- **UR-07** spec · "load 10 years of prices" · idea-refine 2026-10-19 → DATA-01\n'
                   '- **UR-08** architecture · "under 40 s" · idea-refine 2026-10-19 → AD-03\n'
                   '- **UR-09** spec · "five factors" · idea-refine 2026-10-19 → changed: three factors '
                   '(approved "3 is fine", spec-writing 2026-10-19; in STAT-01)\n')
        msgs = [p.message for p in self.problems("request-number")]
        self.assertEqual([m.split(" ")[0] for m in msgs], ["UR-07", "UR-09"])
        self.assertIn("UR-07 says '10', which DATA-01 doesn't state", msgs[0])
        self.assertIn("UR-09 says 'three', which STAT-01 doesn't state", msgs[1])
        self.assertEqual(lint.SEVERITY["request-number"], "W")

    def test_cite(self):
        changed = 'spec-writing 2026-10-19; in DATA-01)'
        self.write(PATH, DOC.replace('spec-writing 2026-10-19)', changed))
        self.replace("docs/architecture.md", "- **Decision:** Parquet via pyarrow.",
                     "- **Decision:** Parquet via pyarrow, monthly as UR-05 asked.")
        self.replace("docs/packages/quant/tests.md", "**Source:** user file `delisted_2018.csv` (given 2026-10-15)",
                     "**Source:** UR-04 and user file `delisted_2018.csv` (given 2026-10-15)")
        msgs = sorted(p.message for p in self.problems("request-cite"))
        self.assertEqual(msgs, ["UR-04 was changed (two predators) in DATA-01, not TC-01: bring TC-01 in line, then "
                                "`dt request change UR-04 --into TC-01`",
                                "UR-05 is superseded by UR-06: follow and cite UR-06"])
        self.write(PATH, DOC.replace('spec-writing 2026-10-19)', 'spec-writing 2026-10-19; in DATA-01, TC-01)'))
        self.assertEqual([p.message[:5] for p in self.problems("request-cite")], ["UR-05"])

    def test_source(self):
        tests = "docs/packages/quant/tests.md"
        self.write(PATH, DOC + '- **UR-07** spec · "the first factor should explain most of it" · '
                   'test-planning 2026-10-19 → STAT-01\n')
        self.replace(tests, "**Source:** generator `one_factor(T=500, N=20, beta=1.0, seed=3)`",
                     "**Source:** UR-07 (the user, 2026-10-19)")
        (p,) = self.problems("request-source")
        self.assertEqual((p.path, p.line), (tests, 21))
        self.assertIn("TC-03: Expected states '40%', which UR-07 doesn't", p.message)
        self.write(PATH, DOC + '- **UR-07** spec · "the first factor explains at least 40%" · '
                   'test-planning 2026-10-19 → STAT-01\n')
        self.assertEqual(self.problems("request-source"), [])
        self.write(PATH, DOC + '- **UR-07** spec · "the first factor should explain most of it" · '
                   'test-planning 2026-10-19 → STAT-01\n')
        self.replace(tests, "**Source:** UR-07 (the user, 2026-10-19)",
                     "**Source:** UR-07, and generator `one_factor(T=500, N=20, beta=1.0, seed=3)`")
        self.assertEqual(self.problems("request-source"), [])                   # derived: its Source says how

    def test_dup(self):
        self.write(PATH, DOC + '- **UR-06** spec · "again" · idea-refine 2026-10-19\n')
        self.assertEqual([p.line for p in self.problems("dup-id")], [13])


@unittest.skipUnless(HAS_GIT, "needs git")
class AppendOnlyTest(unittest.TestCase):
    def setUp(self):
        self.p = Project(git=True)
        self.addCleanup(self.p.cleanup)
        self.p.write(PATH, DOC)
        self.p.commit("requests")

    def edits(self):
        return [p.message for p in lint.lint(Repo(self.p.root)) if p.code == "request-edit"]

    def test_trace_may_change(self):
        run_dt(self.p.root, "request", "trace", "UR-03", "AD-03")
        run_dt(self.p.root, "request", "add", "spec", "new words", "--skill", "spec-writing")
        self.assertEqual(self.edits(), [])

    def test_words_and_deletion(self):
        self.p.edit(PATH, '"Go with A"', '"Go with B"')
        self.p.edit(PATH, '- **UR-06** pipelines · "rebalance weekly" · spec-writing 2026-10-19\n', "")
        msgs = sorted(self.edits())
        self.assertEqual(len(msgs), 2)
        self.assertTrue(msgs[0].startswith("UR-03 changed since HEAD"), msgs)
        self.assertTrue(msgs[1].startswith("UR-06 is gone since HEAD"), msgs)


class StatusNextTest(Base):
    def test_requests_open_per_owner(self):
        self.write(PATH, DOC)
        self.assertEqual(self.status("architecture-design")["requests_open"],
                         ['UR-03 "Go with A" [storage: A = Parquet, B = SQLite]'])
        self.assertEqual(self.status("pipeline-design")["requests_open"], ['UR-06 "rebalance weekly"'])
        self.assertEqual(self.status("spec-writing")["requests_open"], [])
        self.assertEqual(self.status("idea-refine")["requests_open"], [])
        self.assertNotIn("requests_open", self.status("reference-intake"))

    def test_due_architecture_request_revises_and_routes(self):
        self.write(PATH, DOC)
        self.assertEqual(self.status("architecture-design")["mode"], "revise")
        out = json.loads(self.dt("next", "--json")[1])
        self.assertEqual((out["skill"], out["mode"]), ("architecture-design", "revise"))
        self.assertIn('UR-03 "Go with A"', out["reason"])
        self.assertIn("requests: 1 not honoured → architecture-design", self.dt("status", "--summary")[1])

    def test_spec_first(self):
        self.write(PATH, DOC + '- **UR-07** spec · "show the eigenvalues" · spec-writing 2026-10-19\n')
        out = json.loads(self.dt("next", "--json")[1])
        self.assertEqual((out["skill"], out["mode"]), ("spec-writing", "extend"))
        self.assertIn("requests: 2 not honoured → spec-writing, architecture-design", self.dt("status", "--summary")[1])

    def test_nothing_due(self):
        self.write(PATH, DOC.replace(" · architecture-design 2026-10-18\n", " · architecture-design 2026-10-18 → AD-03\n"))
        self.assertNotEqual(self.status("architecture-design")["mode"], "revise")
        self.assertNotIn("requests:", self.dt("status", "--summary")[1])
        self.assertNotIn("not yet honoured", self.dt("next")[1])


if __name__ == "__main__":
    unittest.main()
