# Core Updater Smoke Report

Run: `core-updater-manifest-locking-20260822`
Task: `core-updater-manifest-file-failure-20260822`

## Implemented

- Hardened manifest-based core updater apply error handling.
- `OSError` during file operations is converted to `CoreUpdateError` with code `file_operation_failed`.
- The updater leaves `runtime/core-update/in-progress.json` with:
  - `status: failed`
  - `failed_at`
  - `backup_dir`
  - explicit error code/message.
- `core-update status` exposes `incomplete_update`.
- `core-update repair` reports `manual_repair_required` for failed incomplete updates.

## Smoke Coverage

Updated `tools/smoke_core_update_manifest.py` to cover:

- add/change/remove update;
- unknown file preservation;
- confirm-required apply;
- locally modified blocker;
- malicious path rejection;
- injected locked/file-operation failure;
- incomplete update visibility through `status`;
- repair visibility through `manual_repair_required`.

## Validation

- `python -m py_compile src/processforge_core/core_update.py tools/smoke_core_update_manifest.py`
- `python tools/smoke_core_update_manifest.py`

## Remaining

- Real OS locked-file handle smoke on Windows.
- Automated repair continue/rollback.
- Runtime/MCP stop/start/health integration.
