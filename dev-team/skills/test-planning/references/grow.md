# Grow: cases move with their pipelines

The package split. Move each TC section to the `tests.md` of the package that now owns its pipeline, `git mv tests/fixtures/<old>/TC-NN tests/fixtures/<new>/TC-NN`, and update its Fixture field. IDs and fixture contents don't change; `git diff -M --stat` should show pure renames. Docs touched go to Draft; then the Review Gate.
