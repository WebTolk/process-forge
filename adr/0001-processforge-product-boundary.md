# ADR 0001: ProcessForge Product Boundary

## Status

accepted

## Context

ProcessForge must be a clean-start file-first product for repeatable workflows across domains.

## Decision

ProcessForge is not limited to software development and does not require a backend, database, web UI, runner, or platform-specific integration.

## Consequences

- The MVP uses files as the authoritative interface.
- Future runner and managed modes are optional.
- Public materials describe only ProcessForge concepts.
