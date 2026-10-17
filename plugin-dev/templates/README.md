# <name>

<description>

`PURPOSE.md` states what this plugin is for and what it leaves alone.

## How it runs

<Each workflow in a few lines, by the parts every workflow here has: the workflow skill you
type, what the driver holds, the agents it starts and what each returns, the script that
says what is next and checks each step, and the ledger a run picks up from. Then why it is
built that way for this job. No list of skills or agents and no step-by-step: the site has
both.>

## Install

```
/plugin marketplace add cott435/cott-plugins2
/plugin install <name>@cott-plugins2
```

## The reading site

The goal, a flow page of which role uses which skill and who writes and reads each
document, and every agent, skill and script as a page:

```
python3 ../plugin-dev/scripts/build_site.py --build
python3 -m http.server --directory site/_build 8000
```

Needs `pip install sphinx myst-parser furo sphinxcontrib-mermaid pyyaml` once per machine.
`site/docs/` and `site/_build/` are generated. `site/site.yml`, `site/flow.md`,
`site/workflows/` (one page per workflow skill), `site/reference/` and `site/notes/` are
authored.

## Working on it

Install `plugin-dev` and open a session in this directory. Its hooks print the protocol and
this plugin's purpose, and run the checks.
