# Shape: single package or multi-package

Read before proposing the shape, and when weighing Grow.

- **Single package** (proof of concept, library, one service, research code): `docs/architecture.md` plus `docs/packages/<pkg>/contract.md`. Components are modules, one subfolder each; decisions live in the one doc. 1-3 pages.
- **Multi-package** (a platform or monorepo of separately installed or deployed packages): a root `docs/architecture.md` system map with dependency rules, System pipelines and every decision (each scoped `system` or a package id), plus `architecture.md` and `contract.md` per package. Root 2-4 pages, each package 1-3.

Choose multi-package only for a real boundary: separate install, versioning or deployment, different runtimes or owners, or a dependency stack the rest shouldn't carry. Size is never one: not a long contract (`dt context` loads only the sections a task reads), not a count of pipelines or modules (components are already folders), and not a dependency direction (import-linter enforces it between components of one package). **A proof of concept is almost always a single package.** Don't build the platform inside it: name the seams that would become packages ("the data loader is behind `DataSource` so it can move out") and stop there.

**The user's shape holds.** Once the user has said which shape they want ("keep it as one package", in `docs/requests.md`) or a decision records it, never recommend another; only the user reopens it. A real boundary that arrives later goes under Risks and open questions, with no recommendation and no question.

## Grow triggers

A single package grows into several when the user asks, or when one of these arrives and no recorded shape says otherwise:

- New requirements bring a dependency stack the rest shouldn't carry (torch, torchvision).
- A part runs or deploys on its own (a day-ahead forecast service), or needs its own install, release or owner.

`grow_triggers` in `dt status` and `dt lint`'s `grow-size` measure size, so neither is a trigger: answer them by trimming the doc or splitting a component's modules, and say so at the gate.
