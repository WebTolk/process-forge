# Domain-Neutral Capability Resolution Report

Status: ready_for_review

## Summary

PF core now resolves user process capabilities as opaque data-driven IDs. The
resolver no longer has `BUILTIN_CAPABILITIES`, `BUILTIN_SEED_CAPABILITIES`, or a
`provider: builtin` satisfaction path for user/workplace capabilities.

## Removed Hardcode

- Removed the runtime built-in user capability set from `tools/processforge.py`.
- Removed built-in satisfaction from `build_capability_resolution`.
- Removed default `repository.read` / `markdown.editing` capability injection
  during project onboarding.
- Updated reporting helpers so availability comes from registries rather than
  a core capability catalog.

## Capability Sources

Provided capabilities now come from active data:

- selected specialization definitions
- matched specialization `platform_bindings`
- activated tool/MCP/template registry entries
- selected platform data and project overrides
- project-local specialization overlays

Missing process requirements remain `unsatisfied` and produce
`status: needs_resources`.

## Boundary Proof

- `smoke_no_builtin_user_capability_satisfaction.py` proves a missing
  capability is unsatisfied and no builtin provider is used.
- `smoke_capability_resolution_data_driven_only.py` proves identical PF code
  resolves differently based on workspace data.
- `smoke_domain_neutral_music_video_fixtures.py` proves domain-shaped fixture
  IDs resolve the same way as other fixture IDs.
- `smoke_runtime_no_domain_capability_constants.py` guards the runtime
  capability boundary.

## Project Overrides And Freshness

- `smoke_project_specialization_override_applies.py` proves specialization
  overlays change the effective resource profile before snapshot/capsule use.
- `smoke_specialization_freshness_tracks_definition_change.py` proves
  specialization definition changes mark existing project context stale while
  keeping existing snapshots pinned.
- Existing project override isolation smokes still pass.

## Schema Boundary

`schemas/specialization.schema.json` now rejects workflow fields at top level,
inside `platform_bindings`, and inside nested resource groups. The smoke
`smoke_specialization_nested_workflow_fields_rejected.py` covers these cases.

## Documentation

Updated capability, specialization, process-vs-specialization, project snapshot,
workplace resources, and workplace init docs in English and Russian where
applicable. Docs now state that PF core is domain-neutral and does not satisfy
user capabilities by default.

## Validation

Passed:

- `python -m py_compile tools/processforge.py bin/pf.py tools/specialization_smoke_helpers.py`
- all seven new domain-neutral smokes
- existing specialization/process/project override smokes requested by the prompt
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1 --trace-smokes`
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`
- `git diff --check`

Archive result: PASS, 737 files.

## Limitations

PF still includes software lifecycle process examples as process/package data.
They are not core capability defaults and no longer satisfy missing resource
requirements without active providers.
