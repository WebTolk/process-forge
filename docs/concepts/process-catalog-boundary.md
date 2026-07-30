# Process Catalog Boundary

The core process catalog contains only domain-neutral workflows for resource
management, authoring, initialization, context resolution, orchestration,
supervision, updates, and generic task execution.

Production-grade domain processes retain stable ids and live in official
bundled packs:

- `packs/official/software-development`
- `packs/official/content-workflow`
- `packs/official/verification`

Their manifests declare `origin: official`,
`bundled_with_distribution: true`, and `core_runtime_dependency: false`.
Official processes are available without copying from `examples/`, but only
active packs contribute processes, prompts, knowledge packages, capabilities,
and classifiers to a workplace or project context. The `generic` workplace
profile activates no domain pack.

Examples may demonstrate how to use an official process, but an example process
definition must not shadow an official process id.

Moving a process across this boundary does not transfer ownership of generic
runtime mechanics. Multi-agent orchestration, runtime-driver registration, and
process supervision remain owned by `process-forge-core`.
