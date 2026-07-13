# ADR 0002: Workplace And Project Layer

## Status

accepted

## Context

Process execution needs both machine-local capability knowledge and project-specific rules.

## Decision

ProcessForge separates the workplace layer from the project flow layer.

## Consequences

- Workplace manifests describe local availability.
- Project manifests describe project rules and selected processes.
- Organization policies belong in knowledge packages, not workplace state.
