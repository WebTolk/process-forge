# Execution Context Package

An Execution Context Package is an immutable snapshot for one assignment.

It records the process, stage, role, task input, selected packages, selected templates, selected tools, selected MCP capabilities, allowed actions, forbidden actions, required outputs, quality gates, and checksums.

## Immutability

After creation, an Execution Context Package is not edited. If the assignment, manifest, packages, or templates change, create a new context package.

## Staleness

An Execution Context Package is stale when any required source changes and the checksum no longer matches the recorded source hash.

## Use

Agents and humans should read the package before work and treat it as the active task boundary.
