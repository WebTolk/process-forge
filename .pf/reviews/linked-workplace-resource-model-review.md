# Linked Workplace Resource Model Review

## Reviewed Object

Linked workplace/resource/self-update implementation.

## Reviewer

Codex

## Criteria

- Linked mode is primary and documented.
- Project `.pf/` stays thin.
- Generated hooks YAML is valid.
- Doctor validates hooks and linked distribution.
- Invalid hooks fail gracefully.
- Resource, platform, template, and update contracts exist.
- `platform.joomla` is selected from Joomla project hints and resolves contract includes.
- Package resources are indexed into the snapshot without loading resource contents.
- Existing validators pass.

## Result

pass_with_conditions

## Findings

- No blocking findings.
- Update checks are local MVP stubs; they do not perform automatic migration or remote version discovery.
- Required platform contracts block when missing; optional platform resources warn when absent from workplace registries.

## Evidence

- `.pf/artifacts/linked-workplace-resource-model-report.md`
- `.pf/artifacts/processforge-update-assessment.md`
- `.pf/contexts/project-context.snapshot.yaml`
- `docs/concepts/linked-workplace-model.md`
- `schemas/distributions-registry.schema.json`
- `templates/platform-contract-joomla.yaml`
- `processes/processforge-update-check.yaml`

## Recommendation

Accept for MVP linked operation and keep future package-manager behavior out of scope until a separate assignment defines it.
