# Audit

Read when the user asks for an audit, or at milestone exit. Audit changes nothing.

## Steps

1. Run `bash scripts/floor_guard.sh --base <plan Base>` (it reports a loosened `pyproject.toml`, new config files, removed rules and new exceptions) and `dt status`.
2. Report each loosening since the milestone's Base and whether a build-setup commit recorded the user's yes, plus expired exceptions and config mismatches.
3. Offer Revise for anything to fix.
