# In-Place Update Acceptance Report

Date: 2026-08-23
Status: PASS with compatibility note

## Archive Under Test

- Previous archive source: committed `HEAD:dist/processforge.zip` before the
  final 1.1.0 artifact update.
- Previous archive version: `1.0.2`.
- New archive: `dist/processforge.zip`.
- New archive version: `1.1.0`.

## Acceptance Result

- PASS: extracted previous `1.0.2` archive into a temp installed core root.
- PASS: current 1.1.0 `core-update status --core-root <old-core>`.
- PASS: current 1.1.0 `core-update plan --core-root <old-core>
  --archive dist/processforge.zip`.
- PASS: current 1.1.0 `core-update apply --core-root <old-core>
  --archive dist/processforge.zip --confirm`.
- PASS: installed `VERSION` changed from `1.0.2` to `1.1.0`.
- PASS: current 1.1.0 `core-update status` after apply.
- PASS: updated installed core `release-check`.
- PASS: updated installed core `core-update status`.

## Compatibility Note

The previous `1.0.2` public ZIP does not contain
`processforge-core.manifest.json` and its CLI does not expose `core-update`.
Therefore, self-apply by the old installed tool is not available for that
archive. The accepted path for this prerelease is an external/current
manifest-based updater applying the 1.1.0 archive to an installed 1.0.2 core.

## Supporting Gates

- PASS: `smoke_core_update_manifest`.
- PASS: `smoke_update_stage_verify_apply_file_provider`.
- PASS: full public `release-test`.
