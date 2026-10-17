"""dt guard: the PreToolUse decision for oracle files and the plan archive."""
from __future__ import annotations

import json
import unittest

from dt_helpers import FixtureCopy, run_main


def decision(out: str):
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else None


class GuardTest(unittest.TestCase):
    def hook(self, file_path, cwd="/proj"):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Edit", "cwd": cwd,
                 "tool_input": {"file_path": file_path}}
        return run_main("guard", stdin=json.dumps(event))

    def test_oracle_file_asks(self):
        code, out = self.hook("/proj/tests/fixtures/quant/TC-02/expected.json")
        self.assertEqual((code, decision(out)), (0, "ask"))
        data = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(data["hookEventName"], "PreToolUse")
        self.assertTrue(data["permissionDecisionReason"].startswith("Oracle file: tests/fixtures/quant/TC-02/expected.json"))

    def test_relative_oracle_path_asks(self):
        self.assertEqual(decision(self.hook("tests/fixtures/expected.json")[1]), "ask")

    def test_archive_denies(self):
        code, out = self.hook("/proj/tasks/archive/M1-data-stats.md")
        self.assertEqual((code, decision(out)), (0, "deny"))

    def test_other_paths_pass(self):
        for path in ("/proj/src/quant/stats/cov.py", "/proj/tests/fixtures/quant/TC-02/input.json",
                     "/proj/tasks/plan.md", "/proj/docs/tasks/archive/x.md"):
            self.assertEqual(self.hook(path), (0, ""), path)

    def test_fails_open(self):
        self.assertEqual(run_main("guard", stdin="not json"), (0, ""))
        self.assertEqual(run_main("guard", stdin=json.dumps({"tool_input": {}})), (0, ""))
        self.assertEqual(run_main("guard", stdin=""), (0, ""))

    def test_path_flag(self):
        code, out = run_main("--root", "/proj", "guard", "--path", "tests/fixtures/a/b/expected.json")
        self.assertEqual((code, decision(out)), (0, "ask"))
        self.assertEqual(decision(run_main("--root", "/proj", "guard", "--path", "tasks/archive/M1.md")[1]), "deny")
        self.assertEqual(run_main("--root", "/proj", "guard", "--path", "src/a.py"), (0, ""))


class ContractGuardTest(FixtureCopy):
    """tests/contracts/** is frozen (ask) except while an unticked contract task of the plan covers it (old-style
    plan: `**Step:** contract`, `Files likely`)."""
    legacy = True

    def setUp(self):
        super().setUp()
        self.replace("tasks/plan.md", "**Step:** PL-02 · **Covers:** STAT-04", "**Step:** contract · **Covers:** —")
        self.replace("tasks/plan.md", "**Files likely:** src/quant/stats/pipeline.py,",
                     "**Files likely:** tests/contracts/feed.quotes/fake.py, src/quant/stats/pipeline.py,")

    def decide(self, rel):
        event = {"tool_name": "Write", "cwd": str(self.root / "src"),
                 "tool_input": {"file_path": str(self.root / rel)}}
        return decision(run_main("guard", stdin=json.dumps(event))[1])

    def test_open_contract_task_may_write_its_folders(self):
        self.assertIsNone(self.decide("tests/contracts/stats.estimate_cov/schema.json"))  # in Read:
        self.assertIsNone(self.decide("tests/contracts/feed.quotes/cases/a.json"))         # in Files likely
        self.assertIsNone(self.decide("tests/contracts/conftest.py"))                     # shared support

    def test_folder_no_open_task_covers_asks(self):
        code, out = run_main("--root", str(self.root), "guard", "--path", "tests/contracts/data.load_prices/schema.json")
        self.assertEqual((code, decision(out)), (0, "ask"))
        self.assertIn("Frozen contract: tests/contracts/data.load_prices/schema.json",
                      json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"])

    def test_ticked_contract_task_freezes(self):
        self.replace("tasks/todo.md", "- [ ] M1-T02", "- [x] M1-T02")
        self.assertEqual(self.decide("tests/contracts/stats.estimate_cov/schema.json"), "ask")
        self.assertEqual(self.decide("tests/contracts/conftest.py"), "ask")

    def test_no_plan_asks(self):
        code, out = run_main("--root", "/proj", "guard", "--path", "tests/contracts/a.b/schema.json")
        self.assertEqual((code, decision(out)), (0, "ask"))


class InterfaceGuardTest(FixtureCopy):
    """The interface task (`**Kind:** interface`) opens what its Read: and Writes: claim until it is ticked."""

    def decide(self, rel):
        return decision(run_main("--root", str(self.root), "guard", "--path", rel)[1])

    def test_ticked_interface_task_freezes(self):
        self.assertEqual(self.decide("tests/contracts/stats.Cov/sample.json"), "ask")

    def test_open_interface_task_with_a_contracts_glob(self):
        self.replace("tasks/todo.md", "- [x] M1-T01", "- [ ] M1-T01")
        self.assertIsNone(self.decide("tests/contracts/stats.Cov/sample.json"))
        self.assertIsNone(self.decide("tests/contracts/portfolio.Weights/sample.json"))

    def test_open_interface_task_with_named_folders(self):
        self.replace("tasks/todo.md", "- [x] M1-T01", "- [ ] M1-T01")
        self.replace("tasks/plan.md", "src/quant/stats/report.py, tests/contracts/**",
                     "src/quant/stats/report.py, tests/contracts/stats.Cov/**")
        self.assertIsNone(self.decide("tests/contracts/stats.Cov/sample.json"))             # in Writes:
        self.assertIsNone(self.decide("tests/contracts/data.load_prices/fake.py"))          # in Read:
        self.assertEqual(self.decide("tests/contracts/portfolio.Weights/sample.json"), "ask")


if __name__ == "__main__":
    unittest.main()
