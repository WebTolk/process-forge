# f0912 Review Report

## Result

Bounded review: **PASS with documented limitations**. No concrete regression found in updater restoration/collision handling, search authorization/deduplication, or ingress recovery/concurrency.

## Reviewed design

- `core_update.py`: restores missing unchanged owned files, records `restored`, backs up prior absence as `null`, and blocks symlinks/nonregular paths and obstructing unowned ancestors.
- `local_resource_search.py`: applies include/exclude rules to explicit files and file roots, deduplicates by `(resource_id, relative_path)`, preserves full-text content over overlapping metadata, and invalidates prior schema versions.
- `raw_ingress_kernel.py`: uses serialized ingestion, durable append-before-index ordering, per-shard recovery checkpoints, incremental tail recovery, corruption validation, and deterministic deduplication.

## Verification

Supplied primary acceptance:

- Core updater and migration smokes: PASS.
- Search smokes: 4 PASS.
- Ingress recovery and central-ingress smokes: PASS.
- Ingress evidence reports zero historical decoding for normal 20/100-event runs and 20 concurrent records accepted.

Independent focused attempts:

- `python tools/smoke_core_update_manifest.py` — blocked by `PermissionError: [WinError 5]` creating `D:\temp\pf-core-update-...\core`; cleanup also failed with the same permission error.
- `python tools/smoke_workplace_search_index.py` — blocked by `PermissionError: [WinError 5]` creating the temporary workplace fixture.
- `python tools/smoke_raw_ingress_incremental_recovery.py` — blocked by `PermissionError: [WinError 5]` creating the temporary ingress fixture.

Per brief, no ACL investigation or retry variants were performed.

## Limitations / residual risk

- Symlink-specific updater coverage was skipped in supplied acceptance because Windows symlink creation returned `WinError 1314`.
- Partial out-of-band deletion of an individual ingress index while its checkpoint remains intact is not detected; this is outside the tested crash transitions and should remain an explicit operational limitation.
- Full release, installation, runtime reload, and post-update regression qualification remain pending.