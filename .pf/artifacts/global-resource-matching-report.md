# Resource Matching Report

Reviewed on 2026-09-27. This report describes declared and selected resources;
it does not expand filesystem access or assert all global resources were loaded.

## Selected Work resources

| Resource id | Meaning | Selection |
| --- | --- | --- |
| `project.process-forge:project-profile` | Project profile note | Selected by the current capsule |
| `project.process-forge:project-artifacts` | Project artifact reference collection | Selected by the current capsule |

The project package declares these resources in
[project.process-forge.yaml](../packages/project.process-forge.yaml). Profile
loads when relevant with full-text indexing; artifact collection loads on demand
with metadata indexing. Resource presence is not permission to publish its
contents or bypass Work scope.

## Packages, platform and tools

The manifest knowledge stack includes `processforge.core` from the distribution
and `project.process-forge` from the project. The pinned software process requires
`process-forge-core` and `processforge.official.software-development`.
No platform/toolchain overlay or active specialization is selected. This does
not imply Python is absent: it is the observed implementation language.

Required process templates are documented in the
[template report](template-matching-report.md). Actual tools and MCP limitations
are documented in the [tool report](toolchain-detection-report.md) and
[MCP report](mcp-capability-report.md).

## Readiness and limits

Standard context check reported fresh resources and ready execution with no
missing required capabilities. The connected MCP timed out; no waiver or global
registration is inferred from that observation. Current Work uses installed CLI
and directly verified local tools. Broader global docs/skills/platform roots are
not imported into the project package by this task.
