# Core Update Manifest

ProcessForge core updates use an explicit ownership manifest:

```text
processforge-core.manifest.json
```

The release archive contains the new manifest. An installed core root stores the currently installed manifest at the root of the distribution directory. The manifest is the boundary for PF-owned files.

## Manifest contract

Minimum fields:

- `schema_version: 1`
- `kind: processforge.core_manifest`
- `version`
- `generated_at`
- `source`
- `files[]`
  - `relative_path`
  - `size`
  - `sha256`

Paths must be relative to the core root. Absolute paths, backslashes, empty segments, `.`, `..`, and paths escaping the core root are rejected.

`runtime/`, workplace data, project `.pf` data, caches, SQLite indexes, and update journals are derived/local state and should not be modeled as core-owned payload files.

## Update flow

The CLI surface is:

```bash
python bin/pf.py core-update status --core-root <core>
python bin/pf.py core-update plan --core-root <core> --archive <processforge.zip>
python bin/pf.py core-update apply --core-root <core> --archive <processforge.zip> --confirm
python bin/pf.py core-update repair --core-root <core>
```

`plan` is read-only. `apply` requires `--confirm`.

The updater computes:

```text
removed = old_manifest.files - new_manifest.files
added   = new_manifest.files - old_manifest.files
changed = common paths with different sha256
```

Only paths present in the old manifest and absent from the new manifest are deleted. Unknown files are preserved. Directories are removed only when they become empty.

Locally modified PF-owned files are detected by comparing the current file hash with the old installed manifest. They block apply unless the operator explicitly uses the force option.

The new installed manifest is written last, after file changes have succeeded.

## Recovery

Apply writes runtime update state under:

```text
<core>/runtime/core-update/
```

Backups are written before replacing or removing old PF-owned files. If an update is interrupted, `core-update status` reports `incomplete_update`, and `core-update repair` reports the incomplete state for operator handling.

This first slice provides conservative incomplete-state reporting. Automated continue/rollback repair can be added as a later slice.
