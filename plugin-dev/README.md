# plugin-dev

The protocol every plugin in this repo is built under. `PURPOSE.md` says what it is for.

## How it works

| Part | What it does |
|---|---|
| `protocol.md` | The rules for working on a plugin. One copy, printed into the session by a hook |
| `hooks/session_start.py` | Prints the protocol and the plugin's `PURPOSE.md` when a session opens inside a plugin or at the marketplace root |
| `hooks/on_edit.py` | After an edit to a plugin file, fails the edit back to Claude if the file is over its word limit |
| `hooks/on_stop.py` | Before a session that edited a plugin stops, runs the whole check and reports new failures |
| `scripts/check.py` | The check: purpose, sizes, frontmatter, version, and the claims in `contracts.yml`. The limits are set here |
| `scripts/new_plugin.py` | Scaffolds a plugin from `templates/` and registers it |
| `scripts/build_site.py` | Renders a plugin as a reading site: its README, its goal, its flow page, and every agent, skill, script and plan |
| `skills/` | Workflow skill you type: `new-plugin`. Knowledge: `check-contracts`, `build-site`, and `bump-version` (proposed, then run on your yes) |

The hooks do nothing outside a plugin or a marketplace, and a hook that crashes lets the
session continue.

## Changing a plugin

| You type | In | It leaves |
|---|---|---|
| `/plugin-dev:new-plugin` | the marketplace | a new plugin with its agreed `PURPOSE.md`, registered in `marketplace.json` |

Any other change: edit the file, and the hooks check it. When the change is worth a release,
the level is proposed in chat and `bump-version` runs on your yes.

## Install

```
/plugin marketplace add cott435/cott-plugins2
/plugin install plugin-dev@cott-plugins2
```

`check.py` needs PyYAML only for a plugin that has a `contracts.yml`: `pip install pyyaml`.

## The reading site

The goal, a flow page of which role uses which skill and who writes and reads each file,
and every agent, skill and script as a page. From any plugin's directory:

```
python3 ../plugin-dev/scripts/build_site.py --build
python3 -m http.server --directory site/_build 8000
```

Needs `pip install sphinx myst-parser furo sphinxcontrib-mermaid pyyaml` once per machine.
`site/docs/` and `site/_build/` are generated. `site/site.yml` and `site/flow.md` are
authored, and the `flow` claim in `contracts.yml` holds them to the files.

## Changing it

The installed copy runs the hooks, not this working tree. After changing a hook or a script,
`/plugin marketplace update cott-plugins2` and start a new session to see it act.
