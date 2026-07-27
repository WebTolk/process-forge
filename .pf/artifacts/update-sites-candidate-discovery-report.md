# Update Sites Candidate Discovery Report

## Baseline

ProcessForge already had read-only update source registries, installed subjects, derived entity update sites, normalized update manifest validation, `self-update-check`, and `project-upgrade-check`. The missing slice was the unified operator-controlled lifecycle from update site to candidate, notification, staging, verification, apply, and rollback.

Serena symbol extraction was unavailable for this repository because the active project language profile is empty; implementation used targeted file/range inspection.

## Schemas Changed

- Added `schemas/update-site.schema.json`.
- Added `schemas/update-apply-plan.schema.json`.
- Added `schemas/update-stage-record.schema.json`.
- Added `schemas/update-rollback-record.schema.json`.
- Extended update source, entity update site, installed update site, installed subjects, candidates, notifications, package, tool, MCP, platform, and template schemas for `manifest_url`, `changelog_url`, `provider`, subject types, and tool update policy.

## CLI Commands Added

- `update candidates refresh|list|show|clear`
- `update notifications create|list|acknowledge`
- `update changelog show`
- `update stage`
- `update verify`
- `update apply --confirm`
- `update rollback`
- `update doctor`

Existing commands kept working:

- `self-update-check`
- `project-upgrade-check`
- `update sources`
- `update entity-sources rebuild|list`
- `update manifest validate`

## Subject Types Supported

Implemented/discovered:

- `processforge_distribution`
- `workplace`
- `process_package`
- `knowledge_package`
- `template_package`
- `tool_package`
- `tool_definition`
- `platform_contract`
- `mcp_definition`
- `process_definition`
- `reusable_template`
- `knowledge_resource`

Boundary:

- `project_pf` is excluded from downloadable candidates and remains assessment/migration only.

## Provider Support Matrix

| Provider | Status | Smoke coverage |
| --- | --- | --- |
| `processforge_json_file` | implemented | yes |
| `processforge_json` | implemented with timeout | CLI path, no public network smoke |
| `generic_http_directory` | planned | no |
| `github_releases` | planned | no |
| `gitlab_releases` | planned | no |
| `gitverse_releases` | planned | no |
| `tuf_repository` | planned | no |

## Lifecycle Implemented

- Update sites prefer `manifest_url`; legacy `url`/`path` are normalized and migration-warned.
- Candidate refresh fetches local/HTTP ProcessForge JSON manifests, compares versions semver-first with lexical warning fallback, and writes `runtime/update/candidates.json`.
- Candidate fields include subject id/type, installed/current version, available version, manifest URL, changelog URL, download URL, sha256, status, installable flag, update policy, and post-update doctor list.
- Notifications are created and listable in `runtime/update/notifications.json`; acknowledge updates status and timestamp.
- Optional organized mode mirrors notifications into `director/inbox/` when that directory exists.
- Changelog command shows URL and local file content for file-provider candidates.
- Stage copies/downloads artifacts into `runtime/update/staged/<candidate-id>/` and writes `stage-record.yaml`.
- Verify checks sha256 and zip package identity.
- Apply requires `--confirm`, creates backup, applies local package zip overlays and local tool `replace_file` updates, writes apply record, and updates installed subjects.
- Rollback restores the same local package/tool update from backup and writes rollback record.

## Tool Update Policy

`replace_file` is covered for local deterministic tool updates. `custom_command_requires_confirmation` is blocked by default; the smoke verifies that the custom command is not executed through normal apply.

## Public Boundary

Runtime update caches, staged artifacts, backups, notifications, and private URLs remain under workplace `runtime/update/` and are not public archive content. Public smokes use `file:///` fixtures and no real network.

## Validation Results

- `python tools/smoke_update_sites_schema.py`: PASS
- `python tools/smoke_update_candidate_discovery.py`: PASS
- `python tools/smoke_update_notifications.py`: PASS
- `python tools/smoke_update_stage_verify_apply_file_provider.py`: PASS
- `python tools/smoke_project_pf_upgrade_assessment_boundary.py`: PASS
- `python tools/smoke_tool_update_policy.py`: PASS
- `python tools/validate-process-forge-schemas.py --root .`: PASS
- `python tools/validate-public-cleanliness.py --root .`: PASS
- `python tools/validate-process-forge-checksums.py --root . --check`: PASS
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1`: PASS
- `python bin/pf.py release-test --root . --public --timeout-scale 1`: PASS
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`: PASS, 614 files
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`: PASS
- Clean extracted archive proof from `C:\Users\musst\AppData\Local\Temp\pf-update-sites-final-u68lxhyt`: PASS for six update smokes and public fail-fast release-test. The extracted release-test reports `PASS with warnings` only because `git diff --check` is skipped outside a git repository.

## Remaining Limitations

- `processforge_json` remote fetch is implemented, but public tests intentionally avoid real network.
- Planned providers remain schema/contract names until provider-specific smokes are added.
- ProcessForge distribution self-update apply over a source checkout remains conservative/manual.
- Workplace updates are represented as assessment/migration policy; overwrite-safe migration application is deferred.
