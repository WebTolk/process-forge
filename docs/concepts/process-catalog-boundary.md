# Process Catalog Boundary

The core process catalog contains only domain-neutral workflows for resource
management, authoring, initialization, context resolution, orchestration,
supervision, updates, and generic task execution.

Domain processes retain stable ids but live in optional example packs:

- `examples/domain-packs/software-web`
- `examples/domain-packs/content-workflow`
- `examples/domain-packs/verification-workflow`

They are marked `optional_example`, are not installed by workplace init, and do
not appear in the default process catalog. A workplace or project may import a
pack explicitly and then register its processes, prompts, knowledge packages,
capabilities, and classifiers through normal resource data.

Moving a process across this boundary does not transfer ownership of generic
runtime mechanics. Multi-agent orchestration, runtime-driver registration, and
process supervision remain owned by `process-forge-core`.
