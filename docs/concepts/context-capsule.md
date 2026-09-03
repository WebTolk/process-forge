# Context Capsule

A context capsule is the small launch package for a worker-agent. In the active
`worker-run` path it is the canonical launch descriptor for a bounded assignment.
It records the assignment path, assignment checksum, project snapshot checksum,
scope, outputs, capability records, and context rebuild policy.

For governed Work, the same capsule is also the narrow effective context: it
pins one active process definition, active specialization ids, and selected
resource identities. It must not include definitions for every process or
specialization merely authorized by the project snapshot.

Selected resource identities remain an auditable snapshot pin in 1.1.0. They
do not claim process- or specialization-specific re-resolution of the project
resource universe; that narrower authorization remains a separate future step.

In [multi-agent orchestration](multi-agent-orchestration.md), each worker launch
prompt points to one assignment capsule. The capsule keeps the worker bounded to
its assignment, required sources, allowed scopes, forbidden files, required
outputs, and context rebuild policy.

## Purpose

The capsule lets an orchestrator or runner start workers without handing them the
whole project world. It preserves file scope, source list, allowed actions,
forbidden actions, and context rebuild policy.

## Contents

A capsule includes:

- capsule id
- assignment path
- assignment checksum
- required sources
- allowed files
- forbidden files
- allowed actions
- forbidden actions
- `worker_may_rebuild_context`
- freshness status

## Worker Contract

Workers must read only the required sources unless the assignment expands scope.
They must not rebuild context when `worker_may_rebuild_context` is false. They
must preserve forbidden actions even when an allowed action appears more local.

## Orchestrator Contract

The orchestrator resolves context once and passes capsules to workers when
multi-agent work would otherwise duplicate repository discovery. Automated worker
launches must not overwrite an existing capsule. If the assignment changed after
capsule creation, the worker launch must stop and require an intentional new
capsule.

Execution Context Packages are still supported by the deprecated
`context-compile` compatibility command, but they are not required by the active
`assignment-capsule` and `worker-run` path.
