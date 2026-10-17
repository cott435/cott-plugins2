# The flow

Who does what in `plugin-dev`: which command to type, which file each step writes and
reads, and what the hooks do on their own.

## Which route

| You want to | Type | Page |
|---|---|---|
| Start a plugin from its goal | `/plugin-dev:new-plugin` | [Start a plugin](workflows/new-plugin.md) |
| Check a plugin | nothing: the hooks run the check, or ask for `check-contracts` | |
| Read a plugin as a site | ask for `build-site` | |
| Release a plugin | agree to the level proposed, and `bump-version` runs | |
| Make a small change | nothing: edit the file, and the hooks check it | |

## Agents and skills

<!-- flow:agents-skills -->

## Who writes what

<!-- flow:writes -->

## Who reads what

<!-- flow:reads -->

<!-- flow:documents -->

## How the drivers run

The driver is the main chat following its workflow skill. It holds a conversation with you
and ends on a file you approved.

<!-- flow:drivers -->
