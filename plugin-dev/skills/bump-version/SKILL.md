---
name: bump-version
description: Release a Claude Code plugin. Decides patch, minor or major from what changed, bumps plugin.json and its marketplace.json row, writes the CHANGELOG entry, tags the commit and pushes. Use only inside a plugin (a directory with .claude-plugin/plugin.json). Never run it unasked. Propose the level in chat and wait for a yes.
---

# Release a plugin

## Ask first

This skill commits, tags and pushes. When a change looks worth a release, name the level you
would pick and why, in a sentence or two, and stop. Touch no file and run no `git` command
for the release until the user says yes.

## The level

The version is `version` in the plugin's `.claude-plugin/plugin.json`. Decide from the diff
since the last tag, not from what the commits say.

| Level | When | Example |
|---|---|---|
| **patch** | Wording or examples change. What a skill or agent reads, writes, invokes and promises its callers does not | tightening a skill's steps |
| **minor** | Something new that existing use can ignore | a new skill, agent or optional flag |
| **major** | Something that worked against the plugin breaks | a renamed skill, a moved file another file reads, a changed document format, a new required input |

The test for major is what breaks, not how large the edit was. A one-word rename of a path
others read is major. A rewritten agent that reads and writes the same files is minor.

Hooks, MCP servers and settings carry their own contracts:

- A new hook is at least minor: it acts in every session the plugin is enabled in. A hook
  that blocks what it used to allow is major.
- A renamed MCP server or tool is major: agents' `tools` lists and users' permission rules
  name it in full.
- A new required `userConfig` field is major.

## The procedure, after a yes

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" {plugin dir}`. Stop on a failure
   other than the version one.
2. Set `version` in the plugin's `plugin.json` and in its row of the root
   `.claude-plugin/marketplace.json`.
3. Add `## [{version}] - {date}` at the top of the plugin's `CHANGELOG.md`, one line per
   change under Added, Changed or Fixed.
4. Run the check again. It holds the manifest, the row and the newest changelog heading to
   the same version.
5. Rebuild the reading site with the `build-site` skill, so its pages show the files this
   release ships; stage any site file git tracks.
6. Commit the three files, the site and any uncommitted change they release:
   `{plugin} {version}`.
7. Tag the commit `{plugin}-v{version}`. One repo holds several plugins, so a bare
   `v{version}` would not say which one moved.
8. `git push --follow-tags`. Report the commit and the tag.

The manifest, the changelog and the tag answer one question together: what is in the copy I
have installed. A release missing any one of them cannot answer it.

## Models

`model: inherit` is the default for every agent, so a plugin follows the session's model
instead of making cost and quality decisions behind the user's back. Set a model on an agent
only when its stakes or workload differ from the session's, and record the agent, the model
and the reason in the plugin's `VERSIONING.md`. Use a full model ID for an agent under
evaluation, since an alias moves and a model change then looks like a prompt regression.

`VERSIONING.md` holds only those decisions and any exception to this policy. The policy
itself is this file.
