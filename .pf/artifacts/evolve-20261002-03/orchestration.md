# evolve-20261002-03 Orchestration

Timestamp: 2026-10-02T14:08:00Z

Objective:
Normalize project and Work full-text resource policy for `evolve-20261002-03`.

Work identity:
- Run: `garage-implement-evolve-20261002-03-normalize-project-and-work-full-text`
- Assignment: `implement-evolve-20261002-03-normalize-project-and-work-full-text-resour`
- Context: `implement-evolve-20261002-03-normalize-project-and-work-full-text-resour-capsule`
- Capsule checksum: `sha256:9e920918da4cf9d06610455b2061497736037ea97d4f862465f31963b47e90b4`

Task record:
- Source task: `.pf/artifacts/evolve/tasks-20261002/evolve-20261002-03.md`
- Defect: explicit selected resources without `indexing` can lose legacy
  `index_policy: full_text` and become metadata-only inside Work material.
- Expected result: one normalized policy path for snapshot, project search,
  Work bindings and prepared resources; explicit metadata remains metadata.

Execution context summary:
- `pf.context` is fresh and recommends `continue`.
- The Work capsule is valid and execution readiness is `ready`.
- Python knowledge resources are selected through the project context.
- Serena symbol extraction is unavailable in this checkout with
  `Active languages: []`; code investigation will use narrow `rg` and
  targeted reads.

Lifecycle mode decision:
- Use the pinned `software-feature-development` process.
- Keep the task source-level only: no commit, push, installation or Runtime
  restart unless separately requested.
- Preserve old capsules/processes/accepted artifacts.

Scope note:
- Initial scope including `tools/processforge.py` was rejected because active
  Work `agent-entry-e01-e02-scoped` already owns that file.
- The accepted Work excludes `tools/processforge.py`; investigation must prove
  whether Core-only changes are sufficient or stop with a blocker.
