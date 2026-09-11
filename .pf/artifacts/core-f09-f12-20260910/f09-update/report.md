# f09-update-report

## Design

- Restores missing unchanged owned files from the new manifest.
- Journals prior absence as `null` in `backed_up`.
- Blocks nonregular owned paths, including symlinks and directories.
- Added `tools/smoke_core_update_missing_owned.py` with `--root`.

## Verification

- `python tools/smoke_core_update_missing_owned.py --root .` — blocked by `PermissionError: [WinError 5]` during temporary fixture creation.
- `python tools/smoke_core_update_manifest.py` — blocked by the same error.

Per brief, no ACL investigation or retries were performed.