# plugin-dev protocol

You are working on a Claude Code plugin's own source. This text is printed by plugin-dev's
SessionStart hook wherever the session opens, so open a session in the plugin's directory
and edit there.

## The purpose comes first

`PURPOSE.md` at the plugin's root is the agreed statement of what the plugin is for. It is
printed below. Hold every change to it: when a request does not serve the goal, or falls
under its non-goals, say so before building. Edit `PURPOSE.md` only when the user agrees the
goal itself has changed.

## Definitions stay small

A skill, agent or reference file states what holds now, in the fewest words that let its
reader act. When you change one:

- Rewrite the passage the change belongs in. Do not append a paragraph beside it.
- Delete what the change makes untrue or redundant in the same edit.
- Write no history: no "previously", "now", "as of", and no note about older versions. The
  changelog holds that.
- State a rule once, in the file that owns it. Other files name that file.
- At the limit, an addition is paid for with a cut, or the detail moves to a `references/`
  file its reader loads only when needed.

Word limits, counted after the frontmatter: {limits}. A description is at most
{description} characters. A file is raised above its limit only in the plugin's
`contracts.yml`, with a reason the user accepted.

## Checks run themselves

Hooks run `scripts/check.py` for you: the size limit after each edit to a plugin file, and
the whole check before you stop in a session that edited one. A failure names a file and
often a line. Fix the file. Do not relax a limit or a claim to make it pass.

## Releases wait for a yes

When a change is worth a release, say which level you would pick (patch, minor or major)
and stop. The `bump-version` skill runs only after the user agrees.

## New plugins are the user's to start

A new plugin starts with `/plugin-dev:new-plugin`, and only the user types it. When a
request is for a plugin that does not exist yet, say so and let them run it.
