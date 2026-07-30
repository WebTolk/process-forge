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

Domain-neutral does not mean that the distribution is empty. Production-grade
domain workflows may ship under `packs/official/` as versioned data packs.
Those packs are available from the distribution, but they are not runtime
dependencies and are not active in a generic workplace. Workspace, project,
and custom resources remain separate extension layers.

`examples/` contains tutorials and fixtures. It is not the canonical source for
an official process. This is similar to bundled Joomla extensions: an official
pack is useful out of the box and demonstrates the extension architecture,
while the kernel remains independent of its domain rules.

The policy in `policies/core-hardcode-policy.yaml` and the domain-neutral smoke
suite enforce this boundary in the release archive.
