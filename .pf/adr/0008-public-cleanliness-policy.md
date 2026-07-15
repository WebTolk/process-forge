# ADR 0008: Public Cleanliness Policy

## Status

accepted

## Context

Public product files must not leak private work materials, local machine paths, secrets, or scratch notes.

## Decision

Public product files are validated before release. Private research and work notes are excluded from release inventory.

## Consequences

- Public files use only ProcessForge terminology.
- Release ignores private working areas and local IDE state.
- Public cleanliness is a release gate.
