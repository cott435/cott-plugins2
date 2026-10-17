# Changelog

One entry per tagged release, newest first.

## [1.2.0] - 2026-10-11

### Changed

- `bump-version` rebuilds the reading site with `build-site` before the release commit, and stages any tracked site file, so the pages match the files the release ships.

## [1.1.0] - 2026-10-11

### Added

- A page per workflow skill, `site/workflows/{skill}.md`: its flow chart, each step explained, why it is built that way and where it stops for the user. `build-site`'s `references/workflow-page.md` has the shape.
- `plugin-dev`'s own four workflow pages, linked from its flow page.

### Changed

- The built-in `flow page` check fails a plugin whose workflow skill has no page.

## [1.0.0] - 2026-10-11

### Changed

- `check.py` has a built-in `flow page` check: a plugin with an agent or a workflow skill fails without `site/flow.md`, a `flow:` block in `site/site.yml` and a `flow` claim in `contracts.yml`. The Stop hook runs it, so a session that edits such a plugin is held until the three exist.
- `build_site.py` prints a `!` line when `site/flow.md` or the `flow:` block is missing, where it drew an empty flow page without a word.

## [0.7.1] - 2026-10-11

### Changed

- `PURPOSE.md` names no person: anyone in a session that edits a plugin here uses it.

## [0.7.0] - 2026-10-11

### Added

- `phases.py record ... design` refuses, for the user to settle, a design that asks a change
  of a file no later phase owns. It refuses, for the agent, a request whose `###` heading
  names no file in backticks and a `## Requests` that is neither `None` nor headings.
- `phase-evaluator` returns `blocked` when a check, a skipped test or a scenario fails for a
  fault in a file another phase owns.

### Changed

- `run-phases` stops whenever `finish` exits `1`, and switches no branch, makes no worktree
  and resolves no merge. It reopens a blocked phase with `answer`.
- `phase-designer` returns a question when the work needs a file built already changed.
- `phase-evaluator` does not count a skipped test as passed, or a driver's sentence as
  holding when the script refuses the command it names.

### Fixed

- A slice carries only the requests to files its phase owns.
- A `## ` line inside a code fence no longer cuts a forwarded request short.

## [0.6.0] - 2026-10-11

### Added

- `build-site` and `scripts/build_site.py`: a plugin's reading site, with its README, its
  goal from `PURPOSE.md`, a flow page, and every agent, skill, script and plan as a page.
- A `flow` claim in `contracts.yml`, which holds the `flow:` block of `site/site.yml` to
  the files of the roles, drivers and hooks it names.
- `templates/site/flow.md` and `templates/site/site.yml`, copied into every new plugin, and
  "How it runs" and "The reading site" sections in the README template.
- `plugin-dev`'s own `site/site.yml` and `site/flow.md`.

### Changed

- `PURPOSE.md`: a reading site is part of the plugin, not a non-goal.
- `new_plugin.py` copies folders under `templates/`.

## [0.5.0] - 2026-10-11

### Changed

- A phase design states only what crosses files: commands and exit codes, file formats,
  agent inputs and statuses, names users type, open decisions. It is at most 2,000 words,
  and the implementer writes each file's content from the approved design.
- A phase depends on another only when it imports or runs that phase's code. `plan-check`
  notes each workflow phase that waits for another, and a plan that is mostly serial.
- An eval after the first judges only the fixes the one before it listed. The earlier
  report is kept as `eval-round{n}.md`.
- The evaluator fails a phase only for a fault something depends on. Other differences are
  notes.
- A run does not start on uncommitted files. Changed files no phase owns are the user's to
  settle: `record` exits 3 and no agent is started again.

## [0.4.0] - 2026-10-11

### Added

- `phases.py start`: creates a plan's branch in its own worktree beside the repository, at
  `{repo}-worktrees/{plugin}_{slug}`, so the checkout a chat started in is never switched.
- `phases.py finish`: confirms a plan is done, and with `--merge` merges its branch into the
  default branch in the main checkout, undoing a merge that does not apply.

### Changed

- `design-plugin` writes the design in the plan's worktree. `plan-phases` and `run-phases`
  run there, and every `phases.py` command but `start` refuses the default branch.
- `run-phases` ends by asking before the merge and naming the command that removes the
  worktree.

## [0.3.0] - 2026-10-11

### Added

- `design-plugin`: an idea to an approved design of a plugin's workflows, with flow charts
  and a hand-off for planning, written to `plans/{slug}/design.md`.
- `plan-phases`: the split into phases, one per workflow, with shared files planned up front
  for a closing unify phase, and the overview with its dependency graph.
- `run-phases`: a thin driver that takes every phase through design, implement and eval,
  side by side where the graph allows.
- `scripts/phases.py`, which owns a plan's checks, slices, ledger and commits, and the
  agents `phase-designer`, `phase-implementer` and `phase-evaluator`.

### Changed

- `PURPOSE.md` takes designing, planning and building a change into scope.
- `check.py --help` prints the limits.

## [0.2.0] - 2026-10-11

### Added

- `plugin-anatomy`: how a plugin is built. Workflow skills the user runs, a thin driver in
  the main chat, sub-agents for the steps, and a script that owns the ledger and the checks,
  with what keeps a workflow portable to Codex, Gemini and Grok and the Claude Code facts a
  design depends on.
- A claim that no script reads a harness's environment.

### Changed

- `PURPOSE.md`, the protocol and `new-plugin` state that a plugin runs one or more
  workflows built that way.

## [0.1.0] - 2026-10-11

- Initial release: `PURPOSE.md` per plugin, word limits on definitions, the check
  (`scripts/check.py`), the hooks that print the protocol and run the check, and the
  `new-plugin`, `check-contracts` and `bump-version` skills.
