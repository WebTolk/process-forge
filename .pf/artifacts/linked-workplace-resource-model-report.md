# Linked Workplace Resource Model Report

## Status

ready_for_review

## Scope

Implemented the MVP linked workplace/resource/self-update slice from
`задания/processforge_linked_workplace_resources_self_update_master_prompt.md`.

## Delivered

- Linked mode is documented as the primary model.
- Project `.pf/` remains a thin flow layer; generated projects do not copy core ProcessForge into `.pf/`.
- Workplace initialization now creates `registries/distributions.yaml`.
- Project initialization records `processforge.core` as `source: distribution`.
- Project initialization now selects platforms from detected files, `project.type`, `project.type_hint`, platform hints, and `intake`.
- `example-parent-project`, `example-extension`, and `example-library` hints select `platform.example-parent`.
- Platform contract resolution expands required capabilities plus knowledge package, tool, MCP, and template ids.
- Snapshot resolution indexes package `resources` into `snapshot.knowledge_resources.selected` without reading heavy resource paths.
- Snapshot resource records never expose absolute local paths; resource `path` values are converted to `path_ref`, and private absolute paths are redacted.
- Platform contract `requires.tools/templates/mcp` are treated as required, while `includes.tools/templates/mcp` are treated as recommended.
- Snapshot output clearly separates required and recommended knowledge resources, tools, MCP, and templates.
- Generated `.pf/hooks.yaml` quotes wildcard event types as `"*"`.
- `doctor-project` validates hooks YAML and linked distribution availability.
- `doctor-project` fails on missing required platform contracts and warns on missing optional platform resources.
- `doctor-project` fails when a public project context snapshot contains a local absolute path.
- Invalid hooks produce friendly `FAIL` output instead of Python traceback.
- `project-context-refresh` continues to work when hooks are invalid.
- `terms.yaml` supports Russian semantic aliases and `resolves_to`.
- Package manifests support lightweight resource indexes with load policies.
- Platform contracts, template packages, and update metadata have schemas and templates.
- `self-update-check` and `project-upgrade-check` provide local update assessment behavior without automatic migration.
- Future WTAICC compatibility remains event/outbox based.

## Files Changed

- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `tools/validate-process-forge-checksums.py`
- `tools/validate-public-cleanliness.py`
- `schemas/*.schema.json`
- `templates/*`
- `templates/registries/distributions.yaml`
- `docs/concepts/*`
- `processes/processforge-update-check.yaml`
- `updates/processforge-update-index.yaml`
- `updates/migrations/0.1.0-linked-workplace.md`
- `.pf/process-forge.yaml`
- `.pf/contexts/project-context.snapshot.*`

## Verification Summary

- `python -m py_compile tools/processforge.py`: pass
- `python tools/validate-process-forge-schemas.py --root .`: pass
- `python tools/validate-public-cleanliness.py --root .`: pass
- `python tools/processforge.py events-validate --project-root .`: pass
- `python tools/processforge.py hooks-dispatch --project-root . --event-type assignment.completed --dry-run`: pass
- Temporary init-project smoke: pass
- Example Parent Platform type-hint/platform/resource resolver smoke: pass
- Snapshot public path smoke: pass
- Invalid hooks negative smoke: friendly FAIL, no traceback
- Missing linked distribution negative smoke: FAIL
- Missing required capability negative smoke: blocked refresh
- Missing required platform contract negative smoke: FAIL
- Public snapshot absolute local path negative smoke: FAIL

## Residual Risks

- Update comparison is intentionally simple and does not implement semantic version ordering.
- Platform contract selection depends on workplace registry entries being present; this is now enforced as `FAIL` for required platform contracts.
- `project-upgrade-check` writes a Markdown assessment, not a structured YAML assessment yet.
