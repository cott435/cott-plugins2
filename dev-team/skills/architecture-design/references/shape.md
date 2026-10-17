# Shape: single package or multi-package

Read in New mode before proposing the shape, and when weighing Grow.

- **Single package** (proof of concept, library, one service, research code): `docs/architecture.md` plus `docs/packages/<pkg>/contract.md`. Components are modules, one subfolder each; decisions live in the one doc. 1-3 pages.
- **Multi-package** (a platform or monorepo of separately installed or deployed packages): a root `docs/architecture.md` system map with dependency rules, System pipelines and every decision (each scoped `system` or a package id), plus `architecture.md` and `contract.md` per package. Root 2-4 pages, each package 1-3.

Choose multi-package only for a real boundary: separate install, versioning or deployment, different runtimes or owners, or a dependency direction worth enforcing with tooling. **A proof of concept is almost always a single package.** Don't build the platform inside it: name the seams that would become packages ("the data loader is behind `DataSource` so it can move out") and stop there.
