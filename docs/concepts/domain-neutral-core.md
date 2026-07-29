# Domain-Neutral Core

ProcessForge core defines artifact contracts and runtime mechanics for
workplaces, projects, processes, assignments, runs, tasks, iterations,
capability resolution, orchestration, reviews, handoffs, and release evidence.
It does not assume a software, web, documentation, media, legal, or other
subject domain.

## Boundary

Core may contain:

- generic lifecycle and coordination processes
- schemas, templates, registries, policies, and validators
- opaque capability and resource identifiers
- data-driven project classification mechanics

Core must not contain:

- domain knowledge packages or capability defaults
- file-name rules that infer a technology or platform
- domain processes selected by default
- concrete platform contracts activated without project or workplace data

Domain material belongs in an explicitly installed workplace/project package or
under `examples/domain-packs/`. Merely shipping an example does not register or
activate it.

The policy in `policies/core-hardcode-policy.yaml` and the domain-neutral smoke
suite enforce this boundary in the release archive.
