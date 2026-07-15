# ADR 0003: Cascade Merge Model

## Status

accepted

## Context

Execution contexts need predictable composition from multiple sources.

## Decision

ProcessForge uses a specificity-ordered cascade merge with locked policy protection and blocking conflict handling.

## Consequences

- Contexts record all sources.
- Locked policy conflicts stop context assembly.
- Lists merge by `id` when available.
