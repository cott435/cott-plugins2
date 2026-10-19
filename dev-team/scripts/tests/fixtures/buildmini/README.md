# buildmini

The smallest project that exercises dev-team's build (design/build-phase.md §12, smoke tests): one package,
`mini`, one pipeline (PL-01, one step), one golden case (TC-01), and an approved M1 plan of four tasks.

| Task | Kind | Mode | Halves | Waits on |
|---|---|---|---|---|
| M1-T01 | interface | solo | `M1-T01.solo` | — |
| (barrier) | checkpoint after M1-T01 | | reviewer `M1-T01.mini` | M1-T01 |
| M1-T02 | spine | solo | `M1-T02.solo` | the barrier |
| M1-T03 | thicken, TC-01 | split | `M1-T03.tester`, `M1-T03.implementer` | tester: the barrier; implementer: its tests and M1-T02 |
| M1-T04 | wiring (runs `dt prebuild-clear PL-01` at land) | solo | `M1-T04.solo` | M1-T02 |
| exit | milestone exit | | reviewer `exit.mini` | every task |

The fixture holds only what exists before the build: the planning docs, `tasks/`, the golden case's files and
`src/mini/__init__.py` (so `uv sync` has a package to install). The interface task writes the rest.

## Make it a live repo

```
python3 scripts/tests/fixtures/buildmini/make_live.py /tmp/buildmini
```

That copies the fixture and, as build-setup New mode would:
1. renders build-setup's templates onto it (`scripts/check.sh` and the hook scripts, CONSTRAINTS.md, the tester,
   implementer and reviewer agent files, `tests/conftest.py`, `.gitignore`, `pyproject.toml`) with
   `skills/build-setup/tests/project.py`, package `mini`, `pkg_scope` `mini) echo "mini"`;
2. `git init -b main`, `uv lock`, `uv sync --frozen`, `ruff format`, and commits the skeleton;
3. marks CONSTRAINTS.md Approved (the user's yes), then `dt base`, committed, so the plan's Base holds the bar.

Needs `git` ≥ 2.40 (`dt land` uses `git merge-tree --merge-base`) and `uv`. Then, in the new repo, install the
dev-team plugin and run the build skill, or drive it by hand:

```
python3 <plugin>/scripts/dt.py build start M1
python3 <plugin>/scripts/dt.py ready --reserve      # rows with one-line prompts
```
