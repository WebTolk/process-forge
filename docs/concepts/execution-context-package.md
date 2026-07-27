# Execution Context Package

When an assignment uses a delivery/build profile, the profile is part of the
execution context for the run. It is not a replacement for `process_id`.
Use `process_id: software-feature-development` plus
`execution_profile.delivery_profile` for release/package/install operations.

An Execution Context Package is an immutable snapshot for one assignment.
It is currently a compatibility artifact for the deprecated `context-compile`
command.

It records the process, stage, role, task input, selected packages, selected templates, selected tools, selected MCP capabilities, allowed actions, forbidden actions, required outputs, quality gates, and checksums.

## Immutability

After creation, an Execution Context Package is not edited. If the assignment, manifest, packages, or templates change, create a new context package.

## Staleness

An Execution Context Package is stale when any required source changes and the checksum no longer matches the recorded source hash.

## Use

Agents and humans using legacy `context-compile` flows should read the package
before work and treat it as the active task boundary.

In the active `worker-run` flow, the assignment capsule is the canonical launch
descriptor. New capsules carry assignment and snapshot checksums directly.
