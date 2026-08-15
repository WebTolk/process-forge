# ProcessForge Update Assessment

## Status

safe

## Project

- root: process-forge
- current_version: 1.0.2
- available_version: 1.0.2
- channel: stable

## Breaking Changes

- None recorded.

## Required Migrations

- required: False
- guide: updates/migrations/1.0.2-update-server-contract.md

## Changes

- updates: Update servers now use a simple manifest and changelog URL contract, including local file manifests for offline or staged installations.
- documentation: Documentation now reflects the current runtime driver launch flow and the simplified update model.
- validation: Schemas and smokes now validate providerless update sites and reject the unsupported legacy url field.

## Affected Files

- tools/processforge.py
- schemas/update-site.schema.json
- schemas/entity-update-sites.schema.json
- schemas/update-source-registry.schema.json
- docs/concepts/update-sites.md
- docs/ru/concepts/update-sites.md

## Required Manual Review

- Review migration guide before changing project files.
- Confirm linked distribution registry points to the intended version.
- Run public cleanliness, schema validation, checksum validation, and project doctor after migration.

## Recommended Steps

1. Read the migration guide.
2. Update the ProcessForge distribution outside the project.
3. Refresh project context.
4. Apply project migrations only with approval.
5. Re-run validation gates.

## Rollback Notes

- Keep the previous ProcessForge distribution available in the workplace registry.
- Repoint the workplace distributions registry to the previous version if migration is blocked.
- Do not delete project `.pf/` artifacts created before the update until review passes.
