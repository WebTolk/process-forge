# ADR: strict pre-release contracts without backward compatibility

- ADR id: `pre-release-remediation-no-compatibility-20260730`
- Date: 2026-07-30
- Status: accepted
- Run: `pre-release-remediation-20260730`

## Context

ProcessForge has not had a public release and has no external users. Carrying
legacy readers, deprecated aliases, migration warnings, fallback data shapes,
or compatibility-only public commands would make the first public contract
internally inconsistent before it is published.

The project-local working `.pf` and other dogfooding data are implementation
fixtures, not a reason to ship compatibility code. They may be migrated once
as controlled project/workplace data.

## Decision

1. Every public entity has one canonical schema, path layout, and command
   contract.
2. Deprecated aliases and legacy shapes are removed rather than supported with
   warnings.
3. Commands that may mutate require an explicit mode. Exactly one of
   `--dry-run` and `--apply` is required; neither and both are errors with zero
   product-state writes.
4. Platform authoring uses only the canonical
   `platform-contracts/platform.<id>/platform-contract.yaml` layout. Legacy
   platform paths are unsupported invalid state; the public product does not
   ship a compatibility reader or migration command.
5. Reusable-template manifests use only schema version 1 as the first public
   contract for release `1.0.0`. Pre-release legacy shapes are invalid and must
   be migrated in controlled fixtures before validation.
6. MCP authentication uses only the canonical structural `auth` contract.
   Legacy `auth_ref` input and read compatibility are removed.
7. Release archives use only release-manifest version 1 as the first public
   contract for release `1.0.0`. Pre-release sidecar shapes are rejected by
   every consumer path.
8. Internal source fixtures, project `.pf` data, and the shared dogfooding
   workplace are migrated explicitly and verified, without adding runtime
   compatibility branches.

## Consequences

- Some existing internal fixtures will intentionally fail until migrated.
- Regression tests assert rejection and absence of mutations for legacy input.
- Documentation describes only the canonical contract.
- Any future compatibility promise begins with the first public release, not
  with unpublished development states.

## Acceptance

No release candidate is accepted while public code, schemas, templates,
doctors, or docs still advertise or silently accept a superseded pre-release
contract.
