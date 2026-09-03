# Core Updater Manifest Current-State Audit

Run: `core-updater-manifest-current-state-audit-20260822`
Task: `core-updater-manifest-current-state-audit-20260822`
Mode: read-only product audit; no product code, schema, or docs edits.

## Scope

This audit covers the current install, release, update, CLI, Runtime/MCP, and test surfaces relevant to a future manifest-based in-place ProcessForge core updater.

Primary sources:

- `.pf/artifacts/core-updater-manifest-20260822/master-worker-intake-report.md`
- `tools/processforge.py`
- `docs/getting-started/update-system.md`
- `docs/concepts/update-lifecycle.md`
- `docs/concepts/processforge-self-update.md`
- `tools/smoke_update_stage_verify_apply_file_provider.py`
- `tools/smoke_release_manifest_provenance_contract.py`

## Current Release Archive Surface

The release archive flow is implemented in `tools/processforge.py`:

- `release_git_provenance` requires a Git checkout and a clean worktree before publishing.
- `write_release_zip` writes deterministic ZIP entries and returns per-file `path`, `size`, and `sha256`.
- `release_manifest_payload` writes a sidecar manifest with:
  - `schema_version`
  - `name`
  - `version`
  - `schema_bundle_version`
  - deterministic build metadata
  - Git source commit/tree provenance
  - archive filename/size/sha256/entry count
  - official pack entries
  - archive file entries.
- `command_release_pack` supports `--dry-run` and otherwise writes `<archive>.zip` plus `<archive>.manifest.json`.
- `release-archive-test` validates the archive/manifest contract and can run extracted release tests.

CLI bindings:

- `release-pack` -> `command_release_pack`
- `release-archive-test` -> `command_release_archive_test`

Current limitation for this feature: the sidecar release manifest is an archive content/provenance manifest. It is not yet an installed-core ownership manifest designed for later in-place update decisions.

## Current Update Framework Surface

The update framework is workplace-oriented and centered on update sources, candidates, staging, verification, apply, rollback, and doctor commands.

Current CLI surface:

- `update bootstrap-source list|validate`
- `update sources`
- `update sources-list`
- `update entity-sources rebuild|list`
- `update candidates refresh|list|show|clear`
- `update notifications create|list|acknowledge`
- `update changelog show`
- `update stage`
- `update verify`
- `update apply`
- `update rollback`
- `update doctor`
- `update manifest validate`

Current normalized update manifest validation:

- `validate_normalized_update_manifest_data` validates `normalized-update-manifest.schema.json`.
- It requires `schema_version: 1`, `product.id`, `subjects[]`, subject `type/id`, version `artifacts[]`, artifact `url`, and 64-hex `sha256`.
- It validates artifact URL shape through `valid_artifact_url_shape`.

Current stage/verify/apply/rollback behavior:

- `fetch_update_manifest` supports local/file and HTTP/HTTPS manifests.
- `copy_or_download_update_artifact` supports local/file and HTTP/HTTPS artifacts.
- `command_update_stage` copies/downloads the candidate artifact into `runtime/update/staged/<candidate-id>/`, computes sha256, and writes `stage-record.yaml`.
- `command_update_verify` rechecks sha256 and, for ZIP artifacts, reads a package/tool/process/platform-style manifest from the ZIP and checks subject id/type/version against the candidate.
- `safe_extract_zip` rejects ZIP entries that resolve outside the destination.
- `command_update_apply` requires `--confirm`, reruns verify, creates a backup, then:
  - for `replace_file` or tool subject types, backs up/replaces one executable path;
  - otherwise backs up the existing install directory, removes it, and extracts/copies the staged artifact into the install path.
- `command_update_rollback` restores the backup tree/file and writes a rollback record.
- `command_update_doctor` validates candidate/notification schema state and update runtime readability.
- `mark_impacted_project_contexts_after_update` marks linked project context snapshots stale for update subject types that affect resolved project context.

Current limitation for this feature: apply currently replaces a package/tool install path as a whole. It does not compute old/new core manifest diffs, does not delete only PF-owned obsolete files, does not preserve unknown files by design during a core overlay, and does not detect locally modified PF-owned files from an installed manifest.

## Current Core Distribution Update Model

`docs/getting-started/update-system.md` explicitly treats installed ProcessForge core updates as a manual distribution replacement:

1. Extract `processforge.zip` to a new versioned directory outside the project.
2. Verify the new distribution.
3. Update `<workplace>/registries/distributions.yaml` to point to the new directory/version.
4. Validate the workplace and linked projects.
5. Roll back by repointing the distribution registry to the previous directory.

The same document warns that overlaying a new archive onto an old directory is a manual recovery option and can leave files removed from the new release.

Current limitation for this feature: there is no first-class in-place `core update status|plan|apply|repair` flow. The safe supported core path is side-by-side install plus registry switch.

## Runtime/MCP Surface

The current update framework can mark impacted project context snapshots stale after update. The audited code and docs did not show an owned Runtime/MCP stop/start or health preflight integrated into `update apply`.

Current limitation for this feature: Runtime/MCP ownership and lifecycle handling remains a design requirement for future core updater work. PID-only termination must not be used; process ownership verification is required before any stop/start automation.

## Existing Relevant Test Coverage

Relevant tests/smokes found:

- `tools/smoke_update_stage_verify_apply_file_provider.py` covers local-file package update stage, verify, apply confirmation requirement, installed subject registry update, and rollback.
- `tools/smoke_update_apply_marks_context_stale.py` covers marking project context stale after update apply.
- `tools/smoke_release_manifest_provenance_contract.py` covers `release-pack` and `release-archive-test` manifest/provenance contract behavior.
- Release test registry includes `smoke_knowledge_package_release_update_manifest`.

Coverage gap for this feature:

- installed core manifest validation;
- old/new core manifest diff;
- obsolete PF-owned file deletion;
- unknown/user file preservation;
- local modification detection;
- interrupted core update status/repair;
- Windows locked-file handling;
- Runtime/MCP health and ownership preflight;
- clean install and in-place update parity from one archive.

## Feature Gap Summary

The current codebase already has useful primitives:

- deterministic release archive and sidecar manifest generation;
- archive manifest validation;
- normalized update manifest validation;
- sha256-verified staging;
- safe ZIP extraction containment;
- explicit apply confirmation;
- backup and rollback;
- context snapshot stale marking after relevant updates.

The future core updater still needs a separate installed-core ownership model:

- a core manifest installed with the distribution;
- release archive entries mapped to the same core manifest contract;
- read-only `status`/`plan` before apply;
- old/new manifest diff with add/change/remove classification;
- local file hash comparison against the installed manifest;
- deletion limited to files present in the old manifest and absent from the new manifest;
- unknown files preserved;
- directories removed only when empty after owned-file deletion;
- manifest-last finalize;
- interrupted update detection and repair;
- Runtime/MCP owned-process preflight and post-update health checks.

## Recommended Next Write Scopes

Keep the next work sequential unless scopes are split so no two writers touch `tools/processforge.py`.

1. `core-manifest-design`
   - Output: `.pf/artifacts/core-updater-manifest-20260822/core-manifest-design.md`
   - Product writes: none.

2. `core-update-transaction-design`
   - Output: `.pf/artifacts/core-updater-manifest-20260822/core-update-transaction-design.md`
   - Product writes: none.

3. `core-updater-plan-slice`
   - Product write candidates:
     - `tools/processforge.py`
     - `schemas/` only if a new installed-core manifest schema is introduced.
     - focused `tools/smoke_*core*updater*.py` tests.
   - Required first behavior: read-only archive/manifest validation and plan output. No deletion/apply in this slice.

4. `core-updater-apply-repair-slice`
   - Product write candidates:
     - `tools/processforge.py`
     - focused tests for backup, manifest-last finalize, interrupted update, repair, local modifications, and Windows lock behavior.

5. `core-updater-release-integration`
   - Product write candidates:
     - release pack manifest generation in `tools/processforge.py`
     - release/archive validation tests
     - release documentation.

6. `core-updater-runtime-mcp-slice`
   - Product write candidates:
     - Runtime/MCP process ownership and health-check code after exact runtime entry points are selected.

## Validation Performed

Read-only evidence commands:

- CLI binding search for release/update command handlers.
- Code inspection of release archive manifest generation and validation.
- Code inspection of update stage/verify/apply/rollback/doctor.
- Documentation inspection of the current core distribution update model.
- Existing smoke inspection for update stage/verify/apply/rollback.

No product files were modified.
