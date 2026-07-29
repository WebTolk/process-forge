# Specialization And Project Overrides Report

## Status

validated

## Concept

Specialization is implemented as a workplace/project resource, not as a
hardcoded ProcessForge core role. It is separate from:

- platform: where work happens;
- process: lifecycle being executed;
- agent: who executes;
- project override: project-local refinement of workspace defaults.

Workspace specializations live under `<workplace>/specializations/` and are
registered in `<workplace>/registries/specializations.yaml`. Project-local
specializations and overrides live under `.pf`.

## Schemas And Templates

Added public schemas and templates:

- `schemas/specialization.schema.json`
- `schemas/specialization-registry.schema.json`
- `schemas/project-overrides.schema.json`
- `templates/specialization.yaml`
- `templates/registries/specializations.yaml`
- `templates/project-overrides.yaml`

`workplace.schema.json` and `templates/workplace.yaml` now include the
`specializations` registry.

## Resolver Behavior

The resolver is data-driven. It loads platform stack resources, selected
specializations, matching `platform_bindings`, and `.pf/project-overrides.yaml`.
It computes activated/excluded knowledge packages, tools, MCP providers, and
templates. Project overrides are recorded with base hash, override hash, merge
mode, and effective fingerprint.

Required resources cannot be silently disabled; such attempts are reported as
conflicts. Recommended and optional resources may be disabled by project
overrides.

## Snapshot And Capsule

Project-context snapshots now include:

- selected specializations;
- activated and excluded resources;
- applied project overrides;
- effective fingerprints;
- resolution reasons and conflicts.

Project-context freshness watches `.pf/project-overrides.yaml`,
`.pf/specializations/**`, `.pf/tools/overrides/**`, `.pf/mcp/overrides/**`,
`.pf/packages/**`, `.pf/knowledge/**`, and `.pf/rules/**` through source
fingerprints.

Assignment capsules receive summaries only: effective specializations,
effective resources, and project override summaries. They do not embed full
knowledge content or raw override files.

## CLI

Added generic commands:

- `specialization-list`
- `specialization-show`
- `specialization-doctor`
- `specialization-create`
- `specialization-bind-platform`
- `project-override-add`
- `project-override-list`
- `project-override-doctor`
- explicit `context-resolve --platform --process --specialization --json`

`agent-register`, `agent-checkin`, `session-start`, `run-create`, `task-create`,
and handoff metadata can record specialization support or selection.

## No-Hardcode Rules

Runtime logic uses generic ids and synthetic `fixture.*` smoke fixtures. The
new no-hardcode smoke scans `tools/processforge.py` for forbidden real product
ids.

## Tests Run

Passed targeted new smokes:

- `smoke_specialization_schema.py`
- `smoke_specialization_registry.py`
- `smoke_specialization_create_workplace_resource.py`
- `smoke_specialization_platform_binding.py`
- `smoke_specialization_context_resolution.py`
- `smoke_specialization_same_platform_different_context.py`
- `smoke_specialization_no_tool_leakage.py`
- `smoke_specialization_process_policy.py`
- `smoke_specialization_handoff_routing.py`
- `smoke_specialization_garage_mode_switch.py`
- `smoke_specialization_snapshot_fields.py`
- `smoke_specialization_capsule_activation.py`
- `smoke_specialization_no_core_id_hardcode.py`
- `smoke_project_overrides_schema.py`
- `smoke_project_overrides_resolution.py`
- `smoke_project_overrides_snapshot_fingerprint.py`
- `smoke_project_overrides_freshness.py`
- `smoke_project_overrides_capsule_summary.py`
- `smoke_project_override_does_not_mutate_workspace.py`

Passed release gates:

- `python -m py_compile tools/processforge.py tools/specialization_smoke_helpers.py ...`
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
- archive manifest file count: 722

## Remaining Limitations

- `overlay`, `replace`, and `fork` are schema-supported and recorded; the MVP
  resolver only applies concrete runtime behavior for `disable`, `extension`,
  and `parameterize`.
- The resolver records specialization override fingerprints but does not yet
  deep-merge arbitrary override YAML into base specialization documents.
