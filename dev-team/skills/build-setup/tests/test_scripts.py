"""Run the build-setup templates for real on a tiny project.

    python3 -m unittest discover -s skills/build-setup/tests -v

Needs uv and jq (and network on the first run, for `uv sync` and pip-audit). Each class
builds its project once in a temp dir; each test starts from the committed skeleton.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import project
from project import commit, reset, sh, write

HAVE_TOOLS = bool(shutil.which("uv") and shutil.which("jq") and shutil.which("git"))


def check(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return sh(root, "bash", "scripts/check.sh", *args, check=False)


def hook(root: Path, script: str, payload: object, *args: str, env: dict[str, str] | None = None,
         cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a hook script the way Claude Code does: JSON on stdin, from some other directory."""
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    full_env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root), **(env or {})}
    full_env.pop("VIRTUAL_ENV", None)
    return subprocess.run(
        ["bash", str(root / "scripts/hooks" / script), *args], input=stdin, text=True,
        capture_output=True, cwd=cwd or Path(tempfile.gettempdir()), env=full_env, check=False,
    )


def edit_input(root: Path, rel: str, cwd: Path | None = None) -> dict[str, object]:
    return {"tool_name": "Edit", "cwd": str(cwd or root), "tool_input": {"file_path": f"{root}/{rel}"}}


def append(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


@unittest.skipUnless(HAVE_TOOLS, "needs uv, jq and git")
class SingleProject(unittest.TestCase):
    root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name).resolve() / "proj"
        cls.root.mkdir()
        project.make_single(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def setUp(self) -> None:
        reset(self.root)

    # ------------------------------------------------------------------ check.sh modes
    def test_modes_pass_on_clean_project(self) -> None:
        for mode in ("collect", "gate"):
            with self.subTest(mode=mode):
                result = check(self.root, mode)
                self.assertEqual(result.returncode, 0, result.stderr[-2000:])

    def test_full_passes(self) -> None:
        result = check(self.root, "full")
        failed = [line for line in result.stderr.splitlines() if line.startswith("FAILED:")]
        offline = failed == ["FAILED: pip-audit --skip-editable"]
        if offline:
            self.skipTest("pip-audit could not reach its database (offline)")
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])
        self.assertIn("pyright", result.stderr)  # full runs the other type checker
        self.assertIn("Required test coverage of 80.0% reached", result.stdout)

    def test_fast_fixes_and_reports(self) -> None:
        write(self.root, "src/tinyq/data/extra.py", '"""Extra."""\nimport os\n\n\ndef f() -> int:\n    return 1\n')
        result = check(self.root, "fast", str(self.root / "src/tinyq/data/extra.py"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("import os", (self.root / "src/tinyq/data/extra.py").read_text())
        write(self.root, "src/tinyq/data/bad.py", '"""Bad."""\n\n\ndef f(s: str) -> object:\n    return eval(s)\n')
        result = check(self.root, "fast", "src/tinyq/data/bad.py")
        self.assertEqual(result.returncode, 1)
        self.assertIn("S307", result.stdout + result.stderr)
        self.assertEqual(check(self.root, "fast", "README.md").returncode, 0)

    def test_gate_catches_layer_violation(self) -> None:
        append(self.root, "src/tinyq/data/prices.py", "\nfrom tinyq.stats import moments  # noqa: E402\n")
        result = check(self.root, "gate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAILED: lint-imports", result.stderr)
        self.assertIn("FAILED: bash scripts/floor_guard.sh", result.stderr)  # the noqa

    def test_protected_list_is_printed(self) -> None:
        # tests/contracts/** stands for the contract folders at the base: none yet.
        result = check(self.root, "protected")
        self.assertEqual(result.stdout.split(), [g for g in project.PROTECTED if g != "tests/contracts/**"])

    # ------------------------------------------------------------- frozen contracts (CR-09)
    def test_interface_task_writes_a_new_contract_then_it_is_frozen(self) -> None:
        r = self.root
        schema = "tests/contracts/feed.quotes/schema.json"
        write(r, schema, "{}\n")  # the interface task, before its commit: a folder new since the base
        self.assertEqual(hook(r, "path_guard.sh", edit_input(r, schema), "deny", "--protected").returncode, 0)
        result = check(r, "gate")
        self.assertNotIn("protected files changed", result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])

        commit(r, "interface task")  # the next task's base: frozen from here
        self.assertIn("tests/contracts/feed.quotes/**", check(r, "protected").stdout.split())
        result = hook(r, "path_guard.sh", edit_input(r, schema), "deny", "--protected")
        self.assertEqual(result.returncode, 2)
        self.assertIn("frozen boundary contract (CR-09)", result.stderr)
        new_contract = "tests/contracts/feed.depth/schema.json"
        self.assertEqual(hook(r, "path_guard.sh", edit_input(r, new_contract), "deny", "--protected").returncode, 0)
        routes = {
            "edited": lambda: append(r, schema, "\n"),
            "new file": lambda: write(r, "tests/contracts/feed.quotes/case_2.json", "{}\n"),
            "deleted": lambda: (r / schema).unlink(),
        }
        for name, change in routes.items():
            with self.subTest(route=name):
                sh(r, "git", "checkout", "-q", "--", ".")
                sh(r, "git", "clean", "-q", "-fd", "tests/contracts")
                change()
                result = check(r, "gate")
                self.assertEqual(result.returncode, 1, name)
                self.assertIn("FAILED: protected files changed", result.stderr)

    def test_tester_may_not_write_a_contract(self) -> None:
        write(self.root, "tests/contracts/feed.quotes/schema.json", "{}\n")
        result = check(self.root, "collect")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAILED: files outside tests/intent changed", result.stderr)

    # ---------------------------------------------------------------------------- --pkg
    def test_pkg_scopes_tests_to_package_and_dependents(self) -> None:
        result = check(self.root, "gate", "--pkg", "data")
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertIn("-> pytest tests/intent/stats tests/unit/data tests/unit/stats", result.stderr)
        result = check(self.root, "gate", "--pkg", "stats")
        self.assertIn("-> pytest tests/intent/stats tests/unit/stats ", result.stderr)
        self.assertNotIn("tests/unit/data", result.stderr)
        result = check(self.root, "gate", "--pkg", "report")  # no tests yet: pytest is skipped
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertNotIn("-> pytest", result.stderr)

    def test_unknown_pkg_is_a_usage_error(self) -> None:
        result = check(self.root, "gate", "--pkg", "nope")
        self.assertEqual(result.returncode, 64)
        self.assertIn("unknown package", result.stderr)

    # -------------------------------------------------------------- protected-path diff
    def test_protected_change_fails_gate_by_every_route(self) -> None:
        intent = "tests/intent/stats/test_mean.py"
        routes = {
            "unstaged": lambda: append(self.root, intent, "\n# weakened\n"),
            "staged": lambda: (append(self.root, intent, "\n# weakened\n"), sh(self.root, "git", "add", "-A")),
            "committed": lambda: (append(self.root, intent, "\n# weakened\n"),
                                  sh(self.root, "git", "commit", "-qam", "x")),
            "untracked fixture": lambda: write(self.root, "tests/fixtures/stats/TC-09/expected.json", "{}"),
            "config": lambda: append(self.root, "pyproject.toml", "\n# x\n"),
        }
        for name, change in routes.items():
            with self.subTest(route=name):
                reset(self.root)
                change()
                result = check(self.root, "gate")
                self.assertEqual(result.returncode, 1, name)
                self.assertIn("FAILED: protected files changed", result.stderr)

    def test_collect_fails_when_tester_touches_source(self) -> None:
        append(self.root, "src/tinyq/data/prices.py", "\n\nX = 1\n")
        result = check(self.root, "collect")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAILED: files outside tests/intent changed", result.stderr)

    def test_collect_fails_without_intent_dir(self) -> None:
        shutil.rmtree(self.root / "tests/intent")
        result = check(self.root, "collect")
        self.assertEqual(result.returncode, 1)
        self.assertIn("tests/intent does not exist", result.stderr)

    # ------------------------------------------- interface stubs (CR-02) and red for the right reason
    STUB = ('"""Spread."""\n\n\ndef spread(raw: list[float]) -> float:\n'
            '    """Max minus min."""\n    raise NotImplementedError("M1-T05")\n')

    def interface(self, todo: str = "- [ ] M1-T05 spread spine (tinyq, XS, solo)\n") -> None:
        """The interface task's work: a step signature whose stub names its spine task."""
        write(self.root, "src/tinyq/stats/spread.py", self.STUB)
        write(self.root, "tasks/todo.md", "# M1: Tiny — Todo\n\n" + todo)

    def test_floor_guard_interface_stubs(self) -> None:
        self.interface()
        result = self.floor()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)  # names an open task
        result = self.floor("--exit")
        self.assertEqual(result.returncode, 1)
        self.assertIn("src/tinyq/stats/spread.py:4: [stub-left]", result.stdout)
        commit(self.root, "interface")  # the stub is no longer in the diff; it is still judged
        write(self.root, "tasks/todo.md", "# M1: Tiny — Todo\n\n- [x] M1-T05 spread spine (tinyq, XS, solo)\n")
        result = self.floor()
        self.assertEqual(result.returncode, 1)
        self.assertIn("[stub-task]", result.stdout)
        self.assertIn("M1-T05, which is not open", result.stdout)
        self.assertEqual(check(self.root, "gate").returncode, 1)

    def test_collect_wants_red_for_the_right_reason(self) -> None:
        head = '"""Intent: spread."""\n\nimport pytest\n\n'
        cases = {
            "stub": (head + "from tinyq.stats.spread import spread\n\n\n@pytest.mark.intent\n"
                     "def test_spread() -> None:\n    assert spread([1.0, 3.0]) == pytest.approx(2.0)\n", 0, ""),
            "attribute": (head + "import tinyq.stats.spread as s\n\n\n@pytest.mark.intent\n"
                          "def test_spread() -> None:\n    assert s.spred([1.0, 3.0]) == pytest.approx(2.0)\n",
                          1, "fails for the wrong reason (call: AttributeError)"),
            "never red": (head + "from tinyq.stats.spread import spread\n\n\n@pytest.mark.intent\n"
                          "def test_spread() -> None:\n    assert callable(spread)\n", 1, "no test is red"),
        }
        for name, (text, want, says) in cases.items():
            with self.subTest(case=name):
                reset(self.root)
                self.interface()
                commit(self.root, "interface")  # the tester's base
                write(self.root, "tests/intent/stats/test_spread.py", text)
                result = check(self.root, "collect")
                self.assertEqual(result.returncode, want, result.stdout[-2000:] + result.stderr[-2000:])
                self.assertIn(says, result.stdout)

    def test_path_guard_writes_holds_the_task_to_its_claim(self) -> None:
        r = self.root
        self.assertEqual(hook(r, "path_guard.sh", edit_input(r, "src/tinyq/x.py"), "writes").returncode, 0)
        write(r, ".claude/.task_writes", "src/tinyq/stats/spread.py\ntests/unit/stats/\n")
        for rel, want in [("src/tinyq/stats/spread.py", 0), ("tests/unit/stats/test_spread.py", 0),
                          ("src/tinyq/stats/types.py", 2), ("tasks/todo.md", 2)]:
            with self.subTest(file=rel):
                result = hook(r, "path_guard.sh", edit_input(r, rel), "writes")
                self.assertEqual(result.returncode, want, result.stderr)
        self.assertIn("this task's Writes:", result.stderr)

    # ------------------------------------------------------------------- floor_guard.sh
    def floor(self, *args: str) -> subprocess.CompletedProcess[str]:
        return sh(self.root, "bash", "scripts/floor_guard.sh", *args, check=False)

    def test_floor_guard_clean_change_passes(self) -> None:
        append(self.root, "src/tinyq/data/prices.py",
               '\n\ndef first_price(raw: list[float]) -> float:\n    """First price."""\n    return raw[0]\n')
        result = self.floor()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_floor_guard_catches_type_ignore(self) -> None:
        append(self.root, "src/tinyq/data/prices.py",
               '\n\ndef count() -> int:\n    """Count."""\n    return "3"  # type: ignore[return-value]\n')
        self.assertEqual(sh(self.root, "uv", "run", "--frozen", "mypy", check=False).returncode, 0,
                         "a used type: ignore passes mypy; only the floor guard catches it")
        result = self.floor()
        self.assertEqual(result.returncode, 1)
        self.assertIn("src/tinyq/data/prices.py:13: [suppression]", result.stdout)
        self.assertEqual(check(self.root, "gate").returncode, 1)

    def test_floor_guard_rules(self) -> None:
        cases = {
            "stub": ("src/tinyq/data/todo.py",
                     '"""Todo."""\n\n\ndef later(x: int) -> int:\n    """Later."""\n    raise NotImplementedError\n'),
            "swallowed-exception": ("src/tinyq/data/quiet.py",
                                    '"""Quiet."""\n\n\ndef run() -> None:\n    """Run."""\n    try:\n'
                                    '        print(1)\n    except Exception:\n        pass\n'),
            "test-without-assertion": ("tests/unit/data/test_empty.py",
                                       '"""Empty."""\n\n\ndef test_nothing() -> None:\n    x = 1\n    del x\n'),
            "test-skipped": ("tests/unit/data/test_skip.py",
                             '"""Skip."""\nimport pytest\n\n\n@pytest.mark.skip(reason="later")\n'
                             "def test_x() -> None:\n    assert True\n"),
            "suppression": ("src/tinyq/data/cov.py",
                            '"""Cov."""\n\n\ndef f() -> int:  # pragma: no cover\n    """F."""\n    return 1\n'),
        }
        for rule, (rel, text) in cases.items():
            with self.subTest(rule=rule):
                reset(self.root)
                write(self.root, rel, text)  # untracked: the guard must still see it
                result = self.floor()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(f"[{rule}]", result.stdout)

    def test_floor_guard_allows_abstract_and_protocol_bodies(self) -> None:
        write(self.root, "src/tinyq/data/source.py",
              '"""Source."""\nfrom abc import ABC, abstractmethod\nfrom typing import Protocol\n\n\n'
              "class Source(ABC):\n    @abstractmethod\n    def load(self) -> list[float]:\n"
              '        """Load."""\n        raise NotImplementedError\n\n\n'
              "class Sink(Protocol):\n    def put(self, x: float) -> None: ...\n")
        result = self.floor()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_floor_guard_test_deleted_and_assertion_removed(self) -> None:
        (self.root / "tests/unit/data/test_prices.py").unlink()
        path = self.root / "tests/unit/stats/test_moments.py"
        path.write_text(path.read_text().replace("    assert mean_price", "    mean_price"))
        result = self.floor()
        self.assertEqual(result.returncode, 1)
        self.assertIn("tests/unit/data/test_prices.py: [test-deleted]", result.stdout)
        self.assertIn("[assertion-removed]", result.stdout)

    def test_floor_guard_never_prints_a_secret(self) -> None:
        key = "AKIA" + "ABCDEFGHIJKLMNOP"
        write(self.root, "src/tinyq/data/keys.py", f'"""Keys."""\n\nKEY = "{key}"\n')
        result = self.floor()
        self.assertEqual(result.returncode, 1)
        self.assertIn("[secret]", result.stdout)
        self.assertNotIn(key, result.stdout + result.stderr)

    def test_floor_guard_catches_loosened_config(self) -> None:
        path = self.root / "pyproject.toml"
        text = path.read_text().replace("max-complexity = 10", "max-complexity = 14")
        text = text.replace('"TRY003",   # long', '"TRY003", "B006",   # long')
        path.write_text(text)
        write(self.root, "src/tinyq/ruff.toml", "line-length = 200\n")
        result = self.floor()
        self.assertEqual(result.returncode, 1)
        self.assertIn("max-complexity: 10 -> 14", result.stdout)
        self.assertIn("tool.ruff.lint.ignore gained ['B006']", result.stdout)
        self.assertIn("src/tinyq/ruff.toml: [bar-loosened]", result.stdout)
        path.write_text(path.read_text().replace("max-complexity = 14", "max-complexity = 8")
                        .replace('"TRY003", "B006",', '"TRY003",'))
        (self.root / "src/tinyq/ruff.toml").unlink()
        self.assertEqual(self.floor().returncode, 0, "tightening is silent")

    def test_floor_guard_honours_exceptions_and_flags_new_rows(self) -> None:
        write(self.root, "tests/unit/data/test_skip.py",
              '"""Skip."""\nimport pytest\n\n\n@pytest.mark.skip(reason="vendor down")\n'
              "def test_x() -> None:\n    assert True\n")
        append(self.root, "CONSTRAINTS.md",
               "| EX-01 | CR-03 | `tests/unit/data/test_skip.py` | vendor API down | @t | 2099-01-01 |\n")
        result = self.floor()
        self.assertNotIn("[test-skipped]", result.stdout)
        self.assertIn("[new-exception] new exception EX-01", result.stdout)
        commit(self.root, "exception approved")  # build-setup Revise, with the user's yes
        self.assertEqual(self.floor().returncode, 0)
        path = self.root / "CONSTRAINTS.md"
        path.write_text(path.read_text().replace("2099-01-01", "2020-01-01"))
        commit(self.root, "expired")
        append(self.root, "tests/unit/data/test_skip.py", "\n\n@pytest.mark.skip\ndef test_y() -> None:\n    assert True\n")
        self.assertIn("[test-skipped]", self.floor().stdout, "an expired exception allows nothing")

    def test_floor_guard_base_and_errors(self) -> None:
        append(self.root, "src/tinyq/data/prices.py", "\n\nX = 1  # type: ignore\n")
        commit(self.root, "sneaky")
        self.assertEqual(self.floor().returncode, 0, "the base moved past it")
        self.assertEqual(self.floor("--base", "HEAD~1").returncode, 1)
        self.assertEqual(self.floor("--base", "no-such-ref").returncode, 2)

    # -------------------------------------------------------------- references (CR-08)
    def test_floor_guard_catches_references_on_the_import_path(self) -> None:
        cases = {
            "from": ("src/tinyq/stats/ref.py", '"""Ref."""\n\nfrom references.market import residualize\n'),
            "import": ("src/tinyq/stats/ref.py", '"""Ref."""\n\nimport os, references.market\n'),
            "import_module": ("src/tinyq/stats/ref.py",
                              '"""Ref."""\nimport importlib\n\nm = importlib.import_module("references.market")\n'),
            "sys.path": ("tests/unit/conftest.py",
                         '"""Paths."""\nimport sys\nfrom pathlib import Path\n\nsys.path.insert(\n'
                         '    0,\n    str(Path(__file__).parents[2] / "references"),\n)\n'),
            "PYTHONPATH": ("run.sh", 'export PYTHONPATH="$PWD/references:$PYTHONPATH"\n'),
        }
        for name, (rel, text) in cases.items():
            with self.subTest(case=name):
                reset(self.root)
                write(self.root, rel, text)
                result = self.floor()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                rule = "references-import" if name in {"from", "import", "import_module"} else "references-path"
                self.assertIn(f"{rel}:", result.stdout)
                self.assertIn(f"[{rule}]", result.stdout)

    def test_floor_guard_references_lookalikes_and_exceptions(self) -> None:
        write(self.root, "src/tinyq/data/references.py", '"""Citations."""\n\nSOURCES = ["references"]\n')
        write(self.root, "src/tinyq/data/cite.py",
              '"""Cite."""\n\nfrom tinyq.data.references import SOURCES\n\nfrom .references import SOURCES as S\n')
        write(self.root, "docs/build.md", "Never set PYTHONPATH to include references/.\n")
        result = self.floor()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        write(self.root, "src/tinyq/stats/ref.py", '"""Ref."""\n\nfrom references.market import residualize\n')
        append(self.root, "CONSTRAINTS.md",
               "| EX-01 | CR-08 | `src/tinyq/stats/ref.py` | spike, removed in M2 | @t | 2099-01-01 |\n")
        commit(self.root, "exception approved")
        self.assertEqual(self.floor("--base", "HEAD~1").stdout.count("[references-import]"), 0,
                         "an Exceptions row allows a CR-08 finding")

    def test_floor_guard_allows_code_copied_from_a_reference(self) -> None:
        # The reference itself is not judged: its noqa and stub are the user's, not the builder's.
        write(self.root, "references/market.py",
              "import numpy as np  # noqa: F401\n\n\ndef residualize(xs, beta):\n"
              "    mean = sum(xs) / len(xs)\n    return [x - beta * mean for x in xs]\n\n\n"
              "def later():\n    pass\n")
        write(self.root, "src/tinyq/stats/residuals.py",
              '"""Residuals, adapted from RF-01."""\n\n\ndef residualize(xs: list[float], beta: float) -> list[float]:\n'
              '    """Subtract beta times the mean from each value."""\n'
              "    mean = sum(xs) / len(xs)\n    return [x - beta * mean for x in xs]\n")
        result = self.floor()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_tooling_ignores_references(self) -> None:
        write(self.root, "references/bad.py",
              "import os, sys\nimport torch\ndef f(x):\n  return undefined_name  +1   # teh\n")
        write(self.root, "references/test_bad.py", "def test_fails():\n    assert False\n")
        commit(self.root, "user adds references")  # protected: committed before the task starts
        result = check(self.root, "gate")
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])
        for tool in (["vulture"], ["typos"], ["ruff", "check", "references/bad.py"],
                     ["pytest", ".", "--collect-only", "-q", "--no-cov"]):
            with self.subTest(tool=tool[0]):
                out = sh(self.root, "uv", "run", "--frozen", "--quiet", *tool, check=False)
                self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
                self.assertNotIn("references", out.stdout)

    def test_adding_reference_excludes_is_not_a_loosening(self) -> None:
        path = self.root / "pyproject.toml"
        current = path.read_text()
        # Ruff, mypy, deptry and vulture excludes are the lists the guard watches (CR-07).
        older = re.sub(r'(?m)^(exclude = \["\^?references/"\]|extend_exclude = \["references"\])\n', "",
                       current.replace(', "references"]', "]"))
        self.assertEqual(older.count("references/\"]") + older.count('"references"'), 1)  # typos only
        path.write_text(older)
        commit(self.root, "a bar from before references")
        path.write_text(current)  # Extend adds them back
        result = self.floor()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_the_bar_itself_passes_the_floor_guard(self) -> None:
        """Every skeleton file, as if newly added, is clean (the CR-08 patterns don't match the guard)."""
        files = sh(self.root, "git", "ls-files").stdout
        tmp = Path(self.tmp.name)
        (tmp / "all.txt").write_text(files)
        (tmp / "empty").write_text("")
        result = sh(self.root, "uv", "run", "--frozen", "--quiet", "python", "scripts/floor_guard.py",
                    "--diff", str(tmp / "empty"), "--untracked", str(tmp / "all.txt"),
                    "--old-pyproject", str(tmp / "empty"), check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    # --------------------------------------------------------------------------- hooks
    def test_path_guard(self) -> None:
        r = self.root
        cases = [
            # (args, file, expected exit)
            (["allow", "tests/intent/**"], "tests/intent/stats/test_a.py", 0),
            (["allow", "tests/intent/**"], "src/tinyq/x.py", 2),
            (["allow", "tests/intent/**"], "tests/intent/../../src/x.py", 2),
            (["deny", "--protected"], "tests/intent/stats/test_a.py", 2),
            (["deny", "--protected"], "Tests/Intent/test_a.py", 2),
            (["deny", "--protected"], "tests/fixtures/stats/TC-01/expected.json", 2),
            (["deny", "--protected"], "scripts/check.sh", 2),
            (["deny", "--protected"], ".claude/agents/implementer.md", 2),
            (["deny", "--protected"], "CONSTRAINTS.md", 2),
            (["deny", "--protected"], "uv.lock", 2),
            (["deny", "--protected"], "references/x.py", 2),
            (["deny", "--protected"], "References/notes/a.md", 2),
            (["deny", "--protected"], "src/tinyq/x.py", 0),
            (["deny", "--protected"], "tests/unit/data/test_x.py", 0),
            (["deny", "src/**"], "src/tinyq/data/prices.py", 2),
        ]
        for args, rel, want in cases:
            with self.subTest(args=args, file=rel):
                result = hook(r, "path_guard.sh", edit_input(r, rel), *args)
                self.assertEqual(result.returncode, want, result.stderr)
        # After Claude `cd src`, cwd is a subdirectory: the root is found by walking up.
        result = hook(r, "path_guard.sh", edit_input(r, "pyproject.toml", cwd=r / "src"), "deny", "--protected")
        self.assertEqual(result.returncode, 2)

    def test_path_guard_fails_closed(self) -> None:
        r = self.root
        self.assertEqual(hook(r, "path_guard.sh", "not json", "deny", "--protected").returncode, 2)
        self.assertEqual(hook(r, "path_guard.sh", "not json", "allow", "tests/intent/**").returncode, 2)
        self.assertEqual(hook(r, "path_guard.sh", edit_input(r, "src/x.py"), "bogus").returncode, 2)
        no_path = {"tool_name": "Bash", "cwd": str(r), "tool_input": {"command": "ls"}}
        self.assertEqual(hook(r, "path_guard.sh", no_path, "deny", "--protected").returncode, 0)
        result = hook(r, "path_guard.sh", edit_input(r, "src/x.py"), "deny", "--protected",
                      env={"PATH": path_without("jq")})
        self.assertEqual(result.returncode, 2, "no jq: block")

    def test_path_guard_root_spelled_differently(self) -> None:
        link = Path(tempfile.mkdtemp()) / "alias"
        link.symlink_to(self.root)
        payload = {"cwd": str(self.root), "tool_input": {"file_path": f"{link}/tests/intent/stats/test_a.py"}}
        self.assertEqual(hook(self.root, "path_guard.sh", payload, "allow", "tests/intent/**").returncode, 0)
        self.assertEqual(hook(self.root, "path_guard.sh", payload, "deny", "--protected").returncode, 2)

    def test_post_edit(self) -> None:
        r = self.root
        self.assertEqual(hook(r, "post_edit.sh", edit_input(r, "src/tinyq/data/prices.py")).returncode, 0)
        write(r, "src/tinyq/data/bad.py", '"""Bad."""\n\n\ndef f(s: str) -> object:\n    return eval(s)\n')
        result = hook(r, "post_edit.sh", edit_input(r, "src/tinyq/data/bad.py", cwd=r / "src"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("S307", result.stderr)
        self.assertEqual(hook(r, "post_edit.sh", "garbage").returncode, 1, "reported, not silent")

    def test_stop_gate_blocks_three_times_then_tells_the_user(self) -> None:
        r = self.root
        append(r, "src/tinyq/data/prices.py", "\n\ndef bad(values, factor):\n    return values\n")
        payload = {"cwd": str(r), "agent_id": "agent-1", "session_id": "s1"}
        for attempt in (1, 2, 3):
            result = hook(r, "stop_gate.sh", payload, "gate")
            self.assertEqual(result.returncode, 0)
            answer = json.loads(result.stdout)
            self.assertEqual(answer["decision"], "block")
            self.assertIn(f"attempt {attempt}/3", answer["reason"])
            self.assertIn("FAILED: mypy", answer["reason"])
            self.assertEqual(attempt == 3, "GATE FAILED" in answer["reason"], "the last try says how to report")
        result = hook(r, "stop_gate.sh", payload, "gate")
        self.assertIn("still failing after 3 attempts", json.loads(result.stdout)["systemMessage"])
        self.assertFalse((r / ".claude/.stop_attempts_agent-1").exists())
        again = json.loads(hook(r, "stop_gate.sh", payload, "gate").stdout)
        self.assertIn("attempt 1/3", again["reason"], "the counter starts over")
        other = json.loads(hook(r, "stop_gate.sh", {**payload, "agent_id": "agent-2"}, "gate").stdout)
        self.assertIn("attempt 1/3", other["reason"], "one counter per agent")

    def test_stop_gate_passes_quietly_and_resets(self) -> None:
        r = self.root
        (r / ".claude/.stop_attempts_main").write_text("2")
        result = hook(r, "stop_gate.sh", {"cwd": str(r)}, "gate")
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertFalse((r / ".claude/.stop_attempts_main").exists())

    def test_stop_gate_does_not_fail_open(self) -> None:
        r = self.root
        append(r, "src/tinyq/data/prices.py", "\n\ndef bad(values, factor):\n    return values\n")
        result = hook(r, "stop_gate.sh", "not json at all", "gate", cwd=r / "src")
        self.assertEqual(json.loads(result.stdout)["decision"], "block", "bad input still runs the gate")
        result = hook(r, "stop_gate.sh", {"cwd": str(r)}, "gate", env={"PATH": path_without("jq")})
        self.assertEqual(result.returncode, 2, "no jq: block with exit 2")
        self.assertNotIn("No such file", result.stderr)

    def test_stop_gate_warn_and_check_pkg(self) -> None:
        r = self.root
        append(r, "src/tinyq/data/prices.py", "\n\ndef bad(values, factor):\n    return values\n")
        answer = json.loads(hook(r, "stop_gate.sh", {"cwd": str(r)}, "gate", "--warn").stdout)
        self.assertNotIn("decision", answer)
        self.assertIn("warn only", answer["systemMessage"])
        reset(r)
        (r / ".claude/.check_pkg").write_text("nope\n")
        answer = json.loads(hook(r, "stop_gate.sh", {"cwd": str(r)}, "gate").stdout)
        self.assertIn("unknown package 'nope'", answer["reason"], "the task's package became --pkg")

    def test_stop_gate_collect_for_tester(self) -> None:
        r = self.root
        result = hook(r, "stop_gate.sh", {"cwd": str(r), "agent_id": "t"}, "collect")
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        append(r, "tests/intent/stats/test_mean.py", "\nimport tinyq.nothing_here\n")
        answer = json.loads(hook(r, "stop_gate.sh", {"cwd": str(r), "agent_id": "t"}, "collect").stdout)
        self.assertEqual(answer["decision"], "block")


@unittest.skipUnless(HAVE_TOOLS, "needs uv, jq and git")
class MultiProject(unittest.TestCase):
    root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name).resolve() / "proj"
        cls.root.mkdir()
        project.make_multi(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def setUp(self) -> None:
        reset(self.root)

    def test_gate_and_collect_pass(self) -> None:
        for mode in ("collect", "gate"):
            with self.subTest(mode=mode):
                result = check(self.root, mode)
                self.assertEqual(result.returncode, 0, result.stderr[-3000:])
        self.assertIn("-> deptry packages/qcore", check(self.root, "gate").stderr)

    def test_pkg_runs_dependents(self) -> None:
        result = check(self.root, "gate", "--pkg", "qcore")
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])
        self.assertIn("-> deptry packages/qapp", result.stderr)
        self.assertIn("-> pytest tests/intent/qapp tests/unit/qcore tests/unit/qapp", result.stderr)
        result = check(self.root, "gate", "--pkg", "qapp")
        self.assertNotIn("deptry packages/qcore", result.stderr)
        self.assertNotIn("tests/unit/qcore", result.stderr)

    def test_package_boundaries_and_dependencies(self) -> None:
        write(self.root, "packages/qcore/src/qcore/back.py",
              '"""Back."""\n\nfrom qapp.moments import mean_price\n\n__all__ = ["mean_price"]\n')
        result = check(self.root, "gate")
        self.assertIn("FAILED: deptry packages/qcore", result.stderr)  # qapp is not a qcore dependency
        self.assertIn("FAILED: lint-imports", result.stderr)


class Templates(unittest.TestCase):
    def test_every_placeholder_is_documented(self) -> None:
        """examples.md explains how each value is derived; a new placeholder needs a row."""
        skill = project.TEMPLATES.parent
        used = {m for f in project.TEMPLATES.rglob("*") if f.is_file()
                for m in project.PLACEHOLDER.findall(f.read_text(encoding="utf-8"))}
        documented = (skill / "examples.md").read_text(encoding="utf-8")
        missing = sorted(name for name in used if f"`{name}`" not in documented)
        self.assertEqual(missing, [])

    def test_scripts_are_executable(self) -> None:
        for rel in project.SCRIPTS:
            if rel.endswith(".sh"):
                self.assertTrue(os.access(project.TEMPLATES / rel, os.X_OK), rel)


def path_without(tool: str) -> str:
    """A PATH with every directory's tools except `tool` (symlinked into a temp dir)."""
    shim = Path(tempfile.mkdtemp())
    for directory in os.environ["PATH"].split(os.pathsep):
        if not Path(directory).is_dir():
            continue
        for exe in Path(directory).iterdir():
            target = shim / exe.name
            if exe.name != tool and not target.exists() and os.access(exe, os.X_OK):
                target.symlink_to(exe)
    return str(shim)


if __name__ == "__main__":
    unittest.main()
