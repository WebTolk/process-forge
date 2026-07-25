# ADR: Public Core And Dogfooding Boundary

Date: 2026-07-25

## Status

Accepted

## Context

ProcessForge public release checks were running internal stabilization smokes. Those tests are useful for developing ProcessForge itself, but they exercise timing-sensitive shell-agent and supervisor scenarios that should not define whether a public archive is publishable.

## Decision

Public release-test runs only checks marked `public_gate=true`. Internal stabilization tests live under `.pf/dogfooding/` and are run through `dev-test` / `dogfood-test` or directly through the manifest-driven runner.

The product checksum inventory lives under `checksums/`, not `.pf/artifacts/`, so public archives can exclude local evidence and dogfooding state.

## Consequences

- Public release archives are smaller and cleaner.
- Public release gates are stricter about product hygiene but less coupled to local development stress tests.
- Dogfooding suites remain available for maintainers without being shipped.
