# Versioning: `plugin-dev`

The policy is this plugin's `bump-version` skill. This file holds only what is true of this
plugin.

## Model decisions

No agents.

## Exceptions

A change to what `scripts/check.py` accepts, to a limit, or to what a hook blocks is major
when it fails a plugin that passed: every plugin in the repo is held to it.
