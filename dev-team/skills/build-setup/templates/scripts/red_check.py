#!/usr/bin/env python3
"""RED for the right reason: the tester's new intent tests fail on the behaviour, not the wiring.

Called by `scripts/check.sh collect` with the intent test files changed since the task's base.
Runs them once and sorts every test by why it ended:

    right  AssertionError, NotImplementedError (an interface stub, `raise
           NotImplementedError("M1-T05")`) or pytest.fail / pytest.raises' "DID NOT RAISE"
    wrong  anything else: ImportError, AttributeError, NameError, TypeError, a fixture or
           collection error. The test can't reach the behaviour it claims to check.
    passed the code already does this; listed, not a failure

Exits 1 when any test is wrong, or when none is red: a test that can't fail proves nothing.
With no changed test file there is nothing to judge, and it exits 0.
Prints one line per test that is not right, as `nodeid: reason`.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

RIGHT = {"AssertionError", "NotImplementedError", "Failed"}  # Failed: pytest.fail, DID NOT RAISE


def _right(exc: BaseException | None) -> bool:
    return exc is not None and bool({c.__name__ for c in type(exc).__mro__} & RIGHT)


class Recorder:
    """A pytest plugin that keeps how each test ended: right, wrong (with why) or passed."""

    def __init__(self) -> None:
        self.results: dict[str, str] = {}

    def pytest_collectreport(self, report: Any) -> None:
        if report.failed:
            self.results[report.nodeid or "collection"] = "wrong: collection error"

    def pytest_exception_interact(self, node: Any, call: Any, report: Any) -> None:
        if not hasattr(node, "function"):
            return  # a collector: pytest_collectreport has it
        exc = call.excinfo.value if call.excinfo else None
        if call.when == "call" and _right(exc):
            self.results[node.nodeid] = "right"
        else:
            self.results[node.nodeid] = f"wrong: {call.when}: {type(exc).__name__}"

    def pytest_runtest_logreport(self, report: Any) -> None:
        if report.when == "call" and report.passed:
            self.results.setdefault(report.nodeid, "passed")


def main(paths: list[str]) -> int:
    if not paths:
        print("red_check: no intent test changed since the base; nothing to check", file=sys.stderr)
        return 0
    # pytest is a dev dependency, present wherever check.sh runs. Imported by name: deptry audits
    # the product's imports, and this script is the bar's.
    pytest = importlib.import_module("pytest")
    recorder = Recorder()
    pytest.main([*paths, "-q", "--no-header", "--no-cov", "-p", "no:cacheprovider"], [recorder])
    results = recorder.results
    wrong = {n: r for n, r in results.items() if r.startswith("wrong")}
    for nodeid, why in sorted(wrong.items()):
        print(f"{nodeid}: fails for the wrong reason ({why.removeprefix('wrong: ')})")
    for nodeid in sorted(n for n, r in results.items() if r == "passed"):
        print(f"{nodeid}: passes already (not red)")
    if wrong:
        print("red_check: fix the tests above: each must reach the code and fail on its behaviour")
        return 1
    red = sum(r == "right" for r in results.values())
    if not red:
        print("red_check: no test is red; a test that can't fail proves nothing")
        return 1
    print(f"red_check: {red} red for the right reason", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
