# Specialization Resource Profile Boundary Report

## Status

validated

## Boundary

Specialization is a first-class ProcessForge resource profile. It is created by
operators after workplace initialization, like platform contracts, knowledge
packages, tools, MCP definitions, templates, and runtime drivers. It is not a
hardcoded core role catalog, not a workflow definition, not a mini-process, not
a platform subtype, and not an agent identity.

Process owns workflow: stages, gates, acceptance criteria, required artifacts,
required evidence, and abstract capability requirements. Specialization owns the
professional resource profile: knowledge packages, tools, MCP providers,
templates, and capabilities available to a specialist for a selected
platform/project.

## Implementation

- `schemas/specialization.schema.json` now rejects workflow ownership fields
  such as `stages`, `gates`, `acceptance`, `required_artifacts`, and
  `required_evidence`.
- `templates/specialization.yaml` no longer emits process/workflow fields and
  includes `provides_capabilities`.
- `schemas/process-definition.schema.json` supports process-owned
  `required_artifacts`, `required_evidence`, and `acceptance`.
- `schemas/process-route-map.schema.json` and handoff handling support
  capability-first routing with specialization as a secondary constraint.
- `resolve_specialization_context` now builds:
  - `active_resource_profile`
  - `execution_route`
  - `capability_resolution`
- Existing flat resolver fields remain for backward compatibility.

## Capability Interface

Processes declare abstract required capabilities at the process or stage level.
Specializations provide capabilities generally or through matching
`platform_bindings`. The resolver reports `satisfied` and `unsatisfied`
capabilities and does not automatically switch specialization.

Built-in ProcessForge seed capabilities remain ambient compatibility providers
for existing core processes. User or fixture capabilities must come from the
selected resource profile.

## Snapshot And Capsule

Project-context snapshots now record active resource profile, execution route,
capability resolution, selected specializations, project overrides, conflicts,
effective resources, and fingerprints. Assignment capsules receive summaries
only: activated resources, specialization summary, process route summary,
capability resolution summary, and project override summary.

## Tests Run

Passed targeted checks:

- `python -m py_compile tools/processforge.py tools/validate-process-forge-schemas.py tools/specialization_smoke_helpers.py`
- specialization/project-overrides smoke set, including:
  - `smoke_specialization_no_workflow_ownership.py`
  - `smoke_process_owns_acceptance_not_specialization.py`
  - `smoke_process_capability_requirement_resolution.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --write`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1 --trace-smokes`
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`
- `git diff --check`

Release artifacts:

- `dist/processforge.zip`
- `dist/processforge.manifest.json`
- archive manifest file count: 727

## Remaining Limitations

- `overlay`, `replace`, and `fork` remain schema-reserved project override
  modes; deep arbitrary merge behavior is still outside this MVP.
