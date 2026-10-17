---
name: check-contracts
description: Check a Claude Code plugin against its size limits, frontmatter rules, version agreement and the cross-file claims in its contracts.yml, reporting PASS or FAIL with file and line. Use when asked to check or verify a plugin, when a plugin-dev hook reports a failure, when adding or changing a claim in contracts.yml, and before proposing a version bump. Use only inside a plugin (a directory with .claude-plugin/plugin.json). Not for API contract tests, type checking or linting.
argument-hint: "[plugin dir]"
---

# Check a plugin

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" {plugin dir} [--quiet]
```

The plugin defaults to the one at or above the current directory. Exit 0 means every check
passed, 1 that one failed. `--quiet` prints failures only. plugin-dev's hooks run the same
script after edits and before a session stops, so run it by hand when asked, or to see the
passes.

A `FAIL` is a finding about the plugin. Fix the file it names. Do not raise a limit or loosen
a claim to make it pass unless the user decides the rule itself is wrong.

## Built in

Every plugin is held to these with nothing declared:

| Check | Fails when |
|---|---|
| purpose | there is no `PURPOSE.md` |
| sizes | a skill, agent, reference, `PURPOSE.md` or `CLAUDE.md` is over its word limit, or a description over its character limit |
| frontmatter | a skill or agent uses a key the platform does not document, an agent uses one plugins ignore (`hooks`, `mcpServers`, `permissionMode`, `initialPrompt`), or a description is missing or holds an XML-style tag |
| version | `plugin.json`, the marketplace row and the newest `CHANGELOG.md` heading disagree |
| flow page | the plugin has an agent or a workflow skill and lacks `site/flow.md`, a `flow:` block in `site/site.yml`, a `flow` claim in `contracts.yml`, or a `site/workflows/{skill}.md` page for a workflow skill |

The limits are `LIMITS` in `check.py`, and that is the only place they are set.

## Declared: `contracts.yml` at the plugin root

Optional. A claim is worth declaring when it is true only because two files agree, and
nothing fails at run time when they stop agreeing.

```yaml
forbid:                 # a pattern that must not appear
  - name: no file tells a repo to keep a scripts/ directory
    pattern: '\bscripts/'            # a regex, matched per line
    files: ['agents/*.md']           # optional; default: every authored file
    unless: ['\[project\.scripts\]'] # optional: regexes that pardon a match
    all_of: ['finalize']             # optional: literals that must also be in scope
    near: 40                         # optional: scope is the match plus 40 characters either
                                     # side, not the whole line

headings:               # a reader names only the `##` headings its owner defines
  - name: the reviewer reads the design by the sections the designer writes
    owner: skills/design/references/template.md
    owner_span: ['## Start', null]   # optional: [start, end] literals; null is end of file
    readers:
      - file: agents/reviewer.md
        cites: ['Decisions', 'Open questions']

names_listed:           # every directory is named in a file, and no other name is
  - name: the README lists every skill
    dirs: 'skills/*'
    file: README.md
    span: ['## Skills', '## Install'] # optional
    form: code                        # `code`: in backticks anywhere. `list`: a bullet per name

flow:                   # the site's flow page agrees with the files it maps
  - name: the flow page agrees with the files
    file: site/site.yml               # optional; this is the default

limits:                 # one file allowed more words than its kind
  - file: skills/style-guide/SKILL.md
    words: 6000
    why: vendored from an upstream guide and not ours to trim
```

Writing claims:

- Patterns are matched one line at a time. Quote a fragment that fits on a line as the file
  wraps it.
- Use `near` with `unless` or `all_of`. Without it one pardoned phrase pardons everything
  else on its line, which is where a real violation is most likely to be written.
- A `headings` cite must appear in its reader, so a cite its reader does not name fails.
- A `flow` claim is declared by every plugin with an agent or a workflow skill.
  The `build-site` skill's `references/flow.md` says what it holds.
- A `limits` entry needs a `why`, and the user's agreement. It is for text the plugin does
  not own, not for a definition that grew.
- A claim nobody has seen fail proves nothing. After adding or changing one, plant the
  defect it exists to catch, watch it fail, and remove the defect.

## What this cannot check

Anything that needs a model: whether a prompt is clear, whether an agent acts on a rule it
reads, whether a description triggers.
