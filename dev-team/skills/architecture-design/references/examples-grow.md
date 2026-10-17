# Architecture Example: Grow

ExecGym's spec gains a recorder that saves live minute bars every trading day. It's a long-running service deployed on its own, so the Extend round's Grow check fires ("a part runs or deploys on its own"). The skill proposes Grow, and after the user agrees writes `AD-06: split ExecGym into packages`, giving that reason. It proposes three packages:
- `data` — the `DataSource` seam named in the original design, now shared by the recorder and the environment
- `execgym` — env, market, impact, reward, and baselines; depends on `data`
- `recorder` — the new service; depends on `data`, never on `execgym`

Component ids become package ids, so existing Covers entries and contract IDs still resolve. Module detail moves to `docs/packages/<package>/architecture.md`. The `## data` group of the old contract moves to `docs/packages/data/contract.md` with its IDs (`data.DataSource`) unchanged; the rest stays in `docs/packages/execgym/contract.md`. In the code, `src/execgym/data/` moves out as a folder. The root becomes the system map, with a System pipeline `PL-NN: Record a trading day` (a new ID from `dt next-id PL`; `recorder` → `data`: `data.write_bars`, a new contract section), and the shape changes to `Multi-package`. No existing pipeline crosses the new boundary. Had one, it would keep its own ID as its owning package's segment, and `pipeline-design` Grow would mark it `**Part of:**` the new system pipeline. The seam named in the proof of concept is exactly where the split happens. After approval the skill points to `pipeline-design` Grow.
