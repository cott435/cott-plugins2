# CLAUDE.md

This repo is a marketplace with each plugin as a subdirectory. Open a session in the plugin
you are changing, or here.

The rules for working on a plugin are not in this file. The `plugin-dev` plugin's
SessionStart hook prints them, with the plugin's `PURPOSE.md`, under the heading
**plugin-dev protocol**. If that heading is not in your context, `plugin-dev@cott-plugins2`
is not installed or is out of date: say so before editing anything, and read
`plugin-dev/protocol.md` and the plugin's `PURPOSE.md` yourself.

Check a plugin with `python3 plugin-dev/scripts/check.py {plugin dir}`. Releases go through
plugin-dev's `bump-version` skill, which runs only after the user agrees to the level.
