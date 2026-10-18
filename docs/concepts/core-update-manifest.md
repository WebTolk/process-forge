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

## Compatible Workplace Migration

An archive may carry a declarative Workplace migration under
`updates/migrations/`. For an existing Workplace, include its root in the same
Core-update transaction:

```text
python bin/pf.py core-update plan --core-root <core> --archive <processforge.zip> --workplace-root <workplace>
python bin/pf.py core-update apply --core-root <core> --archive <processforge.zip> --workplace-root <workplace> --confirm
```

The plan lists only archive-declared operations. Apply is serial: it replaces
the Core files and writes the Core manifest first, then applies the compatible
Workplace migration. Project `.pf` changes are assessed and applied later,
inside each project's own governed work. Concurrent independent Core or
Workplace applies are unsupported.

The 1.0.2-to-1.1.0 migration
adds the built-in `codex-exec` driver and its registry entry only when missing;
existing files and registry entries are preserved. It does not invoke
`workplace-init`, which remains a first-time initialization command.

Before a migration write, the updater copies the affected Workplace files into
the Core update backup directory and records the operation in the update
journal. When the post-Core Workplace migration cannot finish, the Core remains
at its new manifest and `core-update repair` reports a manual-repair state with
the backup location. A successful apply automatically runs the short
`doctor-workplace` check and stores its result in `last-apply.json`.

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

Backups are written before replacing or removing old PF-owned files. If an update is interrupted or a file operation fails, `core-update status` reports `incomplete_update`, and `core-update repair` reports the incomplete state for operator handling.

File operation failures, including locked-file style failures surfaced by the OS, are converted into explicit `file_operation_failed` errors and leave `runtime/core-update/in-progress.json` with `status: failed`.

The incomplete update journal records:

- installed and target versions;
- update archive;
- backup directory;
- counts;
- completed operations;
- pending operations;
- backed-up files;
- failure code/message when available.

`core-update repair` classifies incomplete states as:

- `safe_to_rollback` when the update failed before manifest write and the old manifest backup is present;
- `manual_repair_required` when the manifest was already written, the journal is incomplete, or safety cannot be proven;
- `nothing_to_repair` when no incomplete update exists.

Automated continue/rollback execution remains intentionally narrower than the
classification contract and should only be added for states that the journal can
prove safe.
