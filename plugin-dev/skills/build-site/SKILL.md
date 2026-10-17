---
name: build-site
description: Build or refresh a plugin's reading site - its README, its goal, a flow page of who uses, writes and reads what, and every agent, skill, script and plan as a browsable page with a generated nav. Use when asked to build, refresh or read a plugin's site, after a change to what a role uses, writes or reads, and when writing a plugin's README, site/flow.md or site/site.yml. Use only inside a plugin (a directory with .claude-plugin/plugin.json).
argument-hint: "[plugin dir] [--build]"
---

# Build the reading site

One builder serves every plugin, so a fix to the nav or a page layout reaches all of them.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build_site.py" {plugin dir} --build
```

The plugin defaults to the current directory. Without `--build` the script writes only the
source tree, `site/docs/`. With it, Sphinx renders HTML into `site/_build/`. To read it:

```
python3 -m http.server --directory site/_build 8000
```

`--build` needs, once per machine: `pip install sphinx myst-parser furo sphinxcontrib-mermaid pyyaml`.

Report the counts the script prints, since a count that drops after an edit means a skill
or agent stopped being found, and every Sphinx warning, each of which names a page and a
line.

## Generated and authored

Generated on every run and gitignored. Never edit these:

- `site/docs/`: the Sphinx source tree.
- `site/_build/`: the HTML.

Authored and committed:

| File | Holds |
|---|---|
| `README.md` | The home page. See **The README** |
| `PURPOSE.md` | The goal page, as agreed with the user. Not edited for the site |
| `site/flow.md` | The map of the plugin. See `references/flow.md` |
| `site/site.yml` | The only config, every key optional: reading orders, the title, the `flow:` block the flow page is drawn from |
| `site/workflows/{skill}.md` | One page per workflow skill: its flow chart, each step explained, where it stops for the user. See `references/workflow-page.md` |
| `site/reference/*.md` | What a reader looks up: the states a run moves through, each record's format, what each hook checks |
| `site/notes/*.md` | Decision records |
| `site/extra.css` | Optional. Without it the builder's own is used |

`templates/README.md`, `templates/site/site.yml` and `templates/site/flow.md` in this plugin
are the starting shapes, and `new-plugin` copies them into every new plugin.

When a change makes an authored page untrue, edit that page in the same change. A change
to what a role uses, writes or reads is a change to the `flow:` block.

## The README

The README is the site's home page and the plugin's page on GitHub. It holds what the
generated pages cannot: what the plugin is for in a paragraph, how its workflows are driven
and why they are built that way, how to install it, and how to build this site. It carries
no table of skills or agents, no walk-through and no reference detail: the site lists the
first from the files, `site/workflows/` holds the second and `site/reference/` the third.

## Pages and links

- **A skill is a page and its `references/` are its children**, nested under it in the
  sidebar. A link written `references/x.md` in a skill resolves to that child.
- **A script is a page**: its module docstring, the `--help` of the script and of each
  subcommand, a table of its public functions, and its source. The help is captured by
  running the script's `main()` in a child process in an empty directory until it reaches
  argparse, so a script that works before it parses arguments cannot write into the plugin.
- **A backticked mention of a script links to its page**, and that page lists what links to
  it under "Referenced by".
- **A plan is a page**: `plans/{slug}/overview.md`. Its design, slices and ledger are left
  out.
- **Relative `.md` links are rewritten** to the generated layout, so a link written for
  GitHub works on the site. One that points at a file the site does not render is left as
  written and Sphinx warns: fix the link or add the page.

## The nav

A fixed shape. A section with nothing in it is left out:

    Start (README, the goal, the flow) -> Workflows -> Reference -> Agents -> Commands ->
    Workflow skills -> Knowledge skills -> Scripts -> Rules and config -> Plans -> Notes

Everything is found from the files, so a new skill, reference, script or plan needs no edit
anywhere. `site.yml` is touched only to put a page earlier than the alphabet would.

A skill is under **Workflow skills** when its frontmatter says
`disable-model-invocation: true`, and under **Knowledge skills** otherwise.

## If it fails

| It prints | Do |
|---|---|
| no .claude-plugin/plugin.json | Pass the plugin's directory as the first argument |
| not installed | Install the packages above. The source tree was still written |
| PyYAML is not installed | `pip install pyyaml`. Needed only when `site/site.yml` exists |
| a Sphinx warning on a page | It names a page under `site/docs/`. The same path in the plugin is the source: fix that |
