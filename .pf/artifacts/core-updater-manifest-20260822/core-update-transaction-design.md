# Core Update Transaction Design

## CLI Surface

- `core-update status --core-root <core>`
- `core-update plan --core-root <core> --archive <processforge.zip>`
- `core-update apply --core-root <core> --archive <processforge.zip> --confirm`
- `core-update repair --core-root <core>`

`plan` is read-only. `apply` requires explicit confirmation.

## Planning

The updater loads the installed manifest if present and the archive manifest from `processforge-core.manifest.json`.

It validates:

- archive exists and is a ZIP;
- archive contains a valid core manifest;
- all manifest paths are contained under core root;
- every manifest file exists in the archive;
- every archive payload sha256 matches the manifest;
- archive payload paths are safe.

It computes:

- `added`
- `removed`
- `changed`
- `unchanged`
- `locally_modified`
- `missing_owned`
- `blockers`

## Apply

Apply sequence:

1. Require `--confirm`.
2. Build and validate the plan.
3. Block on locally modified PF-owned removed/changed files unless explicitly forced.
4. Write `runtime/core-update/in-progress.json`.
5. Back up existing removed/changed files.
6. Delete only `removed` files listed in the old manifest and absent from the new manifest.
7. Remove only empty directories after owned-file deletion.
8. Atomically write added/changed files from the archive where the OS permits.
9. Write the new installed manifest last.
10. Write `last-apply.json`.
11. Remove `in-progress.json`.

## Recovery

This slice detects incomplete updates through `runtime/core-update/in-progress.json`.

`core-update repair` currently reports `manual_repair_required` for incomplete updates. Automated continue/rollback repair remains a future slice.

## Windows Locking

Atomic replacement uses `os.replace`. A locked file causes the operation to fail instead of reporting success. The incomplete marker remains for later inspection.
