# The flow page

`site/flow.md` holds the prose and one marker line where each generated part goes. The
builder fills a marker from the plugin's files and from `flow:` in `site/site.yml`, so the
tables and charts are one set of facts drawn several ways and cannot disagree.

| In `site/flow.md` | Drawn from | Shows |
|---|---|---|
| **Which route**, written by hand | | which command to type for which kind of work, and the workflow page for each |
| `<!-- flow:agents-skills -->` | every agent's `skills:` frontmatter, plus `flow.uses` | roles against skills: ● always, ○ only on a condition, and the conditions |
| `<!-- flow:writes -->` | `flow.documents[].writes` | the roles in one row; above each, the documents only it writes; below the row, the documents several write, an arrow from each writer |
| `<!-- flow:reads -->` | `flow.documents[].reads` | the same chart for reading, the arrows pointing from the document to the role |
| `<!-- flow:documents -->` | `flow.documents` | the table behind both charts: path, written by, read by, and `stale` when given |
| `<!-- flow:drivers -->` | `flow.drivers`, `flow.hooks` | one row per driver: the ledger, the script that prints the next step, what it spawns, what comes back, the ledger's one writer. Then the hooks that hold each driver, and the hooks that act in every session |

A plugin with an agent or a workflow skill needs `site/flow.md`, the `flow:` block and the
`flow` claim below: the check fails without all three, and the build says which is missing.
The build also warns when the block has a part and `flow.md` has no marker for it.

## The `flow:` block

```yaml
flow:
  roles:            # left to right in the charts. Default: every agent, alphabetically.
    - {id: run-thing, note: driver, relays: true}   # an agent or a skill, by name
    - {id: unit-agent, label: unit agent, file: skills/x/references/unit-prompt.md}
                                                    # anything else: a label, and the file that defines it
  uses:             # beyond what an agent's frontmatter preloads
    builder:
      always: [house-style]
      sometimes:
        - security-review: the step touches auth
      names: [scaffold]                             # its file mentions it and does not load it
  documents:
    - name: the design                              # the label in the charts: keep it short
      path: plans/{slug}/design.md
      match: "design.md"                            # optional: how role files name it, if not by path
      writes: [designer]                            # a role, or {role: a note for the table}
      reads: [builder, {reviewer: round 1}]
      names: [run-thing]                            # its file mentions the document and does not touch it
      stale: the plan changed                       # optional column
  drivers:
    - skill: run-thing
      ledger: "`plans/{slug}/ledger.jsonl`"
      next: "`run.py next`"
      spawns: every ready step's agent, in one turn
      returns: "Result: done | question | blocked"
      writer: "`run.py record`"
      writer_in: driver                             # who runs the writer: `agent` (default) or `driver`
      held: "`gate.py` on `SubagentStop`"
  hooks:            # hooks that hold no driver: they act in every session
    - script: on_edit.py
      event: PostToolUse
      does: fails an oversized file back to the model
```

- A name in `writes` or `reads` that is not a role (a script, a hook, the user) appears in
  the documents table as written and in neither chart. The build prints those names, which
  is where a misspelled role shows up.
- `all` means every role, and moves the document from the chart to its caption.
- A document one role writes is drawn above that role, and one several write is drawn
  below the row, so the charts need no layout config.
- A driver with no `spawns` is drawn writing its ledger itself.
- `names`, `match`, `file` and `relays` draw nothing. They exist for the check below.

## What holds the block to the files

The block is written by hand. A `flow` claim in the plugin's `contracts.yml` holds it to
the files:

```yaml
flow:
  - name: the flow page agrees with the files
    file: site/site.yml        # optional; this is the default
```

A role's file is `agents/{id}.md`, `skills/{id}/SKILL.md`, or the `file:` its entry gives.
The claim fails when:

| Part | Fails when |
|---|---|
| roles | an agent is no role |
| skills | a role's file names a model-loadable skill that is in none of its `always`, `sometimes`, `names` or its agent's `skills:` frontmatter, or one of those lists names a skill the file never names |
| documents | a role's file names a document (by `path`, or by a `match` string as written) and the role is in none of its `writes`, `reads` or `names`, or a role listed there never names it |
| drivers | `skill` is no skill, a `x.py` the driver names does not exist, or one named in `next` or `writer` is not named in the driver's skill |
| hooks | a script wired in `hooks/hooks.json` is named in no driver's `held` and no `flow.hooks` entry, or a hook named in either is not wired, or not to the event given |

So a role that starts loading a skill, a document that gains a writer or a reader, or a new
hook fails the next check until the block says so.

- In a `path`, `{x}`, `<x>` and `*` stand for anything without a space.
- `match: false` leaves a document unchecked. Use it for one no role file names.
- `relays: true` is for a driver that hands paths to agents: what its file names beyond
  its own lists is not held against it.
