---
name: new-plugin
description: Start a new Claude Code plugin in this marketplace repo. Opens a discussion of what the plugin is for, writes the agreed goal to its PURPOSE.md as the source of truth, then scaffolds the plugin and registers it in marketplace.json.
argument-hint: "[plugin-name] [what it is for]"
disable-model-invocation: true
---

# Start a new plugin

A plugin starts as an agreed purpose, not as files. `PURPOSE.md` is what every later session
is held to: plugin-dev's SessionStart hook prints it whenever the plugin is worked on. So the
discussion is the work here, and the scaffold is one command at the end.

## 1. Discuss the goal

Start from `$ARGUMENTS` if given. Talk it through with the user until you can fill every
section of `${CLAUDE_PLUGIN_ROOT}/templates/PURPOSE.md`. Ask a few questions at a time, about
what they have not already told you:

- **Goal.** What is true for the user once this plugin exists that is not true today? One or
  two sentences. If it takes more, the plugin is two plugins or the goal is not clear yet.
- **Who uses it, and when.** What they are in the middle of when they reach for it, and what
  they type or expect to happen on its own.
- **What it does.** Each workflow it runs, as outcomes: where a run starts, what it leaves
  behind, where the user is asked. Not a list of skills and agents: those are decided later
  and will change.
- **Non-goals.** What a reasonable person might expect it to do that it will not. Press for
  these. They are what stops the plugin growing sideways.
- **Done well means.** How the user would tell a good run from a bad one.

Push back where an answer is vague, where two goals pull against each other, or where a
non-goal contradicts something under What it does. Say so and settle it now.

Also settle the name (kebab-case; it becomes the directory and the `/name:` prefix) and a
one-line description for the manifest.

## 2. Agree the text

Show the full `PURPOSE.md` in chat, using the template's headings, within the purpose word
limit. Revise until the user says it is right. Do not scaffold before that yes.

## 3. Scaffold

Write the approved text to a temporary file, then run from anywhere inside the marketplace
repo:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/new_plugin.py" {name} --description "{one line}" --purpose {file}
```

It creates `{name}/` with `PURPOSE.md`, the manifest at 0.1.0, `README.md`, `CHANGELOG.md`,
`VERSIONING.md` and an empty `skills/`, and adds the row to the root `marketplace.json`.
Then run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" {name}` and report its result.

## 4. Stop

Do not write skills or agents in this chat unless the user asks. Tell them the plugin exists,
that committing it is theirs to ask for, and that the next session is best opened in
`{name}/`, where the purpose will be in front of whoever builds it.
