# Components

Read when adding, changing or documenting components.

- **Each component:** one responsibility in a sentence, the spec IDs it covers, what it depends on.
- **Every live requirement is covered**, `QR-` and `DATA-` included; cross-cutting ones under Cross-cutting concerns.
- **Dependencies point one way.** Two components needing each other are one, or miss an interface.
- **Single package:** one subfolder per component, its `__init__` exporting its contract.
- **Route steps to installed skills.** Each skill on the stage's `**Skills:**` line, and any installed skill owning a step (a hypothesis test, a security review), is named on the component running the step, whose contract takes what the skill needs. Never design a replacement procedure.
