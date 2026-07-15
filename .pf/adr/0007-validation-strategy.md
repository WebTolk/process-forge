# ADR 0007: Validation Strategy

## Status

accepted

## Context

The MVP needs useful validation without requiring a service.

## Decision

ProcessForge ships local validation scripts for structure, schema syntax, checksums, and public cleanliness.

## Consequences

- Validation can run in file-only mode.
- Scripts are intentionally lightweight.
- Future validators may become stricter without changing the file-first boundary.
