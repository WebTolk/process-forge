# Context Capsule

A context capsule is the small launch package for a worker-agent. It references
an Execution Context Package and carries the minimum startup policy needed to
begin a bounded assignment.

## Purpose

The capsule lets an orchestrator or runner start workers without handing them the
whole project world. It preserves file scope, source list, allowed actions,
forbidden actions, and context rebuild policy.

## Contents

A capsule includes:

- capsule id
- referenced Execution Context Package
- assignment path
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

The orchestrator resolves context once, compiles one ECP per assignment, and
passes capsules to workers when multi-agent work would otherwise duplicate
repository discovery.
