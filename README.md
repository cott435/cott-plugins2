# cott-plugins2

A marketplace and every plugin it lists, each as a subdirectory.

```
cott-plugins2/
├── .claude-plugin/marketplace.json   the catalog: each plugin, its path and its version
├── .claude/settings.json             enables plugin-dev for sessions opened in this repo
├── plugin-dev/                       the rules the others are built under, run by hooks
├── dev-team/                         takes a project from idea to an enforced build plan
└── workflow-analyzer/                draws, questions and replays what a session did
```

## Use it

```
/plugin marketplace add cott435/cott-plugins2
/plugin install plugin-dev@cott-plugins2
/plugin install dev-team@cott-plugins2
/plugin install workflow-analyzer@cott-plugins2
```

After a `git pull`, `/plugin marketplace update cott-plugins2` picks up the change.

## Working on a plugin

Open a session in the plugin's own directory, such as `dev-team/`. The repo's
`.claude/settings.json` turns plugin-dev on here and the older `cott-plugins` copies off.
plugin-dev's hooks then print the rules and that plugin's `PURPOSE.md` when the session
starts, check a definition's size after each edit, and run the whole check before the
session stops. Its skills act on the plugin at or above the session's directory:

| Skill | Does |
|---|---|
| `check-contracts` | Purpose, sizes, frontmatter, version agreement and the claims in `contracts.yml` |
| `build-site` | Renders the plugin as a reading site |
| `bump-version` | Releases the plugin: manifest, catalog row, changelog, tag. Runs only on your yes |
| `/plugin-dev:new-plugin` | Starts a new plugin here from an agreed purpose |

Each plugin keeps `PURPOSE.md`, `CHANGELOG.md`, `VERSIONING.md` and `contracts.yml` at its
root. A tag is `{plugin}-v{version}`.
