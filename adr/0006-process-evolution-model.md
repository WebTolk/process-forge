# ADR 0006: Process Evolution Model

## Status

accepted

## Context

Processes will evolve while older artifacts and completed work remain valuable.

## Decision

Process versions are immutable, and upgrades are assessed through artifact-centered compatibility.

## Consequences

- Existing approved artifacts cannot be silently invalidated.
- Unsafe upgrades require approval, migration, or blocking.
- Each process definition owns its evolution policy.
