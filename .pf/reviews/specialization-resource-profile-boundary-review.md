# Review: Specialization Resource Profile Boundary

## Status

passed

## Scope

Review the specialization/process boundary across schemas, templates, resolver,
snapshot/capsule output, routing metadata, docs, and smoke coverage.

## Checklist

- Specialization schema does not own stages, gates, acceptance, artifacts, or
  evidence.
- Process schema owns capability, artifact, evidence, and acceptance fields.
- Resolver produces `active_resource_profile`, `execution_route`, and
  `capability_resolution`.
- Unsatisfied non-built-in capabilities are explicit conflicts.
- Handoff routing prefers `required_capabilities` and treats specializations as
  secondary constraints.
- Runtime remains data-driven and fixture-only in public smokes.
- Public cleanliness and schema checks pass.

## Current Result

Targeted boundary smokes, the full specialization/project-overrides smoke set,
schema validation, public cleanliness, checksum validation, public release-test,
release-pack, extracted archive full validation, and `git diff --check` pass.
