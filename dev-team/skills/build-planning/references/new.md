# New

`dt status` says `new`: no active or archived plan, and the roadmap has stages. Cut every designed stage, plan M1 and its todo, and write the AGENTS.md doc map. Example: `examples-new.md`.

1. **Every stage designed first.** When the stages come from the brief (Source `brief`, planned up front), a stage below Designed stops New: `dt status` reports `blocked`, naming the packages with no Approved `pipelines.md`. Route to `pipeline-design`, or the first upstream skill whose doc isn't Approved.
2. **Grow check, cut the stage, scope the milestone:** `cut.md`. Up front, cut every designed stage, not only the first.
3. **Milestone shape** (interface task, one spine per step, wiring per pipeline, system task, folds): `phase0.md`.
4. **Thicken, route skills and references, build modes, checkpoints, `Writes:`, the dependency graph, write:** `tasks.md`.
5. **The AGENTS.md doc map** (below).
6. Run the Review Gate.

## AGENTS.md doc map

`## Docs` and `## Project skills`, ≤ 25 lines, no script paths (the session-start hook supplies them). Replace only these two sections; leave every other section of the file alone. If the repo has `CLAUDE.md` and no `AGENTS.md`, write them there.

```markdown
## Docs
- Plan with dev-team2's `build-planning`, not agent-skills' `/plan`.
- Your task's context: `dt context <M#-T##>`. Read only what it prints.
- Any section by ID: `dt section <ID>...` (e.g. PL-02 TC-02 STAT-02 AD-03)
- Package docs: `docs/packages/<pkg>/{architecture,contract,pipelines,tests}.md`
- Real layout: `dt layout <pkg>` (planned layouts are gone once the wiring lands)
- Quality bar: CONSTRAINTS.md. Oracle files (tests/fixtures/*/expected.json) need user approval to change.
## Project skills
- data-science — stats steps
```

Use real IDs from the project in the `dt section` example. List each project skill with the steps it's routed to.
