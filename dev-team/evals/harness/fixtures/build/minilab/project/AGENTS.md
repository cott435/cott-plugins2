# Minilab

## Docs
- Your task's context: `dt context <M#-T##>`. Read only what it prints.
- Any section by ID: `dt section <ID>...` (e.g. PL-02 TC-05 RISK-02 risk.VolSeries)
- Package docs: `docs/packages/<pkg>/{architecture,contract,pipelines,tests}.md`
- Real layout: `dt layout <pkg>` (planned layouts are gone once the wiring lands)
- Quality bar: CONSTRAINTS.md. Oracle files (tests/fixtures/*/expected.json) need user approval to change.
- Tests: `python -m pytest` from the root; `scripts/check.sh gate` before you finish.
