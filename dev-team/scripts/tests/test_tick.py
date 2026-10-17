"""dt tick: ticking and unticking a task in todo.md."""
from __future__ import annotations

import unittest

from dt_helpers import Project, run_main


class TickTest(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.addCleanup(self.p.cleanup)

    def tick(self, *args):
        return run_main("--root", str(self.p.root), "tick", *args)

    def test_tick_thicken_task(self):
        before = self.p.read("tasks/todo.md")
        self.assertEqual(self.tick("M1-T10"), (0, "ticked: M1-T10\n"))
        after = self.p.read("tasks/todo.md")
        self.assertIn("- [x] M1-T10 Delisting-aware universe", after)
        self.assertEqual(before.replace("- [ ] M1-T10", "- [x] M1-T10"), after)

    def test_wiring_task_prints_prebuild_clear(self):
        code, out = self.tick("M1-T09")
        self.assertEqual((code, out), (0, "ticked: M1-T09\nnext: dt prebuild-clear PL-02\n"))
        self.assertEqual(self.tick("M1-T05"), (0, "ticked: M1-T05\n"))       # a step spine builds no pipeline

    def test_legacy_spine_task_prints_prebuild_clear(self):
        p = Project(legacy=True)
        self.addCleanup(p.cleanup)
        code, out = run_main("--root", str(p.root), "tick", "M1-T02")
        self.assertEqual((code, out), (0, "ticked: M1-T02\nnext: dt prebuild-clear PL-02\n"))

    def test_undo(self):
        self.assertEqual(self.tick("M1-T01", "--undo"), (0, "unticked: M1-T01\n"))
        self.assertIn("- [ ] M1-T01", self.p.read("tasks/todo.md"))

    def test_already_in_state(self):
        before = self.p.read("tasks/todo.md")
        self.assertEqual(self.tick("M1-T04", "--undo"), (0, "unticked: M1-T04 (already)\n"))
        self.assertEqual(self.p.read("tasks/todo.md"), before)

    def test_crlf_kept(self):
        path = self.p.path("tasks/todo.md")
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.tick("M1-T12")
        data = path.read_bytes()
        self.assertIn(b"- [x] M1-T12 Shrinkage covariance (quant, S, split)\r\n", data)
        self.assertNotIn(b"\r\r", data)

    def test_errors(self):
        self.assertEqual(self.tick("M1-T99")[0], 1)
        self.assertEqual(self.tick("T03")[0], 2)
        self.p.path("tasks/todo.md").unlink()
        self.assertEqual(self.tick("M1-T03")[0], 1)


if __name__ == "__main__":
    unittest.main()
