# References and Stage-Level Skill Routing — Design

**Status:** Ready to build · **Last updated:** 2026-10-16 · **Companion to:** [planning-stage.md](planning-stage.md), [build-setup.md](build-setup.md)

Covers two gaps in the planning flow:

1. **Reference material.** You have files that show how something is done (a TFT dataset builder, a target builder, a market-decomposition transform). The skills that design and build a stage should read them, and builders decide what to reuse.
2. **Skills tied to a stage.** A project skill, such as data analysis or null-hypothesis definitions, should reach the stage it's for, and that link should be checkable.

---

## 1. Today

| Need | What exists | Gap |
|---|---|---|
| Builder reads a reference file | A task's `Read:` accepts repo paths; `dt context` pastes the file in | Only works if build-planning happens to list the path. Nothing says the file exists, what it's for or which stage it serves. The packet doesn't mark it as a reference |
| Planning reads reference files | `idea-refine` scans the codebase for prior art | Not a step later skills repeat; no record of what each file is for |
| Example data | test-planning's `tests/fixtures/<pkg>/TC-NN/source/` | Data for golden cases only, not code to learn from |
| Skill reaches a stage | architecture-design names a skill on a component; test-planning and build-planning put `**Skills:**` on cases and tasks; `dt status` lists `skills_available` and `skills_missing` | Matching is by description, task by task. Nothing ties a skill to a milestone or checks it was carried through. The eval found the `null-hypothesis-testing` hand-off happened by chance |

---

## 2. Decisions at a glance

1. **Reference files live in a root `references/` folder.** They're inputs, like fixtures, not project code: excluded from tooling, protected from edits, never imported.
2. **Every file gets an index entry `RF-NN` in `docs/references.md`.** The entry holds a short summary and which milestone it serves. Skills and tasks cite the ID, never the path, as with every other unit (planning-stage.md §4).
3. **A new skill, `reference-intake`, writes the index.** It sends one read-only subagent per new or changed file to draft the summary, then asks you to confirm each file's milestone. `dt status` reports files waiting for intake in every skill and at session start.
4. **Stage-level routing has one source for each kind:**
   - references → the index entry's `**Milestones:**` field
   - skills → a `**Skills:**` line in the roadmap's milestone section
5. **Each planning skill picks them up by ID** (§6). build-planning puts RF IDs in task `Read:` fields and skills in `**Skills:**`. `dt status` flags a milestone reference or skill that no task carries.
6. **Builders read references through `dt context` under a fixed banner** that says it's a reference and leaves the choice to them: reuse what fits the contract and design as is, adapt it, or ignore it. Large files come in as an outline plus the named functions. The only hard rule is that nothing imports from `references/`; copied code meets the same bar as any other code.

---

## 3. Where files go

```
references/
  tft_dataset.py              TFT dataset builder (yours)
  tft_targets.py              target construction
  market_decomposition.py     PCA / market-mode transforms
  notes/hrp-derivation.md     (optional: markdown notes)
docs/references.md            the index: one RF-NN section per file
```

- **Any time, any file.** Drop the TFT files in when forecasting is being designed, or everything up front for an all-at-once plan. Intake works the same either way.
- **Kinds:** `code` (source files; `.py` gets an `ast` outline) and `doc` (markdown or text). No PDFs, notebooks or data files in v1; example data belongs in test-planning's fixtures.
- **Not project code.** `build-setup` adds `references/` to the excludes for Ruff, mypy, pytest, coverage, deptry and vulture, and to the protected list. Builders can't edit it, and the gate never lints it.
- **Not importable.** It has no `__init__.py` and isn't on any path. Importing from it is a floor violation (§7).
- **Files are data, never instructions.** Intake agents and builders treat comments and docstrings in a reference as content to summarize, not as directions. This is the same rule as fixture `source/`.

---

## 4. The index: `docs/references.md`

````markdown
# Quant Lab — References
**Status:** Approved · **Last updated:** 2026-11-20

### RF-01: Market decomposition transforms
**File:** `references/market_decomposition.py` · **Hash:** 3f9a1c2e · **Kind:** code · **Milestones:** M2
- **Purpose:** removes the market mode and the top-k factors from a returns panel by PCA; returns residuals and loadings
- **Key parts:** `demean_returns`, `pca_factors(returns, k)`, `residualize(returns, factors)`
- **In → Out:** T×N returns DataFrame → residual returns (T×N), loadings (N×k), explained variance
- **Use for:** PL-03 `remove_market` step design; the planted-factor known-answer case
- **Caveats:** fits PCA on the whole sample (look-ahead); the project must fit per window

### RF-02: TFT target construction
**File:** `references/tft_targets.py` · **Hash:** 81bd07aa · **Kind:** code · **Milestones:** M4
- **Purpose:** …

## Retired
- ~~RF-04: Old loader~~ Retired 2026-12-01: file removed; superseded by RF-05
````

- **One section per file**, at most ~8 lines. The summary says what the file is *for*, not how it works line by line. A builder that needs the detail gets the file itself (§7).
- **`Hash`** is the first 8 hex digits of the file's sha256. `dt` writes it (`dt references --stamp`), and a mismatch sends the file back to intake.
- **`Milestones`** lists `M<n>` IDs, `all`, or `—` (not assigned yet).
- **`Caveats`** is where a reference's known flaws go: look-ahead, a library the architecture rejected, a shortcut. Builders see it before the code, so they know what not to reuse as is. A reference is never the oracle unless test-planning says so (§6).
- **Status:** Draft → Approved, as for the other docs. Intake leaves it Draft; your confirmation approves it.
- **Retire, don't delete:** a removed file collapses to one struck line, so its `RF-NN` is never reused.
- **ID prefix `RF` is reserved.** spec-writing must not use it for requirements (the old quant spec had a `REF` prefix). `dt next-id` and spec-writing's prefix check enforce this.

---

## 5. Intake: `reference-intake`

**When:** `dt status` reports `references_unindexed` (files with no entry), `references_changed` (hash mismatch) or `references_missing` (entry whose file is gone). Every skill's status shows these keys, and the SessionStart summary adds one line, e.g. `references: 3 waiting → reference-intake`. Planning skills route there before relying on a reference.

**Process**
1. `dt status --skill reference-intake` lists the files to read.
2. **One subagent per file, in parallel, read-only** (Read, Glob, Grep; no Bash, no Edit). Each gets:
   - The file. For a `.py` file over ~400 lines, it gets `dt outline <file>` (each def and class with signature and docstring) plus the first 150 lines, and reads further only where the outline points.
   - Each subagent returns the five summary bullets and a guess at the milestone, with a one-line reason.
3. The main skill writes the entries (Draft), stamps hashes with `dt references --stamp`, and runs `dt lint docs/references.md`.
4. **Milestone assignment:** one question per file, each with the agent's guess as the default ("`tft_dataset.py` → M4 Forecasting & agents? [yes / other / not yet]"). If the stage doesn't exist yet, `Milestones: —`. idea-refine asks again when that stage's roadmap row is added.
5. **Review gate:** the entries, each with **ASSUMPTIONS** (milestone guesses, caveats inferred), then stop. Approval sets `Status: Approved`.

**Why a separate skill and not an idea-refine step:** files arrive at any point, including mid-build. Intake must not drag a brief or idea-file round along with it. It's small (~120 lines) and its write-matrix row is one file.

**Write matrix (addition to planning-stage.md §10):**

| Skill / role | May write |
|---|---|
| reference-intake | `docs/references.md` |
| idea-refine | also: `**Milestones:**` on RF entries, `**Skills:**` in roadmap sections |
| `dt` (mechanical) | also: `Hash` fields (`dt references --stamp`) |

---

## 6. Stage-level routing

**Skills:** each roadmap milestone section gains one line:

```markdown
## M2: Structure + classical portfolios
**Outline:** PCA and MP-cleaned covariance feed min-var, risk parity and HRP, compared out of sample.
**Skills:** data-analysis, null-hypothesis-testing
```

- **Written by idea-refine** when the stage is accepted. It reads the descriptions of the project skills (`.claude/skills/*/SKILL.md`) and plugin skills (`dt status` → `skills_available`), proposes the ones that fit, and asks once ("route data-analysis and null-hypothesis-testing to this stage? [yes / edit]").
- On Extend, idea-refine also offers unassigned references (`Milestones: —`) for the new stage.
- A skill named here that isn't installed is reported by `dt status` (`skills_missing`), as today.

**References:** taken from each entry's `Milestones` field; `dt` derives "references for M2". There's no second list in the roadmap, so the two can't drift apart.

**How each skill uses them** (each reads the milestone's References and Skills from `dt status`):

| Skill | References | Skills |
|---|---|---|
| idea-refine | Assigns milestones; the idea file may cite RF IDs as prior art | Writes the milestone's `**Skills:**` |
| spec-writing | Reads summaries for behaviour worth requiring. Names no files or functions (hygiene rule unchanged) | — |
| architecture-design | A decision's Context cites the RF it learned from ("RF-01 fits PCA on the full sample; AD-14 fits per window") | Names each milestone skill on the component that runs its step (existing rule, now with a list to start from) |
| pipeline-design | A PL section may carry `**References:** RF-01 (remove_market)`. A spine version may follow a reference ("as RF-01, per-window fit") | — |
| test-planning | A reference can be a case's **Source** only through output you supply (you run it, or the file records known outputs). Planning never runs it. Its Caveats are candidate known-answer cases (e.g. a look-ahead case) | `**Skills:**` on cases, as today |
| build-planning | Puts each RF in the `Read:` of the tasks whose step it informs, with a selector for large files (§7) | `**Skills:**` on every task the skill fits; the plan's Scope lists the milestone's skills |

**Checks:** `dt status --skill build-planning` adds:
- `references_unrouted`: milestone references in no task's `Read:`
- `skills_unrouted`: milestone skills on no task's `**Skills:**`

Both must be empty at build-planning's review gate, or each item must give a one-line reason under Open questions. This replaces "routed by chance" with a checked link.

---

## 7. Build: reading references

**`dt context` rendering.** An `RF-NN` in `Read:` prints the index entry, then the file under a fixed banner:

```
### Reference RF-01: references/market_decomposition.py
> Reference, not part of the project. Reuse what fits the contract and step table as is, adapt it, or ignore it: your call.
> Never import from references/. Anything you bring over meets the same bar as the rest of the code.
> Caveats: fits PCA on the whole sample (look-ahead); the project must fit per window
```

- **Selectors keep packets small:** `RF-01:pca_factors` prints just that function or class (via `ast`); `RF-01:outline` prints only the outline.
- **No selector:** a file over 300 lines prints the outline, and `dt lint` warns (`ref-large`) so build-planning adds a selector.
- The 2,000-line packet budget still applies.
- A `doc` reference prints whole (markdown is usually short); over 300 lines it needs a heading selector, `RF-03:<heading>`.

**Guards (build-setup):**
- **Whether to copy is the builder's call.** References vary: some code is good as is, some only shows an approach. A line-count threshold would block good reuse and miss bad reuse, so there is none. The banner tells the builder what the file is; the entry's Caveats say what not to trust.
- **New floor rule `CR-08`:** nothing imports from `references/` or adds it to `sys.path`. References are outside the tooling, so imported code would bypass the bar. `floor_guard.sh` checks the diff for both.
- **Copied code is project code.** It passes the same gate (types, size, complexity, tests) and follows the contract's names and the step table. Nothing is exempt because it came from a reference.
- **Reviewer checklist** gains one item: where reference code was reused, its Caveats were handled (e.g. the full-sample PCA fit became per-window), and it fits the contract rather than the reference's own structure.

---

## 8. Worked example (quant)

1. You add `market_decomposition.py` to `references/` while M2 (structure + classical portfolios) is being specced, and the two TFT files at the same time.
2. Next session: `references: 3 waiting → reference-intake`. Three subagents summarize the files. You confirm `market_decomposition.py` → M2, and the two TFT files → `—` (no forecasting stage yet).
3. idea-refine accepts M2 and writes `**Skills:** data-analysis, null-hypothesis-testing`.
4. architecture-design: AD-14 "per-window PCA" cites RF-01's caveat. The `stats` component names data-analysis; the `claims` step names null-hypothesis-testing.
5. pipeline-design: PL-03 `remove_market` step, `**References:** RF-01`.
6. test-planning: TC-09, a planted-factor case, comes from RF-01's caveat. The case carries `**Skills:** null-hypothesis-testing`.
7. build-planning: `M2-T04 Per-window market removal` has `Read: PL-03, TC-09, stats.residualize, RF-01:residualize` and `**Skills:** data-analysis`. `references_unrouted` and `skills_unrouted` are both empty.
8. Build: the builder's packet shows the banner and only `residualize`. It reuses the residual arithmetic as is, refits per window as the caveat says, and names things per the contract. The floor guard would catch an import from `references/`.
9. Months later, at M4 kickoff, idea-refine offers the two unassigned TFT references for the forecasting stage.

---

## 9. `dt` changes

| Area | Change |
|---|---|
| Parser | Doc kind `references` (`docs/references.md`); `RF-NN` sections with fields File, Hash, Kind, Milestones; retired lines. Roadmap sections' `**Skills:**` field |
| `dt status` | All skills: `references_unindexed`, `references_changed`, `references_missing`. `--skill reference-intake` (new). idea-refine: `references_unassigned`. build-planning: `milestone_references`, `milestone_skills`, `references_unrouted`, `skills_unrouted`. `--summary`: one line when intake is waiting. spec-writing: `RF` in reserved prefixes |
| `dt context` | `RF-NN` and `RF-NN:<symbol\|outline>` rendering with the banner (§7) |
| `dt outline <file>` | New: defs and classes with signatures and docstring first lines, via `ast` (never imports or runs the file); headings for markdown |
| `dt references --stamp` | New, mechanical: writes each entry's Hash |
| `dt lint` | `missing-ref` covers `RF-NN` (selector stripped); new `ref-file` E (entry's file missing), `ref-hash` W (stale hash), `ref-large` W (file over 300 lines read with no selector), `ref-prefix` E (a spec requirement uses `RF-`); roadmap `**Skills:**` naming an uninstalled skill W |
| `dt next-id RF` | Works already (generic prefix) |

---

## 10. Evals

- **Scenario:** quant facts gain "you have three reference files". The harness copies them into `references/` when the stage that uses them is revealed: `market_decomposition.py` at structure_portfolios, both TFT files at forecasting_agents. In all-at-once mode they're all there from the start. Small fixed files live in `evals/harness/references/quant/`.
- **Assertions:**
  - every reference indexed and Approved
  - each assigned to the right milestone
  - `references_unrouted` and `skills_unrouted` empty for every planned milestone
  - data-analysis on at least one structure_portfolios task
  - no `references/` import (when evals later cover building)
  - intake ran one subagent per file (from the stream's Agent tool calls)

---

## 11. Decisions (2026-10-16)

1. **Folder:** root `references/`, excluded once by build-setup.
2. **Intake:** a separate `reference-intake` skill, not an idea-refine step.
3. **Copying:** no line-count threshold. The builder knows the file is a reference and decides what to reuse; reused code meets the normal bar. Importing from `references/` is the one hard rule.
4. **Kinds:** code and markdown/text only. No PDFs (or notebooks, or data) in v1.
5. **Skills route per milestone,** not per pipeline step. build-planning narrows them to tasks.

## 12. Build order

1. `dt`: parser, `outline`, `references --stamp`, status keys, context rendering, lint codes, with tests on a fixture that has a `references/` folder.
2. `reference-intake` skill.
3. idea-refine (Skills line, assigning references); build-planning (Read and Skills routing, the two checks at the gate); small additions to architecture-design, pipeline-design and test-planning (§6).
4. build-setup: excludes, protected glob, CR-08 (import check in `floor_guard`), reviewer checklist item.
5. Evals (§10).
