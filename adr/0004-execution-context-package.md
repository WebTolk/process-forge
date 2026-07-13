# ADR 0004: Execution Context Package

## Status

accepted

## Context

Agents need a stable task boundary even when manifests, packages, or templates change later.

## Decision

Each assignment can produce an immutable Execution Context Package.

## Consequences

- Context packages are not edited after creation.
- Source changes require a new context package.
- Checksums support stale-context detection.
