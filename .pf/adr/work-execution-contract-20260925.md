# ADR: Work, executor and diagnostic boundaries

## Status

Accepted design in T01 of vision-alignment plan r02; implementation belongs to
separate T09/T02/T03/T04/T05 Works. No product code changed by this ADR.

## Context

Source baseline a180ad624442d4fbe8ac1710073ef7d4c44babc4 has declarative Work and
process pinning, two different capsule builders, project-level resource reading,
provider-specific checks inside Host and a knowledge prompt that requires MCP.
T08 real-host acceptance restored installed/source provenance parity and exposed
the distinction between index readiness and authorized corpus coverage.
Sources: ../artifacts/t01-work-contract-20260925/investigation.md and
../artifacts/t01-work-contract-20260925/worker-capsule-field-map.md.

## Decision

Adopt docs/concepts/work-execution-contract.md and architecture decisions D01–D15.
One neutral contract separates immutable assignment intent/context from stage and
attempt projections. Work access intersects current authorization; no old cache
can restore revoked access. Scope defaults deny, required outputs do not add grants.
Additive Work reads leave project navigation semantics explicit. Public refs are
portable and private prepared runtime may resolve paths.

Keep old capsule envelopes readable, add a versioned complete contract block,
and reject ambiguous legacy execution instead of broadening it. Context replacement
preserves old capsules and provenance. Provider policy lives in trusted adapters;
Host retains generic authorization/raw-first/dedup/replay guarantees.

Optional diagnostics use canonical severity, profiles/config/locks and bounded
redacted sinks/export; required journal/evidence failure semantics stay independent.
The detailed decision matrix defines positive/negative/legacy/diagnostic behavior.

## Consequences

- T09 comes next and fixes bounded logger/config/sinks/export and entrypoint wiring.
- T02/T03 share normalization and pinned material concepts without silently changing
  project APIs or overwriting historical Work. Content identity cannot be inferred
  from metadata-only resources; mutable output trees need explicit roles.
- T04/T05 allow another trusted provider or offline shell without relaxing checks.
- Existing v1 ambiguity can require explicit successor/migration; this is deliberate
  refusal to manufacture absent permissions, not automatic global migration.
- T06 must test composition and actual-host behavior after integrated source changes.
- No global rules, installed update or public release is applied by this decision.
