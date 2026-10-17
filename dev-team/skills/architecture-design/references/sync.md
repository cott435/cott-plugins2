# Sync

Read when `dt status --skill architecture-design` reports Sync: the code and the doc disagree, or there's code with no doc. It ends at the Review Gate in `../SKILL.md`, following `writing-rules.md`.

1. Document what *is* first: components, dependencies, and contracts as built (a component's `__init__` exports are its contract). Components follow `components.md`, contracts `contracts.md`; a missing doc is written from `templates.md`.
2. List each mismatch for the user and ask which way it resolves: update the doc to match the code (record a decision if it was a real choice, as `decisions.md` says), or keep the doc and plan a fix. Never silently rewrite the doc to match code that broke a dependency rule.
