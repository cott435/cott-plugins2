# Purpose: `plugin-dev`

## Goal

Every plugin in this marketplace is held to the same rules without anyone having to
remember them: an agreed purpose, small definitions, cross-file claims that are checked,
a reading site, and releases that version the manifest, the catalog and the changelog
together. Changing a plugin is cheap because the checks run themselves.

## Who uses it, and when

Anyone in a session that edits a plugin here. Most of it acts on its own through hooks.
They type a command only to start a new plugin.

## What it does

- Starts a plugin from a discussion of its goal, kept before every later session as
  `PURPOSE.md`.
- Limits definition sizes, and checks a plugin's cross-file claims, frontmatter and version.
- Renders a plugin as a reading site: its goal, flow and files.
- Defines how a plugin is released, and waits for a yes.

## Non-goals

- Designing or planning a plugin's workflows.
- Grading behaviour with repeated model runs, or auditing real runs.
- Restating a harness's docs.

## Done well means

A session opened anywhere in the repo knows the plugin's purpose and the rules before its
first edit. An oversized file or a broken claim is reported where it was caused. A release
leaves the manifest, the catalog row, the changelog and the tag in agreement.
