# Evals

Ad hoc tests run against this plugin's own skills and agents — targeted checks of one
specific behavioral claim: does an agent actually invoke a skill when it should, does a
patched instruction change behavior, does a description trigger correctly.

Each entry is one dated file naming the commit and model it was tested against, and a clean
pass is recorded exactly like a failure.

## Index

| Date | Subject | File | Commit | Verdict |
|---|---|---|---|---|
| 2026-10-17 | `view --flat` and the `audits/issues/` fallback, for plugin-dev; defaults unchanged | [2026-10-17-view-flat-and-issues-fallback.md](2026-10-17-view-flat-and-issues-fallback.md) | `69509e2` | pass |
| 2026-10-17 | The scripts build, query, extract, replay, grade and compare real sessions | [2026-10-17-scripts-mechanical.md](2026-10-17-scripts-mechanical.md) | `2e94e6c` | Holds after fixes |
| 2026-10-17 | Each skill on a real chat and a real dev-team2 eval run | [2026-10-17-skills-on-real-sessions.md](2026-10-17-skills-on-real-sessions.md) | `8dd7264`, `2e94e6c` | Holds after fixes |
