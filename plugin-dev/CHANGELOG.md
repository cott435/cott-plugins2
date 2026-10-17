# Changelog

One entry per tagged release, newest first.

## [1.0.0] - 2026-10-17

### Added
- Protocol rule: a skill is its role, plus one file per mode.
- `check.py` built-in `modes` check: a skill that names modes without a `## Modes` table, a working mode without its own `references/<mode>.md`, or a `SKILL.md` heading holding a mode's process fails. Major under this plugin's VERSIONING exception, because it failed a plugin that passed.

## [0.1.0] - 2026-10-17

- Initial release: the protocol hook, the size, frontmatter, version and contract checks,
  the reading site, `new-plugin` and `bump-version`.
