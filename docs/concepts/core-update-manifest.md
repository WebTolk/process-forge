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

### Stop, update, validate, restart

In Garage, the operator stops PF and other writers before replacement. In Forge,
the updater owns the single PF executor and its stop/update/start lifecycle.
The file update operation requires an offline target; it does not discover or
exclude every historical process. A known live Workplace App Server blocks apply.

Extract the verified release ZIP outside the installed Core and run that
archive's `bin/pf.py core-update plan|apply` with the installed target and original
ZIP. Pass the Workplace root explicitly when the installation serves one.
Use the existing `server stop --workplace <workplace>` operation for that server
and verify successful shutdown before replacement.

For updater-owned Forge lifecycle, add `--manage-runtime` to the external
installer's `core-update apply --confirm --workplace-root WORKPLACE`.
It preflights the archive, uses the existing guarded `server stop` without
force, applies the file update, then invokes `runtime start` from the updated
target. Startup uses the normal Runtime defaults and persisted configuration;
one-off launch flags from the old process are not inferred. The
`--runtime-timeout` option uses the normal start/stop default of 10 seconds.
Missing confirmation or a blocked preflight does not stop Runtime. A busy stop
prevents file replacement. A failed file update does not attempt startup.
For before-manifest recovery, repeat `--manage-runtime` on the existing
`core-update repair --resume --archive ORIGINAL.zip --confirm --workplace-root WORKPLACE`.
Successful file replacement with failed or unverified startup returns exit 2
and a separate `runtime_lifecycle` result; inspect Runtime before explicitly
retrying its start. This option never imports project journals.

Backups, progress/failure journals, private data and manifest-last verification
are preserved. Installer and target roots must not overlap. Historical native
enrollment markers are neither required nor interpreted as update authority;
they remain untouched. The cooperating file mutex prevents simultaneous update
operations, not arbitrary independently running writers.

With an explicit Workplace, the updater also holds its existing Runtime
singleton mutex for the whole apply/resume operation. After confirming the old
process is absent, it retains that observation while the lifecycle records stay
unchanged; an unrelated process reusing the old PID cannot interrupt the update.
Changed lifecycle records are checked again. The mutex is released on success
and failure so the caller can restart PF or resume recovery.

An installed manifest may own the old Core startup templates
`.pf/AGENTS.md`, `.pf/hooks.yaml` and `.pf/process-forge.yaml`. The updater
backs up their actual preimages or records absence before removing old-only
paths. This compatibility rule depends on manifest ownership, not a product
version. New archives cannot claim private `.pf` data.

Core replacement does not migrate project journals. Existing projects with
legacy journals remain blocked until their explicit
[journal migration](sqlite-journal-maintenance.md); fresh projects start on SQL.
For a manual restart, run `doctor-workplace --root <workplace>` after replacement.
Managed startup uses the normal Runtime configuration validation and verifies the
loaded Core identity. See the [public upgrade evidence](../audits/issue-19-public-upgrade.md).

## Workplace and project data

The current file-only apply/resume route uses `--workplace-root` to select the
Runtime exclusion and optional lifecycle. It does not execute Workplace or
project data migration. Historical archive migration descriptions and a plan's
compatibility assessment do not make those operations part of file replacement.
Workplace configuration maintenance remains a separate explicit operation;
`workplace-init` remains a first-time initialization command.

When PF reports `storage_migration_required` for a project, its agent runs the
documented migration during work on that project. Core replacement does not
enumerate projects or run their migration commands. A restarted Runtime can
produce normal service observations and SQLite sidecars; that is not journal
import or execution-history migration.

## File replacement

The updater computes:

```text
removed = old_manifest.files - new_manifest.files
added   = new_manifest.files - old_manifest.files
changed = common paths with different sha256
```

Only paths present in the old manifest and absent from the new manifest are deleted. Unknown files are preserved. Directories are removed only when they become empty.

PF owns the release-owned Core payload. A confirmed update must bring all such
files to the qualified target release bytes, replacing local Core edits even
when the official bytes did not change between releases. The manifest
differences above therefore do not limit which Core files need replacement.

Existing public flags remain accepted. Force is not required solely for local
Core edits and does not bypass authority, ownership, selection, path, collision
or safety checks. Unknown non-owned files, configuration, project and Workplace
data, and runtime state retain their existing handling. This replacement policy
does not authorize deleting user data.

The new installed manifest is written last, after file changes have succeeded.

## Recovery

Apply writes runtime update state under:

```text
<core>/runtime/core-update/
```

Before replacing or removing old PF-owned files, the existing recovery backup
preserves their actual pre-update bytes, including local edits, and records
absence for missing files. If an update is interrupted or a file operation fails,
`core-update status` reports `incomplete_update`, and `core-update repair` reports
the incomplete state for operator handling.

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

The default repair command and the Python `repair_status` API remain read-only.
The classification alone does not authorize recovery. A new file-only apply
pins the original archive, old/new manifests, saved plan, actual preimage hashes
and lengths, and initial absence of added paths before any payload mutation.

For a failed or interrupted **before-manifest file-only** update made by this
updater, stop the selected Workplace App Server, release the filesystem fault,
and use the same external sealed installer and original archive:

```sh
python installer/bin/pf.py core-update repair --core-root CORE --resume --archive ORIGINAL.zip --workplace-root WORKPLACE --confirm
```

Repeat the original explicit Workplace selection; omit it only when the original
apply omitted it. Without confirmation, no recovery writes occur. Recovery uses
the same cooperating file mutex, physical-target, nonoverlap and offline guards.
It checks target/Workplace identity, all pinned control and backup bytes, and
current touched files against proven initial or exact intended bytes. An
operation interrupted after replacement but before journal publication can be
completed idempotently from those bytes. Progress counters alone grant nothing.

Recovery continues the original plan without replanning around the incomplete
update blocker. It preserves original backups, update identity and failure
history, retains the prior journal for each admitted recovery attempt, verifies
all target-owned bytes, and publishes the manifest last. Another failure retains
the incomplete journal and evidence. Unknown files remain preserved.

Old journals without versioned proof, incomplete/corrupt backups, drift, wrong
archive or bindings, and any after-manifest state
refuse this route. Ordinary apply still refuses incomplete updates. This command
does not roll back files, change SQL bindings or
downgrade Core after SQL commits; those states require their own supported
maintenance procedure.
